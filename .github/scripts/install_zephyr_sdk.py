#!/usr/bin/env python3
"""
Download and install the Zephyr SDK inside GitHub Actions.

The SDK version can be controlled through the ZSDK_VERSION environment variable.
If it is empty or unset, the script falls back to the latest release.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional


REPO_RELEASES = "https://api.github.com/repos/zephyrproject-rtos/sdk-ng/releases"


def resolve_release(version: Optional[str]) -> Dict:
    """Fetch the release metadata for a specific version or the latest release."""
    version = (version or "").strip()
    url = f"{REPO_RELEASES}/tags/v{version}" if version else f"{REPO_RELEASES}/latest"
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "zephyr-ci-cd"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Failed to fetch SDK release metadata from {url}: {exc}") from exc


def pick_installer_asset(release: Dict) -> Dict:
    """Pick the standard Linux installer asset."""
    assets = release.get("assets", []) or []
    linux_assets = []
    for asset in assets:
        name = asset.get("name", "")
        lowered = name.lower()
        if not lowered.endswith(".run"):
            continue
        if "linux" not in lowered or "x86_64" not in lowered:
            continue
        if "hosttools" in lowered:
            continue
        if "setup" not in lowered:
            continue
        linux_assets.append(asset)
    if linux_assets:
        return linux_assets[0]
    asset_names = ", ".join(a.get("name", "<unknown>") for a in assets) or "<no assets>"
    raise SystemExit(
        f"Zephyr SDK linux installer not found. Available assets: {asset_names}"
    )


def download(url: str, destination: Path) -> None:
    """Stream the remote file to disk."""
    with urllib.request.urlopen(url) as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)


def main() -> None:
    version = os.environ.get("ZSDK_VERSION", "")
    release = resolve_release(version)
    asset = pick_installer_asset(release)
    download_url = asset["browser_download_url"]

    workspace = Path.cwd()
    installer_path = workspace / asset["name"]
    print(f"Downloading {download_url} -> {installer_path}")
    download(download_url, installer_path)

    installer_path.chmod(installer_path.stat().st_mode | stat.S_IEXEC)
    sdk_dir = Path(os.environ["HOME"]) / "zephyr-sdk"
    print(f"Installing Zephyr SDK into {sdk_dir}")
    subprocess.run([str(installer_path), "--", "-d", str(sdk_dir)], check=True)

    github_env = os.environ.get("GITHUB_ENV")
    if not github_env:
        raise SystemExit("GITHUB_ENV is not set; cannot persist SDK path.")
    with open(github_env, "a", encoding="utf-8") as env_file:
        env_file.write(f"ZEPHYR_SDK_INSTALL_DIR={sdk_dir}\n")
    print(f"Recorded ZEPHYR_SDK_INSTALL_DIR in {github_env}")


if __name__ == "__main__":
    main()

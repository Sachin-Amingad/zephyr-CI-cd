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
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple


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


def pick_installer_asset(release: Dict) -> Tuple[Dict, str]:
    """Pick the best available Linux installer asset. Returns the asset and type."""
    assets = release.get("assets", []) or []

    def filtered(predicate):
        return [asset for asset in assets if predicate(asset)]

    run_assets = filtered(
        lambda asset: asset.get("name", "").endswith(".run")
        and "linux" in asset.get("name", "").lower()
        and "x86_64" in asset.get("name", "").lower()
        and "hosttools" not in asset.get("name", "").lower()
    )
    if run_assets:
        return run_assets[0], "run"

    tar_assets = filtered(
        lambda asset: asset.get("name", "").endswith(".tar.xz")
        and "linux" in asset.get("name", "").lower()
        and "x86_64" in asset.get("name", "").lower()
    )
    if tar_assets:
        preferred = [a for a in tar_assets if "minimal" not in a.get("name", "").lower()]
        asset = preferred[0] if preferred else tar_assets[0]
        return asset, "tar"

    asset_names = ", ".join(a.get("name", "<unknown>") for a in assets) or "<no assets>"
    raise SystemExit(
        f"Zephyr SDK Linux installer not found. Available assets: {asset_names}"
    )


def download(url: str, destination: Path) -> None:
    """Stream the remote file to disk."""
    with urllib.request.urlopen(url) as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)


def install_from_run(installer_path: Path, sdk_dir: Path) -> Path:
    installer_path.chmod(installer_path.stat().st_mode | stat.S_IEXEC)
    subprocess.run([str(installer_path), "--", "-d", str(sdk_dir)], check=True)
    return sdk_dir


def install_from_tarball(archive_path: Path, version: str) -> Path:
    home = Path.home()
    print(f"Extracting {archive_path} into {home}")
    with tarfile.open(archive_path) as tar:
        tar.extractall(path=home)

    candidates = []
    version = (version or "").strip()
    if version:
        candidates.append(home / f"zephyr-sdk-{version}")

    base_name = archive_path.name.replace(".tar.xz", "")
    # Strip platform suffix (e.g., _linux-x86_64 or _linux-x86_64_minimal)
    if "_linux" in base_name:
        candidates.append(home / base_name.split("_linux", 1)[0])
    candidates.append(home / base_name)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    extracted = sorted(home.glob("zephyr-sdk-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if extracted:
        return extracted[0]

    raise SystemExit("Failed to locate extracted Zephyr SDK directory after unpacking tarball.")


def main() -> None:
    version = os.environ.get("ZSDK_VERSION", "")
    release = resolve_release(version)
    asset, asset_type = pick_installer_asset(release)
    download_url = asset["browser_download_url"]

    workspace = Path.cwd()
    artifact_path = workspace / asset["name"]
    print(f"Downloading {download_url} -> {artifact_path}")
    download(download_url, artifact_path)

    sdk_dir = Path(os.environ["HOME"]) / "zephyr-sdk"
    if asset_type == "run":
        print(f"Installing Zephyr SDK via installer into {sdk_dir}")
        install_from_run(artifact_path, sdk_dir)
    else:
        print("Installer (.run) not available, falling back to tarball extraction.")
        sdk_dir = install_from_tarball(artifact_path, version)
        print(f"Tarball extracted to {sdk_dir}")

    github_env = os.environ.get("GITHUB_ENV")
    if not github_env:
        raise SystemExit("GITHUB_ENV is not set; cannot persist SDK path.")
    with open(github_env, "a", encoding="utf-8") as env_file:
        env_file.write(f"ZEPHYR_SDK_INSTALL_DIR={sdk_dir}\n")
    print(f"Recorded ZEPHYR_SDK_INSTALL_DIR={sdk_dir} in {github_env}")


if __name__ == "__main__":
    main()

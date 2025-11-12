# zephyr-CI-cd

## CI/CD Pipeline for Zephyr Platform

This repository contains a CI/CD pipeline for the Zephyr platform. The pipeline is designed to:

1. Build the Zephyr project using `clang`.
2. Run unit tests using `ztest`.
3. Perform hardware-in-the-loop (HIL) testing.

### Tools Used
- **Clang**: For building the project.
- **Ztest**: For running unit tests.
- **Hardware Loop**: For testing on actual hardware.

### Setting Up the Pipeline
1. Clone this repository.
2. Ensure the following tools are installed:
   - Clang
   - Zephyr SDK
   - Ztest framework
3. Configure the hardware for HIL testing.

### Running the Pipeline
The pipeline is automated using a CI/CD tool (e.g., GitHub Actions). It will:
- Build the project.
- Run unit tests.
- Execute hardware tests.

Refer to the `.github/workflows/ci.yml` file (or equivalent) for detailed pipeline steps.
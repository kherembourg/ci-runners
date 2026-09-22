# Qualification evidence

Updated 2026-09-23. This page distinguishes observed results from planned capabilities.

## Host

- Apple M1 Pro, 8 CPU cores, 32 GiB RAM, macOS 27.0.
- AC power connected; system sleep on AC power is disabled.
- Tart 2.37.0 from the official release archive, SHA-256 verified before extraction.
- Softnet 0.23.0 installed from the official Homebrew tap and used for job-clone isolation.
- Limit configured to two VMs, each 4 vCPUs and 8192 MiB RAM.

## Linux lane

- Ubuntu 24.04 ARM64 base: `ghcr.io/cirruslabs/ubuntu:24.04`.
- GitHub Actions runner 2.337.0 ARM64 installed from an archive checked against its published SHA-256.
- Docker Engine 29.1.3 from Ubuntu packages.
- In a Softnet-isolated clone, `nproc` reported 4, `free -m` reported 7914 MiB total, GitHub HTTPS egress worked, and Docker ran an ARM64 `hello-world` container.
- A local lifecycle test passed: clone, boot, stdin-only JIT handoff, runner execution, stop, and clone deletion.
- [GitHub Actions Linux smoke run 35783619253](https://github.com/kherembourg/ci-runners/actions/runs/35783619253) passed its CPU, memory, and Docker steps. The ephemeral runner removed its registration; the clone was deleted afterward.
- The Android Gradle Plugin's AAPT2 Linux artifact failed to start in an ARM64 guest during [finance's Android run](https://github.com/kherembourg/finance/actions/runs/35790257111). Android application builds are routed to macOS ARM64 until a separate Linux ARM64 toolchain is qualified.

## macOS lane

- macOS ARM64 base: `ghcr.io/cirruslabs/macos-tahoe-xcode:26.5`.
- The guest reported 4 vCPUs, 8589934592 bytes of memory, Xcode 26.5, and Swift 6.3.2.
- GitHub Actions runner 2.337.0 ARM64 installed from an archive checked against its published SHA-256.
- [GitHub Actions macOS smoke run 35785084902](https://github.com/kherembourg/ci-runners/actions/runs/35785084902) passed its CPU, memory, Xcode, and Swift steps. The ephemeral runner removed its registration; the clone was deleted afterward.
- An iPhone 17 Pro simulator booted in a disposable clone and reached terminal `bootstatus` in about 49 seconds. [KaMPKit iOS](https://github.com/kherembourg/KaMPKit/actions/runs/35786695244) and [lebref iOS](https://github.com/kherembourg/lebref/actions/runs/35786740613) subsequently passed project-specific Apple Silicon jobs.
- [KaMPKit Android build](https://github.com/kherembourg/KaMPKit/actions/runs/35792825395) passed on a macOS ARM64 runner with native Android SDK tools.
- [KaMPKit iOS build](https://github.com/kherembourg/KaMPKit/actions/runs/35792825410) also passed on the final workflow commit.
- [lebref's complete CI](https://github.com/kherembourg/lebref/actions/runs/35793479459) passed server, web, desktop, iOS simulator, and Android jobs on the personal runners.
- [finance's complete CI](https://github.com/kherembourg/finance/actions/runs/35793189870) passed server, Android tests and coverage, iOS simulator compilation, and Xcode simulator build on the personal runners.

## Capacity and unattended service

Unit tests confirm that only two jobs are admitted while a third waits, and that an orphaned clone reserves capacity until its runner state is inspected. A live mixed-lane overlap had one Linux and one macOS clone running at the same time; both [Linux](https://github.com/kherembourg/ci-runners/actions/runs/35785204958) and [macOS](https://github.com/kherembourg/ci-runners/actions/runs/35785209188) GitHub jobs passed, and both clones were deleted. The dedicated GitHub App is installed, and a live installation token was verified to expose exactly the five configured repositories. The unattended LaunchAgent automatically admitted and completed separate [Linux](https://github.com/kherembourg/ci-runners/actions/runs/35786415003) and [macOS](https://github.com/kherembourg/ci-runners/actions/runs/35786418676) smoke runs; both passed.

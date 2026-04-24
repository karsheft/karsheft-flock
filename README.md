# Karsheft Flock

> A cross-platform, federated package distribution system for deterministic, auditable installation of deb packages — with tiered trust verification and GitHub Pages as the default mirror backend.

## Overview

Karsheft Flock is a package management layer built on top of the Debian package format (`.deb`). It provides:

- **Deterministic installs** via a version-controlled lockfile (`flock.lock`)
- **Tiered trust verification** — lightweight checksum verification for developers, full GPG + checksum verification for CI/CD and end-user builds
- **Flock packages** — a thin metadata wrapper around `.deb` files with extended provenance and signing fields
- **GitHub Pages mirror** — the default publishing backend, making any GitHub repository a valid Karsheft Flock package mirror
- **Federated network** — any compliant mirror (GitHub Pages or otherwise) can participate; no central registry required

## Documentation

- [Trust Model & Developer Protocols](docs/trust-model.md)
- [Flock Package Format](docs/flock-package-format.md)
- [Mirror Protocol](docs/mirror-protocol.md)
- [CLI Specification](docs/cli-spec.md)
- [Federation Protocol](docs/federation.md)
- [CI/CD Integration](docs/cicd.md)

## Quick Start

```bash
# Initialize a flock manifest in your project
flock init

# Resolve and lock packages (developer mode)
flock resolve --pkg curl --pkg build-essential

# Install from lockfile (developer default: checksum verification)
flock install

# Install with full verification (CI/CD mode)
flock install --verify=full
```

## License

Apache 2.0

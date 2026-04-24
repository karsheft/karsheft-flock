import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from .manifest import init_manifest, read_manifest
from .lockfile import read_lockfile, write_lockfile
from .resolver import resolve_packages, PackageNotFoundError
from .installer import install_packages
from .verify import VERIFY_LEVELS, VerificationError

MANIFEST_FILE = "flock.toml"
LOCKFILE = "flock.lock"
DEFAULT_MIRROR = "https://deb.debian.org/debian"


@click.group()
@click.version_option(package_name="karsheft-flock")
def main() -> None:
    """Flock — reproducible Debian package management with cryptographic verification."""


@main.command()
def init() -> None:
    """Initialize a flock.toml manifest in the current directory."""
    path = Path(MANIFEST_FILE)
    if path.exists():
        raise click.ClickException(
            f"{MANIFEST_FILE} already exists. Remove it first if you want to reinitialize."
        )
    init_manifest(path)
    click.echo(click.style(f"Created {MANIFEST_FILE}", fg="green"))
    click.echo("Add packages with [[package]] entries, then run 'flock resolve'.")


@main.command()
@click.option(
    "--pkg",
    "packages",
    multiple=True,
    required=True,
    metavar="NAME",
    help="Package name to resolve. May be specified multiple times.",
)
@click.option(
    "--verify",
    "verify_level",
    default="checksum",
    show_default=True,
    type=click.Choice(list(VERIFY_LEVELS)),
    help="Verification level to embed in the lockfile.",
)
@click.option(
    "--mirror",
    default=DEFAULT_MIRROR,
    show_default=True,
    help="Debian mirror base URL.",
)
def resolve(packages: tuple[str, ...], verify_level: str, mirror: str) -> None:
    """Resolve packages and write flock.lock."""
    click.echo(f"Resolving {len(packages)} package(s) from {mirror} ...")

    try:
        resolved = resolve_packages(list(packages), mirror, verify_level)
    except PackageNotFoundError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Resolution failed: {e}")

    timestamp = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    lockfile_data = {
        "meta": {
            "generated_by": "flock resolve",
            "verify_level": verify_level,
            "timestamp": timestamp,
        },
        "package": resolved,
    }

    lockfile_path = Path(LOCKFILE)
    write_lockfile(lockfile_path, lockfile_data)

    click.echo(click.style(f"Wrote {LOCKFILE} with {len(resolved)} package(s).", fg="green"))
    for pkg in resolved:
        click.echo(f"  {pkg['name']} {pkg['version']} ({pkg['architecture']})")


@main.command("install")
@click.option(
    "--verify",
    "verify_level",
    default="checksum",
    show_default=True,
    type=click.Choice(list(VERIFY_LEVELS)),
    help="Verification level. 'none' requires --i-understand-the-risk.",
)
@click.option(
    "--i-understand-the-risk",
    "i_understand_the_risk",
    is_flag=True,
    default=False,
    help="Required when --verify=none. Acknowledges that verification is disabled.",
)
def install(verify_level: str, i_understand_the_risk: bool) -> None:
    """Install packages from flock.lock."""
    lockfile_path = Path(LOCKFILE)

    try:
        lockfile_data = read_lockfile(lockfile_path)
    except FileNotFoundError as e:
        raise click.ClickException(str(e))

    if verify_level == "none" and not i_understand_the_risk:
        raise click.ClickException(
            "--verify=none requires --i-understand-the-risk flag. "
            "This disables all cryptographic verification."
        )

    if verify_level == "none":
        click.echo(
            click.style(
                "WARNING: verification is DISABLED (--verify=none). "
                "Packages are being installed without integrity checks.",
                fg="red",
                bold=True,
            ),
            err=True,
        )

    packages = lockfile_data.get("package", [])
    click.echo(f"Installing {len(packages)} package(s) [verify={verify_level}]...")

    try:
        install_packages(lockfile_data, verify_level, i_understand_the_risk)
    except VerificationError as e:
        raise click.ClickException(f"Verification failed: {e}")
    except RuntimeError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Installation failed: {e}")

    click.echo(click.style("All packages installed successfully.", fg="green"))

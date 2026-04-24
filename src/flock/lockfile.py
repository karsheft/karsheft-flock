import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

def _enforce_read_only_at_install_time(path: Path) -> None:
    """Raise RuntimeError if called during install with a path that would overwrite the lockfile."""
    raise RuntimeError(
        f"Refusing to write to lockfile at install time: {path}\n"
        "The lockfile (flock.lock) is read-only during 'flock install'. "
        "Run 'flock resolve' to regenerate it."
    )


def read_lockfile(path: Path) -> dict:
    """Read flock.lock file. Raises FileNotFoundError if missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"Lockfile not found: {path}\n"
            "Run 'flock resolve' to generate the lockfile."
        )
    with open(path, "rb") as f:
        return tomllib.load(f)


def write_lockfile(path: Path, data: dict) -> None:
    """Write lockfile data to flock.lock in TOML format."""
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


def assert_lockfile_not_modified(original: dict, current: dict) -> None:
    """Raise ValueError if two lockfile dicts differ (lockfile was modified)."""
    if original != current:
        raise ValueError(
            "Lockfile has been modified since it was last read. "
            "The lockfile must not be modified at install time. "
            "Re-run 'flock resolve' to regenerate a consistent lockfile."
        )

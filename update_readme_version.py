"""Update the version shown in README.md to match VERSION in ezee-backup.py.

Run by build_gui.bat after a successful build. Updates:
  - the "**Current version: X.**" line
  - the numbered build example, "dist\\ezee-backup - (VX).exe"
"""
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
APP_FILE = PROJECT_DIR / "ezee-backup.py"
README_FILE = PROJECT_DIR / "README.md"

VERSION_PATTERN = re.compile(r'^VERSION = "([^"]+)"', re.MULTILINE)
CURRENT_VERSION_PATTERN = re.compile(r"(\*\*Current version: )[^*]+?(\.\*\*)")
NUMBERED_EXE_PATTERN = re.compile(r"(dist\\ezee-backup - \(V)[^)<>]+(\)\.exe)")


def read_app_version(app_text: str) -> str:
    match = VERSION_PATTERN.search(app_text)
    if not match:
        raise ValueError("VERSION not found in ezee-backup.py")
    return match.group(1)


def update_readme_text(readme_text: str, version: str) -> tuple[str, int]:
    """Return the README text with the version updated, and how many places were changed."""
    updated, current_count = CURRENT_VERSION_PATTERN.subn(rf"\g<1>{version}\g<2>", readme_text)
    # The pattern excludes "<" and ">", so the "(V<version>)" placeholder in the text is left alone.
    updated = NUMBERED_EXE_PATTERN.sub(rf"\g<1>{version}\g<2>", updated)
    changed = sum(1 for old, new in zip(readme_text.splitlines(), updated.splitlines()) if old != new)
    if current_count == 0:
        raise ValueError('"**Current version: ...**" line not found in README.md')
    return updated, changed


def main() -> int:
    try:
        version = read_app_version(APP_FILE.read_text(encoding="utf-8"))
        with README_FILE.open("r", encoding="utf-8", newline="") as handle:
            readme_text = handle.read()
        updated, changed = update_readme_text(readme_text, version)
        if changed:
            with README_FILE.open("w", encoding="utf-8", newline="") as handle:
                handle.write(updated)
            print(f"README.md updated to version {version} ({changed} line(s) changed).")
        else:
            print(f"README.md already shows version {version}.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"WARNING: Could not update the README version: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

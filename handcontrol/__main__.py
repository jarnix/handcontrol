"""Placeholder entry point; replaced by the real CLI in Task 11."""

from handcontrol import __version__


def main(argv: list[str] | None = None) -> int:
    print(f"handcontrol {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

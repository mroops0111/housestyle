import sys

from .. import __version__


def main() -> int:
    sys.stdout.write(f"commentstyle {__version__}\n")
    sys.stdout.write("Not implemented yet. See the repository for status.\n")
    return 0

"""Write requirements-linux.txt: requirements.txt minus Windows-only packages.

requirements.txt is a full `pip freeze` from a Windows PC, so it contains packages
(e.g. pywinpty) that cannot be installed on Linux (Docker, GitHub Actions).
"""

import re
import sys
from pathlib import Path

WINDOWS_ONLY = {"pywin32", "pywinpty", "pypiwin32", "pywin32-ctypes"}


def main(src: str = "requirements.txt", dst: str = "requirements-linux.txt") -> None:
    raw = Path(src).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    kept, dropped = [], []
    for line in text.splitlines():
        name = re.split(r"[=<>~!\s;\[]", line.strip(), maxsplit=1)[0].lower()
        (dropped if name in WINDOWS_ONLY else kept).append(line)
    Path(dst).write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"{dst}: kept {len(kept)} lines, dropped {dropped}")


if __name__ == "__main__":
    main(*sys.argv[1:3])

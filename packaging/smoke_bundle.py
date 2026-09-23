"""Launch a frozen desktop app and verify that it opens a sample .pdet file."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from particle_detector.model import Pulse, Recording
from particle_detector.storage import save_pdet


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python packaging/smoke_bundle.py EXECUTABLE")
    executable = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="pdet-smoke-") as directory:
        sample = Path(directory) / "sample.pdet"
        result = Path(directory) / "result.txt"
        save_pdet(sample, Recording(
            "alpha", 48000, "2026-09-24T00:00:00Z",
            [Pulse(1000, -950, [0, -950, 0]), Pulse(2000, -1100, [0, -1100, 0])],
        ))
        env = dict(os.environ)
        env.update(PDET_SMOKE_RECORDING=str(sample), PDET_SMOKE_OUTPUT=str(result))
        env.setdefault("APPIMAGE_EXTRACT_AND_RUN", "1")
        process = subprocess.run([str(executable)], env=env, capture_output=True, text=True, timeout=90)
        content = result.read_text() if result.exists() else ""
        if process.returncode != 0 or content != "pulses=2 profile=alpha\n":
            print(f"exit={process.returncode} result={content!r}\n{process.stdout}\n{process.stderr}", file=sys.stderr)
            return 1
        print("Frozen app opened sample.pdet: 2 alpha pulses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

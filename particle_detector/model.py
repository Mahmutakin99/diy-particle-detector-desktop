from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(eq=True)
class Calibration:
    """User supplied amplitude / energy pairs. Energy is always in keV."""

    points: list[tuple[float, float]]

    def __post_init__(self):
        if len(self.points) < 2 or len({p[0] for p in self.points}) != len(self.points):
            raise ValueError("Calibration needs two or more distinct amplitudes")
        if any(a <= 0 or e <= 0 for a, e in self.points):
            raise ValueError("Calibration values must be positive")
        if self.slope <= 0:
            raise ValueError("Calibration energy must increase with amplitude")

    @property
    def slope(self):
        xs, ys = zip(*self.points)
        xbar, ybar = sum(xs) / len(xs), sum(ys) / len(ys)
        return sum((x - xbar) * (y - ybar) for x, y in self.points) / sum((x - xbar) ** 2 for x in xs)

    def energy_kev(self, amplitude: float) -> float:
        xs, ys = zip(*self.points)
        return self.slope * (amplitude - sum(xs) / len(xs)) + sum(ys) / len(ys)


@dataclass(eq=True)
class Pulse:
    timestamp_us: int
    peak: float
    waveform: list[float] = field(default_factory=list)


@dataclass(eq=True)
class Recording:
    profile: str
    sample_rate: int
    started_at: str
    pulses: list[Pulse] = field(default_factory=list)
    calibration: Calibration | None = None
    lost_samples: int = 0

    def __post_init__(self):
        if self.profile not in ("electron", "alpha"):
            raise ValueError("Unknown detector profile")
        if not 8000 <= self.sample_rate <= 384000:
            raise ValueError("Unsupported sample rate")


def default_data_dir() -> Path:
    import os
    import sys

    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "DIY Particle Detector" / "recordings"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

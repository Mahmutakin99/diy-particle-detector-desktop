"""Small command-line analysis for portable and legacy recordings."""

import argparse
from collections import Counter

from .storage import load_recording


def main():
    parser = argparse.ArgumentParser(description="Inspect a DIY Particle Detector recording")
    parser.add_argument("recording")
    parser.add_argument("--trusted-pickle", action="store_true", help="Allow a trusted local .pkl file to be decoded")
    args = parser.parse_args()
    recording = load_recording(args.recording, trusted_pickle=args.trusted_pickle)
    duration = (recording.pulses[-1].timestamp_us - recording.pulses[0].timestamp_us) / 1e6 if len(recording.pulses) > 1 else 0
    print(f"profile: {recording.profile}\nsample rate: {recording.sample_rate} Hz\npulses: {len(recording.pulses)}\nduration: {duration:.2f} s")
    if recording.calibration:
        print("calibration: enabled (energy output is in keV)")
    else:
        print("calibration: unavailable; amplitudes are not energies")


if __name__ == "__main__":
    main()

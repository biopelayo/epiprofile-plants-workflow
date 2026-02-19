#!/usr/bin/env python3
"""
Full pipeline: raw -> MSConvert (centroided mzML) -> xtract_xml.exe (.ms1 + .ms2)

For each PXD dataset:
  1. MSConvert: raw/*.raw -> mzML/*.mzML (peakPicking vendor, metadataFixer)
  2. xtract_xml: mzML/*.mzML -> MS1_MS2/*.ms1 + *.HCD.*.ms2
  3. Rename: *.HCD.*.ms2 -> *.ms2
  4. Create empty: RawData/*.raw (placeholders for EpiProfile)
  5. Clean up intermediate mzML (optional, saves disk space)

Usage:
  python convert_and_extract.py [--pxd PXD046034] [--skip-msconvert] [--keep-mzml]
  python convert_and_extract.py --pxd PXD046034 --base D:/epiprofile_data
  python convert_and_extract.py --pxd PXD046034 --msconvert /path/to/msconvert.exe --xtract /path/to/xtract_xml.exe
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import time

# Defaults (Windows local machine) -- override via CLI args or env vars
DEFAULT_MSCONVERT = os.environ.get(
    "MSCONVERT_PATH", r"D:\MS\share\OpenMS\THIRDPARTY\pwiz-bin\msconvert.exe"
)
DEFAULT_XTRACT = os.environ.get(
    "XTRACT_PATH", r"D:\EpiProfile2.1_1Basic_Running_version\xtract_xml.exe"
)
DEFAULT_BASE = os.environ.get("EPIPROFILE_DATA", r"D:\epiprofile_data")

ALL_PXD = ["PXD046034", "PXD046788", "PXD014739"]


def convert_raw_to_mzml(raw_dir, mzml_dir, msconvert_path):
    """MSConvert: raw -> centroided mzML (full, no ms-level split)."""
    mzml_dir.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(raw_dir.glob("*.raw"))
    total = len(raw_files)
    done = 0
    errors = []

    for i, raw in enumerate(raw_files, 1):
        stem = raw.stem
        out = mzml_dir / f"{stem}.mzML"
        if out.exists() and out.stat().st_size > 0:
            done += 1
            print(f"  [{i}/{total}] {stem} - already exists ({out.stat().st_size/1e6:.0f} MB), skip")
            continue

        print(f"  [{i}/{total}] {stem} - converting...", end=" ", flush=True)
        t0 = time.time()
        try:
            result = subprocess.run(
                [
                    msconvert_path, str(raw),
                    "--filter", "peakPicking vendor msLevel=1-",
                    "--filter", "metadataFixer",
                    "--outdir", str(mzml_dir),
                ],
                capture_output=True, text=True, timeout=600
            )
            elapsed = time.time() - t0
            if out.exists() and out.stat().st_size > 0:
                done += 1
                print(f"OK ({out.stat().st_size/1e6:.0f} MB, {elapsed:.0f}s)")
            else:
                errors.append(stem)
                print(f"FAIL (no output after {elapsed:.0f}s)")
                if result.stderr:
                    print(f"    stderr: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            errors.append(stem)
            print("TIMEOUT (600s)")
        except Exception as e:
            errors.append(stem)
            print(f"ERROR: {e}")

    return done, errors


def extract_ms1_ms2(mzml_dir, out_dir, xtract_path):
    """xtract_xml.exe: mzML -> .ms1 + .ms2 files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    mzml_files = sorted(mzml_dir.glob("*.mzML"))
    total = len(mzml_files)
    done = 0
    errors = []

    for i, mzml in enumerate(mzml_files, 1):
        stem = mzml.stem
        ms1_out = out_dir / f"{stem}.ms1"
        if ms1_out.exists() and ms1_out.stat().st_size > 0:
            done += 1
            print(f"  [{i}/{total}] {stem} - already extracted, skip")
            continue

        print(f"  [{i}/{total}] {stem} - extracting...", end=" ", flush=True)
        t0 = time.time()
        try:
            result = subprocess.run(
                [xtract_path, "-ms", "-o", str(out_dir), str(mzml)],
                capture_output=True, text=True, timeout=300,
                cwd=str(pathlib.Path(xtract_path).parent)
            )
            elapsed = time.time() - t0
            if ms1_out.exists() and ms1_out.stat().st_size > 0:
                done += 1
                print(f"OK ({elapsed:.0f}s)")
            else:
                errors.append(stem)
                print(f"FAIL after {elapsed:.0f}s")
                if result.stderr:
                    print(f"    stderr: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            errors.append(stem)
            print("TIMEOUT (300s)")
        except Exception as e:
            errors.append(stem)
            print(f"ERROR: {e}")

    return done, errors


def rename_ms2_files(out_dir):
    """Rename sample.HCD.FTMS.ms2 (or any *.ms2 with extra parts) -> sample.ms2."""
    renamed = 0
    for f in out_dir.iterdir():
        if f.suffix == ".ms2" and f.name.count(".") > 1:
            # e.g. 3905_fas1.HCD.FTMS.ms2 -> 3905_fas1.ms2
            stem_parts = f.name.split(".")
            new_name = f"{stem_parts[0]}.ms2"
            new_path = f.parent / new_name
            if new_path.exists() and new_path != f:
                new_path.unlink()
            f.rename(new_path)
            renamed += 1
    return renamed


def create_raw_empty(out_dir, raw_data_dir):
    """Create empty .raw placeholder files matching each .ms1 file."""
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for ms1 in sorted(out_dir.glob("*.ms1")):
        raw = raw_data_dir / f"{ms1.stem}.raw"
        if not raw.exists():
            raw.touch()
            created += 1
    return created


def cleanup_extras(out_dir):
    """Remove .rawInfo, .xtract temp files from xtract output dir."""
    removed = 0
    for pattern in ["*.rawInfo", "*.xtract"]:
        for f in out_dir.glob(pattern):
            f.unlink()
            removed += 1
    return removed


def process_pxd(pxd, base_dir, msconvert_path, xtract_path,
                skip_msconvert=False, keep_mzml=False):
    """Full pipeline for one PXD dataset."""
    pxd_dir = base_dir / pxd
    raw_dir = pxd_dir / "raw"
    mzml_dir = pxd_dir / "mzML"
    out_dir = pxd_dir / "MS1_MS2"
    raw_data_dir = pxd_dir / "RawData"

    n_raw = len(list(raw_dir.glob("*.raw")))
    print(f"\n{'='*60}")
    print(f"  {pxd}: {n_raw} raw files")
    print(f"{'='*60}")

    # Step 1: MSConvert
    if not skip_msconvert:
        print(f"\n[Step 1] MSConvert: raw -> mzML")
        done, errors = convert_raw_to_mzml(raw_dir, mzml_dir, msconvert_path)
        print(f"  Result: {done}/{n_raw} converted, {len(errors)} errors")
        if errors:
            print(f"  Failed: {errors}")
            return False
    else:
        print(f"\n[Step 1] MSConvert: SKIPPED (--skip-msconvert)")

    # Step 2: xtract_xml
    n_mzml = len(list(mzml_dir.glob("*.mzML")))
    print(f"\n[Step 2] xtract_xml: mzML -> .ms1 + .ms2 ({n_mzml} files)")
    done, errors = extract_ms1_ms2(mzml_dir, out_dir, xtract_path)
    print(f"  Result: {done}/{n_mzml} extracted, {len(errors)} errors")
    if errors:
        print(f"  Failed: {errors}")

    # Step 3: Rename ms2
    print(f"\n[Step 3] Rename *.HCD.*.ms2 -> *.ms2")
    renamed = rename_ms2_files(out_dir)
    print(f"  Renamed: {renamed} files")

    # Step 4: Create RawData placeholders
    print(f"\n[Step 4] Create RawData/ empty .raw placeholders")
    created = create_raw_empty(out_dir, raw_data_dir)
    print(f"  Created: {created} files")

    # Step 5: Cleanup xtract extras
    removed = cleanup_extras(out_dir)
    print(f"  Cleaned up {removed} temp files (.rawInfo, .xtract)")

    # Step 6: optionally delete mzML
    if not keep_mzml:
        print(f"\n[Step 5] Deleting intermediate mzML/ to save space...")
        sz = sum(f.stat().st_size for f in mzml_dir.glob("*.mzML"))
        shutil.rmtree(mzml_dir)
        print(f"  Freed {sz/1e9:.1f} GB")

    # Summary
    n_ms1 = len(list(out_dir.glob("*.ms1")))
    n_ms2 = len(list(out_dir.glob("*.ms2")))
    n_raw_e = len(list(raw_data_dir.glob("*.raw")))
    ms1_sz = sum(f.stat().st_size for f in out_dir.glob("*.ms1"))
    ms2_sz = sum(f.stat().st_size for f in out_dir.glob("*.ms2"))

    print(f"\n  DONE: {n_ms1} .ms1 ({ms1_sz/1e9:.1f} GB) + {n_ms2} .ms2 ({ms2_sz/1e9:.1f} GB) + {n_raw_e} .raw (empty)")
    ok = n_ms1 == n_raw and n_ms2 == n_raw and n_raw_e == n_raw
    if ok:
        print(f"  [OK] All {n_raw} triads complete")
    else:
        print(f"  [FAIL] MISMATCH: expected {n_raw} each")
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="raw -> mzML -> xtract_xml -> EpiProfile triada",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pxd PXD046034
  %(prog)s --pxd PXD046034 PXD046788 --keep-mzml
  %(prog)s --pxd PXD046034 --base /data/epiprofile --msconvert /usr/local/bin/msconvert
        """,
    )
    parser.add_argument("--pxd", nargs="*", default=ALL_PXD,
                        help="PXD IDs to process (default: all three)")
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help=f"Base data directory (default: {DEFAULT_BASE})")
    parser.add_argument("--msconvert", default=DEFAULT_MSCONVERT,
                        help=f"Path to msconvert.exe (default: {DEFAULT_MSCONVERT})")
    parser.add_argument("--xtract", default=DEFAULT_XTRACT,
                        help=f"Path to xtract_xml.exe (default: {DEFAULT_XTRACT})")
    parser.add_argument("--skip-msconvert", action="store_true",
                        help="Skip MSConvert step (use existing mzML)")
    parser.add_argument("--keep-mzml", action="store_true",
                        help="Keep intermediate mzML files (default: delete to save space)")
    args = parser.parse_args()

    base_dir = pathlib.Path(args.base)
    msconvert_path = args.msconvert
    xtract_path = args.xtract

    print(f"MSConvert: {msconvert_path}")
    print(f"xtract_xml: {xtract_path}")
    print(f"Base dir: {base_dir}")
    print(f"Datasets: {args.pxd}")

    t0 = time.time()
    results = {}
    for pxd in args.pxd:
        results[pxd] = process_pxd(
            pxd, base_dir, msconvert_path, xtract_path,
            args.skip_msconvert, args.keep_mzml,
        )

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  ALL DONE in {elapsed/60:.0f} min")
    for pxd, ok in results.items():
        print(f"  {pxd}: {'OK' if ok else 'ERRORS'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

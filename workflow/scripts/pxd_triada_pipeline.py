#!/usr/bin/env python3
"""
pxd_triada_pipeline.py

1) Download vendor RAW files for a ProteomeXchange accession (PXD...)
2) Convert to mzML with MSConvert
3) Create triada structure:
   - triada/ms1   (MS1-only mzML)
   - triada/ms2   (MS2+ mzML)
   - triada/raw_empty (empty placeholders + manifest)

Dependencies:
  pip install pridepy ppx

MSConvert:
  Install ProteoWizard and ensure `msconvert` (or msconvert.exe) is in PATH,
  or pass its full path via --msconvert.

Example:
  python pxd_triada_pipeline.py PXD046034 --out D:/data/PXD046034 \
      --protocol ftp --centroid vendor \
      --msconvert "D:/MS/share/OpenMS/THIRDPARTY/pwiz-bin/msconvert.exe"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Multi-dot extensions MUST come before their single-dot prefixes so that
# matching works correctly (we test with str.endswith, longest first).
RAW_EXTS_ORDERED = [
    ".wiff2.scan",
    ".wiff.scan",
    ".wiff2",
    ".wiff",
    ".raw",
    ".d",
]

# Which primary extensions require a companion file
PAIR_MAP = {
    ".wiff":  ".wiff.scan",
    ".wiff2": ".wiff2.scan",
}

VALID_PROTOCOLS = {"ftp", "aspera", "globus", "s3"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_raw_ext(name: str) -> Optional[str]:
    """Return the raw extension of *name* (longest match first), or None."""
    lower = name.lower()
    for ext in RAW_EXTS_ORDERED:
        if lower.endswith(ext):
            return ext
    return None


def is_raw_candidate(p: Path) -> bool:
    """Check whether *p* looks like a vendor raw file/folder."""
    if p.is_dir():
        return p.suffix.lower() == ".d"
    return get_raw_ext(p.name) is not None


def is_companion(p: Path) -> bool:
    """True if the file is a WIFF/WIFF2 companion (.wiff.scan, .wiff2.scan)."""
    lower = p.name.lower()
    return lower.endswith(".wiff.scan") or lower.endswith(".wiff2.scan")


def safe_stem(raw_path: Path) -> str:
    """Extract the stem before the vendor extension."""
    ext = get_raw_ext(raw_path.name)
    if ext:
        return raw_path.name[: -len(ext)]
    return raw_path.stem


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def run_cmd(cmd: list[str], log_path: Optional[Path] = None) -> str:
    """Run a command; capture stdout+stderr; write to log; raise on failure."""
    print(f"  $ {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    out_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        out_lines.append(line)
        # Print progress dots for long-running commands
        if len(out_lines) % 100 == 0:
            print(f"    ... {len(out_lines)} lines of output ...", flush=True)
    rc = proc.wait()

    combined = "".join(out_lines)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(combined, encoding="utf-8")

    if rc != 0:
        tail = "".join(out_lines[-50:])
        raise RuntimeError(
            f"Command failed (rc={rc}): {' '.join(cmd)}\n--- tail ---\n{tail}"
        )
    return combined


def which_or_die(tool: str) -> str:
    p = shutil.which(tool)
    if not p:
        raise FileNotFoundError(f"Required tool not found in PATH: {tool}")
    return p


# ---------------------------------------------------------------------------
# Pair validation
# ---------------------------------------------------------------------------

def ensure_pairs(downloaded: list[Path]) -> list[str]:
    """Check that every .wiff/.wiff2 has its companion .scan file."""
    names_lower = {p.name.lower() for p in downloaded}
    problems: list[str] = []
    for p in downloaded:
        if p.is_dir():
            continue
        ext = get_raw_ext(p.name)
        if ext and ext in PAIR_MAP:
            stem_before_ext = p.name[: -len(ext)]
            companion_name = stem_before_ext + PAIR_MAP[ext]
            if companion_name.lower() not in names_lower:
                problems.append(
                    f"Missing pair for {p.name}: expected {companion_name}"
                )
    return problems


# ---------------------------------------------------------------------------
# Download backends
# ---------------------------------------------------------------------------

def download_with_pridepy(
    pxd: str, out_raw: Path, protocol: str, checksum: bool,
) -> None:
    """
    Download using pridepy Python API (download_all_raw_files method).
    This is the most reliable approach on Windows.
    """
    out_raw.mkdir(parents=True, exist_ok=True)

    if protocol not in VALID_PROTOCOLS:
        raise ValueError(
            f"Invalid protocol '{protocol}'. Choose from: {VALID_PROTOCOLS}"
        )

    log_dir = out_raw.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    from pridepy.pridepy import Files as PrideFiles  # type: ignore
    pf = PrideFiles()

    # First, list files for the log/manifest
    print(f"  [pridepy] Listing raw files for {pxd} ...")
    file_list = pf.get_all_raw_file_list(pxd)

    # Log the file list with sizes
    file_summary = []
    total_bytes = 0
    for entry in file_list:
        name = entry.get("fileName", "?") if isinstance(entry, dict) else str(entry)
        size = entry.get("fileSizeBytes", 0) if isinstance(entry, dict) else 0
        total_bytes += size
        file_summary.append({"fileName": name, "fileSizeBytes": size})

    (log_dir / f"{pxd}.pridepy_file_list.json").write_text(
        json.dumps(file_summary, indent=2), encoding="utf-8"
    )
    print(f"  [pridepy] Found {len(file_list)} raw files ({total_bytes/1e9:.1f} GB total).")

    # Use the batch download method
    print(f"  [pridepy] Starting download via {protocol} ...")
    print(f"  [pridepy] Output: {out_raw}")
    pf.download_all_raw_files(
        accession=pxd,
        output_folder=str(out_raw),
        skip_if_downloaded_already=True,
        protocol=protocol,
        aspera_maximum_bandwidth="500M",
        checksum_check=checksum,
    )
    print(f"  [pridepy] Download complete.")


def download_with_ppx(pxd: str, out_raw: Path) -> None:
    """Fallback using ppx (PRIDE/MassIVE)."""
    try:
        import ppx  # type: ignore
    except ImportError as e:
        raise RuntimeError("ppx not installed (pip install ppx)") from e

    out_raw.mkdir(parents=True, exist_ok=True)
    proj = ppx.find_project(pxd, local=str(out_raw))

    remote = proj.remote_files()
    remote_lower_map = {f.lower(): f for f in remote}

    wanted: set[str] = set()
    for f in remote:
        ext = get_raw_ext(f)
        if ext is not None:
            wanted.add(f)
            # Also grab the companion if this is a primary WIFF/WIFF2
            if ext in PAIR_MAP:
                stem = f[: -len(ext)]
                companion = stem + PAIR_MAP[ext]
                if companion.lower() in remote_lower_map:
                    wanted.add(remote_lower_map[companion.lower()])

    wanted_sorted = sorted(wanted)
    log_dir = out_raw.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{pxd}.ppx_selected_files.json").write_text(
        json.dumps(wanted_sorted, indent=2), encoding="utf-8"
    )

    print(f"  [ppx] Downloading {len(wanted_sorted)} files ...")
    for i, f in enumerate(wanted_sorted, 1):
        print(f"  [{i}/{len(wanted_sorted)}] {f}")
        proj.download(f)


# ---------------------------------------------------------------------------
# MSConvert
# ---------------------------------------------------------------------------

@dataclass
class ConvertOptions:
    msconvert: str
    gzip: bool
    centroid: str   # "none" | "vendor" | "cwt"
    bit_depth: int = 64


def build_msconvert_cmd(
    msconvert: str,
    infile: Path,
    outdir: Path,
    outfile: str,
    filters: list[str],
    gzip: bool,
    bit_depth: int = 64,
) -> list[str]:
    """
    Build an msconvert command line.
    Uses --outfile to control the output name directly.
    """
    cmd = [
        msconvert, str(infile),
        "--mzML", f"--{bit_depth}",
        "-o", str(outdir),
        "--outfile", outfile,
    ]
    if gzip:
        cmd.append("--gzip")
    for flt in filters:
        cmd += ["--filter", flt]
    return cmd


def convert_one(
    raw_path: Path,
    triada_ms1: Path,
    triada_ms2: Path,
    logs: Path,
    opt: ConvertOptions,
) -> dict:
    """Convert one raw file into MS1-only and MS2-only mzML in the triada dirs."""
    stem = safe_stem(raw_path)

    # Build centroiding filters (must be FIRST per ProteoWizard docs)
    prefix_filters: list[str] = []
    if opt.centroid == "vendor":
        prefix_filters = ["peakPicking vendor msLevel=1-", "metadataFixer"]
    elif opt.centroid == "cwt":
        prefix_filters = ["peakPicking cwt msLevel=1-", "metadataFixer"]
    elif opt.centroid == "none":
        pass
    else:
        raise ValueError(f"centroid must be none|vendor|cwt, got '{opt.centroid}'")

    triada_ms1.mkdir(parents=True, exist_ok=True)
    triada_ms2.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    suffix = ".mzML.gz" if opt.gzip else ".mzML"
    ms1_outfile = f"{stem}.ms1{suffix}"
    ms2_outfile = f"{stem}.ms2{suffix}"

    # --- MS1-only conversion ---
    cmd1 = build_msconvert_cmd(
        opt.msconvert, raw_path, triada_ms1, ms1_outfile,
        filters=prefix_filters + ["msLevel 1"],
        gzip=opt.gzip,
        bit_depth=opt.bit_depth,
    )
    run_cmd(cmd1, log_path=logs / f"{stem}.ms1.msconvert.log")

    ms1_final = triada_ms1 / ms1_outfile
    if not ms1_final.exists() or ms1_final.stat().st_size == 0:
        raise RuntimeError(
            f"MS1 conversion produced no/empty output: {ms1_final}\n"
            f"Check log: {logs / f'{stem}.ms1.msconvert.log'}"
        )

    # --- MS2+ conversion ---
    cmd2 = build_msconvert_cmd(
        opt.msconvert, raw_path, triada_ms2, ms2_outfile,
        filters=prefix_filters + ["msLevel 2-"],
        gzip=opt.gzip,
        bit_depth=opt.bit_depth,
    )
    run_cmd(cmd2, log_path=logs / f"{stem}.ms2.msconvert.log")

    ms2_final = triada_ms2 / ms2_outfile
    if not ms2_final.exists() or ms2_final.stat().st_size == 0:
        raise RuntimeError(
            f"MS2 conversion produced no/empty output: {ms2_final}\n"
            f"Check log: {logs / f'{stem}.ms2.msconvert.log'}"
        )

    return {
        "input": str(raw_path),
        "ms1": str(ms1_final),
        "ms2": str(ms2_final),
        "ms1_size": ms1_final.stat().st_size,
        "ms2_size": ms2_final.stat().st_size,
        "ms1_sha256": sha256_file(ms1_final),
        "ms2_sha256": sha256_file(ms2_final),
    }


# ---------------------------------------------------------------------------
# raw_empty placeholders
# ---------------------------------------------------------------------------

def create_raw_empty_placeholders(raw_files: list[Path], raw_empty_dir: Path) -> None:
    raw_empty_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for rf in raw_files:
        placeholder = raw_empty_dir / (rf.name + ".empty")
        placeholder.write_text("", encoding="utf-8")
        manifest.append({"raw": str(rf), "placeholder": str(placeholder)})
    (raw_empty_dir / "README.txt").write_text(
        "raw_empty/ contains placeholder files to satisfy downstream tooling\n"
        "that expects a RAW presence. These are NOT real vendor files.\n",
        encoding="utf-8",
    )
    (raw_empty_dir / "raw_empty_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Download PXD raw files and convert to MS1/MS2 mzML triada."
    )
    ap.add_argument("pxd", help="ProteomeXchange accession, e.g. PXD046034")
    ap.add_argument("--out", required=True, help="Output root folder")
    ap.add_argument(
        "--protocol", default="ftp",
        choices=sorted(VALID_PROTOCOLS),
        help="pridepy download protocol (default: ftp)",
    )
    ap.add_argument("--no-checksum", action="store_true",
                    help="Disable pridepy checksum check")
    ap.add_argument("--download-only", action="store_true",
                    help="Only download; skip MSConvert")
    ap.add_argument("--convert-only", action="store_true",
                    help="Skip download; convert existing raw/ files")
    ap.add_argument("--msconvert", default="msconvert",
                    help="Path to msconvert binary (default: msconvert)")
    ap.add_argument("--gzip", action="store_true",
                    help="Gzip mzML output")
    ap.add_argument("--centroid", default="none",
                    choices=["none", "vendor", "cwt"],
                    help="Centroiding mode (default: none)")
    ap.add_argument("--bit-depth", type=int, default=64, choices=[32, 64],
                    help="Binary encoding precision (default: 64)")
    args = ap.parse_args()

    pxd = args.pxd.strip()
    root = Path(args.out).resolve()
    raw_dir = root / "raw"
    triada = root / "triada"
    triada_ms1 = triada / "ms1"
    triada_ms2 = triada / "ms2"
    raw_empty = triada / "raw_empty"
    logs = root / "logs"
    root.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"{'='*60}")
    print(f"PXD Triada Pipeline")
    print(f"  Accession : {pxd}")
    print(f"  Output    : {root}")
    print(f"  Protocol  : {args.protocol}")
    print(f"{'='*60}")

    # ------------------------------------------------------------------
    # Step 1: Download
    # ------------------------------------------------------------------
    used_downloader = None
    if not args.convert_only:
        print(f"\n[STEP 1] Downloading {pxd} into {raw_dir} ...")
        try:
            download_with_pridepy(
                pxd, raw_dir,
                protocol=args.protocol,
                checksum=not args.no_checksum,
            )
            used_downloader = "pridepy"
        except Exception as e_pridepy:
            print(f"[WARN] pridepy failed: {e_pridepy}")
            print("[INFO] Falling back to ppx ...")
            try:
                download_with_ppx(pxd, raw_dir)
                used_downloader = "ppx"
            except Exception as e_ppx:
                raise RuntimeError(
                    f"Download failed with both backends.\n"
                    f"  pridepy: {e_pridepy}\n"
                    f"  ppx:    {e_ppx}"
                ) from e_ppx
    else:
        if not raw_dir.exists():
            raise FileNotFoundError(
                f"--convert-only but raw dir does not exist: {raw_dir}"
            )
        used_downloader = "skipped (--convert-only)"

    # ------------------------------------------------------------------
    # Step 2: Collect raw candidates
    # ------------------------------------------------------------------
    print(f"\n[STEP 2] Scanning for raw files in {raw_dir} ...")
    raw_files: list[Path] = []
    for p in sorted(raw_dir.rglob("*")):
        if is_raw_candidate(p):
            raw_files.append(p)

    pair_problems = ensure_pairs(raw_files)
    download_report = {
        "pxd": pxd,
        "downloader": used_downloader,
        "raw_count": len(raw_files),
        "raw_files": [str(p) for p in raw_files],
        "pair_problems": pair_problems,
    }
    report_path = root / "download_report.json"
    report_path.write_text(
        json.dumps(download_report, indent=2), encoding="utf-8"
    )

    if pair_problems:
        for prob in pair_problems:
            print(f"  [WARN] {prob}")

    print(f"  Found {len(raw_files)} raw items (via {used_downloader}).")
    print(f"  Report: {report_path}")

    # ------------------------------------------------------------------
    # Step 3: raw_empty placeholders
    # ------------------------------------------------------------------
    print(f"\n[STEP 3] Creating raw_empty placeholders ...")
    create_raw_empty_placeholders(raw_files, raw_empty)
    print(f"  Done: {raw_empty}")

    if args.download_only:
        elapsed = time.time() - t0
        print(f"\n[OK] Download-only mode. Elapsed: {elapsed:.0f}s")
        return

    # ------------------------------------------------------------------
    # Step 4: MSConvert -> MS1 / MS2
    # ------------------------------------------------------------------
    print(f"\n[STEP 4] Converting raw -> mzML (MS1 + MS2) ...")
    msconvert_path = args.msconvert
    if os.path.sep not in msconvert_path and "/" not in msconvert_path and "\\" not in msconvert_path:
        msconvert_path = which_or_die(msconvert_path)
    print(f"  MSConvert: {msconvert_path}")
    print(f"  Centroid:  {args.centroid}")
    print(f"  Gzip:      {args.gzip}")
    print(f"  Bit depth: {args.bit_depth}")

    opt = ConvertOptions(
        msconvert=msconvert_path,
        gzip=args.gzip,
        centroid=args.centroid,
        bit_depth=args.bit_depth,
    )

    # Filter out companions — only convert primary raw files
    primary_raw = [rf for rf in raw_files if not is_companion(rf)]
    print(f"  Primary raw files to convert: {len(primary_raw)}")

    conversions: list[dict] = []
    errors: list[dict] = []

    for i, rf in enumerate(primary_raw, 1):
        print(f"\n  [{i}/{len(primary_raw)}] Converting {rf.name} ...")
        try:
            record = convert_one(rf, triada_ms1, triada_ms2, logs, opt)
            conversions.append(record)
            print(f"    MS1: {record['ms1_size']:,} bytes -> {record['ms1']}")
            print(f"    MS2: {record['ms2_size']:,} bytes -> {record['ms2']}")
        except Exception as e:
            err = {"input": str(rf), "error": str(e)}
            errors.append(err)
            print(f"    [ERROR] {e}")

    manifest = {
        "pxd": pxd,
        "conversions": conversions,
        "errors": errors,
        "total_converted": len(conversions),
        "total_errors": len(errors),
    }
    manifest_path = root / "conversion_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    if errors:
        print(f"[WARN] {len(errors)} file(s) failed conversion.")
    print(
        f"[OK] Converted {len(conversions)}/{len(primary_raw)} raw runs "
        f"into triada/ under {triada}"
    )
    print(f"  Manifest: {manifest_path}")
    print(f"  Elapsed:  {elapsed:.0f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

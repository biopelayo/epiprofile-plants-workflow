# rules/ms1_ms2.smk
# mzML -> .ms1 + .ms2 text extraction via xtract_xml.exe (pXtract).
#
# EpiProfile requires .ms1 and .ms2 TEXT files (not mzML).
# xtract_xml.exe reads centroided mzML and produces:
#   - sample.ms1            (MS1 scans)
#   - sample.HCD.FTMS.ms2   (MS2 scans, needs renaming to sample.ms2)
#
# Config keys:
#   base_dir            - root data directory for this PXD
#   xtract_xml_path     - path to xtract_xml.exe (Windows) or wrapper
#   mzml_dir            - subdir with centroided mzML (default: "mzML")
#   ms1_dir             - output subdir for .ms1 (default: "MS1")
#   ms2_dir             - output subdir for .ms2 (default: "MS2")
#
# NOTE: xtract_xml.exe is a Windows-only binary (from pFind/EpiProfile).
#       On Linux, you would need Wine or a Docker wrapper.

import os


rule extract_ms1_ms2_text:
    """
    Extract MS1/MS2 text files from centroided mzML using xtract_xml.exe.

    Pipeline:
      mzML -> xtract_xml -ms -> .ms1 + .HCD.FTMS.ms2 -> rename -> organize
      Also creates empty .raw placeholders in RawData/ for EpiProfile.
    """
    input:
        manifest=os.path.join(config["base_dir"], "conversion_manifest.json"),
    output:
        ms1_dir=directory(os.path.join(config["base_dir"], config.get("ms1_dir", "MS1"))),
        ms2_dir=directory(os.path.join(config["base_dir"], config.get("ms2_dir", "MS2"))),
        raw_data_dir=directory(os.path.join(config["base_dir"], "RawData")),
    params:
        xtract=config.get("xtract_xml_path", "xtract_xml.exe"),
        mzml_dir=os.path.join(config["base_dir"], config.get("mzml_dir", "mzML")),
    log:
        os.path.join(config["base_dir"], "logs", "ms1_ms2_extract.log"),
    run:
        import pathlib, subprocess, time

        mzml_dir = pathlib.Path(params.mzml_dir)
        ms1_out = pathlib.Path(output.ms1_dir)
        ms2_out = pathlib.Path(output.ms2_dir)
        raw_data_out = pathlib.Path(output.raw_data_dir)

        # Work dir for xtract output (flat, then we move files out)
        work_dir = pathlib.Path(config["base_dir"]) / "MS1_MS2_tmp"
        work_dir.mkdir(parents=True, exist_ok=True)
        ms1_out.mkdir(parents=True, exist_ok=True)
        ms2_out.mkdir(parents=True, exist_ok=True)
        raw_data_out.mkdir(parents=True, exist_ok=True)

        xtract = params.xtract
        xtract_cwd = str(pathlib.Path(xtract).parent)
        log_lines = []
        errors = []

        mzml_files = sorted(mzml_dir.glob("*.mzML"))
        for i, mzml in enumerate(mzml_files, 1):
            stem = mzml.stem
            ms1_check = work_dir / f"{stem}.ms1"
            if ms1_check.exists() and ms1_check.stat().st_size > 0:
                log_lines.append(f"[{i}/{len(mzml_files)}] {stem} - skip (exists)")
                continue

            t0 = time.time()
            try:
                result = subprocess.run(
                    [xtract, "-ms", "-o", str(work_dir), str(mzml)],
                    capture_output=True, text=True, timeout=300,
                    cwd=xtract_cwd,
                )
                elapsed = time.time() - t0
                if ms1_check.exists() and ms1_check.stat().st_size > 0:
                    log_lines.append(f"[{i}/{len(mzml_files)}] {stem} OK ({elapsed:.0f}s)")
                else:
                    errors.append(stem)
                    log_lines.append(f"[{i}/{len(mzml_files)}] {stem} FAIL")
            except subprocess.TimeoutExpired:
                errors.append(stem)
                log_lines.append(f"[{i}/{len(mzml_files)}] {stem} TIMEOUT")
            except Exception as e:
                errors.append(stem)
                log_lines.append(f"[{i}/{len(mzml_files)}] {stem} ERROR: {e}")

        # Rename HCD.FTMS.ms2 -> .ms2
        for f in work_dir.iterdir():
            if f.suffix == ".ms2" and f.name.count(".") > 1:
                parts = f.name.split(".")
                f.rename(work_dir / f"{parts[0]}.ms2")

        # Move .ms1 -> MS1/, .ms2 -> MS2/, create empty .raw -> RawData/
        import shutil
        for ms1 in sorted(work_dir.glob("*.ms1")):
            shutil.move(str(ms1), str(ms1_out / ms1.name))
        for ms2 in sorted(work_dir.glob("*.ms2")):
            shutil.move(str(ms2), str(ms2_out / ms2.name))
        for ms1 in sorted(ms1_out.glob("*.ms1")):
            (raw_data_out / f"{ms1.stem}.raw").touch()

        # Cleanup temp files
        for pattern in ["*.rawInfo", "*.xtract"]:
            for f in work_dir.glob(pattern):
                f.unlink()

        # Write log
        log_lines.append(f"\nExtracted: {len(mzml_files) - len(errors)}/{len(mzml_files)}")
        if errors:
            log_lines.append(f"Errors: {errors}")
        pathlib.Path(log[0]).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(log[0]).write_text("\n".join(log_lines), encoding="utf-8")

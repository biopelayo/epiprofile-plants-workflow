# rules/ms1_ms2.smk
# Placeholder for mzML → MS1/MS2 text extraction (for EpiProfile_PLANTS).
#
# The triada conversion (mzml.smk) already produces MS1-only and MS2-only
# mzML files.  This rule handles the OPTIONAL further extraction into the
# legacy MS1/MS2 text format that EpiProfile_PLANTS may require
# (via xtract_xml, Raw2MS, or similar tools).
#
# If your EpiProfile_PLANTS version reads mzML directly, you can skip this
# step by not requesting the ms1_ms2 outputs in rule all.

import os


rule extract_ms1_ms2_text:
    """
    Extract MS1/MS2 text files from the triada mzML.
    This is a placeholder — implement when xtract_xml / Raw2MS is available.
    """
    input:
        manifest=os.path.join(config["base_dir"], "conversion_manifest.json"),
    output:
        ms1_dir=directory(os.path.join(config["base_dir"], config.get("ms1_dir", "MS1"))),
        ms2_dir=directory(os.path.join(config["base_dir"], config.get("ms2_dir", "MS2"))),
    log:
        os.path.join(config["base_dir"], "logs", "ms1_ms2_extract.log"),
    run:
        import json, pathlib

        manifest_path = pathlib.Path(input.manifest)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        ms1_out = pathlib.Path(output.ms1_dir)
        ms2_out = pathlib.Path(output.ms2_dir)
        ms1_out.mkdir(parents=True, exist_ok=True)
        ms2_out.mkdir(parents=True, exist_ok=True)

        log_lines = []
        for entry in manifest.get("conversions", []):
            ms1_src = pathlib.Path(entry["ms1"])
            ms2_src = pathlib.Path(entry["ms2"])

            if ms1_src.exists():
                # For now, symlink the triada mzML into the MS1/MS2 dirs.
                # Replace with xtract_xml call when available.
                dest1 = ms1_out / ms1_src.name
                if not dest1.exists():
                    try:
                        dest1.symlink_to(ms1_src.resolve())
                    except OSError:
                        # Windows may not support symlinks without admin;
                        # fall back to copy
                        import shutil
                        shutil.copy2(str(ms1_src), str(dest1))
                log_lines.append(f"MS1: {ms1_src} -> {dest1}")

            if ms2_src.exists():
                dest2 = ms2_out / ms2_src.name
                if not dest2.exists():
                    try:
                        dest2.symlink_to(ms2_src.resolve())
                    except OSError:
                        import shutil
                        shutil.copy2(str(ms2_src), str(dest2))
                log_lines.append(f"MS2: {ms2_src} -> {dest2}")

        pathlib.Path(log[0]).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(log[0]).write_text("\n".join(log_lines), encoding="utf-8")

# rules/mzml.smk
# Convert vendor RAW → mzML (MS1-only + MS2-only) using MSConvert.
#
# Expects these config keys:
#   base_dir, project_id,
#   msconvert_path (optional, default "msconvert"),
#   msconvert_centroid (optional, default "none": none|vendor|cwt),
#   msconvert_gzip (optional, default false),
#   msconvert_bit_depth (optional, default 64)

import os


rule convert_raw_to_mzml:
    """
    Convert all downloaded RAW files into the triada layout:
      triada/ms1/  (MS1-only mzML)
      triada/ms2/  (MS2-only mzML)
      triada/raw_empty/  (placeholders)

    Requires download_report.json to exist (i.e. download must finish first).
    Produces conversion_manifest.json.
    """
    input:
        download_report=os.path.join(config["base_dir"], "download_report.json"),
    output:
        manifest=os.path.join(config["base_dir"], "conversion_manifest.json"),
    params:
        pxd=config.get("project_id", ""),
        out_root=config["base_dir"],
        msconvert=config.get("msconvert_path", "msconvert"),
        centroid=config.get("msconvert_centroid", "none"),
        gzip="--gzip" if config.get("msconvert_gzip", False) else "",
        bit_depth=config.get("msconvert_bit_depth", 64),
    log:
        os.path.join(config["base_dir"], "logs", "msconvert.log"),
    shell:
        r"""
        python workflow/scripts/pxd_triada_pipeline.py \
            {params.pxd} \
            --out {params.out_root} \
            --convert-only \
            --msconvert {params.msconvert} \
            --centroid {params.centroid} \
            --bit-depth {params.bit_depth} \
            {params.gzip} \
            2>&1 | tee {log}
        """

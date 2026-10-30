# rules/mzml.smk
# Convert vendor RAW -> centroided mzML using MSConvert.
#
# Produces ONE full centroided mzML per raw file (MS1+MS2 combined, no level
# split) in <base_dir>/<mzml_dir>/.  That is exactly what rules/ms1_ms2.smk
# (xtract_xml.exe) reads next.
#
# Expects these config keys:
#   base_dir, project_id,
#   mzml_dir (optional, default "mzML"),
#   msconvert_path (optional, default "msconvert"),
#   msconvert_centroid (optional, default "vendor": none|vendor|cwt),
#   msconvert_gzip (optional, default false),
#   msconvert_bit_depth (optional, default 64)

import os


rule convert_raw_to_mzml:
    """
    Convert all downloaded RAW files into full centroided mzML:
      <base_dir>/<mzml_dir>/<sample>.mzML

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
        mzml_dir=config.get("mzml_dir", "mzML"),
        msconvert=config.get("msconvert_path", "msconvert"),
        centroid=config.get("msconvert_centroid", "vendor"),
        gzip="--gzip" if config.get("msconvert_gzip", False) else "",
        bit_depth=config.get("msconvert_bit_depth", 64),
    log:
        os.path.join(config["base_dir"], "logs", "msconvert.log"),
    shell:
        r"""
        mkdir -p "$(dirname {log})"
        python workflow/scripts/pxd_triada_pipeline.py \
            {params.pxd} \
            --out "{params.out_root}" \
            --convert-only \
            --layout full \
            --mzml-dir "{params.mzml_dir}" \
            --msconvert "{params.msconvert}" \
            --centroid {params.centroid} \
            --bit-depth {params.bit_depth} \
            {params.gzip} \
            2>&1 | tee {log}
        """

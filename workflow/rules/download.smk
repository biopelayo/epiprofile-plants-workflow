# rules/download.smk
# Download vendor RAW files from ProteomeXchange (PRIDE / MassIVE).
#
# Expects these config keys:
#   base_dir, project_id, download_protocol (optional, default ftp),
#   download_checksum (optional, default true)

import os


rule download_pxd:
    """
    Download raw vendor files for a PXD accession using pridepy (preferred)
    or ppx as fallback.  Produces a download_report.json manifest.
    """
    output:
        report=os.path.join(config["base_dir"], "download_report.json"),
    params:
        pxd=config.get("project_id", ""),
        out_root=config["base_dir"],
        protocol=config.get("download_protocol", "ftp"),
        checksum="--no-checksum" if not config.get("download_checksum", True) else "",
    log:
        os.path.join(config["base_dir"], "logs", "download.log"),
    shell:
        r"""
        python workflow/scripts/pxd_triada_pipeline.py \
            {params.pxd} \
            --out {params.out_root} \
            --protocol {params.protocol} \
            {params.checksum} \
            --download-only \
            2>&1 | tee {log}
        """

# ONTOGENY_DEMO

Internal Arabidopsis rosette ontogeny demo dataset used to validate the
EpiProfile_PLANTS workflow before running the full PXD datasets.

## Status

Placeholder — the actual demo dataset (BOT/FLOR/SEN conditions) is not
yet included in this repository. The configuration template is at
`config/config_ontogeny_demo.yml` and needs its `base_dir` path adjusted
to your local data directory.

## Usage

```bash
# 1. Install the Snakemake environment
mamba env create -f envs/snakemake.yml
mamba activate epiprofile-plants-workflow

# 2. Run the workflow with the demo config
snakemake -s workflow/Snakefile --configfile config/config_ontogeny_demo.yml

# 3. Or run the standalone pipeline scripts directly:
python workflow/scripts/pxd_triada_pipeline.py ONTOGENY_DEMO --out /path/to/demo --download-only
python workflow/scripts/convert_and_extract.py --pxd ONTOGENY_DEMO --base /path/to/data
```

## Related files

- `config/config_ontogeny_demo.yml` — dataset configuration (paths, MSConvert, xtract_xml)
- `workflow/Snakefile` — uses this config by default
- `envs/snakemake.yml` — Conda environment specification

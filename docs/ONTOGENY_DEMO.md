# ONTONOGENY_DEMO

This folder collects documentation and helper files for the internal
Arabidopsis rosette ontogeny demo dataset used to validate the
EpiProfile_PLANTS workflow.

For now, running:

```bash
mamba env create -f envs/snakemake.yml
mamba activate epiprofile-plants-workflow
snakemake -s workflow/Snakefile

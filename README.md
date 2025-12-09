# EpiProfile_PLANTS workflow

Reproducible workflow from **WIFF/RAW → mzML → MS1/MS2 → EpiProfile_PLANTS → hPTM matrices**  
for plant histone proteomics.

This repository complements the MATLAB code in  
[`epiprofile-plants`](https://github.com/biopelayo/epiprofile-plants) by providing
a Docker/Snakemake pipeline that:

1. Organises **ProteomeXchange (PXD) datasets** on disk in a consistent way.
2. Converts vendor files (e.g. SCIEX WIFF/WIFFSCAN) to `mzML`.
3. Extracts **MS1/MS2** text files required by EpiProfile 2.0 / EpiProfile_PLANTS.
4. Runs EpiProfile_PLANTS with species-specific layouts (Arabidopsis, Marchantia, Chlamydomonas).
5. Produces **analysis-ready matrices** of histone PTM areas for downstream R/Python analysis.

> Status: work in progress as part of a PhD thesis on **H3K79 in Arabidopsis**.
> The goal is a fully reproducible, FAIR-compliant workflow that can be reused on public datasets
> and new plant experiments.

---

## 1. Scope and design

The workflow is intentionally:

- **Dataset-agnostic** – it should work with any compatible PXD (or local dataset)
  once paths and layout files are specified.
- **Tool-agnostic on the MS side** – conversion and extraction are wrapped in Docker,
  so the host system only needs Docker (or Apptainer/Singularity).
- **Modular** – each major step (download, mzML, MS1/MS2, EpiProfile_PLANTS, post-processing)
  is a separate Snakemake rule.
- **Traceable** – every step leaves logs and small manifest files for later audit.

Typical use cases:

- Reanalysis of public datasets such as **PXD010102** and **PXD046034**.
- Internal datasets for **Arabidopsis rosette ontogeny** (BGSR; YNG/BOT/FLOR/SEN).
- Small demonstration sets such as **ONTOGENY_DEMO** (BOT_8, FLOR_3 inj1/inj2, FLOR_6, SEN_6).

---

## 2. High-level workflow

Conceptually the pipeline follows these steps:

1. **Dataset preparation**
   - (Optional) Download from PRIDE / ProteomeXchange using R (e.g. `rpridemetadb`) or Python.
   - Organise files into a standard directory tree:
     `raw_wiff/`, `mzML/`, `MS1_MS2/`, `EpiProfile_output/`, `phenodata/`, etc.

2. **Vendor → mzML**
   - Use **ProteoWizard `msconvert`** in a Docker container.
   - Apply standard options for histone proteomics, e.g.:
     - 64-bit
     - `zlib` compression
     - vendor peak picking
   - Output to `mzML/` (profile and/or centroid, depending on the project).

3. **mzML → MS1/MS2**
   - Use `xtract_xml` / `Raw2MS`-like tools to generate:
     - `<sample>.MS1`
     - `<sample>.MS2`
   - Save to `MS1_MS2/MS1/` and `MS1_MS2/MS2/`.

4. **EpiProfile_PLANTS quantification**
   - Select the appropriate **species layout** and `init_histone0_*` file
     (e.g. Arabidopsis, Marchantia, Chlamydomonas, or “core” panel).
   - Run EpiProfile_PLANTS to obtain histone peptide/PTM areas per sample.
   - Store outputs under `EpiProfile_output/`.

5. **Post-processing**
   - Collect EpiProfile output files into:
     - a **long table** (one row per peptide/PTM/sample),
     - and **wide matrices** (peptides/PTMs × samples).
   - Generate small QC summaries to check sample completeness, NA/zero structure, etc.
   - These matrices are then used in R/Python (e.g. for qsmooth, ComBat, limma).

Snakemake orchestrates these steps, so a single command can rebuild the entire pipeline.

---

## 3. Repository structure (planned)

The folder layout of this repository is designed to be explicit and readable:

```text
epiprofile-plants-workflow/
├── workflow/
│   ├── Snakefile              # main Snakemake entry point
│   ├── rules/                 # modular rule files
│   │   ├── download.smk       # (optional) PRIDE / PXD download logic
│   │   ├── mzml.smk           # WIFF/RAW → mzML via Docker
│   │   ├── ms1_ms2.smk        # mzML → MS1/MS2
│   │   ├── epiprofile.smk     # EpiProfile_PLANTS calls
│   │   └── postprocess.smk    # matrices & QC summaries
│   └── scripts/               # helper scripts (Python/R/bash)
│
├── config/
│   ├── config_pxd010102.yml   # example config for PXD010102
│   ├── config_pxd046034.yml   # example config for PXD046034
│   └── config_ontogeny_demo.yml
│
├── envs/                      # Conda environment definitions
│   ├── snakemake.yml
│   ├── msconvert.yml
│   └── r_postprocess.yml
│
├── docker/                    # Dockerfiles for vendor tools and helpers
│   └── msconvert.Dockerfile
│
├── example-projects/
│   ├── ONTOGENY_DEMO/         # minimal BOT/FLOR/SEN dataset
│   └── PXD046034_demo/        # small subset of PXD046034
│
└── docs/
    ├── 01_overview.md
    ├── 02_setup.md
    └── 03_examples.md

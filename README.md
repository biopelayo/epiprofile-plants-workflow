# EpiProfile_PLANTS Workflow

Preprocessing pipeline for **Arabidopsis histone PTM
quantification** from Thermo `.raw` files deposited in PRIDE/ProteomeXchange.

<img width="1024" height="572" alt="image" src="https://github.com/user-attachments/assets/b77a8d73-035a-4577-9b06-d253865d0782" />

This repository handles **data acquisition and format conversion** — from raw
mass-spectrometry files to the `.ms1`/`.ms2` text files that EpiProfile needs.
The actual histone PTM quantification is done by
[**epiprofile-plants**](https://github.com/biopelayo/epiprofile-plants), a
MATLAB extension of EpiProfile 2.0 with plant-specific histone peptide catalogs,
species layouts (Arabidopsis, Marchantia, Chlamydomonas), and QC utilities.

Part of a PhD thesis on **H3K79 in *Arabidopsis thaliana***.

---

## How the two repositories work together

| Repository | Role | Language |
|------------|------|----------|
| **epiprofile-plants-workflow** (this repo) | Download `.raw` from PRIDE, convert to `.mzML`, extract `.ms1`/`.ms2` text | Python + Snakemake |
| [**epiprofile-plants**](https://github.com/biopelayo/epiprofile-plants) | Quantify histone PTMs from `.ms1`/`.ms2` files, produce area matrices | MATLAB |

**Typical workflow:**

```
this repo                                  epiprofile-plants
--------                                   -----------------
.raw (PRIDE)                               .ms1 + .ms2 + .raw (empty)
  |  download (pridepy)                       |
  v                                           |  EpiProfile_PLANTS.m
.raw (local)                                  v
  |  MSConvert (vendor centroiding)        hPTM area matrices (CSV)
  v
.mzML (centroided, full MS1+MS2)
  |  xtract_xml.exe (pXtract)
  v
.ms1 + .ms2 (text) ---------------------->
```

---

## Pipeline overview

### Steps

1. **Download** `.raw` files from PRIDE via `pridepy` (FTP).
2. **MSConvert**: `.raw` to centroided `.mzML`
   (filters: `peakPicking vendor msLevel=1-`, `metadataFixer`).
3. **xtract_xml.exe** (pXtract): `.mzML` to `.ms1` + `.HCD.FTMS.ms2` text.
4. **Rename**: `.HCD.FTMS.ms2` to `.ms2`.
5. **Organize**: create `MS1/`, `MS2/`, `RawData/` (empty `.raw` placeholders).
6. **Batch** (optional): group by experimental condition into `batches/{group}/`.
7. **Quantify** with [epiprofile-plants](https://github.com/biopelayo/epiprofile-plants).

---

## Repository structure

```text
epiprofile-plants-workflow/
  workflow/
    Snakefile                      # Snakemake entry point (includes 3 rule files)
    rules/
      download.smk                 # Rule: PRIDE download via pridepy
      mzml.smk                     # Rule: raw -> centroided mzML via MSConvert
      ms1_ms2.smk                  # Rule: mzML -> .ms1/.ms2 text via xtract_xml
    scripts/
      pxd_triada_pipeline.py       # Standalone: download + MSConvert
      convert_and_extract.py       # Standalone: raw -> mzML -> xtract_xml -> organized
  config/
    config_pxd046034.yml           # PXD046034 dataset config
    config_pxd046788.yml           # PXD046788 dataset config
    config_pxd014739.yml           # PXD014739 dataset config
    config_ontogeny_demo.yml       # Demo/template config
  envs/
    snakemake.yml                  # Conda environment (Python 3.11, Snakemake 7-9)
  docs/
    PIPELINE_RUN_LOG.md            # Detailed execution log (all 3 PXDs)
    TUTORIAL.md                    # Step-by-step guide
    ONTOGENY_DEMO.md               # Internal demo dataset docs
  deploy_server.sh                 # Linux server deployment (Docker MSConvert)
  README.md
  LICENSE                          # GPLv2
```

---

## Snakemake workflow

The Snakefile chains three rules:

```
download.smk          mzml.smk              ms1_ms2.smk
------------          --------              -----------
download_pxd    ->    convert_raw_to_mzml   ->    extract_ms1_ms2_text
(pridepy FTP)         (MSConvert)                 (xtract_xml.exe)
     |                     |                           |
     v                     v                           v
download_report.json  conversion_manifest.json    MS1/ MS2/ RawData/
```

Each rule reads its settings from a YAML config file. Run with:

```bash
# Using the default config (config/config_ontogeny_demo.yml):
snakemake -s workflow/Snakefile

# Using a specific dataset config:
snakemake -s workflow/Snakefile --configfile config/config_pxd046034.yml
```

### Config keys (per-dataset YAML)

| Key | Description | Example |
|-----|-------------|---------|
| `project_id` | PXD accession | `"PXD046034"` |
| `base_dir` | Root data directory | `"D:/epiprofile_data/PXD046034"` |
| `msconvert_path` | Path to MSConvert binary | `"D:/MS/.../msconvert.exe"` |
| `msconvert_centroid` | Centroiding mode | `"vendor"` |
| `xtract_xml_path` | Path to xtract_xml.exe | `"D:/EpiProfile2.1_.../xtract_xml.exe"` |
| `download_protocol` | PRIDE download method | `"ftp"` |

---

## Standalone scripts (without Snakemake)

The pipeline can also be run directly with Python scripts:

```bash
# 1. Download a dataset from PRIDE
python workflow/scripts/pxd_triada_pipeline.py PXD046034 \
    --out D:/epiprofile_data/PXD046034 --protocol ftp --download-only

# 2. Convert raw -> mzML -> .ms1 + .ms2 (all-in-one)
python workflow/scripts/convert_and_extract.py --pxd PXD046034
```

### Script descriptions

| Script | Purpose | Usage |
|--------|---------|-------|
| `pxd_triada_pipeline.py` | Download `.raw` from PRIDE + MSConvert to mzML | `--download-only` or `--convert-only` |
| `convert_and_extract.py` | Full pipeline: raw → mzML → xtract_xml → .ms1/.ms2 → organize | `--pxd PXD046034 [--base DIR]` |

---

## Datasets processed

| PXD | Description | Instrument | Files | Raw size |
|-----|-------------|------------|-------|----------|
| PXD046034 | Histone chaperone mutants (fas/nap) | Orbitrap Fusion Lumos | 48 | 32 GB |
| PXD046788 | HDAC inhibitors (TSA/NaB) in calli | Orbitrap Fusion Lumos | 58 | 48 GB |
| PXD014739 | Histone acetylation profiling | LTQ Orbitrap Elite | 114 | 43 GB |

**Total**: 220 raw files, 123 GB. All downloaded, converted, and extracted.

See [docs/PIPELINE_RUN_LOG.md](docs/PIPELINE_RUN_LOG.md) for full execution details.

---

## Data organization

After running the pipeline, each dataset has:

```
D:/epiprofile_data/PXD046034/
  MS1_MS2/    48 x sample.ms1 + 48 x sample.ms2
  RawData/    48 x sample.raw (empty placeholders)
```

Optionally organized by condition with hard-linked batch folders:

```
D:/epiprofile_data/organized/PXD046034/
  MS1/        all .ms1 files
  MS2/        all .ms2 files
  RawData/    all empty .raw placeholders
  batches/
    3905_wt/      MS1/ MS2/ RawData/  (6 samples)
    3905_fas/     MS1/ MS2/ RawData/  (6 samples)
    ...
```

---

## Running EpiProfile (next step)

After this workflow produces `.ms1` + `.ms2` files, use
[**epiprofile-plants**](https://github.com/biopelayo/epiprofile-plants) to
quantify histone PTMs in MATLAB.

### paras.txt configuration

Edit `paras.txt` in the EpiProfile directory to point to your data:

```matlab
[EpiProfile]
% the datapath of raw files
raw_path=D:\epiprofile_data\PXD046788\MS1_MS2\RawData

% 1: Arabidopsis thaliana (in epiprofile-plants)
norganism=1

% 1: histone_LFQ, 2: histone_SILAC, 3: histone_13CD3, 4: histone_15N
nsource=1

% if histone_LFQ: 0=light only
nsubtype=0
```

Change `raw_path` to point to the `RawData/` folder of the PXD or batch you
want to analyze. EpiProfile reads `.ms1`/`.ms2` from the parent of `raw_path`.

See the [epiprofile-plants README](https://github.com/biopelayo/epiprofile-plants)
for full setup, species bundles, and the hDP → hPF → hPTM output model.

---

## Requirements

- **Windows 10/11** (MSConvert and xtract_xml are Windows binaries)
- **Python 3.10+** with `pridepy`, `ppx` (`pip install pridepy ppx`)
- **MSConvert** (ProteoWizard, via OpenMS or standalone install)
- **xtract_xml.exe** (bundled with EpiProfile 2.1 / pXtract)
- **Snakemake 7+** (optional, for rule-based execution)
- ~200 GB free disk space for all 3 datasets

For Linux deployment: MSConvert runs via Docker
(`chambm/pwiz-skyline-i-agree-to-the-vendor-licenses`).
xtract_xml requires Windows or Wine. See `deploy_server.sh`.

---

## Known issues

- **MSConvert can hang** on large Orbitrap files (zero CPU). Kill process and re-convert.
- **pridepy** may create 0-byte placeholder files. Delete and re-download.
- **xtract_xml.exe** generates `sample.HCD.FTMS.ms2` naming; `convert_and_extract.py` handles the rename automatically.
- **xtract_xml.exe** must run from its parent directory (needs Xcalibur DLLs in the working directory).

---

## License

GNU General Public License v2.0

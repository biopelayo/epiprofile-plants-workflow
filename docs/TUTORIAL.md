# EpiProfile_PLANTS Tutorial

Step-by-step guide for processing Arabidopsis histone PTM data from PRIDE
datasets through the EpiProfile_PLANTS preprocessing pipeline.

This workflow produces `.ms1` + `.ms2` text files. The actual histone PTM
quantification is done by
[**epiprofile-plants**](https://github.com/biopelayo/epiprofile-plants),
a separate MATLAB tool.

---

## Prerequisites

### Software

| Tool | Version | Purpose |
|------|---------|---------|
| **Windows 10/11** | — | MSConvert and xtract_xml are Windows-only binaries |
| **Python 3.10+** | 3.13 tested | Pipeline scripts |
| **MSConvert** | ProteoWizard 3.x | `.raw` to centroided `.mzML` |
| **xtract_xml.exe** | EpiProfile 2.1 bundle (pXtract) | `.mzML` to `.ms1` + `.ms2` text |
| **pridepy** | 0.0.12+ | Download from PRIDE |
| **Snakemake** | 7+ (optional) | Rule-based workflow execution |

For the quantification step (after this workflow):

| Tool | Version | Purpose |
|------|---------|---------|
| **MATLAB** | R2023b+ | Run [epiprofile-plants](https://github.com/biopelayo/epiprofile-plants) |

### Install Python dependencies

```bash
pip install pridepy ppx
```

### Optional: install Snakemake environment

```bash
mamba env create -f envs/snakemake.yml
mamba activate epiprofile-plants-workflow
```

### Disk space

Each dataset needs roughly `raw_size * 1.3` total (raw + .ms1 + .ms2).
For all 3 reference datasets: **~200 GB**.

### Verify tool paths

```bash
# MSConvert
"D:/MS/share/OpenMS/THIRDPARTY/pwiz-bin/msconvert.exe" --help

# xtract_xml (run from its parent directory)
cd "D:/EpiProfile2.1_1Basic_Running_version"
xtract_xml.exe --help
```

---

## Option A: Run with Snakemake

Snakemake chains the three pipeline stages automatically. Each dataset has
its own config YAML (`config/config_pxd046034.yml`, etc.).

```bash
# Activate the environment
mamba activate epiprofile-plants-workflow

# Run the full pipeline for PXD046034
snakemake -s workflow/Snakefile --configfile config/config_pxd046034.yml

# Or run only a specific stage:
snakemake -s workflow/Snakefile --configfile config/config_pxd046034.yml download_pxd
snakemake -s workflow/Snakefile --configfile config/config_pxd046034.yml convert_raw_to_mzml
snakemake -s workflow/Snakefile --configfile config/config_pxd046034.yml extract_ms1_ms2_text
```

### Snakemake rule chain

```
download_pxd  →  convert_raw_to_mzml  →  extract_ms1_ms2_text
(pridepy FTP)    (MSConvert)              (xtract_xml.exe)
```

Each rule reads settings from the config YAML. See the
[config keys table in README.md](../README.md#config-keys-per-dataset-yaml)
for all available options.

---

## Option B: Run with standalone scripts

### Step 1: Download raw files from PRIDE

```bash
python workflow/scripts/pxd_triada_pipeline.py PXD046034 \
    --out D:/epiprofile_data/PXD046034 \
    --protocol ftp \
    --download-only
```

This creates:

```
D:/epiprofile_data/PXD046034/
  raw/                  # 48 .raw files
  download_report.json
```

#### Troubleshooting downloads

- **0-byte files**: pridepy sometimes creates placeholder files. Delete them
  and re-run the download command.
- **Slow FTP**: Try `--protocol aspera` if Aspera client is installed.
- **Partial downloads**: Re-run the same command; it skips existing files.

### Step 2: Convert raw to .ms1 + .ms2

The `convert_and_extract.py` script handles the full conversion pipeline:

```bash
python workflow/scripts/convert_and_extract.py --pxd PXD046034
```

With custom paths:

```bash
python workflow/scripts/convert_and_extract.py \
    --pxd PXD046034 \
    --base D:/epiprofile_data \
    --msconvert "D:/MS/share/OpenMS/THIRDPARTY/pwiz-bin/msconvert.exe" \
    --xtract "D:/EpiProfile2.1_1Basic_Running_version/xtract_xml.exe"
```

#### What happens internally

1. **MSConvert**: Each `.raw` file is converted to a full centroided `.mzML`
   with filters: `peakPicking vendor msLevel=1-` and `metadataFixer`.
2. **xtract_xml**: Each `.mzML` is extracted into `.ms1` + `.HCD.FTMS.ms2`
   text files.
3. **Rename**: `.HCD.FTMS.ms2` files are renamed to `.ms2`.
4. **RawData placeholders**: Empty `.raw` files are created (EpiProfile
   requires a matching `.raw` file in its RawData/ directory).
5. **Cleanup**: Intermediate `.mzML`, `.rawInfo`, and `.xtract` files are
   deleted to save disk space.

#### Output

```
D:/epiprofile_data/PXD046034/
  raw/                  # original .raw files
  MS1_MS2/              # 48 .ms1 + 48 .ms2 text files
  RawData/              # 48 empty .raw placeholders
```

#### Troubleshooting conversion

- **MSConvert hangs** (zero CPU, no progress): Kill the process and re-run.
  The script will skip already-converted files.
- **xtract_xml "Xcalibur not found"**: Make sure you run from the EpiProfile
  directory, or that the Xcalibur DLLs are accessible from the working directory.
- **Disk full**: The script processes files sequentially and deletes intermediate
  mzML after extraction. For very large datasets, ensure at least `largest_raw * 5`
  free space.

---

## Step 3: Verify output

Check that all files were created:

```bash
# Count ms1 files
dir /B D:\epiprofile_data\PXD046034\MS1_MS2\*.ms1 | find /c /v ""

# Count ms2 files
dir /B D:\epiprofile_data\PXD046034\MS1_MS2\*.ms2 | find /c /v ""

# Count RawData placeholders
dir /B D:\epiprofile_data\PXD046034\RawData\*.raw | find /c /v ""
```

All three counts should match the number of raw files (e.g., 48 for PXD046034).

---

## Step 4: Organize into batch folders (optional)

For running EpiProfile on subsets of samples grouped by experimental condition,
create an organized directory with batch folders:

```
D:\epiprofile_data\organized\PXD046034\
  MS1/                  # all .ms1 files (hard links)
  MS2/                  # all .ms2 files (hard links)
  RawData/              # all empty .raw placeholders (hard links)
  batches/
    3905_wt/
      MS1/   MS2/   RawData/    # 6 samples
    3905_fas/
      MS1/   MS2/   RawData/    # 6 samples
    ...
```

### How to create batch folders

Use hard links (zero extra disk space) to populate batch directories. Each
batch folder must contain matching triads: `sample.ms1`, `sample.ms2`, and
`sample.raw`.

Example Python snippet:

```python
import os

samples = ["3905_wt1", "3905_wt2", "3905_wt3",
           "3905_wt4", "3905_wt5", "3905_wt6"]
src = "D:/epiprofile_data/PXD046034"
dst = "D:/epiprofile_data/organized/PXD046034/batches/3905_wt"

for s in samples:
    os.makedirs(f"{dst}/MS1", exist_ok=True)
    os.makedirs(f"{dst}/MS2", exist_ok=True)
    os.makedirs(f"{dst}/RawData", exist_ok=True)
    os.link(f"{src}/MS1_MS2/{s}.ms1", f"{dst}/MS1/{s}.ms1")
    os.link(f"{src}/MS1_MS2/{s}.ms2", f"{dst}/MS2/{s}.ms2")
    os.link(f"{src}/RawData/{s}.raw", f"{dst}/RawData/{s}.raw")
```

### Reference batch groups

See [PIPELINE_RUN_LOG.md](PIPELINE_RUN_LOG.md#102-batch-groups) for the
complete list of 31 condition groups across all 3 PXD datasets.

---

## Step 5: Quantify with epiprofile-plants

**This step uses a different repository:**
[**biopelayo/epiprofile-plants**](https://github.com/biopelayo/epiprofile-plants)

`epiprofile-plants` is a MATLAB extension of EpiProfile 2.0 adapted for plant
histone proteomics. It provides:

- **Species bundles** (Arabidopsis, Marchantia, Chlamydomonas) with histone
  peptide catalogs and layouts
- **Three-layer data model**: hDP (histone-derived peptides) → hPF (peptideforms) → hPTM (site-level summaries)
- **QC utilities** for quality control and provenance tracking

### Setup

```bash
git clone https://github.com/biopelayo/epiprofile-plants.git
```

### Configuration (paras.txt)

The `paras.txt` file lives in the EpiProfile working directory. It tells the
MATLAB tool where to find the `.ms1`/`.ms2` files and which analysis mode to use.

Comments use MATLAB syntax (`%`). Only `raw_path` changes between runs — point
it to the `RawData/` folder of the batch or PXD you want to analyze.

```matlab
[EpiProfile]
% the datapath of raw files
raw_path=D:\epiprofile_data\PXD046788\MS1_MS2\RawData

% 1: Arabidopsis thaliana (in epiprofile-plants)
norganism=1

% 1: histone_LFQ, 2: histone_SILAC, 3: histone_13CD3, 4: histone_15N, 5: histone_13C2, 6: histone_D3
nsource=1

% if histone_LFQ: 0=light only, 1=heavy R no light, 2=heavy K+R no light
nsubtype=0
```

#### Example raw_path values for each PXD

| Dataset | raw_path (all files) | raw_path (batch example) |
|---------|---------------------|--------------------------|
| PXD046034 | `D:\epiprofile_data\PXD046034\MS1_MS2\RawData` | `D:\epiprofile_data\organized\PXD046034\batches\3905_wt\RawData` |
| PXD046788 | `D:\epiprofile_data\PXD046788\MS1_MS2\RawData` | `D:\epiprofile_data\organized\PXD046788\batches\TSA_root\RawData` |
| PXD014739 | `D:\epiprofile_data\PXD014739\MS1_MS2\RawData` | `D:\epiprofile_data\organized\PXD014739\batches\3w_LD\RawData` |

> **Important**: EpiProfile looks for `.ms1` and `.ms2` files **in the parent
> directory** of `raw_path` (i.e., alongside `RawData/`). This is why the
> pipeline creates `MS1_MS2/RawData/` inside each PXD, and the organized batch
> layout puts `MS1/`, `MS2/`, and `RawData/` as siblings.

#### Parameters explained

| Key | Value | Meaning |
|-----|-------|---------|
| `raw_path` | Path to `RawData/` folder | EpiProfile reads `.ms1`/`.ms2` from the parent, `.raw` from here |
| `norganism` | `1` | Organism (1 = Arabidopsis in epiprofile-plants; 1 = Human in upstream EpiProfile 2.0) |
| `nsource` | `1` | Quantification: 1=LFQ, 2=SILAC, 3=13CD3, 4=15N, 5=13C2, 6=D3 |
| `nsubtype` | `0` | For LFQ: 0=light only, 1=heavy R, 2=heavy K+R |

### Datasets at a glance

| PXD | Organism | Source | Description | Conditions |
|-----|----------|--------|-------------|------------|
| PXD046034 | *A. thaliana* | LFQ | Histone chaperone mutants (fas1, nap1) | wt, fas, nap, fasnap, +/- zymosan |
| PXD046788 | *A. thaliana* | LFQ | HDAC inhibitors in calli | Control, TSA, NaB, SAHA, Nicotinamide (root + calli) |
| PXD014739 | *A. thaliana* | LFQ | Histone acetylation across development | 12d, 3w, 5w, 7w (LD/SD), bolting, flowering, silique, senescing |

### Run

See the [epiprofile-plants README](https://github.com/biopelayo/epiprofile-plants)
for full instructions on running the MATLAB analysis, selecting species bundles,
and interpreting results.

---

## Quick reference

| Step | Command |
|------|---------|
| Download | `python workflow/scripts/pxd_triada_pipeline.py PXD046034 --out D:/epiprofile_data/PXD046034 --protocol ftp --download-only` |
| Convert | `python workflow/scripts/convert_and_extract.py --pxd PXD046034` |
| Verify | `dir /B D:\epiprofile_data\PXD046034\MS1_MS2\*.ms1 \| find /c /v ""` |
| Snakemake (all-in-one) | `snakemake -s workflow/Snakefile --configfile config/config_pxd046034.yml` |
| Quantify | Use [epiprofile-plants](https://github.com/biopelayo/epiprofile-plants) in MATLAB |

---

## Common issues

| Problem | Cause | Fix |
|---------|-------|-----|
| pridepy creates 0-byte files | PRIDE FTP timeout | Delete, re-download |
| MSConvert hangs (zero CPU) | Large Orbitrap file | Kill process, re-run |
| xtract_xml "Xcalibur not found" | Wrong working directory | `cd` to EpiProfile dir first |
| `.HCD.FTMS.ms2` not renamed | Script interrupted | Rename manually: `ren *.HCD.FTMS.ms2 *.ms2` |
| EpiProfile finds no files | Wrong `raw_path` | Ensure MS1/ MS2/ are siblings of RawData/ |
| MATLAB license expired | Trial/academic license | Renew or use institution license |

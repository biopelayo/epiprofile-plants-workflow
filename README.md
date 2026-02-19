# EpiProfile_PLANTS workflow

Reproducible pipeline for **Arabidopsis histone PTM quantification** from
Thermo `.raw` files using EpiProfile 2.1.

Part of a PhD thesis on **H3K79 in *Arabidopsis thaliana***.

Companion to the MATLAB code at
[`epiprofile-plants`](https://github.com/biopelayo/epiprofile-plants).

---

## Pipeline overview

```
.raw (Thermo)
  |  MSConvert (vendor centroiding)
  v
.mzML (centroided, full MS1+MS2)
  |  xtract_xml.exe (pXtract)
  v
.ms1 + .ms2 (text format)
  |  organize into MS1/ MS2/ RawData/
  v
EpiProfile.m (MATLAB)  -->  hPTM area matrices
```

### Steps

1. **Download** raw files from PRIDE via `pridepy` (FTP).
2. **MSConvert**: `.raw` to centroided `.mzML`
   (filters: `peakPicking vendor msLevel=1-`, `metadataFixer`).
3. **xtract_xml.exe**: `.mzML` to `.ms1` + `.HCD.FTMS.ms2`.
4. **Rename**: `.HCD.FTMS.ms2` to `.ms2`.
5. **Organize**: `MS1/`, `MS2/`, `RawData/` (empty `.raw` placeholders).
6. **Batch** (optional): group by condition into `batches/{group}/`.
7. **EpiProfile.m**: run from MATLAB on the `RawData/` path.

See [docs/TUTORIAL.md](docs/TUTORIAL.md) for a full step-by-step guide.

---

## Datasets processed

| PXD | Description | Instrument | Files | Raw size |
|-----|-------------|------------|-------|----------|
| PXD046034 | Histone chaperone mutants (fas/nap) | Orbitrap Fusion Lumos | 48 | 32 GB |
| PXD046788 | HDAC inhibitors (TSA/NaB) in calli | Orbitrap Fusion Lumos | 58 | 48 GB |
| PXD014739 | Histone acetylation profiling | LTQ Orbitrap Elite | 114 | 43 GB |

**Total**: 220 raw files, 123 GB. All downloaded, converted, and extracted.

---

## Repository structure

```text
epiprofile-plants-workflow/
  workflow/
    Snakefile                      # main entry point
    rules/
      download.smk                 # PRIDE download via pridepy
      mzml.smk                     # raw -> mzML via MSConvert
      ms1_ms2.smk                  # mzML -> .ms1/.ms2 via xtract_xml
    scripts/
      pxd_triada_pipeline.py       # download + MSConvert (standalone)
      convert_and_extract.py       # raw -> mzML -> xtract_xml -> organized
  config/
    config_pxd046034.yml
    config_pxd046788.yml
    config_pxd014739.yml
    config_ontogeny_demo.yml
  envs/
    snakemake.yml
  docs/
    PIPELINE_RUN_LOG.md            # detailed execution log
    TUTORIAL.md                    # step-by-step guide
    ONTOGENY_DEMO.md
  deploy_server.sh                 # Linux server deployment
  README.md
  LICENSE
```

---

## Requirements

- **Windows 10/11** (MSConvert and xtract_xml are Windows binaries)
- **Python 3.10+** with `pridepy`, `ppx` (`pip install pridepy ppx`)
- **MSConvert** (ProteoWizard, via OpenMS or standalone install)
- **xtract_xml.exe** (bundled with EpiProfile 2.1)
- **MATLAB** with EpiProfile.m
- ~200 GB free disk space for all 3 datasets

For Linux deployment: MSConvert runs via Docker
(`chambm/pwiz-skyline-i-agree-to-the-vendor-licenses`).
See `deploy_server.sh`.

---

## Quick start

```bash
# 1. Download a dataset from PRIDE
python workflow/scripts/pxd_triada_pipeline.py PXD046034 \
    --out D:/epiprofile_data/PXD046034 --protocol ftp --download-only

# 2. Convert raw -> mzML -> .ms1 + .ms2
python workflow/scripts/convert_and_extract.py --pxd PXD046034

# 3. Open MATLAB, configure paras.txt, run EpiProfile.m
```

---

## Data organization

After running the pipeline, each dataset has:

```
D:/epiprofile_data/organized/PXD046034/
  MS1/        48 x sample.ms1
  MS2/        48 x sample.ms2
  RawData/    48 x sample.raw (empty)
  batches/
    3905_wt/      MS1/ MS2/ RawData/  (6 samples)
    3905_fas/     MS1/ MS2/ RawData/  (6 samples)
    4105_nap/     MS1/ MS2/ RawData/  (6 samples)
    ...
```

Each batch folder has matching `sample.ms1` + `sample.ms2` + `sample.raw` triads.
Point MATLAB EpiProfile at any `batches/{group}/RawData/` folder.

---

## EpiProfile configuration (paras.txt)

```ini
[EpiProfile]
raw_path=D:\epiprofile_data\organized\PXD046034\batches\3905_wt\RawData
norganism=1    ; 1=Human (closest available for Arabidopsis)
nsource=1      ; LFQ
nsubtype=0     ; light only
```

---

## Known issues

- **MSConvert can hang** on large Orbitrap files (zero CPU). Kill process and re-convert.
- **pridepy** may create 0-byte placeholder files. Delete and re-download.
- **xtract_xml.exe** generates `sample.HCD.FTMS.ms2` naming; `convert_and_extract.py` handles the rename automatically.

---

## License

GNU General Public License v2.0

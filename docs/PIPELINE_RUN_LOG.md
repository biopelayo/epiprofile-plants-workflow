# Pipeline Execution Log

Step-by-step record of running the PXD Triada Pipeline on three
ProteomeXchange datasets for the EpiProfile_PLANTS workflow.

## Environment

| Component | Version / Path |
|-----------|---------------|
| OS | Windows 10 Home 10.0.19045 |
| Python | 3.13.1 (`C:\Python313\python.exe`) |
| MSConvert | `D:\MS\share\OpenMS\THIRDPARTY\pwiz-bin\msconvert.exe` (ProteoWizard via OpenMS 3.2.0) |
| pridepy | 0.0.12 |
| ppx | 1.5.0 |
| Snakemake | 9.16.3 |
| Docker | Installed (not used for MSConvert in this run) |

### Disk space (before downloads)

| Drive | Total | Free | Used% |
|-------|-------|------|-------|
| C: | 563 GB | 54 GB | 91% |
| D: | 390 GB | 258 GB | 35% |
| E: | 932 GB | 4.1 GB | 100% |

All downloads go to **D:** drive.

---

## Target Datasets

| PXD | Description | Instrument | Format | Files (actual) | Size (raw) |
|-----|-------------|------------|--------|----------------|------------|
| PXD046034 | Arabidopsis histone chaperone mutants (fas/nap) | Orbitrap Fusion Lumos | `.raw` | 48 | ~32 GB |
| PXD046788 | Arabidopsis calli HDAC inhibitors (TSA/NaB) | Orbitrap Fusion Lumos | `.raw` | 58 | ~48 GB |
| PXD014739 | Arabidopsis histone acetylation profiling | LTQ Orbitrap Elite | `.raw` | 114 | ~52 GB |

**Total actual: ~132 GB raw + ~80 GB mzML output**

---

## 1. Preparation

### 1.1 Dependencies installed

```bash
pip install pridepy ppx
```

Both installed successfully with all transitive dependencies (boto3, httpx,
cloudpathlib, etc.).

### 1.2 Pipeline script

The main script is `workflow/scripts/pxd_triada_pipeline.py`. Key features:

- Downloads raw files via pridepy Python API (`Files.download_all_raw_files`)
- Falls back to ppx if pridepy fails
- Converts with MSConvert using `--outfile` for explicit output naming
- Creates triada layout: `triada/ms1/`, `triada/ms2/`, `triada/raw_empty/`
- Vendor centroiding (peakPicking) placed first in filter chain per ProteoWizard docs
- Per-file logs, download_report.json, conversion_manifest.json

### 1.3 Configuration files created

- `config/config_pxd046034.yml`
- `config/config_pxd046788.yml`
- `config/config_pxd014739.yml`

All configured with:
- `base_dir` on D: drive
- `msconvert_path` pointing to local OpenMS ProteoWizard install
- `msconvert_centroid: vendor`
- `msconvert_gzip: false`
- `msconvert_bit_depth: 64`

---

## 2. PXD046034 — Download

**Started:** 2026-02-19 ~09:25 UTC

```bash
python workflow/scripts/pxd_triada_pipeline.py PXD046034 \
    --out "D:/epiprofile_data/PXD046034" \
    --protocol ftp \
    --download-only
```

**Status:** COMPLETE

**Results:**
- 48 `.raw` files downloaded (~32 GB total)
- Download time: ~673 seconds (~11 min)
- Downloader: pridepy (FTP)
- `download_report.json` written

**Output directory:**
```
D:/epiprofile_data/PXD046034/
  raw/                  # 48 .raw files
  logs/                 # pridepy download logs
  triada/
    raw_empty/          # 48 placeholder files + manifest
  download_report.json
```

---

## 3. PXD046034 — Conversion

```bash
python workflow/scripts/pxd_triada_pipeline.py PXD046034 \
    --out "D:/epiprofile_data/PXD046034" \
    --convert-only \
    --msconvert "D:/MS/share/OpenMS/THIRDPARTY/pwiz-bin/msconvert.exe" \
    --centroid vendor
```

**Status:** COMPLETE

**Results:**
- 48/48 MS1 conversions successful
- 48/48 MS2 conversions successful
- Total MS1 output: **3.7 GB** (48 files, avg ~77 MB each)
- Total MS2 output: **11.5 GB** (48 files, avg ~240 MB each)
- `conversion_manifest.json` written with SHA256 checksums
- 96 MSConvert log files in `logs/`

**MSConvert filters used:**
```
MS1: peakPicking vendor msLevel=1- | metadataFixer | msLevel 1
MS2: peakPicking vendor msLevel=1- | metadataFixer | msLevel 2-
```

**Output:**
```
D:/epiprofile_data/PXD046034/
  triada/
    ms1/    # 48 x <sample>.ms1.mzML  (3.7 GB total)
    ms2/    # 48 x <sample>.ms2.mzML  (11.5 GB total)
  conversion_manifest.json
  logs/     # 96 per-file msconvert logs
```

---

## 4. PXD046788 — Download

```bash
python workflow/scripts/pxd_triada_pipeline.py PXD046788 \
    --out "D:/epiprofile_data/PXD046788" \
    --protocol ftp \
    --download-only
```

**Status:** COMPLETE

**Results:**
- 58 `.raw` files downloaded (~48 GB total)
- Download time: ~940 seconds (~16 min)
- Downloader: pridepy (FTP)
- Note: Initial estimate was ~96 files, but PRIDE API returned 58 raw files

---

## 5. PXD046788 — Conversion

```bash
python workflow/scripts/pxd_triada_pipeline.py PXD046788 \
    --out "D:/epiprofile_data/PXD046788" \
    --convert-only \
    --msconvert "D:/MS/share/OpenMS/THIRDPARTY/pwiz-bin/msconvert.exe" \
    --centroid vendor
```

**Status:** COMPLETE

**Results:**
- 58/58 MS1 conversions successful
- 58/58 MS2 conversions successful
- Total MS1 output: **8.5 GB** (58 files)
- Total MS2 output: **29.4 GB** (58 files)
- `conversion_manifest.json` written with SHA256 checksums
- 116 MSConvert log files in `logs/`

**Issues encountered:**
- MSConvert hung on `TSA_root1.raw` MS2 conversion (zero CPU, stuck in memory for 90+ min).
  Killed process (PID 39924) with `cmd //c "taskkill /PID 39924 /F"`.
  Script caught the error and continued. TSA_root1.ms2.mzML was truncated (210 MB).
  Re-converted manually: `msconvert.exe TSA_root1.raw --filter "msLevel 2-"` → 578 MB (correct).

**Output:**
```
D:/epiprofile_data/PXD046788/
  triada/
    ms1/    # 58 x <sample>.ms1.mzML  (8.5 GB total)
    ms2/    # 58 x <sample>.ms2.mzML  (29.4 GB total)
  conversion_manifest.json
  logs/     # 116 per-file msconvert logs
```

---

## 6. PXD014739 — Download

```bash
python workflow/scripts/pxd_triada_pipeline.py PXD014739 \
    --out "D:/epiprofile_data/PXD014739" \
    --protocol ftp \
    --download-only
```

**Status:** COMPLETE

**Results:**
- 114 `.raw` files downloaded (~52 GB total)
- Downloader: pridepy (FTP)
- Note: Initial estimate was ~147 files, but PRIDE API returned 114 raw files

---

## 7. PXD014739 — Conversion

```bash
python workflow/scripts/pxd_triada_pipeline.py PXD014739 \
    --out "D:/epiprofile_data/PXD014739" \
    --convert-only \
    --msconvert "D:/MS/share/OpenMS/THIRDPARTY/pwiz-bin/msconvert.exe" \
    --centroid vendor
```

**Status:** COMPLETE

**Results:**
- 114/114 MS1 conversions successful
- 114/114 MS2 conversions successful
- Total MS1 output: **14.8 GB** (114 files)
- Total MS2 output: **8.3 GB** (114 files)
- `conversion_manifest.json` written with SHA256 checksums
- 228 MSConvert log files in `logs/`

**Issues encountered:**
- Initial pridepy download created 91/114 files as 0-byte placeholders (pridepy bug).
  Only 23 files (8.2 GB) had actual data.
  Fix: deleted all 91 zero-byte files, re-ran `--download-only`. All 114 files downloaded correctly (43.4 GB).
  Conversion then ran successfully: 114/114, 0 errors.

**Output:**
```
D:/epiprofile_data/PXD014739/
  triada/
    ms1/    # 114 x <sample>.ms1.mzML  (14.8 GB total)
    ms2/    # 114 x <sample>.ms2.mzML  (8.3 GB total)
  conversion_manifest.json
  logs/     # 228 per-file msconvert logs
```

---

## 8. Linux Server Deployment

A deployment script (`deploy_server.sh`) has been created following the same
pattern as the K-CHOPORE project. The Linux deployment uses Docker for MSConvert
(since ProteoWizard is Windows-only natively).

**Target server:** `/home/pelamovic/epiprofile_plants/`
(same server used for K-CHOPORE at `/home/pelamovic/K-CHOPORE/`)

**SSH config:**
```
Host 156.35.42.17    # University server (usuario2)
Host 192.168.44.11   # Local server (pelayo)
```

**Transfer options:**
```bash
# Transfer already-converted data from Windows:
rsync -avP /d/epiprofile_data/ usuario2@156.35.42.17:/home/pelamovic/epiprofile_plants/epiprofile_data/

# Or download + convert on server (from scratch):
bash deploy_server.sh /home/pelamovic/epiprofile_plants
nohup bash run_all_pxd.sh /home/pelamovic/epiprofile_plants > pipeline.log 2>&1 &
```

---

## Bugs Found and Fixed

### In the original pasted script

| # | Bug | Impact | Fix |
|---|-----|--------|-----|
| 1 | `Path.suffix` only returns last dot (`.scan`), so `.wiff.scan` never matched RAW_EXTS | WIFF files would be silently skipped | New `get_raw_ext()` with `str.endswith()`, longest-first |
| 2 | `--outfile` claimed not to exist in MSConvert | Would have caused temp-dir workaround | Tested local MSConvert: `--outfile` IS supported; used directly |
| 3 | pridepy API returns dicts, not URLs | `download_raw_file()` called with dict instead of URL | Use `download_all_raw_files()` batch method instead |
| 4 | `ensure_pairs()` paired construction appended ext instead of replacing | `sample.wiff.wiff.scan` instead of `sample.wiff.scan` | Extract stem before ext, append paired ext |
| 5 | No protocol validation | Silent failures with unsupported protocols | Added `VALID_PROTOCOLS` set + argparse choices |
| 6 | `shutil.which("pridepy")` fails on Windows (not on PATH) | Download would fail | Use Python API directly instead of CLI |
| 7 | No `--convert-only` flag | Had to re-download to convert | Added flag |
| 8 | Centroiding filter syntax | `peakPicking vendor 1-` vs `peakPicking vendor msLevel=1-` | Used correct ProteoWizard syntax |

### In the existing Snakefile

| # | Bug | Fix |
|---|-----|-----|
| 1 | `open(configfile, ...)` fails — `configfile` is a directive, not a Python string | Use `config` dict directly (populated by Snakemake) |
| 2 | Typo: `ONTNOGENY` | Fixed to `ONTOGENY` |
| 3 | Fragile `.format()` in shell block | Replaced with `run:` block using Python f-strings |

---

## Disk Usage Summary

| Dataset | Raw | MS1 mzML | MS2 mzML | Total |
|---------|-----|----------|----------|-------|
| PXD046034 | 32 GB | 3.7 GB | 11.5 GB | ~47 GB |
| PXD046788 | 48 GB | 8.5 GB | 29.4 GB | ~86 GB |
| PXD014739 | 43 GB | 14.8 GB | 8.3 GB | ~66 GB |
| **Total** | **123 GB** | **27 GB** | **49.2 GB** | **~199 GB** |

D: drive final: 331 GB used, 58 GB free.

---

## File Inventory (final)

```
epiprofile-plants-workflow-main/
  workflow/
    Snakefile                          # Fixed: includes rules, uses config dict
    rules/
      download.smk                     # Snakemake rule for download step
      mzml.smk                         # Snakemake rule for MSConvert step
      ms1_ms2.smk                      # Placeholder for text extraction
    scripts/
      pxd_triada_pipeline.py           # Main pipeline script (all bugs fixed)
  config/
    config_ontogeny_demo.yml           # Updated with msconvert/download fields
    config_pxd046034.yml               # PXD046034 config
    config_pxd046788.yml               # PXD046788 config
    config_pxd014739.yml               # PXD014739 config
  envs/
    snakemake.yml
  docs/
    ONTOGENY_DEMO.md
    PIPELINE_RUN_LOG.md                # THIS FILE
  deploy_server.sh                     # Linux server deployment script
  README.md
  LICENSE
```

**Data on D: drive:**
```
D:/epiprofile_data/
  PXD046034/
    raw/                  # 48 .raw files (32 GB)
    triada/
      ms1/                # 48 .ms1.mzML (3.7 GB)
      ms2/                # 48 .ms2.mzML (11.5 GB)
      raw_empty/          # 48 placeholders
    logs/                 # 96 msconvert logs + pridepy logs
    download_report.json
    conversion_manifest.json
  PXD046788/
    raw/                  # 58 .raw files (48 GB)
    triada/
      ms1/                # 58 .ms1.mzML (8.5 GB)
      ms2/                # 58 .ms2.mzML (29.4 GB)
      raw_empty/          # 58 placeholders
    logs/                 # 116 msconvert logs + pridepy logs
    download_report.json
    conversion_manifest.json
  PXD014739/
    raw/                  # 114 .raw files (43 GB)
    triada/
      ms1/                # 114 .ms1.mzML (14.8 GB)
      ms2/                # 114 .ms2.mzML (8.3 GB)
      raw_empty/          # 114 placeholders
    logs/                 # 228 msconvert logs + pridepy logs
    download_report.json
    conversion_manifest.json
```

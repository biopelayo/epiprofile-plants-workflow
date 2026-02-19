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

**Total actual: ~123 GB raw + ~40 GB ms1/ms2 text output**

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

## 9. xtract_xml Conversion (replacing triada mzML split)

### 9.1 Why the change

The original "triada" approach split each `.raw` into two mzML files filtered by
MS level (`ms1.mzML` and `ms2.mzML`). However, **EpiProfile 2.1 does not read
mzML**. It expects `.ms1` and `.ms2` **text** files produced by the `xtract_xml.exe`
tool (pXtract, bundled with pFind/EpiProfile). The correct pipeline is:

```
.raw → MSConvert (full centroided mzML) → xtract_xml.exe → .ms1 + .ms2 (text)
```

The old triada ms1/ms2 mzML directories (76 GB total) were deleted to free disk
space before running the new conversion.

### 9.2 Tool and command

```
D:\EpiProfile2.1_1Basic_Running_version\xtract_xml.exe
```

`xtract_xml.exe` must be run from its parent directory (needs Xcalibur DLLs).
Command per file:

```bash
xtract_xml.exe -ms -o <output_dir> <sample.mzML>
```

Produces: `sample.ms1`, `sample.HCD.FTMS.ms2`, `sample.rawInfo`, `sample.xtract`.
The `.HCD.FTMS.ms2` must be renamed to `.ms2` for EpiProfile.

### 9.3 Conversion script

`workflow/scripts/convert_and_extract.py` automates the full pipeline per PXD:
1. MSConvert: `.raw` → full centroided `.mzML` (vendor peakPicking, metadataFixer)
2. xtract_xml: `.mzML` → `.ms1` + `.HCD.FTMS.ms2`
3. Rename `.HCD.FTMS.ms2` → `.ms2`
4. Create empty `.raw` placeholders in `RawData/`
5. Delete intermediate `.mzML` to save disk space
6. Clean up `.rawInfo` and `.xtract` temp files

### 9.4 Results

| PXD | Files | MS1 size | MS2 size | Time | Errors |
|-----|-------|----------|----------|------|--------|
| PXD046034 | 48/48 | 3.4 GB | 6.4 GB | ~30 min | 0 |
| PXD046788 | 58/58 | 8.2 GB | 6.2 GB | ~105 min | 0 |
| PXD014739 | 114/114 | 13.5 GB | 2.0 GB | ~45 min | 0 |
| **Total** | **220/220** | **25.1 GB** | **14.6 GB** | **~3 h** | **0** |

All 220 files converted successfully with zero errors. Intermediate mzML was
deleted after each PXD to stay within D: drive capacity.

**Note:** PXD046788 `TSA_root1.raw` (which hung MSConvert in the old triada run)
converted normally this time (657 MB mzML, 99 s).

---

## 10. Batch Organization by Condition

### 10.1 Directory layout

Each PXD is organized into a standard EpiProfile-compatible structure with
per-condition batch folders:

```
D:\epiprofile_data\organized\{PXD}\
  MS1/          # all .ms1 files (hard links)
  MS2/          # all .ms2 files (hard links)
  RawData/      # all empty .raw placeholders (hard links)
  batches/
    {condition}/
      MS1/      # subset .ms1
      MS2/      # subset .ms2
      RawData/  # subset .raw (empty)
```

Hard links (Windows `os.link()`) are used instead of copies — **zero extra disk
space**. Each batch folder contains matching triads: `sample.ms1` + `sample.ms2`
+ `sample.raw`.

### 10.2 Batch groups

**PXD046034** — 8 batches (48 files):

| Batch | Samples |
|-------|---------|
| 3905_wt | 6 |
| 3905_fas | 6 |
| 3905_wt_Z | 6 |
| 3905_fas_Z | 6 |
| 4105_wt | 6 |
| 4105_fas | 6 |
| 4105_nap | 6 |
| 4105_fasnap | 6 |

**PXD046788** — 10 batches (58 files):

| Batch | Samples |
|-------|---------|
| Control_root | 6 |
| Control_calli | 6 |
| TSA_root | 6 |
| TSA_calli | 5 |
| NaB_root | 6 |
| NaB_calli | 6 |
| SAHA_root | 5 |
| SAHA_calli | 6 |
| Nicotinamide_root | 6 |
| Nicotinamide_calli | 6 |

**PXD014739** — 13 batches (114 files):

| Batch | Samples |
|-------|---------|
| 12d_light | 9 |
| 12d_dark | 9 |
| 3w_LD | 9 |
| 3w_SD | 9 |
| 5w_LD | 9 |
| 5w_SD | 9 |
| 7w_LD | 9 |
| 7w_SD | 9 |
| bolting | 9 |
| flowering | 9 |
| silique_green | 6 |
| silique_yellow | 9 |
| senescing | 9 |

**Total: 31 batches across 3 PXDs, 220 files.**

### 10.3 Running EpiProfile on a batch

Point MATLAB EpiProfile at any batch's `RawData/` path via `paras.txt`:

```ini
[EpiProfile]
raw_path=D:\epiprofile_data\organized\PXD046034\batches\3905_wt\RawData
norganism=1    ; 1=Human (closest available for Arabidopsis)
nsource=1      ; LFQ
nsubtype=0     ; light only
```

---

## Disk Usage Summary

| Dataset | Raw | .ms1 (text) | .ms2 (text) | Total |
|---------|-----|-------------|-------------|-------|
| PXD046034 | 32 GB | 3.4 GB | 6.4 GB | ~42 GB |
| PXD046788 | 48 GB | 8.2 GB | 6.2 GB | ~62 GB |
| PXD014739 | 43 GB | 13.5 GB | 2.0 GB | ~59 GB |
| **Total** | **123 GB** | **25.1 GB** | **14.6 GB** | **~163 GB** |

Organized directory (hard links): ~0 GB extra.

Old triada mzML (76 GB) deleted. Intermediate full mzML deleted after each PXD.

D: drive final: ~314 GB used, ~105 GB free.

---

## File Inventory (final)

```
epiprofile-plants-workflow-main/
  workflow/
    Snakefile                          # Fixed: includes rules, uses config dict
    rules/
      download.smk                     # Snakemake rule for download step
      mzml.smk                         # Snakemake rule for MSConvert step
      ms1_ms2.smk                      # xtract_xml extraction rule
    scripts/
      pxd_triada_pipeline.py           # Download + MSConvert (standalone)
      convert_and_extract.py           # raw -> mzML -> xtract_xml -> organized
  config/
    config_ontogeny_demo.yml           # Ontogeny demo config
    config_pxd046034.yml               # PXD046034 config
    config_pxd046788.yml               # PXD046788 config
    config_pxd014739.yml               # PXD014739 config
  envs/
    snakemake.yml
  docs/
    ONTOGENY_DEMO.md
    PIPELINE_RUN_LOG.md                # THIS FILE
    TUTORIAL.md                        # Step-by-step guide
  deploy_server.sh                     # Linux server deployment script
  README.md
  LICENSE
```

**Data on D: drive:**
```
D:/epiprofile_data/
  PXD046034/
    raw/                  # 48 .raw files (32 GB)
    MS1_MS2/              # 48 .ms1 + 48 .ms2 text files (9.8 GB)
    RawData/              # 48 empty .raw placeholders
    logs/
  PXD046788/
    raw/                  # 58 .raw files (48 GB)
    MS1_MS2/              # 58 .ms1 + 58 .ms2 text files (14.4 GB)
    RawData/              # 58 empty .raw placeholders
    logs/
  PXD014739/
    raw/                  # 114 .raw files (43 GB)
    MS1_MS2/              # 114 .ms1 + 114 .ms2 text files (15.5 GB)
    RawData/              # 114 empty .raw placeholders
    logs/
  organized/
    PXD046034/            # MS1/ MS2/ RawData/ batches/{8 groups}/
    PXD046788/            # MS1/ MS2/ RawData/ batches/{10 groups}/
    PXD014739/            # MS1/ MS2/ RawData/ batches/{13 groups}/
```

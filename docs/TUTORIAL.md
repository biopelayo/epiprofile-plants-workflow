# EpiProfile_PLANTS Tutorial

Step-by-step guide for processing Arabidopsis histone PTM data from PRIDE
datasets through the EpiProfile_PLANTS pipeline.

---

## Prerequisites

### Software

| Tool | Version | Purpose |
|------|---------|---------|
| **Windows 10/11** | — | MSConvert and xtract_xml are Windows-only binaries |
| **Python 3.10+** | 3.13 tested | Pipeline scripts |
| **MSConvert** | ProteoWizard 3.x | `.raw` to centroided `.mzML` |
| **xtract_xml.exe** | EpiProfile 2.1 bundle | `.mzML` to `.ms1` + `.ms2` text |
| **MATLAB** | R2023b+ | Run EpiProfile.m |
| **pridepy** | 0.0.12+ | Download from PRIDE |

### Install Python dependencies

```bash
pip install pridepy ppx
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

## Step 1: Download raw files from PRIDE

Use the standalone download script to fetch `.raw` files via FTP:

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

### Troubleshooting downloads

- **0-byte files**: pridepy sometimes creates placeholder files. Delete them
  and re-run the download command.
- **Slow FTP**: Try `--protocol aspera` if Aspera client is installed.
- **Partial downloads**: Re-run the same command; it skips existing files.

---

## Step 2: Convert raw to .ms1 + .ms2

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

### What happens internally

1. **MSConvert**: Each `.raw` file is converted to a full centroided `.mzML`
   with filters: `peakPicking vendor msLevel=1-` and `metadataFixer`.
2. **xtract_xml**: Each `.mzML` is extracted into `.ms1` + `.HCD.FTMS.ms2`
   text files.
3. **Rename**: `.HCD.FTMS.ms2` files are renamed to `.ms2`.
4. **RawData placeholders**: Empty `.raw` files are created (EpiProfile
   requires a matching `.raw` file in its RawData/ directory).
5. **Cleanup**: Intermediate `.mzML`, `.rawInfo`, and `.xtract` files are
   deleted to save disk space.

### Output

```
D:/epiprofile_data/PXD046034/
  raw/                  # original .raw files
  MS1_MS2/              # 48 .ms1 + 48 .ms2 text files
  RawData/              # 48 empty .raw placeholders
```

### Troubleshooting conversion

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

## Step 4: Organize into batch folders

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

## Step 5: Configure EpiProfile

Edit the `paras.txt` file in the EpiProfile directory to point to a batch:

```ini
[EpiProfile]
raw_path=D:\epiprofile_data\organized\PXD046034\batches\3905_wt\RawData
norganism=1    ; 1=Human (closest available for Arabidopsis)
nsource=1      ; LFQ
nsubtype=0     ; light only
```

### Parameters explained

| Key | Value | Meaning |
|-----|-------|---------|
| `raw_path` | Full path to `RawData/` folder | Where EpiProfile looks for `.ms1`, `.ms2`, and `.raw` files |
| `norganism` | `1` | Organism code (1=Human is used as closest proxy for Arabidopsis) |
| `nsource` | `1` | Quantification mode (1=LFQ, label-free quantification) |
| `nsubtype` | `0` | Labeling subtype (0=light only) |

> **Important**: EpiProfile looks for `.ms1` and `.ms2` files in the **parent
> directory** of `raw_path`, i.e., at the same level as `RawData/`. This is why
> the batch layout puts `MS1/`, `MS2/`, and `RawData/` as siblings.

---

## Step 6: Run EpiProfile in MATLAB

1. Open MATLAB.
2. Navigate to the EpiProfile directory:
   ```matlab
   cd('D:\EpiProfile2.1_1Basic_Running_version')
   ```
3. Run the main script:
   ```matlab
   EpiProfile
   ```
4. EpiProfile reads `paras.txt`, finds the files, and produces area matrices
   for each histone peptide + PTM combination.

### Running multiple batches

To process all condition groups, update `paras.txt` → run EpiProfile → save
output → repeat. For systematic processing, a MATLAB loop can iterate over
batch folders:

```matlab
batches = dir('D:\epiprofile_data\organized\PXD046034\batches\*');
for i = 1:length(batches)
    if batches(i).isdir && ~startsWith(batches(i).name, '.')
        % Update paras.txt raw_path
        fid = fopen('paras.txt', 'w');
        fprintf(fid, '[EpiProfile]\n');
        fprintf(fid, 'raw_path=%s\\RawData\n', ...
            fullfile(batches(i).folder, batches(i).name));
        fprintf(fid, 'norganism=1\n');
        fprintf(fid, 'nsource=1\n');
        fprintf(fid, 'nsubtype=0\n');
        fclose(fid);

        % Run EpiProfile
        EpiProfile;

        % Move output to batch-specific folder
        % (adjust based on EpiProfile output location)
    end
end
```

---

## Step 7: Collect and analyze results

EpiProfile outputs area matrices (CSV/Excel) with columns for each sample and
rows for each histone peptide + PTM combination. Downstream analysis typically
includes:

- Normalization (relative abundance per peptide)
- Statistical comparison between conditions (e.g., wt vs. fas)
- Visualization (heatmaps, bar charts)
- Integration with the custom MATLAB code at
  [`epiprofile-plants`](https://github.com/biopelayo/epiprofile-plants)

---

## Quick reference

| Step | Command |
|------|---------|
| Download | `python workflow/scripts/pxd_triada_pipeline.py PXD046034 --out D:/epiprofile_data/PXD046034 --protocol ftp --download-only` |
| Convert | `python workflow/scripts/convert_and_extract.py --pxd PXD046034` |
| Verify | `dir /B D:\epiprofile_data\PXD046034\MS1_MS2\*.ms1 \| find /c /v ""` |
| Configure | Edit `paras.txt` with `raw_path` pointing to batch `RawData/` |
| Run | `EpiProfile` in MATLAB |

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

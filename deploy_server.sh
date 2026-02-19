#!/bin/bash
# ==============================================================
# EpiProfile-PLANTS Server Deployment Script
# ==============================================================
# Deploys the EpiProfile_PLANTS preprocessing pipeline to a Linux server.
#
# PREREQUISITES:
#   - Docker installed and running (for MSConvert — ProteoWizard is Windows-only)
#   - Python 3.10+ with pip
#   - ~500 GB free disk space (3 PXD datasets + converted output)
#
# USAGE:
#   bash deploy_server.sh /path/to/workspace [threads]
#
# DATA TRANSFER (from Windows to server):
#   # Transfer already-converted data from D: drive:
#   rsync -avP D:/epiprofile_data/ user@server:/workspace/epiprofile_data/
#
#   # Or transfer only raw files and re-convert on server:
#   rsync -avP D:/epiprofile_data/PXD046034/raw/ user@server:/workspace/epiprofile_data/PXD046034/raw/
#
# The workspace directory will contain:
#   epiprofile_data/
#   +-- PXD046034/
#   |   +-- raw/           # 48 .raw files (~32 GB)
#   |   +-- mzML/          # intermediate centroided mzML (deleted after extraction)
#   |   +-- MS1_MS2/       # 48 .ms1 + 48 .ms2 text files
#   |   +-- RawData/       # 48 empty .raw placeholders (for EpiProfile)
#   |   +-- download_report.json
#   |   +-- conversion_manifest.json
#   |   +-- logs/
#   +-- PXD046788/         # same structure, 58 files
#   +-- PXD014739/         # same structure, 114 files
#   repo/
#   +-- epiprofile-plants-workflow-main/  # git clone of the pipeline
#
# NOTE: xtract_xml.exe (mzML → .ms1/.ms2 text) is Windows-only.
# On Linux, use Wine or convert on Windows and rsync .ms1/.ms2 files.
#
# Total disk needed: ~500 GB (raw + mzML + ms1/ms2 + working space)
# ==============================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
WORKSPACE="${1:-}"
THREADS="${2:-$(nproc)}"
MSCONVERT_DOCKER="chambm/pwiz-skyline-i-agree-to-the-vendor-licenses:latest"

if [ -z "$WORKSPACE" ]; then
    echo -e "${RED}ERROR: Please specify the workspace path.${NC}"
    echo ""
    echo "Usage: bash $0 /path/to/workspace [threads]"
    echo ""
    echo "Example: bash $0 /home/pelamovic/epiprofile_plants"
    exit 1
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} EpiProfile-PLANTS Server Deployment${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "Workspace:       ${YELLOW}$WORKSPACE${NC}"
echo -e "Threads:         ${YELLOW}$THREADS${NC}"
echo -e "MSConvert image: ${YELLOW}$MSCONVERT_DOCKER${NC}"
echo ""

# --- Step 1: System checks ---
echo -e "${GREEN}[1/6] Checking system requirements...${NC}"

# Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 not found. Install: sudo apt install python3 python3-pip${NC}"
    exit 1
fi
PYVER=$(python3 --version)
echo -e "  Python: ${GREEN}$PYVER${NC}"

# Docker (needed for MSConvert on Linux)
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}WARNING: Docker not found. Needed for MSConvert on Linux.${NC}"
    echo -e "  Install: curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker \$USER"
    DOCKER_OK=0
else
    if docker info &> /dev/null; then
        echo -e "  Docker: ${GREEN}$(docker --version)${NC}"
        DOCKER_OK=1
    else
        echo -e "  Docker: ${YELLOW}installed but daemon not running${NC}"
        DOCKER_OK=0
    fi
fi

# Git
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}WARNING: Git not found. Install: sudo apt install git${NC}"
fi

# Disk space
AVAIL_GB=$(df -BG "$WORKSPACE" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo "unknown")
echo -e "  Disk free: ${YELLOW}${AVAIL_GB} GB${NC}"
if [ "$AVAIL_GB" != "unknown" ] && [ "$AVAIL_GB" -lt 300 ]; then
    echo -e "  ${YELLOW}WARNING: Less than 300 GB free. Full pipeline needs ~500 GB.${NC}"
fi

# System info
echo -e "  CPUs: ${YELLOW}$(nproc)${NC}"
echo -e "  RAM:  ${YELLOW}$(free -h | awk '/Mem:/{print $2}')${NC}"
echo ""

# --- Step 2: Create directory structure ---
echo -e "${GREEN}[2/6] Setting up workspace...${NC}"
mkdir -p "$WORKSPACE"/{repo,epiprofile_data/{PXD046034,PXD046788,PXD014739}/{raw,mzML,MS1_MS2,RawData,logs}}
echo -e "  ${GREEN}Directory structure created.${NC}"
echo ""

# --- Step 3: Install Python dependencies ---
echo -e "${GREEN}[3/6] Installing Python dependencies...${NC}"
pip3 install --user pridepy ppx 2>&1 | tail -5
echo -e "  ${GREEN}pridepy + ppx installed.${NC}"
echo ""

# --- Step 4: Pull MSConvert Docker image ---
echo -e "${GREEN}[4/6] Pulling MSConvert Docker image...${NC}"
if [ "$DOCKER_OK" -eq 1 ]; then
    docker pull "$MSCONVERT_DOCKER" 2>&1 | tail -5
    echo -e "  ${GREEN}Docker image ready.${NC}"
else
    echo -e "  ${YELLOW}Skipping (Docker not available).${NC}"
fi
echo ""

# --- Step 5: Create wrapper scripts ---
echo -e "${GREEN}[5/6] Creating helper scripts...${NC}"

# msconvert wrapper for Linux (runs via Docker)
cat > "$WORKSPACE/msconvert_linux.sh" << 'WRAPPER_EOF'
#!/bin/bash
# MSConvert wrapper for Linux via Docker
# Usage: bash msconvert_linux.sh <args-for-msconvert>
# The raw file path must be an absolute path.
#
# This wraps the official ProteoWizard Docker image.
# Ref: https://hub.docker.com/r/chambm/pwiz-skyline-i-agree-to-the-vendor-licenses

IMAGE="chambm/pwiz-skyline-i-agree-to-the-vendor-licenses:latest"

# Find the raw file argument (first non-flag argument)
RAW_FILE=""
DOCKER_ARGS=()
for arg in "$@"; do
    if [[ "$arg" != -* ]] && [ -z "$RAW_FILE" ]; then
        RAW_FILE="$arg"
    fi
done

if [ -z "$RAW_FILE" ]; then
    echo "ERROR: No input file specified."
    exit 1
fi

RAW_DIR=$(dirname "$(realpath "$RAW_FILE")")
RAW_BASE=$(basename "$RAW_FILE")

# Find the output directory from -o flag
OUT_DIR=""
NEXT_IS_OUT=0
for arg in "$@"; do
    if [ "$NEXT_IS_OUT" -eq 1 ]; then
        OUT_DIR="$arg"
        NEXT_IS_OUT=0
    fi
    if [ "$arg" = "-o" ]; then
        NEXT_IS_OUT=1
    fi
done

if [ -z "$OUT_DIR" ]; then
    OUT_DIR="$RAW_DIR"
fi
OUT_DIR=$(realpath "$OUT_DIR" 2>/dev/null || echo "$OUT_DIR")
mkdir -p "$OUT_DIR"

# Build the msconvert command, remapping paths inside the container
# Mount raw dir at /data/raw and output dir at /data/out
CONTAINER_ARGS=()
for arg in "$@"; do
    if [ "$arg" = "$RAW_FILE" ]; then
        CONTAINER_ARGS+=("/data/raw/$RAW_BASE")
    elif [ "$arg" = "$OUT_DIR" ]; then
        CONTAINER_ARGS+=("/data/out")
    else
        CONTAINER_ARGS+=("$arg")
    fi
done

docker run --rm \
    -v "$RAW_DIR:/data/raw:ro" \
    -v "$OUT_DIR:/data/out" \
    "$IMAGE" \
    wine msconvert "${CONTAINER_ARGS[@]}"
WRAPPER_EOF
chmod +x "$WORKSPACE/msconvert_linux.sh"
echo -e "  ${GREEN}Created: msconvert_linux.sh${NC}"

# Download + convert helper
cat > "$WORKSPACE/run_pxd.sh" << 'RUN_EOF'
#!/bin/bash
# Download and/or convert a single PXD dataset
# Usage: bash run_pxd.sh <PXD_ID> [download|convert|both] [workspace]
set -euo pipefail

PXD="${1:?Usage: bash run_pxd.sh PXD046034 [download|convert|both] [workspace]}"
MODE="${2:-both}"
WORKSPACE="${3:-$(dirname "$(realpath "$0")")}"
SCRIPT="$WORKSPACE/repo/epiprofile-plants-workflow-main/workflow/scripts/pxd_triada_pipeline.py"
OUT="$WORKSPACE/epiprofile_data/$PXD"
MSCONVERT="$WORKSPACE/msconvert_linux.sh"

echo "PXD:       $PXD"
echo "Mode:      $MODE"
echo "Output:    $OUT"
echo "Script:    $SCRIPT"
echo ""

if [ "$MODE" = "download" ] || [ "$MODE" = "both" ]; then
    echo "=== Downloading $PXD ==="
    python3 "$SCRIPT" "$PXD" --out "$OUT" --protocol ftp --download-only
fi

if [ "$MODE" = "convert" ] || [ "$MODE" = "both" ]; then
    echo "=== Converting $PXD ==="
    python3 "$SCRIPT" "$PXD" --out "$OUT" \
        --convert-only \
        --msconvert "$MSCONVERT" \
        --centroid vendor
fi

echo ""
echo "=== Done: $PXD ==="
RUN_EOF
chmod +x "$WORKSPACE/run_pxd.sh"
echo -e "  ${GREEN}Created: run_pxd.sh${NC}"

# Run-all script
cat > "$WORKSPACE/run_all_pxd.sh" << 'ALLEOF'
#!/bin/bash
# Download and convert all three PXD datasets sequentially
set -euo pipefail

WORKSPACE="${1:-$(dirname "$(realpath "$0")")}"

for PXD in PXD046034 PXD046788 PXD014739; do
    echo ""
    echo "============================================"
    echo " Processing $PXD"
    echo "============================================"
    bash "$WORKSPACE/run_pxd.sh" "$PXD" both "$WORKSPACE"
done

echo ""
echo "============================================"
echo " ALL DATASETS COMPLETE"
echo "============================================"
ALLEOF
chmod +x "$WORKSPACE/run_all_pxd.sh"
echo -e "  ${GREEN}Created: run_all_pxd.sh${NC}"
echo ""

# --- Step 6: Summary ---
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN} Deployment complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo "Directory layout:"
echo "  $WORKSPACE/"
echo "  +-- epiprofile_data/"
echo "  |   +-- PXD046034/  (48 files, ~32 GB raw)"
echo "  |   +-- PXD046788/  (58 files, ~48 GB raw)"
echo "  |   +-- PXD014739/  (114 files, ~52 GB raw)"
echo "  +-- repo/            (git clone of the workflow)"
echo "  +-- msconvert_linux.sh  (Docker wrapper)"
echo "  +-- run_pxd.sh          (per-dataset runner)"
echo "  +-- run_all_pxd.sh      (all datasets)"
echo ""
echo "OPTION A: Transfer already-converted data from Windows:"
echo -e "  ${YELLOW}rsync -avP D:/epiprofile_data/ user@this-server:$WORKSPACE/epiprofile_data/${NC}"
echo ""
echo "OPTION B: Download + convert on server (from scratch):"
echo -e "  ${YELLOW}nohup bash $WORKSPACE/run_all_pxd.sh $WORKSPACE > $WORKSPACE/pipeline.log 2>&1 &${NC}"
echo ""
echo "OPTION C: Run individual datasets:"
echo -e "  ${YELLOW}bash $WORKSPACE/run_pxd.sh PXD046034 download${NC}"
echo -e "  ${YELLOW}bash $WORKSPACE/run_pxd.sh PXD046034 convert${NC}"
echo ""
echo "Monitor progress:"
echo -e "  ${YELLOW}tail -f $WORKSPACE/pipeline.log${NC}"
echo ""

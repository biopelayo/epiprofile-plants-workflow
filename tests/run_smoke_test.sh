#!/usr/bin/env bash
# Smoke test: runs the whole Snakemake chain and the standalone script on
# synthetic .raw files using fake MSConvert / xtract_xml binaries.
# Needs only Python 3 and snakemake. No PRIDE network, no Windows tools.
#
#   bash tests/run_smoke_test.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${SMOKE_DIR:-$(mktemp -d)}"
FAKE="$REPO/tests/fakebin"
PXD="PXDTEST"
BASE="$WORK/$PXD"

echo "== workdir: $WORK"
mkdir -p "$BASE/raw"
for s in 3905_wt1 3905_wt2 3905_fas1; do head -c 2048 /dev/urandom > "$BASE/raw/$s.raw"; done

# The download rule needs PRIDE network access; pre-stage its report so the
# rest of the DAG (convert -> extract) runs offline.
python3 - "$BASE" "$PXD" <<'EOF'
import json, pathlib, sys
base, pxd = pathlib.Path(sys.argv[1]), sys.argv[2]
raw = sorted(str(p) for p in (base / "raw").glob("*.raw"))
(base / "download_report.json").write_text(json.dumps(
    {"pxd": pxd, "downloader": "pre-staged (smoke test)", "raw_count": len(raw),
     "raw_files": raw, "pair_problems": []}, indent=2))
EOF

cat > "$WORK/config_smoke.yml" <<EOF
project_id: "$PXD"
base_dir: "$BASE"
mzml_dir: "mzML"
ms1_dir: "MS1"
ms2_dir: "MS2"
msconvert_path: "$FAKE/msconvert.py"
msconvert_centroid: "vendor"
xtract_xml_path: "$FAKE/xtract_xml.py"
EOF

echo "== [1/3] Snakemake: download_report -> convert_raw_to_mzml -> extract_ms1_ms2_text"
cd "$REPO"
snakemake -s workflow/Snakefile --configfile "$WORK/config_smoke.yml" -c1 --quiet rules

for d in MS1 MS2 RawData; do
    n=$(ls "$BASE/$d" | grep -cv '^\.' || true)
    [ "$n" -eq 3 ] || { echo "FAIL: $d has $n files, expected 3"; exit 1; }
done
grep -q '"layout": "full"' "$BASE/conversion_manifest.json" || { echo "FAIL: manifest layout"; exit 1; }
ls "$BASE/MS2" | grep -q 'HCD' && { echo "FAIL: .HCD.FTMS.ms2 not renamed"; exit 1; }
echo "   OK: 3 x .ms1, 3 x .ms2, 3 x .raw placeholders"

echo "== [2/3] Snakemake re-run is a no-op"
snakemake -s workflow/Snakefile --configfile "$WORK/config_smoke.yml" -c1 all 2>&1 | grep -q "Nothing to be done" \
    || { echo "FAIL: re-run was not a no-op"; exit 1; }
echo "   OK: nothing to be done"

echo "== [3/3] Standalone convert_and_extract.py"
mkdir -p "$WORK/standalone/$PXD/raw" && cp "$BASE/raw/"*.raw "$WORK/standalone/$PXD/raw/"
python3 workflow/scripts/convert_and_extract.py --pxd "$PXD" --base "$WORK/standalone" \
    --msconvert "$FAKE/msconvert.py" --xtract "$FAKE/xtract_xml.py" | grep -E "\[OK\]|\[FAIL\]"
[ "$(ls "$WORK/standalone/$PXD/MS1_MS2/"*.ms2 | wc -l)" -eq 3 ] || { echo "FAIL: standalone"; exit 1; }

echo
echo "SMOKE TEST PASSED"

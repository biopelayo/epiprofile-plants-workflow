#!/usr/bin/env python3
"""Generate analysis figures for the smoke test run and the documented real runs."""
import json, pathlib, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

RUN = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

# ---- palette (validated default, light mode) ----
C = dict(blue="#2a78d6", orange="#eb6834", aqua="#1baf7a", yellow="#eda100",
         magenta="#e87ba4", green="#008300")
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
GOOD = "#0ca30c"
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "figure.facecolor": SURF, "axes.facecolor": SURF,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "text.color": INK, "axes.titleweight": "semibold", "axes.titlesize": 11, "axes.titlelocation": "left",
})

def finish(fig, name, note=None):
    if note:
        fig.text(0.01, -0.06, note, fontsize=8, color=MUTED, ha="left", va="bottom")
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / name)

def hbar(ax, labels, values, color, fmt="{:g}"):
    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=color, height=0.55)
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    for b, v in zip(bars, values):
        ax.text(b.get_width(), b.get_y() + b.get_height() / 2, "  " + fmt.format(v),
                va="center", ha="left", fontsize=9, color=INK2)
    return bars

# =========================================================================
# 1. Rule graph (DAG) of the Snakemake workflow
# =========================================================================
fig, ax = plt.subplots(figsize=(9, 2.6)); ax.axis("off"); ax.grid(False)
nodes = [("download_pxd", "pridepy FTP\n→ download_report.json", C["blue"]),
         ("convert_raw_to_mzml", "MSConvert --layout full\n→ mzML/*.mzML + manifest", C["orange"]),
         ("extract_ms1_ms2_text", "xtract_xml.exe\n→ MS1/ MS2/ RawData/", C["aqua"]),
         ("all", "convenience target", MUTED)]
xs = [0.05, 0.32, 0.59, 0.86]
for (name, sub, col), x in zip(nodes, xs):
    ax.add_patch(FancyBboxPatch((x, 0.35), 0.2, 0.42, boxstyle="round,pad=0.01,rounding_size=0.02",
                                fc=SURF, ec=col, lw=2, transform=ax.transAxes))
    ax.text(x + 0.1, 0.66, name, ha="center", va="center", fontsize=9.5, weight="semibold", transform=ax.transAxes)
    ax.text(x + 0.1, 0.47, sub, ha="center", va="center", fontsize=8, color=INK2, transform=ax.transAxes)
for a, b in zip(xs[:-1], xs[1:]):
    ax.add_patch(FancyArrowPatch((a + 0.2, 0.56), (b, 0.56), arrowstyle="-|>", mutation_scale=14,
                                 color=MUTED, lw=1.5, transform=ax.transAxes))
ax.text(0.05, 0.12, "raw (.raw)", fontsize=8, color=MUTED, transform=ax.transAxes)
ax.text(0.32, 0.12, "mzML centroidado (MS1+MS2)", fontsize=8, color=MUTED, transform=ax.transAxes)
ax.text(0.59, 0.12, ".ms1 + .ms2 texto (EpiProfile)", fontsize=8, color=MUTED, transform=ax.transAxes)
ax.set_title("Fig. 1  Cadena de reglas Snakemake (rulegraph) tras la corrección")
finish(fig, "fig1_rulegraph.png", "Antes del fix, convert_raw_to_mzml escribía triada/ms1 + triada/ms2 y extract_ms1_ms2_text buscaba en mzML/: la cadena no enlazaba.")

# =========================================================================
# 2. Timing per stage of the smoke run
# =========================================================================
tim = {}
for line in (RUN / "timings.txt").read_text().splitlines():
    k, *rest = line.split()
    tim[k] = float(rest[-1].rstrip("s"))
labels = ["convert_raw_to_mzml\n(12 raw → mzML)", "extract_ms1_ms2_text\n(12 mzML → ms1/ms2)",
          "all (verificación DAG)", "re-ejecución (no-op)", "convert_and_extract.py\n(standalone, 12 raw)"]
vals = [tim["convert_raw_to_mzml"], tim["extract_ms1_ms2_text"], tim["all"], tim["rerun_noop"], tim["standalone"]]
fig, ax = plt.subplots(figsize=(8, 3.6))
hbar(ax, labels, vals, C["blue"], fmt="{:.2f} s")
ax.set_xlabel("segundos (wall clock)")
ax.set_title("Fig. 2  Tiempo por etapa del smoke test (binarios simulados)")
finish(fig, "fig2_timings.png", "Snakemake 9.27.1, Linux, 1 core. El tiempo es casi todo arranque de Snakemake/Python; no refleja MSConvert ni xtract_xml reales.")

# =========================================================================
# 3. Output inventory: files and bytes per directory
# =========================================================================
inv = {}
for line in (RUN / "inventory.txt").read_text().splitlines():
    size, path = line.split(" ", 1)
    d = path.split("/")[0] if "/" in path else "(raíz)"
    inv.setdefault(d, [0, 0]); inv[d][0] += 1; inv[d][1] += int(size)
order = [d for d in ["raw", "mzML", "MS1", "MS2", "RawData", "logs", "(raíz)"] if d in inv]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
hbar(axes[0], order, [inv[d][0] for d in order], C["blue"], fmt="{:d}")
axes[0].set_title("Fig. 3a  Ficheros generados por directorio"); axes[0].set_xlabel("nº ficheros")
hbar(axes[1], order, [inv[d][1] / 1024 for d in order], C["orange"], fmt="{:.1f} KB")
axes[1].set_title("Fig. 3b  Bytes por directorio"); axes[1].set_xlabel("KB")
finish(fig, "fig3_inventory.png", "12 muestras sintéticas (4 condiciones × 3 réplicas). RawData/ son placeholders vacíos (0 B) que EpiProfile exige junto a MS1/ y MS2/.")

# =========================================================================
# 4. Triad completeness check per sample
# =========================================================================
samples = sorted({pathlib.Path(p.split(" ", 1)[1]).stem for p in (RUN / "inventory.txt").read_text().splitlines()
                  if p.split(" ", 1)[1].startswith("raw/")})
stages = ["raw", "mzML", "MS1", "MS2", "RawData"]
ext = {"raw": ".raw", "mzML": ".mzML", "MS1": ".ms1", "MS2": ".ms2", "RawData": ".raw"}
present = set(p.split(" ", 1)[1] for p in (RUN / "inventory.txt").read_text().splitlines())
M = np.array([[1 if f"{st}/{s}{ext[st]}" in present else 0 for st in stages] for s in samples])
fig, ax = plt.subplots(figsize=(6.5, 4.4))
ax.imshow(M, cmap=matplotlib.colors.ListedColormap(["#f0efec", GOOD]), vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(stages))); ax.set_xticklabels(stages)
ax.set_yticks(range(len(samples))); ax.set_yticklabels(samples, fontsize=8)
ax.grid(False)
for i in range(len(samples)):
    for j in range(len(stages)):
        ax.text(j, i, "✓" if M[i, j] else "✗", ha="center", va="center", fontsize=9,
                color="white" if M[i, j] else INK)
ax.set_title(f"Fig. 4  Completitud de tríadas: {int(M.all(axis=1).sum())}/{len(samples)} muestras completas")
finish(fig, "fig4_triads.png", "Una muestra está completa cuando existe raw → mzML → .ms1 + .ms2 + placeholder .raw.")

# =========================================================================
# 5. Documented real runs (docs/PIPELINE_RUN_LOG.md): sizes per PXD
# =========================================================================
pxd = ["PXD046034", "PXD046788", "PXD014739"]
files = [48, 58, 114]
raw_gb = [32, 48, 43]; ms1_gb = [3.4, 8.2, 13.5]; ms2_gb = [6.4, 6.2, 2.0]
mins = [30, 105, 45]
fig, axes = plt.subplots(1, 3, figsize=(13, 3.8)); fig.subplots_adjust(wspace=0.35)
x = np.arange(3); w = 0.26
ax = axes[0]
for k, (vals_, lab, col) in enumerate([(raw_gb, ".raw (entrada)", C["blue"]), (ms1_gb, ".ms1 (texto)", C["orange"]), (ms2_gb, ".ms2 (texto)", C["aqua"])]):
    b = ax.bar(x + (k - 1) * w, vals_, w * 0.92, label=lab, color=col)
    for r, v in zip(b, vals_):
        ax.text(r.get_x() + r.get_width() / 2, v, f"{v:g}", ha="center", va="bottom", fontsize=8, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(pxd); ax.set_ylabel("GB"); ax.grid(axis="x", visible=False)
ax.legend(frameon=False, fontsize=8); ax.set_title("Fig. 5a  Tamaño por dataset (GB)")
ax = axes[1]
b = ax.bar(x, files, 0.55, color=C["blue"])
for r, v in zip(b, files): ax.text(r.get_x() + r.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=9, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(pxd); ax.set_ylabel("ficheros .raw"); ax.grid(axis="x", visible=False)
ax.set_title("Fig. 5b  Ficheros .raw (220 total, 0 errores)")
ax = axes[2]
rate = [m / f for m, f in zip(mins, files)]
b = ax.bar(x, rate, 0.55, color=C["orange"])
for r, v in zip(b, rate): ax.text(r.get_x() + r.get_width() / 2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(pxd); ax.set_ylabel("min por fichero"); ax.grid(axis="x", visible=False)
ax.set_title("Fig. 5c  Minutos por fichero")
finish(fig, "fig5_real_runs.png", "Fuente: docs/PIPELINE_RUN_LOG.md §9.4 (ejecución real en Windows, Orbitrap Fusion Lumos / LTQ Orbitrap Elite).")

# =========================================================================
# 6. Reduction ratio raw -> text, and batch groups
# =========================================================================
batches = {
    "PXD046034": [("3905_wt", 6), ("3905_fas", 6), ("3905_wt_Z", 6), ("3905_fas_Z", 6), ("4105_wt", 6), ("4105_fas", 6), ("4105_nap", 6), ("4105_fasnap", 6)],
    "PXD046788": [("Control_root", 6), ("Control_calli", 6), ("TSA_root", 6), ("TSA_calli", 5), ("NaB_root", 6), ("NaB_calli", 6), ("SAHA_root", 5), ("SAHA_calli", 6), ("Nicotinamide_root", 6), ("Nicotinamide_calli", 6)],
    "PXD014739": [("12d_light", 9), ("12d_dark", 9), ("3w_LD", 9), ("3w_SD", 9), ("5w_LD", 9), ("5w_SD", 9), ("7w_LD", 9), ("7w_SD", 9), ("bolting", 9), ("flowering", 9), ("silique_green", 6), ("silique_yellow", 9), ("senescing", 9)],
}
fig = plt.figure(figsize=(12, 6.2))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.6])
ax = fig.add_subplot(gs[0])
ratio = [(a + b) / r for a, b, r in zip(ms1_gb, ms2_gb, raw_gb)]
b = ax.bar(x, [100 * v for v in ratio], 0.55, color=C["blue"])
for r, v in zip(b, ratio): ax.text(r.get_x() + r.get_width() / 2, 100 * v, f"{100*v:.0f}%", ha="center", va="bottom", fontsize=9, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(pxd); ax.set_ylabel("% del tamaño raw"); ax.grid(axis="x", visible=False)
ax.set_title("Fig. 6a  .ms1+.ms2 como % del raw")
ax = fig.add_subplot(gs[1])
labels, vals, cols = [], [], []
colmap = dict(zip(pxd, [C["blue"], C["orange"], C["aqua"]]))
for p in pxd:
    for name, n in batches[p]:
        labels.append(name); vals.append(n); cols.append(colmap[p])
y = np.arange(len(labels))
ax.barh(y, vals, color=cols, height=0.7)
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7.5); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
ax.set_xlabel("muestras por batch"); ax.set_title("Fig. 6b  31 batches por condición (220 muestras)")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=colmap[p], label=p) for p in pxd], frameon=False, fontsize=8,
          loc="upper left", bbox_to_anchor=(1.01, 1.0))
finish(fig, "fig6_batches.png", "Fuente: docs/PIPELINE_RUN_LOG.md §10. Los batches son hard links (0 GB extra) listos para paras.txt raw_path.")

# ---- JSON summary for the report ----
summary = {"timings_s": tim, "inventory": {d: {"files": inv[d][0], "bytes": inv[d][1]} for d in order},
           "samples": len(samples), "complete_triads": int(M.all(axis=1).sum())}
(OUT / "smoke_summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))

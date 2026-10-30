#!/usr/bin/env python3
"""Fake MSConvert for smoke tests (no ProteoWizard needed).

Understands the two call styles used in this repo:
  msconvert <raw> --mzML --64 -o <dir> --outfile <name> --filter ...   (pxd_triada_pipeline.py)
  msconvert <raw> --filter ... --outdir <dir>                           (convert_and_extract.py)
Writes a small text placeholder named like the real output would be.
"""
import pathlib
import sys

a = sys.argv[1:]
raw = pathlib.Path(a[0])
if "-o" in a:
    out = pathlib.Path(a[a.index("-o") + 1])
elif "--outdir" in a:
    out = pathlib.Path(a[a.index("--outdir") + 1])
else:
    out = raw.parent
name = a[a.index("--outfile") + 1] if "--outfile" in a else f"{raw.stem}.mzML"
filters = [a[i + 1] for i, x in enumerate(a) if x == "--filter"]
out.mkdir(parents=True, exist_ok=True)
(out / name).write_text(
    f"<mzML source='{raw.name}' filters='{'|'.join(filters)}'>\n" + "spectrum\n" * 100
)
print(f"[fake msconvert] {raw.name} -> {out / name} filters={filters}")

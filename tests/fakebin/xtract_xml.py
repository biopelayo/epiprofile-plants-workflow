#!/usr/bin/env python3
import sys, pathlib
a = sys.argv[1:]; out = pathlib.Path(a[a.index("-o")+1]); mz = pathlib.Path(a[-1]); stem = mz.stem
assert mz.exists(), f"input missing: {mz}"
for suf, body in [(".ms1","S\t1\t1\n"), (".HCD.FTMS.ms2","S\t2\t2\n"), (".rawInfo","x"), (".xtract","x")]:
    (out/f"{stem}{suf}").write_text(body*10)
print(f"[fake xtract_xml] {mz.name} -> {stem}.ms1 + {stem}.HCD.FTMS.ms2")

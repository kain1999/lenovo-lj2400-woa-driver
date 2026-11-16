# -*- coding: utf-8 -*-
import glob, re
fs = sorted(glob.glob(r"E:\Deepseek\lj2400lin\deb_extract\uos_print\data.tar.xz.d\._usr_share_cups_model_lenovo_lenovo-*-cups-en.ppd"))
print("files:", len(fs), fs[0])
raw = open(fs[0], "rb").read()
print("head bytes:", raw[:40])
text = raw.decode("utf-8", errors="replace")
lines = text.splitlines()
hits = [l for l in lines if l.startswith("*PageSize")]
print("startswith hits:", len(hits))
for l in hits[:4]:
    print(repr(l))
pat = re.compile(r'\*PageSize\s+(\S+?)\s*/\s*"([^"]*)"')
ok = [pat.match(l) for l in hits]
print("regex matches:", sum(1 for m in ok if m))

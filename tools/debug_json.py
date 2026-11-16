# -*- coding: utf-8 -*-
import json
models = json.load(open(r"E:\Deepseek\lj2400lin\analysis\ppd_extract.json", encoding="utf-8"))
m = models[0]
print("keys:", sorted(m.keys()))
for k in sorted(m.keys()):
    v = m[k]
    if isinstance(v, (list, dict)):
        print("---", k, type(v).__name__, len(v))
        s = json.dumps(v, ensure_ascii=False)
        print(s[:600])
    else:
        print("---", k, "=", repr(v)[:120])

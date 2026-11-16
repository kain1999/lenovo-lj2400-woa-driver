#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_bisect2.py — 从全量静态 GPD 删减出 6 个变体, AddPrinter 二分定位 0x3EB 根因
B2: -Sleep  B3: -TonerSave  B4: -Constraints  B6: -CUSTOMSIZE系  B7: -CmdStartJob/StartDoc/EndJob  B8: 中文Name->英文
"""
import re, os

SRC = r"E:\Deepseek\lj2400woa\build\LJ2405D_static.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\bisect2"
os.makedirs(OUT, exist_ok=True)

text = open(SRC, encoding="utf-16").read()

def drop_feature(t, name):
    """按 *Feature: <name> { ... } 平衡括号删整段"""
    m = re.search(r'\*Feature:\s+%s\s*\{' % re.escape(name), t)
    if not m:
        return t
    i = m.end() - 1
    depth = 0
    j = i
    while j < len(t):
        if t[j] == '{':
            depth += 1
        elif t[j] == '}':
            depth -= 1
            if depth == 0:
                break
        j += 1
    return t[:m.start()] + t[j + 1:]

def drop_constraints(t):
    return re.sub(r'\*Constraints:.*\n', '', t)

ZH_MAP = {
    "黑白": "Mono", "纸张大小": "PaperSize", "分辨率": "Resolution", "介质类型": "MediaType",
    "纸张来源": "InputBin", "省墨模式": "TonerSave", "休眠时间[分]": "Sleep",
    "打印机默认值": "PrinterDefault", "双面打印": "Duplex", "单向打印": "Simplex",
    "双向打印(长边装订)": "FlipOnLongEdge", "双向打印(短边装订)": "FlipOnShortEdge",
}
def dezh(t):
    for k, v in ZH_MAP.items():
        t = t.replace('"%s"' % k, '"%s"' % v)
    return t

b2 = drop_feature(text, "Sleep")
b3 = drop_feature(b2, "TonerSave")
b4 = drop_constraints(text)
b6 = re.sub(r'(?s)\s+\*Option: (CUSTOM[123]|CustomMediaSize)\s*\{.*?\n    \}', '', b2)
b6 = re.sub(r',\s*(CUSTOM[123]|CustomMediaSize)(?=,|\))', '', b6)  # 清 DefaultOption/LIST 引用
b7 = re.sub(r'(?s)\*Command: CmdStartJob\s*\{.*?\n\}\n?', '', text)
b7 = re.sub(r'(?s)\*Command: CmdStartDoc\s*\{.*?\n\}\n?', '', b7)
b7 = re.sub(r'(?s)\*Command: CmdEndJob\s*\{.*?\n\}\n?', '', b7)
b8 = dezh(b2)

for name, body in (("B2_nosleep", b2), ("B3_notoner", b3), ("B4_noconst", b4),
                   ("B6_nocustom", b6), ("B7_nojobcmds", b7), ("B8_enname", b8)):
    open(os.path.join(OUT, name + ".gpd"), "wb").write(body.encode("utf-16"))
    print("OK", name, len(body))

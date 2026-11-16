#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_y4c.py — Y4c: Resolution 只留 600dpi; Y4d: Resolution 保留字段去命令"""
import re, os

SRC = r"E:\Deepseek\lj2400woa\build\inc8\Y4_res.gpd"
OUT = r"E:\Deepseek\lj2400woa\build\inc8"

t = open(SRC, encoding="ascii").read()

def feat_block(t, name):
    m = re.search(r'(\*Feature:\s+%s\s*\{)' % re.escape(name), t)
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
    return t[m.start():j + 1], m.start(), j + 1

res, s, e = feat_block(t, "Resolution")

# Y4c: 只留 600dpi 选项
head = res[:res.find('    *Option: 300dpi')]
o600 = res[res.find('    *Option: 600dpi'):]
o600 = o600[:o600.find('    }') + len('    }') + 1]
y4c_body = head + o600 + "\n}\n"
y4c = t[:s] + y4c_body + t[e:]

# Y4d: 去掉所有 *Command 行
y4d_body = re.sub(r'\s*\*Command:\s+\w+\s*\{[^}]*\}', '', res)
y4d = t[:s] + y4d_body + t[e:]

open(os.path.join(OUT, "Y4c_one.gpd"), "w", encoding="ascii", newline="\r\n").write(y4c)
open(os.path.join(OUT, "Y4d_nocmd.gpd"), "w", encoding="ascii", newline="\r\n").write(y4d)
print("OK Y4c/Y4d", len(y4c), len(y4d))

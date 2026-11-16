#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
model_reconcile.py —— 自检④：Setup\Program.cs 的 InfModelNames 常量表
与 E:\Deepseek\lj2400lin\analysis\ppd_extract.json 的 27 个 ModelName 逐一对账。

判定：集合一致（数量相同、无缺失、无多余）→ PASS；否则打印差异明细并 FAIL。
"""
import io
import json
import re
import sys

SRC = r"E:\Deepseek\lj2400woa\installer\Setup\Program.cs"
JSON_PATH = r"E:\Deepseek\lj2400lin\analysis\ppd_extract.json"


def extract_constants(src_text: str):
    m = re.search(r"InfModelNames\s*=\s*new string\[\]\s*\{(.*?)\};", src_text, re.S)
    if not m:
        return None
    return re.findall(r'"([^"]+)"', m.group(1))


def main():
    with io.open(SRC, "r", encoding="utf-8") as f:
        src = f.read()
    consts = extract_constants(src)
    if consts is None:
        print("[FAIL] 在 Program.cs 中找不到 InfModelNames 常量表")
        sys.exit(1)

    with io.open(JSON_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)
    models = ["Lenovo " + str(e.get("ModelName")).strip() for e in entries]

    set_c, set_m = set(consts), set(models)
    missing = [m for m in models if m not in set_c]   # JSON 有、常量缺
    extra = [c for c in consts if c not in set_m]     # 常量有、JSON 无

    print("常量表 %d 项 / JSON %d 项（ModelName + 'Lenovo ' 前缀）" % (len(consts), len(models)))
    if consts == models:
        print("[PASS] 顺序与内容完全一致（27 项逐一对账通过）")
        sys.exit(0 if len(models) == 27 else 1)
    if not missing and not extra and len(consts) == len(models):
        print("[PASS] 集合一致（顺序不同不影响 INF 匹配），项数 %d" % len(consts))
        sys.exit(0)
    for m in missing:
        print("  [缺失] %s（JSON 有、常量表没有）" % m)
    for e in extra:
        print("  [多余] %s（常量表有、JSON 没有）" % e)
    print("[FAIL] 对账不一致")
    sys.exit(1)


if __name__ == "__main__":
    main()

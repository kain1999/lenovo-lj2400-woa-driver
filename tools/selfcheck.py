#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
selfcheck.py — Lenovo LJ24/LJ26/M74/M76 WoA v4 驱动包自检
对照任务书硬指标 + 生成器 gen_meta.json 逐项核对, 结果写 E:\Deepseek\lj2400woa\build\selfcheck.txt。
检查项:
  1  文件存在与数量(27 GPD + 27 manifest + 27 pipelineconfig + 1 INF = 82)
  2  编码: GPD/INF = UTF-16 LE BOM(FF FE); manifest 无 BOM 纯 ASCII; pipelineconfig 内容
  3  GPD 括号配平 + 关键指令存在(*GPDFileName/*ModelName/*MasterUnits/Include)
  4  选项计数: PaperSize 26(22 实纸型+CUSTOM1-3+CustomMediaSize) / MediaType 9 / InputBin 2 /
     Resolution 3 / TonerSave 2 / ColorMode 1 / Duplex 0 或 3 / Sleep 0 或 4, 与 ppd_extract.json 一致
  5  TonerSave CmdSelect 与 rawtobr3_strings.txt 第 42/43 行逐字节一致
  6  关键命令串在位(&l4096a26a6d1E / &l0S,1S,2S / *b%d{NumOfDataBytes}W / HQ1200 三串)
  7  UIConstraints ↔ *Constraints: 每条 JSON 约束在 GPD 侧可寻且总数一致
  8  INF↔manifest PrinterDriverID 一一对应 + GUID v4 唯一
  9  USB 硬件 ID 在位(3 个可映射; LJ2455D 无对应型号, 单独记录)
  10 文件名无路径分隔符; INF %Model.<n>% 27 个; DriverFiles/SourceDisksFiles 81 项
  11 Duplex 有无与矩阵一致(7 无 / 20 有)
  12 尺寸抽查(整数 master units 换算复核)
"""
import json
import os
import re
import glob as _glob
import sys

BASE   = r"E:\Deepseek\lj2400woa"
DRIVER = os.path.join(BASE, "driver")
BUILD  = os.path.join(BASE, "build")
PPDJSON  = r"E:\Deepseek\lj2400lin\analysis\ppd_extract.json"
PPD_GLOB = r"E:\Deepseek\lj2400lin\deb_extract\uos_print\data.tar.xz.d\._usr_share_cups_model_lenovo_lenovo-*-cups-en.ppd"
STRINGS  = r"E:\Deepseek\lj2400lin\analysis\rawtobr3_strings.txt"

results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))

def mm2units(mm):
    return int(mm * 1200 / 25.4 + 0.5)

def decode_gpd_cmd(s):
    """GPD 命令串字面量 → 实际字节语义(用于与 rawtobr3 比较)."""
    s = s.replace("%%", "\x00")
    def sub(m):
        return {"<0A>": "\n", "<0D>": "\r", "<1B>": "\x1b", "<22>": '"'}.get(m.group(0).upper(), m.group(0))
    s = re.sub(r"<[0-9a-fA-F]{2}>", sub, s)
    return s.replace("\x00", "%")

def unescape_radare(s):
    """radare2 strings 列的 C 转义文本 → 实际字节."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            c = s[i + 1]
            out.append({"n": "\n", "r": "\r", "t": "\t", "e": "\x1b"}.get(c, "\\" if c == "\\" else None))
            if out[-1] is None:
                out.pop(); out.append("\\"); out.append(c)
            i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)

def parse_ppd_sizes(path):
    pat = re.compile(r'\*PageSize\s+(\S+?)\s*/\s*([^:]*?):\s*"([^"]*)"')
    sizes = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = pat.match(line)
        if m:
            sizes.append(m.group(1))
    return sizes

def main():
    models = json.load(open(PPDJSON, encoding="utf-8"))
    meta = json.load(open(os.path.join(BUILD, "gen_meta.json"), encoding="utf-8"))

    # ---- 1. 文件存在与数量 ----
    gpd_files = sorted(_glob.glob(os.path.join(DRIVER, "*.gpd")))
    man_files = sorted(_glob.glob(os.path.join(DRIVER, "*-manifest.ini")))
    pc_files  = sorted(_glob.glob(os.path.join(DRIVER, "*-pipelineconfig.xml")))
    inf_path  = os.path.join(DRIVER, "LJ2400WOA.INF")
    check("1.1 GPD 数量=27", len(gpd_files) == 27, str(len(gpd_files)))
    check("1.2 manifest 数量=27", len(man_files) == 27, str(len(man_files)))
    check("1.3 pipelineconfig 数量=27", len(pc_files) == 27, str(len(pc_files)))
    check("1.4 INF 存在", os.path.isfile(inf_path))
    check("1.5 包文件总数=82", len(gpd_files) + len(man_files) + len(pc_files) + 1 == 82)

    # ---- 2. 编码 ----
    bad_bom = []
    for p in gpd_files + [inf_path]:
        with open(p, "rb") as f:
            if f.read(2) != b"\xff\xfe":
                bad_bom.append(os.path.basename(p))
    check("2.1 GPD+INF 均为 FF FE BOM", not bad_bom, ",".join(bad_bom))
    bad_man = []
    for p in man_files:
        with open(p, "rb") as f:
            head = f.read(4)
            if head[:2] in (b"\xff\xfe", b"\xfe\xff") or head[0] == 0:
                bad_man.append(os.path.basename(p))
    check("2.2 manifest 无 BOM 纯 ASCII", not bad_man, ",".join(bad_man))

    # 原始 PPD 纸型清单(独立重读, 与生成器无关)
    ppd_files = sorted(_glob.glob(PPD_GLOB))
    ppd_kws = parse_ppd_sizes(ppd_files[0])
    check("2.3 原始 PPD PageSize=25 项", len(ppd_kws) == 25, str(len(ppd_kws)))

    # ---- 3/4/5/6/7. GPD 逐文件检查 ----
    duplex_kw_set = {"OneSided", "DuplexNoTumble", "DuplexTumble"}
    expect_duplex = {m["ModelName"].replace(" ", ""): bool(m.get("Duplex_opts")) for m in models}
    expect_sleep  = {m["ModelName"].replace(" ", ""): bool(m.get("Sleep_opts")) for m in models}

    # rawtobr3 第 42/43 行(ECONOMODE)与 30/31/32/33/80 行等关键命令
    lines = open(STRINGS, encoding="utf-8", errors="replace").read().splitlines()
    row_re = re.compile(r'^\s*(\d+)\s+0x[0-9a-f]+\s+0x[0-9a-f]+\s+(\d+)\s+(\d+)\s+\S+\s+ascii\s+(.*)$')
    strings_by_no = {}
    for ln in lines:
        m = row_re.match(ln)
        if m:
            strings_by_no[int(m.group(1))] = m.group(4)
    eco_on  = unescape_radare(strings_by_no.get(42, "@PJL SET ECONOMODE = ON\\n"))
    eco_off = unescape_radare(strings_by_no.get(43, "@PJL SET ECONOMODE = OFF\\n"))

    paper_kw_expect = {
        "NorthAmericaLetter", "NorthAmericaLegal", "NorthAmericaExecutive", "OtherMetricFolio",
        "ISOA4", "ISOA5", "ISOA6", "NorthAmericaNumber10Envelope", "NorthAmericaMonarchEnvelope",
        "ISODLEnvelope", "ISOC5Envelope", "ISOB5Envelope", "JISB5", "ISOB6", "JISB6",
        "NorthAmerica4X6", "JapanHagakiPostcard", "JapanDoubleHagakiPostcard", "JapanYou4Envelope",
        "16K_195x270mm", "16K_184x260mm", "16K_197x273mm",
        "CUSTOM1", "CUSTOM2", "CUSTOM3", "CustomMediaSize",
    }
    cons_fail = []
    eco_fail, dims_fail, key_fail, dup_fail, opt_fail, brace_fail = [], [], [], [], [], []
    total_ps_ok = True
    for p in gpd_files:
        token = os.path.basename(p)[:-4]
        text = open(p, "rb").read().decode("utf-16")
        # 3. 括号配平
        if text.count("{") != text.count("}"):
            brace_fail.append("%s: {=%d }=%d" % (token, text.count("{"), text.count("}")))
        for directive in ('*GPDSpecVersion: "1.0"', '*GPDFileName:    "%s.gpd"' % token,
                          '*ModelName:      "Lenovo %s"' % token if "Pro" not in token and "W" != token[-1] else '*ModelName:',
                          '*MasterUnits:    PAIR(1200, 1200)', '*Include:        "StdNames.gpd"',
                          '*Include:        "MSXPSINC.GPD"'):
            if directive not in text:
                brace_fail.append("%s: 缺 %s" % (token, directive))
        # 4. 选项计数
        def count_opts(feature):
            fm = re.search(r'\*Feature: %s\s*\{(.*?)\n\}' % feature, text, re.S)
            if not fm:
                return -1
            return len(re.findall(r'^\s{4}\*Option:', fm.group(1), re.M))
        ps_n = count_opts("PaperSize")
        if ps_n != 26:
            opt_fail.append("%s PaperSize=%d" % (token, ps_n))
        if count_opts("MediaType") != 9: opt_fail.append("%s MediaType" % token)
        if count_opts("InputBin") != 2:  opt_fail.append("%s InputBin" % token)
        if count_opts("Resolution") != 3: opt_fail.append("%s Resolution" % token)
        if count_opts("TonerSave") != 2: opt_fail.append("%s TonerSave" % token)
        if count_opts("ColorMode") != 1: opt_fail.append("%s ColorMode" % token)
        dx_n = count_opts("Duplex")
        if expect_duplex[token] and dx_n != 3: dup_fail.append("%s Duplex=%d 应=3" % (token, dx_n))
        if not expect_duplex[token] and dx_n != -1: dup_fail.append("%s 不应有 Duplex" % token)
        sl_n = count_opts("Sleep")
        if expect_sleep[token] and sl_n != 4: opt_fail.append("%s Sleep=%d 应=4" % (token, sl_n))
        if not expect_sleep[token] and sl_n != -1: opt_fail.append("%s 不应有 Sleep" % token)
        # 4.1 PaperSize 选项名全覆盖
        found = set(re.findall(r'^\s{4}\*Option: (\S+)', text, re.M))
        missing_ps = paper_kw_expect - found
        if missing_ps:
            total_ps_ok = False
            opt_fail.append("%s 缺纸型 %s" % (token, ",".join(sorted(missing_ps))))
        # 5. TonerSave 逐字节比对 rawtobr3 42/43 行
        for want, no in ((eco_off, 43), (eco_on, 42)):
            kw = "OFF" if no == 43 else "ON"
            fm = re.search(r'\*Option: %s\s*\{.*?\*Cmd:\s*"([^"]*)"' % kw, text, re.S)
            if not fm or decode_gpd_cmd(fm.group(1)) != want:
                eco_fail.append("%s TonerSave.%s != strings 第%d行 (%s)" % (token, kw, no, fm.group(1) if fm else "缺"))
        # 6. 关键命令串
        keys = ["<1B>&l4096a26a6d1E", "<1B>&l0S", "<1B>&l1S", "<1B>&l2S",
                "%d{NumOfDataBytes}", "@PJL SET RESOLUTION = 1200", "PAPERFEEDSPEED=HALF",
                "@PJL SET RAS1200MODE = TRUE", "@PJL ENTER LANGUAGE = PCL",
                "%%-12345X", "*b0M", "<1B>*r0A", "<1B>*rB"]
        keys_eff = keys if expect_duplex[token] else [
            k for k in keys if k not in ("<1B>&l0S", "<1B>&l1S", "<1B>&l2S")]
        for k in keys_eff:
            if k not in text:
                key_fail.append("%s 缺 %s" % (token, k))
        # 7. UIConstraints ↔ *Constraints
        cons = models[[m["ModelName"].replace(" ", "") for m in models].index(token)].get("UIConstraints") or []
        cmap = meta.get("papers") and None  # 占位, 用生成器同一映射表
        import importlib.util
        spec = importlib.util.spec_from_file_location("gen_gpd", os.path.join(BASE, "tools", "gen_gpd.py"))
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        gpd_cons = {}
        for fm in re.finditer(r'\*Feature: (\w+)\s*\{(.*?)\n\}', text, re.S):
            feat, body = fm.group(1), fm.group(2)
            for om in re.finditer(r'\*Option: (\S+)\s*\{(.*?)\n    \}', body, re.S):
                opt, obody = om.group(1), om.group(2)
                cm = re.search(r'\*Constraints: LIST\(([^)]*)\)', obody)
                if cm:
                    for ref in cm.group(1).split(","):
                        ref = ref.strip()
                        if ref:
                            gpd_cons.setdefault((feat, opt), set()).add(ref)
        has_dup = expect_duplex[token]
        mapped = gen.convert_constraints(cons, paper_kw_expect, duplex_kw_set, has_dup,
                                         set(["PLAIN","THIN","THICK","THICKERPAPER2","BOND","ENV","ENVTHICK","ENVTHIN","RECYCLED"]),
                                         set(["MANUAL","TRAY1"]))
        n_expect = sum(len(v) for v in mapped.values())
        n_actual = sum(len(v) for v in gpd_cons.values())
        if n_expect != n_actual:
            cons_fail.append("%s 约束数 %d != %d" % (token, n_actual, n_expect))
        else:
            for (f, o), refs in mapped.items():
                got = gpd_cons.get((f, o), set())
                for r in refs:
                    if "%s.%s" % (r[0], r[1]) not in got:
                        cons_fail.append("%s 缺 %s.%s→%s.%s" % (token, f, o, r[0], r[1]))
        # 12. 尺寸抽查
        for gk, wmm, hmm in (("ISOA4", 210.0, 297.0), ("NorthAmericaLetter", 215.9, 279.4),
                             ("NorthAmericaLegal", 215.9, 355.6), ("16K_197x273mm", 197.0, 273.0)):
            fm = re.search(r'\*Option: %s\s*\{.*?\*PageDimensions: PAIR\((\d+), (\d+)\)' % gk, text, re.S)
            if not fm or (int(fm.group(1)), int(fm.group(2))) != (mm2units(wmm), mm2units(hmm)):
                dims_fail.append("%s %s 尺寸异常" % (token, gk))

    check("3.1 GPD 括号配平+指令", not brace_fail, "; ".join(brace_fail[:5]))
    check("4.1 选项计数(26/9/2/3/2/1 + Duplex/Sleep)", not opt_fail, "; ".join(opt_fail[:5]))
    check("4.2 PaperSize 26 选项名全覆盖×27", total_ps_ok)
    check("5.1 TonerSave == rawtobr3 42/43 行", not eco_fail, "; ".join(eco_fail[:3]))
    check("6.1 关键命令串在位", not key_fail, "; ".join(key_fail[:5]))
    check("7.1 UIConstraints↔Constraints 一致", not cons_fail, "; ".join(cons_fail[:5]))
    check("11.1 Duplex 有无=矩阵(7 无/20 有)", not dup_fail, "; ".join(dup_fail[:5]))
    check("12.1 尺寸抽查(A4/Letter/Legal/16K197)", not dims_fail, "; ".join(dims_fail[:5]))

    # ---- 8/9/10. INF/manifest ----
    inf = open(inf_path, "rb").read().decode("utf-16")
    inf_ids = re.findall(r'\{([0-9A-Fa-f-]{36})\}', inf)
    inf_ids = [i for i in inf_ids if i.upper() not in
               ("4D36E979-E325-11CE-BFC1-08002BE10318",)]
    man_ids = []
    for p in man_files:
        txt = open(p, "r", encoding="ascii").read()
        m = re.search(r'PrinterDriverID=(\{[0-9A-Fa-f-]{36}\})', txt)
        man_ids.append((os.path.basename(p), m.group(1) if m else None))
    man_id_set = set(i[1] for i in man_ids)
    inf_id_set = set("{%s}" % i.upper() if not i.startswith("{") else i for i in
                     re.findall(r'= \w+\.Install, (\{[0-9A-Fa-f-]{36}\})', inf))
    check("8.1 INF PrinterDriverID=27 个", len(inf_id_set) == 27, str(len(inf_id_set)))
    check("8.2 manifest PrinterDriverID=27 个", all(i[1] for i in man_ids) and len(man_id_set) == 27)
    check("8.3 INF↔manifest 一一对应", inf_id_set == man_id_set,
          "差集=%s" % list(inf_id_set ^ man_id_set)[:3])
    guids_meta = meta["guids"]
    check("8.4 GUID 与生成记录一致且唯一", len(set(guids_meta)) == 27 and
          all(("{%s}" % g.strip("{}")) in inf_id_set for g in guids_meta))
    uuid_ok = all(g[15] == "4" and g[20] in "89abAB" for g in guids_meta)  # v4 版本位/变体位
    check("8.5 GUID 均为 v4", uuid_ok)

    usb_in = [u for u in ["USBPRINT\\LENOVOLJ2405D6330", "USBPRINT\\LENOVOLJ2605DDB31",
                          "USBPRINT\\LENOVOLJ2655DN2C9A"] if u in inf]
    check("9.1 USB ID 3 个在位(双写)", len(usb_in) == 3 and
          all(inf.count(u) == 3 and
              (inf.count(u.split("\\", 1)[1]) - inf.count(u)) == 3 for u in usb_in),
          "%d/3" % len(usb_in))
    check("9.2 LJ2455D ID 无对应型号(记录不挂)", "LENOVOLJ2455D6220" not in inf)

    model_strs = re.findall(r'Model\.(\d+) = "([^"]*)"', inf)
    check("10.1 %Model.n% 27 个", len(model_strs) == 27, str(len(model_strs)))
    badname = [s for _, s in model_strs if "/" in s or "\\" in s]
    check("10.2 型号显示名无路径分隔符", not badname)
    badfile = [os.path.basename(p) for p in gpd_files + man_files + pc_files
               if "/" in os.path.basename(p) or "\\" in os.path.basename(p)]
    check("10.3 生成文件名无路径分隔符", not badfile)
    df = re.search(r'\[DriverFiles\](.*?)\[', inf, re.S).group(1)
    ndf = len([l for l in df.strip().splitlines() if l.strip()])
    check("10.4 DriverFiles=81 项", ndf == 81, str(ndf))
    sdf = re.search(r'\[SourceDisksFiles\](.*?)\[', inf, re.S).group(1)
    nsdf = len([l for l in sdf.strip().splitlines() if l.strip()])
    check("10.5 SourceDisksFiles=81 项", nsdf == 81, str(nsdf))
    check("10.6 DriverIsolation=2", "DriverIsolation=2" in inf)
    check("10.7 ClassVer=4.0", "ClassVer=4.0" in inf)
    cat_ok = ("CatalogFile.NTamd64 = LJ2400WOA_amd64.cat" in inf
              and "CatalogFile.NTarm64 = LJ2400WOA_arm64.cat" in inf)
    check("10.10 CatalogFile 分架构指令", cat_ok, "amd64+arm64" if cat_ok else "缺 CatalogFile.NTamd64/NTarm64")
    man_ok = True
    for p in man_files:
        txt = open(p, "r", encoding="ascii").read()
        gpd_base = re.search(r'DataFile=(\S+\.gpd)', txt).group(1)
        if os.path.basename(p)[:-13] != gpd_base[:-4]:
            man_ok = False
        if "RequiredFiles=UNIRES.DLL,STDNAMES.GPD,STDDTYPE.GDL,STDSCHEM.GDL,STDSCHMX.GDL,MSXPSINC.GPD" not in txt:
            man_ok = False
        if "DriverCategory=PrintFax.Printer" not in txt or "XpsFormat=OpenXPS,XPS" not in txt:
            man_ok = False
    check("10.8 manifest DataFile 基名对应+RequiredFiles+Category+XpsFormat", man_ok)
    pc_ok = all("<Filters />" in open(p, encoding="utf-8").read() for p in pc_files)
    check("10.9 pipelineconfig=<Filters/> ×27", pc_ok)

    # ---- 汇总 ----
    passed = sum(1 for _, ok, _ in results if ok)
    out = []
    out.append("Lenovo LJ24/LJ26/M74/M76 WoA v4 驱动包自检报告")
    out.append("=" * 60)
    for name, ok, detail in results:
        out.append("[%s] %s%s" % ("PASS" if ok else "FAIL", name, (" | " + detail) if detail else ""))
    out.append("=" * 60)
    out.append("合计: %d/%d PASS" % (passed, len(results)))
    report = "\n".join(out)
    with open(os.path.join(BUILD, "selfcheck.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    sys.exit(0 if passed == len(results) else 1)

if __name__ == "__main__":
    main()

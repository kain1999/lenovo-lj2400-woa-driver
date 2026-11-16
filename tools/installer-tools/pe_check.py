#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pe_check.py —— 自检①②：确认 exe 为 MSIL AnyCPU（WoA/ARM64 与 x64 通用）

判定标准（CLR 可执行 PE）：
  COFF Machine      = 0x014C (I386)
  OptionalHeader Magic = 0x010B (PE32)
  DataDirectory[14]（CLR Runtime Header）非零
  COR20 Header Flags = ILONLY(0x1) 置位 且 32BITREQUIRED(0x2) 清零

AnyCPU 且无 32BITPREFERRED(0x00020000) → 任意架构按本机 64 位 JIT。
"""
import struct
import sys


def check(path: str) -> bool:
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"MZ":
        print("[FAIL] %s 不是 PE（缺少 MZ）" % path)
        return False
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        print("[FAIL] %s 缺少 PE 签名" % path)
        return False

    coff = e_lfanew + 4
    machine, num_sections, _, _, _, opt_size, _ = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]

    dirs_off = opt + (96 if magic == 0x10B else 112)  # PE32=96 / PE32+=112 字节后为数据目录
    clr_rva, clr_size = struct.unpack_from("<II", data, dirs_off + 14 * 8)  # 目录项 14 = CLR Runtime Header

    ok = True
    if machine != 0x014C:
        print("[FAIL] Machine=0x%04X（期望 0x014C I386）" % machine)
        ok = False
    if magic != 0x10B:
        print("[FAIL] OptionalHeader Magic=0x%04X（期望 0x010B PE32）" % magic)
        ok = False
    if clr_size == 0 or clr_rva == 0:
        print("[FAIL] CLR 目录为空（不是 .NET 程序集）")
        ok = False
    else:
        # CLR 头在节内，用 RVA→文件偏移粗换算（.NET 单一映像下第一个节通常够用）
        sec_off = opt + opt_size
        file_off = None
        for i in range(num_sections):
            base = sec_off + i * 40
            name = data[base:base + 8].rstrip(b"\0")
            vsize, vrva, rsize, roff = struct.unpack_from("<IIII", data, base + 8)
            if vrva <= clr_rva < vrva + max(vsize, rsize):
                file_off = roff + (clr_rva - vrva)
                break
        if file_off is None:
            print("[FAIL] 找不到 CLR 头所在节")
            ok = False
        else:
            # IMAGE_COR20_HEADER: DWORD cb(4) Major(2) Minor(2) MetaData 目录(8) → Flags 在偏移 +16
            flags = struct.unpack_from("<I", data, file_off + 16)[0]
            ilonly = flags & 0x1
            bit32 = flags & 0x2
            pref32 = flags & 0x00020000
            print("CLR Flags=0x%08X  ILONLY=%s  32BITREQUIRED=%s  32BITPREFERRED=%s"
                  % (flags, bool(ilonly), bool(bit32), bool(pref32)))
            if not ilonly:
                print("[FAIL] 未置 ILONLY（混合原生代码）")
                ok = False
            if bit32:
                print("[FAIL] 置了 32BITREQUIRED（x86 专属）")
                ok = False
            if pref32:
                print("[WARN] 置了 32BITPREFERRED（WoA 上会走 x86 模拟）")
                ok = False
    if ok:
        print("[PASS] %s 是 MSIL AnyCPU（ARM64/x64 通用）" % path)
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python pe_check.py <exe1> [exe2 ...]")
        sys.exit(2)
    all_ok = True
    for p in sys.argv[1:]:
        all_ok = check(p) and all_ok
    sys.exit(0 if all_ok else 1)

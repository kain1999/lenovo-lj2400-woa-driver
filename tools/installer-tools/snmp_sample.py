#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snmp_sample.py —— LJ24/LJ26/M74/M76 真机 SNMP 采样工具（校准 LJ2400Manager 墨粉阈值用）

用途：用户接真机后跑一遍，把响应 JSON 交给开发侧，用于校准 Manager 的
      Brother 私有 OID 语义与墨粉百分比阈值。

用法：
  python snmp_sample.py --ip 192.168.1.100
  python snmp_sample.py --ip 192.168.1.100 --out result.json
  python snmp_sample.py --ip 192.168.1.100 --table E:\\Deepseek\\lj2655win\\analysis\\oid_table.txt

实现：手写 socket + ASN.1/BER（无 pysnmp，无任何第三方依赖），SNMPv1 GET，
      community 默认 public，超时 3 秒重试 2 次。
输出：JSON（oid/value/type/timestamp）到 stdout 与 --out 文件。

python: 3.13（C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python313\\python.EXE）
"""

import argparse
import json
import socket
import sys
import time

# 标准 MIB（hrDevice / hrPrinter / Printer-MIB 页数与耗材）
STANDARD_OIDS = [
    "1.3.6.1.2.1.25.3.2.1.3.1",     # hrDeviceDescr   型号
    "1.3.6.1.2.1.25.3.2.1.7.1",     # hrDeviceStatus  设备状态
    "1.3.6.1.2.1.25.3.5.1.1.1",     # hrPrinterStatus 打印机状态
    "1.3.6.1.2.1.25.3.5.1.2.1",     # hrPrinterDetectedErrorState
    "1.3.6.1.2.1.43.10.2.1.4.1.1",  # prtMarkerLifeCount 总页数
    "1.3.6.1.2.1.43.11.1.1.6.1.1",  # prtSuppliesDescription 耗材描述
    "1.3.6.1.2.1.43.11.1.1.9.1.1",  # prtSuppliesLevel    耗材余量
]

SNMP_PORT = 161


# ---------------------------------------------------------------------------
# BER 编码（发送侧）
# ---------------------------------------------------------------------------
def encode_tlv(tag: int, payload: bytes) -> bytes:
    return bytes([tag]) + encode_length(len(payload)) + payload


def encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    body = b""
    while n > 0:
        body = bytes([n & 0xFF]) + body
        n >>= 8
    return bytes([0x80 | len(body)]) + body


def encode_int(value: int) -> bytes:
    # 有符号整数最小长度编码
    if value == 0:
        return b"\x00"
    data = value.to_bytes((value.bit_length() // 8) + 1, "big", signed=True)
    # 去掉冗余前导字节（保留符号位）
    while len(data) > 1:
        if data[0] == 0x00 and (data[1] & 0x80) == 0:
            data = data[1:]
            continue
        if data[0] == 0xFF and (data[1] & 0x80) != 0:
            data = data[1:]
            continue
        break
    return data


def encode_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.split(".")]
    body = encode_subid(parts[0] * 40 + parts[1])
    for p in parts[2:]:
        body += encode_subid(p)
    return body


def encode_subid(value: int) -> bytes:
    out = bytes([value & 0x7F])
    value >>= 7
    while value > 0:
        out = bytes([(value & 0x7F) | 0x80]) + out
        value >>= 7
    return out


def build_get(request_id: int, community: str, oid: str) -> bytes:
    varbind = encode_tlv(0x30, encode_tlv(0x06, encode_oid(oid)) + encode_tlv(0x05, b""))
    pdu_body = (encode_tlv(0x02, encode_int(request_id))
                + encode_tlv(0x02, encode_int(0))       # error-status
                + encode_tlv(0x02, encode_int(0))       # error-index
                + encode_tlv(0x30, varbind))
    msg_body = (encode_tlv(0x02, encode_int(0))         # version = 0 (SNMPv1)
                + encode_tlv(0x04, community.encode("ascii"))
                + encode_tlv(0xA0, pdu_body))
    return encode_tlv(0x30, msg_body)


# ---------------------------------------------------------------------------
# BER 解码（接收侧）
# ---------------------------------------------------------------------------
def ber_iter(data: bytes, start: int, end: int):
    """迭代 (tag, value_bytes)，位置推进到 end 为止。"""
    pos = start
    while pos < end:
        tag = data[pos]
        pos += 1
        b = data[pos]
        pos += 1
        if b < 0x80:
            length = b
        else:
            count = b & 0x7F
            length = 0
            for _ in range(count):
                length = (length << 8) | data[pos]
                pos += 1
        yield tag, data[pos:pos + length]
        pos += length


def decode_oid(raw: bytes) -> str:
    ids = []
    val = 0
    for b in raw:
        val = (val << 7) | (b & 0x7F)
        if not (b & 0x80):
            ids.append(val)
            val = 0
    if not ids:
        return ""
    first = ids[0]
    rest = [first // 40, first % 40] + ids[1:]
    return ".".join(str(x) for x in rest)


def decode_value(tag: int, raw: bytes):
    """返回 (类型名, 字符串值)。"""
    if tag == 0x02:
        if raw:
            sign = -1 if (raw[0] & 0x80) else 1
            v = int.from_bytes(raw, "big", signed=False)
            if sign < 0:
                v = v - (1 << (len(raw) * 8))
            return "INTEGER", str(v)
        return "INTEGER", "0"
    if tag == 0x04:
        printable = bool(raw) and all(b >= 0x20 or b in (9, 10, 13) for b in raw)
        if printable:
            return "OCTET STRING", raw.decode("utf-8", "replace")
        return "OCTET STRING", raw.hex(" ")
    if tag == 0x05:
        return "NULL", ""
    if tag == 0x06:
        return "OID", decode_oid(raw)
    if tag == 0x40:
        if len(raw) == 4:
            return "IPAddress", ".".join(str(b) for b in raw)
        return "IPAddress", raw.hex(" ")
    if tag == 0x41:
        return "Counter", str(int.from_bytes(raw, "big"))
    if tag == 0x42:
        return "Gauge", str(int.from_bytes(raw, "big"))
    if tag == 0x43:
        ticks = int.from_bytes(raw, "big")
        return "TimeTicks", "%d (约 %.1f 秒)" % (ticks, ticks / 100.0)
    if tag == 0x44:
        return "Opaque", raw.hex(" ")
    if tag == 0x46:
        return "Counter64", str(int.from_bytes(raw, "big"))
    return "0x%02X" % tag, raw.hex(" ")


SNMP_ERRORS = {1: "tooBig", 2: "noSuchName", 3: "badValue", 4: "readOnly",
               5: "genErr", 6: "noAccess", 7: "wrongType", 8: "wrongLength",
               9: "wrongEncoding", 10: "wrongValue", 11: "noCreation",
               12: "inconsistentValue", 13: "resourceUnavailable",
               14: "commitFailed", 15: "undoFailed", 16: "authorizationError",
               17: "notWritable", 18: "inconsistentName"}


def parse_response(packet: bytes):
    """SNMPv1 GetResponse 解析 → (error_status_name, [(oid, type_name, value_str), ...])"""
    outer = list(ber_iter(packet, 0, len(packet)))
    if not outer or outer[0][0] != 0x30:
        raise ValueError("响应缺少顶层 SEQUENCE")
    _, body = outer[0]
    fields = list(ber_iter(body, 0, len(body)))
    if len(fields) < 3 or fields[2][0] != 0xA2:
        raise ValueError("响应 PDU 类型异常（期望 GetResponse 0xA2）")
    _, pdu = fields[2]
    pd = list(ber_iter(pdu, 0, len(pdu)))
    if len(pd) < 4:
        raise ValueError("PDU 字段不足")
    err_status = int.from_bytes(pd[1][1], "big") if pd[1][1] else 0
    _, vbl = pd[3]
    result = []
    for tag, vb in ber_iter(vbl, 0, len(vbl)):
        pair = list(ber_iter(vb, 0, len(vb)))
        if len(pair) < 2:
            continue
        oid = decode_oid(pair[0][1])
        tname, value = decode_value(pair[1][0], pair[1][1])
        result.append((oid, tname, value))
    return err_status, result


def snmp_get(ip: str, community: str, oid: str, timeout: float, retries: int):
    """单 OID GET；失败返回 (None, 错误信息)。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    last_err = None
    try:
        for _ in range(retries + 1):
            try:
                sock.sendto(build_get(int(time.time()) % 0x7FFFFFF0, community, oid), (ip, SNMP_PORT))
                data, _ = sock.recvfrom(4096)
                err, vars_ = parse_response(data)
                if err != 0:
                    return None, SNMP_ERRORS.get(err, "SNMP错误码%d" % err)
                for v_oid, tname, value in vars_:
                    if v_oid == oid:
                        return (tname, value), None
                return (vars_[0][1], vars_[0][2]) if vars_ else (None, "响应缺少 VarBind")
            except socket.timeout:
                last_err = "超时（%.1fs）" % timeout
            except OSError as e:
                last_err = "网络错误：%s" % e
        return None, last_err or "无响应"
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# OID 表加载：取全部 1.3.6.1.4.1.2435.*（含 .63/.67/.99/.64/.68 分支），
# 去尾部句点（字符串区提取时的通配前缀残留）、去重，附加标准 MIB。
# ---------------------------------------------------------------------------
def load_oids(table_path: str):
    brother = []
    if table_path:
        try:
            with open(table_path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    if not s.startswith("1.3.6.1.4.1.2435"):
                        continue
                    s = s.rstrip(".")
                    if s and s not in brother:
                        brother.append(s)
        except OSError as e:
            print("[警告] OID 表读取失败：%s（仅用标准 MIB）" % e, file=sys.stderr)
    return brother, STANDARD_OIDS


def main():
    ap = argparse.ArgumentParser(description="LJ24/LJ26/M74/M76 真机 SNMP 采样（手写 BER，无第三方依赖）")
    ap.add_argument("--ip", required=True, help="打印机 IP 地址")
    ap.add_argument("--out", default=None, help="JSON 输出文件路径（缺省只打 stdout）")
    ap.add_argument("--community", default="public", help="SNMP community（默认 public）")
    ap.add_argument("--table", default=r"E:\Deepseek\lj2655win\analysis\oid_table.txt",
                    help="Brother OID 全表路径（oid_table.txt）")
    ap.add_argument("--timeout", type=float, default=3.0, help="单次超时秒数（默认 3）")
    ap.add_argument("--retries", type=int, default=2, help="重试次数（默认 2）")
    args = ap.parse_args()

    brother, standard = load_oids(args.table)
    all_oids = standard + brother
    print("[i] 共 %d 个 OID（标准 %d + Brother 私有 %d），开始逐个 GET：%s"
          % (len(all_oids), len(standard), len(brother), args.ip), file=sys.stderr)

    results = []
    ok_count = 0
    for i, oid in enumerate(all_oids, 1):
        got, err = snmp_get(args.ip, args.community, oid, args.timeout, args.retries)
        rec = {"oid": oid, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        if got:
            tname, value = got
            rec.update({"ok": True, "type": tname, "value": value})
            ok_count += 1
            print("[%d/%d] %s = %r (%s)" % (i, len(all_oids), oid, value, tname))
        else:
            rec.update({"ok": False, "value": None, "error": err})
            print("[%d/%d] %s → 无响应（%s）" % (i, len(all_oids), oid, err), file=sys.stderr)
        results.append(rec)

    out = {
        "ip": args.ip,
        "community": args.community,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {"total": len(all_oids), "responded": ok_count},
        "results": results,
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("[i] 已写入 %s（响应 %d/%d）" % (args.out, ok_count, len(all_oids)), file=sys.stderr)


if __name__ == "__main__":
    main()

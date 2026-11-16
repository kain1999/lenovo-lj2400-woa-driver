// ============================================================================
// LJ2400Manager.exe —— 联想 LJ24/LJ26/M74/M76 打印机管理工具
// Windows on ARM / x64 通用（AnyCPU，纯 .NET Framework WinForms，零第三方依赖）
//
// 功能：
//   1. 本机队列枚举（winspool EnumPrinters，LOCAL + CONNECTIONS）
//   2. SNMPv1 客户端 —— 手写 ASN.1/BER 编解码（UDP 161，community "public"，
//      超时 3 秒 × 重试 2 次，OID→值解析），禁止第三方库
//   3. PJL 客户端 —— TcpClient 9100，@PJL INFO STATUS / @PJL DINQUIRE SERIALNUMPRN
//   4. 状态显示：标准 hrDevice/PrinterMIB + Brother 私有分支（1.3.6.1.4.1.2435.*，
//      含 .63/.67/.99/.64/.68 分支，OID 表来自 lj2655win\analysis\oid_table.txt）
//   5. 墨粉/纸盒/保密箱分组 + 智能猜测（0-100 显示 ≈N%，阈值待真机校准）
//   6. 打印测试页 / 设备 Web 管理 / 导出状态报告(JSON)
//
// 编译（唯一编译链）：
//   C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
//     /target:winexe /platform:anycpu /out:dist\LJ2400Manager.exe Manager\Manager.cs
// ============================================================================

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

namespace LenovoLJ2400Manager
{
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ManagerForm());
        }
    }

    // ==========================================================================
    // winspool P/Invoke：EnumPrinters / OpenPrinter / GetPrinter(2) / ClosePrinter
    // ==========================================================================
    internal static class WinspoolNative
    {
        public const int PRINTER_ENUM_LOCAL = 0x00000002;
        public const int PRINTER_ENUM_CONNECTIONS = 0x00000004;

        [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool EnumPrinters(int flags, string name, int level, IntPtr pPrinterEnum, int cbBuf,
            out int pcbNeeded, out int pcReturned);

        [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);

        [DllImport("winspool.drv", SetLastError = true)]
        public static extern bool ClosePrinter(IntPtr hPrinter);

        [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool GetPrinter(IntPtr hPrinter, int level, IntPtr pBuffer, int cbBuf, out int pcbNeeded);

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        public struct PRINTER_INFO_2
        {
            public string pServerName;
            public string pPrinterName;
            public string pShareName;
            public string pPortName;
            public string pDriverName;
            public string pComment;
            public string pLocation;
            public IntPtr pDevMode;
            public IntPtr pSepFile;
            public string pPrintProcessor;
            public string pDatatype;
            public string pParameters;
            public IntPtr pSecurityDescriptor;
            public uint Attributes;
            public uint Priority;
            public uint DefaultPriority;
            public uint StartTime;
            public uint UntilTime;
            public uint Status;
            public uint cJobs;
            public uint AveragePPM;
        }

        // 枚举本机队列 + 已连接队列
        public static List<PRINTER_INFO_2> EnumLocalPrinters()
        {
            List<PRINTER_INFO_2> list = new List<PRINTER_INFO_2>();
            int needed, returned;
            int flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS;
            EnumPrinters(flags, null, 2, IntPtr.Zero, 0, out needed, out returned);
            if (needed <= 0) return list;
            IntPtr buf = Marshal.AllocHGlobal(needed);
            try
            {
                if (!EnumPrinters(flags, null, 2, buf, needed, out needed, out returned)) return list;
                int size = Marshal.SizeOf(typeof(PRINTER_INFO_2));
                for (int i = 0; i < returned; i++)
                {
                    IntPtr item = IntPtr.Add(buf, i * size);
                    list.Add((PRINTER_INFO_2)Marshal.PtrToStructure(item, typeof(PRINTER_INFO_2)));
                }
            }
            finally { Marshal.FreeHGlobal(buf); }
            return list;
        }

        // 读取指定队列的 PRINTER_INFO_2；失败返回 null
        public static PRINTER_INFO_2? GetPrinterInfo2(string printerName)
        {
            IntPtr h;
            if (!OpenPrinter(printerName, out h, IntPtr.Zero)) return null;
            try
            {
                int needed = 0;
                GetPrinter(h, 2, IntPtr.Zero, 0, out needed);
                if (needed <= 0) return null;
                IntPtr buf = Marshal.AllocHGlobal(needed);
                try
                {
                    int written;
                    if (!GetPrinter(h, 2, buf, needed, out written)) return null;
                    return (PRINTER_INFO_2)Marshal.PtrToStructure(buf, typeof(PRINTER_INFO_2));
                }
                finally { Marshal.FreeHGlobal(buf); }
            }
            finally { ClosePrinter(h); }
        }
    }

    // ==========================================================================
    // SNMPv1 客户端：手写 ASN.1/BER（UDP 161）。零第三方依赖。
    //   编码：SEQUENCE{ version=0, community, GetRequest-PDU[0xA0]{ id, err, idx, VarBindList } }
    //   解码：GetResponse-PDU[0xA2] → VarBindList → (OID, value)
    //   类型标签：02 INTEGER / 04 STRING / 05 NULL / 06 OID / 40 IPAddress /
    //            41 Counter / 42 Gauge / 43 TimeTicks / 44 Opaque / 46 Counter64
    // ==========================================================================
    internal class SnmpClient
    {
        private readonly string _ip;
        private readonly string _community;
        private readonly int _timeoutMs;
        private readonly int _retries;
        private int _requestId;
        private readonly Random _rand = new Random();

        public SnmpClient(string ip, string community, int timeoutMs, int retries)
        {
            _ip = ip;
            _community = string.IsNullOrEmpty(community) ? "public" : community;
            _timeoutMs = timeoutMs <= 0 ? 3000 : timeoutMs;
            _retries = retries < 0 ? 2 : retries;
            _requestId = _rand.Next(1, 0x7FFFFFF0);
        }

        public class SnmpVar
        {
            public string Oid;
            public byte TypeTag;
            public string TypeName;   // 类型名（INTEGER / OCTET STRING / ...）
            public string Value;      // 解码后的值（无响应时为 null）
        }

        // 单个 OID GET（VarBindList 只放一条，最稳妥；批量会因单个 OID 不支持而整体失败）
        public SnmpVar Get(string oid)
        {
            byte[] req = BuildGetRequest(new string[] { oid });
            byte[] resp = UdpExchange(req);
            SnmpVar v = ParseGetResponse(resp);
            if (string.IsNullOrEmpty(v.Oid)) v.Oid = oid;
            return v;
        }

        // ---------- BER 编码 ----------
        private static byte[] Tlv(byte tag, byte[] value)
        {
            byte[] len = EncodeLength(value.Length);
            byte[] outBuf = new byte[1 + len.Length + value.Length];
            outBuf[0] = tag;
            Buffer.BlockCopy(len, 0, outBuf, 1, len.Length);
            Buffer.BlockCopy(value, 0, outBuf, 1 + len.Length, value.Length);
            return outBuf;
        }

        private static byte[] EncodeLength(int length)
        {
            if (length < 0x80) return new byte[] { (byte)length };
            List<byte> bytes = new List<byte>();
            int v = length;
            while (v > 0) { bytes.Insert(0, (byte)(v & 0xFF)); v >>= 8; }
            byte[] outBuf = new byte[bytes.Count + 1];
            outBuf[0] = (byte)(0x80 | bytes.Count);
            for (int i = 0; i < bytes.Count; i++) outBuf[1 + i] = bytes[i];
            return outBuf;
        }

        private static byte[] EncodeInteger(int value)
        {
            byte[] bytes = BitConverter.GetBytes(value); // 小端
            if (BitConverter.IsLittleEndian) Array.Reverse(bytes);
            // 去掉冗余前导字节（保留符号位）
            int i = 0;
            while (i < bytes.Length - 1 &&
                ((bytes[i] == 0x00 && (bytes[i + 1] & 0x80) == 0) ||
                 (bytes[i] == 0xFF && (bytes[i + 1] & 0x80) != 0))) i++;
            byte[] trimmed = new byte[bytes.Length - i];
            Array.Copy(bytes, i, trimmed, 0, trimmed.Length);
            return trimmed;
        }

        private static byte[] EncodeOid(string oid)
        {
            string[] parts = oid.Split('.');
            if (parts.Length < 2) throw new ArgumentException("OID 格式错误：" + oid);
            int first = int.Parse(parts[0]);
            int second = int.Parse(parts[1]);
            List<byte> body = new List<byte>();
            AppendSubId(body, first * 40 + second);
            for (int i = 2; i < parts.Length; i++) AppendSubId(body, int.Parse(parts[i]));
            return body.ToArray();
        }

        private static void AppendSubId(List<byte> body, int value)
        {
            // base-128 编码，高位为延续位
            byte[] tmp = new byte[5];
            int n = 0;
            tmp[n++] = (byte)(value & 0x7F);
            value >>= 7;
            while (value > 0) { tmp[n++] = (byte)((value & 0x7F) | 0x80); value >>= 7; }
            for (int i = n - 1; i >= 0; i--) body.Add(tmp[i]);
        }

        // 不定参拼接（BuildGetRequest 需要拼 2/3/4 段 BER）
        private static byte[] Concat(params byte[][] parts)
        {
            int total = 0;
            foreach (byte[] p in parts) total += p.Length;
            byte[] outBuf = new byte[total];
            int off = 0;
            foreach (byte[] p in parts)
            {
                Buffer.BlockCopy(p, 0, outBuf, off, p.Length);
                off += p.Length;
            }
            return outBuf;
        }

        private byte[] BuildGetRequest(string[] oids)
        {
            _requestId++;
            List<byte> varbinds = new List<byte>();
            foreach (string oid in oids)
            {
                byte[] name = Tlv(0x06, EncodeOid(oid));
                byte[] nul = Tlv(0x05, new byte[0]);
                varbinds.AddRange(Tlv(0x30, Concat(name, nul)));
            }
            byte[] pduBody = Concat(
                Tlv(0x02, EncodeInteger(_requestId)), // request-id
                Tlv(0x02, EncodeInteger(0)),          // error-status = 0
                Tlv(0x02, EncodeInteger(0)),          // error-index  = 0
                Tlv(0x30, varbinds.ToArray()));
            byte[] pdu = Tlv(0xA0, pduBody);          // GetRequest [APPLICATION 0]
            byte[] msgBody = Concat(
                Tlv(0x02, EncodeInteger(0)),          // version: SNMPv1 = 0
                Tlv(0x04, Encoding.ASCII.GetBytes(_community)),
                pdu);
            return Tlv(0x30, msgBody);
        }

        // ---------- UDP 收发（超时 3 秒 × 重试 2 次）----------
        private static IPAddress ResolveHost(string host)
        {
            IPAddress ip;
            if (IPAddress.TryParse(host, out ip)) return ip;
            return Dns.GetHostAddresses(host)[0];
        }

        private byte[] UdpExchange(byte[] packet)
        {
            Exception last = null;
            int attempts = _retries + 1;
            for (int attempt = 0; attempt < attempts; attempt++)
            {
                try
                {
                    using (Socket udp = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp))
                    {
                        udp.ReceiveTimeout = _timeoutMs;
                        udp.SendTimeout = _timeoutMs;
                        IPEndPoint ep = new IPEndPoint(ResolveHost(_ip), 161);
                        udp.SendTo(packet, ep);
                        byte[] buf = new byte[4096];
                        EndPoint remote = (EndPoint)new IPEndPoint(IPAddress.Any, 0);
                        int n = udp.ReceiveFrom(buf, ref remote);
                        byte[] outBuf = new byte[n];
                        Array.Copy(buf, outBuf, n);
                        return outBuf;
                    }
                }
                catch (Exception ex) { last = ex; }
            }
            throw new Exception("SNMP 无响应（超时 " + _timeoutMs + "ms × " + attempts + " 次）：" +
                (last == null ? "未知错误" : last.Message));
        }

        // ---------- BER 解码 ----------
        private class BerReader
        {
            public byte[] Data;
            public int Pos;
            public int End;
            public byte Tag;
            public int ValueStart;
            public int ValueLen;

            public BerReader(byte[] data) { Data = data; Pos = 0; End = data.Length; }

            // 在当前 TLV 的 value 区间上开一个子读取器
            public BerReader SubReader()
            {
                BerReader r = new BerReader(Data);
                r.Pos = ValueStart;
                r.End = ValueStart + ValueLen;
                return r;
            }

            public bool ReadNext()
            {
                if (Pos >= End) return false;
                Tag = Data[Pos];
                Pos++;
                int len = ReadLength();
                if (Pos + len > End) throw new Exception("BER 长度越界");
                ValueStart = Pos;
                ValueLen = len;
                Pos = ValueStart + len;
                return true;
            }

            private int ReadLength()
            {
                if (Pos >= End) throw new Exception("BER 长度越界");
                int b = Data[Pos];
                Pos++;
                if (b < 0x80) return b;
                int count = b & 0x7F;
                if (count == 0 || Pos + count > End) throw new Exception("BER 长度格式错误");
                int len = 0;
                for (int i = 0; i < count; i++) { len = (len << 8) | Data[Pos]; Pos++; }
                return len;
            }

            public byte[] ValueBytes()
            {
                byte[] v = new byte[ValueLen];
                Array.Copy(Data, ValueStart, v, 0, ValueLen);
                return v;
            }
        }

        private SnmpVar ParseGetResponse(byte[] packet)
        {
            BerReader top = new BerReader(packet);
            if (!top.ReadNext() || top.Tag != 0x30) throw new Exception("SNMP 响应缺少顶层 SEQUENCE");
            BerReader body = top.SubReader();
            body.ReadNext();                                   // INTEGER version
            body.ReadNext();                                   // OCTET STRING community
            if (!body.ReadNext() || body.Tag != 0xA2)
                throw new Exception("SNMP 响应 PDU 类型异常：0x" + body.Tag.ToString("X2"));
            BerReader pdu = body.SubReader();
            pdu.ReadNext();                                    // request-id
            pdu.ReadNext();                                    // error-status
            int errStatus = (int)DecodeUnsigned(pdu.ValueBytes());
            pdu.ReadNext();                                    // error-index
            if (!pdu.ReadNext() || pdu.Tag != 0x30) throw new Exception("SNMP 响应缺少 VarBind 列表");
            BerReader vbl = pdu.SubReader();
            SnmpVar first = null;
            while (vbl.ReadNext())
            {
                BerReader vb = vbl.SubReader();
                vb.ReadNext();                                 // OID
                string oid = DecodeOid(vb.ValueBytes());
                vb.ReadNext();                                 // value
                byte vt = vb.Tag;
                string tn;
                string val = DecodeValue(vt, vb.ValueBytes(), out tn);
                SnmpVar v = new SnmpVar();
                v.Oid = oid;
                v.TypeTag = vt;
                v.TypeName = tn;
                v.Value = val;
                if (first == null) first = v;
            }
            if (first == null) throw new Exception("SNMP 响应没有 VarBind");
            if (errStatus != 0)
            {
                // 2=noSuchName：该 OID 设备不支持；其余见 RFC1157。统一按「无响应值」处理
                first.TypeName = "SNMP错误码" + errStatus;
                first.Value = null;
            }
            return first;
        }

        private static ulong DecodeUnsigned(byte[] v)
        {
            ulong r = 0;
            foreach (byte b in v) r = (r << 8) | b;
            return r;
        }

        private static long DecodeIntegerSigned(byte[] v)
        {
            if (v.Length == 0) return 0;
            long r = (v[0] & 0x80) != 0 ? -1 : 0; // 符号扩展
            foreach (byte b in v) r = (r << 8) | b;
            return r;
        }

        private static string DecodeOid(byte[] v)
        {
            if (v.Length == 0) return "";
            List<ulong> ids = new List<ulong>();
            ulong val = 0;
            foreach (byte b in v)
            {
                val = (val << 7) | (uint)(b & 0x7F); // (uint) 隐式零扩展到 ulong，避免符号扩展告警
                if ((b & 0x80) == 0) { ids.Add(val); val = 0; }
            }
            if (ids.Count == 0) return "";
            long first = (long)ids[0];
            long a = first / 40;
            long b2 = first % 40;
            StringBuilder sb = new StringBuilder();
            sb.Append(a).Append('.').Append(b2);
            for (int i = 1; i < ids.Count; i++) sb.Append('.').Append(ids[i]);
            return sb.ToString();
        }

        private static string DecodeString(byte[] v)
        {
            // 可打印则直接文本，否则十六进制
            bool printable = v.Length > 0;
            foreach (byte b in v)
            {
                if (b < 0x20 && b != 0x09 && b != 0x0A && b != 0x0D) { printable = false; break; }
            }
            if (printable) return Encoding.UTF8.GetString(v);
            return BytesToHex(v);
        }

        private static string BytesToHex(byte[] v)
        {
            StringBuilder sb = new StringBuilder(v.Length * 3);
            for (int i = 0; i < v.Length; i++)
            {
                if (i > 0) sb.Append(' ');
                sb.Append(v[i].ToString("X2"));
            }
            return sb.ToString();
        }

        private static string DecodeValue(byte tag, byte[] v, out string typeName)
        {
            switch (tag)
            {
                case 0x02: typeName = "INTEGER"; return DecodeIntegerSigned(v).ToString();
                case 0x04: typeName = "OCTET STRING"; return DecodeString(v);
                case 0x05: typeName = "NULL"; return "";
                case 0x06: typeName = "OID"; return DecodeOid(v);
                case 0x40:
                    typeName = "IPAddress";
                    if (v.Length == 4) return v[0] + "." + v[1] + "." + v[2] + "." + v[3];
                    return BytesToHex(v);
                case 0x41: typeName = "Counter"; return DecodeUnsigned(v).ToString();
                case 0x42: typeName = "Gauge"; return DecodeUnsigned(v).ToString();
                case 0x43:
                    typeName = "TimeTicks";
                    ulong t = DecodeUnsigned(v);
                    return t + "（约 " + (t / 100.0).ToString("0.0") + " 秒）";
                case 0x44: typeName = "Opaque"; return BytesToHex(v);
                case 0x46: typeName = "Counter64"; return DecodeUnsigned(v).ToString();
                default: typeName = "0x" + tag.ToString("X2"); return BytesToHex(v);
            }
        }
    }

    // ==========================================================================
    // PJL 客户端：TcpClient 9100，直发 @PJL 指令并读回响应
    // ==========================================================================
    internal class PjlClient
    {
        private readonly string _ip;
        private readonly int _port;
        private readonly int _timeoutMs;

        public PjlClient(string ip, int port, int timeoutMs)
        {
            _ip = ip;
            _port = port;
            _timeoutMs = timeoutMs <= 0 ? 3000 : timeoutMs;
        }

        // commands 为含 \r\n 的完整指令串，如 "@PJL\r\n@PJL INFO STATUS\r\n"
        public string Query(string[] commands)
        {
            using (TcpClient client = new TcpClient())
            {
                IAsyncResult ar = client.BeginConnect(_ip, _port, null, null);
                if (!ar.AsyncWaitHandle.WaitOne(_timeoutMs))
                    throw new Exception("TCP 连接超时（" + _ip + ":" + _port + "）");
                client.EndConnect(ar);
                client.ReceiveTimeout = _timeoutMs;
                client.SendTimeout = _timeoutMs;
                using (NetworkStream s = client.GetStream())
                {
                    StringBuilder sb = new StringBuilder();
                    foreach (string cmd in commands)
                    {
                        byte[] data = Encoding.ASCII.GetBytes(cmd);
                        s.Write(data, 0, data.Length);
                        sb.Append("--- " + cmd.Replace("\r\n", " ").TrimEnd() + " ---\r\n");
                        sb.Append(ReadUntilIdle(client, s)).Append("\r\n\r\n");
                    }
                    return sb.ToString();
                }
            }
        }

        // 读到空闲（首包用满超时等待，之后 600ms 无后续数据视为响应结束）
        private string ReadUntilIdle(TcpClient client, NetworkStream s)
        {
            StringBuilder sb = new StringBuilder();
            byte[] buf = new byte[4096];
            try
            {
                while (true)
                {
                    int n = s.Read(buf, 0, buf.Length);
                    if (n <= 0) break;
                    sb.Append(Encoding.ASCII.GetString(buf, 0, n));
                    client.ReceiveTimeout = 600; // 已收到数据，缩短尾部等待
                }
            }
            catch (System.IO.IOException) { /* 读超时 = 响应结束 */ }
            catch (SocketException) { /* 同上 */ }
            return sb.ToString();
        }
    }

    // ==========================================================================
    // 队列端口 → 打印机 IP 解析：
    //   ① 注册表 Standard TCP/IP Port\Ports\<PortName> 的 IPAddress / HostName
    //   ② 端口名内嵌 IP（Windows 约定 IP_x.x.x.x）
    //   ③ FILE:/PORTPROMPT/WSD/USB 端口 → 提示手动输入 IP
    // ==========================================================================
    internal static class PortIpResolver
    {
        public static string ResolveIp(string portName, out string note)
        {
            note = null;
            if (string.IsNullOrEmpty(portName)) return null;
            try
            {
                using (RegistryKey k = Registry.LocalMachine.OpenSubKey(
                    @"SYSTEM\CurrentControlSet\Control\Print\Monitors\Standard TCP/IP Port\Ports\" + portName))
                {
                    if (k != null)
                    {
                        object ipa = k.GetValue("IPAddress");
                        object hn = k.GetValue("HostName");
                        string s = null;
                        if (ipa != null && !string.IsNullOrWhiteSpace(ipa.ToString()) && ipa.ToString() != "0.0.0.0")
                            s = ipa.ToString();
                        if (string.IsNullOrEmpty(s) && hn != null) s = hn.ToString();
                        if (!string.IsNullOrEmpty(s)) return s;
                    }
                }
            }
            catch { /* 注册表不可读则走兜底 */ }
            Match m = Regex.Match(portName, @"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})");
            if (m.Success)
            {
                note = "从端口名解析出 IP";
                return m.Groups[1].Value;
            }
            if (portName.StartsWith("USB", StringComparison.OrdinalIgnoreCase))
                note = "USB 端口：SNMP/PJL 需要打印机网络地址，请手动输入 IP（设备需接入网络）";
            else if (portName.StartsWith("WSD", StringComparison.OrdinalIgnoreCase))
                note = "WSD 端口：请手动输入打印机 IP";
            else if (portName.StartsWith("PORTPROMPT", StringComparison.OrdinalIgnoreCase) || portName == "FILE:")
                note = "本地虚拟端口：请手动输入打印机 IP";
            else
                note = "非 TCP/IP 端口：请手动输入打印机 IP";
            return null;
        }
    }

    // ==========================================================================
    // 主窗体
    // ==========================================================================
    internal class ManagerForm : Form
    {
        // 标准管理 OID（SNMP 实例号 .1）
        private static readonly string[] StandardOids = new string[]
        {
            "1.3.6.1.2.1.25.3.2.1.3.1",    // hrDeviceDescr —— 型号
            "1.3.6.1.2.1.25.3.5.1.1.1",    // hrPrinterStatus —— 打印机状态
            "1.3.6.1.2.1.25.3.2.1.7.1",    // hrDeviceStatus —— 设备状态
            "1.3.6.1.2.1.43.10.2.1.4.1.1"  // prtMarkerLifeCount —— 总页数
        };

        // Brother 私有分支全表（41 个，去尾点去重）：
        // 来源 E:\Deepseek\lj2655win\analysis\oid_table.txt（lerbm13a.dll SNMP OID 全表），
        // 覆盖 1.3.6.1.4.1.2435.* 全部与 .63/.67/.99/.64/.68 分支。
        private static readonly string[] BrotherOidTable = new string[]
        {
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.47.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.48.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.67.13.2.1.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.67.12.2.1.3",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.67.11.2.1.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.5.1.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.67.14.1.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.67.14.2.0",
            "1.3.6.1.4.1.2435.2.4.3.99.3.1.1.1.2",
            "1.3.6.1.4.1.2435.2.4.3.99.3.1.3.1.2",
            "1.3.6.1.4.1.2435.2.4.3.99.3.1.4.1.2",
            "1.3.6.1.4.1.2435.2.4.3.99.3.1.5.1.2",
            "1.3.6.1.4.1.2435.2.4.3.99.3.1.2.1.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.3.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.26.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.27.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.6.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.28.1.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.7.1.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.28.1.3",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.7.1.3",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.5.1.3.11",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.5.1.4.11",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.5.1.3.8",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.5.1.4.8",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.21.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.9.1.3",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.9.1.4",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.25.1.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.22.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.23.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.24.0",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.25.1.5",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.25.1.3",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.63.25.1.4",
            "1.3.6.1.4.1.2435.2.4.3.99.3.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.64",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.64.11.2.1.2",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.64.11.2.1.3",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.68",
            "1.3.6.1.4.1.2435.2.3.9.4.2.1.5.1.2.67"
        };

        // PJL 指令（与 oid_table.txt 中提取的 @PJL 命令区对应）
        private static readonly string[] PjlCommands = new string[]
        {
            "@PJL\r\n@PJL INFO STATUS\r\n",
            "@PJL\r\n@PJL DINQUIRE SERIALNUMPRN\r\n"
        };

        private ComboBox _cboQueues;
        private TextBox _txtIp;
        private Button _btnRefresh;
        private Button _btnQuery;
        private Button _btnRefreshStatus;
        private Button _btnTestPage;
        private Button _btnWeb;
        private Button _btnExport;
        private Label _lblHint;
        private ListView _lvStatus;
        private TextBox _txtPjl;

        private readonly Dictionary<string, WinspoolNative.PRINTER_INFO_2> _printers =
            new Dictionary<string, WinspoolNative.PRINTER_INFO_2>();
        private readonly List<SnmpRow> _lastRows = new List<SnmpRow>();
        private string _currentQueue;
        private bool _querying;
        private CancellationTokenSource _cts;

        private class SnmpRow
        {
            public string Group;
            public string Name;
            public string Oid;
            public string Raw;
            public string Guess;
        }

        public ManagerForm()
        {
            BuildUi();
            RefreshQueues();
        }

        // ------------------------------------------------------------------
        // UI 构建（简体中文）
        // ------------------------------------------------------------------
        private void BuildUi()
        {
            Text = "联想 LJ24/LJ26/M74/M76 打印机管理（Windows on ARM / x64 通用）";
            ClientSize = new System.Drawing.Size(860, 640);
            MinimumSize = new System.Drawing.Size(720, 560);
            StartPosition = FormStartPosition.CenterScreen;

            Panel top = new Panel();
            top.Dock = DockStyle.Top;
            top.Height = 104;

            Label lblQueue = new Label();
            lblQueue.Text = "本机队列：";
            lblQueue.SetBounds(12, 14, 66, 20);

            _cboQueues = new ComboBox();
            _cboQueues.DropDownStyle = ComboBoxStyle.DropDownList;
            _cboQueues.SetBounds(82, 11, 300, 23);
            _cboQueues.SelectedIndexChanged += CboQueues_SelectedIndexChanged;

            _btnRefresh = new Button();
            _btnRefresh.Text = "刷新";
            _btnRefresh.SetBounds(392, 10, 60, 25);
            _btnRefresh.Click += BtnRefresh_Click;

            Label lblIp = new Label();
            lblIp.Text = "IP/主机名：";
            lblIp.SetBounds(462, 14, 74, 20);

            _txtIp = new TextBox();
            _txtIp.SetBounds(538, 11, 160, 23);

            _btnQuery = new Button();
            _btnQuery.Text = "查询状态";
            _btnQuery.SetBounds(706, 10, 90, 25);
            _btnQuery.Click += BtnQueryStatus_Click;

            _btnRefreshStatus = new Button();
            _btnRefreshStatus.Text = "刷新状态(本地)";
            _btnRefreshStatus.SetBounds(12, 46, 110, 26);
            _btnRefreshStatus.Click += BtnRefreshStatus_Click;

            _btnTestPage = new Button();
            _btnTestPage.Text = "打印测试页";
            _btnTestPage.SetBounds(132, 46, 100, 26);
            _btnTestPage.Click += BtnTestPage_Click;

            _btnWeb = new Button();
            _btnWeb.Text = "打开设备 Web 管理";
            _btnWeb.SetBounds(242, 46, 140, 26);
            _btnWeb.Click += BtnWeb_Click;

            _btnExport = new Button();
            _btnExport.Text = "导出状态报告(JSON)";
            _btnExport.SetBounds(392, 46, 150, 26);
            _btnExport.Click += BtnExport_Click;

            _lblHint = new Label();
            _lblHint.ForeColor = System.Drawing.Color.Gray;
            _lblHint.SetBounds(12, 78, 830, 18);

            top.Controls.Add(lblQueue);
            top.Controls.Add(_cboQueues);
            top.Controls.Add(_btnRefresh);
            top.Controls.Add(lblIp);
            top.Controls.Add(_txtIp);
            top.Controls.Add(_btnQuery);
            top.Controls.Add(_btnRefreshStatus);
            top.Controls.Add(_btnTestPage);
            top.Controls.Add(_btnWeb);
            top.Controls.Add(_btnExport);
            top.Controls.Add(_lblHint);

            _lvStatus = new ListView();
            _lvStatus.View = View.Details;
            _lvStatus.FullRowSelect = true;
            _lvStatus.Dock = DockStyle.Fill;
            _lvStatus.Columns.Add("项目", 220);
            _lvStatus.Columns.Add("OID", 260);
            _lvStatus.Columns.Add("原始值", 180);
            _lvStatus.Columns.Add("智能解读", 200);

            _txtPjl = new TextBox();
            _txtPjl.Multiline = true;
            _txtPjl.ReadOnly = true;
            _txtPjl.ScrollBars = ScrollBars.Vertical;
            _txtPjl.Font = new System.Drawing.Font("Consolas", 9F);
            _txtPjl.Dock = DockStyle.Bottom;
            _txtPjl.Height = 120;

            Controls.Add(_lvStatus);
            Controls.Add(_txtPjl);
            Controls.Add(top);
        }

        // ------------------------------------------------------------------
        // UI 线程调度 + 分组
        // ------------------------------------------------------------------
        private void Ui(Action a)
        {
            try
            {
                if (IsDisposed) return;
                if (InvokeRequired) BeginInvoke(a);
                else a();
            }
            catch { /* 窗体关闭中的竞态，忽略 */ }
        }

        private ListViewGroup FindGroup(string name)
        {
            foreach (ListViewGroup g in _lvStatus.Groups)
            {
                if (g.Name == name) return g;
            }
            ListViewGroup ng = new ListViewGroup(name, name);
            _lvStatus.Groups.Add(ng);
            return ng;
        }

        private void AddRow(string group, string name, string oid, string raw, string guess)
        {
            SnmpRow row = new SnmpRow();
            row.Group = group;
            row.Name = name;
            row.Oid = oid;
            row.Raw = raw;
            row.Guess = guess;
            _lastRows.Add(row);
            Ui(delegate
            {
                ListViewItem it = new ListViewItem(name);
                it.SubItems.Add(oid);
                it.SubItems.Add(raw);
                it.SubItems.Add(guess);
                it.Group = FindGroup(group);
                _lvStatus.Items.Add(it);
            });
        }

        private void SetBusy(bool busy)
        {
            Ui(delegate
            {
                _btnQuery.Enabled = !busy;
                _btnRefreshStatus.Enabled = !busy;
                _btnRefresh.Enabled = !busy;
                _btnTestPage.Enabled = !busy;
                _btnWeb.Enabled = !busy;
                _btnExport.Enabled = !busy;
            });
        }

        // ------------------------------------------------------------------
        // 队列枚举与 IP 解析
        // ------------------------------------------------------------------
        private void RefreshQueues()
        {
            try
            {
                List<WinspoolNative.PRINTER_INFO_2> list = WinspoolNative.EnumLocalPrinters();
                _printers.Clear();
                string keep = _cboQueues.SelectedItem as string;
                _cboQueues.Items.Clear();
                foreach (WinspoolNative.PRINTER_INFO_2 p in list)
                {
                    if (string.IsNullOrEmpty(p.pPrinterName)) continue;
                    _printers[p.pPrinterName] = p;
                    _cboQueues.Items.Add(p.pPrinterName);
                }
                if (keep != null && _cboQueues.Items.Contains(keep)) _cboQueues.SelectedItem = keep;
                else if (_cboQueues.Items.Count > 0) _cboQueues.SelectedIndex = 0;
                _lblHint.Text = "本机队列 " + _cboQueues.Items.Count + " 个。选择队列自动解析 IP；USB/WSD 等端口需手动输入 IP。";
            }
            catch (Exception ex)
            {
                _lblHint.Text = "枚举队列失败：" + ex.Message;
            }
        }

        private void CboQueues_SelectedIndexChanged(object sender, EventArgs e)
        {
            string name = _cboQueues.SelectedItem as string;
            if (string.IsNullOrEmpty(name)) return;
            _currentQueue = name;
            WinspoolNative.PRINTER_INFO_2 p;
            if (!_printers.TryGetValue(name, out p)) return;
            string note;
            string ip = PortIpResolver.ResolveIp(p.pPortName, out note);
            if (!string.IsNullOrEmpty(ip))
            {
                _txtIp.Text = ip;
                _lblHint.Text = "队列端口 " + p.pPortName + " → " + ip + (note == null ? "" : "（" + note + "）");
            }
            else
            {
                _lblHint.Text = "队列端口 " + p.pPortName + "：" + (note ?? "请手动输入打印机 IP");
            }
        }

        private string ResolveTargetIp()
        {
            string ip = _txtIp.Text.Trim();
            if (!string.IsNullOrEmpty(ip)) return ip;
            string name = _cboQueues.SelectedItem as string;
            if (string.IsNullOrEmpty(name)) return null;
            WinspoolNative.PRINTER_INFO_2 p;
            if (!_printers.TryGetValue(name, out p)) return null;
            string note;
            return PortIpResolver.ResolveIp(p.pPortName, out note);
        }

        // ------------------------------------------------------------------
        // 按钮：刷新（重枚举队列）
        // ------------------------------------------------------------------
        private void BtnRefresh_Click(object sender, EventArgs e)
        {
            RefreshQueues();
        }

        // ------------------------------------------------------------------
        // 按钮：刷新状态（仅本地：队列列表 + winspool 状态位，不联网）
        // ------------------------------------------------------------------
        private void BtnRefreshStatus_Click(object sender, EventArgs e)
        {
            RefreshQueues();
            _lvStatus.Items.Clear();
            _lvStatus.Groups.Clear();
            _lastRows.Clear();
            string name = _cboQueues.SelectedItem as string;
            if (string.IsNullOrEmpty(name))
            {
                _lblHint.Text = "本机没有打印队列。";
                return;
            }
            WinspoolNative.PRINTER_INFO_2 p;
            if (_printers.TryGetValue(name, out p))
            {
                AddRow("基本信息", "队列", "-", name, "驱动 " + p.pDriverName + " / 端口 " + p.pPortName);
                AddRow("状态", "打印队列状态位", "-", "0x" + p.Status.ToString("X8"), MapWinspoolStatus(p.Status));
            }
        }

        // ------------------------------------------------------------------
        // 按钮：查询状态（全量：SNMP 标准 + Brother 私有 41 OID + winspool 位 + PJL）
        // 网络任务全部 Task.Run 异步 + CancellationToken（单次探测 3 秒封顶）；
        // 离线显示「无法连接（检查 IP/联机）」。
        // ------------------------------------------------------------------
        private async void BtnQueryStatus_Click(object sender, EventArgs e)
        {
            if (_querying) return;
            string ip = ResolveTargetIp();
            if (string.IsNullOrEmpty(ip))
            {
                MessageBox.Show("请先选择 TCP/IP 端口的本机队列，或直接输入打印机 IP。\r\nUSB 队列请手动填 IP（设备需接入网络）。",
                    "缺少打印机地址", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            _querying = true;
            SetBusy(true);
            _lvStatus.Items.Clear();
            _lvStatus.Groups.Clear();
            _lastRows.Clear();
            _txtPjl.Clear();
            _cts = new CancellationTokenSource();
            CancellationToken token = _cts.Token;
            int responded = 0;
            try
            {
                _lblHint.Text = "探活中：" + ip + "（SNMP hrDeviceStatus，3 秒超时）…";

                // ① 探活 + 设备状态（单发 3 秒，超时即判定离线）
                SnmpClient.SnmpVar probe = await Task.Run(delegate { return SnmpGetSafe(ip, "1.3.6.1.2.1.25.3.2.1.7.1", 3000, 0, token); });
                if (probe == null || probe.Value == null)
                {
                    // 离线：仍显示 winspool 队列状态位（本地信息不依赖网络）
                    ShowQueueStatusBits();
                    Ui(delegate { _lblHint.ForeColor = System.Drawing.Color.Red; });
                    Ui(delegate { _lblHint.Text = "无法连接（检查 IP/联机）——" + ip + " SNMP 无响应"; });
                    MessageBox.Show("无法连接（检查 IP/联机）。\r\nSNMP " + ip + " 无响应：请确认打印机开机、与主机网络互通。",
                        "连接失败", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
                AddRow("状态", "设备状态 hrDeviceStatus", "1.3.6.1.2.1.25.3.2.1.7.1", probe.Value, MapHrDeviceStatus(probe.Value));
                Ui(delegate { _lblHint.ForeColor = System.Drawing.Color.Black; });

                // ② 标准 MIB：型号 / hrPrinterStatus / 总页数
                SnmpClient.SnmpVar vDescr = await Task.Run(delegate { return SnmpGetSafe(ip, StandardOids[0], 3000, 2, token); });
                if (vDescr != null && vDescr.Value != null)
                    AddRow("基本信息", "设备型号 hrDeviceDescr", StandardOids[0], vDescr.Value, "");

                SnmpClient.SnmpVar vPrn = await Task.Run(delegate { return SnmpGetSafe(ip, StandardOids[1], 3000, 2, token); });
                if (vPrn != null && vPrn.Value != null)
                    AddRow("状态", "打印机状态 hrPrinterStatus", StandardOids[1], vPrn.Value, MapHrPrinterStatus(vPrn.Value));

                SnmpClient.SnmpVar vPages = await Task.Run(delegate { return SnmpGetSafe(ip, StandardOids[3], 3000, 2, token); });
                if (vPages != null && vPages.Value != null)
                {
                    long pages;
                    string g = long.TryParse(vPages.Value, out pages) ? "总页数 " + pages.ToString("N0") : "";
                    AddRow("页数", "打印机总页数 prtMarkerLifeCount", StandardOids[3], vPages.Value, g);
                }

                // ③ winspool 队列状态位（离线/卡纸/缺纸等中文映射）
                ShowQueueStatusBits();

                // ④ Brother 私有分支 41 OID 逐个 GET（超时 3 秒、不重试，控制总时长；
                //    凡有响应显示「OID = 原始值」+ 智能猜测，0-100 显示 ≈N% 待真机校准）
                for (int i = 0; i < BrotherOidTable.Length; i++)
                {
                    if (token.IsCancellationRequested) break;
                    string oid = BrotherOidTable[i];
                    if (i % 5 == 0)
                    {
                        int shown = i;
                        Ui(delegate { _lblHint.Text = "Brother 私有 OID 采集中 " + shown + "/" + BrotherOidTable.Length + "…"; });
                    }
                    SnmpClient.SnmpVar v = await Task.Run(delegate { return SnmpGetSafe(ip, oid, 3000, 0, token); });
                    if (v != null && v.Value != null)
                    {
                        responded++;
                        AddRow(GroupOf(oid), "Brother …" + TailOf(oid, 3), oid, v.Value, SmartGuess(v.TypeName, v.Value));
                    }
                }

                // ⑤ PJL：@PJL INFO STATUS + @PJL DINQUIRE SERIALNUMPRN（TCP 9100）
                string pjl = await Task.Run(delegate
                {
                    try { return new PjlClient(ip, 9100, 3000).Query(PjlCommands); }
                    catch (Exception pex) { return "[PJL 失败] " + pex.Message + "\r\n（PJL 通道不影响 SNMP 状态显示）"; }
                });
                Ui(delegate { _txtPjl.Text = pjl; });

                _lblHint.Text = "完成：Brother 私有 OID 有响应 " + responded + "/" + BrotherOidTable.Length +
                    "（无响应属正常，语义与阈值待真机校准，采样工具 tools\\snmp_sample.py）";
            }
            catch (OperationCanceledException)
            {
                _lblHint.Text = "查询已取消。";
            }
            catch (Exception ex)
            {
                MessageBox.Show("查询状态失败：" + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                _querying = false;
                SetBusy(false);
                if (_cts != null) _cts.Dispose();
                _cts = null;
            }
        }

        // winspool 状态位行（选中队列）
        private void ShowQueueStatusBits()
        {
            string name = _currentQueue;
            if (string.IsNullOrEmpty(name)) return;
            WinspoolNative.PRINTER_INFO_2? info = WinspoolNative.GetPrinterInfo2(name);
            if (info.HasValue)
            {
                AddRow("状态", "打印队列状态位（winspool）", "-", "0x" + info.Value.Status.ToString("X8"),
                    MapWinspoolStatus(info.Value.Status));
            }
        }

        // ------------------------------------------------------------------
        // 中文映射与智能猜测
        // ------------------------------------------------------------------
        private static void AddBit(uint st, uint bit, string name, List<string> parts)
        {
            if ((st & bit) != 0) parts.Add(name);
        }

        // winspool Printer_Status 位 → 中文（离线/卡纸/缺纸等）
        private static string MapWinspoolStatus(uint st)
        {
            if (st == 0) return "就绪";
            List<string> parts = new List<string>();
            AddBit(st, 0x00000001, "暂停", parts);
            AddBit(st, 0x00000002, "错误", parts);
            AddBit(st, 0x00000004, "正在删除", parts);
            AddBit(st, 0x00000008, "卡纸", parts);
            AddBit(st, 0x00000010, "缺纸", parts);
            AddBit(st, 0x00000020, "手动送纸", parts);
            AddBit(st, 0x00000040, "纸张问题", parts);
            AddBit(st, 0x00000080, "离线", parts);
            AddBit(st, 0x00000100, "I/O 活动", parts);
            AddBit(st, 0x00000200, "忙碌", parts);
            AddBit(st, 0x00000400, "打印中", parts);
            AddBit(st, 0x00000800, "出纸盒已满", parts);
            AddBit(st, 0x00001000, "不可用", parts);
            AddBit(st, 0x00002000, "等待", parts);
            AddBit(st, 0x00004000, "处理中", parts);
            AddBit(st, 0x00008000, "初始化中", parts);
            AddBit(st, 0x00010000, "预热中", parts);
            AddBit(st, 0x00020000, "墨粉不足", parts);
            AddBit(st, 0x00040000, "无墨粉", parts);
            AddBit(st, 0x00100000, "需要用户干预", parts);
            AddBit(st, 0x00200000, "内存不足", parts);
            AddBit(st, 0x00400000, "盖板打开", parts);
            return parts.Count == 0 ? ("状态位 0x" + st.ToString("X8")) : string.Join("、", parts.ToArray());
        }

        // hrDeviceStatus（RFC2790）→ 中文
        private static string MapHrDeviceStatus(string v)
        {
            switch (v)
            {
                case "1": return "未知(1)";
                case "2": return "正常运行(2)";
                case "3": return "警告(3)——可能缺纸/卡纸/墨粉低";
                case "4": return "测试中(4)";
                case "5": return "已停机(5)";
                default: return "值=" + v;
            }
        }

        // hrPrinterStatus（RFC2790）→ 中文
        private static string MapHrPrinterStatus(string v)
        {
            switch (v)
            {
                case "1": return "其他(1)";
                case "2": return "未知(2)";
                case "3": return "空闲(3)";
                case "4": return "打印中(4)";
                case "5": return "预热(5)";
                default: return "值=" + v;
            }
        }

        // 智能猜测：INTEGER/Counter/Gauge 且 0-100 → 「≈N%」并标注阈值待真机校准
        private static string SmartGuess(string typeName, string raw)
        {
            long n;
            if ((typeName == "INTEGER" || typeName == "Counter" || typeName == "Gauge") && long.TryParse(raw, out n))
            {
                if (n >= 0 && n <= 100) return "≈" + n + "%（阈值待真机校准）";
            }
            return "";
        }

        // Brother OID 分组（启发式，待真机校准）：
        //   .4.3.99.*        → 保密箱（Brother 安全打印分支，与 @PJL INFO 命令区对应）
        //   …63.25.1.x       → 纸盒（进纸参数猜测）
        //   …63.5.1.x / …63.x.0 → 墨粉/耗材（与 KCYM 校正 PJL 命令对应的猜测）
        //   其余             → Brother 私有
        private static string GroupOf(string oid)
        {
            if (oid.Contains(".4.3.99.")) return "保密箱";
            if (oid.Contains(".5.1.2.63.25.")) return "纸盒";
            if (oid.Contains(".5.1.2.63.")) return "墨粉/耗材";
            return "Brother 私有";
        }

        private static string TailOf(string oid, int parts)
        {
            string[] seg = oid.Split('.');
            int from = Math.Max(0, seg.Length - parts);
            StringBuilder sb = new StringBuilder();
            for (int i = from; i < seg.Length; i++)
            {
                if (sb.Length > 0) sb.Append('.');
                sb.Append(seg[i]);
            }
            return sb.ToString();
        }

        // ------------------------------------------------------------------
        // SNMP 安全调用：异常一律吞掉返回 null（离线/不支持都不打断整轮采集）
        // ------------------------------------------------------------------
        private static SnmpClient.SnmpVar SnmpGetSafe(string ip, string oid, int timeoutMs, int retries, CancellationToken token)
        {
            try
            {
                if (token.IsCancellationRequested) return null;
                SnmpClient c = new SnmpClient(ip, "public", timeoutMs, retries);
                return c.Get(oid);
            }
            catch { return null; }
        }

        // ------------------------------------------------------------------
        // 按钮：打印测试页（rundll32 printui.dll,PrintUIEntry /k /n "<队列>"）
        // ------------------------------------------------------------------
        private void BtnTestPage_Click(object sender, EventArgs e)
        {
            string queue = _cboQueues.SelectedItem as string;
            if (string.IsNullOrEmpty(queue))
            {
                MessageBox.Show("请先选择本机队列。", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            try
            {
                Process.Start("rundll32.exe", "printui.dll,PrintUIEntry /k /n \"" + queue + "\"");
            }
            catch (Exception ex)
            {
                MessageBox.Show("打印测试页失败：" + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ------------------------------------------------------------------
        // 按钮：打开设备 Web 管理（http://<ip>/）
        // ------------------------------------------------------------------
        private void BtnWeb_Click(object sender, EventArgs e)
        {
            string ip = _txtIp.Text.Trim();
            if (string.IsNullOrEmpty(ip))
            {
                MessageBox.Show("请先填入打印机 IP（选择队列可自动解析）。", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            try
            {
                Process.Start("http://" + ip + "/");
            }
            catch (Exception ex)
            {
                MessageBox.Show("打开浏览器失败：" + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ------------------------------------------------------------------
        // 按钮：导出状态报告(JSON)——手写 JSON 序列化，零第三方依赖
        // ------------------------------------------------------------------
        private void BtnExport_Click(object sender, EventArgs e)
        {
            if (_lastRows.Count == 0)
            {
                MessageBox.Show("还没有查询结果，请先点【查询状态】。", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            using (SaveFileDialog dlg = new SaveFileDialog())
            {
                dlg.Filter = "JSON 文件 (*.json)|*.json";
                dlg.FileName = "LJ2400状态报告_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".json";
                if (dlg.ShowDialog(this) != DialogResult.OK) return;
                StringBuilder sb = new StringBuilder();
                sb.Append("{\r\n");
                sb.Append("  \"queue\": ").Append(JsonStr(_currentQueue)).Append(",\r\n");
                sb.Append("  \"ip\": ").Append(JsonStr(_txtIp.Text.Trim())).Append(",\r\n");
                sb.Append("  \"timestamp\": \"").Append(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")).Append("\",\r\n");
                sb.Append("  \"pjl\": ").Append(JsonStr(_txtPjl.Text)).Append(",\r\n");
                sb.Append("  \"items\": [\r\n");
                for (int i = 0; i < _lastRows.Count; i++)
                {
                    SnmpRow r = _lastRows[i];
                    sb.Append("    {\"group\": ").Append(JsonStr(r.Group));
                    sb.Append(", \"name\": ").Append(JsonStr(r.Name));
                    sb.Append(", \"oid\": ").Append(JsonStr(r.Oid));
                    sb.Append(", \"raw\": ").Append(JsonStr(r.Raw));
                    sb.Append(", \"guess\": ").Append(JsonStr(r.Guess));
                    sb.Append("}");
                    if (i < _lastRows.Count - 1) sb.Append(",");
                    sb.Append("\r\n");
                }
                sb.Append("  ]\r\n}\r\n");
                File.WriteAllText(dlg.FileName, sb.ToString(), Encoding.UTF8);
                MessageBox.Show("已导出：" + dlg.FileName, "导出完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
        }

        private static string JsonStr(string s)
        {
            if (s == null) return "null";
            StringBuilder sb = new StringBuilder("\"");
            foreach (char ch in s)
            {
                switch (ch)
                {
                    case '\\': sb.Append("\\\\"); break;
                    case '"': sb.Append("\\\""); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (ch < ' ') sb.Append("\\u").Append(((int)ch).ToString("x4"));
                        else sb.Append(ch);
                        break;
                }
            }
            sb.Append("\"");
            return sb.ToString();
        }

        // ------------------------------------------------------------------
        // 关窗时取消未完成的网络任务
        // ------------------------------------------------------------------
        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (_cts != null)
            {
                try { _cts.Cancel(); } catch { }
            }
            base.OnFormClosing(e);
        }
    }
}

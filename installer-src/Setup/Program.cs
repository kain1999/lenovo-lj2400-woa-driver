// ============================================================================
// LJ2400Setup.exe —— 联想 LJ24/LJ26/M74/M76 系列打印机驱动安装器
// Windows on ARM / x64 通用（AnyCPU，纯 .NET Framework WinForms，零第三方依赖）
//
// 两条安装路线（ARM64/x64 界面一致）：
//   签名安装路线（推荐主推）：
//          inf2cat /os:10_X64,10_ARM64 → New-SelfSignedCertificate(CN=Lenovo WoA Test)
//          → Set-AuthenticodeSignature 签 .cat → 证书入 LocalMachine/CurrentUser\TrustedPublisher
//          → bcdedit /set testsigning on → 提示重启（state.json=pending_reboot）
//          → 重启后再次运行本安装器自动续装（pnputil 进 store → 27 型号验证 → 建队列）
//          SDK 引导：HttpClient 下载微软官方安装器直链（x86 二进制，WoA 模拟层可运行）
//          → winsdksetup.exe /features OptionId.SigningTools /q /norestart 静默最小安装
//          → 重新探测 inf2cat；静默退出码非 0 或探测仍失败 → 自动转 GUI 安装器 → 「重新检测 Inf2Cat」
//   IPP 路线（基础打印，无需 SDK，零依赖）：
//          Add-Printer -IppUrl http://<ip>/ipp/print（网络型号 DN/DW/DNA/DXF/W 后缀）
//
// 状态机：%ProgramData%\LenovoLJ2400WoA\state.json
//   pending_signature → pending_reboot →（重启）→ ready → installed
//
// 编译（唯一编译链）：
//   C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
//     /target:winexe /platform:anycpu /r:System.Net.Http.dll
//     /out:dist\LJ2400Setup.exe /win32manifest:app.manifest Setup\Program.cs
//
// 自检入口（winexe 无控制台，结果写 exe 同目录文件 + 退出码）：
//   LJ2400Setup.exe /selftest-state   → selftest_state.txt（状态机读写往返测试）
//   LJ2400Setup.exe /selftest-arch    → selftest_arch.txt（ARM64 检测函数单测）
//   LJ2400Setup.exe /selftest-sdk     → selftest_sdk.txt（SDK 引导单测：直链/静默命令/探测顺序，不实际下载）
// ============================================================================

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

namespace LenovoLJ2400Setup
{
    internal static class Program
    {
        // --------------------------------------------------------------------
        // INF 型号名常量表（27 项）：与 E:\Deepseek\lj2400lin\analysis\ppd_extract.json
        // 的 27 个 ModelName 逐一对账（格式 "Lenovo <Model>"）。
        // 对账脚本：tools\model_reconcile.py。
        // --------------------------------------------------------------------
        public static readonly string[] InfModelNames = new string[]
        {
            "Lenovo LJ2400 Pro",
            "Lenovo LJ2405",
            "Lenovo LJ2405D",
            "Lenovo LJ2605D",
            "Lenovo LJ2655DN",
            "Lenovo LJ2680DN",
            "Lenovo M7400 Pro",
            "Lenovo M7400W",
            "Lenovo M7405D",
            "Lenovo M7405DW",
            "Lenovo M7450F Pro",
            "Lenovo M7455DNF",
            "Lenovo M7460",
            "Lenovo M7480",
            "Lenovo M7490DNF",
            "Lenovo M7605D",
            "Lenovo M7605DW",
            "Lenovo M7615DNA",
            "Lenovo M7625DWA",
            "Lenovo M7626DNA",
            "Lenovo M7628DNA",
            "Lenovo M7655DHF",
            "Lenovo M7675DXF",
            "Lenovo M7680D",
            "Lenovo M7685DXF",
            "Lenovo M7686DXF",
            "Lenovo M7690DNA"
        };

        // 驱动包文件名（v4 打印模型，由生成器产出）
        public const string InfFileName = "LJ2400WOA.INF";

        // 签名安装路线自签证书主题（测试签名专用，无秘钥写入代码）
        public const string CertSubject = "CN=Lenovo WoA Test";

        [STAThread]
        private static int Main()
        {
            // 自检入口：winexe 无控制台，结果写文件 + 退出码（供构建脚本断言）
            foreach (string a in Environment.GetCommandLineArgs())
            {
                if (string.Equals(a, "/selftest-state", StringComparison.OrdinalIgnoreCase))
                {
                    Environment.Exit(SelfTest.RunState(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "selftest_state.txt")));
                }
                if (string.Equals(a, "/selftest-arch", StringComparison.OrdinalIgnoreCase))
                {
                    Environment.Exit(SelfTest.RunArch(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "selftest_arch.txt")));
                }
                if (string.Equals(a, "/selftest-sdk", StringComparison.OrdinalIgnoreCase))
                {
                    Environment.Exit(SelfTest.RunSdk(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "selftest_sdk.txt")));
                }
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SetupForm());
            return 0;
        }
    }

    // ==========================================================================
    // 原生架构检测：GetNativeSystemInfo，wProcessorArchitecture==12 即 ARM64
    // ==========================================================================
    internal static class NativeMethods
    {
        [DllImport("kernel32.dll", SetLastError = true)]
        public static extern void GetNativeSystemInfo(out SYSTEM_INFO lpSystemInfo);

        [StructLayout(LayoutKind.Sequential)]
        public struct SYSTEM_INFO
        {
            public ushort wProcessorArchitecture; // 联合体首字段：0=x86, 9=x64, 12=ARM64
            public ushort wReserved;
            public uint dwPageSize;
            public IntPtr lpMinimumApplicationAddress;
            public IntPtr lpMaximumApplicationAddress;
            public IntPtr dwActiveProcessorMask;  // DWORD_PTR（64 位下 8 字节）
            public uint dwNumberOfProcessors;
            public uint dwProcessorType;
            public uint dwAllocationGranularity;
            public ushort wProcessorLevel;
            public ushort wProcessorRevision;
        }
    }

    internal static class ArchDetect
    {
        public const ushort PROCESSOR_ARCHITECTURE_INTEL = 0;
        public const ushort PROCESSOR_ARCHITECTURE_AMD64 = 9;
        public const ushort PROCESSOR_ARCHITECTURE_ARM64 = 12;

        public static ushort GetArch()
        {
            NativeMethods.SYSTEM_INFO si;
            NativeMethods.GetNativeSystemInfo(out si);
            return si.wProcessorArchitecture;
        }

        public static bool IsArm64()
        {
            return GetArch() == PROCESSOR_ARCHITECTURE_ARM64;
        }

        public static string ArchName(ushort arch)
        {
            switch (arch)
            {
                case PROCESSOR_ARCHITECTURE_INTEL: return "x86";
                case PROCESSOR_ARCHITECTURE_AMD64: return "x64";
                case PROCESSOR_ARCHITECTURE_ARM64: return "ARM64";
                default: return "0x" + arch.ToString("X4");
            }
        }
    }

    // ==========================================================================
    // 状态机存储：%ProgramData%\LenovoLJ2400WoA\state.json（手写 JSON，读侧正则容错）
    // ==========================================================================
    internal static class InstallStates
    {
        public const string PendingSignature = "pending_signature";
        public const string PendingReboot = "pending_reboot";
        public const string Ready = "ready";
        public const string Installed = "installed";
    }

    internal class StateRecord
    {
        public string State = "";
        public string Route = "";
        public string Model = "";
        public string Queue = "";
        public string Connection = "";   // usb / net / none
        public string Ip = "";
        public string Note = "";
        public string Timestamp = "";
    }

    internal static class StateStore
    {
        public static string StatePath()
        {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                "LenovoLJ2400WoA", "state.json");
        }

        public static void Write(StateRecord r)
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("{\r\n");
            sb.Append("  \"state\": ").Append(JsonStr(r.State)).Append(",\r\n");
            sb.Append("  \"route\": ").Append(JsonStr(r.Route)).Append(",\r\n");
            sb.Append("  \"model\": ").Append(JsonStr(r.Model)).Append(",\r\n");
            sb.Append("  \"queue\": ").Append(JsonStr(r.Queue)).Append(",\r\n");
            sb.Append("  \"connection\": ").Append(JsonStr(r.Connection)).Append(",\r\n");
            sb.Append("  \"ip\": ").Append(JsonStr(r.Ip)).Append(",\r\n");
            sb.Append("  \"note\": ").Append(JsonStr(r.Note)).Append(",\r\n");
            sb.Append("  \"timestamp\": ").Append(JsonStr(r.Timestamp)).Append("\r\n");
            sb.Append("}\r\n");
            Directory.CreateDirectory(Path.GetDirectoryName(StatePath()));
            File.WriteAllText(StatePath(), sb.ToString(), Encoding.UTF8);
        }

        // 容错读：文件缺失 / 损坏 / state 字段为空 → 返回 null（按全新安装处理）
        public static StateRecord Read()
        {
            try
            {
                string p = StatePath();
                if (!File.Exists(p)) return null;
                string s = File.ReadAllText(p);
                StateRecord r = new StateRecord();
                r.State = Pick(s, "state");
                r.Route = Pick(s, "route");
                r.Model = Pick(s, "model");
                r.Queue = Pick(s, "queue");
                r.Connection = Pick(s, "connection");
                r.Ip = Pick(s, "ip");
                r.Note = Pick(s, "note");
                r.Timestamp = Pick(s, "timestamp");
                if (r.State.Length == 0) return null;
                return r;
            }
            catch { return null; }
        }

        private static string Pick(string json, string key)
        {
            Match m = Regex.Match(json, "\"" + key + "\"\\s*:\\s*\"([^\"]*)\"");
            return m.Success ? m.Groups[1].Value : "";
        }

        public static string JsonStr(string s)
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
    }

    // ==========================================================================
    // inf2cat.exe 探测：WindowsSdkDir 环境变量 + Windows Kits 双根；
    // 版本目录降序；子目录探测顺序 ARM64\ → x86\ → x64\ → 版本根
    // （ARM64 机上 x86 版经模拟层也可运行，探测到任一即可用）
    // ==========================================================================
    internal static class Inf2CatLocator
    {
        public const string SubOrderText = "ARM64\\ → x86\\ → x64\\ → 版本根目录";
        private static readonly string[] SubDirs = new string[] { "ARM64", "x86", "x64", "" };

        public static List<string> SearchRoots()
        {
            List<string> roots = new List<string>();
            try
            {
                string sdk = Environment.GetEnvironmentVariable("WindowsSdkDir");
                if (!string.IsNullOrEmpty(sdk)) roots.Add(Path.Combine(sdk.TrimEnd('\\'), "bin"));
            }
            catch { }
            roots.Add(@"C:\Program Files (x86)\Windows Kits\10\bin");
            roots.Add(@"C:\Program Files\Windows Kits\10\bin");
            return roots;
        }

        public static List<string> VersionDirsOf(string binRoot)
        {
            List<string> dirs = new List<string>();
            try
            {
                if (Directory.Exists(binRoot))
                {
                    string[] found = Directory.GetDirectories(binRoot);
                    Array.Sort(found, delegate(string a, string b)
                    {
                        return string.Compare(b, a, StringComparison.OrdinalIgnoreCase);
                    });
                    dirs.AddRange(found);
                }
            }
            catch { }
            return dirs;
        }

        // 探测路径清单（自检 /selftest-sdk 输出用）
        public static string DescribeSearch()
        {
            StringBuilder sb = new StringBuilder();
            foreach (string root in SearchRoots())
            {
                sb.Append("  根：" + root + (Directory.Exists(root) ? "  [存在]" : "  [不存在]"));
                List<string> vdirs = VersionDirsOf(root);
                if (vdirs.Count > 0) sb.Append("；版本目录(降序)：" + string.Join(", ", vdirs.ToArray()));
                sb.Append("\r\n");
            }
            sb.Append("  子目录探测顺序：" + SubOrderText + "\r\n");
            return sb.ToString();
        }

        // 取版本号最高的命中（版本目录字符串降序，10.0.26100 排在 10.0.22621 前）
        public static string Find()
        {
            foreach (string binRoot in SearchRoots())
            {
                foreach (string vdir in VersionDirsOf(binRoot))
                {
                    foreach (string sub in SubDirs)
                    {
                        string p = sub.Length == 0 ? Path.Combine(vdir, "inf2cat.exe") : Path.Combine(vdir, sub, "inf2cat.exe");
                        if (File.Exists(p)) return p;
                    }
                }
            }
            return null;
        }
    }

    // ==========================================================================
    // Windows SDK 引导：官方安装器直链下载 → SigningTools 静默最小安装 → 探测；
    // 静默退出码非 0 或探测仍失败 → 自动转 GUI 安装器 → 用户装完点「重新检测 Inf2Cat」
    // ==========================================================================
    internal static class SdkInstaller
    {
        // 微软官方 Windows SDK 安装器直链（Learn 官方页数据；x86 二进制，WoA 模拟层可运行）
        public const string DownloadUrl = "https://go.microsoft.com/fwlink/?linkid=2382519";

        // 官方下载页（次入口）
        public const string OfficialPageUrl = "https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads";

        // 本地安装器落盘位置
        public static string InstallerPath()
        {
            return Path.Combine(Path.GetTempPath(), "winsdksetup.exe");
        }

        // 静默最小安装：SigningTools 组件含 Inf2Cat/Signtool
        public static string SilentArgs()
        {
            return "/features OptionId.SigningTools /q /norestart";
        }

        // 静默安装按钮文案
        public static string InstallButtonText()
        {
            return "安装 Windows SDK 签名工具\r\n（自动下载微软官方安装器，含 Inf2Cat）";
        }
    }

    // ==========================================================================
    // 进程执行与 PowerShell（EncodedCommand 规避引号转义；输出统一 UTF-8 解码，
    // 修复 cmd/powershell 中文输出乱码）
    // ==========================================================================
    internal class ProcResult
    {
        public int ExitCode;
        public string Output;
    }

    internal static class Proc
    {
        // 子进程输出统一按 UTF-8 解码
        public static readonly Encoding OutputEncoding = Encoding.UTF8;

        public static ProcResult Run(string exe, string arguments, int timeoutMs)
        {
            ProcResult r = new ProcResult();
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo(exe, arguments);
                psi.UseShellExecute = false;
                psi.RedirectStandardOutput = true;
                psi.RedirectStandardError = true;
                psi.CreateNoWindow = true;
                psi.StandardOutputEncoding = OutputEncoding;
                psi.StandardErrorEncoding = OutputEncoding;
                using (Process p = Process.Start(psi))
                {
                    string so = p.StandardOutput.ReadToEnd();
                    string se = p.StandardError.ReadToEnd();
                    if (!p.WaitForExit(timeoutMs))
                    {
                        try { p.Kill(); } catch { }
                        r.Output = so + se + "\r\n[执行超时，进程已终止]";
                        r.ExitCode = -1;
                        return r;
                    }
                    r.Output = so + se;
                    r.ExitCode = p.ExitCode;
                }
            }
            catch (Exception ex)
            {
                r.Output = "[启动进程异常] " + ex.Message;
                r.ExitCode = -1;
            }
            return r;
        }
    }

    internal static class Psh
    {
        public static ProcResult Run(string script, int timeoutMs)
        {
            string b64 = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
            return Proc.Run("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -EncodedCommand " + b64, timeoutMs);
        }
    }

    // ==========================================================================
    // winspool P/Invoke：OpenPrinter / GetPrinter(2) / EnumPrinterDrivers(2)
    // ==========================================================================
    internal static class WinspoolNative
    {
        [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);

        [DllImport("winspool.drv", SetLastError = true)]
        public static extern bool ClosePrinter(IntPtr hPrinter);

        [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool GetPrinter(IntPtr hPrinter, int level, IntPtr pBuffer, int cbBuf, out int pcbNeeded);

        [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool EnumPrinterDrivers(string pName, string pEnvironment, int level,
            IntPtr pDriverEnum, int cbBuf, out int pcbNeeded, out int lpcReturned);

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

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct DRIVER_INFO_2
        {
            public string pName;         // 驱动名（打印模型下即 INF 型号名）
            public string pEnvironment;
            public string pDriverPath;
            public string pDataFile;
            public string pConfigFile;
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

        // 枚举驱动 store 中的驱动名（签名安装路线续装后验证 27 型号全部进 store）
        public static List<string> EnumDriverNames()
        {
            List<string> names = new List<string>();
            int needed, returned;
            EnumPrinterDrivers(null, null, 2, IntPtr.Zero, 0, out needed, out returned);
            if (needed <= 0) return names;
            IntPtr buf = Marshal.AllocHGlobal(needed);
            try
            {
                if (!EnumPrinterDrivers(null, null, 2, buf, needed, out needed, out returned)) return names;
                int size = Marshal.SizeOf(typeof(DRIVER_INFO_2));
                for (int i = 0; i < returned; i++)
                {
                    DRIVER_INFO_2 d = (DRIVER_INFO_2)Marshal.PtrToStructure(IntPtr.Add(buf, i * size), typeof(DRIVER_INFO_2));
                    if (!string.IsNullOrEmpty(d.pName)) names.Add(d.pName);
                }
            }
            finally { Marshal.FreeHGlobal(buf); }
            return names;
        }
    }

    // ==========================================================================
    // 安装日志：TextBox 实时回显 + %ProgramData%\LenovoLJ2400WoA\setup.log 落盘
    // ==========================================================================
    internal class SetupLogger
    {
        private readonly TextBox _box;
        private readonly string _logPath;

        public string LogPath { get { return _logPath; } }

        public SetupLogger(TextBox box, string logPath)
        {
            _box = box;
            _logPath = logPath;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(_logPath));
                if (!File.Exists(_logPath))
                    File.WriteAllText(_logPath, "==== LJ2400WoA 安装日志 ====" + Environment.NewLine);
            }
            catch { /* 日志目录创建失败不阻断安装主流程 */ }
        }

        public void Log(string msg)
        {
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + msg;
            try
            {
                if (_box != null && _box.IsHandleCreated && !_box.IsDisposed)
                    _box.BeginInvoke(new Action(delegate { _box.AppendText(line + Environment.NewLine); }));
            }
            catch { /* 窗体关闭中的竞态，忽略 */ }
            try { File.AppendAllText(_logPath, line + Environment.NewLine, Encoding.UTF8); }
            catch { /* 日志写盘失败不阻断主流程 */ }
        }
    }

    // ==========================================================================
    // 签名安装路线签名工作流：inf2cat → 自签 .cat → 证书入 TrustedPublisher → testsigning
    // ==========================================================================
    internal static class SigningWorkflow
    {
        // 全部成功返回 true；每步失败都留日志与可操作提示
        public static bool Run(string inf2catPath, string driverDir, bool skipTestSigning, SetupLogger logger)
        {
            // ① inf2cat 生成驱动目录（.cat 产出在 driverDir 内）
            logger.Log("[签名①] \"" + inf2catPath + "\" /driver:\"" + driverDir + "\" /os:10_X64,10_ARM64");
            ProcResult r = Proc.Run(inf2catPath, "/driver:\"" + driverDir + "\" /os:10_X64,10_ARM64", 300000);
            logger.Log("[签名①] inf2cat 退出码 " + r.ExitCode + "\r\n" + Indent(r.Output));
            if (r.ExitCode != 0)
            {
                logger.Log("[签名①] 失败。常见原因：INF 的 [Version] 节缺少 CatalogFile 指令" +
                    "（需 CatalogFile.NTx64 / CatalogFile.NTarm64 与 /os 列表对应），由驱动包生成任务补齐后重试。");
                return false;
            }
            string[] cats = Directory.GetFiles(driverDir, "*.cat");
            if (cats.Length == 0)
            {
                logger.Log("[签名①] inf2cat 成功但目录内未找到 .cat——检查 INF 的 CatalogFile 指令。");
                return false;
            }
            logger.Log("[签名①] 已生成目录文件：" + string.Join("；", cats));

            // ②③④ 自签 + 证书入两个 TrustedPublisher（一个 EncodedCommand 脚本内完成）
            string script = @"$ErrorActionPreference='Stop'
$c = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq '" + Program.CertSubject + @"' } | Select-Object -First 1
if (-not $c) { $c = New-SelfSignedCertificate -Type CodeSigningCert -Subject '" + Program.CertSubject + @"' -CertStoreLocation Cert:\CurrentUser\My }
$s = Set-AuthenticodeSignature -FilePath '" + cats[0] + @"' -Certificate $c
if ($s.Status -ne 'Valid') { throw ('签名失败: ' + $s.Status) }
$cer = Join-Path $env:TEMP 'LenovoWoATest.cer'
Export-Certificate -Cert $c -FilePath $cer -Type CERT | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation Cert:\LocalMachine\TrustedPublisher | Out-Null
Import-Certificate -FilePath $cer -CertStoreLocation Cert:\CurrentUser\TrustedPublisher | Out-Null
Write-Output ('SIGN_OK ' + $s.Status)";
            logger.Log("[签名②] 自签 " + Path.GetFileName(cats[0]) + "（证书 " + Program.CertSubject + "）+ 导入 TrustedPublisher（LocalMachine/CurrentUser）");
            ProcResult pr = Psh.Run(script, 180000);
            logger.Log("[签名②] powershell 退出码 " + pr.ExitCode + "\r\n" + Indent(pr.Output));
            if (pr.ExitCode != 0 || pr.Output == null || !pr.Output.Contains("SIGN_OK"))
            {
                logger.Log("[签名②] 失败。可操作提示：以管理员重跑；检查 Cert:\\CurrentUser\\My 是否可写；确认 .cat 未被占用。");
                return false;
            }

            // ⑤ bcdedit /set testsigning on（已开启则跳过）
            if (skipTestSigning)
            {
                logger.Log("[签名⑤] testsigning 此前已开启，跳过 bcdedit。");
            }
            else
            {
                ProcResult bc = Proc.Run("bcdedit.exe", "/set testsigning on", 60000);
                logger.Log("[签名⑤] bcdedit /set testsigning on 退出码 " + bc.ExitCode + "\r\n" + Indent(bc.Output));
                if (bc.ExitCode != 0)
                {
                    logger.Log("[签名⑤] 失败。可操作提示：确认以管理员运行（本安装器清单已 requireAdministrator）。");
                    return false;
                }
            }
            return true;
        }

        // bcdedit 当前 testsigning 状态（zh-CN 输出值仍为 Yes/No，两种都查）
        public static bool IsTestSigningOn(ProcResult bcdeditOutput)
        {
            string o = bcdeditOutput.Output ?? "";
            return o.Contains("testsigning") && (o.Contains("Yes") || o.Contains("是"));
        }

        private static string Indent(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return "    " + s.Replace("\r\n", "\r\n    ").TrimEnd() + "\r\n";
        }
    }

    // ==========================================================================
    // 自检入口实现（/selftest-state、/selftest-arch、/selftest-sdk）
    // ==========================================================================
    internal static class SelfTest
    {
        // 状态机读写测试：四状态往返 + 缺失/损坏容错
        public static int RunState(string outPath)
        {
            StringBuilder sb = new StringBuilder("==== LJ2400Setup 自检：state.json 读写 ====\r\n");
            int fail = 0;
            try { File.Delete(StateStore.StatePath()); } catch { }

            StateRecord missing = StateStore.Read();
            Check(sb, ref fail, missing == null, "缺失 state.json 时 Read() 返回 null");

            string[] states = new string[]
            {
                InstallStates.PendingSignature, InstallStates.PendingReboot,
                InstallStates.Ready, InstallStates.Installed
            };
            foreach (string st in states)
            {
                StateRecord w = new StateRecord();
                w.State = st;
                w.Route = "signed";
                w.Model = "Lenovo LJ2405";
                w.Queue = "自检队列" + st;
                w.Connection = "net";
                w.Ip = "192.168.1.100";
                w.Note = "自检写入";
                w.Timestamp = "2026-01-01 00:00:00";
                StateStore.Write(w);
                StateRecord g = StateStore.Read();
                bool ok = g != null && g.State == st && g.Model == "Lenovo LJ2405"
                    && g.Queue == "自检队列" + st && g.Connection == "net" && g.Ip == "192.168.1.100";
                Check(sb, ref fail, ok, "状态 " + st + " 写入/读回八字段一致");
            }

            File.WriteAllText(StateStore.StatePath(), "{{{ not json !!!", Encoding.UTF8);
            StateRecord corrupt = StateStore.Read();
            Check(sb, ref fail, corrupt == null, "损坏 state.json 容错返回 null");

            // 清场：自检不留脏状态
            try { File.Delete(StateStore.StatePath()); } catch { }

            sb.Append(fail == 0 ? "[PASS] state.json 读写测试全部通过\r\n" : "[FAIL] " + fail + " 项失败\r\n");
            File.WriteAllText(outPath, sb.ToString(), Encoding.UTF8);
            return fail == 0 ? 0 : 1;
        }

        // ARM64 检测函数单测：P/Invoke 可用 + 返回值在已知集合 + 与环境变量交叉验证
        public static int RunArch(string outPath)
        {
            StringBuilder sb = new StringBuilder("==== LJ2400Setup 自检：ARM64 检测 ====\r\n");
            int fail = 0;
            ushort arch = ArchDetect.GetArch();
            sb.Append("GetNativeSystemInfo().wProcessorArchitecture = " + arch + " → " + ArchDetect.ArchName(arch) + "\r\n");
            Check(sb, ref fail,
                arch == ArchDetect.PROCESSOR_ARCHITECTURE_INTEL || arch == ArchDetect.PROCESSOR_ARCHITECTURE_AMD64
                || arch == ArchDetect.PROCESSOR_ARCHITECTURE_ARM64,
                "返回值属于已知架构集合 {0=x86, 9=x64, 12=ARM64}");
            string env = (Environment.GetEnvironmentVariable("PROCESSOR_ARCHITECTURE") ?? "").ToUpperInvariant();
            sb.Append("环境变量 PROCESSOR_ARCHITECTURE = " + env + "\r\n");
            if (arch == ArchDetect.PROCESSOR_ARCHITECTURE_AMD64)
                Check(sb, ref fail, env == "AMD64", "x64 检测与环境变量 AMD64 一致");
            else if (arch == ArchDetect.PROCESSOR_ARCHITECTURE_ARM64)
                Check(sb, ref fail, env == "ARM64", "ARM64 检测与环境变量一致（WoA 原生进程）");
            Check(sb, ref fail, ArchDetect.IsArm64() == (arch == ArchDetect.PROCESSOR_ARCHITECTURE_ARM64),
                "IsArm64() 与 GetArch()==12 判定一致");
            sb.Append(fail == 0 ? "[PASS] ARM64 检测函数单测通过\r\n" : "[FAIL] " + fail + " 项失败\r\n");
            File.WriteAllText(outPath, sb.ToString(), Encoding.UTF8);
            return fail == 0 ? 0 : 1;
        }

        // SDK 引导单测：打印下载直链、静默命令、探测路径顺序（不实际下载）
        public static int RunSdk(string outPath)
        {
            StringBuilder sb = new StringBuilder("==== LJ2400Setup 自检：SDK 引导 ====\r\n");
            int fail = 0;
            sb.Append("当前架构：" + ArchDetect.ArchName(ArchDetect.GetArch()) +
                (ArchDetect.IsArm64() ? "（WoA）" : "") + "\r\n");
            sb.Append("下载直链：" + SdkInstaller.DownloadUrl + "（微软官方 Windows SDK 安装器，x86 二进制，WoA 模拟层可运行）\r\n");
            sb.Append("本地安装器路径：" + SdkInstaller.InstallerPath() + "\r\n");
            sb.Append("静默命令：winsdksetup.exe " + SdkInstaller.SilentArgs() + "（SigningTools 组件含 Inf2Cat/Signtool）\r\n");
            sb.Append("异常路径：静默退出码非 0 或探测仍失败 → 自动转 GUI 安装器 → 「重新检测 Inf2Cat」\r\n");
            sb.Append("官方下载页：" + SdkInstaller.OfficialPageUrl + "\r\n");
            sb.Append("子进程输出解码：" + Proc.OutputEncoding.WebName + "\r\n");
            Check(sb, ref fail, SdkInstaller.DownloadUrl == "https://go.microsoft.com/fwlink/?linkid=2382519",
                "官方安装器下载直链常量正确");
            Check(sb, ref fail, SdkInstaller.SilentArgs().Contains("OptionId.SigningTools")
                && SdkInstaller.SilentArgs().Contains("/q") && SdkInstaller.SilentArgs().Contains("/norestart"),
                "静默安装参数含 SigningTools 组件 + /q + /norestart");
            Check(sb, ref fail, SdkInstaller.OfficialPageUrl.StartsWith("https://learn.microsoft.com/"),
                "官方下载页 URL 常量正确");
            Check(sb, ref fail, Proc.OutputEncoding == Encoding.UTF8,
                "子进程输出统一 UTF-8 解码");
            Check(sb, ref fail, Inf2CatLocator.SearchRoots().Count >= 2,
                "inf2cat 探测根数量 ≥2（Windows Kits 双根常驻）");
            Check(sb, ref fail, Inf2CatLocator.SubOrderText.Contains("ARM64") && Inf2CatLocator.SubOrderText.Contains("x86")
                && Inf2CatLocator.SubOrderText.Contains("x64"),
                "子目录探测顺序含 ARM64\\、x86\\、x64\\（ARM64 机上 x86 版经模拟层可用）");
            sb.Append(Inf2CatLocator.DescribeSearch());
            string hit = Inf2CatLocator.Find();
            sb.Append("inf2cat 命中：" + (hit ?? "未检测到（本机未装 SDK 属预期，UI 引导安装）") + "\r\n");
            sb.Append(fail == 0 ? "[PASS] SDK 引导自检通过\r\n" : "[FAIL] " + fail + " 项失败\r\n");
            File.WriteAllText(outPath, sb.ToString(), Encoding.UTF8);
            return fail == 0 ? 0 : 1;
        }

        private static void Check(StringBuilder sb, ref int fail, bool ok, string name)
        {
            sb.Append((ok ? "  [PASS] " : "  [FAIL] ") + name + "\r\n");
            if (!ok) fail++;
        }
    }

    // ==========================================================================
    // 安装主窗体
    // 仅两条路线（ARM64/x64 一致）：签名安装路线（推荐）／ IPP 路线（基础打印）
    // ==========================================================================
    internal class SetupForm : Form
    {
        private readonly string _baseDir;        // exe 所在目录
        private readonly string _driverSrcDir;   // exe 同目录 driver\
        private readonly string _workRoot;       // %ProgramData%\LenovoLJ2400WoA
        private readonly string _driverDstDir;   // %ProgramData%\LenovoLJ2400WoA\driver
        private readonly string _infDstPath;     // 目标 INF 路径
        private string _inf2catPath;             // inf2cat.exe 探测缓存

        // 路线选择：签名安装路线 / IPP 路线
        private RadioButton _rbRouteSigned;
        private RadioButton _rbRouteIpp;
        private Label _lblRecommend;             // 自动推荐
        private Label _lblRouteHint;             // 路线动态提示
        private Button _btnInstallSdk;           // 一键下载并安装 SDK 签名工具（官方安装器直链）
        private Button _btnSdkPage;              // 打开官方下载页（次入口）
        private Button _btnRedetect;             // 重新检测 Inf2Cat（GUI 安装完成后用）
        private ProgressBar _pbarSdk;            // 安装器下载进度
        private Button _btnIppAdd;               // IPP 自动添加
        private Button _btnIppSettings;          // 打开系统打印设置

        private RadioButton _rbUsb;
        private RadioButton _rbNet;
        private RadioButton _rbDriverOnly;
        private TextBox _txtIp;
        private ComboBox _cboModel;
        private TextBox _txtQueue;
        private TextBox _txtLog;
        private Button _btnInstall;
        private Button _btnOpenManager;
        private Label _lblLogPath;
        private SetupLogger _logger;
        private bool _installing;

        public SetupForm()
        {
            _baseDir = AppDomain.CurrentDomain.BaseDirectory;
            _driverSrcDir = Path.Combine(_baseDir, "driver");
            _workRoot = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                "LenovoLJ2400WoA");
            _driverDstDir = Path.Combine(_workRoot, "driver");
            _infDstPath = Path.Combine(_driverDstDir, Program.InfFileName);

            BuildUi();

            _logger = new SetupLogger(_txtLog, Path.Combine(_workRoot, "setup.log"));
            _lblLogPath.Text = "日志：" + Path.Combine(_workRoot, "setup.log") + "　状态机：" + StateStore.StatePath();

            FillModels();
            TryDetectUsbDevice();

            _inf2catPath = Inf2CatLocator.Find();
            _logger.Log("本机架构：" + ArchDetect.ArchName(ArchDetect.GetArch()) +
                (ArchDetect.IsArm64() ? "（WoA）" : "") + "；inf2cat：" + (_inf2catPath ?? "未检测到"));
            _logger.Log("驱动包来源：" + _driverSrcDir);

            _lblRecommend.Text = ComputeRecommendation();
            UpdateRouteUi();
        }

        // ------------------------------------------------------------------
        // UI 构建（简体中文；两条路线：签名安装 → IPP）
        // ------------------------------------------------------------------
        private void BuildUi()
        {
            Text = "联想 LJ24/LJ26/M74/M76 系列打印机驱动安装（Windows on ARM / x64 通用）";
            ClientSize = new System.Drawing.Size(720, 700);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;

            // —— 签名安装路线（推荐，主推默认）——
            _rbRouteSigned = new RadioButton();
            _rbRouteSigned.Text = "签名安装路线（推荐）";
            _rbRouteSigned.SetBounds(16, 34, 688, 22);
            _rbRouteSigned.Checked = true;

            // —— IPP 路线（基础打印，第二入口）——
            _rbRouteIpp = new RadioButton();
            _rbRouteIpp.Text = "IPP 路线（基础打印）";
            _rbRouteIpp.SetBounds(16, 58, 688, 22);

            _lblRecommend = new Label();
            _lblRecommend.ForeColor = System.Drawing.Color.DarkGreen;
            _lblRecommend.SetBounds(16, 84, 688, 18);

            _lblRouteHint = new Label();
            _lblRouteHint.ForeColor = System.Drawing.Color.Gray;
            _lblRouteHint.SetBounds(16, 106, 534, 60);

            _btnInstallSdk = new Button();
            _btnInstallSdk.Text = SdkInstaller.InstallButtonText();
            _btnInstallSdk.SetBounds(560, 106, 146, 44);
            _btnInstallSdk.Visible = false;
            _btnInstallSdk.Click += _btnInstallSdk_Click;

            _btnSdkPage = new Button();
            _btnSdkPage.Text = "打开官方下载页";
            _btnSdkPage.SetBounds(560, 154, 146, 28);
            _btnSdkPage.Visible = false;
            _btnSdkPage.Click += _btnSdkPage_Click;

            _btnRedetect = new Button();
            _btnRedetect.Text = "重新检测 Inf2Cat";
            _btnRedetect.SetBounds(560, 186, 146, 28);
            _btnRedetect.Visible = false;
            _btnRedetect.Click += _btnRedetect_Click;

            _pbarSdk = new ProgressBar();
            _pbarSdk.SetBounds(560, 218, 146, 18);
            _pbarSdk.Minimum = 0;
            _pbarSdk.Maximum = 100;
            _pbarSdk.Visible = false;

            _btnIppAdd = new Button();
            _btnIppAdd.Text = "通过 IPP 自动添加打印机";
            _btnIppAdd.SetBounds(560, 106, 146, 28);
            _btnIppAdd.Visible = false;
            _btnIppAdd.Click += _btnIppAdd_Click;

            _btnIppSettings = new Button();
            _btnIppSettings.Text = "打开系统打印设置手动添加";
            _btnIppSettings.SetBounds(560, 138, 146, 28);
            _btnIppSettings.Visible = false;
            _btnIppSettings.Click += _btnIppSettings_Click;

            GroupBox grpConn = new GroupBox();
            grpConn.Text = "连接方式";
            grpConn.SetBounds(12, 242, 696, 112);

            _rbUsb = new RadioButton();
            _rbUsb.Text = "USB 连接（自动识别已接入的设备与端口）";
            _rbUsb.SetBounds(16, 24, 660, 22);
            _rbUsb.Checked = true;

            _rbNet = new RadioButton();
            _rbNet.Text = "网络连接（TCP/IP 端口，RAW 9100）";
            _rbNet.SetBounds(16, 50, 660, 22);

            _rbDriverOnly = new RadioButton();
            _rbDriverOnly.Text = "仅安装驱动，不创建打印队列";
            _rbDriverOnly.SetBounds(16, 76, 660, 22);

            _rbNet.CheckedChanged += _rbNet_CheckedChanged;
            grpConn.Controls.Add(_rbUsb);
            grpConn.Controls.Add(_rbNet);
            grpConn.Controls.Add(_rbDriverOnly);

            Label lblIp = new Label();
            lblIp.Text = "打印机 IP / 主机名：";
            lblIp.SetBounds(16, 352, 120, 20);

            _txtIp = new TextBox();
            _txtIp.SetBounds(142, 349, 200, 23);
            _txtIp.Enabled = false;

            Label lblModel = new Label();
            lblModel.Text = "INF 型号名：";
            lblModel.SetBounds(16, 384, 120, 20);

            _cboModel = new ComboBox();
            _cboModel.DropDownStyle = ComboBoxStyle.DropDownList;
            _cboModel.SetBounds(142, 381, 280, 23);
            _cboModel.SelectedIndexChanged += _cboModel_SelectedIndexChanged;

            Label lblQueue = new Label();
            lblQueue.Text = "打印队列名称：";
            lblQueue.SetBounds(16, 416, 120, 20);

            _txtQueue = new TextBox();
            _txtQueue.SetBounds(142, 413, 280, 23);

            _btnInstall = new Button();
            _btnInstall.Text = "开始安装";
            _btnInstall.SetBounds(16, 450, 150, 34);
            _btnInstall.Click += _btnInstall_Click;

            _btnOpenManager = new Button();
            _btnOpenManager.Text = "打开打印机管理";
            _btnOpenManager.SetBounds(184, 450, 180, 34);
            _btnOpenManager.Enabled = false;
            _btnOpenManager.Click += _btnOpenManager_Click;

            _txtLog = new TextBox();
            _txtLog.Multiline = true;
            _txtLog.ReadOnly = true;
            _txtLog.ScrollBars = ScrollBars.Vertical;
            _txtLog.Font = new System.Drawing.Font("Consolas", 9F);
            _txtLog.SetBounds(12, 492, 696, 176);
            _txtLog.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;

            _lblLogPath = new Label();
            _lblLogPath.ForeColor = System.Drawing.Color.Gray;
            _lblLogPath.SetBounds(16, 672, 690, 18);
            _lblLogPath.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;

            Controls.Add(_rbRouteSigned);
            Controls.Add(_rbRouteIpp);
            Controls.Add(_lblRecommend);
            Controls.Add(_lblRouteHint);
            Controls.Add(_btnInstallSdk);
            Controls.Add(_btnSdkPage);
            Controls.Add(_btnRedetect);
            Controls.Add(_pbarSdk);
            Controls.Add(_btnIppAdd);
            Controls.Add(_btnIppSettings);
            Controls.Add(grpConn);
            Controls.Add(lblIp);
            Controls.Add(_txtIp);
            Controls.Add(lblModel);
            Controls.Add(_cboModel);
            Controls.Add(lblQueue);
            Controls.Add(_txtQueue);
            Controls.Add(_btnInstall);
            Controls.Add(_btnOpenManager);
            Controls.Add(_txtLog);
            Controls.Add(_lblLogPath);

            _rbRouteSigned.CheckedChanged += RouteRadio_CheckedChanged;
            _rbRouteIpp.CheckedChanged += RouteRadio_CheckedChanged;
        }

        // ------------------------------------------------------------------
        // 当前路线：0=签名安装路线（默认）/ 1=IPP 路线
        // ------------------------------------------------------------------
        private int CurrentRoute()
        {
            if (_rbRouteIpp.Checked) return 1;
            return 0;
        }

        // ------------------------------------------------------------------
        // 型号表填充：常量 27 项 + INF 解析备用路径
        // ------------------------------------------------------------------
        private void FillModels()
        {
            _cboModel.Items.Clear();
            foreach (string m in Program.InfModelNames) _cboModel.Items.Add(m);
            foreach (string m in ParseInfModelNames(Path.Combine(_driverSrcDir, Program.InfFileName)))
            {
                if (!_cboModel.Items.Contains(m)) _cboModel.Items.Add(m);
            }
        }

        // 备用路径：从 INF 文本解析 "Lenovo xxx" 型号名（驱动包更新时自动适配）
        public static List<string> ParseInfModelNames(string infPath)
        {
            List<string> result = new List<string>();
            try
            {
                if (!File.Exists(infPath)) return result;
                foreach (string raw in File.ReadAllLines(infPath))
                {
                    string line = raw.Trim();
                    if (line.StartsWith(";")) continue;
                    foreach (Match m in Regex.Matches(line, "\"([^\"]*Lenovo[^\"]*)\"", RegexOptions.IgnoreCase))
                    {
                        string name = m.Groups[1].Value.Trim();
                        if (name.Length > 0 && !result.Contains(name)) result.Add(name);
                    }
                }
            }
            catch { }
            return result;
        }

        // ------------------------------------------------------------------
        // IPP 能力型号：规格指定 DN/DW/DNA/DXF/W 后缀；
        // DNF/DHF/DWA 为同族网络/无线/传真一体后缀，一并收录
        // ------------------------------------------------------------------
        public static List<string> IppCapableModels()
        {
            string[] suffixes = new string[] { "DN", "DW", "DNA", "DXF", "W", "DNF", "DHF", "DWA" };
            List<string> result = new List<string>();
            foreach (string m in Program.InfModelNames)
            {
                foreach (string s in suffixes)
                {
                    if (m.EndsWith(s, StringComparison.OrdinalIgnoreCase)) { result.Add(m); break; }
                }
            }
            return result;
        }

        // ------------------------------------------------------------------
        // 路线自动推荐（两架构 UI 一致：签名安装路线为主推、IPP 路线第二入口）
        // ------------------------------------------------------------------
        private string ComputeRecommendation()
        {
            bool arm = ArchDetect.IsArm64();
            if (arm)
            {
                if (_inf2catPath != null) return "本机 ARM64：推荐签名安装路线（inf2cat 已就绪）";
                return "本机 ARM64：推荐签名安装路线（先安装 Windows SDK 签名工具获取 Inf2Cat）；急用打印可先用 IPP 路线（基础打印）";
            }
            if (_inf2catPath != null) return "本机 x64：推荐签名安装路线（inf2cat 已就绪）";
            return "本机 x64：推荐签名安装路线（先安装 Windows SDK 签名工具获取 Inf2Cat）；急用可先用 IPP 路线（基础打印）";
        }

        // ------------------------------------------------------------------
        // 路线切换 UI
        // ------------------------------------------------------------------
        private void RouteRadio_CheckedChanged(object sender, EventArgs e)
        {
            UpdateRouteUi();
        }

        private void UpdateRouteUi()
        {
            int route = CurrentRoute();
            _btnInstallSdk.Visible = false;
            _btnSdkPage.Visible = false;
            _btnRedetect.Visible = false;
            _btnIppAdd.Visible = false;
            _btnIppSettings.Visible = false;

            if (route == 0)
            {
                _cboModel.Enabled = true;
                _txtIp.Enabled = _rbNet.Checked;
                if (_inf2catPath == null)
                {
                    _lblRouteHint.Text = "签名安装路线 前置：未检测到 inf2cat.exe（Windows SDK 组件）。点右侧按钮自动下载微软官方安装器" +
                        "并静默安装签名工具组件，\r\n或点「打开官方下载页」手动获取安装器（官网提供 ARM64 兼容组件可选）。";
                    _btnInstallSdk.Visible = true;
                    _btnSdkPage.Visible = true;
                    _btnRedetect.Visible = true;
                }
                else
                {
                    _lblRouteHint.Text = "签名安装路线 就绪（inf2cat：" + _inf2catPath + "）" +
                        "\r\n流程：inf2cat → 自签 .cat → 证书入 TrustedPublisher → testsigning on → 重启后自动续装 27 型号";
                }
            }
            else
            {
                _lblRouteHint.Text = "IPP 路线（免驱动、免签名，无需 SDK，基础打印立即可用）：网络型号 " +
                    string.Join("、", IppCapableModels().ToArray()) +
                    "\r\nIPP 模式下省墨等 OEM 附加功能由设备 Web 管理（http://<ip>/）设置。";
                _btnIppAdd.Visible = true;
                _btnIppSettings.Visible = true;
                _cboModel.Enabled = false;
                _rbNet.Checked = true;
                if (_txtQueue.Text.Trim().Length == 0) _txtQueue.Text = "IPP 打印机";
            }
        }

        // ------------------------------------------------------------------
        // USB 设备识别
        // ------------------------------------------------------------------
        private void TryDetectUsbDevice()
        {
            string model = DetectUsbModel();
            if (model != null)
            {
                if (_cboModel.Items.Contains(model)) _cboModel.SelectedItem = model;
                _rbUsb.Checked = true;
                _logger.Log("[USB] 已识别接入设备：" + model + "，型号已自动选中");
            }
        }

        private string DetectUsbModel()
        {
            try
            {
                using (RegistryKey root = Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Enum\USBPRINT"))
                {
                    if (root == null) return null;
                    foreach (string devKey in root.GetSubKeyNames())
                    {
                        using (RegistryKey dev = root.OpenSubKey(devKey))
                        {
                            if (dev == null) continue;
                            foreach (string instKey in dev.GetSubKeyNames())
                            {
                                using (RegistryKey inst = dev.OpenSubKey(instKey))
                                {
                                    if (inst == null) continue;
                                    string desc = ReadUsbFriendlyName(inst);
                                    if (!string.IsNullOrEmpty(desc))
                                    {
                                        string model = MatchModelFromDescription(desc);
                                        if (model != null) return model;
                                    }
                                }
                            }
                            string modelFromKey = MatchModelFromDescription(devKey.Replace('_', ' '));
                            if (modelFromKey != null) return modelFromKey;
                        }
                    }
                }
            }
            catch { }
            return null;
        }

        private static string ReadUsbFriendlyName(RegistryKey inst)
        {
            object v = inst.GetValue("FriendlyName");
            if (v == null) v = inst.GetValue("DeviceDesc");
            string s = v as string;
            if (string.IsNullOrEmpty(s)) return null;
            if (s.StartsWith("@"))
            {
                int semi = s.LastIndexOf(';');
                if (semi >= 0 && semi + 1 < s.Length) s = s.Substring(semi + 1);
            }
            return s;
        }

        private static string MatchModelFromDescription(string desc)
        {
            string norm = NormalizeName(desc);
            string best = null;
            int bestLen = -1;
            foreach (string model in Program.InfModelNames)
            {
                string needle = NormalizeName(model);
                if (needle.Length > bestLen && norm.Contains(needle)) { best = model; bestLen = needle.Length; }
            }
            if (best != null) return best;
            foreach (string model in Program.InfModelNames)
            {
                string needle = NormalizeName(model);
                if (needle.StartsWith("lenovo")) needle = needle.Substring(6);
                if (needle.Length > 3 && norm.Contains(needle) && needle.Length > bestLen)
                {
                    best = model;
                    bestLen = needle.Length;
                }
            }
            return best;
        }

        private static string NormalizeName(string s)
        {
            StringBuilder sb = new StringBuilder(s.Length);
            foreach (char ch in s.ToLowerInvariant())
            {
                if (char.IsLetterOrDigit(ch)) sb.Append(ch);
            }
            return sb.ToString();
        }

        private static List<string> EnumUsbPorts()
        {
            List<string> ports = new List<string>();
            try
            {
                using (RegistryKey root = Registry.LocalMachine.OpenSubKey(
                    @"SYSTEM\CurrentControlSet\Control\Print\Monitors\USB Monitor\Ports"))
                {
                    if (root != null) ports.AddRange(root.GetSubKeyNames());
                }
            }
            catch { }
            return ports;
        }

        // ------------------------------------------------------------------
        // 事件：网络模式启用 IP 输入框（IPP 路线除外）
        // ------------------------------------------------------------------
        private void _rbNet_CheckedChanged(object sender, EventArgs e)
        {
            if (CurrentRoute() != 1) _txtIp.Enabled = _rbNet.Checked;
        }

        private void _cboModel_SelectedIndexChanged(object sender, EventArgs e)
        {
            string m = _cboModel.SelectedItem as string;
            if (!string.IsNullOrEmpty(m) && CurrentRoute() != 1) _txtQueue.Text = m;
        }

        // ------------------------------------------------------------------
        // 启动状态机：pending_reboot 自动续装入口
        // ------------------------------------------------------------------
        protected override void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            HandlePendingState();
        }

        private async void HandlePendingState()
        {
            StateRecord st = StateStore.Read();
            if (st == null) return;
            _logger.Log("[状态机] state.json = " + st.State + "（route=" + st.Route + "，" + st.Timestamp + "）");

            if (st.State == InstallStates.PendingReboot)
            {
                DialogResult dr = MessageBox.Show(
                    "检测到上次「签名安装路线」已完成签名并等待重启。\r\n" +
                    "是否现在自动完成剩余安装？（pnputil 进 store → 27 型号验证 → 建队列）",
                    "继续安装", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (dr != DialogResult.Yes)
                {
                    _logger.Log("[状态机] 用户暂缓续装——可稍后重跑本安装器。");
                    return;
                }
                _installing = true;
                _btnInstall.Enabled = false;
                bool ok = false;
                try { ok = await ContinuePendingReboot(st); }
                catch (Exception ex)
                {
                    _logger.Log("[续装][异常] " + ex.GetType().Name + ": " + ex.Message);
                    MessageBox.Show("续装出现异常：" + ex.Message + "\r\n日志：\r\n" + _logger.LogPath,
                        "续装失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
                _installing = false;
                _btnInstall.Enabled = true;
                if (ok)
                {
                    _btnOpenManager.Enabled = File.Exists(Path.Combine(_workRoot, "LJ2400Manager.exe"));
                    _logger.Log("[续装] 完成：state=installed");
                    MessageBox.Show("重启后续装完成，打印队列已就绪。", "安装完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                else
                {
                    MessageBox.Show("续装未完成，查看日志定位：\r\n" + _logger.LogPath,
                        "续装未完成", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
                return;
            }

            if (st.State == InstallStates.PendingSignature)
            {
                _logger.Log("[状态机] 上次签名阶段未完成（" + st.Note + "）——可在签名安装路线重试，签名成功后会重新推进状态。");
                _lblRecommend.ForeColor = System.Drawing.Color.DarkOrange;
                _lblRecommend.Text = "上次签名阶段中断：" + st.Note + "（可在签名安装路线重试）";
                return;
            }
            if (st.State == InstallStates.Ready)
            {
                _logger.Log("[状态机] 驱动已进 store（ready）——可续建队列完成安装。");
            }
            if (st.State == InstallStates.Installed)
            {
                _logger.Log("[状态机] 上次安装已完成（installed）——可重新安装或直接使用管理工具。");
            }
        }

        // ------------------------------------------------------------------
        // 签名安装路线：inf2cat → 自签 → 信任链 → testsigning → 重启续装
        // ------------------------------------------------------------------
        private async Task<bool> RunRouteSigned(string model, string queueName, string ip, bool netMode, bool usbMode)
        {
            if (_inf2catPath == null)
            {
                MessageBox.Show("未检测到 inf2cat.exe（签名安装路线 前置条件）。\r\n请点「安装 Windows SDK 签名工具」自动下载微软官方安装器并静默安装，" +
                    "\r\n或点「打开官方下载页」手动获取安装器。",
                    "缺少 Inf2Cat", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return false;
            }
            if (!File.Exists(Path.Combine(_driverSrcDir, Program.InfFileName)))
                throw new FileNotFoundException("驱动包缺少 " + Program.InfFileName + "，请将 driver\\ 子目录放到 " + _baseDir,
                    Program.InfFileName);

            // 拷贝驱动包到工作目录（inf2cat 与后续 pnputil 都用这份）
            _logger.Log("[签名] 步骤1：复制驱动包 → " + _driverDstDir);
            CopyDriverPackage();

            StateRecord st = new StateRecord();
            st.State = InstallStates.PendingSignature;
            st.Route = "signed";
            st.Model = model;
            st.Queue = queueName;
            st.Connection = _rbDriverOnly.Checked ? "none" : (netMode ? "net" : "usb");
            st.Ip = netMode ? ip : "";
            st.Note = "inf2cat + 签名进行中";
            st.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            StateStore.Write(st);
            _logger.Log("[签名] state.json = pending_signature");

            // testsigning 现状（已开启则签名后免重启直接续装）
            ProcResult bc = await Task.Run(delegate { return Proc.Run("bcdedit.exe", "/enum {current}", 60000); });
            bool alreadyOn = SigningWorkflow.IsTestSigningOn(bc);
            _logger.Log("[签名] testsigning 当前状态：" + (alreadyOn ? "已开启（本次免重启）" : "未开启（签名后需重启一次）"));

            bool ok = await Task.Run(delegate { return SigningWorkflow.Run(_inf2catPath, _driverDstDir, alreadyOn, _logger); });
            if (!ok)
            {
                st.Note = "签名链失败，保留状态供重试";
                st.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                StateStore.Write(st);
                return false;
            }

            if (alreadyOn)
            {
                // 测试签名已开启：直接续装，免重启
                _logger.Log("[签名] 测试签名已开启，直接续装（pnputil → 队列）。");
                st.State = InstallStates.Ready;
                st.Note = "签名完成，直接续装";
                st.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                StateStore.Write(st);
                return await ContinuePendingReboot(st);
            }

            // 首次开启 testsigning：需重启，续装交由下次启动的状态机
            st.State = InstallStates.PendingReboot;
            st.Note = "签名完成，等待重启续装";
            st.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            StateStore.Write(st);
            _logger.Log("[签名] state.json = pending_reboot（已记录型号/队列/连接方式，重启后自动续装）");
            MessageBox.Show(
                "签名与测试签名配置完成。\r\n\r\n需重启一次（桌面会短暂显示「测试模式」水印，属正常现象）。\r\n" +
                "重启后再次运行本安装器，将自动完成剩余安装（pnputil 进 store → 建队列）。",
                "签名安装：等待重启", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return true;
        }

        // 重启后自动续装：pnputil → 27 型号 store 验证 → 建队列 → 验证 → installed
        private async Task<bool> ContinuePendingReboot(StateRecord st)
        {
            // ① 测试签名确认（提示性）
            ProcResult bc = await Task.Run(delegate { return Proc.Run("bcdedit.exe", "/enum {current}", 60000); });
            bool on = SigningWorkflow.IsTestSigningOn(bc);
            _logger.Log("[续装①] testsigning = " + (on ? "已开启" : "未开启（若 pnputil 仍被 0xBCB 拒，请管理员运行 bcdedit /set testsigning on 后重启再试）"));

            // ② pnputil 进 store
            string infSrc = Path.Combine(_driverDstDir, Program.InfFileName);
            if (!File.Exists(infSrc))
            {
                _logger.Log("[续装②] 工作目录驱动包缺失，重新从 exe 同目录复制。");
                CopyDriverPackage();
            }
            ProcResult p = await Task.Run(delegate { return Proc.Run("pnputil.exe", "/add-driver \"" + infSrc + "\" /install", 180000); });
            _logger.Log("[续装②] pnputil 退出码 " + p.ExitCode + "\r\n" + Indent(p.Output));
            if (!PnputilLooksOk(p))
            {
                StateRecord bad = new StateRecord();
                bad.State = InstallStates.PendingSignature;
                bad.Route = st.Route;
                bad.Model = st.Model;
                bad.Queue = st.Queue;
                bad.Connection = st.Connection;
                bad.Ip = st.Ip;
                bad.Note = "pnputil 被拒（0xBCB 常见）——确认测试签名与 TrustedPublisher 后重走签名安装路线";
                bad.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                StateStore.Write(bad);
                return false;
            }

            // ③ 27 型号进 store 验证（EnumPrinterDrivers）
            List<string> drivers = await Task.Run(delegate { return WinspoolNative.EnumDriverNames(); });
            int matched = CountInstalledModels(drivers);
            _logger.Log("[续装③] 驱动 store 型号验证：" + matched + "/27" +
                (matched == Program.InfModelNames.Length ? "（全部就位）" : "（部分进 store——包内全部型号共用同一 INF，缺失通常是 INF 型号节不全）"));
            if (matched == 0)
            {
                _logger.Log("[续装③] store 中未找到任何本系列驱动——pnputil 输出见上，检查 INF。");
                return false;
            }
            StateRecord ready = new StateRecord();
            ready.State = InstallStates.Ready;
            ready.Route = st.Route;
            ready.Model = st.Model;
            ready.Queue = st.Queue;
            ready.Connection = st.Connection;
            ready.Ip = st.Ip;
            ready.Note = "store 型号 " + matched + "/27";
            ready.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            StateStore.Write(ready);

            // ④ 建队列（仅驱动模式跳过）：用 Add-Printer -DriverName，失败降级 printui
            if (st.Connection == "none")
            {
                _logger.Log("[续装④] 连接方式为仅驱动，跳过建队列。");
                InstallManagerAndShortcuts();
                WriteInstalled(st, "仅驱动安装完成");
                return true;
            }
            string port = await ResolvePort(st.Connection == "net", st.Ip);
            bool qok = await CreateQueueViaAddPrinter(st.Queue, st.Model, port);
            if (!qok)
            {
                _logger.Log("[续装④] Add-Printer 失败，降级 printui /if。");
                qok = await Task.Run(delegate { return RunPrintuiInstall(st.Queue, infSrc, port, st.Model); });
            }
            if (!qok) return false;

            // ⑤ 队列验证
            WinspoolNative.PRINTER_INFO_2? info = WinspoolNative.GetPrinterInfo2(st.Queue);
            if (!info.HasValue || !string.Equals(info.Value.pDriverName, st.Model, StringComparison.OrdinalIgnoreCase))
            {
                _logger.Log("[续装⑤] 队列验证失败：期望驱动 \"" + st.Model + "\"，实际 " +
                    (info.HasValue ? "\"" + info.Value.pDriverName + "\"" : "队列不存在"));
                return false;
            }
            _logger.Log("[续装⑤] 队列验证通过：\"" + st.Queue + "\" 驱动=\"" + info.Value.pDriverName + "\" 端口=" + info.Value.pPortName);

            // ⑥ 管理工具 + 快捷方式 + installed
            InstallManagerAndShortcuts();
            WriteInstalled(st, "队列 \"" + st.Queue + "\" 验证通过");
            return true;
        }

        private void WriteInstalled(StateRecord st, string note)
        {
            StateRecord done = new StateRecord();
            done.State = InstallStates.Installed;
            done.Route = st.Route;
            done.Model = st.Model;
            done.Queue = st.Queue;
            done.Connection = st.Connection;
            done.Ip = st.Ip;
            done.Note = note;
            done.Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            StateStore.Write(done);
        }

        private static int CountInstalledModels(List<string> driverNames)
        {
            int n = 0;
            foreach (string model in Program.InfModelNames)
            {
                foreach (string dn in driverNames)
                {
                    if (string.Equals(dn, model, StringComparison.OrdinalIgnoreCase)) { n++; break; }
                }
            }
            return n;
        }

        // 队列创建：Add-Printer -Name -DriverName -PortName
        private async Task<bool> CreateQueueViaAddPrinter(string queue, string driverName, string port)
        {
            _logger.Log("[续装④] powershell Add-Printer（队列 " + queue + "，驱动 " + driverName + "，端口 " + port + "）");
            ProcResult r = await Task.Run(delegate
            {
                return Psh.Run("Add-Printer -Name '" + queue + "' -DriverName '" + driverName + "' -PortName '" + port + "'", 90000);
            });
            _logger.Log("[续装④] Add-Printer 退出码 " + r.ExitCode + "\r\n" + Indent(r.Output));
            return r.ExitCode == 0;
        }

        // ------------------------------------------------------------------
        // IPP 路线：Add-Printer -IppUrl（免驱动、免签名；OEM 功能走设备 Web 管理）
        // ------------------------------------------------------------------
        private async Task<bool> RunIppAdd()
        {
            string ip = _txtIp.Text.Trim();
            string queue = _txtQueue.Text.Trim();
            if (!IsValidHost(ip))
            {
                MessageBox.Show("请填写打印机 IP / 主机名（IPP 需网络型号）。", "缺少地址", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return false;
            }
            if (queue.Length == 0)
            {
                MessageBox.Show("请填写队列名称。", "缺少参数", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return false;
            }
            _logger.Log("[IPP] powershell Add-Printer -IppUrl http://" + ip + "/ipp/print（队列：" + queue + "）");
            ProcResult r = await Task.Run(delegate
            {
                return Psh.Run("Add-Printer -Name '" + queue + "' -IppUrl 'http://" + ip + "/ipp/print'", 90000);
            });
            _logger.Log("[IPP] Add-Printer 退出码 " + r.ExitCode + "\r\n" + Indent(r.Output));
            if (r.ExitCode != 0)
            {
                MessageBox.Show("IPP 添加失败。\r\n可操作提示：确认设备支持 IPP/AirPrint 且 IP 可达（ping " + ip +
                    "）；或点「打开系统打印设置手动添加」。\r\n日志：\r\n" + _logger.LogPath,
                    "IPP 添加失败", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return false;
            }
            WinspoolNative.PRINTER_INFO_2? info = WinspoolNative.GetPrinterInfo2(queue);
            if (!info.HasValue)
            {
                _logger.Log("[IPP] 队列创建后未查询到（winspool）——检查队列名是否重复。");
                return false;
            }
            _logger.Log("[IPP] IPP 队列就绪：\"" + queue + "\" 端口=" + info.Value.pPortName +
                "（省墨等 OEM 功能由设备 Web 管理 http://" + ip + "/ 设置）");
            InstallManagerAndShortcuts();
            _btnOpenManager.Enabled = File.Exists(Path.Combine(_workRoot, "LJ2400Manager.exe"));
            return true;
        }

        private void _btnIppSettings_Click(object sender, EventArgs e)
        {
            try { Process.Start("ms-settings:printers"); }
            catch (Exception ex) { MessageBox.Show("打开系统设置失败：" + ex.Message, "错误", MessageBoxButtons.OK, MessageBoxIcon.Error); }
        }

        private async void _btnIppAdd_Click(object sender, EventArgs e)
        {
            if (_installing) return;
            _installing = true;
            _btnIppAdd.Enabled = false;
            _logger.Log("==== IPP 路线（基础打印）====");
            bool ok = false;
            try { ok = await RunIppAdd(); }
            catch (Exception ex)
            {
                _logger.Log("[IPP][异常] " + ex.Message);
                MessageBox.Show("IPP 添加异常：" + ex.Message + "\r\n日志：\r\n" + _logger.LogPath,
                    "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            _installing = false;
            _btnIppAdd.Enabled = true;
            if (ok) MessageBox.Show("IPP 打印机已添加（基础打印）。\r\n省墨等 OEM 功能在设备 Web 管理中设置。", "完成",
                MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        // ------------------------------------------------------------------
        // 官方 SDK 下载页入口（次入口）
        // ------------------------------------------------------------------
        private void _btnSdkPage_Click(object sender, EventArgs e)
        {
            try
            {
                Process.Start(SdkInstaller.OfficialPageUrl);
                _logger.Log("[SDK] 已打开官方下载页：" + SdkInstaller.OfficialPageUrl);
            }
            catch (Exception ex)
            {
                MessageBox.Show("打开官方下载页失败：" + ex.Message + "\r\n请手动访问：\r\n" + SdkInstaller.OfficialPageUrl,
                    "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ------------------------------------------------------------------
        // GUI 安装完成后重新检测 Inf2Cat
        // ------------------------------------------------------------------
        private void _btnRedetect_Click(object sender, EventArgs e)
        {
            _inf2catPath = Inf2CatLocator.Find();
            if (_inf2catPath != null)
            {
                _logger.Log("[SDK] 重新检测：inf2cat 已就绪：" + _inf2catPath);
                _lblRecommend.Text = ComputeRecommendation();
                UpdateRouteUi();
                MessageBox.Show("inf2cat 已就绪，签名安装路线可继续。", "重新检测", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else
            {
                _logger.Log("[SDK] 重新检测：仍未检测到 inf2cat——确认 SDK 安装勾选了 SigningTools 组件后重试，或用图形安装器完成安装。");
                MessageBox.Show("仍未检测到 inf2cat。\r\n可操作提示：确认 SDK 安装勾选了「Windows SDK Signing Tools」组件；或重新运行图形安装器完成后再点本按钮。",
                    "重新检测", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        // ------------------------------------------------------------------
        // SDK 引导：官方安装器直链下载 → SigningTools 静默安装 → 探测；
        // 静默退出码非 0 或探测仍失败 → 自动转 GUI 安装器
        // ------------------------------------------------------------------
        private async void _btnInstallSdk_Click(object sender, EventArgs e)
        {
            if (_installing) return;
            _installing = true;
            _btnInstallSdk.Enabled = false;
            _pbarSdk.Value = 0;
            _pbarSdk.Visible = true;
            try
            {
                string installer = SdkInstaller.InstallerPath();
                if (!File.Exists(installer))
                {
                    _logger.Log("[SDK] 下载微软官方 Windows SDK 安装器（SigningTools 组件含 Inf2Cat/Signtool）…");
                    _logger.Log("[SDK] 直链：" + SdkInstaller.DownloadUrl);
                    bool dl = await DownloadSdkInstaller();
                    if (!dl) return; // 下载失败已弹官方下载页
                    _logger.Log("[SDK] 下载完成：" + installer + "（" + new FileInfo(installer).Length + " B）");
                }
                else
                {
                    _logger.Log("[SDK] 复用已下载的官方安装器：" + installer);
                }

                _logger.Log("[SDK] 静默安装：winsdksetup.exe " + SdkInstaller.SilentArgs());
                ProcResult r = await Task.Run(delegate { return Proc.Run(installer, SdkInstaller.SilentArgs(), 1800000); });
                _logger.Log("[SDK] 静默安装退出码 " + r.ExitCode + "\r\n" + Indent(r.Output));

                _inf2catPath = Inf2CatLocator.Find();
                if (r.ExitCode != 0 || _inf2catPath == null)
                {
                    if (r.ExitCode != 0)
                        _logger.Log("[SDK] 静默安装非零退出码（输出原样见上）——自动转图形界面安装。");
                    else
                        _logger.Log("[SDK] 静默安装完成但未探测到 inf2cat——自动转图形界面安装（可在安装器中勾选组件）。");
                    OpenSdkGui(installer);
                    return;
                }
                _logger.Log("[SDK] inf2cat 已就绪：" + _inf2catPath);
            }
            finally
            {
                _pbarSdk.Visible = false;
                _btnInstallSdk.Enabled = true;
                _installing = false;
                _lblRecommend.Text = ComputeRecommendation();
                UpdateRouteUi();
            }
        }

        // 官方安装器下载（HttpClient 流式下载 + 进度上报）
        private async Task<bool> DownloadSdkInstaller()
        {
            string dst = SdkInstaller.InstallerPath();
            try
            {
                try { ServicePointManager.SecurityProtocol |= (SecurityProtocolType)3072; } catch { } // TLS 1.2
                using (HttpClient client = new HttpClient())
                {
                    client.Timeout = TimeSpan.FromMinutes(30);
                    using (HttpResponseMessage resp = await client.GetAsync(SdkInstaller.DownloadUrl, HttpCompletionOption.ResponseHeadersRead))
                    {
                        resp.EnsureSuccessStatusCode();
                        long? total = resp.Content.Headers.ContentLength;
                        using (Stream src = await resp.Content.ReadAsStreamAsync())
                        using (FileStream fs = new FileStream(dst, FileMode.Create, FileAccess.Write))
                        {
                            byte[] buf = new byte[81920];
                            long readBytes = 0;
                            int lastPct = -1;
                            while (true)
                            {
                                int n = await src.ReadAsync(buf, 0, buf.Length);
                                if (n <= 0) break;
                                await fs.WriteAsync(buf, 0, n);
                                readBytes += n;
                                if (total.HasValue && total.Value > 0)
                                {
                                    int pct = (int)(readBytes * 100 / total.Value);
                                    if (pct != lastPct) { lastPct = pct; ReportSdkProgress(pct); }
                                }
                            }
                            ReportSdkProgress(100);
                        }
                    }
                }
                return true;
            }
            catch (Exception ex)
            {
                _logger.Log("[SDK][下载失败] " + ex.Message + " —— 已打开官方下载页，请手动获取安装器并运行其图形安装，再点「重新检测 Inf2Cat」。");
                try { Process.Start(SdkInstaller.OfficialPageUrl); } catch { }
                return false;
            }
        }

        private void ReportSdkProgress(int pct)
        {
            try
            {
                if (_pbarSdk.IsHandleCreated && !_pbarSdk.IsDisposed)
                    _pbarSdk.BeginInvoke(new Action(delegate { _pbarSdk.Value = pct; }));
            }
            catch { }
            if (pct == 25 || pct == 50 || pct == 75 || pct == 100)
                _logger.Log("[SDK] 下载进度 " + pct + "%");
        }

        // 静默失败/探测仍失败 → 打开 SDK 安装器图形界面，用户手动完成后点「重新检测 Inf2Cat」
        private void OpenSdkGui(string installer)
        {
            try
            {
                Process.Start(installer); // GUI 模式（无 /q）
                _logger.Log("[SDK] 已打开 SDK 安装器图形界面——请在安装器中完成安装（可勾选组件），装完点「重新检测 Inf2Cat」。");
                MessageBox.Show("已打开 SDK 安装器图形界面。\r\n请在安装器中完成安装（组件可勾选），完成后回到本窗口点「重新检测 Inf2Cat」。",
                    "请手动完成安装", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                _logger.Log("[SDK] 打开图形安装器失败：" + ex.Message);
                MessageBox.Show("打开 SDK 安装器失败：" + ex.Message + "\r\n请从官方下载页手动获取安装器：\r\n" + SdkInstaller.OfficialPageUrl,
                    "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ------------------------------------------------------------------
        // 开始安装：按路线分派
        // ------------------------------------------------------------------
        private async void _btnInstall_Click(object sender, EventArgs e)
        {
            if (_installing) return;

            int route = CurrentRoute();
            bool netMode = _rbNet.Checked;
            bool usbMode = _rbUsb.Checked;
            bool driverOnly = _rbDriverOnly.Checked;
            string model = _cboModel.SelectedItem as string;
            string ip = _txtIp.Text.Trim();
            string queueName = _txtQueue.Text.Trim();

            // 参数校验（IPP 路线由其流程自行校验）
            if (route == 0 && !driverOnly && string.IsNullOrEmpty(model))
            {
                MessageBox.Show("请先选择 INF 型号名。\r\n若列表为空，请确认 exe 同目录 driver\\ 存在（LJ2400WOA.INF）。",
                    "缺少参数", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            if (route == 0 && !driverOnly && string.IsNullOrEmpty(queueName))
            {
                MessageBox.Show("请填写打印队列名称。", "缺少参数", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            if (route == 0 && netMode && !IsValidHost(ip))
            {
                MessageBox.Show("请填写合法的打印机 IP（如 192.168.1.100）或主机名。", "缺少参数",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            _installing = true;
            _btnInstall.Enabled = false;
            _btnOpenManager.Enabled = false;
            _logger.Log("==== 开始安装（" + (route == 0 ? "签名安装路线" : "IPP 路线（基础打印）") +
                "，模式：" + (driverOnly ? "仅驱动" : usbMode ? "USB" : "网络") + "）====");

            bool ok = false;
            try
            {
                if (route == 0)
                {
                    ok = await RunRouteSigned(model, queueName, ip, netMode, usbMode);
                }
                else
                {
                    ok = await RunIppAdd();
                }
            }
            catch (Exception ex)
            {
                _logger.Log("[异常] " + ex.GetType().Name + ": " + ex.Message);
                MessageBox.Show("安装过程中出现异常：\r\n" + ex.Message +
                    "\r\n\r\n可操作提示：查看日志后修正环境再重试。\r\n日志路径：\r\n" + _logger.LogPath,
                    "安装失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }

            _installing = false;
            _btnInstall.Enabled = true;
            if (ok && route != 0) // 签名安装路线成功时是「等待重启」提示框，不重复弹完成框
            {
                _btnOpenManager.Enabled = File.Exists(Path.Combine(_workRoot, "LJ2400Manager.exe"));
                _logger.Log("==== 安装完成 ====");
                MessageBox.Show("安装完成。\r\n管理工具与快捷方式：开始菜单 / 桌面「联想打印机管理」。\r\n日志：\r\n" + _logger.LogPath,
                    "安装完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            else if (!ok)
            {
                MessageBox.Show("安装未全部成功。\r\n可操作提示：USB 模式请确认打印机已开机插线；网络模式确认 IP 可达（ping 通）；" +
                    "\r\n签名安装路线失败先确认 inf2cat/签名步骤输出。\r\n详细日志：\r\n" + _logger.LogPath,
                    "安装未完成", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        // ------------------------------------------------------------------
        // 签名安装路线续装的 printui 降级建队列（Add-Printer 失败时的备用路径）
        // ------------------------------------------------------------------
        private bool RunPrintuiInstall(string queueName, string infPath, string port, string model)
        {
            string args = "/if /b \"" + queueName + "\" /f \"" + infPath + "\" /r \"" + port + "\" /m \"" + model + "\"";
            _logger.Log("命令：rundll32 printui.dll,PrintUIEntry " + args);
            ProcResult r = Proc.Run("rundll32.exe", "printui.dll,PrintUIEntry " + args, 600000);
            _logger.Log("printui 退出码 " + r.ExitCode +
                (r.ExitCode == 0 ? "（成功）" : "（失败——若弹出信任框请点「仍要安装此驱动程序软件」后重试）"));
            if ((r.Output ?? "").Trim().Length > 0) _logger.Log(Indent(r.Output));
            return r.ExitCode == 0;
        }

        // 端口决策：网络 → TCP/IP 端口（RAW 9100）；USB → 现有 USB 端口或 USB001 尝试
        private async Task<string> ResolvePort(bool netMode, string ip)
        {
            if (netMode) return await EnsureTcpIpPort(ip);
            List<string> usbPorts = EnumUsbPorts();
            if (usbPorts.Count == 0)
            {
                _logger.Log("[端口] 未检测到 USB 打印机端口（USB Monitor\\Ports 为空）——设备可能未连接。仍尝试 USB001。");
                return "USB001";
            }
            _logger.Log("[端口] 使用现有 USB 端口：" + usbPorts[0]);
            return usbPorts[0];
        }

        private void CopyDriverPackage()
        {
            if (!Directory.Exists(_driverSrcDir))
                throw new DirectoryNotFoundException("未找到驱动包目录：" + _driverSrcDir + "\r\n请将 driver\\ 子目录放到 LJ2400Setup.exe 同目录。");
            Directory.CreateDirectory(_driverDstDir);
            int files = 0;
            foreach (string f in Directory.GetFiles(_driverSrcDir, "*", SearchOption.AllDirectories))
            {
                string rel = f.Substring(_driverSrcDir.Length).TrimStart('\\');
                string dst = Path.Combine(_driverDstDir, rel);
                Directory.CreateDirectory(Path.GetDirectoryName(dst));
                File.Copy(f, dst, true);
                files++;
            }
            _logger.Log("已复制 " + files + " 个文件到 " + _driverDstDir);
        }

        private static bool PnputilLooksOk(ProcResult r)
        {
            if (r.ExitCode != 0) return false;
            string outLower = (r.Output ?? "").ToLowerInvariant();
            if (Regex.IsMatch(r.Output ?? "", @"0x8[0-9a-fA-F]{7}")) return false; // HRESULT 错误码（未签名驱动包实测 0xBCB）
            if ((r.Output ?? "").Contains("拒绝")) return false;
            if ((r.Output ?? "").Contains("失败")) return false;
            if ((r.Output ?? "").Contains("无法")) return false;
            if (outLower.Contains("error") || outLower.Contains("failed")) return false;
            return true;
        }

        private async Task<string> EnsureTcpIpPort(string ip)
        {
            string portName = "IP_" + ip;
            using (RegistryKey k = Registry.LocalMachine.OpenSubKey(
                @"SYSTEM\CurrentControlSet\Control\Print\Monitors\Standard TCP/IP Port\Ports\" + portName))
            {
                if (k != null)
                {
                    _logger.Log("[端口] TCP/IP 端口已存在，复用：" + portName);
                    return portName;
                }
            }
            _logger.Log("[端口] powershell Add-PrinterPort 创建 RAW 9100 TCP/IP 端口：" + portName);
            ProcResult r = await Task.Run(delegate
            {
                return Psh.Run("Add-PrinterPort -Name '" + portName + "' -PrinterHostAddress '" + ip + "' -PortNumber 9100", 90000);
            });
            if (r.ExitCode != 0)
            {
                _logger.Log("[端口] Add-PrinterPort 退出码 " + r.ExitCode + "：" + Indent(r.Output));
                throw new Exception("创建 TCP/IP 端口失败（powershell Add-PrinterPort）。\r\n请确认打印机 IP 可达（ping " + ip +
                    "）后重试，或在「打印管理」中手动创建 RAW 9100 端口 " + portName + "。");
            }
            _logger.Log("[端口] TCP/IP 端口创建成功：" + portName);
            return portName;
        }

        private void InstallManagerAndShortcuts()
        {
            string src = Path.Combine(_baseDir, "LJ2400Manager.exe");
            string dst = Path.Combine(_workRoot, "LJ2400Manager.exe");
            if (File.Exists(src))
            {
                Directory.CreateDirectory(_workRoot);
                File.Copy(src, dst, true);
                _logger.Log("管理工具已复制：" + dst);
            }
            else
            {
                _logger.Log("警告：exe 同目录未找到 LJ2400Manager.exe，跳过管理工具安装。");
            }
            if (!File.Exists(dst)) return;
            CreateShortcut(
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonStartMenu), "Programs", "联想打印机管理.lnk"),
                dst, "开始菜单");
            CreateShortcut(
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonDesktopDirectory), "联想打印机管理.lnk"),
                dst, "桌面");
        }

        private void CreateShortcut(string lnkPath, string targetPath, string where)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(lnkPath));
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                object shell = Activator.CreateInstance(shellType);
                object shortcut = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell,
                    new object[] { lnkPath });
                Type scType = shortcut.GetType();
                scType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { targetPath });
                scType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, shortcut,
                    new object[] { Path.GetDirectoryName(targetPath) });
                scType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
                _logger.Log(where + "快捷方式已创建：" + lnkPath);
            }
            catch (Exception ex)
            {
                _logger.Log(where + "快捷方式创建失败（不影响使用）：" + ex.Message);
            }
        }

        private void _btnOpenManager_Click(object sender, EventArgs e)
        {
            string mgr = Path.Combine(_workRoot, "LJ2400Manager.exe");
            if (File.Exists(mgr))
            {
                Process.Start(mgr);
            }
            else
            {
                MessageBox.Show("未找到 " + mgr + "\r\n请确认安装器同目录带 LJ2400Manager.exe 后重新安装。", "提示",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private static bool IsValidHost(string s)
        {
            if (string.IsNullOrEmpty(s)) return false;
            return Regex.IsMatch(s, @"^(\d{1,3}\.){3}\d{1,3}$") || Regex.IsMatch(s, @"^[A-Za-z0-9][A-Za-z0-9._-]{0,253}[A-Za-z0-9]$");
        }

        private static string Indent(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return "    " + s.Replace("\r\n", "\r\n    ").TrimEnd() + "\r\n";
        }
    }
}

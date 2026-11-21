using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;

namespace LeagueDirectLauncher
{
    static class Program
    {
        private const string ServicesExe = @"C:\Riot Games\Riot Client\RiotClientServices.exe";
        private static readonly string LockfilePath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            @"Riot Games\Riot Client\Config\lockfile"
        );
        private static readonly string LogFilePath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            @"Riot Games\direct_launch.log"
        );

        private static void Log(string msg)
        {
            try
            {
                File.AppendAllText(LogFilePath, string.Format("[{0:yyyy-MM-dd HH:mm:ss}] [EXE] {1}\r\n", DateTime.Now, msg));
            }
            catch { }
        }

        private static bool IsLeagueRunning()
        {
            try
            {
                Process[] p1 = Process.GetProcessesByName("LeagueClientUx");
                if (p1.Length > 0) return true;
                Process[] p2 = Process.GetProcessesByName("LeagueClient");
                if (p2.Length > 0) return true;
            }
            catch (Exception ex)
            {
                Log(string.Format("IsLeagueRunning hata: {0}", ex.Message));
            }
            return false;
        }

        private static bool IsPidAlive(int pid)
        {
            try
            {
                Process p = Process.GetProcessById(pid);
                return !p.HasExited;
            }
            catch
            {
                return false;
            }
        }

        private static string[] GetLockfileInfo()
        {
            try
            {
                if (!File.Exists(LockfilePath))
                {
                    Log("Lockfile dosyasi mevcut degil.");
                    return null;
                }

                string content;
                using (FileStream fs = new FileStream(LockfilePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                using (StreamReader sr = new StreamReader(fs, Encoding.UTF8))
                {
                    content = sr.ReadToEnd().Trim();
                }

                string[] parts = content.Split(':');
                int pid;
                if (parts.Length >= 5 && int.TryParse(parts[1], out pid))
                {
                    if (IsPidAlive(pid))
                    {
                        Log(string.Format("Lockfile okundu: Port {0}, PID {1}", parts[2], pid));
                        return parts;
                    }
                    else
                    {
                        Log(string.Format("Lockfile eski (PID {0} calismiyor).", pid));
                    }
                }
            }
            catch (Exception ex)
            {
                Log(string.Format("GetLockfileInfo hata: {0}", ex.Message));
            }
            return null;
        }

        private static bool TriggerApi(string port, string token)
        {
            try
            {
                ServicePointManager.ServerCertificateValidationCallback = delegate { return true; };
                ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11 | SecurityProtocolType.Tls;
                string url = string.Format("https://127.0.0.1:{0}/product-launcher/v1/products/league_of_legends/patchlines/live", port);
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
                req.Method = "POST";
                req.Timeout = 4000;
                req.ContentType = "application/json";
                string auth = Convert.ToBase64String(Encoding.ASCII.GetBytes(string.Format("riot:{0}", token)));
                req.Headers["Authorization"] = "Basic " + auth;

                byte[] data = Encoding.UTF8.GetBytes("{}");
                req.ContentLength = data.Length;
                using (Stream stream = req.GetRequestStream())
                {
                    stream.Write(data, 0, data.Length);
                }

                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                {
                    int code = (int)resp.StatusCode;
                    Log(string.Format("API basarili: HTTP {0}", code));
                    return true;
                }
            }
            catch (WebException we)
            {
                HttpWebResponse hr = we.Response as HttpWebResponse;
                if (hr != null)
                {
                    int code = (int)hr.StatusCode;
                    if (code == 423 || code == 400 || code == 409)
                    {
                        Log(string.Format("Istemci zaten baslatiliyor (HTTP {0})", code));
                        return true;
                    }
                    Log(string.Format("API WebException HTTP: {0}", code));
                }
                else
                {
                    Log(string.Format("API WebException: {0}", we.Message));
                }
            }
            catch (Exception ex)
            {
                Log(string.Format("API genel hata: {0}", ex.Message));
            }
            return false;
        }

        private static void FallbackLaunch()
        {
            try
            {
                Log("Fallback: RiotClientServices baslatiliyor...");
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = ServicesExe,
                    Arguments = "--launch-product=league_of_legends --launch-patchline=live",
                    WorkingDirectory = Path.GetDirectoryName(ServicesExe),
                    UseShellExecute = true
                };
                Process.Start(psi);
                Log("Fallback: RiotClientServices baslatildi.");
            }
            catch (Exception ex)
            {
                Log(string.Format("Fallback baslatma hatasi: {0}", ex.Message));
            }
        }

        [STAThread]
        static void Main()
        {
            try
            {
                Log("=== League Direct Launcher (.exe) Baslatildi ===");

                // 1. LoL zaten aciksa cik
                if (IsLeagueRunning())
                {
                    Log("League zaten calisiyor. Cikiliyor.");
                    return;
                }

                // 2. Riot Client calisiyor mu kontrol et
                string[] lockInfo = GetLockfileInfo();
                if (lockInfo == null)
                {
                    Log("Riot Client acik degil. Baslatiliyor...");
                    FallbackLaunch();

                    for (int i = 0; i < 30; i++)
                    {
                        Thread.Sleep(200);
                        lockInfo = GetLockfileInfo();
                        if (lockInfo != null)
                        {
                            break;
                        }
                    }
                }

                // 3. API ile dogrudan LoL'u tetikle
                bool apiSuccess = false;
                if (lockInfo != null)
                {
                    for (int i = 0; i < 15; i++)
                    {
                        if (TriggerApi(lockInfo[2], lockInfo[3]))
                        {
                            apiSuccess = true;
                            break;
                        }
                        Thread.Sleep(300);
                    }
                }

                // 4. API basarisiz olduysa ve LoL baslamadiysa fallback yap
                if (!apiSuccess && !IsLeagueRunning())
                {
                    Log("API basarisiz oldu, fallback calistiriliyor...");
                    FallbackLaunch();
                }

                Log("=== League Direct Launcher (.exe) Tamamlandi ===");
            }
            catch (Exception ex)
            {
                Log(string.Format("Main kritik hata: {0}", ex.ToString()));
            }
        }
    }
}

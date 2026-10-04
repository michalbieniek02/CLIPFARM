using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Launcher
{
    [STAThread]
    static void Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string python = Path.Combine(root, "runtime", "Scripts", "python.exe");
        try
        {
            if (!File.Exists(python))
                throw new Exception("Brak środowiska aplikacji. Uruchom Install-CLIPFARM.ps1.");
            var start = new ProcessStartInfo(python, "\"" + Path.Combine(root, "app.py") + "\"");
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.EnvironmentVariables["TEMP"] = root;
            start.EnvironmentVariables["TMP"] = root;
            Process.Start(start);
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "CLIPFARM", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}

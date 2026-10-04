using System;
using System.Diagnostics;
using System.IO;
using System.Text;

internal static class Installer
{
    // Windows command-line escaping, including paths ending in a backslash.
    static string Quote(string value)
    {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char character in value)
        {
            if (character == '\\') { slashes++; continue; }
            result.Append('\\', character == '"' ? slashes * 2 + 1 : slashes);
            result.Append(character);
            slashes = 0;
        }
        result.Append('\\', slashes * 2);
        return result.Append('"').ToString();
    }

    static int Main(string[] args)
    {
        bool pause = true;
        int exitCode = 1;
        foreach (string argument in args)
            if (argument.Equals("--no-pause", StringComparison.OrdinalIgnoreCase)) pause = false;
        try
        {
            string root = AppDomain.CurrentDomain.BaseDirectory;
            string script = Path.Combine(root, "Install-CLIPFARM.ps1");
            if (!File.Exists(script))
                throw new FileNotFoundException("Brak Install-CLIPFARM.ps1. Wypakuj caly ZIP do jednego folderu.");
            var arguments = new StringBuilder("-NoLogo -NoProfile -ExecutionPolicy Bypass -File " + Quote(script));
            foreach (string argument in args)
            {
                if (argument.Equals("--no-pause", StringComparison.OrdinalIgnoreCase)) continue;
                arguments.Append(' ').Append(Quote(argument));
            }
            string powershell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"WindowsPowerShell\v1.0\powershell.exe");
            var start = new ProcessStartInfo(powershell, arguments.ToString());
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            using (var process = Process.Start(start))
            {
                process.WaitForExit();
                exitCode = process.ExitCode;
            }
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("Instalacja nie powiodla sie: " + error.Message);
        }
        if (pause && !Console.IsInputRedirected)
        {
            Console.WriteLine();
            Console.Write("Nacisnij dowolny klawisz, aby zamknac...");
            Console.ReadKey(true);
        }
        return exitCode;
    }
}

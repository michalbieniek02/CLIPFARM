using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

// WScript.Shell.Save uses the system ANSI code page for the link filename.
// IShellLinkW + IPersistFile keeps both filenames and shortcut fields Unicode.
public static class ClipfarmShortcut
{
    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    private class ShellLink { }

    [ComImport, Guid("000214F9-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IShellLinkW
    {
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int count, IntPtr data, uint flags);
        void GetIDList(out IntPtr id);
        void SetIDList(IntPtr id);
        void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder text, int count);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string text);
        void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int count);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string path);
        void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder args, int count);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string args);
        void GetHotkey(out short key);
        void SetHotkey(short key);
        void GetShowCmd(out int command);
        void SetShowCmd(int command);
        void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int count, out int index);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string path, int index);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, uint reserved);
        void Resolve(IntPtr window, uint flags);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string path);
    }

    public static void Save(string filename, string target, string args, string directory, string icon)
    {
        var link = (IShellLinkW)new ShellLink();
        try
        {
            link.SetPath(target);
            link.SetArguments(args);
            link.SetWorkingDirectory(directory);
            link.SetIconLocation(icon, 0);
            link.SetDescription("CLIPFARM - edytor klipow wideo");
            ((IPersistFile)link).Save(filename, true);
        }
        finally { Marshal.FinalReleaseComObject(link); }
    }

    // Read native persisted fields for installation verification.
    public static string[] Read(string filename)
    {
        var link = (IShellLinkW)new ShellLink();
        try
        {
            ((IPersistFile)link).Load(filename, 0);
            var target = new StringBuilder(32768);
            var args = new StringBuilder(32768);
            var directory = new StringBuilder(32768);
            var icon = new StringBuilder(32768);
            var description = new StringBuilder(1024);
            int index;
            link.GetPath(target, target.Capacity, IntPtr.Zero, 4);
            link.GetArguments(args, args.Capacity);
            link.GetWorkingDirectory(directory, directory.Capacity);
            link.GetIconLocation(icon, icon.Capacity, out index);
            link.GetDescription(description, description.Capacity);
            return new[] { target.ToString(), args.ToString(), directory.ToString(), icon.ToString() + "," + index, description.ToString() };
        }
        finally { Marshal.FinalReleaseComObject(link); }
    }
}

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

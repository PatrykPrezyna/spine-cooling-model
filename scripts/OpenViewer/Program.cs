using System.Diagnostics;

var exePath = Environment.ProcessPath
    ?? throw new InvalidOperationException("Could not determine the launcher path.");
var modelDir = Path.GetDirectoryName(exePath)
    ?? throw new InvalidOperationException("Could not determine the model folder.");
Directory.SetCurrentDirectory(modelDir);

Console.Title = "CoolSpine SysML Explorer";
Console.WriteLine("Starting sysml-explorer in:");
Console.WriteLine("  " + modelDir);
Console.WriteLine();

var explorer = FindSysmlExplorer();
if (explorer is null)
{
    Console.Error.WriteLine("Could not find sysml-explorer.");
    Console.Error.WriteLine();
    Console.Error.WriteLine("Install it once with:");
    Console.Error.WriteLine("  pip install \"git+https://github.com/PatrykPrezyna/SE_assistant.git#subdirectory=tools/sysml_explorer\"");
    Console.Error.WriteLine();
    Console.WriteLine("Press Enter to close...");
    Console.ReadLine();
    return 1;
}

var start = new ProcessStartInfo
{
    FileName = explorer.FileName,
    Arguments = explorer.Arguments,
    WorkingDirectory = modelDir,
    UseShellExecute = false,
};

try
{
    using var process = Process.Start(start);
    if (process is null)
        throw new InvalidOperationException("Process.Start returned null.");
    process.WaitForExit();
    return process.ExitCode;
}
catch (Exception ex)
{
    Console.Error.WriteLine("Failed to start sysml-explorer.");
    Console.Error.WriteLine(ex.Message);
    Console.Error.WriteLine();
    Console.WriteLine("Press Enter to close...");
    Console.ReadLine();
    return 1;
}

static LaunchCommand? FindSysmlExplorer()
{
    foreach (var dir in PathDirs())
    {
        var exe = Path.Combine(dir, "sysml-explorer.exe");
        if (File.Exists(exe))
            return new LaunchCommand(exe, ".");
    }

    foreach (var python in FindPythons())
    {
        if (CanRunModule(python, "sysml_explorer"))
            return new LaunchCommand(python, "-m sysml_explorer .");
    }

    return null;
}

static IEnumerable<string> PathDirs()
{
    var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    foreach (var raw in new[]
    {
        Environment.GetEnvironmentVariable("PATH"),
        Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.User),
        Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.Machine),
    })
    {
        if (string.IsNullOrWhiteSpace(raw))
            continue;
        foreach (var part in raw.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            var dir = part.Trim().Trim('"');
            if (dir.Length > 0 && seen.Add(dir))
                yield return dir;
        }
    }

    var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
    foreach (var dir in new[]
    {
        Path.Combine(home, "miniconda3", "Scripts"),
        Path.Combine(home, "anaconda3", "Scripts"),
        Path.Combine(home, "Miniconda3", "Scripts"),
        Path.Combine(home, "Anaconda3", "Scripts"),
        Path.Combine(local, "Programs", "Python", "Python313", "Scripts"),
        Path.Combine(local, "Programs", "Python", "Python312", "Scripts"),
        Path.Combine(local, "Programs", "Python", "Python311", "Scripts"),
    })
    {
        if (seen.Add(dir))
            yield return dir;
    }
}

static IEnumerable<string> FindPythons()
{
    var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    foreach (var name in new[] { "python.exe", "python3.exe", "py.exe" })
    {
        foreach (var dir in PathDirs())
        {
            var candidate = Path.Combine(dir, name);
            if (File.Exists(candidate) && seen.Add(candidate))
                yield return candidate;
        }
    }
}

static bool CanRunModule(string python, string module)
{
    try
    {
        var check = Process.Start(new ProcessStartInfo
        {
            FileName = python,
            Arguments = $"-c \"import {module}\"",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        });
        if (check is null)
            return false;
        check.WaitForExit(8000);
        return check.ExitCode == 0;
    }
    catch
    {
        return false;
    }
}

sealed record LaunchCommand(string FileName, string Arguments);

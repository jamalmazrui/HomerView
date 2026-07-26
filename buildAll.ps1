# buildAll.ps1
# Builds everything a release needs, in the order tagRelease expects:
# the add-on package, then the installer whose version resource tagRelease reads.
# Writes buildAll.log beside itself.

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathLog = Join-Path $pathRoot "buildAll.log"

function writeLog {
    param([string] $sMessage)
    $sStamped = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $sMessage
    Write-Host $sStamped
    Add-Content -Path $pathLog -Value $sStamped -Encoding UTF8
}

Set-Content -Path $pathLog -Value "" -Encoding UTF8
writeLog "buildAll starting in $pathRoot"
Set-Location $pathRoot

writeLog "Step 1 of 2: building the add-on"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $pathRoot "buildAddon.ps1")
if ($LASTEXITCODE -ne 0) { writeLog "ERROR: the add-on build failed"; exit 1 }

# Inno Setup's compiler is not on the path by default, so look where its own
# installer puts it rather than asking the user to add it.
$pathCompiler = ""
foreach ($sCandidate in @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe")) {
    if (Test-Path $sCandidate) { $pathCompiler = $sCandidate; break }
}
if (-not $pathCompiler) {
    $command = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($command) { $pathCompiler = $command.Source }
}
if (-not $pathCompiler) {
    writeLog "ERROR: the Inno Setup compiler was not found."
    writeLog "       Install it from https://jrsoftware.org/isdl.php, then run this again."
    exit 1
}
writeLog "Inno Setup compiler: $pathCompiler"

writeLog "Step 2 of 2: compiling the installer"
& $pathCompiler (Join-Path $pathRoot "HomerView_setup.iss")
if ($LASTEXITCODE -ne 0) { writeLog "ERROR: the installer did not compile"; exit 1 }

$pathInstaller = Join-Path $pathRoot "HomerView_setup.exe"
if (-not (Test-Path $pathInstaller)) {
    writeLog "ERROR: HomerView_setup.exe was not produced. Check OutputDir in the setup script."
    exit 1
}
$sVersion = (Get-Item $pathInstaller).VersionInfo.FileVersion
writeLog "Built HomerView_setup.exe, version $sVersion, $([math]::Round((Get-Item $pathInstaller).Length/1MB,1)) MB"
writeLog "Ready for tagRelease."
writeLog "buildAll finished"

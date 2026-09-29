# buildHomerView.ps1
# Builds everything a release needs, in the order release expects:
# the add-on package, then the installer whose version resource release reads.
# Writes buildHomerView.log beside itself.

# HANDED IN BY buildHomerView.cmd, WHICH CARRIES THE KIT CONTRACT. This
# engine used to choose its own compiler (the legacy one under
# Microsoft.NET\Framework64) and its own shared sources (copies in homer\).
# Both are now decided by the wrapper from the Homer Development Kit, and
# handed in: the compiler must be Roslyn, since the kit's classes use C#
# beyond version 5, and the sources are the kit's own files rather than
# copies that drift. Run without the wrapper, the old choices still apply,
# so a direct run of this file does what it always did.
param(
    [string] $pathCompiler = "",
    [string] $sHomerSources = "",
    [string] $pathLogFile = "",
    [string] $sBump = "bump"
)

$ErrorActionPreference = "Stop"

$pathRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# ONE LOG PER SESSION, IN logs\, SHARED WITH THE WRAPPER. The wrapper opens
# HomerView-build-<stamp>.log and passes its path; this appends. Run alone,
# the same name is made here so the convention holds either way.
if ($pathLogFile) {
    $pathLog = $pathLogFile
} else {
    $pathLogs = Join-Path $pathRoot "logs"
    if (-not (Test-Path $pathLogs)) { New-Item -ItemType Directory -Path $pathLogs | Out-Null }
    $pathLog = Join-Path $pathLogs ("HomerView-build-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
}

function writeLog {
    # THE HOMER LOG LINE (HomerDev 1.43.21): an ISO 8601 time with milliseconds
    # and UTC offset, a five-character level -- ERROR or WARN when the text says
    # so -- then the text. The console shows the text alone.
    param([string] $sMessage)
    $sLevel = "INFO "
    if ($sMessage -match '\b(ERROR|FAIL|FAILED)\b') { $sLevel = "ERROR" } elseif ($sMessage -match '\bWARN(ING)?\b') { $sLevel = "WARN " }
    Write-Host $sMessage
    Add-Content -Path $pathLog -Value ("{0} {1} {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffzzz"), $sLevel, $sMessage) -Encoding UTF8
}

if (-not $pathLogFile) { Set-Content -Path $pathLog -Value "" -Encoding UTF8 }
function checkSetupScript {
    # Everything Inno Setup will reject, found before Inno Setup sees it. Its
    # own report is a line number and four words, which is enough to find the
    # line and not enough to explain it.
    $pathSetup = Join-Path $pathRoot "HomerView_setup.iss"
    if (Test-Path $pathSetup) {
        $lLines = Get-Content $pathSetup
        $bInSetup = $false
        $dSeen = @{}
        $iProblems = 0
        foreach ($sLine in $lLines) {
            $sTrimmed = $sLine.Trim()
            if ($sTrimmed -match '^\[(\w+)\]') {
                $bInSetup = ($Matches[1] -eq "Setup")
                continue
            }
            if (-not $bInSetup) { continue }
            if ($sTrimmed.StartsWith(";") -or $sTrimmed.StartsWith("#") -or -not $sTrimmed.Contains("=")) { continue }
            $sName = $sTrimmed.Split("=")[0].Trim()
            if ($dSeen.ContainsKey($sName)) {
                writeLog "ERROR: [Setup] directive $sName is specified more than once. Inno Setup will refuse to compile."
                $iProblems += 1
            }
            $dSeen[$sName] = $true
        }
        foreach ($sLine in $lLines) {
            if ($sLine -match 'Source:\s*"([^"]+)"' -and $sLine -notmatch 'skipifsourcedoesntexist') {
                $sSource = $Matches[1]
                # BUILD OUTPUT IS NOT CHECKED HERE, because it does not exist yet.
                # exec\ holds what steps 3, 4 and 5 produce, and this runs at step
                # 1. With build\ the add-on happened to survive from the previous
                # run, so the check passed by accident; the first build into a
                # fresh exec\ stopped on "exec\HomerView.nvda-addon does not
                # exist". The installer compile at step 5 is the right place to
                # find a missing binary, and it does.
                if ($sSource -match '^exec\\') { continue }
                if ($sSource -notmatch '\*') {
                    $sResolved = $sSource -replace '\{#AddonFile\}', 'HomerView.nvda-addon'
                    # Relative to the project, as the kit's installers are written.
                    # The absolute C:\HomerView\ prefix went on 25 September 2026;
                    # a relative name is resolved here the way Inno resolves it.
                    if (-not [System.IO.Path]::IsPathRooted($sResolved)) {
                        $sResolved = Join-Path $pathRoot $sResolved
                    }
                    if (-not (Test-Path $sResolved)) {
                        writeLog "ERROR: the setup script references $sResolved, which does not exist."
                        $iProblems += 1
                    }
                }
            }
        }
        # A setup script that has lost a section still compiles, and produces an
        # installer that installs nothing. That happened once, from an edit that
        # matched the word Run inside a comment instead of the section header, and
        # it was found by a user rather than by the build.
        foreach ($sSection in @("[Setup]", "[Files]", "[Icons]", "[Run]", "[Code]")) {
            if (-not ($lLines | Where-Object { $_.Trim() -eq $sSection })) {
                writeLog "ERROR: the setup script has no $sSection section."
                $iProblems += 1
            }
        }
        $iSources = ($lLines | Where-Object { $_.TrimStart().StartsWith("Source:") }).Count
        if ($iSources -lt 5) {
            writeLog "ERROR: the setup script lists only $iSources files to install, which is too"
            writeLog "       few to be right. A section has probably been lost."
            $iProblems += 1
        }
    
        # A flag valid in one section is not valid in every section. Inno Setup
    # rejects an unknown flag rather than ignoring it, and runasoriginaluser in
    # [UninstallRun] is what stopped a build: it is a [Run] flag, and the two
    # sections look similar enough that the mistake is easy.
    $dSectionFlags = @{
        "Run" = @("postinstall","skipifsilent","runascurrentuser","runasoriginaluser",
            "nowait","shellexec","waituntilterminated","waituntilidle","runhidden",
            "runminimized","runmaximized","skipifdoesntexist","unchecked","hidewizard",
            "64bit","dontlogparameters")
        "UninstallRun" = @("runhidden","runminimized","runmaximized","shellexec",
            "skipifdoesntexist","waituntilterminated","waituntilidle","64bit",
            "dontlogparameters","hidewizard")
    }
    $sSection = ""
    $iLine = 0
    foreach ($sLine in $lLines) {
        $iLine += 1
        $sTrimmed = $sLine.Trim()
        if ($sTrimmed -match '^\[(\w+)\]') { $sSection = $Matches[1] }
        if (-not $dSectionFlags.ContainsKey($sSection)) { continue }
        if ($sTrimmed -notmatch 'Flags:\s*([^;\\]+)') { continue }
        foreach ($sFlag in ($Matches[1] -split '\s+')) {
            if (-not $sFlag) { continue }
            if ($dSectionFlags[$sSection] -notcontains $sFlag.ToLower()) {
                writeLog "ERROR: line $iLine uses the flag $sFlag, which is not valid in"
                writeLog "       the [$sSection] section. Inno Setup rejects an unknown flag"
                writeLog "       rather than ignoring it."
                $iProblems += 1
            }
        }
    }

    # A line beginning with an opening bracket is read as a section header, and
        # a line beginning with a hash as a preprocessor directive, in both cases
        # before Pascal is compiled and regardless of any comment it sits inside.
        $lValidSections = @("[setup]","[types]","[components]","[tasks]","[dirs]","[files]",
            "[icons]","[ini]","[installdelete]","[languages]","[messages]","[custommessages]",
            "[langoptions]","[registry]","[run]","[uninstalldelete]","[uninstallrun]","[code]")
        $iLine = 0
        foreach ($sLine in $lLines) {
            $iLine += 1
            $sTrimmed = $sLine.Trim()
            if ($sTrimmed.StartsWith("[") -and (-not ($lValidSections -contains $sTrimmed.ToLower()))) {
                writeLog "ERROR: line $iLine begins with an opening bracket but is not a section"
                writeLog "       header, so Inno Setup will reject it: $sTrimmed"
                writeLog "       Start the line with a word instead, even inside a comment."
                $iProblems += 1
            }
        }
    
        # Inno Setup's preprocessor runs over the whole file before Pascal sees it,
        # and reads any line whose first non-blank character is a hash as a
        # directive. So #13#10 at the start of a line inside [Code] fails to
        # compile with nothing but a line number to go on. Catching it here says
        # what is wrong.
        $lDirectives = @("#define","#include","#if","#ifdef","#ifndef","#else",
            "#elif","#endif","#emit","#expr","#error","#pragma","#sub","#endsub",
            "#for","#dim","#undef","#file","#insert","#append")
        $iLine = 0
        foreach ($sLine in $lLines) {
            $iLine += 1
            $sTrimmed = $sLine.Trim()
            if (-not $sTrimmed.StartsWith("#")) { continue }
            $bKnown = $false
            foreach ($sDirective in $lDirectives) {
                if ($sTrimmed.ToLower().StartsWith($sDirective)) { $bKnown = $true; break }
            }
            if (-not $bKnown) {
                writeLog "ERROR: line $iLine begins with a leading hash that is not a preprocessor"
                writeLog "       directive: $sTrimmed"
                writeLog "       Inside [Code], put the value in a variable or start the line with"
                writeLog "       something else. Chr(13) + Chr(10) avoids the problem entirely."
                $iProblems += 1
            }
        }
    
        if ($iProblems -gt 0) {
            writeLog "The setup script has $iProblems problem(s). Fix them before compiling."
            exit 1
        }
        writeLog "The setup script checks out."
    }
}

function buildBridge {
    # The command line utility the JAWS scripts use.
    #
    # JAWS scripting cannot open a WebSocket, which is where every Chrome
    # DevTools command that reads or acts on a page travels. This program holds
    # that side: a script runs it, it asks the browser, and it writes the answer
    # to a file the script reads.
    #
    # Compiled with csc.exe from the .NET Framework, which is on every Windows
    # machine already, so this needs no Visual Studio and no NuGet.
    $pathSource = Join-Path $pathRoot "HomerView.cs"
    # exec\ HOLDS EVERY BUILT BINARY, as the kit lays a project out: the
    # bridge, the add-on and the installer, none of them in git. The compiler
    # will not create the folder it writes into, so it is made here first.
    $pathExec = Join-Path $pathRoot "exec"
    if (-not (Test-Path $pathExec)) { New-Item -ItemType Directory -Path $pathExec | Out-Null }
    $pathBridge = Join-Path $pathExec "HomerView.exe"
    if (-not (Test-Path $pathSource)) {
        writeLog "HomerView.cs is not here, so the JAWS bridge is skipped."
        writeLog "The NVDA add-on does not need it; only the JAWS scripts do."
        return
    }

    if (-not $pathCompiler) {
        $pathCompiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
        writeLog "  no compiler was handed in, so the .NET Framework one is used"
    }
    # A PROGRAM THAT IS RUNNING CANNOT BE OVERWRITTEN, and the compiler's
    # way of saying so is a CS2012 about a file in use, buried in its output.
    # FileDir's build says "FileDir.exe is running" and stops; so does this.
    # The bridge lives for one command, so this is rare -- but a command
    # waiting on a browser that never answers holds the file open for the
    # whole of its timeout.
    $pathBridgeOut = Join-Path $pathRoot "exec\HomerView.exe"
    if (Test-Path $pathBridgeOut) {
        foreach ($oProcess in (Get-Process -Name "HomerView" -ErrorAction SilentlyContinue)) {
            if ($oProcess.Path -and ($oProcess.Path -ieq $pathBridgeOut)) {
                writeLog "ERROR: HomerView.exe is running (process $($oProcess.Id)), so it cannot be rebuilt."
                writeLog "       Wait for the command it is serving to finish, or end it, and build again."
                exit 1
            }
        }
    }
    if (-not (Test-Path $pathCompiler)) {
        writeLog "ERROR: the compiler was not found at $pathCompiler."
        exit 1
    }
    writeLog "  compiler: $pathCompiler"

    if (Test-Path $pathBridge) {
        Remove-Item $pathBridge -Force
        writeLog "Removed the previous $pathBridge"
    }
    writeLog "Compiling with $pathCompiler"
    # System.Windows.Forms for the clipboard, which is the only way to put a
    # file on it in the format Explorer and Outlook understand. No window is
    # ever shown; the assembly is referenced for one class.
    #
    # System.Runtime.Serialization for JsonReaderWriterFactory, which reads the
    # browser's JSON and presents it as XML. That is what lets the JAWS side
    # use the XML functions it has instead of the JSON functions it does not,
    # and it means no JSON parser is written by hand on either side.
    #
    # System.Xml for XmlDocument and XPath. csc reads csc.rsp and references a
    # list of assemblies by default, and System.Xml is very likely on it -- but
    # "very likely" is how this project has lost afternoons before, a duplicate
    # reference costs nothing, and being wrong costs a build.
    #
    # ALL THREE SHIP WITH .NET FRAMEWORK. Nothing is downloaded, and no third
    # party JSON library is needed: JsonReaderWriterFactory has been in
    # System.Runtime.Serialization since .NET 3.5.
    #
    # System.IO.Compression for ZipArchive, which is how the .xlsx is
    # written. A spreadsheet is a zip of XML parts, so writing one needs no
    # library -- the same approach exportReport.py takes on the NVDA side.
    # See the note at the installer step: 2>&1 with ErrorActionPreference
    # "Stop" turns a native program's first stderr line into a TERMINATING
    # error, killing the script before it can log why. csc writes its errors
    # to stdout so this has not bitten here, but the trap is identical.
    # THE SHARED HOMER CLASSES ARE COMPILED IN, NOT REFERENCED.
    #
    # They are C# sources rather than a library, which suits this build: csc
    # is the whole toolchain here, there is no package manager, and a source
    # file cannot get out of step with the binary beside it. They are in the
    # same namespace, Homer, as this program, so nothing needs a using line.
    #
    # WHAT THEY REPLACED, and why the duplication was worth removing. Three
    # separate Content-Disposition parsers had grown in HomerView.cs and no
    # two of them agreed; a MIME-to-extension table had been written out a
    # second time; and forty lines edited an .inix file by hand. All of that
    # is one call each now, into code EdSharp and the other Homer tools use.
    #
    # MISSING ONES ARE NAMED RATHER THAN SKIPPED. A shared class that quietly
    # is not there produces a compile error a hundred lines long about
    # undefined names, and the real cause -- one absent file -- appears
    # nowhere in it.
    $lShared = @()
    if ($sHomerSources) {
        # THE KIT'S OWN FILES, named by the wrapper, semicolon-joined. The
        # first version split on quotes, and the quotes had been stripped at
        # the cmd-to-PowerShell boundary, so nothing was found and the bridge
        # was compiled with no kit at all. A list that comes in empty is now a
        # failure here, not a compiler error forty lines later.
        foreach ($sOne in $sHomerSources.Split(";")) {
            $sOne = $sOne.Trim().Trim('"')
            if (-not $sOne) { continue }
            if (-not (Test-Path $sOne)) {
                writeLog "ERROR: kit source not found: $sOne"
                exit 1
            }
            $lShared += $sOne
            writeLog "  kit source: $sOne"
        }
        if ($lShared.Count -eq 0) {
            writeLog "ERROR: the wrapper named kit sources but none could be read from: $sHomerSources"
            exit 1
        }
    } else {
        foreach ($sName in @("Inix.cs", "Web.cs")) {
            $pathShared = Join-Path $pathRoot "homer\$sName"
            if (Test-Path $pathShared) {
                $lShared += $pathShared
                writeLog "  shared class: homer\$sName (no kit was handed in)"
            } else {
                writeLog "ERROR: no kit sources were handed in and homer\$sName is not here."
                writeLog "       Run buildHomerView.cmd, which finds the Homer Development Kit."
                exit 1
            }
        }
    }

    $ErrorActionPreference = "Continue"
    # WINEXE, NOT EXE, AND THE REASON IS THE DESKTOP SHORTCUT.
    #
    # HomerView.exe is now the target of a .lnk carrying Alt+Control+Shift+H, and a
    # console program started from a shortcut puts a black window on the
    # screen and a button on the taskbar before it does anything. Nothing is
    # lost by removing the console: every answer this program gives is
    # written to a FILE, which is what the JAWS scripts read, and everything
    # else goes to its log. Console.Error.WriteLine still compiles and simply
    # goes nowhere.
    #
    # The one thing that changes is below: PowerShell does not wait for a
    # windows program the way it waits for a console one.
    $sOutput = & $pathCompiler /nologo /target:winexe /platform:x64 `
        /reference:System.Windows.Forms.dll `
        /reference:System.Runtime.Serialization.dll `
        /reference:System.Xml.dll `
        /reference:System.IO.Compression.dll `
        "/out:$pathBridge" $pathSource $lShared 2>&1 | Out-String
    $iExit = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    foreach ($sLine in ($sOutput -split "`n")) {
        if ($sLine.Trim()) { writeLog "    $($sLine.Trim())" }
    }
    if ($iExit -ne 0 -or -not (Test-Path $pathBridge)) {
        writeLog "ERROR: the bridge did not build, exit code $iExit."
        exit 1
    }
    writeLog "Built HomerView.exe, $([math]::Round((Get-Item $pathBridge).Length / 1KB)) KB."

    # It must at least run. A program that compiles and will not start is worth
    # finding here rather than from a JAWS script that got no answer.
    $pathProbe = Join-Path $env:TEMP "HomerViewProbe.txt"
    if (Test-Path $pathProbe) { Remove-Item $pathProbe -Force }
    # START-PROCESS -WAIT, BECAUSE THE PROGRAM IS NOW A WINDOWS ONE.
    # PowerShell waits for a console program to exit before carrying on; for
    # a windows program it does not, so the call operator would return at
    # once and the test below would read a file that had not been written
    # yet -- a probe that fails only sometimes, which is the worst kind.
    Start-Process -FilePath $pathBridge -ArgumentList @("tabs", $pathProbe) `
        -WindowStyle Hidden -Wait
    if (Test-Path $pathProbe) {
        writeLog "It runs and answers. (An error about connecting is expected here:"
        writeLog "HomerView's browser is not running during a build.)"
        Remove-Item $pathProbe -Force
    } else {
        writeLog "WARNING: the bridge wrote no file, which it should do even on failure."
    }
}


function buildAddon {
    # Packaging the add-on, folded in from what used to be a second script.
    #
    # One script, one log. The split meant two logs for one build, and the
    # reason for a failure could be in whichever of them the reader had not
    # been asked for. Nothing about packaging a zip needed its own program.
    #
    # The add-on always has the same name, HomerView.nvda-addon, so the setup
    # script never has to be edited when the version changes. One file, not
    # two: a copy named for the version was written here as well, and two
    # identical files with different names in one folder invites the wrong one
    # being picked up. The version is in the manifest, which is what NVDA reads.
    $pathAddon = Join-Path $pathRoot "addon"
    $pathBuild = Join-Path $pathRoot "exec"
    # What went in, gathered rather than announced line by line.
    $script:lIncluded = New-Object System.Collections.ArrayList

    # THE PATCH NUMBER IS RAISED HERE, AND THIS CLOSES A REAL GAP.
    #
    # release tells the reader "BuildHomerView.cmd takes a NEW version every
    # time it runs, and skips any number that is already released." THAT WAS
    # NOT TRUE: the build only ever READ the version from manifest.ini, so a
    # whole day's work could be built at a number already published, and
    # release would rightly refuse to publish it -- looking like a failure
    # when it was doing its job.
    #
    # A build that produces a distinct artefact should carry a distinct number.
    # Only the LAST component moves, so setting 1.49.0 by hand in manifest.ini
    # still works and is still the way to mark anything bigger than a fix.
    $pathManifest = Join-Path $pathAddon "manifest.ini"
    $pathVersion = Join-Path $pathRoot "version.txt"
    # version.txt IS THE SOURCE OF TRUTH, AS THE KIT HAS IT. The add-on's
    # manifest.ini used to be, and version.txt was written FROM it at the
    # end. The kit turns that round: version.txt holds one line and is never
    # pushed; the build steps it and writes every other place the number
    # appears from it -- here manifest.ini, and the installer, which reads
    # version.txt itself at compile time. One number, one file, and
    # release reads it back out of the built installer so the tag cannot
    # disagree with what was built.
    #
    # SEEDED FROM manifest.ini WHEN ABSENT, not from 1.0.0 as the template
    # does: HomerView is past 1.48, and a fresh clone that reset it would
    # publish a release number older than every installed copy.
    $sVersion = ""
    if (Test-Path $pathVersion) {
        $sVersion = (Get-Content $pathVersion -Raw).Trim()
    }
    if (-not $sVersion) {
        foreach ($sLine in Get-Content $pathManifest) {
            if ($sLine -match '^\s*version\s*=\s*"([^"]+)"') { $sVersion = $Matches[1] }
        }
        writeLog "No version.txt, so the version was taken from manifest.ini: $sVersion"
    }
    # nobump KEEPS THE NUMBER, as the kit's builds do. A rebuild that changes
    # nothing a user would notice should not spend a release number.
    if ($sBump -eq "nobump") {
        writeLog "Version kept at $sVersion (nobump)"
    } elseif ($sVersion -match '^(.*)\.(\d+)$') {
        $sWas = $sVersion
        $sVersion = "$($Matches[1]).$([int]$Matches[2] + 1)"
        writeLog "Version: $sWas -> $sVersion"
    } else {
        writeLog "WARNING: the version '$sVersion' does not end in a number, so it was left alone."
    }
    if (-not $sVersion) {
        writeLog "ERROR: no version was found in manifest.ini"
        exit 1
    }
    writeLog "Version $sVersion"

    # Written out so the installed program can say what it is.
    #
    # Nothing that reaches the installation folder carried the version, so the
    # JAWS log's header said "HomerView unknown". The installer passes it as a
    # parameter too, and this is the belt to that pair of braces: a parameter
    # can go astray between four programs, a file in the folder cannot.
    Set-Content -Path $pathVersion -Value $sVersion -Encoding ASCII -NoNewline
    # And manifest.ini EVERY build, bumped or not, so the two cannot drift.
    $lManifestLines = Get-Content $pathManifest | ForEach-Object {
        if ($_ -match '^\s*version\s*=') { "version = `"$sVersion`"" } else { $_ }
    }
    Set-Content -Path $pathManifest -Value $lManifestLines -Encoding UTF8
    writeLog "Wrote version.txt and manifest.ini for $sVersion"

    # THE TWO ACCESSIBILITY ENGINES, FETCHED ONCE AT BUILD TIME.
    #
    # They used to be pulled from a CDN on FIRST USE, on the user's machine.
    # That put a network fetch inside a command the JAWS side waits on -- and a
    # blocked JSL script blocks ALL of JAWS, so a tester lost speech entirely
    # for minutes while a download stalled, and got no report at the end of it.
    #
    # Fetched here instead, and installed beside the program: the ordinary case
    # never touches the network. THE BUILD IS THE RIGHT PLACE FOR A DOWNLOAD --
    # it has a developer watching it, a log, and no screen reader waiting on it.
    #
    # A failure here is a WARNING, not an error: the runtime still falls back to
    # the CDN, and a build should not stop because a CDN is briefly unwell.
    foreach ($oEngine in @(
        @{ Name = "Axe.js"; Urls = @(
            "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js",
            "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js",
            "https://unpkg.com/axe-core@4.10.2/axe.min.js") },
        @{ Name = "Ace.js"; Urls = @(
            "https://unpkg.com/accessibility-checker-engine@latest/ace.js",
            "https://cdn.jsdelivr.net/npm/accessibility-checker-engine@latest/ace.js",
            "https://able.ibm.com/rules/archives/latest/js/ace.js") },
        # THE LANGUAGE ENGINE, WHICH WAS MISSED THE FIRST TIME.
        #
        # Names uses a THIRD engine, compromise, and only the two accessibility
        # ones were shipped. A tester got "The language engine could not be
        # loaded" on acb.org -- HomerView's own message, not a JAWS one -- which
        # is what a blocked or slow CDN looks like from inside that command.
        # jsdelivr first: unpkg answered 404 for this exact path on 15 August.
        @{ Name = "Nlp.js"; Urls = @(
            "https://cdn.jsdelivr.net/npm/compromise@14/builds/compromise.min.js",
            "https://unpkg.com/compromise@latest/builds/compromise.min.js",
            "https://unpkg.com/compromise@14/builds/compromise.min.js") }
    )) {
        $pathEngine = Join-Path $pathRoot $oEngine.Name
        $bGot = $false
        foreach ($sUrl in $oEngine.Urls) {
            if ($bGot) { break }
            try {
                $ErrorActionPreference = "Continue"
                Invoke-WebRequest -Uri $sUrl -OutFile $pathEngine -UseBasicParsing -TimeoutSec 30
                $ErrorActionPreference = "Stop"
                $iSize = (Get-Item $pathEngine).Length
                # A CDN error page is a few hundred bytes; an engine is hundreds
                # of thousands. Size is the cheapest way to tell them apart.
                if ($iSize -gt 100000) {
                    writeLog "Fetched $($oEngine.Name), $([int]($iSize / 1024)) KB, from $sUrl"
                    $bGot = $true
                } else {
                    writeLog "  $sUrl answered with only $iSize bytes, so it was not the engine"
                }
            } catch {
                $ErrorActionPreference = "Stop"
                writeLog "  $sUrl did not answer: $($_.Exception.Message)"
            }
        }
        if (-not $bGot) {
            writeLog "WARNING: $($oEngine.Name) could not be fetched. The installer will ship"
            writeLog "         whatever copy is already there, and the runtime still has the CDN."
        }
    }

    # THE START PAGE, BUILT ONCE AS AN ASSET.
    #
    # It used to be written at run time by the NVDA add-on only, so a JAWS-only
    # machine never had one and the browser opened about:blank. Composing a
    # second copy in C# would have meant two pages drifting apart, so it is
    # generated HERE from the add-on's own generator and installed beside the
    # program. One source, one file, both screen readers.
    try {
        $pathStartPage = Join-Path $pathRoot "templates\Start.htm"
        $pathGenerator = Join-Path $pathAddon "globalPlugins\homerView\startPage.py"
        if (Test-Path $pathGenerator) {
            $sPython = (Get-Command python -ErrorAction SilentlyContinue).Source
            if ($sPython) {
                $ErrorActionPreference = "Continue"
                $sPage = & $sPython -c "import sys; sys.path.insert(0, r'$pathAddon\globalPlugins\homerView'); import startPage; sys.stdout.write(startPage.getStartPageText())" 2>&1 | Out-String
                $ErrorActionPreference = "Stop"
                if ($sPage -and $sPage.Contains("<")) {
                    Set-Content -Path $pathStartPage -Value $sPage -Encoding UTF8
                    writeLog "Wrote Start.htm from the add-on's generator, $($sPage.Length) characters"
                } else {
                    writeLog "WARNING: the start page generator produced nothing usable, so Start.htm was left alone."
                }
            } else {
                writeLog "WARNING: python is not on the path, so Start.htm was not regenerated."
            }
        }
    } catch {
        writeLog "WARNING: Start.htm could not be generated: $($_.Exception.Message)"
    }

    if (-not (Test-Path $pathBuild)) {
        New-Item -ItemType Directory -Path $pathBuild | Out-Null
        writeLog "Created $pathBuild"
    }

    $pathOutput = Join-Path $pathBuild "HomerView.nvda-addon"
    if (Test-Path $pathOutput) {
        Remove-Item $pathOutput -Force
        writeLog "Removed the previous $pathOutput"

        # Stale documents. Unzipping a new version over an old folder adds and
        # replaces but never removes, so a document that has been renamed leaves
        # its old name behind and that old name is then packaged. HomerView.htm
        # survived the rename to HomerView.htm exactly this way.
        $pathDocs = Join-Path $pathAddon "doc\en"
        # FILLED FROM help\ ON EVERY BUILD, not kept as a fourth copy. The
        # add-on carries its documents so NVDA's add-on manager can show them,
        # and until 26 September 2026 those were checked-in copies that
        # drifted from the real ones. Now help\ is the source, README comes
        # from the top, and readme.html -- an .html duplicate of README.htm
        # -- is no longer expected at all.
        if (-not (Test-Path $pathDocs)) { New-Item -ItemType Directory -Path $pathDocs | Out-Null }
        foreach ($sDoc in @("Announce", "Developer", "History", "HomerView", "hotkeys")) {
            $pathFrom = Join-Path $pathRoot "help\$sDoc.htm"
            if (Test-Path $pathFrom) { Copy-Item $pathFrom (Join-Path $pathDocs "$sDoc.htm") -Force }
        }
        $pathReadme = Join-Path $pathRoot "README.htm"
        if (Test-Path $pathReadme) { Copy-Item $pathReadme (Join-Path $pathDocs "README.htm") -Force }
        writeLog "Refreshed the add-on documents from help\"
        if (Test-Path $pathDocs) {
            $lExpected = @("Announce.htm", "HomerView.htm", "Developer.htm", "History.htm",
                "README.htm", "hotkeys.htm")
            foreach ($fileDoc in (Get-ChildItem -Path $pathDocs -File)) {
                if ($lExpected -notcontains $fileDoc.Name) {
                    Remove-Item $fileDoc.FullName -Force
                    writeLog "Removed the stale document $($fileDoc.Name), which the project no longer generates"
                }
            }
        }
    }
    # Any versioned copy an earlier build left behind, so the folder holds one file.
    foreach ($pathOld in (Get-ChildItem $pathBuild -Filter "HomerView-*.nvda-addon" -ErrorAction SilentlyContinue)) {
        Remove-Item $pathOld.FullName -Force
        writeLog "Removed the leftover $($pathOld.Name)"
    }

    foreach ($pathCache in (Get-ChildItem -Path $pathAddon -Recurse -Directory -Filter "__pycache__")) {
        Remove-Item $pathCache.FullName -Recurse -Force
        writeLog "Removed $($pathCache.FullName)"
    }

    foreach ($pathFile in (Get-ChildItem -Path $pathAddon -Recurse -File)) {
        $null = $lIncluded.Add($pathFile.FullName.Substring($pathAddon.Length + 1))
    }

    Compress-Archive -Path (Join-Path $pathAddon "*") -DestinationPath "$pathOutput.zip" -Force
    Move-Item "$pathOutput.zip" $pathOutput -Force
    $iModules = @($lIncluded | Where-Object { $_ -like "*.py" }).Count
    $iDocuments = @($lIncluded | Where-Object { $_ -like "doc\*" }).Count
    writeLog "Included $($lIncluded.Count) files: $iModules Python modules, $iDocuments documents, and the manifest."
    writeLog "Wrote $pathOutput"



}

writeLog "buildHomerView starting"

# The environment, recorded before anything can fail. A log that says only what
# went wrong, and not what it went wrong on, sends the reader back to ask.
writeLog "  script:            $($MyInvocation.MyCommand.Path)"
writeLog "  PowerShell:        $($PSVersionTable.PSVersion)"
writeLog "  platform:          $([System.Environment]::OSVersion.VersionString)"
writeLog "  working directory: $(Get-Location)"
writeLog "  project root:      $pathRoot"
writeLog "  command line:      $($MyInvocation.Line.Trim())"
$commandPython = Get-Command python -ErrorAction SilentlyContinue
if ($commandPython) {
    writeLog "  Python:            $(& python --version 2>&1)"
}
writeLog ""

# The checks run FIRST. An earlier version ran them after the installer was
# compiled, which the log made plain: buildHomerView finished, and then it
# announced it was checking the setup script. A check nobody can act on is not
# a check, and the whole point of these is to stop a bad script reaching Inno
# Setup, which reports a line number and four words.
# THE DOCUMENTS, MADE FROM THEIR MARKDOWN BEFORE ANYTHING IS CHECKED.
#
# Every .md in the documentation set has a .htm beside it, and both are
# delivered -- that is the standing rule. The .htm files were being made by
# hand, on whichever machine last had pandoc to hand, and committed. So they
# could go missing without anything noticing until the installer asked for
# one: on 25 September 2026 homerTidy took all six for stray drafts, moved
# them to notes\drafts, and the next build stopped at "HomerView.htm does not
# exist".
#
# A generated file is regenerated, not mourned. This makes each .htm from its
# .md with the same pandoc call the kit's builds use, and only when the .md is
# newer or the .htm is absent, so a build that changed no document costs
# nothing here. pandoc is found on the PATH or at the standard machine-wide
# install, which is where installPandoc.cmd puts it.
function buildDocuments {
    $pathPandoc = ""
    $oCommand = Get-Command pandoc -ErrorAction SilentlyContinue
    if ($oCommand) { $pathPandoc = $oCommand.Source }
    if (-not $pathPandoc) {
        foreach ($sTry in @((Join-Path ${env:ProgramFiles} "Pandoc\pandoc.exe"),
                            (Join-Path $env:LOCALAPPDATA "Pandoc\pandoc.exe"),
                            (Join-Path $pathRoot "pandoc.exe"))) {
            if (Test-Path $sTry) { $pathPandoc = $sTry; break }
        }
    }
    if (-not $pathPandoc) {
        writeLog "WARNING: pandoc was not found, so no .htm was made from a .md."
        writeLog "         Run installPandoc.cmd; the installer needs every .htm the .iss names."
        return
    }
    writeLog "Documents: pandoc at $pathPandoc"
    $iMade = 0
    # README at the top, everything else in help\, as the kit lays it out.
    foreach ($sName in @("Announce", "Developer", "History", "HomerView", "README", "hotkeys")) {
        $sWhere = if ($sName -eq "README") { $pathRoot } else { Join-Path $pathRoot "help" }
        $pathMd = Join-Path $sWhere "$sName.md"
        $pathHtm = Join-Path $sWhere "$sName.htm"
        if (-not (Test-Path $pathMd)) { continue }
        $bMake = -not (Test-Path $pathHtm)
        if (-not $bMake) {
            $bMake = (Get-Item $pathMd).LastWriteTimeUtc -gt (Get-Item $pathHtm).LastWriteTimeUtc
        }
        if (-not $bMake) { continue }
        $sOut = & $pathPandoc -s --toc --toc-depth=3 $pathMd -o $pathHtm 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            writeLog "ERROR: pandoc failed on $sName.md: $($sOut.Trim())"
            exit 1
        }
        # Pandoc writes neither the byte order mark nor CRLF; the Homer encoding
        # is put on afterwards, as fixEncoding would, so the file is right the
        # moment it exists rather than after the next build.
        $sText = [System.IO.File]::ReadAllText($pathHtm)
        $sText = $sText -replace "`r`n", "`n" -replace "`n", "`r`n"
        [System.IO.File]::WriteAllText($pathHtm, $sText, (New-Object System.Text.UTF8Encoding($true)))
        writeLog "  made $sName.htm from $sName.md"
        $iMade += 1
    }
    writeLog "Documents: $iMade made, the rest already current"
}

writeLog "Step 0 of 5: the documents"
# makeDocs FIRST: it writes help\hotkeys.md, configs\Hotkeys.inix, the start
# page and its command list from the two key tables, and those are what
# pandoc then turns into .htm. Run by hand until 26 September 2026, which is
# how Hotkeys.inix came to list keys that no longer existed.
$pathMakeDocs = Join-Path $pathRoot "scripts\makeDocs.py"
if (Test-Path $pathMakeDocs) {
    $sOut = & python $pathMakeDocs 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        writeLog "ERROR: makeDocs failed:"
        foreach ($sLine in ($sOut -split "`n")) { if ($sLine.Trim()) { writeLog "    $($sLine.Trim())" } }
        exit 1
    }
    foreach ($sLine in ($sOut -split "`n")) { if ($sLine.Trim()) { writeLog "  makeDocs: $($sLine.Trim())" } }
}
buildDocuments
writeLog ""
writeLog "Step 1 of 5: checking the setup script and the sources"
writeLog "Checking HomerView_setup.iss"
checkSetupScript

# A second copy of a shipped file is a copy that will diverge, and this one
# already had. The installer ships jaws\*, so the copies of HomerView.jss,
# HomerView.jkm, HomerView.jsd and HomerViewGlobal.jkm that sat in the project
# root were read by nobody, and the root HomerView.jss had been left behind at
# an older and broken revision. Anyone opening the one in the root would have
# been reading a file that no build and no installer had touched for days.
# The old build\ folder is the same story: exec\ holds the add-on now.
if (Test-Path (Join-Path $pathRoot "build")) {
    writeLog "WARNING: a build\ folder is still in the project root. Built output lives"
    writeLog "         in exec\ now; tidy will move the old one to notes."
}
# AND THE OLD jaws\ FOLDER ITSELF, since the set moved to scripts\jaws on
# 26 September 2026. A copy left at the old place is the same trap one
# level down: read by nobody, and the first thing a reader opens.
if (Test-Path (Join-Path $pathRoot "jaws")) {
    writeLog "WARNING: a jaws\ folder is still in the project root. The script set lives"
    writeLog "         in scripts\jaws\ now; tidy will move the old one to notes."
}
foreach ($sStray in @("HomerView.jss", "HomerView.jkm", "HomerView.jsd", "HomerViewGlobal.jkm")) {
    $pathStray = Join-Path $pathRoot $sStray
    if (Test-Path $pathStray) {
        writeLog "WARNING: $sStray is in the project root as well as in scripts\jaws\, and only the"
        writeLog "         one in scripts\jaws\ is built and shipped. Delete the root copy."
    }
}
writeLog ""

# The JAWS scripts, before anything is built rather than after everything is
# installed.
#
# Every JSL failure so far has been found by building an add-on, compiling an
# installer, running it, ticking the JAWS box and then opening a log in
# C:\temp: minutes for an answer the compiler gives in under a second. The
# check runs here, on the same footing as the setup script check, and for the
# same reason.
#
# It does not stop the build. The NVDA add-on is unaffected by the state of the
# JAWS scripts, and an installer worth testing should still be produced. What
# it does is make the build finish with a failure, so that release does not
# run on a release whose JAWS half does not compile.
# THE POWERSHELL WE SHIP IS PARSED HERE, NOT ON A TESTER'S MACHINE.
#
# chainJawsScripts.ps1 and installJawsScripts.ps1 run at INSTALL time, so a
# syntax error in either survives every build and first appears when somebody
# installs -- which is exactly what happened once: a trailing comma in an array
# literal meant chainJawsScripts died before writing one line of its log, and
# the installer could only report that the keys had not been bound.
#
# PowerShell's own parser answers this in a moment. Nothing is executed.
writeLog "Step 1b of 5: parsing the PowerShell that the installer runs"
foreach ($sName in @("scripts\chainJawsScripts.ps1", "scripts\installJawsScripts.ps1", "scripts\checkJawsScripts.ps1")) {
    $pathScript = Join-Path $pathRoot $sName
    if (-not (Test-Path $pathScript)) {
        writeLog "  $sName is not here, so it was not parsed."
        continue
    }
    $lErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $pathScript, [ref] $null, [ref] $lErrors)
    if ($lErrors -and $lErrors.Count -gt 0) {
        writeLog "  ERROR: $sName does not parse. It would fail at install time:"
        foreach ($oError in $lErrors) {
            writeLog "    line $($oError.Extent.StartLineNumber): $($oError.Message)"
        }
        writeLog "buildHomerView finished with a failure"
        exit 1
    }
    writeLog "  $sName parses"
}

writeLog "Step 2 of 5: checking that the JAWS scripts compile"
$script:bJawsFailed = $false
$pathCheck = Join-Path $pathRoot "scripts\checkJawsScripts.ps1"
if (-not (Test-Path $pathCheck)) {
    writeLog "WARNING: checkJawsScripts.ps1 is not here, so the JAWS scripts were not checked."
} else {
    # A child process, and its output captured into this log. The one log a
    # person is asked for has to hold the reason, not a note that the reason
    # is in another file.
    $ErrorActionPreference = "Continue"
    $sOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $pathCheck 2>&1 | Out-String
    $iCheck = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    foreach ($sLine in ($sOutput -split "`n")) {
        $sTrimmed = $sLine.Trim()
        if (-not $sTrimmed) { continue }
        # The child stamps its own lines and this log stamps them again, so
        # every folded line read "2026-08-14 00:39:18  2026-08-14 00:39:18 ...".
        # Twice the date and none of the meaning, on every line of a log that
        # is listened to rather than glanced at.
        # The trailing whitespace is optional. It was not, and the child's
        # BLANK lines arrive as a bare timestamp with nothing after it for the
        # pattern to match, so half of them survived and the log still read
        # like a stutter.
        $sTrimmed = ($sTrimmed -replace '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*', '').Trim()
        if (-not $sTrimmed) { continue }
        writeLog "    $sTrimmed"
    }
    # THE CHILD'S OWN LOG FILE, FOLDED IN TOO -- OR ACCOUNTED FOR.
    #
    # He asked for ONE file to upload after a build. Its console output is
    # already above, and comparing the two files line for line showed every
    # line of checkJawsScripts.log ALREADY PRESENT HERE. So there is nothing to
    # copy, and copying it anyway would double a 200-line log for no gain.
    #
    # What was missing is SAYING SO. A second log file sitting beside this one
    # invites the question of what is in it, and the answer belongs in the file
    # he actually sends.
    $pathCheckLog = Join-Path $pathRoot "checkJawsScripts.log"
    if (Test-Path $pathCheckLog) {
        $lCheckLog = @(Get-Content $pathCheckLog | Where-Object { $_.Trim() })
        $lHere = @(Get-Content $pathLog | Where-Object { $_.Trim() }) |
            ForEach-Object { ($_ -replace '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*', '').Trim() }
        $lExtra = @($lCheckLog | ForEach-Object {
                ($_ -replace '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*', '').Trim()
            } | Where-Object { $_ -and ($lHere -notcontains $_) })
        if ($lExtra.Count -eq 0) {
            writeLog "    checkJawsScripts.log holds nothing that is not already above."
        } else {
            writeLog "    checkJawsScripts.log also held $($lExtra.Count) line(s), folded in here:"
            foreach ($sLine in $lExtra) { writeLog "      $sLine" }
        }
    }
    if ($iCheck -ne 0) {
        writeLog "ERROR: the JAWS scripts did not compile. The build carries on, because the"
        writeLog "       NVDA add-on does not depend on them, but it will finish as a failure."
        $script:bJawsFailed = $true
    }
}
writeLog ""

writeLog "Step 3 of 5: building the bridge for JAWS"
buildBridge
writeLog ""

writeLog "Step 4 of 5: building the add-on"
buildAddon

# Even on success, record what the add-on build produced, so this log alone
# answers the ordinary questions: how many files, and how big.
$pathBuilt = Join-Path $pathRoot "exec\HomerView.nvda-addon"
if (Test-Path $pathBuilt) {
    $nAddonSize = [math]::Round((Get-Item $pathBuilt).Length / 1KB)
    writeLog "The add-on is $nAddonSize KB."
}

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

writeLog "Step 5 of 5: compiling the installer"
# Captured, not just run. The first version let Inno Setup print to the console
# and logged four words when it failed, so the one log a person uploads said
# that something went wrong and nothing about what. Inno Setup names the line
# and the reason; that belongs in the log.
# 2>&1 IS A TRAP WHEN ErrorActionPreference IS "Stop", AND IT COST A BUILD.
#
# Redirecting a native program's stderr into the pipeline turns each of its
# error lines into a PowerShell ErrorRecord. With Stop in force, the FIRST such
# line TERMINATES THE SCRIPT -- so when Inno Setup reported a fault, this line
# threw before the next line could log anything, and the log simply STOPPED
# after "Step 5 of 5" with no reason given. The capture written to explain a
# failure was itself the reason nothing was explained.
#
# Stopping for the duration of the call is enough: the exit code is checked
# immediately below, so a failure is still a failure -- it is now a REPORTED
# one.
$sOutput = ""
try {
    $ErrorActionPreference = "Continue"
    # THE KIT'S FOLDER, TOLD TO THE INSTALLER. HomerView_setup.iss includes the
    # kit's HomerComponents.iss, and defaults to C:\HomerDev; when the wrapper
    # found the kit somewhere else, that is where the include must come from.
    # The kit is the nearest folder above a C# source that holds
    # Templates\HomerComponents.iss. (It was taken as two levels up, which
    # stopped being true when the sources moved into exec\CSharp, HomerDev
    # 1.43.22: the build of 28 September told Inno the kit was C:\HomerDev\exec.)
    $lInnoArguments = @()
    if ($sHomerSources) {
        $sFirst = $sHomerSources.Split(";")[0].Trim().Trim('"')
        $sKit = ""
        $sClimb = if ($sFirst) { Split-Path -Parent $sFirst } else { "" }
        while ($sClimb) {
            if (Test-Path -LiteralPath (Join-Path $sClimb "Templates\HomerComponents.iss")) { $sKit = $sClimb; break }
            $sParent = Split-Path -Parent $sClimb
            if ($sParent -eq $sClimb) { break }
            $sClimb = $sParent
        }
        if ($sKit) {
            $lInnoArguments += "/DHomerDev=$sKit"
            writeLog "  telling the installer the kit is at $sKit"
        }
    }
    $lInnoArguments += (Join-Path $pathRoot "HomerView_setup.iss")
    $sOutput = & $pathCompiler @lInnoArguments 2>&1 | Out-String
    $iExit = $LASTEXITCODE
} finally {
    $ErrorActionPreference = "Stop"
}
if ($iExit -ne 0) {
    writeLog "ERROR: the installer did not compile, exit code $iExit."
    writeLog "Inno Setup said:"
    foreach ($sLine in ($sOutput -split "`n")) {
        if ($sLine.Trim()) { writeLog "    $($sLine.Trim())" }
    }
    exit 1
}
# On success only the last few lines matter; the rest is a list of files.
$lLines = @($sOutput -split "`n" | Where-Object { $_.Trim() })
foreach ($sLine in ($lLines | Select-Object -Last 3)) {
    writeLog "    $($sLine.Trim())"
}

# AT THE TOP OF THE PROJECT (OutputDir=.), where scripts\release looks. A copy
# an older build left in exec is removed, so there is one installer to find.
$pathInstaller = Join-Path $pathRoot "HomerView_setup.exe"
$pathOldInstaller = Join-Path $pathRoot "exec\HomerView_setup.exe"
if (Test-Path $pathOldInstaller) { Remove-Item -LiteralPath $pathOldInstaller -Force; writeLog "Removed the old exec\HomerView_setup.exe" }
if (-not (Test-Path $pathInstaller)) {
    writeLog "ERROR: HomerView_setup.exe was not produced. Check OutputDir in the setup script."
    exit 1
}
# Trimmed. A version resource is a fixed-width field, so it arrives padded,
# and the log read "version 1.41.0              , 2.7 MB".
$sVersion = ((Get-Item $pathInstaller).VersionInfo.FileVersion).Trim()
writeLog "Built HomerView_setup.exe, version $sVersion, $([math]::Round((Get-Item $pathInstaller).Length/1MB,1)) MB"
# What was built is checked against what was meant to be built. The add-on and
# the installer carry versions from two different files, and a release where
# they disagree is one nobody notices until a user reports the wrong number.
$sManifestVersion = ""
$pathManifest = Join-Path $pathRoot "addon\manifest.ini"
if (Test-Path $pathManifest) {
    $matchVersion = Select-String -Path $pathManifest -Pattern 'version\s*=\s*"([^"]+)"'
    if ($matchVersion) { $sManifestVersion = $matchVersion.Matches[0].Groups[1].Value }
}
if ($sManifestVersion -and ($sManifestVersion -ne $sVersion)) {
    writeLog "ERROR: the add-on says $sManifestVersion and the installer says $sVersion."
    writeLog "       They come from addon\manifest.ini and HomerView_setup.iss, and both"
    writeLog "       need changing for a release."
    exit 1
}
writeLog "The add-on and the installer both say $sVersion."

# Every module the add-on imports must be inside it. A module left out builds
# cleanly and fails on the user's machine at the moment they press the key.
$pathBuiltAddon = Join-Path $pathRoot "exec\HomerView.nvda-addon"
if (-not (Test-Path $pathBuiltAddon)) {
    writeLog "ERROR: $pathBuiltAddon was not built."
    exit 1
}
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($pathBuiltAddon)
    try {
        $lInside = @($archive.Entries | ForEach-Object { $_.FullName })
    } finally {
        $archive.Dispose()
    }
    $iPacked = @($lInside | Where-Object { $_ -like "*.py" }).Count
    # __pycache__ is not source and is never packaged, so it must not be
    # counted on the side that is compared against the package.
    $iOnDisk = @(Get-ChildItem -Path (Join-Path $pathRoot "addon") -Filter "*.py" -Recurse |
        Where-Object { $_.FullName -notlike "*__pycache__*" }).Count
    if ($iPacked -ne $iOnDisk) {
        writeLog "ERROR: $iOnDisk Python files are on disk but $iPacked are in the add-on."
        writeLog "       A module left out builds cleanly and fails on the user's machine."
        # Now the names matter, which is why they were kept rather than only
        # counted. Listing them every time buried everything else in the log.
        $lPackedNames = @($lInside | Where-Object { $_ -like "*.py" } |
            ForEach-Object { Split-Path $_ -Leaf })
        foreach ($fileOnDisk in (Get-ChildItem -Path (Join-Path $pathRoot "addon") -Filter "*.py" -Recurse |
                Where-Object { $_.FullName -notlike "*__pycache__*" })) {
            if ($lPackedNames -notcontains $fileOnDisk.Name) {
                writeLog "       missing from the add-on: $($fileOnDisk.Name)"
            }
        }
        exit 1
    }
    writeLog "All $iPacked Python modules are in the add-on."
} catch {
    # A check that cannot run is worth saying so about. It is not worth
    # stopping a build that has otherwise succeeded, and an earlier version
    # did exactly that: it referred to a variable that did not exist, and the
    # script died where the log stops, with nothing written to say why.
    writeLog "WARNING: the add-on could not be checked: $($_.Exception.Message)"
}

if ($script:bJawsFailed) {
    writeLog "The add-on and the installer were built, and can be installed and tested."
    writeLog "The JAWS scripts did not compile, so this build is NOT ready for release."
    writeLog "buildHomerView finished with a failure"
    exit 1
}
writeLog "Ready for release."
writeLog "buildHomerView finished"
# EXPLICIT, so the exit code cannot be inherited from the last native
# command that happened to run. His routine keys off it.
exit 0

# --- Check the setup script before anyone compiles it -----------------------
#
# Inno Setup rejects a directive specified twice and fails on a missing source
# file, both at compile time. Finding either here means the failure is reported
# next to the change that caused it rather than minutes later in another program.


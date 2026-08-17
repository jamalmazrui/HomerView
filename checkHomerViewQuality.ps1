# checkHomerViewQuality.ps1 -- fifteen quality checks for the HomerView JAWS port.
#
# READ-ONLY. It reads jaws\HomerView.jss, jaws\HomerView.jkm, jaws\HomerView.jsd
# and HomerView.cs, and writes nothing but its own log beside this script. It
# cannot damage a build.
#
# Each check reports WHAT IT FOUND before it judges. A check that only says
# "passed" is the project's own recurring fault wearing the uniform of a
# solution: it tells you the step ran, not that it worked.
#
# The eleventh check in the notes -- nothing used before it is defined -- is
# not here. It already lives in checkJawsScripts.ps1, and two implementations
# of one rule eventually disagree.
#
# Regexes are single quoted because PowerShell interpolates $ and ` inside
# double quotes. That is the language requiring a form, not a style choice.

param (
    [string] $sRoot = "",
    [switch] $bChild
)

$ErrorActionPreference = "Continue"

$script:iFail = 0
$script:sLogFile = ""

function writeLog {
    param ([string] $sText)
    Write-Host $sText
    if ($script:sLogFile -ne "") {
        try { Add-Content -LiteralPath $script:sLogFile -Value $sText -Encoding UTF8 } catch { }
    }
}

function reportFail {
    param ([string] $sText)
    $script:iFail = $script:iFail + 1
    writeLog ("  FAIL  " + $sText)
}

function reportNote {
    param ([string] $sText)
    writeLog ("        " + $sText)
}

function readText {
    param ([string] $sPath)
    if (-not (Test-Path -LiteralPath $sPath)) { return $null }
    try { return (Get-Content -LiteralPath $sPath -Raw -Encoding UTF8) } catch { return $null }
}

function textLines {
    param ([string] $sText)
    if ($null -eq $sText) { return @() }
    return ($sText -split '\r?\n')
}

function literalsIn {
    param ([string] $sText)
    $lFound = New-Object System.Collections.ArrayList
    foreach ($oMatch in ([regex]'"((?:[^"\\]|\\.)*)"').Matches($sText)) {
        [void] $lFound.Add($oMatch.Groups[1].Value)
    }
    # The comma keeps this a list. Without it PowerShell unrolls a
    # one-element collection into a bare string, and indexing a string
    # hands back a single character -- which is exactly how check 4 came to
    # compare every command against the letter L.
    return ,$lFound
}

function stripLiterals {
    param ([string] $sText)
    return ($sText -replace '"(?:[^"\\]|\\.)*"', '""')
}

function normalKey {
    param ([string] $sKey)
    if ($null -eq $sKey) { return "" }
    return ($sKey -replace '\s', '').ToLower()
}

function looksLikeKey {
    param ([string] $sText)
    return ($sText -match '^(Alt\+|Control\+|Shift\+|JAWSKey\+|F\d|Insert\+)')
}

function scriptNames {
    param ([string[]] $aLines)
    $lNames = New-Object System.Collections.ArrayList
    foreach ($sLine in $aLines) {
        if ($sLine -match '^\s*Script\s+(\w+)\s*\(') { [void] $lNames.Add($Matches[1]) }
    }
    return ,$lNames
}

function functionNames {
    param ([string[]] $aLines)
    $lNames = New-Object System.Collections.ArrayList
    foreach ($sLine in $aLines) {
        if ($sLine -match '^\s*\w+\s+Function\s+(\w+)\s*\(') { [void] $lNames.Add($Matches[1]) }
    }
    return ,$lNames
}

function keyMapEntries {
    param ([string[]] $aLines)
    $lEntries = New-Object System.Collections.ArrayList
    $sSection = ""
    foreach ($sLine in $aLines) {
        $sTrim = $sLine.Trim()
        if ($sTrim -eq "" -or $sTrim.StartsWith(";")) { continue }
        if ($sTrim -match '^\[(.+)\]$') { $sSection = $Matches[1]; continue }
        if ($sTrim -match '^([^=]+)=(.*)$') {
            $sScript = $Matches[2].Trim()
            if ($sScript -eq "") { continue }
            [void] $lEntries.Add([pscustomobject] @{
                Section = $sSection
                Key     = $Matches[1].Trim()
                Script  = $sScript
            })
        }
    }
    return ,$lEntries
}

function scriptBlock {
    param ([string[]] $aLines, [string] $sName)
    $iStart = -1
    $iEnd = -1
    for ($i = 0; $i -lt $aLines.Count; $i++) {
        if ($iStart -lt 0) {
            if ($aLines[$i] -match ('^\s*Script\s+' + [regex]::Escape($sName) + '\s*\(')) { $iStart = $i }
            continue
        }
        if ($aLines[$i] -match '^\s*EndScript') { $iEnd = $i; break }
    }
    if ($iStart -lt 0) { return @() }
    if ($iEnd -lt 0) { $iEnd = $aLines.Count - 1 }
    return $aLines[$iStart..$iEnd]
}

function bigVariables {
    param ([string[]] $aLines)
    # A variable is page sized if it is built up by concatenation with itself,
    # or filled from anything that can return a whole page.
    $lBig = New-Object System.Collections.ArrayList
    for ($i = 0; $i -lt $aLines.Count; $i++) {
        if ($aLines[$i] -match '^\s*Let\s+(s\w+)\s*=\s*\1\s*\+') {
            if (-not $lBig.Contains($Matches[1])) { [void] $lBig.Add($Matches[1]) }
            continue
        }
        if (-not ($aLines[$i] -match '^\s*Let\s+(s\w+)\s*=(.*)$')) { continue }
        $sName = $Matches[1]
        $sTail = $Matches[2]
        $j = $i
        while ($j + 1 -lt $aLines.Count -and $aLines[$j + 1].Trim().StartsWith("+")) {
            $j = $j + 1
            $sTail = $sTail + $aLines[$j]
        }
        if ($sTail -match '\b(runScript|GetDocumentXML|GetElementXML|FileToString|hVCallBridge)\s*\(') {
            if (-not $lBig.Contains($sName)) { [void] $lBig.Add($sName) }
        }
    }
    return ,$lBig
}

function menuEntries {
    param ([string[]] $aMenu)
    # ONE TABLE NOW. Each row is "display<tab>script", rows separated by
    # character 7, and the dialog's row number picks the script. There is no
    # pairing to recover and no matching to verify: the correspondence is
    # inside each row. What is still worth checking is that every script named
    # in the table exists, and that the display halves are well formed.
    $lItems = New-Object System.Collections.ArrayList
    $lPairs = New-Object System.Collections.ArrayList
    $sJoined = ""
    for ($i = 0; $i -lt $aMenu.Count; $i++) {
        if (-not ($aMenu[$i] -match '^\s*Let\s+sTable\s*=\s*"')) { continue }
        $sRun = $aMenu[$i]
        $j = $i
        while ($j + 1 -lt $aMenu.Count -and $aMenu[$j + 1].Trim().StartsWith("+")) {
            $j = $j + 1
            $sRun = $sRun + $aMenu[$j]
        }
        $sJoined = $sRun
        break
    }
    foreach ($sLit in (literalsIn $sJoined)) {
        foreach ($sPart in ($sLit -split '\\7')) {
            $sRow = $sPart.Trim()
            if ($sRow.Length -lt 8) { continue }
            $lFields = $sRow -split '\\t'
            if ($lFields.Count -lt 2) {
                reportFail ("menu row has no script after the tab: " + $sRow)
                continue
            }
            [void] $lItems.Add($lFields[0].Trim())
            [void] $lPairs.Add([pscustomobject] @{
                Text = $lFields[0].Trim(); Script = $lFields[1].Trim() })
        }
    }
    return [pscustomobject] @{ Items = $lItems; Pairs = $lPairs }
}

function checkOne {
    param ($lScripts, $lKeys)
    writeLog "CHECK 1  every Script named in the .jkm exists in the .jss, and back"
    reportNote ("scripts in the .jss (" + $lScripts.Count + "): " + ($lScripts -join ", "))
    reportNote ("keys in the .jkm: " + $lKeys.Count)
    foreach ($oEntry in $lKeys) {
        if ($lScripts -notcontains $oEntry.Script) {
            reportFail ("[" + $oEntry.Section + "] " + $oEntry.Key + " names " + $oEntry.Script + ", which is not a Script in the .jss")
        }
    }
    $lBound = @($lKeys | ForEach-Object { $_.Script })
    foreach ($sName in $lScripts) {
        if ($lBound -notcontains $sName) { reportNote ($sName + " has no key, so it must be menu only") }
    }
}

function checkTwo {
    param ($oMenu, $lScripts)
    writeLog "CHECK 2  every PerformScript name in the menu exists"
    reportNote ("PerformScript calls in the menu: " + $oMenu.Pairs.Count)
    # SAY WHAT WAS FOUND. Had this been here, one look would have shown the
    # words being matched were single letters rather than command names.
    foreach ($oPair in $oMenu.Pairs) {
        reportNote ("""" + $oPair.Text + """ runs " + $oPair.Script)
    }
    foreach ($oPair in $oMenu.Pairs) {
        if ($lScripts -notcontains $oPair.Script) {
            reportFail ("the menu performs " + $oPair.Script + ", which is not a Script in the .jss")
        }
        if ($oPair.Text -eq "") {
            reportFail ("PerformScript " + $oPair.Script + " has no StringContains text before it")
        }
    }
}

function checkThree {
    param ($oMenu)
    writeLog 'CHECK 3  every menu item reads: name, sentence (Key), with no parentheses when there is no key'
    reportNote ("menu items found: " + $oMenu.Items.Count)
    foreach ($sItem in $oMenu.Items) {
        reportNote ("item: " + $sItem)
        if ($sItem -match '\([^()]*\)\s*:') { reportFail ("a colon follows the key in: " + $sItem); continue }
        if ($sItem -match '\(\s*\)') { reportFail ("empty parentheses in: " + $sItem); continue }
        if (-not ($sItem -match '^([^,]+),\s+(.+?)(\s*\(([^()]+)\))?$')) {
            reportFail ("does not read as name, sentence (Key): " + $sItem)
            continue
        }
        $sName = $Matches[1].Trim()
        $sSentence = $Matches[2].Trim()
        $sKey = $Matches[4]
        if (looksLikeKey $sSentence) {
            reportFail ("the key is bare after a comma; it belongs in parentheses at the end: " + $sItem)
            continue
        }
        if ($sName.Length -gt 40) { reportFail ("the part before the comma is not a command name: " + $sItem) }
        if ($sSentence.Length -lt 15) { reportFail ("the part after the comma is not a descriptive sentence: " + $sItem) }
        if ($null -ne $sKey -and $sKey -ne "" -and -not (looksLikeKey $sKey)) {
            reportFail ("the parenthesised part is not a key: " + $sItem)
        }
    }
}

function checkFour {
    param ($oMenu, $lKeys, [string] $sChain)
    writeLog "CHECK 4  every keyed command is on the menu, and the menu key matches the .jkm"
    $dKeyOf = @{}
    foreach ($oEntry in $lKeys) { $dKeyOf[$oEntry.Script] = $oEntry.Key }
    # Keys bound in the BROWSER'S OWN map are not in the .jkm, which records
    # them only as comments, so the binder is read for those. Without this the
    # menu was compared against an empty entry and every page-level command was
    # reported as showing a key the .jkm did not have -- correctly, for a rule
    # that had not caught up with a third place a key can live.
    if ($sChain) {
        foreach ($sLine in (textLines $sChain)) {
            foreach ($oMatch in ([regex]'"([^"=]+)=(\w+)"').Matches($sLine)) {
                if (-not $dKeyOf.ContainsKey($oMatch.Groups[2].Value)) {
                    $dKeyOf[$oMatch.Groups[2].Value] = $oMatch.Groups[1].Value
                }
            }
        }
    }
    foreach ($oPair in $oMenu.Pairs) {
        $sShown = ""
        # The row IS the pairing now, so there is no item to go looking for:
        # the display half and the script sit in the same row and cannot
        # disagree. All that is left to read off is the key in parentheses.
        if ($oPair.Text -match '\(([^()]+)\)\s*$') { $sShown = $Matches[1] }
        $sReal = ""
        if ($dKeyOf.ContainsKey($oPair.Script)) { $sReal = $dKeyOf[$oPair.Script] }
        if ((normalKey $sShown) -eq (normalKey $sReal)) { continue }
        if ($sShown -eq "") {
            reportFail ($oPair.Script + " is bound to " + $sReal + " but its menu item shows no key in parentheses")
        } elseif ($sReal -eq "") {
            reportFail ($oPair.Script + " has no key in the .jkm but the menu shows " + $sShown)
        } else {
            reportFail ($oPair.Script + ": the menu shows " + $sShown + " but the .jkm binds " + $sReal)
        }
    }
    $lOnMenu = @($oMenu.Pairs | ForEach-Object { $_.Script })
    foreach ($oEntry in $lKeys) {
        # The menu itself is the one command that does not list itself.
        if ($oEntry.Script -eq "hVShowHomerViewMenu") { continue }
        if ($lOnMenu -notcontains $oEntry.Script) {
            reportFail ($oEntry.Script + " is bound to " + $oEntry.Key + " but is not on the Alternate Menu")
        }
    }
}

function checkFive {
    param ([string] $sJsd, $lScripts)
    writeLog "CHECK 5  every .jsd entry names a real script, and every script has an entry"
    if ($null -eq $sJsd) { reportFail "jaws\HomerView.jsd could not be read"; return }
    $lDoc = New-Object System.Collections.ArrayList
    foreach ($sLine in (textLines $sJsd)) {
        $sTrim = $sLine.Trim()
        if ($sTrim -eq "" -or $sTrim.StartsWith(";")) { continue }
        if ($sTrim -match '^(\w+?)(_Synopsis|_Description)?=') {
            if (-not $lDoc.Contains($Matches[1])) { [void] $lDoc.Add($Matches[1]) }
        }
    }
    reportNote ("documented in the .jsd (" + $lDoc.Count + "): " + ($lDoc -join ", "))
    foreach ($sName in $lDoc) {
        if ($lScripts -notcontains $sName) { reportFail ("the .jsd documents " + $sName + ", which is not a Script in the .jss") }
    }
    foreach ($sName in $lScripts) {
        if ($lDoc -notcontains $sName) { reportFail ($sName + " has no .jsd entry, so the Key Describer says nothing about it") }
    }
}

function checkSix {
    param ([string[]] $aLines)
    writeLog "CHECK 6  no lone backslash inside a string literal"
    reportNote 'a backslash may only precede one of \ " r n t 7 or an apostrophe'
    $iLine = 0
    foreach ($sLine in $aLines) {
        $iLine = $iLine + 1
        if ($sLine.Trim().StartsWith(";")) { continue }
        foreach ($sLit in (literalsIn $sLine)) {
            $i = 0
            while ($i -lt $sLit.Length) {
                if (([string] $sLit[$i]) -ne '\') { $i = $i + 1; continue }
                if ($i + 1 -ge $sLit.Length) {
                    reportFail ("line " + $iLine + ": a literal ends in a backslash")
                    break
                }
                $sNext = [string] $sLit[$i + 1]
                if (-not ('\"rnt7''').Contains($sNext)) {
                    reportFail ("line " + $iLine + ": lone backslash before " + $sNext + " in: " + $sLit)
                }
                $i = $i + 2
            }
        }
    }
}

function checkSeven {
    param ([string[]] $aLines)
    writeLog "CHECK 7  no C-style comment"
    $iLine = 0
    foreach ($sLine in $aLines) {
        $iLine = $iLine + 1
        $sStripped = stripLiterals $sLine
        if ($sStripped -match '/\*' -or $sStripped -match '\*/' -or $sStripped -match '//') {
            reportFail ("line " + $iLine + ": C-style comment: " + $sLine.Trim())
        }
    }
}

function checkEight {
    param ([string[]] $aLines)
    writeLog "CHECK 8  no Null, no Let without an assignment, every declared name carries its own type"
    $iLine = 0
    $bInVar = $false
    foreach ($sLine in $aLines) {
        $iLine = $iLine + 1
        $sTrim = (stripLiterals $sLine).Trim()
        if ($sTrim.StartsWith(";")) { continue }
        if ($sTrim -match '(^|\W)Null(\W|$)') {
            reportFail ("line " + $iLine + ": there is no Null in JSL: " + $sLine.Trim())
        }
        if ($sTrim -match '^Let\b' -and $sTrim -notmatch '=') {
            reportFail ("line " + $iLine + ": Let with no assignment; a bare method call needs no Let: " + $sLine.Trim())
        }
        if ($sTrim -match '^(Var|Globals|Const)\b(.*)$') {
            $bInVar = $true
            $sTrim = $Matches[2].Trim()
        } elseif ($sTrim -match '^(Script|EndScript|EndFunction|Include|Import|Prototype)\b' -or $sTrim -match '\bFunction\b') {
            $bInVar = $false
            continue
        }
        if (-not $bInVar -or $sTrim -eq "") { continue }
        $bMore = $sTrim.EndsWith(",")
        foreach ($sPart in ($sTrim.TrimEnd(",") -split ",")) {
            $sDecl = $sPart.Trim()
            if ($sDecl -eq "" -or $sDecl.Contains("=")) { continue }
            if (-not ($sDecl -match '^\w+\s+\w+$')) {
                reportFail ("line " + $iLine + ": " + $sDecl + " has no type of its own; JSL reads the second name as a type")
                $bInVar = $false
            }
        }
        if (-not $bMore) { $bInVar = $false }
    }
}

function checkTen {
    param ([string[]] $aLines, [string] $sCs)
    writeLog "CHECK 10  every helper command has a case, and every dispatched method is defined"
    if ($null -eq $sCs) { reportFail "HomerView.cs could not be read"; return }
    $lAsked = New-Object System.Collections.ArrayList
    foreach ($sLine in $aLines) {
        foreach ($oMatch in ([regex]'hVCallBridge\s*\(\s*"([^"]+)"').Matches($sLine)) {
            if (-not $lAsked.Contains($oMatch.Groups[1].Value)) { [void] $lAsked.Add($oMatch.Groups[1].Value) }
        }
    }
    $lCases = New-Object System.Collections.ArrayList
    foreach ($oMatch in ([regex]'case\s+"([^"]+)"\s*:').Matches($sCs)) {
        if (-not $lCases.Contains($oMatch.Groups[1].Value)) { [void] $lCases.Add($oMatch.Groups[1].Value) }
    }
    reportNote ("commands the .jss asks for: " + ($lAsked -join ", "))
    reportNote ("cases in HomerView.cs: " + ($lCases -join ", "))
    reportNote "the dispatch lowercases the command, so these are compared without case"
    $lLower = @($lCases | ForEach-Object { $_.ToLower() })
    foreach ($sName in $lAsked) {
        if ($lLower -notcontains $sName.ToLower()) {
            reportFail ("the .jss calls helper command " + $sName + ", which has no case in HomerView.cs")
        }
    }
    $lDefined = New-Object System.Collections.ArrayList
    foreach ($oMatch in ([regex]'(?m)^\s*(?:public|private|internal|static|\s)+[\w<>\[\],]+\s+(\w+)\s*\(').Matches($sCs)) {
        if (-not $lDefined.Contains($oMatch.Groups[1].Value)) { [void] $lDefined.Add($oMatch.Groups[1].Value) }
    }
    reportNote ("methods defined in HomerView.cs: " + $lDefined.Count)
    foreach ($oMatch in ([regex]'sResult\s*=\s*(\w+)\s*\(').Matches($sCs)) {
        $sCalled = $oMatch.Groups[1].Value
        if ($lDefined -notcontains $sCalled) {
            reportFail ("the C# dispatch calls " + $sCalled + "(), which is not defined in HomerView.cs")
        }
    }
}

function checkEleven {
    param ([string[]] $aLines)
    writeLog "CHECK 11  no page-sized argument reaches a command line"
    reportNote "Windows takes about 32,000 characters; beyond that the program is never started at all"
    # hVCallBridge is the one door to the helper, so the protection belongs there
    # rather than at every call site. What this checks is that the door is still
    # shut: that hVCallBridge writes the argument to a file and passes @path. A
    # check that policed each caller instead would have to be argued with every
    # time a caller was added, and would pass the day someone bypassed it.
    $bRouted = $false
    $aBridge = @()
    $iStart = -1
    for ($i = 0; $i -lt $aLines.Count; $i++) {
        if ($iStart -lt 0) {
            if ($aLines[$i] -match '^\s*\w+\s+Function\s+hVCallBridge\s*\(') { $iStart = $i }
            continue
        }
        if ($aLines[$i] -match '^\s*EndFunction') { $aBridge = $aLines[$iStart..$i]; break }
    }
    if ($aBridge.Count -eq 0) {
        reportFail "hVCallBridge was not found in the .jss"
    } else {
        foreach ($sLine in $aBridge) {
            if ($sLine -match 'CreateTextFile' -and -not ($sLine.Trim().StartsWith(";"))) { $bRouted = $true }
        }
        if ($bRouted) {
            reportNote "hVCallBridge writes the argument to a file and passes its path, so no caller can overflow"
        } else {
            reportFail "hVCallBridge passes its argument straight to the command line; it must write a file and pass @path"
        }
    }
    # shellRun goes to a command line directly, with no such door.
    $lBig = bigVariables $aLines
    reportNote ("variables that can hold a whole page: " + ($lBig -join ", "))
    $iLine = 0
    foreach ($sLine in $aLines) {
        $iLine = $iLine + 1
        foreach ($oMatch in ([regex]'shellRun\s*\(([^)]*)').Matches($sLine)) {
            $sArgs = $oMatch.Groups[1].Value
            foreach ($sName in $lBig) {
                if ($sArgs -match ('(^|\W)' + [regex]::Escape($sName) + '(\W|$)')) {
                    reportFail ("line " + $iLine + ": " + $sName + " can hold a whole page and goes straight to a command line through shellRun")
                }
            }
            if ($sArgs -match 'GetDocumentXML|GetElementXML|runScript') {
                reportFail ("line " + $iLine + ": a page-sized call goes straight to a command line through shellRun")
            }
        }
    }
}
function checkTwelve {
    param ([string] $sCs)
    writeLog "CHECK 12  the entry point still carries STAThread, and no attribute is orphaned"
    reportNote "OLE needs a single threaded apartment; an attribute on any other method does not give it one"
    if ($null -eq $sCs) { reportFail "HomerView.cs could not be read"; return }
    $aCs = textLines $sCs
    # An attribute must be immediately followed by the declaration it belongs
    # to. Inserting a method between the two moves the attribute onto the new
    # method, and it still compiles: that is how Main lost STAThread and the
    # clipboard began refusing every call.
    for ($i = 0; $i -lt $aCs.Count; $i++) {
        if (-not ($aCs[$i] -match '^\s*\[\s*(\w+)\s*\]\s*$')) { continue }
        $sAttribute = $Matches[1]
        $sNext = ""
        if ($i + 1 -lt $aCs.Count) { $sNext = $aCs[$i + 1].Trim() }
        if ($sNext -match '^(///|//|/\*)' -or $sNext -eq "") {
            reportFail ("line " + ($i + 1) + ": [" + $sAttribute + "] is followed by a comment or a blank line, so it attaches to whatever comes after that")
            continue
        }
        reportNote ("[" + $sAttribute + "] is attached to: " + $sNext)
        if ($sAttribute -eq "STAThread" -and $sNext -notmatch '\bMain\s*\(') {
            reportFail ("[STAThread] is on " + $sNext + " rather than on Main")
        }
    }
    if ($sCs -notmatch '(?m)^\s*\[STAThread\]') {
        reportFail "HomerView.cs has no [STAThread] at all; the clipboard commands cannot work"
    }
}

function checkThirteen {
    param ([string[]] $aLines, [string] $sCs)
    writeLog "CHECK 13  the two sides agree on how the answer file is written and read"
    reportNote "the helper writes the answer and the scripts read it; a mismatch shows up as an unparsable answer"
    if ($null -eq $sCs) { reportFail "HomerView.cs could not be read"; return }
    # The helper must write UTF-16, because that is the only encoding the
    # FileSystemObject can be asked to read. Written as UTF-8 with a byte order
    # mark, the mark arrived as three visible characters in front of the XML.
    # Scoped to WriteResult. MainContent.htm is deliberately UTF-8 with a mark,
    # because a browser reads that one, so asking the question of the whole file
    # would fail on a correct line.
    $sWrite = ""
    $aCs2 = textLines $sCs
    for ($i = 0; $i -lt $aCs2.Count; $i++) {
        if (-not ($aCs2[$i] -match 'void\s+WriteResult\s*\(')) { continue }
        $iEnd = [Math]::Min($i + 30, $aCs2.Count - 1)
        $sWrite = ($aCs2[$i..$iEnd] -join "`n")
        break
    }
    if ($sWrite -eq "") { reportFail "WriteResult was not found in HomerView.cs" }
    $bWritesUnicode = ($sWrite -match 'new UnicodeEncoding') -and ($sWrite -notmatch 'new UTF8Encoding')
    if ($bWritesUnicode) {
        reportNote "the helper writes the answer file as UTF-16"
    } else {
        reportFail "WriteResult does not write UTF-16; the scripts cannot read what it produces"
    }
    # And the scripts must ask for Unicode when they open it.
    $bReadsUnicode = $false
    foreach ($sLine in $aLines) {
        if ($sLine -match 'OpenTextFile\s*\(\s*c_sAnswerPath\s*,\s*1\s*,\s*False\s*,\s*-1\s*\)') { $bReadsUnicode = $true }
    }
    if ($bReadsUnicode) {
        reportNote "the scripts open the answer file as Unicode"
    } else {
        reportFail "the .jss opens the answer file without asking for Unicode, so a byte order mark will reach the parser"
    }
    # An argument crossing from the scripting language carries a NUL, and a NUL
    # inside a JavaScript payload is a syntax error the browser cannot locate.
    if ($sCs -match 'Replace\("\\0", ""\)') {
        reportNote "the helper strips NUL characters from the argument it is handed"
    } else {
        reportFail "ReadArgument does not strip NUL characters; a JavaScript payload will fail to parse"
    }
}

function checkSixteen {
    param ($oMenu)
    writeLog "CHECK 16  no menu command name contains another"
    reportNote "the menu dispatches by matching words, so a name inside another name runs the wrong command"
    # "Check Accessibility with IBM" contained "Check Accessibility", and the
    # axe branch came first, so the IBM item silently ran axe. Reordering the
    # branches would have fixed that one collision and left the next one to be
    # found the same way; names that cannot contain each other cannot collide
    # whatever order the branches are in.
    $lNames = New-Object System.Collections.ArrayList
    foreach ($sItem in $oMenu.Items) {
        if ($sItem -match '^([^,]+),') { [void] $lNames.Add($Matches[1].Trim()) }
    }
    reportNote ("command names on the menu: " + $lNames.Count)
    foreach ($sOne in $lNames) {
        foreach ($sOther in $lNames) {
            if ($sOne -eq $sOther) { continue }
            if ($sOther.Contains($sOne)) {
                reportFail ("""" + $sOne + """ is inside """ + $sOther + """, so whichever branch comes first will answer for both")
            }
        }
    }
    # The dispatch is by row number now, so a name inside another name can no
    # longer run the wrong command. It is still kept as a check, because two
    # commands whose names contain one another are confusing to hear read out
    # even when the machinery is sound.
}

function checkFourteen {
    param ([string[]] $aLines, [string] $sChain, $lKeys)
    writeLog "CHECK 14  every place a key is written says the same thing"
    reportNote "keys live in three files: jaws\HomerView.jkm, chainJawsScripts.ps1, and the Hotkey Summary"
    reportNote "chainJawsScripts is the one that actually binds; the .jkm is never read by JAWS at all"
    if ($null -eq $sChain) {
        reportFail "chainJawsScripts.ps1 could not be read, so the bindings could not be checked"
        return
    }
    # The .jkm is kept as the readable home for the key list, but JAWS would
    # need it named after the executable, so nothing loads it. What binds the
    # keys is the block chainJawsScripts writes into the user default.jkm. If
    # those two drift, every check passes and no key works.
    # Section as well as key. They drifted on exactly this: the pair sat in
    # [Common Keys] in the .jkm and in the virtual list in the binder, which
    # is the difference between a key taken on a web page and a key taken from
    # every program on the machine.
    $dChain = @{}
    $dChainSection = @{}
    $sSection = ""
    foreach ($sLine in (textLines $sChain)) {
        if ($sLine -match '\$lCommonKeys\s*=') { $sSection = "Common Keys" }
        if ($sLine -match '\$lVirtualKeys\s*=') { $sSection = "Virtual Keys" }
        # A THIRD HOME FOR A KEY: the browser's own map, msedge.jkm, which
        # chainJawsScripts writes so that a page-level command works in any
        # cursor mode while Edge is in front, and in no other program. The
        # project .jkm records those as comments, so the binder is the
        # authority for them and the .jkm cannot be asked about them.
        if ($sLine -match '\$lBrowserKeys\s*=') { $sSection = "Browser Keys" }
        foreach ($oMatch in ([regex]'"([^"=]+)=(\w+)"').Matches($sLine)) {
            $dChain[$oMatch.Groups[2].Value] = $oMatch.Groups[1].Value
            $dChainSection[$oMatch.Groups[2].Value] = $sSection
        }
    }
    reportNote ("chainJawsScripts binds " + $dChain.Count + " keys")
    $dMap = @{}
    $dMapSection = @{}
    foreach ($oEntry in $lKeys) {
        $dMap[$oEntry.Script] = $oEntry.Key
        $dMapSection[$oEntry.Script] = $oEntry.Section
    }
    foreach ($sScript in $dMap.Keys) {
        if (-not $dChain.ContainsKey($sScript)) {
            reportFail ($sScript + " is in the .jkm on " + $dMap[$sScript] + " but chainJawsScripts binds nothing for it")
        } elseif ((normalKey $dChain[$sScript]) -ne (normalKey $dMap[$sScript]) -and
                  $dChainSection[$sScript] -ne "Browser Keys") {
            # A BROWSER KEY MAY ALSO BE A VIRTUAL KEY, on purpose: while the
            # application key map is unproven the same key stays in
            # [Virtual Keys] as a fallback, so a wrongly-named browser map
            # costs nothing.
            reportFail ($sScript + ": the .jkm says " + $dMap[$sScript] + " but chainJawsScripts binds " + $dChain[$sScript])
        } elseif ($dChainSection[$sScript] -ne $dMapSection[$sScript]) {
            reportFail ($sScript + " is in [" + $dMapSection[$sScript] + "] in the .jkm but chainJawsScripts binds it in [" + $dChainSection[$sScript] + "]")
        }
    }
    $iBrowser = 0
    foreach ($sScript in $dChain.Keys) {
        if ($dChainSection[$sScript] -eq "Browser Keys") { $iBrowser += 1; continue }
        if (-not $dMap.ContainsKey($sScript)) {
            reportFail ("chainJawsScripts binds " + $dChain[$sScript] + " to " + $sScript + ", which is not in the .jkm")
        }
    }
    if ($iBrowser -gt 0) {
        reportNote ($iBrowser.ToString() + " command(s) are bound in the browser's own key map")
    }
    # And the summary the user reads, which is a third copy of the same list.
    $aSummary = scriptBlock $aLines "hVHotKeyHelp"
    if ($aSummary.Count -eq 0) { reportFail "hVHotKeyHelp was not found"; return }
    $lShown = New-Object System.Collections.ArrayList
    foreach ($sLine in $aSummary) {
        foreach ($sLit in (literalsIn $sLine)) {
            if ($sLit -match '^\s{2}((?:Alt|Control|Shift|JAWSKey|F\d)\S*)\s') {
                [void] $lShown.Add($Matches[1])
            }
        }
    }
    reportNote ("the Hotkey Summary lists " + $lShown.Count + " keys: " + ($lShown -join ", "))
    foreach ($sKey in $lShown) {
        $bKnown = $false
        foreach ($sScript in $dChain.Keys) {
            if ((normalKey $dChain[$sScript]) -eq (normalKey $sKey)) { $bKnown = $true }
        }
        if (-not $bKnown) {
            reportFail ("the Hotkey Summary tells the user about " + $sKey + ", which is bound to nothing")
        }
    }
    foreach ($sScript in $dChain.Keys) {
        $bShown = $false
        foreach ($sKey in $lShown) {
            if ((normalKey $dChain[$sScript]) -eq (normalKey $sKey)) { $bShown = $true }
        }
        if (-not $bShown) {
            reportFail ($sScript + " is bound to " + $dChain[$sScript] + " but the Hotkey Summary never mentions it")
        }
    }
}

function checkFifteen {
    param ([string[]] $aLines, $lScripts, $lFuncs)
    writeLog "CHECK 15  every link in the Hotkey Summary names a function that exists"
    reportNote "UserBufferAddLink names its target as TEXT, so the compiler cannot check it and a wrong name simply does nothing"
    $lTargets = New-Object System.Collections.ArrayList
    $lAsked = New-Object System.Collections.ArrayList
    $iLine = 0
    foreach ($sLine in $aLines) {
        $iLine = $iLine + 1
        if ($sLine -notmatch 'UserBufferAddLink') { continue }
        # A CALL CAN SPAN LINES, and the tab list's does. Reading only the line
        # the name appears on found no target at all and said nothing about it,
        # which is the same silence this check exists to prevent. The call is
        # gathered until its brackets balance.
        $sCall = $sLine
        $iDepth = 0
        foreach ($cCharacter in $sCall.ToCharArray()) {
            if ($cCharacter -eq "(") { $iDepth = $iDepth + 1 }
            if ($cCharacter -eq ")") { $iDepth = $iDepth - 1 }
        }
        $iNext = $iLine
        while ($iDepth -gt 0 -and $iNext -lt $aLines.Count) {
            $sCall = $sCall + $aLines[$iNext]
            foreach ($cCharacter in $aLines[$iNext].ToCharArray()) {
                if ($cCharacter -eq "(") { $iDepth = $iDepth + 1 }
                if ($cCharacter -eq ")") { $iDepth = $iDepth - 1 }
            }
            $iNext = $iNext + 1
        }
        $sLine = $sCall
        # THE TARGET IS NOT ALWAYS ONE LITERAL. A link whose target is built by
        # concatenation -- "homerViewTab (\"" + sId + "\")" -- was invisible to
        # the pattern that expected a whole call in one string, so the tab list's
        # links went unchecked the moment they were written. Every literal in the
        # line is examined instead, and one that begins with an identifier and an
        # opening bracket names a function.
        foreach ($sLit in (literalsIn $sLine)) {
            if ($sLit -match '^(\w+)\s*\(') {
                if (-not $lTargets.Contains($Matches[1])) { [void] $lTargets.Add($Matches[1]) }
            }
            if ($sLit -match '^\w+\s*\(\\"(\w+)\\"\)$') {
                [void] $lAsked.Add($Matches[1])
            }
        }
    }
    reportNote ("link targets: " + ($lTargets -join ", "))
    reportNote ("commands offered as links: " + $lAsked.Count)
    if ($lAsked.Count -eq 0) { reportFail "no links were found in the Hotkey Summary"; return }
    foreach ($sName in $lTargets) {
        if ($lFuncs -notcontains $sName) {
            reportFail ("a link calls " + $sName + "(), which is not a Function in the .jss")
        }
    }
    # The link dispatcher is one PerformScriptByName call now, so there is no
    # branch to be missing. What still cannot be checked by the compiler is
    # whether the name names a real script, and that is the whole risk: the
    # name is a string, so a typo is silent.
    foreach ($sName in $lAsked) {
        if ($lScripts -notcontains $sName) {
            reportFail ("a link asks for " + $sName + ", which is not a Script in the .jss")
        }
    }
}

# --- driver ---

if ($sRoot -eq "") { $sRoot = Split-Path -Parent $MyInvocation.MyCommand.Path }
# Run on its own it keeps its own log beside itself. Run as a child of
# checkJawsScripts it writes to the console only, and the parent puts every
# line into its own log -- so there is ONE owner of the file and one copy of
# each line. The first version of this handed the child a log path instead;
# the child dutifully wrote its findings to checkJawsScripts.log while the
# parent said "they are listed above" into a different file entirely, and the
# build reported a failure nobody could read.
if ($bChild) {
    $script:sLogFile = ""
} else {
    $script:sLogFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "checkHomerViewQuality.log"
    try { Remove-Item -LiteralPath $script:sLogFile -ErrorAction SilentlyContinue } catch { }
}

writeLog ("checkHomerViewQuality, " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
writeLog ("script:            " + $MyInvocation.MyCommand.Path)
writeLog ("root:              " + $sRoot)
writeLog ("log:               " + $script:sLogFile)
writeLog ("PowerShell:        " + $PSVersionTable.PSVersion.ToString())
writeLog ("edition:           " + $PSVersionTable.PSEdition)
writeLog ("Windows:           " + [System.Environment]::OSVersion.VersionString)
writeLog ("64 bit process:    " + [System.Environment]::Is64BitProcess)
writeLog ("culture:           " + (Get-Culture).Name)
writeLog ("working directory: " + (Get-Location).Path)
writeLog ("command line:      " + ([string] $MyInvocation.Line).Trim())
writeLog ""

$sPathJss = Join-Path $sRoot "jaws\HomerView.jss"
$sPathJkm = Join-Path $sRoot "jaws\HomerView.jkm"
$sPathJsd = Join-Path $sRoot "jaws\HomerView.jsd"
$sPathCs  = Join-Path $sRoot "HomerView.cs"
$sPathChain = Join-Path $sRoot "chainJawsScripts.ps1"

foreach ($sPath in @($sPathJss, $sPathJkm, $sPathJsd, $sPathCs, $sPathChain)) {
    if (Test-Path -LiteralPath $sPath) {
        writeLog ("found   " + $sPath + ", " + (Get-Item -LiteralPath $sPath).Length + " bytes")
    } else {
        writeLog ("MISSING " + $sPath)
    }
}
writeLog ""

$sJss = readText $sPathJss
$sJkm = readText $sPathJkm
$sJsd = readText $sPathJsd
$sCs  = readText $sPathCs
$sChain = readText (Join-Path $sRoot "chainJawsScripts.ps1")

if ($null -eq $sJss) {
    writeLog "jaws\HomerView.jss could not be read, so nothing further can be checked."
    writeLog "Pass the project folder as -sRoot if it is not the folder holding this script."
    exit 1
}

$aJss     = textLines $sJss
$lScripts = scriptNames $aJss
$lFuncs   = functionNames $aJss
$lKeys    = keyMapEntries (textLines $sJkm)
$aMenuBlk = scriptBlock $aJss "hVShowHomerViewMenu"
$oMenu    = menuEntries $aMenuBlk

writeLog ("functions in the .jss (" + $lFuncs.Count + "): " + ($lFuncs -join ", "))
if ($aMenuBlk.Count -eq 0) { reportFail "hVShowHomerViewMenu was not found in the .jss, so checks 2, 3 and 4 have nothing to read" }
writeLog ""

$lChecks = @(
    { checkOne    $lScripts $lKeys },
    { checkTwo    $oMenu $lScripts },
    { checkThree  $oMenu },
    { checkFour   $oMenu $lKeys $sChain },
    { checkFive   $sJsd $lScripts },
    { checkSix    $aJss },
    { checkSeven  $aJss },
    { checkEight  $aJss },
    { checkTen      $aJss $sCs },
    { checkEleven   $aJss },
    { checkTwelve   $sCs },
    { checkThirteen $aJss $sCs },
    { checkFourteen $aJss $sChain $lKeys },
    { checkFifteen  $aJss $lScripts $lFuncs },
    { checkSixteen  $oMenu })

foreach ($oCheck in $lChecks) {
    $iBefore = $script:iFail
    try { & $oCheck } catch { reportFail ("the check itself failed: " + $_.Exception.Message) }
    if ($script:iFail -eq $iBefore) { writeLog "        passed" }
    writeLog ""
}

writeLog ("checkHomerViewQuality finished with " + $script:iFail + " problem(s).")
if ($script:iFail -gt 0) { exit 1 }
exit 0

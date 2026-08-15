; HomerView.jss -- HomerView scripts for Microsoft Edge
;
; HomerView gives a screen reader user what the browser knows and the reading
; order never carries. The NVDA version does this from inside NVDA, in Python.
; JAWS scripting cannot open a WebSocket, which is where every Chrome DevTools
; command that reads or acts on a page travels, so this version asks
; HomerViewBridge.exe to do that part and reads back what it said.
;
; The bridge is run through WScript.Shell, which waits for it to finish, and
; its answer is read with Scripting.FileSystemObject. Both of those are
; registered on every Windows machine already, so nothing of HomerView's has to
; be registered at all.
;
; What is NOT here matters as much as what is. JAWS already moves to the main
; region with Q, says the web address with JAWSKey+A, lists headings, links and
; form fields with JAWSKey+F5, F6 and F7, and finds with Control+F. HomerView
; on NVDA has its own versions of those only because NVDA lacks them. Taking a
; key a JAWS user already knows and giving it something almost the same would
; be worse than not having it.
;
; So this adds Shift+Q, for the main content of a page that declares none, and
; the commands nothing else has.

Include "hjconst.jsh"

Const
    sBridgeName = "HomerViewBridge.exe",
    sFileSystemProgId = "Scripting.FileSystemObject",
    sHomerFolder = "HomerView",
    sShellProgId = "WScript.Shell"

Globals
    string gsLastResult

; Runs the bridge with one command and returns what it wrote.
;
; Hidden and waited for, so the script has the answer on the next line. A
; screen reader command is a question somebody is waiting on, so there is
; nothing to gain from doing it in the background.


; Where the bridge lives. Beside the JAWS scripts first, since that is where
; the installer puts it, then the program folder.
; Where the bridge lives. Beside the JAWS scripts first, since that is where
; the installer puts it, then the program folder.
Function bridgePath () returns string
Var
    object oFileSystem,
    string sCandidate
Let oFileSystem = CreateObjectEx (sFileSystemProgId, False)
If oFileSystem == Null Then
    Return ""
EndIf
Let sCandidate = GetJawsSettingsPath () + sBridgeName
If oFileSystem.FileExists (sCandidate) Then
    Let oFileSystem = Null
    Return sCandidate
EndIf
Let sCandidate = "C:\\Program Files\\HomerView\\" + sBridgeName
If oFileSystem.FileExists (sCandidate) Then
    Let oFileSystem = Null
    Return sCandidate
EndIf
Let oFileSystem = Null
Return ""
EndFunction

Function callBridge (string sCommand, string sArgument) returns string
Var
    handle hFile,
    object oFileSystem, oShell,
    string sBridge, sOutput, sResult
Let sBridge = bridgePath ()
If sBridge == "" Then
    SayMessage (OT_ERROR, "HomerViewBridge.exe was not found. HomerView is not installed properly.")
    Return ""
EndIf
Let sOutput = outputPath ()
Let oShell = CreateObjectEx (sShellProgId, False)
If oShell == Null Then
    SayMessage (OT_ERROR, "Windows Script Host is not available.")
    Return ""
EndIf
; Nought hides the window; the one waits for it to finish.
Let oShell.Run ("\"" + sBridge + "\" " + sCommand + " \"" + sOutput + "\" \"" + sArgument + "\"", 0, 1)
Let oShell = Null
Let oFileSystem = CreateObjectEx (sFileSystemProgId, False)
If oFileSystem == Null Then
    Return ""
EndIf
If oFileSystem.FileExists (sOutput) == False Then
    SayMessage (OT_ERROR, "HomerView did not answer.")
    Let oFileSystem = Null
    Return ""
EndIf
Let hFile = oFileSystem.OpenTextFile (sOutput, 1)
Let sResult = hFile.ReadAll ()
Let hFile.Close ()
Let oFileSystem = Null
Let gsLastResult = sResult
Return sResult
EndFunction


; Checks the page for accessibility problems. Alt+JAWSKey+A.
; Checks the page for accessibility problems. Alt+JAWSKey+A.
Script checkAccessibility ()
SayMessage (OT_STATUS, "Checking the page")
Var string sResult
Let sResult = runScript (
    "(async () => {"
    + "if (typeof axe === 'undefined') {"
    + "  const el = document.createElement('script');"
    + "  el.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js';"
    + "  document.head.appendChild(el);"
    + "  await new Promise(r => { el.onload = r; setTimeout(r, 8000); });"
    + "}"
    + "if (typeof axe === 'undefined') return 'The testing engine could not be loaded.';"
    + "const d = await axe.run();"
    + "let n = 0; for (const v of d.violations) n += v.nodes.length;"
    + "return d.violations.length + ' kinds of problem, ' + n + ' places.';"
    + "})()")
If sResult != "" Then
    SayMessage (OT_MESSAGE, sResult)
EndIf
EndScript


; Says what is at the link under the cursor, without going there. Alt+L.
; Says what is at the link under the cursor, without going there. Alt+L.
Script describeLinkTarget ()
Var string sResult, sUrl
Let sUrl = GetObjectAttributes ()
Let sUrl = getLinkUrl ()
If sUrl == "" Then
    SayMessage (OT_ERROR, "No link here")
    Return
EndIf
SayMessage (OT_STATUS, "Asking where that goes")
Let sResult = runScript (
    "(async () => { try {"
    + "const r = await fetch(" + jsQuote (sUrl) + ", {method:'GET'});"
    + "const t = (r.headers.get('content-type') || '').split(';')[0];"
    + "const n = r.headers.get('content-length');"
    + "let s = r.ok ? 'A ' + (t || 'page') : 'That link is broken: ' + r.status;"
    + "if (n) s += ', about ' + Math.round(n/1024) + ' kilobytes';"
    + "if (new URL(r.url).host !== new URL(" + jsQuote (sUrl) + ").host)"
    + "  s += '. It ends up at ' + new URL(r.url).host;"
    + "return s;"
    + "} catch (e) { return 'The link could not be reached.'; } })()")
If sResult != "" Then
    SayMessage (OT_MESSAGE, sResult)
EndIf
EndScript


; Describes how the page is laid out, including what is visible but unspoken.
; Alt+JAWSKey+E, and Y in the virtual cursor.
; Describes how the page is laid out, including what is visible but unspoken.
; Alt+JAWSKey+E, and Y in the virtual cursor.
Script explorePage ()
SayMessage (OT_STATUS, "Looking at the page")
Var string sResult
Let sResult = runScript (
    "(() => {"
    + "const q = s => document.querySelectorAll(s).length;"
    + "const l = [];"
    + "l.push(q('h1,h2,h3,h4,h5,h6') + ' headings');"
    + "l.push(q('a[href]') + ' links');"
    + "l.push(q('input,select,textarea,button') + ' form controls');"
    + "l.push(q('table') + ' tables');"
    + "l.push(q('img') + ' images');"
    + "const m = document.querySelector('main,[role=main]');"
    + "l.push(m ? 'The page says where its main content is.'"
    + "         : 'The page does not say where its main content is; press Shift+Q.');"
    + "const lOver = [];"
    + "for (const el of document.querySelectorAll('div,section,aside,dialog')) {"
    + "  const st = getComputedStyle(el);"
    + "  if (st.display === 'none' || st.visibility === 'hidden') continue;"
    + "  if (st.position !== 'fixed' && st.position !== 'sticky') continue;"
    + "  const b = el.getBoundingClientRect();"
    + "  if (b.width < 120 || b.height < 30) continue;"
    + "  const s = (el.innerText || '').trim().slice(0, 60);"
    + "  if (s) lOver.push(s);"
    + "}"
    + "if (lOver.length) l.push(lOver.length + ' things are pinned over the page: ' + lOver.join('; '));"
    + "const dl = document.querySelector('dialog[open],[role=dialog],[role=alertdialog]');"
    + "if (dl) l.push('A dialog is open and may be taking your keystrokes.');"
    + "return l.join('. ');"
    + "})()")
If sResult != "" Then
    SayMessage (OT_MESSAGE, sResult)
EndIf
EndScript


; Extracts the readable part of the page into a tab of its own. Shift+F9,
; beside Edge's own reading view on F9.
; Extracts the readable part of the page into a tab of its own. Shift+F9,
; beside Edge's own reading view on F9.
Script extractMainContent ()
SayMessage (OT_STATUS, "Extracting the main content")
Var string sResult
Let sResult = runScript (
    "(() => {"
    + "let elBest = null, nBest = 0;"
    + "for (const el of document.querySelectorAll('article,section,div,td')) {"
    + "  const s = (el.innerText || '').trim();"
    + "  if (s.length < 200) continue;"
    + "  let iLink = 0;"
    + "  for (const a of el.querySelectorAll('a')) iLink += (a.innerText || '').length;"
    + "  const nShare = iLink / s.length;"
    + "  if (nShare > 0.5) continue;"
    + "  let n = s.length * (1 - nShare);"
    + "  if (el.tagName === 'ARTICLE') n *= 1.5;"
    + "  if (n > nBest) { nBest = n; elBest = el; }"
    + "}"
    + "if (!elBest) return 'No main content was found.';"
    + "const w = window.open('', '_blank');"
    + "w.document.write('<!doctype html><html lang=\\\"en\\\"><head><meta charset=\\\"utf-8\\\">'"
    + "  + '<title>' + document.title + '</title></head><body><main>'"
    + "  + elBest.innerHTML + '</main></body></html>');"
    + "w.document.close();"
    + "return 'Extracted, about ' + Math.round(elBest.innerText.length / 5) + ' words.';"
    + "})()")
If sResult != "" Then
    SayMessage (OT_MESSAGE, sResult)
EndIf
EndScript


; The address of the link under the virtual cursor, taken from JAWS rather
; than from the browser, because JAWS already knows it.
; The address of the link under the virtual cursor, taken from JAWS rather
; than from the browser, because JAWS already knows it.
Function getLinkUrl () returns string
Var string sUrl
Let sUrl = GetLinkURL ()
Return sUrl
EndFunction


; Pulls one string value out of the bridge's answer.
;
; A whole JSON parser is not needed. Every answer HomerView asks for is a
; single value, and finding it by name is enough. Anything more elaborate would
; be work for its own sake.
; Pulls one string value out of the bridge's answer.
;
; A whole JSON parser is not needed. Every answer HomerView asks for is a
; single value, and finding it by name is enough. Anything more elaborate would
; be work for its own sake.
Function jsonValue (string sJson, string sName) returns string
Var
    int iEnd, iStart,
    string sMark
Let sMark = "\"" + sName + "\":\""
Let iStart = StringContains (sJson, sMark)
If iStart == 0 Then
    Return ""
EndIf
Let iStart = iStart + StringLength (sMark)
Let iEnd = iStart
While iEnd <= StringLength (sJson)
    If SubString (sJson, iEnd, 1) == "\"" Then
        If SubString (sJson, iEnd - 1, 1) != "\\" Then
            Return SubString (sJson, iStart, iEnd - iStart)
        EndIf
    EndIf
    Let iEnd = iEnd + 1
EndWhile
Return ""
EndFunction


; Quotes a string for putting inside JavaScript.
; Quotes a string for putting inside JavaScript.
Function jsQuote (string sText) returns string
Let sText = StringReplaceSubstrings (sText, "\\", "\\\\")
Let sText = StringReplaceSubstrings (sText, "\"", "\\\"")
Return "\"" + sText + "\""
EndFunction


; Launches or reconnects HomerView's copy of Microsoft Edge. Alt+JAWSKey+H.
; Launches or reconnects HomerView's copy of Microsoft Edge. Alt+JAWSKey+H.
Script launchHomerView ()
SayMessage (OT_STATUS, "Starting HomerView")
Var string sAnswer
Let sAnswer = callBridge ("launch", "")
If sAnswer == "" Then
    Return
EndIf
If StringContains (sAnswer, "\"connected\":true") > 0 Then
    SayMessage (OT_MESSAGE, "HomerView is ready.")
Else
    SayMessage (OT_ERROR, jsonValue (sAnswer, "error"))
EndIf
EndScript


; Moves to the probable main content of a page that declares none. Shift+Q.
;
; JAWS already moves to a declared main region with Q, so this is the case Q
; cannot serve: about half the web names no main region at all. It weighs every
; part of the page, the most text with the fewest links winning, and always
; says that it inferred the answer rather than being told it.
; Moves to the probable main content of a page that declares none. Shift+Q.
;
; JAWS already moves to a declared main region with Q, so this is the case Q
; cannot serve: about half the web names no main region at all. It weighs every
; part of the page, the most text with the fewest links winning, and always
; says that it inferred the answer rather than being told it.
Script moveToProbableMain ()
Var string sResult
Let sResult = runScript (
    "(() => {"
    + "if (document.querySelector('main,[role=main]')) return 'declared';"
    + "let elBest = null, nBest = 0;"
    + "for (const el of document.querySelectorAll('article,section,div')) {"
    + "  const s = (el.innerText || '').trim();"
    + "  if (s.length < 200) continue;"
    + "  let iLink = 0;"
    + "  for (const a of el.querySelectorAll('a')) iLink += (a.innerText || '').length;"
    + "  const nShare = iLink / s.length;"
    + "  if (nShare > 0.5) continue;"
    + "  let n = s.length * (1 - nShare);"
    + "  if (el.tagName === 'ARTICLE') n *= 1.5;"
    + "  if (n > nBest) { nBest = n; elBest = el; }"
    + "}"
    + "if (!elBest) return '';"
    + "return elBest.innerText.replace(/\\s+/g, ' ').trim().slice(0, 90);"
    + "})()")
If sResult == "declared" Then
    SayMessage (OT_MESSAGE, "This page says where its main content is. Press Q.")
    Return
EndIf
If sResult == "" Then
    SayMessage (OT_ERROR, "The main content could not be worked out.")
    Return
EndIf
; The words are the bridge between the browser and the virtual cursor. JAWS
; has no notion of the browser's own elements, and both sides have the text.
JAWSFindFirst (sResult, 0, 0, 0, 0, 0)
SayMessage (OT_MESSAGE, "Main content, by weighing the page")
SayLine ()
EndScript


; Where the bridge writes its answer. One file, overwritten each time, in the
; folder Windows clears on its own.
; Where the bridge writes its answer. One file, overwritten each time, in the
; folder Windows clears on its own.
Function outputPath () returns string
Return GetEnvironmentVariable ("TEMP") + "\\" + sHomerFolder + "Answer.json"
EndFunction


; Runs a piece of JavaScript in the page and returns what it produced.
; Runs a piece of JavaScript in the page and returns what it produced.
Function runScript (string sJavaScript) returns string
Var string sAnswer
Let sAnswer = callBridge ("evaluate", sJavaScript)
If sAnswer == "" Then
    Return ""
EndIf
If StringContains (sAnswer, "\"error\"") > 0 Then
    SayMessage (OT_ERROR, jsonValue (sAnswer, "error"))
    Return ""
EndIf
Return jsonValue (sAnswer, "value")
EndFunction

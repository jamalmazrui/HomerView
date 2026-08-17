; HomerView.jss -- HomerView scripts for Microsoft Edge
;
; HomerView gives a screen reader user what the browser knows and the reading
; order never carries. The NVDA version does this from inside NVDA, in Python.
; JAWS scripting cannot open a WebSocket, which is where every Chrome DevTools
; command that reads or acts on a page travels, so this version asks
; HomerView.exe to do that part and reads back what it said.
;
; The bridge is run through WScript.Shell, which waits for it to finish, and
; its answer is read with Scripting.FileSystemObject. Both of those are
; registered on every Windows machine already, so nothing of HomerView's has to
; be registered at all.
;
; TWO PATHS ARE WRITTEN INTO THIS FILE WHEN IT IS INSTALLED, by
; installJawsScripts.ps1: where the bridge is, and where its answer goes. The
; installer knows both, having just put the one there and being run as the user
; who owns the other. Working them out here instead would mean calling built-in
; functions whose names and return types are the thing this file has been wrong
; about more often than anything else. If the two constants below still read
; @bridgePath@ and @answerPath@, this copy was compiled without being
; installed, and every command says so rather than failing quietly.
;
; What is NOT here matters as much as what is. JAWS already moves to the main
; region with Q, says the web address with JAWSKey+A, lists headings, links and
; form fields with JAWSKey+F5, F6 and F7, and finds with Control+F. HomerView
; on NVDA has its own versions of those only because NVDA lacks them. Taking a
; key a JAWS user already knows and giving it something almost the same would
; be worse than not having it.
;
; So this adds the main content of a page that declares none, and the commands
; nothing else has. Not on Shift+Q: all twenty-six letters are already
; navigation quick keys, and Shift with a quick key is reserved for the
; previous element of that kind. These take modified keys and sit in the
; virtual keys section of the key map, where they cannot fire outside a virtual
; document and cannot interfere with typing.
;
; Four things the compiler has taught this file. All four cost a release each,
; so they are written down here rather than remembered:
;
; 1. Every variable in a Var block carries its own type. "string sOne, sTwo" is
;    not two strings: the second name is read as a type, and the compiler then
;    asks for a variable to follow it. So "string sOne, string sTwo".
;
; 2. There is no Null. An object is not compared with anything and is not
;    cleared; it goes when the function does.
;
; 3. Let in front of a method call is rejected outright, so oShell.Run is
;    assigned to the exit code it returns and oFile.ReadAll to the text. A bare
;    method call with no Let IS a valid statement — EdSharp's library writes
;    oFile.close() exactly that way. It was the Let that was wrong, not the
;    call, and this file said otherwise for a day.
;
; 3a. There is no Null, but there is an idiom for it and EdSharp uses it
;    everywhere: declare an object variable, never assign it, and assign FROM it
;    to clear another. Object oNull in the Var block, then Let oFile = oNull.
;
; 4. The return type goes before the word Function, not after the parameters.
;
; 5. A Var block comes first in a script, before any statement.
;
; 7. A CALL TO A FUNCTION THAT DOES NOT EXIST IS NOT AN ERROR when its result
;    is discarded. The compiler invents a declaration and moves on, so the
;    command simply does nothing at run time and nothing ever says why. Two
;    calls in this file were like that: GetLinkURL and JAWSFindFirst, neither of
;    which is in Freedom Scientific's reference. Every name here has now been
;    read from that reference rather than remembered.
;
; 6. EVERYTHING IS DEFINED BEFORE IT IS USED. The compiler reads the file once.
;    The order is: the helpers adapted from EdSharp, then HomerView's own
;    functions, then the scripts, each group alphabetical within itself. Plain
;    alphabetical across everything stopped working the moment callBridge
;    needed shellRun.
;    A call to a function it has not reached yet is not an error in itself: it
;    invents a declaration from that first call and assumes the return is an
;    int. What is reported is the assignment further along the line, as
;    "Expected sResult to be a variable of type int not string", which says
;    nothing about the real cause and points at the wrong thing entirely. So
;    every Function comes before every Script, and each group is in
;    alphabetical order, which happens to put callBridge and xmlValue above
;    runScript where they are needed.

Include "hjconst.jsh"

Const
    c_iWaitLimit = 120,
    c_sAnswerPath = "@answerPath@",
    c_sInstalled = "@installed@",
    c_sVersion = "@version@",
    c_sLogFile = "@logFile@",
    c_sAppFolder = "@appFolder@",
    c_sBridgePath = "@bridgePath@",
    c_sFileSystemProgId = "Scripting.FileSystemObject",
    c_sXmlProgId = "msxml2.DOMDocument.6.0",
    c_sXmlProgIdAny = "Msxml2.DOMDocument",
    c_sShellProgId = "WScript.Shell"

; EVERY FUNCTION HERE IS PREFIXED hv, AND THAT IS NOT A STYLE CHOICE.
;
; Vispero's own guidance: scripts and functions in MyExtensions WITH THE SAME
; NAME as ones in default or application scripts WILL NEVER RUN -- the other
; one runs instead, silently.
;
; A tester's machine has a chain of other script sets loaded through a
; default.jss dating from 2021. His log showed hVShowHomerViewMenu running (a
; name nobody else would use) and then dialogPick LOGGING NOTHING AT ALL --
; because a DIFFERENT dialogPick was running. DlgSelectItemInList was never at
; fault; it is a JAWS built-in that has worked for twenty years, and it was
; never reached.
;
; Names like dialogPick, shellRun, runScript, logLine and stringQuote are the
; sort of thing any script author writes. On a machine with only HomerView
; installed they are safe; on a machine with a script chain they are a
; collision waiting to happen, and the failure is SILENT.

; THREE ARE DELIBERATELY NOT QUALIFIED, AND THE REASON IS THE PROPAGATION
; WARNING ABOVE: ScheduleFunction, PerformScriptByName and UserBufferAddLink
; ALL RESOLVE ONE OF OUR OWN NAMES LATER -- a function name, a script name, a
; link target. Restricting their scope to Builtin would restrict THAT LOOKUP
; too, and none of our names live there. Qualifying them would have broken the
; menu and the poller outright. They stay unqualified and rely on the hV prefix.

; WHY SOME CALLS SAY Builtin:: AND OTHERS DO NOT.
;
; FSDN: "In addition to specifying a qualification by script file name, you may
; also specify that a built-in function be called... Builtin::SayLine ()
; specifies that the built-in SayLine function be called, NOT AN OVERWRITTEN
; SayLine function."
;
; That matters here because a machine may carry a large script suite -- Leasey,
; for one -- that is always loaded and replaces functions by name. An overwritten
; DlgSelectItemInList does not have to fail loudly; it can simply answer
; differently, and this file would believe it.
;
; SO THE SPLIT IS DELIBERATE:
;
; QUALIFIED are the built-ins whose RETURN VALUE drives the logic -- the list
; dialog, the input box, the string functions, the buffer, the dispatcher, COM.
; If any of those answers differently, this code computes the wrong thing and
; says nothing about it.
;
; NOT QUALIFIED are the SPEECH functions: SayMessage, SayLine, SayAll. A suite
; like Leasey overrides those ON PURPOSE, to serve that user's voice, braille
; and verbosity settings. Forcing the built-in would override the user's own
; screen reader on their own machine, which is not ours to do. WE WANT OUR
; LOGIC BACK, NOT THEIR SPEECH.
;
; One caution from the same page, which is why this is not applied wholesale:
; restricting a call's scope also restricts every call made from inside it.
; That is harmless for built-ins, which call no script code, and would not be
; for our own functions -- those are kept unqualified and safe by their hV
; prefix instead.

Globals
    int giLastPick, int giWaitTicks,
    string gsClipboardFile, string gsLastFind,
    string gsLastResult, string gsLastTag, string gsLastText, string gsLogPath,
    string gsWaitFor


; The one log, with a session header written the first time it is asked for.
;
; The file is chosen by the installer and written in here, so the installation
; and every command afterwards land in one file. It used to name its own,
; which meant an install left one file and the next JAWS session started
; another, and the build's own test of the bridge started a third. Three files
; from one afternoon, and a question every time about which to send.
;
; gsLogPath doubles as the mark that this session's header has been written.
; It lasts as long as JAWS keeps the scripts loaded, so each sitting adds one
; header and its own lines beneath it.
string Function hVLogPath ()
Var
    object oFile, object oFileSystem
; THE HEADER IS WRITTEN WHEN THE FILE LACKS ONE, NOT ONCE PER SESSION.
;
; Two of a tester's logs came back with NO VERSION ANYWHERE IN THEM, so there
; was no way to tell which build they described, and a round of reasoning went
; into the wrong file. The old test was "have I written a header THIS SESSION",
; which says nothing about whether THIS FILE has one -- a fresh log named by a
; new install gets none if the session already wrote to the previous name.
;
; The test is now the file itself: no file, or an empty one, gets a header.
Let oFileSystem = Builtin::CreateObjectEx (c_sFileSystemProgId, False)
If gsLogPath != "" Then
    If oFileSystem.FileExists (gsLogPath) Then
        Return gsLogPath
    EndIf
EndIf
Let gsLogPath = c_sLogFile
Let oFile = oFileSystem.OpenTextFile (gsLogPath, 8, True)
oFile.WriteLine ("")
oFile.WriteLine ("==========================================================")
oFile.WriteLine ("HomerView " + c_sVersion + " for " + GetJAWSVersionInfo ())
oFile.WriteLine ("  scripts installed: " + c_sInstalled)
oFile.WriteLine ("  session started:   " + Builtin::SysGetDate ("yyyy-MM-dd") + " " + Builtin::SysGetTime ("HH:mm:ss"))
oFile.WriteLine ("  bridge:            " + c_sBridgePath)
oFile.WriteLine ("==========================================================")
oFile.Close ()
Return gsLogPath
EndFunction


; Appends a line to the same log the bridge writes.
;
; THE SCRIPT SIDE HAS NEVER HAD A LOG, and every silent failure of the last few
; days has been on this side of the line. The bridge records what it was asked
; and what it answered; between that answer and the user there were four steps
; nobody could see. Now they say what they did.
;
; Nothing here can fail loudly: a log that throws while recording a fault is
; worse than no log at all. Append mode is 8, and True creates the file.
Void Function hVLogLine (string sText)
Var
    object oFile, object oFileSystem,
    string sFolder
; LOGGING MUST NOT BE ABLE TO KILL A COMMAND, AND IT COULD.
;
; JSL has no way to catch a fault, so a line that throws ENDS THE SCRIPT THERE.
; Every command in this file begins with logLine, so if OpenTextFile failed --
; a folder that does not exist, a path that cannot be written -- THE COMMAND
; DIED AT ITS FIRST LINE WITH NO SPEECH AND NO LOG ENTRY. That is exactly what
; a tester saw: menu items that did nothing at all, and a log with no session
; in it. A diagnostic that disappears when things go wrong is worse than none.
;
; So the folder is made first if it is missing. OpenTextFile creates a FILE
; that is not there; it does NOT create the FOLDER above it.
Let oFileSystem = Builtin::CreateObjectEx (c_sFileSystemProgId, False)
Let sFolder = oFileSystem.GetParentFolderName (hVLogPath ())
If sFolder != "" Then
    If oFileSystem.FolderExists (sFolder) == False Then
        oFileSystem.CreateFolder (sFolder)
    EndIf
EndIf
Let oFile = oFileSystem.OpenTextFile (hVLogPath (), 8, True)
; Stamped like the bridge's lines, so the two interleave into one account
; rather than one column of times and one without.
oFile.WriteLine (Builtin::SysGetDate ("yyyy-MM-dd") + " " + Builtin::SysGetTime ("HH:mm:ss") + "  script: " + sText)
oFile.Close ()
EndFunction


; Shows a choice and returns what was picked, not its number.
;
; The items are separated by "\7". Not "\007": the reference writes the
; character that way, homer.jss writes "\7", and a library that has been
; calling this function for years beats a manual's typography.
;
; The pause matters more than it looks. The dialog is closing and focus is
; moving as this returns, and anything spoken into that is spoken into nothing.
; homer.jss pauses here for the same reason.
int Function hVDialogPick (string sTitle, string sItems)
Var
    int iChoice, int iOpenedAt
; The fourth argument is where the list opens, and giLastPick is where it was
; left. A list that always opens at the top makes the second use of a command
; as long as the first, and the commands people use are the ones they used
; last. Cancelling does not move it: changing your mind is not a choice.
; NEVER 0. THE FOURTH ARGUMENT IS A ONE BASED INDEX.
;
; FSDN: "the index of the item which should have the focus when the dialog is
; invoked", and the return is "the one based index of the selected item".
; giLastPick starts at 0, WHICH IS NOT A VALID INDEX -- and the fault it caused
; kept itself alive: the dialog answered 0, so the line below that sets
; giLastPick was never reached, so it stayed 0, so the next menu did the same.
;
; A tester saw exactly that and reported both halves of it without either of us
; joining them up: EVERY Alternate Menu command did nothing, said nothing and
; logged nothing, AND the menu never remembered the last item. Those were one
; fault. Commands on KEYS worked throughout, which is why his log showed
; hVCopySelection running normally in the same session.
; BRACKETED BY LOGGING, BECAUSE THE SCRIPT STOPS SOMEWHERE IN HERE.
;
; On a tester's machine hVShowHomerViewMenu logged "offering the menu" FOUR
; TIMES and dialogPick logged NOTHING AT ALL -- not a choice, not even a
; cancellation. A JSL script that faults ENDS THERE, silently, so the missing
; line is the evidence: execution reaches this function and does not leave it.
;
; The same build logs normally on the developer's machine, so the difference
; is environmental and only his log can name it. These lines bracket every
; statement that could be the one, and the LENGTH of the item string is
; recorded because 44 rows is several thousand characters and a limit there
; would look exactly like this.
hVLogLine ("dialogPick: about to offer " + Builtin::IntToString (Builtin::StringLength (sItems))
    + " characters of items, opening at " + Builtin::IntToString (giLastPick))
If giLastPick < 1 Then
    Let giLastPick = 1
EndIf
Let iOpenedAt = giLastPick
Let iChoice = Builtin::DlgSelectItemInList (sItems, sTitle, False, giLastPick)
hVLogLine ("dialogPick: the dialog returned")
Pause ()
hVLogLine ("dialogPick: the pause finished")
; BOTH NUMBERS, BECAUSE THE PAIR IS THE MEASUREMENT.
;
; The answer alone says the menu worked. The value it OPENED AT says
; whether giLastPick survived since the last time -- and a global that does
; not survive means THE SET IS LOADED TWICE, each copy keeping its own.
; That is the difference between a machine where the menu remembers and one
; where it forgets, and one run of this log settles which.
hVLogLine ("dialogPick: " + sTitle + " opened at " + Builtin::IntToString (iOpenedAt)
    + " and answered " + Builtin::IntToString (iChoice))
If iChoice == 0 Then
    Return 0
EndIf
Let giLastPick = iChoice
Return iChoice
EndFunction


; Puts text in the Virtual Viewer and starts reading it.
;
; This is JAWS's own answer to "show the user something they can look through",
; and it is what Hot Key Help uses. A message box can only be read as a whole:
; examining it by line, word or character means turning on the JAWS cursor
; first, which is a lot to ask of somebody who only wanted to see a result. The
; Virtual Viewer is a document — arrow keys work, the reading commands work,
; find works, and it can hold links.
;
; Deactivate before clearing, because a buffer that is already showing keeps
; what it had otherwise.
Void Function hVSayVirtual (string sText)
Var
    int iActivated, int iAdded
Builtin::UserBufferDeactivate ()
Builtin::UserBufferClear ()
Let iAdded = Builtin::UserBufferAddText (sText)
Let iActivated = Builtin::UserBufferActivate ()
JAWSTopOfFile ()
SayAll ()
; Both of these return a result and both were being thrown away. Every way of
; showing a result has failed silently in turn, and each time the only thing
; missing was somebody asking whether it had worked.
hVLogLine ("sayVirtual: added " + Builtin::IntToString (iAdded) + ", activated " + Builtin::IntToString (iActivated) + ", " + Builtin::IntToString (Builtin::StringLength (sText)) + " characters")
EndFunction


; A short sentence is SAID; anything worth examining is SHOWN.
;
; HIS POINT, and it is about what a result costs to receive. A virtual view is
; the right home for a report you want to read by line and character. It is the
; wrong home for "No links": that arrives as a buffer
; you must escape from, after which the line you were on has to be read again
; to find out where you are. A sentence with nothing in it to examine should
; simply be spoken.
;
; The rule is deliberately mechanical rather than a judgement made command by
; command: one line and under two hundred characters is a sentence, and
; everything else is a document.
Void Function hVSayOrShow (string sText)
If sText == "" Then
    Return
EndIf
If Builtin::StringContains (sText, "\r\n") > 0 Then
    hVSayVirtual (sText)
    Return
EndIf
If Builtin::StringLength (sText) > 200 Then
    hVSayVirtual (sText)
    Return
EndIf
hVLogLine ("sayOrShow speaking " + Builtin::IntToString (Builtin::StringLength (sText)) + " characters rather than showing them")
SayMessage (OT_MESSAGE, sText)
EndFunction


; Runs a command line, hidden or shown, waiting or not, and hands back the exit
; code. Windows Script Host is registered on every Windows machine, so nothing
; of ours has to be.
int Function hVShellRun (string sCommandLine, int iWindowStyle, int iWait)
Var
    int iExit,
    object oShell
Let oShell = Builtin::CreateObjectEx (c_sShellProgId, False)
Let iExit = oShell.Run (sCommandLine, iWindowStyle, iWait)
Return iExit
EndFunction


; Wraps a string in double quotes, for a path going onto a command line.
string Function hVStringQuote (string sText)
Return "\"" + sText + "\""
EndFunction


; Pulls one attribute's value out of a piece of XML.
;
; A whole parser is not needed to read one attribute, and the string functions
; are certain where an object model would be another thing to be wrong about.
string Function hVAttributeValue (string sXml, string sName)
Var
    int iEnd, int iStart,
    string sMark
Let sMark = sName + "=\""
Let iStart = Builtin::StringContains (sXml, sMark)
If iStart == 0 Then
    Return ""
EndIf
Let iStart = iStart + Builtin::StringLength (sMark)
Let iEnd = iStart
While iEnd <= Builtin::StringLength (sXml)
    If Builtin::SubString (sXml, iEnd, 1) == "\"" Then
        Return Builtin::SubString (sXml, iStart, iEnd - iStart)
    EndIf
    Let iEnd = iEnd + 1
EndWhile
Return ""
EndFunction


; Runs the bridge with one command and returns what it wrote.
;
; Hidden and waited for, so the script has the answer on the next line. A
; screen reader command is a question somebody is waiting on, so there is
; nothing to gain from doing it in the background.
;
; The whole command line is wrapped in double quotes, which is why nothing this
; file sends the bridge contains one: see jsQuote.
; Starts the helper WITHOUT waiting for it, for the commands that take a while.
;
; A JSL SCRIPT RUNS ON JAWS'S OWN THREAD. callBridge below ends in
; hVShellRun (..., True) -- WAIT -- so until the helper exits, JAWS CANNOT SPEAK
; OR TAKE A KEY. That is right for a command that answers in a moment, and it
; froze a whole screen reader when an accessibility scan did not: speech went
; everywhere, not just in HomerView, and Alt+Tab produced silence.
;
; ScheduleFunction is a TIMER, not a thread -- JSL is single threaded and stays
; so. But blocking was never the problem; NOT RETURNING was. This starts the
; helper, returns at once so JAWS is responsive again, and asks JAWS to look
; back in a moment. Each visit costs milliseconds, and Escape works throughout.
int Function hVStartBridge (string sWaitFor, string sCommand, string sArgument)
Var
    int iExit,
    object oFile, object oFileSystem, object oNull,
    string sArgumentPath, string sCommandLine, string sPassed
If Builtin::SubString (c_sBridgePath, 1, 1) == "@" Then
    SayMessage (OT_ERROR, "HomerView is not installed. Run its installer.")
    Return False
EndIf
Let oFileSystem = Builtin::CreateObjectEx (c_sFileSystemProgId, False)
Let sArgumentPath = c_sAnswerPath + ".arg"
If sArgument == "" Then
    Let sPassed = ""
Else
    Let oFile = oFileSystem.CreateTextFile (sArgumentPath, True, True)
    oFile.Write (sArgument)
    oFile.Close ()
    Let oFile = oNull
    Let sPassed = "@" + sArgumentPath
EndIf
Let sCommandLine = hVStringQuote (c_sBridgePath) + " " + sCommand
    + " " + hVStringQuote (c_sAnswerPath) + " " + hVStringQuote (sPassed)
hVLogLine ("startBridge " + sCommand + " without waiting, for " + sWaitFor)
If oFileSystem.FileExists (c_sAnswerPath) Then
    oFileSystem.DeleteFile (c_sAnswerPath)
EndIf
; False is the whole point of this function: do not wait.
Let iExit = hVShellRun (sCommandLine, 0, False)
Let gsWaitFor = sWaitFor
Let giWaitTicks = 0
ScheduleFunction ("hVBridgePoll", 5)
Return True
EndFunction


string Function hVCallBridge (string sCommand, string sArgument)
Var
    int iExit,
    object oFile, object oFileSystem, object oNull,
    string sAnswer, string sArgumentPath, string sCommandLine, string sPassed
If Builtin::SubString (c_sBridgePath, 1, 1) == "@" Then
    SayMessage (OT_ERROR, "HomerView is not installed. Run its installer.")
    Return ""
EndIf
; THE ARGUMENT NEVER TRAVELS ON THE COMMAND LINE.
;
; Windows takes about 32,000 characters and then refuses to start the program
; at all, which is not an error you can catch: the command simply never runs,
; and whatever was in the answer file from last time gets read as this time's
; reply. That cost a release when a page with 669 links handed 49,536
; characters to the clipboard command.
;
; So every argument goes through a file, whatever its length. A rule that only
; applies to big arguments is a branch that is almost never taken, and a branch
; almost never taken is a branch nobody has tested. The helper reads the file
; and deletes it.
;
; True as the third argument to CreateTextFile writes UTF-16, so an accented
; character survives the trip. .NET reads the byte order mark and knows.
Let oFileSystem = Builtin::CreateObjectEx (c_sFileSystemProgId, False)
Let sArgumentPath = c_sAnswerPath + ".arg"
If sArgument == "" Then
    Let sPassed = ""
Else
    Let oFile = oFileSystem.CreateTextFile (sArgumentPath, True, True)
    oFile.Write (sArgument)
    oFile.Close ()
    Let oFile = oNull
    Let sPassed = "@" + sArgumentPath
EndIf
Let sCommandLine = hVStringQuote (c_sBridgePath) + " " + sCommand
    + " " + hVStringQuote (c_sAnswerPath) + " " + hVStringQuote (sPassed)
hVLogLine ("callBridge " + sCommand + " sending "
    + Builtin::IntToString (Builtin::StringLength (sArgument)) + " characters through a file")
; A command that never started must never be read as the last one's success.
If oFileSystem.FileExists (c_sAnswerPath) Then
    oFileSystem.DeleteFile (c_sAnswerPath)
EndIf
; Nought hides the window; True waits for it to finish.
Let iExit = hVShellRun (sCommandLine, 0, True)
If oFileSystem.FileExists (c_sAnswerPath) Then
    ; The fourth argument is -1, which asks the FileSystemObject to read the
    ; file as Unicode. The helper writes UTF-16 and this reads it, which is the
    ; only pairing that works: opened in the default mode the byte order mark
    ; arrived as three visible characters in front of the answer, so nothing
    ; would parse as XML, and every accented character was mojibake. The two
    ; sides have to agree, and check 13 makes sure they still do.
    Let oFile = oFileSystem.OpenTextFile (c_sAnswerPath, 1, False, -1)
    Let sAnswer = oFile.ReadAll ()
Else
    SayMessage (OT_ERROR, "HomerView did not answer. Launch it and try again.")
    Return ""
EndIf
hVLogLine ("callBridge " + sCommand + " read " + Builtin::IntToString (Builtin::StringLength (sAnswer)) + " characters")
Let gsLastResult = sAnswer
Return sAnswer
EndFunction


; Reads one value out of the helper's answer, which is XML.
;
; JSL HAS NO JSON FUNCTIONS -- not one in the seventeen hundred odd names the
; reference documents. What sat here originally was a hand written JSON reader:
; find the name, walk forward a character at a time looking for the closing
; quote, then undo six escape sequences in a fixed order. It worked for a flat
; answer with a single string in it and would have been wrong the first time
; the helper returned anything nested, silently, because there is nothing in
; that method that can notice it has gone wrong.
;
; So the helper answers in XML instead: .NET turns the browser's JSON into XML
; with its own reader, and the answer's shape is the helper's own, so a path
; asked for here is a path the helper always writes.
string Function hVXmlValue (string sXml, string sPath)
Var
    object oDoc, object oNode
; A REAL XML PARSER, AND NOT ONE WRITTEN HERE.
;
; This first used CreateXMLDomDoc, LoadAndParseXML and GetXMLDomNodeText --
; Freedom Scientific's own, documented from JAWS 18. They compile on one
; machine and NOT on another: a tester's scompile answered
;
;   line 378: Expected oDoc to be a variable of type int not object
;
; on JAWS 2024, 2025 AND 2026, which is JSL assuming int for a function whose
; declaration it cannot resolve. Whatever supplies those declarations is
; present on some installations and absent on others, and a script set that
; only compiles on some machines cannot be released.
;
; MSXML THROUGH CreateObjectEx HAS NO SUCH PROBLEM, because a COM object's
; methods are resolved at RUN time -- there is no declaration for the compiler
; to look for. This file already reaches Scripting.FileSystemObject and
; Shell.Application exactly this way, on both machines, so the mechanism is
; proven here rather than hoped for.
;
; AND IT IS FREEDOM SCIENTIFIC'S OWN ADVICE. Their scripting notes for JAWS 14
; demonstrate parsing XML from a script with precisely this: create
; msxml2.DOMDocument, set async and resolveExternals to false, call loadXML,
; then query it. Their sample uses CreateObject; CreateObjectEx is the same
; call with the apartment argument this file already passes everywhere else.
;
; So the parsing is still done by a parser, and the entities are still its
; business rather than ours.
If sXml == "" Then
    Return ""
EndIf
; NO TEST THAT THE OBJECT EXISTS. Rule 2 at the top of this file: THERE IS NO
; NULL IN JSL, and an object is not compared with anything. If MSXML cannot be
; created the next line fails, and callBridge's caller reports the error the
; same way it reports any other -- which is how every other COM object in this
; file is already handled.
; THE VERSION INDEPENDENT PROGID IS TRIED TOO, AND THE RESULT IS LOGGED.
;
; A tester saw EVERY command do nothing while the launch still opened a
; browser. That is exactly the shape of this function failing: the bridge
; launches Edge before any answer is read, so launching looks fine, and every
; command that READS an answer silently returns "". Alt+Apostrophe is in that
; set too -- it goes through callBridge like the rest.
;
; If msxml2.DOMDocument.6.0 is not registered on a machine, CreateObjectEx
; hands back nothing and there is no error to hear. So the unversioned ProgID
; is tried after it, and the log SAYS which one answered, or that neither did.
Let oDoc = Builtin::CreateObjectEx (c_sXmlProgId, False)
If oDoc.loadXML ("<root/>") == False Then
    hVLogLine ("xmlValue: " + c_sXmlProgId + " did not answer, trying " + c_sXmlProgIdAny)
    Let oDoc = Builtin::CreateObjectEx (c_sXmlProgIdAny, False)
EndIf
; Written the way Freedom Scientific write it in their own sample: no Let,
; which JAWS 11 Update 1 made optional, and a property set on a COM object
; rather than a variable.
oDoc.async = False
oDoc.resolveExternals = False
If oDoc.loadXML (sXml) == False Then
    hVLogLine ("xmlValue: the answer was not well formed XML, asking for " + sPath)
    Return ""
EndIf
Let oNode = oDoc.selectSingleNode (sPath)
Return oNode.text
EndFunction


; Looks to see whether the helper has answered yet, and finishes if it has.
;
; Called by ScheduleFunction, so JAWS is between things when it runs. It either
; finds an answer and hands it to whoever asked, re-schedules itself, or gives
; up and SAYS SO -- a command that quietly never reports back is worse than one
; that fails.
;
; c_iWaitLimit visits of a half second each: ONE MINUTE. Nobody waits longer
; than that wondering whether a command is still going, and being told it is
; still running beats silence. The work is not cancelled -- the helper keeps
; going and its own log says how it ended.
; Typed int, not void. Every function in this file carries a type and none
; says void, so this uses the form the file has already proved compiles
; everywhere. The result is not read by anybody -- ScheduleFunction calls
; it by name -- so the type is a formality the compiler wants.
int Function hVBridgePoll ()
Var
    object oFile, object oFileSystem,
    string sAnswer, string sWaitFor
If gsWaitFor == "" Then
    Return False
EndIf
Let oFileSystem = Builtin::CreateObjectEx (c_sFileSystemProgId, False)
If oFileSystem.FileExists (c_sAnswerPath) == False Then
    Let giWaitTicks = giWaitTicks + 1
    If giWaitTicks > c_iWaitLimit Then
        Let sWaitFor = gsWaitFor
        Let gsWaitFor = ""
        hVLogLine ("bridgePoll: " + sWaitFor + " gave no answer in time")
        ; THE HELPER IS STILL GOING, AND IT WILL FINISH. He watched a Washington
        ; Post scan complete long after this point and write its report. So this
        ; says what is TRUE -- the waiting has stopped, the work has not.
        SayMessage (OT_MESSAGE, "Still working on that page. The report will be saved when it finishes.")
        Return False
    EndIf
    ; A WORD EVERY TEN SECONDS, NOT ONE AT THE END.
    ;
    ; Silence is the thing that makes a wait feel broken: a reader who hears
    ; nothing cannot tell a slow scan from a dead one, and starts pressing keys
    ; or restarting JAWS. Saying so costs a moment of speech and is worth it
    ; even if it makes the whole thing marginally slower.
    ;
    ; Twenty looks of half a second each is ten seconds. The division rather
    ; than a remainder operator keeps to arithmetic this file already uses.
    If giWaitTicks / 20 * 20 == giWaitTicks Then
        ; SHORT, BECAUSE IT REPEATS. Spoken every ten seconds, "Still working"
        ; is three syllables of nothing each time; the NUMBER is the only part
        ; that changes and the only part worth hearing.
        SayMessage (OT_STATUS, "Working, "
            + Builtin::IntToString (giWaitTicks / 2))
    EndIf
    ScheduleFunction ("hVBridgePoll", 5)
    Return False
EndIf
Let oFile = oFileSystem.OpenTextFile (c_sAnswerPath, 1, False, -1)
Let sAnswer = oFile.ReadAll ()
Let gsLastResult = sAnswer
Let sWaitFor = gsWaitFor
Let gsWaitFor = ""
hVLogLine ("bridgePoll: " + sWaitFor + " answered with "
    + Builtin::IntToString (Builtin::StringLength (sAnswer)) + " characters after "
    + Builtin::IntToString (giWaitTicks) + " looks")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    hVSayOrShow (hVXmlValue (sAnswer, "/root/error"))
    Return True
EndIf
If sWaitFor == "extractMainContent" Then
    SayMessage (OT_MESSAGE, "Extracted. It is open in HomerView.")
    Return True
EndIf
If sWaitFor == "openDocument" Then
    SayMessage (OT_MESSAGE, "Opened in HomerView.")
    Return True
EndIf
; The two scans both answer with a sentence of their own.
hVSayOrShow (hVXmlValue (sAnswer, "/root/value"))
EndFunction


; Quotes a string for putting inside JavaScript.
;
; Single quotes, not double. The JavaScript reaches the bridge as one command
; line argument wrapped in double quotes, so a double quote inside it would end
; the argument early and the rest of the program would arrive as separate
; arguments nobody reads. Nothing in this file's JavaScript uses one.
string Function hVJsQuote (string sText)
Let sText = Builtin::StringReplaceSubstrings (sText, "\\", "\\\\")
Let sText = Builtin::StringReplaceSubstrings (sText, "'", "\\'")
Return "'" + sText + "'"
EndFunction


; The address of the link under the virtual cursor.
;
; The element on its own first, and only then the element with its parent. That
; order matters: a paragraph holding three links, asked for with its parent
; included, hands back all three and the first one wins whether or not it is
; the one under the cursor. Asking for the element alone gets the right answer
; whenever JAWS reports the link itself, and the parent is a fallback for when
; it reports the list item or the paragraph that contains it.
;
; When there is no address, what the cursor IS on is worth saying. "No link
; here" sends a person hunting for a fault; "this is a banner region" tells
; them to move.
string Function hVLinkUrl ()
Var
    string sHref, string sTag, string sXml
Let sXml = GetElementXML (0)
Let sHref = hVAttributeValue (sXml, "href")
If sHref == "" Then
    Let sXml = GetElementXML (1)
    Let sHref = hVAttributeValue (sXml, "href")
EndIf
hVLogLine ("linkUrl: element XML is " + Builtin::IntToString (Builtin::StringLength (sXml)) + " characters: " + sXml)
If sHref == "" Then
    Let sTag = hVAttributeValue (sXml, "fsTag")
    hVLogLine ("linkUrl: no href; the cursor is on a " + sTag)
    Let gsLastTag = sTag
Else
    Let gsLastTag = ""
EndIf
; The link's own words go with the address. The helper compares them with the
; page's title and says when they have nothing in common, which is the mismatch
; a sighted reader catches by hovering and a blind reader never sees.
Let gsLastText = hVAttributeValue (sXml, "fsText")
hVLogLine ("linkUrl: href is " + sHref)
Return sHref
EndFunction


; Runs a piece of JavaScript in the page and returns what it produced.
;
; PLAIN TEXT, not JSON. This language has no JSON of its own, so an answer in
; JSON had to be taken apart here, character by character in a loop — bearable
; for a sentence and hopeless for an extracted article of fifty thousand
; characters. The helper takes it apart instead, where a runtime exists, and
; sends back the value alone. A failure arrives as a line beginning ERROR:,
; which one comparison finds.
string Function hVRunScript (string sJavaScript)
Var string sAnswer
Let sAnswer = hVCallBridge ("evaluateText", sJavaScript)
If sAnswer == "" Then
    Return ""
EndIf
If Builtin::SubString (sAnswer, 1, 6) == "ERROR:" Then
    hVLogLine ("runScript: " + sAnswer)
    SayMessage (OT_ERROR, sAnswer)
    Return ""
EndIf
hVLogLine ("runScript returning " + Builtin::IntToString (Builtin::StringLength (sAnswer)) + " characters")
Return sAnswer
EndFunction


; Opens one of HomerView's own documents in HomerView's browser.
;
; A FUNCTION, NOT SEVEN NEAR-IDENTICAL SCRIPTS. Each document command is three
; lines that name a file and call this, so a new document is a new script and a
; new row in the table rather than another copy of the same twenty lines.
Void Function hVOpenOwnDocument (string sFile, string sWhat)
Var
    int iExit,
    string sAnswer
hVLogLine ("openOwnDocument asked for " + sFile)
Let sAnswer = hVCallBridge ("openPage", c_sAppFolder + "\\" + sFile)
If hVXmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_STATUS, "Opening " + sWhat)
    Return
EndIf
; The same fallback the guide has: a document that will not open at all is
; worse than one in the wrong window, and these are what somebody reaches for
; when nothing else is working.
hVLogLine ("openOwnDocument: falling back to the default browser")
Let iExit = hVShellRun ("cmd.exe /c start \"\" " + hVStringQuote (c_sAppFolder + "\\" + sFile), 0, False)
SayMessage (OT_STATUS, "Opening outside HomerView")
EndFunction


; Marks every match in the page and moves to the first. Used by all four finds.
;
; ONE MARKING PASS, THEN NAVIGATION. Every match is wrapped in an element
; carrying an attribute of our own, and after that Find Again is simply a move
; to the next or previous element carrying it. Nothing has to remember a
; position between keystrokes, and "whichever kind of find was used last"
; settles itself: once marked, a plain match and a pattern match are the same
; thing.
;
; The same attribute trick Jump to Probable Main uses, for the same reason --
; an attribute is the one thing the browser and the virtual cursor can both
; see.
Void Function hVFindAndMark (string sMode, string sNeedle, int bBackwards)
Var
    int iMoved,
    string sAnswer, string sCount
Let sAnswer = hVCallBridge ("findMark", sMode + "\t" + sNeedle)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sCount = hVXmlValue (sAnswer, "/root/value")
If sCount == "0" Then
    SayMessage (OT_ERROR, "Not found")
    Return
EndIf
Let gsLastFind = sNeedle
If bBackwards Then
    Let iMoved = Builtin::MoveToTagWithAttribute (S_BOTTOM, "", "data-homerviewfind", True)
Else
    Let iMoved = Builtin::MoveToTagWithAttribute (S_TOP, "", "data-homerviewfind", True)
EndIf
hVLogLine ("findAndMark: " + sCount + " matches, moved " + Builtin::IntToString (iMoved))
If iMoved Then
    SayMessage (OT_MESSAGE, sCount + " found")
    SayLine ()
Else
    SayMessage (OT_MESSAGE, sCount + " found, cursor not moved")
EndIf
EndFunction


; Moves to the next or previous match already marked. F3 and Shift+F3.
Void Function hVFindAgain (int bBackwards)
Var int iMoved
If gsLastFind == "" Then
    SayMessage (OT_ERROR, "Nothing searched for yet")
    Return
EndIf
If bBackwards Then
    Let iMoved = Builtin::MoveToTagWithAttribute (S_PRIOR, "", "data-homerviewfind", True)
Else
    Let iMoved = Builtin::MoveToTagWithAttribute (S_NEXT, "", "data-homerviewfind", True)
EndIf
If iMoved Then
    SayLine ()
Else
    SayMessage (OT_MESSAGE, "No more")
EndIf
EndFunction


; Whether opening this file will run a converter.
;
; The same list the helper uses to pass a file through untouched. Kept in
; step with it by check 17, because two places deciding the same question
; differently is how a message comes to describe something that did not
; happen.
Int Function hVNeedsConverting (string sPath)
Var
    int iDot,
    string sExtension
Let iDot = Builtin::StringContains (sPath, ".")
If iDot == 0 Then
    Return True
EndIf
; -1 is the LAST segment, which JAWS 7 and later support directly. Counting
; the segments first would work too and gives one more place to be wrong.
Let sExtension = Builtin::StringLower (Builtin::StringSegment (sPath, ".", -1))
If sExtension == "htm" Then
    Return False
EndIf
If sExtension == "html" Then
    Return False
EndIf
If sExtension == "txt" Then
    Return False
EndIf
If sExtension == "xml" Then
    Return False
EndIf
If sExtension == "svg" Then
    Return False
EndIf
Return True
EndFunction


; Adds the clipboard to the end of a text file. Control+Shift+Apostrophe.
;
; The apostrophe family is his across every one of his programs: Alt for say,
; Control for save, Control+Shift for append, Alt+Shift for clear. They are
; VIRTUAL keys here and not common ones, which is deliberate -- a common key
; would take Alt+Apostrophe away from FileDir and EdSharp, which handle it
; themselves and would never see it again.
Script hVAppendClipboard ()
Var
    string sAnswer, string sPath
hVLogLine ("hVAppendClipboard started")
; THE SAME FILE AS LAST TIME, WITHOUT ASKING AGAIN.
;
; Appending is gathering, and gathering means many presses into one file. Being
; asked for the name every time would defeat it. When no file has been chosen
; yet there is nothing to append to, so this behaves exactly as Save Clipboard
; does and asks once.
If gsClipboardFile == "" Then
    hVLogLine ("hVAppendClipboard: no file yet, so asking as Save Clipboard would")
    PerformScriptByName ("hVSaveClipboard")
    Return
EndIf
Let sAnswer = hVCallBridge ("clipboardToFile", "+" + gsClipboardFile)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, hVXmlValue (sAnswer, "/root/value"))
EndScript


; Empties the clipboard, so an append starts afresh. Alt+Shift+Apostrophe.
Script hVClearClipboard ()
Var string sAnswer
hVLogLine ("hVClearClipboard started")
Let sAnswer = hVCallBridge ("clipboardClear", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, hVXmlValue (sAnswer, "/root/value"))
EndScript


; Adds what is selected, or the current line, to what is already on the
; clipboard. Alt+C.
;
; The whole point of an append is gathering: three paragraphs from different
; parts of a page into one note, without a second window to paste into.
Script hVCopyAppend ()
Var
    string sAnswer, string sText
hVLogLine ("hVCopyAppend started")
Let sText = Builtin::GetSelectedText ()
If sText == "" Then
    Let sText = GetLine ()
EndIf
If sText == "" Then
    SayMessage (OT_ERROR, "Nothing to copy")
    Return
EndIf
Let sAnswer = hVCallBridge ("clipboardAdd", sText)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, hVXmlValue (sAnswer, "/root/value"))
EndScript


; Puts the whole page on the clipboard. Control+F8.
;
; EdSharp's key for the same idea. JAWS has no equivalent: selecting a whole
; virtual document and copying it is Control+A then Control+C, which is the
; browser's selection rather than the text a reader sees, and on many pages
; brings back the navigation and the footers with it.
Script hVCopyAll ()
Var string sAnswer
hVLogLine ("hVCopyAll started")
SayMessage (OT_STATUS, "Copying")
Let sAnswer = hVCallBridge ("copyAll", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, hVXmlValue (sAnswer, "/root/value"))
EndScript


; Runs IBM's Equal Access checker and saves the results. Alt+JAWSKey+I.
;
; A SECOND ENGINE, NOT A REPLACEMENT. axe checks WCAG; IBM's unified ruleset
; folds EN 301 549 and Section 508 in with it, which is the superset several
; procurement regimes actually ask about.
;
; Everything it produces goes in one folder named after the page, under
; Downloads, replaced whole on each run -- and the HTML report opens in
; HomerView's own browser when it is done, so every other HomerView command
; works on it.
Script hVCheckAccessibilityIbm ()
Var int iStarted
hVLogLine ("hVCheckAccessibilityIbm started")
SayMessage (OT_STATUS, "Check Accessibility with IBM")
; STARTED, NOT WAITED FOR. A scan takes many seconds, and waiting here would
; hold JAWS'S OWN THREAD for all of them -- no speech anywhere, not just in
; HomerView. bridgePoll speaks the answer when it arrives.
Let iStarted = hVStartBridge ("checkAccessibilityIbm", "ace", "IBM_Accessibility")
If iStarted == False Then
    Return
EndIf
EndScript


; Copies what is selected, or the current line if nothing is. Control+C.
;
; CONTROL+C IS THE BROWSER'S KEY AND IS TAKEN ON THE PROJECT'S OWN TERMS: a key
; may be taken only where HomerView does everything the browser did with it and
; more. Edge copies a selection and does nothing at all without one. This
; copies the selection when there is one and the line under the cursor when
; there is not, which is the case a reader hits most often.
Script hVCopySelection ()
Var string sText
hVLogLine ("hVCopySelection started")
Let sText = Builtin::GetSelectedText ()
If sText == "" Then
    Let sText = GetLine ()
    If sText == "" Then
        SayMessage (OT_ERROR, "Nothing to copy")
        Return
    EndIf
    CopyToClipboard (sText)
    SayMessage (OT_MESSAGE, "Line copied")
    Return
EndIf
CopyToClipboard (sText)
SayMessage (OT_MESSAGE, "Copied " + Builtin::IntToString (Builtin::StringLength (sText)) + " characters.")
EndScript


; Selects from where the selection was started to here. Shift+F8.
Script hVCompleteSelection ()
Var string sText
hVLogLine ("hVCompleteSelection started")
; Muted for the same reason: this one reads the whole selection aloud, which
; on a long passage is the entire passage before he can do anything with it.
SpeechOff ()
PerformScript SelectTextBetweenMarkedPlaceAndCurrentPosition ()
SpeechOn ()
Let sText = Builtin::GetSelectedText ()
; THE OUTCOME, NOT THE ACTION. The previous version reported whether a function
; had returned true and logged nothing at all, so when it silently selected
; nothing there was no way to tell from the log whether the key had even
; arrived. The length of what is now selected is the only answer that means
; anything.
hVLogLine ("hVCompleteSelection: " + Builtin::IntToString (Builtin::StringLength (sText)) + " characters are selected")
If sText == "" Then
    SayMessage (OT_ERROR, "Nothing selected")
    Return
EndIf
; THE COUNT IS THE RESULT, so it is what gets said. "Complete Selection"
; only repeated the command name back; the number of characters is the one
; thing the reader cannot see and actually wanted to know.
SayMessage (OT_MESSAGE, "Complete Selection, "
    + Builtin::IntToString (Builtin::StringLength (sText)) + " characters")
EndScript


; Checks the page for accessibility problems. Alt+JAWSKey+A.
; Checks the page for accessibility problems. Alt+JAWSKey+A, the key the NVDA
; side uses. Not Alt+A, which on the NVDA side says the address.
;
; The same standards and the same four outcomes the NVDA side asks for: WCAG
; 2.0 A and AA, WCAG 2.1 AA, and best practice, with violations, things to
; review, passes and rules that did not apply. Left to itself the engine
; reports violations only, which is why a page with dozens of things worth
; reviewing came back saying one thing was wrong.
;
; Up to five places per problem, with what each element is and why the engine
; objected. A count without a location is a complaint, not a finding.
Script hVCheckAccessibility ()
Var int iStarted
hVLogLine ("hVCheckAccessibility started")
; COMMAND ECHO. The NAME of the command, not a description and not a vague
; "Checking": a reader who has just chosen from a 44 row menu, or pressed a
; key they may not be sure of, hears WHICH command is now running before any
; of the waiting begins. The same words as the menu row, so the two agree.
SayMessage (OT_STATUS, "Check Accessibility with axe")
; THE WHOLE REPORT, SAVED AND OPENED -- and started rather than waited for.
;
; The helper builds the report report.py builds on the NVDA side: plain
; language first, then the severity breakdown, then each violation with its
; criterion NAMED and its level given. It writes it to Downloads as one file
; and opens it in the browser.
;
; That takes seconds, sometimes tens of them, and this used to WAIT -- which
; froze every part of JAWS until it finished. bridgePoll reports instead.
Let iStarted = hVStartBridge ("checkAccessibility", "axeReport", "")
If iStarted == False Then
    Return
EndIf
EndScript


; Puts HomerView's JAWS log on the clipboard. Alt+JAWSKey+L.
;
; MOVED OFF JAWSKey+L, which was written into the key map, read back
; correctly, and never once fired. Something else has that key and finding
; out what is a longer road than taking a key of the same shape as the five
; Alt+JAWSKey ones that demonstrably work.
;
; As a FILE first, so Control+V in the body of an Outlook message attaches it,
; and as the path in plain text if that is refused.
;
; The helper does the work. This scripting language cannot reach the clipboard,
; and neither Windows Script Host nor the FileSystemObject can put a FILE on it
; in any case. PowerShell can, but only when started with -STA, and when that
; was missing the failure went to a hidden console and the command appeared to
; do nothing at all — twice. A program that declares its own apartment cannot
; fail that way, and the helper is already there.
Script hVCopyLogToClipboard ()
Var
    string sAnswer
hVLogLine ("hVCopyLogToClipboard started")
Let sAnswer = hVCallBridge ("clipboardFile", hVLogPath ())
If hVXmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_MESSAGE, "Log on the clipboard, as a file and as a path")
    Return
EndIf
hVLogLine ("hVCopyLogToClipboard: the file drop was refused: " + hVXmlValue (sAnswer, "/root/error"))
Let sAnswer = hVCallBridge ("clipboardText", hVLogPath ())
If hVXmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_MESSAGE, "Log path on the clipboard")
Else
    SayMessage (OT_ERROR, "Clipboard refused. Log at " + hVLogPath ())
EndIf
EndScript


; Puts every link on the page on the clipboard. Alt+Shift+P.
;
; The text and the address of each, one per line, in the order they appear.
; A page's links are a table of contents nobody prints, and having them as
; text means they can be pasted into a message, searched, or kept.
Script hVCopyPageLinks ()
Var
    int iJaws, int iLength,
    string sAnswer, string sResult, string sStripped, string sXml
hVLogLine ("hVCopyPageLinks started")
; THE PARITY QUESTION, ASKED ON EVERY RUN RATHER THAN ONCE IN A LABORATORY.
;
; The links could be collected here instead of in the browser: GetDocumentXML
; hands back the whole virtual document and its Link elements carry href. That
; would need no helper and would work in any browser JAWS supports.
;
; But the two do not necessarily see the same page. The helper reads the DOM,
; which is what HomerView for NVDA reads. This reads the off screen model,
; which is JAWS's own rendering of it, and the two can disagree about links
; that are hidden, inside an iframe, or added after the page settled. Fewer
; links here than there means the off screen model is the poorer source and
; the collection stays where it is.
;
; So both counts go in the log every time the command runs, on whatever page
; he happens to be on. A comparison made on one page of my choosing would
; prove nothing about the pages he actually reads.
;
; Counted without a loop: take the length, take the length again with every
; opening Link tag removed, and the difference divided by the length of the
; tag is how many there were.
Let sXml = GetDocumentXML ()
Let iLength = Builtin::StringLength (sXml)
Let sStripped = Builtin::StringReplaceSubstrings (sXml, "<Link ", "")
Let iJaws = (iLength - Builtin::StringLength (sStripped)) / 6
hVLogLine ("  the off screen model has " + Builtin::IntToString (iJaws) + " links in "
    + Builtin::IntToString (iLength) + " characters of document XML")
SayMessage (OT_STATUS, "Collecting links")
Let sResult = hVRunScript (
    "(() => {"
    + "const l = [];"
    + "for (const a of document.querySelectorAll('a[href]')) {"
    + "  const s = (a.innerText || a.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();"
    + "  l.push((s || '(no text)') + '\\t' + a.href);"
    + "}"
    + "if (!l.length) return '';"
    + "return l.length + ' links.\\n\\n' + l.join('\\n');"
    + "})()")
If sResult == "" Then
    SayMessage (OT_ERROR, "No links")
    Return
EndIf
; The browser's own count is the first word of what it sent back. It stays a
; string: turning it into a number would need a conversion this file has never
; proved exists, and an unknown function is assumed to return an int, so the
; arithmetic would type check perfectly and be wrong in silence. Two numbers on
; one log line need no arithmetic to compare.
hVLogLine ("  PARITY on this page: off screen model " + Builtin::IntToString (iJaws)
    + " links, browser " + Builtin::StringSegment (sResult, " ", 1) + " links")
Let sAnswer = hVCallBridge ("clipboardText", sResult)
If hVXmlValue (sAnswer, "/root/value") != "" Then
    ; A COUNT, BECAUSE IT IS THE ONE THING THE READER CANNOT SEE.
    ; "Links on the clipboard" says the command finished; the NUMBER says
    ; what it got, and tells them at once whether it found the whole page
    ; or three stragglers. The browser already returns the count first.
    SayMessage (OT_MESSAGE, Builtin::StringSegment (sResult, " ", 1)
        + " links on the clipboard")
Else
    SayMessage (OT_ERROR, "Clipboard refused")
EndIf
EndScript


; Says what is at the link under the cursor, without going there. Alt+L.
;
; The question goes to the bridge, not to the page. Asking the page meant
; calling fetch inside it, and a page may not fetch another site unless that
; site says it may — so every link that pointed somewhere else came back as
; "The link could not be reached", which read as a broken link when it was
; nothing of the kind. The bridge is a program, not a page, and no such rule
; applies to it.
Script hVDescribeLinkTarget ()
Var
    string sAnswer, string sResult, string sUrl
hVLogLine ("hVDescribeLinkTarget started")
Let sUrl = hVLinkUrl ()
If sUrl == "" Then
    hVLogLine ("hVDescribeLinkTarget: no address here")
    If gsLastTag == "" Then
        SayMessage (OT_ERROR, "No link here")
    Else
        SayMessage (OT_ERROR, "No link here, a " + gsLastTag)
    EndIf
    Return
EndIf
SayMessage (OT_STATUS, "Asking")
Let sAnswer = hVCallBridge ("probe", sUrl + "\t" + gsLastText)
If sAnswer == "" Then
    Return
EndIf
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = hVXmlValue (sAnswer, "/root/value")
; THE ADDRESS IS SHOWN WHATEVER ELSE HAPPENS.
;
; This used to be two commands: one that fetched a description and one that
; only showed the address. Two keys for one question, and the reader had to
; know in advance which of them would answer. Worse, when the fetch failed the
; describing one showed nothing at all, so the address -- which was already in
; hand and needed no network -- was the thing you lost.
;
; Now the address is always there, and the description is added when it can be
; got. The order follows the NVDA side: what the page is, then the address
; last, where it can be read a character at a time.
If sResult == "" Then
    hVLogLine ("hVDescribeLinkTarget: nothing came back about the target, showing the address alone")
    hVSayOrShow ("Link not reached. Its address:"
        + "\r\n\r\n" + sUrl)
Else
    hVSayOrShow (sResult)
EndIf
EndScript


; Closes whatever is covering the page. Alt+JAWSKey+D.
;
; Cookie banners, newsletter offers and sign-in walls are not part of the page
; and are rarely reachable by the keys that would dismiss them. This closes any
; open dialog element, then presses Escape at whatever else is pinned over the
; content, and says how many things it shifted.
Script hVDismissDialog ()
Var string sResult
hVLogLine ("hVDismissDialog started")
Let sResult = hVRunScript (
    "(() => {"
    + "let n = 0;"
    + "for (const el of document.querySelectorAll('dialog[open]')) { el.close(); n += 1; }"
    + "for (const el of document.querySelectorAll('[role=dialog],[role=alertdialog]')) {"
    + "  const b = el.querySelector('[aria-label*=close i],[aria-label*=dismiss i],"
    + "button[class*=close i],button[class*=dismiss i]');"
    + "  if (b) { b.click(); n += 1; continue; }"
    + "  const st = getComputedStyle(el);"
    + "  if (st.display !== 'none' && st.visibility !== 'hidden') { el.remove(); n += 1; }"
    + "}"
    + "for (const el of document.querySelectorAll('div,section,aside')) {"
    + "  const st = getComputedStyle(el);"
    + "  if (st.position !== 'fixed' && st.position !== 'sticky') continue;"
    + "  if (st.display === 'none' || st.visibility === 'hidden') continue;"
    + "  const b = el.getBoundingClientRect();"
    + "  if (b.height < window.innerHeight * 0.25) continue;"
    + "  if (b.width < window.innerWidth * 0.5) continue;"
    + "  el.remove(); n += 1;"
    + "}"
    + "document.documentElement.style.overflow = 'auto';"
    + "document.body.style.overflow = 'auto';"
    + "return n === 0 ? 'Nothing was covering the page.'"
    + "  : n + (n === 1 ? ' thing was' : ' things were') + ' closed.';"
    + "})()")
If sResult != "" Then
    SayMessage (OT_MESSAGE, sResult)
EndIf
EndScript


; Extracts the readable part of the page into a document and opens it.
; Shift+F9, the key the NVDA side uses, beside Edge's own reading view on F9.
;
; The whole job is the helper's. It injects Mozilla's Readability, takes the
; article as HTML rather than as text, writes a document with a heading, the
; byline, the site and a link back to where it came from, and opens that in a
; new tab through the debugger — a page may not open a file address itself.
;
; AS HTML, because an article's links are often the reason for reading it, and
; plain text throws every one of them away. That was the fault in the version
; before this: it showed the words and lost everything they pointed at.
Script hVExtractMainContent ()
Var int iStarted
hVLogLine ("hVExtractMainContent started")
SayMessage (OT_STATUS, "Extract Main Content")
; STARTED, NOT WAITED FOR, LIKE THE TWO SCANS.
;
; Tracing the menu commands by hand caught this one: extracting an article
; from a long page reads and rewrites the whole document, which takes as long
; as a scan does -- and this still WAITED, holding JAWS'S OWN THREAD for all of
; it. A reader would have lost speech everywhere, exactly as happened with Axe.
; The three slow commands were converted; this is the fourth and it was missed.
Let iStarted = hVStartBridge ("extractMainContent", "extract", "")
If iStarted == False Then
    Return
EndIf
EndScript


; Launches or reconnects HomerView's copy of Microsoft Edge. No key by default:
; see the guide, since default.jkm is never touched.
Script hVLaunchHomerView ()
Var string sAnswer
SayMessage (OT_STATUS, "Launching HomerView")
Let sAnswer = hVCallBridge ("launch", "")
If sAnswer == "" Then
    Return
EndIf
If hVXmlValue (sAnswer, "/root/connected") == "true" Then
    ; NOTHING IS SAID HERE ON PURPOSE.
    ;
    ; A browser window opening announces itself: the screen reader reads the
    ; new window and its page, as it does for any other window. Saying "ready"
    ; on top of that is a second voice for one event, and it arrives just as
    ; the reader is listening for the page. The window IS the confirmation.
    ;
    ; A FAILURE still speaks, below, because nothing else would say so.
    hVLogLine ("hVLaunchHomerView: launched, and the window will announce itself")
Else
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
EndIf
EndScript


; The open tabs, by name and address. On the menu, with no key of its own.
;
; No key because F4 is what the NVDA side uses and F4 in this browser puts the
; cursor in the address bar. A key that takes something away from the browser
; has to give more back than it costs, and a list nobody asked for does not.
Script hVListTabs ()
Var
    int iActivated, int iAdded, int iTab,
    string sAnswer, string sId, string sRecord, string sResult,
    string sTitle, string sUrl
hVLogLine ("hVListTabs started")
Let sAnswer = hVCallBridge ("tabList", "")
If sAnswer == "" Then
    Return
EndIf
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = hVXmlValue (sAnswer, "/root/value")
If sResult == "" Then
    SayMessage (OT_ERROR, "No tabs")
    Return
EndIf
; EACH TITLE IS A LINK, AND ENTER OPENS THAT TAB.
;
; What a JAWS user expects of a list: F6 and F7 give lists you can act on, not
; paragraphs you read and then have to act on separately. The helper sends one
; record per tab -- target id, title and address separated by tabs, records
; separated by character 7 -- so the id survives to reach the link. A list built
; as prose would have thrown the id away, and the id is the only thing that can
; activate anything.
Builtin::UserBufferDeactivate ()
Builtin::UserBufferClear ()
Let iAdded = Builtin::UserBufferAddText ("HomerView tabs. Press Enter on one to go to it.")
Let iAdded = Builtin::UserBufferAddText ("")
Let iTab = 1
Let sRecord = Builtin::StringSegment (sResult, "\7", iTab)
While sRecord != ""
    Let sId = Builtin::StringSegment (sRecord, "\t", 1)
    Let sTitle = Builtin::StringSegment (sRecord, "\t", 2)
    Let sUrl = Builtin::StringSegment (sRecord, "\t", 3)
    Let iAdded = UserBufferAddLink (Builtin::IntToString (iTab) + ". " + sTitle,
        "hVHomerViewTab (\"" + sId + "\")", sTitle)
    Let iAdded = Builtin::UserBufferAddText ("   " + sUrl)
    Let iTab = iTab + 1
    Let sRecord = Builtin::StringSegment (sResult, "\7", iTab)
EndWhile
Let iActivated = Builtin::UserBufferActivate ()
JAWSTopOfFile ()
SayAll ()
hVLogLine ("hVListTabs showed " + Builtin::IntToString (iTab - 1) + " tabs, activated " + Builtin::IntToString (iActivated))
EndScript


; Moves to the probable main content of a page that declares none.
; Alt+JAWSKey+Q.
;
; JAWS already moves to a declared main region with Q, so this is the case Q
; cannot serve: about half the web names no main region at all. It weighs every
; part of the page, the most text with the fewest links winning, and always
; says that it inferred the answer rather than being told it.
;
; SHIFT+Q, BESIDE JAWS'S OWN Q. Freedom Scientific's list gives Shift plus a
; navigation quick key to the PREVIOUS element of that kind, so Shift+Q
; natively means the previous main region -- and a page has one main region, so
; that meaning has nowhere to go. Q itself is untouched, and the pair reads the
; way a JAWS user would expect: Q for the region the page declares, Shift+Q for
; the main content whether it declares one or not.
;
; A virtual key, so it cannot fire outside a virtual document and cannot take
; the letter away from anywhere a person is typing.
;
; The browser marks the winner with an attribute of our own and JAWS moves to
; whatever carries it. Searching for the text was the alternative, and it fails
; on any page that repeats the words elsewhere. The mark is removed from
; wherever it was last so a page only ever has one.
Script hVMoveToProbableMain ()
Var
    int iMoved,
    string sResult
Let sResult = hVRunScript (
    "(() => {"
    + "for (const el of document.querySelectorAll('[data-homerviewmain]'))"
    + "  el.removeAttribute('data-homerviewmain');"
    + "const elDeclared = document.querySelector('main,[role=main]');"
    + "if (elDeclared) {"
    + "  elDeclared.setAttribute('data-homerviewmain', '1');"
    + "  return 'declared';"
    + "}"
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
    + "elBest.setAttribute('data-homerviewmain', '1');"
    + "return elBest.innerText.replace(/\\s+/g, ' ').trim().slice(0, 90);"
    + "})()")
If sResult == "" Then
    SayMessage (OT_ERROR, "No main content found")
    Return
EndIf
; The attribute is the bridge between the browser and the virtual cursor. The
; tag is left empty because any element may have won; S_TOP is used rather than
; S_NEXT so it does not matter where the cursor was.
;
; An earlier version called JAWSFindFirst, which does not exist. A call to an
; unknown function is not an error on its own in this language, so the compiler
; accepted it and the command would simply have done nothing.
Let iMoved = Builtin::MoveToTagWithAttribute (S_TOP, "", "data-homerviewmain", True)
hVLogLine ("hVMoveToProbableMain: the page said " + sResult
    + " and the move returned " + Builtin::IntToString (iMoved))
If iMoved Then
    ; WHICH KIND OF MAIN CONTENT IT IS, and the cursor moved either way.
    ;
    ; The declared case used to return early without marking anything, so on a
    ; page that declares a main region this command said "declared" and left
    ; the cursor where it was, and Q had to be pressed as well. A page that
    ; declares its main content still HAS probable main content -- the same
    ; content, only more certainly -- so it is marked and moved to like any
    ; other, and the wording says which it was.
    If sResult == "declared" Then
        SayMessage (OT_MESSAGE, "Main content, declared")
    Else
        SayMessage (OT_MESSAGE, "Main content, inferred")
    EndIf
    SayLine ()
Else
    ; The mark was set but the buffer does not show it. Saying what was found is
    ; worth more than silence, and silence is what the old version gave.
    SayMessage (OT_MESSAGE, "Found, cursor not moved. " + sResult)
EndIf
EndScript


; Opens HomerView's guide. Control+F1, the key the NVDA side uses.
Script hVOpenUserGuide ()
Var
    int iExit,
    string sAnswer
hVLogLine ("hVOpenUserGuide started")
; IN HOMERVIEW'S BROWSER, NOT WHICHEVER ONE WINDOWS PREFERS.
;
; This used to be cmd /c start, which asks Windows what opens a .htm file. On a
; machine whose default is Firefox the HomerView guide opened in Firefox, where
; not one HomerView command works, because there is no debugging connection to
; it. Anything HomerView opens belongs in HomerView's own Edge.
;
; The shell is kept only for the case where the browser is not running at all,
; because a guide that will not open is worse than a guide in the wrong window,
; and the guide is exactly what somebody reaches for when nothing else works.
Let sAnswer = hVCallBridge ("openPage", c_sAppFolder + "\\HomerView.htm")
If hVXmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_STATUS, "Opening the guide")
    Return
EndIf
hVLogLine ("hVOpenUserGuide: falling back to the default browser")
Let iExit = hVShellRun ("cmd.exe /c start \"\" " + hVStringQuote (c_sAppFolder + "\\HomerView.htm"), 0, False)
SayMessage (OT_STATUS, "Opening outside HomerView")
EndScript


; What the page says about itself. Alt+M.
;
; The same fields the NVDA side reports, in the same order and with the same
; order of preference between the conventions that carry them: Open Graph
; first, then Twitter's, then Dublin Core, then the citation tags academic
; publishers use, then the document's own title and language.
;
; Where each answer came from is reported with it. A published date from a
; citation tag and one guessed from a time element are not equally trustworthy,
; and a reader deciding whether to cite the page should be told which it is.
Script hVSayMetadata ()
Var string sResult
hVLogLine ("hVSayMetadata started")
SayMessage (OT_STATUS, "Reading metadata")
Let sResult = hVRunScript (
    "(() => {"
    + "const meta = {};"
    + "for (const el of document.querySelectorAll('meta[name],meta[property]')) {"
    + "  const k = (el.getAttribute('name') || el.getAttribute('property') || '').toLowerCase();"
    + "  const v = (el.getAttribute('content') || '').trim();"
    + "  if (k && v && !meta[k]) meta[k] = v;"
    + "}"
    + "const fields = ["
    + "  ['Title', ['og:title','twitter:title','dc.title','citation_title']],"
    + "  ['Site', ['og:site_name','application-name','apple-mobile-web-app-title']],"
    + "  ['Author', ['author','article:author','dc.creator','citation_author','twitter:creator']],"
    + "  ['Publisher', ['publisher','dc.publisher','citation_journal_title']],"
    + "  ['Published', ['article:published_time','datepublished','dc.date','date','citation_publication_date','og:updated_time']],"
    + "  ['Modified', ['article:modified_time','datemodified','last-modified','dc.modified']],"
    + "  ['Summary', ['description','og:description','twitter:description','dc.description']],"
    + "  ['Licence', ['dc.rights','rights','copyright','license']],"
    + "  ['Language', ['dc.language','content-language','og:locale']],"
    + "  ['Type', ['og:type','dc.type']],"
    + "  ['Section', ['article:section','dc.subject']],"
    + "  ['Keywords', ['keywords','news_keywords']],"
    + "  ['Built with', ['generator']]];"
    + "const l = [];"
    + "const used = new Set();"
    + "for (const [label, keys] of fields) {"
    + "  let value = '', from = '';"
    + "  for (const k of keys) { used.add(k); if (meta[k]) { value = meta[k]; from = k; break; } }"
    + "  if (!value && label === 'Title') { value = document.title; from = 'document title'; }"
    + "  if (!value && label === 'Language') {"
    + "    value = document.documentElement.getAttribute('lang') || ''; from = 'html lang'; }"
    + "  if (!value && label === 'Published') {"
    + "    const t = document.querySelector('time[datetime]');"
    + "    if (t) { value = t.getAttribute('datetime'); from = 'time element'; } }"
    + "  if (!value && label === 'Licence') {"
    + "    const a = document.querySelector('link[rel~=license]');"
    + "    if (a) { value = a.href; from = 'link rel license'; } }"
    + "  if (value) l.push(label + ': ' + value + '  [' + from + ']');"
    + "}"
    + "const extra = [];"
    + "for (const k of Object.keys(meta).sort()) {"
    + "  if (used.has(k)) continue;"
    + "  if (/^(viewport|theme-color|msapplication|format-detection)/.test(k)) continue;"
    + "  extra.push('  ' + k + ': ' + meta[k]);"
    + "}"
    + "if (!l.length && !extra.length) return 'This page says nothing about itself.';"
    + "if (extra.length) { l.push(''); l.push('--- everything else it declares ---'); }"
    + "return l.concat(extra).join('\\n');"
    + "})()")
If sResult != "" Then
    hVSayOrShow (sResult)
Else
    hVLogLine ("nothing to show: runScript returned nothing")
EndIf
EndScript


; Marks where a selection starts. F8.
;
; F8 AND SHIFT+F8 AS VIRTUAL KEYS, at his decision. JAWS's own F8 is Select
; Entire Element, and it keeps that key everywhere except inside a web page,
; where these two are the pair EdSharp users reach for.
;
; A PAIR, NOT A DRAG: press F8 where the passage begins, move by whatever means
; suits -- arrows, headings, find -- and press Shift+F8 where it ends. That is
; how EdSharp and Lbc do it, and it is the only way to select a passage longer
; than a screen without holding a key down.
;
; SaveCurrentLocation and SelectFromSavedLocationToCurrent are Freedom
; Scientific's own, from JAWS 16.
Script hVStartSelection ()
hVLogLine ("hVStartSelection started")
; SaveCurrentLocation DID NOT DO IT. Its own description says it remembers the
; cursor's location for a later selection, and in an edit control it does --
; but in a VIRTUAL BUFFER the mechanism JAWS itself uses is a TEMPORARY
; PLACEMARKER, which is why his own sequence for this is Control+Windows+K and
; then Insert+Space, M. Those are two shipped scripts, so this performs them.
; A pair of keys instead of a keystroke and then a layer.
; THE SHIPPED SCRIPT SPEAKS FOR ITSELF, AND ITS WORDS WERE WINNING.
;
; DefineATempPlaceMarker announces its own placemarker, so asking for "Start
; Selection" afterwards produced two messages and he heard the wrong one.
; Speech is muted around the call and turned back on for ours.
SpeechOff ()
PerformScript DefineATempPlaceMarker ()
SpeechOn ()
SayMessage (OT_MESSAGE, "Start Selection")
EndScript


; Speaks the whole page without moving anything. Alt+F8.
;
; NOT SAY ALL, AND THE DIFFERENCE IS THE POINT. JAWS's Say All speaks the
; VIRTUAL view from wherever the cursor happens to be, and leaves the cursor
; further down the document. This speaks the page's OWN text -- what Control+A
; would select -- from the top, and does not touch the cursor at all, so
; whatever you were reading is still where you left it.
;
; The virtual view is close to the page but not the same: it puts a link on a
; line of its own, among other differences. Copy All and Read All both take the
; browser's text, so the two commands, and both screen readers, deliver the
; same characters.
Script hVReadAll ()
Var string sAnswer, string sText
hVLogLine ("hVReadAll started")
Let sAnswer = hVCallBridge ("pageText", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sText = hVXmlValue (sAnswer, "/root/value")
If sText == "" Then
    SayMessage (OT_ERROR, "No text")
    Return
EndIf
hVLogLine ("hVReadAll speaking " + Builtin::IntToString (Builtin::StringLength (sText)) + " characters")
SayMessage (OT_MESSAGE, sText)
EndScript


; Opens a document of any kind in HomerView's browser. Control+O.
;
; CONTROL+O IS TAKEN ON THE PROJECT'S OWN TERMS: a browser key may be taken
; only where HomerView does everything the browser did with it and more. Edge's
; Control+O opens a file the browser can already display. This opens those AND
; a Word document, a PDF, a spreadsheet, a slide deck or an ebook, by converting
; it to a web page first -- after which every other HomerView command works on
; it, which the browser's own Open cannot offer.
;
; The converters are FOUND, not shipped: pandoc and 2htm are looked for where
; they already live, and the command says plainly when neither is there.
Script hVOpenDocument ()
Var
    string sAnswer, string sPath
hVLogLine ("hVOpenDocument started")
Let sAnswer = hVCallBridge ("openDialog", "Open a document in HomerView\tDocuments|*.htm;*.html;*.txt;*.md;*.docx;*.doc;*.pdf;*.epub;*.rtf;*.odt;*.pptx;*.xlsx;*.csv|All files|*.*\t")
Let sPath = hVXmlValue (sAnswer, "/root/value")
If sPath == "" Then
    hVLogLine ("hVOpenDocument: no file was chosen")
    Return
EndIf
; "CONVERTING" ONLY WHEN SOMETHING IS CONVERTED.
;
; A web page, a text file, an XML or SVG file is opened AS IT IS: no
; converter runs and no temporary copy is made. Saying "Converting" over
; that is a claim about work that is not happening, and the reader has no
; way to tell the difference between a message that is wrong and one that
; is about to be followed by a wait.
; THE NAME FIRST, THEN WHAT IS HAPPENING TO THE FILE.
;
; The echo names the command, as every other command now does. "Converting" is
; kept after it because it says something the name does not: that this file
; needs work before it can be read, so a wait is expected. A web page gets the
; name alone and no promise of work that is not happening.
SayMessage (OT_STATUS, "Open Document")
If hVNeedsConverting (sPath) Then
    SayMessage (OT_STATUS, "Converting")
EndIf
; Converting a large PDF can take a minute, and waiting for it here held all
; of JAWS. Started instead; bridgePoll says "Opened in HomerView" when it is.
; THE SECOND ARGUMENT IS A BRIDGE COMMAND, NOT A SCRIPT NAME.
; The hV rename reached it and made it "hVOpenDocument", which no case in
; the helper matches -- every Control+O answered "unknown command" for
; every file type. I repaired the FIRST argument of these calls at the time
; and did not check the second.
If hVStartBridge ("openDocument", "openDocument", sPath) == False Then
    Return
EndIf
EndScript


; Saves the page in whatever format the chosen name asks for. Control+S.
;
; Edge's Control+S saves a page as html or as a single file. This saves it that
; way and also as anything pandoc can write -- Word, OpenDocument, Markdown,
; ebook -- chosen simply by naming the file, which is more than the browser
; offers and is why the key is taken.
Script hVSavePage ()
Var
    string sAnswer, string sPath
hVLogLine ("hVSavePage started")
Let sAnswer = hVCallBridge ("saveDialog", "Save this page as\tWeb page|*.htm|Word document|*.docx|OpenDocument text|*.odt|Markdown|*.md|EPUB ebook|*.epub|All files|*.*\t")
Let sPath = hVXmlValue (sAnswer, "/root/value")
If sPath == "" Then
    hVLogLine ("hVSavePage: no file was chosen")
    Return
EndIf
SayMessage (OT_STATUS, "Saving")
Let sAnswer = hVCallBridge ("savePage", sPath)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    hVSayOrShow (hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, hVXmlValue (sAnswer, "/root/value"))
EndScript


; Fetches the files a page links to. Alt+Shift+W, EdSharp's key for it.
;
; NOT THE BROWSER'S OWN DOWNLOAD. The browser is asked what it KNOWS -- the
; links after script has run, its cookies for that address, its user agent --
; and the helper then makes the request itself, carrying all of that plus the
; Referer and the Sec-Fetch headers a click would have produced. Sites gate
; files on exactly those, and a request without them comes back as a refusal or
; a login page rather than the file.
;
; Two steps because the reader chooses: the first says what kinds are there and
; fills in the ones worth having, the second fetches. Page addresses and script
; assets are listed but not filled in, since they are numerous and rarely
; wanted -- typing html gets them anyway.
; Opens this page's folder in File Explorer. Alt+Shift+F.
;
; The Alt+Shift family is the one that ACTS ON THE WHOLE PAGE and leaves
; something behind: W fetches its files, P copies its links, and F now opens
; the folder where W put them. F for Folder, and it sits beside the command
; whose output it exists to show.
;
; NOTHING IS CREATED HERE. If nothing has been saved from this page there is
; no folder, and the answer says so rather than opening an empty one.
Script hVOpenPageFolder ()
Var
    string sAnswer
hVLogLine ("hVOpenPageFolder started")
Let sAnswer = hVCallBridge ("openPageFolder", "")
If sAnswer == "" Then
    Return
EndIf
If hVXmlValue (sAnswer, "/root/error") != "" Then
    hVSayOrShow (hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, hVXmlValue (sAnswer, "/root/value"))
EndScript


; THE HELPER'S LISTS ARE SEPARATED BY A VERTICAL BAR, NOT BY \7.
;
; \7 is what JAWS uses in its own menu strings, and copying it here broke Web
; Download completely: the helper's answer is turned into XML, XML FORBIDS
; CONTROL CHARACTERS, MSXML rejected the document, and every field came back
; empty -- "0 fetched, 0 failed" on a page with 17 files ready to download.
; The menu below still uses \7, because that string never leaves this file.

Script hVDownloadFiles ()
Var
    int iFailed, int iGot, int iOk, int iWhich,
    string sAnswer, string sFolder, string sKinds, string sName,
    string sNames, string sSummary, string sTrouble
hVLogLine ("hVDownloadFiles started")
SayMessage (OT_STATUS, "Scanning links")
Let sAnswer = hVCallBridge ("downloadScan", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sSummary = hVXmlValue (sAnswer, "/root/value")
If sSummary == "" Then
    hVLogLine ("hVDownloadFiles: nothing came back from the scan")
    Return
EndIf
Let sKinds = Builtin::StringSegment (sSummary, "\t", 2)
Let iOk = Builtin::InputBox ("Which kinds? " + Builtin::StringSegment (sSummary, "\t", 1),
    "Web Download", sKinds)
If iOk == 0 Then
    Return
EndIf
If sKinds == "" Then
    SayMessage (OT_ERROR, "Nothing chosen")
    Return
EndIf
Let sAnswer = hVCallBridge ("downloadList", sKinds)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sSummary = hVXmlValue (sAnswer, "/root/value")
Let sFolder = Builtin::StringSegment (sSummary, "\t", 2)
Let sNames = Builtin::StringSegment (sSummary, "\t", 3)
; ONE AT A TIME, EACH NAME SPOKEN BEFORE IT IS FETCHED.
;
; urlFido's way, and the reason it reads well: the name goes by, and silence
; after it means it arrived. Only a failure says anything more, so a run of
; twenty files is twenty names and nothing else, and the one that went wrong
; stands out by being the only thing followed by a word.
; The loop ends when the list runs out, rather than counting to a number.
; StringToInt has never been compiled in this project, and a first use of an
; unproven function belongs in a batch where a failure blocks nothing -- not in
; the middle of a command he is waiting to test.
Let iWhich = 1
Let iGot = 0
Let iFailed = 0
Let sTrouble = ""
Let sName = Builtin::StringSegment (sNames, "|", iWhich)
While sName != ""
    SayMessage (OT_MESSAGE, sName)
    Let sAnswer = hVCallBridge ("downloadOne", Builtin::IntToString (iWhich))
    If hVXmlValue (sAnswer, "/root/error") != "" Then
        Let iFailed = iFailed + 1
        Let sTrouble = sTrouble + sName + ": " + hVXmlValue (sAnswer, "/root/error") + "\r\n"
        SayMessage (OT_ERROR, "Error. " + hVXmlValue (sAnswer, "/root/error"))
    Else
        Let iGot = iGot + 1
    EndIf
    Let iWhich = iWhich + 1
    Let sName = Builtin::StringSegment (sNames, "|", iWhich)
EndWhile
; A MESSAGE BOX AT THE END, because a spoken summary after twenty spoken names
; is one more thing said and gone, and this is the part worth reading twice.
Let sSummary = Builtin::IntToString (iGot) + " of " + Builtin::IntToString (iGot + iFailed)
    + " files fetched into" + "\r\n" + sFolder
If iFailed > 0 Then
    Let sSummary = sSummary + "\r\n\r\n" + Builtin::IntToString (iFailed)
        + " did not come:" + "\r\n" + sTrouble
EndIf
hVLogLine ("hVDownloadFiles: " + Builtin::IntToString (iGot) + " fetched, "
    + Builtin::IntToString (iFailed) + " failed")
MessageBox (sSummary)
EndScript


; Searches backwards for text. Control+Shift+F.
;
; CONTROL+F IS LEFT ALONE. JAWS's own find is forward only and it is a good
; find; what JAWS has no key for is going the other way, so this is the missing
; half rather than a replacement.
Script hVFindBackwards ()
Var
    int iOk,
    string sNeedle
hVLogLine ("hVFindBackwards started")
Let sNeedle = gsLastFind
Let iOk = Builtin::InputBox ("Find backwards", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
hVFindAndMark ("plain", sNeedle, True)
EndScript


; Searches forward for a regular expression. Control+F3.
Script hVFindByPattern ()
Var
    int iOk,
    string sNeedle
hVLogLine ("hVFindByPattern started")
Let sNeedle = gsLastFind
Let iOk = Builtin::InputBox ("Find forward with a regular expression", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
hVFindAndMark ("pattern", sNeedle, False)
EndScript


; Searches backwards for a regular expression. Control+Shift+F3.
Script hVFindByPatternBackwards ()
Var
    int iOk,
    string sNeedle
hVLogLine ("hVFindByPatternBackwards started")
Let sNeedle = gsLastFind
Let iOk = Builtin::InputBox ("Find backwards with a regular expression", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
hVFindAndMark ("pattern", sNeedle, True)
EndScript


; The next match, of whichever find was done last. F3.
Script hVFindNext ()
hVLogLine ("hVFindNext started")
hVFindAgain (False)
EndScript


; The previous match, of whichever find was done last. Shift+F3.
Script hVFindPrevious ()
hVLogLine ("hVFindPrevious started")
hVFindAgain (True)
EndScript


; Every match of a regular expression, gathered for reading. Control+Shift+E.
;
; A find moves you to matches one at a time. This is the other question: what
; are they all? Each match is separated by a form feed between blank lines, so
; they read as pages rather than as a run-on list.
Script hVExtractByPattern ()
Var
    int iOk,
    string sAnswer, string sNeedle, string sResult
hVLogLine ("hVExtractByPattern started")
Let sNeedle = gsLastFind
Let iOk = Builtin::InputBox ("Extract every match of a regular expression", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
If sNeedle == "" Then
    SayMessage (OT_ERROR, "No pattern")
    Return
EndIf
Let gsLastFind = sNeedle
Let sAnswer = hVCallBridge ("extractPattern", sNeedle)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = hVXmlValue (sAnswer, "/root/value")
If sResult == "" Then
    hVLogLine ("hVExtractByPattern: nothing came back")
    Return
EndIf
; NAMED ON ITS FIRST LINE, the same practice as the generated tabs.
; A virtual view has no title bar for JAWSKey+T to read, so the first
; line IS the title -- and a reader who lands in a buffer of text with
; no heading has to work out what they are looking at.
hVSayVirtual ("Pattern Matches" + "\r\n\r\n" + sResult)
EndScript


; The Quick Start. Alt+Shift+F1.
Script hVOpenQuickStart ()
hVOpenOwnDocument ("ReadMe.htm", "the Quick Start")
EndScript


; What has changed, release by release. Shift+F1.
Script hVShowHistory ()
hVOpenOwnDocument ("History.htm", "the history of changes")
EndScript


; The notes for anyone working on HomerView itself. Control+Shift+F1.
Script hVOpenDeveloperNotes ()
hVOpenOwnDocument ("Developer.htm", "the developer notes")
EndScript


; What HomerView is for, in its own words. No key; on the menu.
Script hVOpenAnnouncement ()
hVOpenOwnDocument ("Announce.htm", "the project announcement")
EndScript


; This session's log, opened to read rather than copied to send. Alt+Control+F1.
Script hVOpenSessionLog ()
Var
    int iExit,
    string sAnswer
hVLogLine ("hVOpenSessionLog started")
Let sAnswer = hVCallBridge ("openPage", c_sLogFile)
If hVXmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_STATUS, "Opening the log")
    Return
EndIf
Let iExit = hVShellRun ("cmd.exe /c start \"\" " + hVStringQuote (c_sLogFile), 0, False)
SayMessage (OT_STATUS, "Opening outside HomerView")
EndScript


; Which build is loaded, and where everything lives. Alt+F1.
;
; NOT A DOCUMENT, because the useful facts about a build are not in a file that
; ships with it: the version, when it was installed, and where the log is.
Script hVShowAbout ()
hVLogLine ("hVShowAbout started")
hVSayVirtual ("HomerView " + c_sVersion + " for JAWS"
    + "\r\n" + "Installed " + c_sInstalled
    + "\r\n\r\n" + "Program: " + c_sAppFolder
    + "\r\n" + "Log: " + c_sLogFile
    + "\r\n\r\n" + "Alt+JAWSKey+F10 opens the menu. Alt+Shift+H lists every key.")
EndScript


; Finds whoever can be told about this site. Alt+JAWSKey+C.
;
; A COMMAND OF ITS OWN, not a section inside an accessibility report. "Who do I
; tell" is asked at other times than "what is wrong with this page", and
; attaching it to a checker would hide it from anyone who has not just run one.
;
; Three places are looked at, as AccReporter does: the page in front of you,
; the site's home page -- because a contact link lives in a footer an article
; may not carry -- and a short list of addresses worth trying directly, which
; is how an accessibility statement is usually found at all, since most sites
; never link to theirs.
Script hVFindContacts ()
Var string sAnswer, string sResult
hVLogLine ("hVFindContacts started")
SayMessage (OT_STATUS, "Finding contacts")
Let sAnswer = hVCallBridge ("contacts", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    hVSayOrShow (hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = hVXmlValue (sAnswer, "/root/value")
If sResult == "" Then
    hVLogLine ("hVFindContacts: nothing came back")
    Return
EndIf
; NAMED ON ITS FIRST LINE, the same practice as the generated tabs.
; A virtual view has no title bar for JAWSKey+T to read, so the first
; line IS the title -- and a reader who lands in a buffer of text with
; no heading has to work out what they are looking at.
hVSayVirtual ("Publisher Contacts" + "\r\n\r\n" + sResult)
EndScript


; Lists every name, place, organisation and date the page mentions. Alt+N.
;
; A DIFFERENT WAY OF READING A PAGE. Headings tell you how a page is arranged
; and links tell you where it goes; neither tells you WHO AND WHAT it is about.
; On a long report this answers that in one keystroke, and on a page of
; deadlines the list of dates is the thing you came for.
;
; The engine is compromise, a rule-based English parser that carries no model
; and makes no network call once cached. IT GUESSES, and the report says so on
; its own first page: expect a company called a person now and then, and expect
; it to miss a name it has not seen. Presented as fact that would be worse than
; useless; presented as a starting point it is something no screen reader
; offers.
Script hVListNames ()
Var string sAnswer, string sResult
hVLogLine ("hVListNames started")
SayMessage (OT_STATUS, "Reading names")
Let sAnswer = hVCallBridge ("pageNames", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    hVSayOrShow (hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = hVXmlValue (sAnswer, "/root/value")
If sResult == "" Then
    ; A COMMAND WITH NOTHING TO REPORT MUST SAY SO. Silence here was
    ; indistinguishable from a command that never ran -- and this one has a
    ; real way to fail: it needs a language engine, which on one machine
    ; could not be loaded at all.
    hVLogLine ("hVListNames: nothing came back")
    SayMessage (OT_MESSAGE, "No names were found on this page")
    Return
EndIf
; Spoken, not shown: the list has just been opened in a tab, and a buffer in
; front of it would take the focus away from the thing itself.
SayMessage (OT_MESSAGE, sResult)
EndScript


; Says the names of the open tabs, and moves nothing. Shift+F4.
;
; Tab List shows a buffer of links and takes focus, which is right when the
; point is to GO somewhere. This is the other question -- what is open -- and
; answering it should cost nothing. F4 itself belongs to Edge's address bar, so
; the shifted key takes the idea without taking the browser's key.
Script hVSayTabNames ()
Var
    int iWhich,
    string sAnswer, string sNames, string sRecord, string sSpoken
hVLogLine ("hVSayTabNames started")
Let sAnswer = hVCallBridge ("tabList", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sNames = hVXmlValue (sAnswer, "/root/value")
If sNames == "" Then
    SayMessage (OT_ERROR, "No tabs")
    Return
EndIf
Let iWhich = 1
Let sRecord = Builtin::StringSegment (sNames, "|", iWhich)
While sRecord != ""
    If sSpoken == "" Then
        Let sSpoken = Builtin::StringSegment (sRecord, "\t", 2)
    Else
        Let sSpoken = sSpoken + ". " + Builtin::StringSegment (sRecord, "\t", 2)
    EndIf
    Let iWhich = iWhich + 1
    Let sRecord = Builtin::StringSegment (sNames, "|", iWhich)
EndWhile
SayMessage (OT_MESSAGE, sSpoken)
EndScript


; Says what is on the clipboard. Alt+Apostrophe.
;
; The same answer FileDir gives to the same key: "Path drop list" and then the
; paths when a file has been copied, and the text otherwise. Two of his own
; programs answering one question two ways would be a second vocabulary for one
; idea.
Script hVSayClipboard ()
Var string sAnswer, string sResult
hVLogLine ("hVSayClipboard started")
Let sAnswer = hVCallBridge ("clipboardSay", "")
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = hVXmlValue (sAnswer, "/root/value")
If sResult == "" Then
    ; SILENCE IS NOT AN ANSWER, AND HERE IT LOOKED LIKE A BROKEN KEY.
    ;
    ; This wrote a log line and returned without speaking, so an EMPTY
    ; CLIPBOARD was indistinguishable from a command that never ran -- and a
    ; tester reported Alt+Apostrophe "not working" on a machine where the key
    ; map was demonstrably fine. A command that has nothing to report must SAY
    ; that it has nothing to report.
    ; "BLANK" IS THE JAWS CONVENTION for nothing to read, so this says that
    ; rather than a sentence of its own.
    ;
    ; AND THE RAW ANSWER IS LOGGED, because this case is not yet understood.
    ; The helper handles a file drop list explicitly: it answers "Path drop
    ; list" and the path, which is what JAWS itself says in a folder window. So
    ; after the log command there SHOULD have been something to read, and a
    ; tester heard nothing. Either the answer never arrived or it did not
    ; survive parsing, and the length and opening characters say which WITHOUT
    ; another round trip to him.
    hVLogLine ("hVSayClipboard: no value; the answer was "
        + Builtin::IntToString (Builtin::StringLength (sAnswer))
        + " characters: " + Builtin::SubString (sAnswer, 1, 120))
    SayMessage (OT_MESSAGE, "Blank")
    Return
EndIf
hVSayOrShow (sResult)
EndScript


; Saves the clipboard to a text file, proposing the last name used.
; Control+Apostrophe.
Script hVSaveClipboard ()
Var
    string sAnswer, string sPath
hVLogLine ("hVSaveClipboard started")
; A REAL SAVE-AS DIALOG, not a box to type a path into.
;
; InputBox asked for a path and gave no way to look for one. The helper shows
; the CLASSIC Windows dialog -- the old GetSaveFileName one, not the modern
; Common Item Dialog -- because that is the one with a folder tree that can be
; walked and a tab order that goes where you expect.
Let sAnswer = hVCallBridge ("saveDialog", "Save the clipboard as\tText files|*.txt|All files|*.*\t" + gsClipboardFile)
Let sPath = hVXmlValue (sAnswer, "/root/value")
If sPath == "" Then
    hVLogLine ("hVSaveClipboard: no file was chosen")
    Return
EndIf
Let gsClipboardFile = sPath
Let sAnswer = hVCallBridge ("clipboardToFile", sPath)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, hVXmlValue (sAnswer, "/root/value"))
EndScript


; Every HomerView command and its key. Alt+Shift+H, the key the NVDA side uses.
;
; Not a list of what is bound, which JAWS gives on Insert+H, but a list of what
; HomerView has — including the commands with no key at all, which are the ones
; a person cannot otherwise find.
; Every command and its key, and every one of them a link.
;
; JAWS's own Hot Key Help renders each entry as a link so a command can be run
; from the list rather than remembered, and UserBufferAddLink is how: the second
; argument is a FUNCTION NAME with its parentheses and parameters, called when
; Enter is pressed on that line. So one dispatcher takes the command name and
; performs it, and the third argument gives the link a proper name in the list
; links dialog, which is what JAWSKey+F7 shows.
;
; This is also the one place that says which build is loaded, now that the
; version has left the Alternate Menu title.
; Says what HomerView knows about itself, out loud, touching nothing.
;
; THIS EXISTS BECAUSE THE LOG WAS NOT ENOUGH. A tester's commands did nothing,
; said nothing, and left NO LOG ENTRY, so every round of debugging began by
; asking him to find files and read them over the phone -- and each round cost
; him an evening and told us almost nothing.
;
; So this reports the four things that decide whether anything can work, IN
; SPEECH, WITHOUT WRITING A LOG AND WITHOUT CALLING THE BRIDGE. If the scripts
; are loaded at all, this SPEAKS -- which is itself the first fact worth having.
Script hVSayDiagnostics ()
Var
    object oFileSystem,
    string sText
SayMessage (OT_MESSAGE, "HomerView diagnostics")
Let sText = "Version " + c_sVersion + ". "
Let oFileSystem = Builtin::CreateObjectEx (c_sFileSystemProgId, False)
If oFileSystem.FileExists (c_sBridgePath) Then
    Let sText = sText + "The helper program is there. "
Else
    Let sText = sText + "THE HELPER PROGRAM IS MISSING at " + c_sBridgePath + ". "
EndIf
If oFileSystem.FolderExists (oFileSystem.GetParentFolderName (c_sLogFile)) Then
    Let sText = sText + "The log folder is there. "
Else
    Let sText = sText + "THE LOG FOLDER IS MISSING at " + c_sLogFile + ". "
EndIf
If oFileSystem.FileExists (c_sAppFolder + "\\Start.htm") Then
    Let sText = sText + "The start page is installed. "
Else
    Let sText = sText + "The start page is NOT installed in " + c_sAppFolder + ". "
EndIf
; THE ONE FACT THAT DIFFERS BETWEEN THE TWO MACHINES WE HAVE COMPARED.
;
; A user copy of default.jss replaces the one JAWS ships. HomerView is chained
; through MyExtensions, which the FACTORY default file chains -- so a
; replacement decides whether these scripts load at all, whether a name of
; theirs is shadowed, and whether the set is loaded twice and therefore keeps
; TWO SETS OF GLOBALS. That last one shows up as a menu that never remembers
; the last item chosen, which is exactly what one machine reported and the
; other never did.
; GetJAWSSettingsDirectory: "the JAWS drive and settings directory without a
; trailing backslash", no parameters. Read in FSDN rather than assumed, and
; it is the folder the installer writes these scripts into.
If oFileSystem.FileExists (Builtin::GetJAWSSettingsDirectory () + "\\default.jss") Then
    Let sText = sText + "THIS MACHINE HAS ITS OWN default.jss, which replaces the one JAWS ships. "
Else
    Let sText = sText + "No custom default.jss, so JAWS uses its own. "
EndIf
Let sText = sText + "Answers go to " + c_sAnswerPath + "."
hVSayOrShow (sText)
hVLogLine ("hVSayDiagnostics: " + sText)
EndScript


Script hVHotKeyHelp ()
Var
    int iActivated, int iAdded
Builtin::UserBufferDeactivate ()
Builtin::UserBufferClear ()
Let iAdded = Builtin::UserBufferAddText ("HomerView " + c_sVersion + " for JAWS, installed " + c_sInstalled)
Let iAdded = Builtin::UserBufferAddText ("")
; THE POINTER TO JAWS'S OWN HELP, BECAUSE THAT IS THE REAL INTEGRATION.
;
; Every one of these keys has a Synopsis and a Description in HomerView.jsd,
; which is what JAWS Keyboard Help reads out. So a reader who presses one of
; these keys in Keyboard Help hears HomerView describe it, in JAWS's own
; voice and by JAWS's own mechanism -- no separate convention to learn.
; Saying so here is what makes that discoverable.
Let iAdded = Builtin::UserBufferAddText ("In JAWS Keyboard Help, JAWSKey+1, press any key below to hear what it does.")
Let iAdded = Builtin::UserBufferAddText ("")
Let iAdded = Builtin::UserBufferAddText ("Anywhere:")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+H   Launch or return to HomerView", "hVHomerViewLink (\"hVLaunchHomerView\")", "Launch HomerView")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+F10 Alternate Menu, every command in one list", "hVHomerViewLink (\"hVShowHomerViewMenu\")", "Alternate Menu")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+A   Check the page with axe and save a report", "hVHomerViewLink (\"hVCheckAccessibility\")", "Check Accessibility with axe")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+D   Close a cookie banner or consent wall", "hVHomerViewLink (\"hVDismissDialog\")", "Dismiss Dialog")
Let iAdded = UserBufferAddLink ("  Alt+Shift+H     This summary", "hVHomerViewLink (\"hVHotKeyHelp\")", "Hotkey Summary")
Let iAdded = UserBufferAddLink ("  Shift+F4        Say the names of the open tabs", "hVHomerViewLink (\"hVSayTabNames\")", "Tab Names")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+L   Copy the log file to the clipboard", "hVHomerViewLink (\"hVCopyLogToClipboard\")", "Log to Clipboard")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+Q   Say what HomerView knows about itself", "hVHomerViewLink (\"hVSayDiagnostics\")", "Diagnostics")
Let iAdded = Builtin::UserBufferAddText ("")
Let iAdded = Builtin::UserBufferAddText ("On a web page:")
Let iAdded = UserBufferAddLink ("  Shift+Q         Move to the main content, declared or not", "hVHomerViewLink (\"hVMoveToProbableMain\")", "Jump to Probable Main")
Let iAdded = UserBufferAddLink ("  Alt+L           Where this link goes, and its address", "hVHomerViewLink (\"hVDescribeLinkTarget\")", "Link Target")
Let iAdded = UserBufferAddLink ("  Alt+M           What the page says about itself", "hVHomerViewLink (\"hVSayMetadata\")", "Say Metadata")
Let iAdded = UserBufferAddLink ("  Alt+Shift+P     Copy every link on the page to the clipboard", "hVHomerViewLink (\"hVCopyPageLinks\")", "Page Links to Clipboard")
Let iAdded = UserBufferAddLink ("  Alt+Shift+W     Fetch the files this page links to", "hVHomerViewLink (\"hVDownloadFiles\")", "Web Download")
Let iAdded = UserBufferAddLink ("  Alt+Shift+F     Open this page's folder", "hVHomerViewLink (\"hVOpenPageFolder\")", "Page Folder")
Let iAdded = UserBufferAddLink ("  Control+O       Open a document as a page", "hVHomerViewLink (\"hVOpenDocument\")", "Open Document")
Let iAdded = UserBufferAddLink ("  Control+S       Save this page in any format", "hVHomerViewLink (\"hVSavePage\")", "Save Page")
Let iAdded = UserBufferAddLink ("  Control+F1      The HomerView guide", "hVHomerViewLink (\"hVOpenUserGuide\")", "User Guide")
Let iAdded = UserBufferAddLink ("  Alt+Shift+F1    The Quick Start", "hVHomerViewLink (\"hVOpenQuickStart\")", "Quick Start")
Let iAdded = UserBufferAddLink ("  Shift+F1        What changed in each release", "hVHomerViewLink (\"hVShowHistory\")", "History of Changes")
Let iAdded = UserBufferAddLink ("  Control+Shift+F1 Notes for developers", "hVHomerViewLink (\"hVOpenDeveloperNotes\")", "Developer Notes")
Let iAdded = UserBufferAddLink ("  Alt+Control+F1  This session's log, to read", "hVHomerViewLink (\"hVOpenSessionLog\")", "Session Log")
Let iAdded = UserBufferAddLink ("  Alt+F1          Which build is loaded", "hVHomerViewLink (\"hVShowAbout\")", "About HomerView")
Let iAdded = UserBufferAddLink ("  Control+Shift+F Find backwards", "hVHomerViewLink (\"hVFindBackwards\")", "Reverse Find for Text")
Let iAdded = UserBufferAddLink ("  Control+F3      Find forward with a pattern", "hVHomerViewLink (\"hVFindByPattern\")", "Forward Find with Regular Expression")
Let iAdded = UserBufferAddLink ("  Control+Shift+F3 Find backwards with a pattern", "hVHomerViewLink (\"hVFindByPatternBackwards\")", "Reverse Find with Regular Expression")
Let iAdded = UserBufferAddLink ("  F3              The next match", "hVHomerViewLink (\"hVFindNext\")", "Forward Find Again")
Let iAdded = UserBufferAddLink ("  Shift+F3        The previous match", "hVHomerViewLink (\"hVFindPrevious\")", "Reverse Find Again")
Let iAdded = UserBufferAddLink ("  Control+Shift+E Gather every match of a pattern", "hVHomerViewLink (\"hVExtractByPattern\")", "Extract with Regular Expression")
Let iAdded = UserBufferAddLink ("  Shift+F9        Extract the main content into a tab", "hVHomerViewLink (\"hVExtractMainContent\")", "Extract Main Content")
Let iAdded = UserBufferAddLink ("  Alt+Apostrophe  Say what is on the clipboard", "hVHomerViewLink (\"hVSayClipboard\")", "Say Clipboard")
Let iAdded = UserBufferAddLink ("  Control+Apostrophe Save the clipboard to a file", "hVHomerViewLink (\"hVSaveClipboard\")", "Save Clipboard")
Let iAdded = UserBufferAddLink ("  Control+Shift+Apostrophe Add the clipboard to a file", "hVHomerViewLink (\"hVAppendClipboard\")", "Append Clipboard")
Let iAdded = UserBufferAddLink ("  Alt+Shift+Apostrophe Empty the clipboard", "hVHomerViewLink (\"hVClearClipboard\")", "Clear Clipboard")
Let iAdded = UserBufferAddLink ("  F8              Start a selection here", "hVHomerViewLink (\"hVStartSelection\")", "Start Selection")
Let iAdded = UserBufferAddLink ("  Shift+F8        Select from there to here", "hVHomerViewLink (\"hVCompleteSelection\")", "Complete Selection")
Let iAdded = UserBufferAddLink ("  Control+C       Copy the selection, or this line", "hVHomerViewLink (\"hVCopySelection\")", "Copy Selection")
Let iAdded = UserBufferAddLink ("  Alt+C           Add it to what is on the clipboard", "hVHomerViewLink (\"hVCopyAppend\")", "Copy Append")
Let iAdded = UserBufferAddLink ("  Control+F8      Put the whole page on the clipboard", "hVHomerViewLink (\"hVCopyAll\")", "Copy All")
Let iAdded = UserBufferAddLink ("  Alt+F8          Speak the whole page, cursor unmoved", "hVHomerViewLink (\"hVReadAll\")", "Read All")
Let iAdded = UserBufferAddLink ("  Alt+N           List the names, places and dates", "hVHomerViewLink (\"hVListNames\")", "List Names")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+C   Find who to tell about this site", "hVHomerViewLink (\"hVFindContacts\")", "Find Contacts")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+I   Check the page with IBM Equal Access", "hVHomerViewLink (\"hVCheckAccessibilityIbm\")", "Check Accessibility with IBM")
Let iAdded = Builtin::UserBufferAddText ("")
Let iAdded = Builtin::UserBufferAddText ("On the Alternate Menu only:")
Let iAdded = UserBufferAddLink ("  The open tabs, by name and address", "hVHomerViewLink (\"hVListTabs\")", "Tab List")
Let iAdded = Builtin::UserBufferAddText ("")
Let iAdded = Builtin::UserBufferAddText ("JAWS already does these, so HomerView does not: the element lists on")
Let iAdded = Builtin::UserBufferAddText ("JAWSKey+F5, F6 and F7, the main region on Q, the address on JAWSKey+A,")
Let iAdded = Builtin::UserBufferAddText ("find on Control+F, and the page summary on JAWSKey+F3.")
Let iActivated = Builtin::UserBufferActivate ()
JAWSTopOfFile ()
SayAll ()
hVLogLine ("hVHotKeyHelp: last add " + Builtin::IntToString (iAdded) + ", activated " + Builtin::IntToString (iActivated))
EndScript


; The Alternate Menu, on Alt+JAWSKey+F10, the key it has on the NVDA side.
;
; Every command in one list, whether or not it has a key of its own. Silence is
; the worst failure mode this project has: a command out of scope is
; indistinguishable from a broken one, and a command nobody can find is
; indistinguishable from a command that does not exist. One key that always
; works answers both.
;
; It is not a keystroke layer. A layer takes a key and then waits for another,
; and it hides what it can do until you are already inside it. This is a list
; you can arrow through and read, which is the same thing a menu has always
; been.
;
; Not sorted, because the order here puts what is used most at the top rather
; than what starts with A.
Script hVShowHomerViewMenu ()
Var
    int bOnPage, int iChoice, int iKept, int iRecord,
    string sApp, string sItems, string sKept, string sRecord, string sTable
; ONE TABLE, AND THE INDEX PICKS FROM IT.
;
; This used to build the list in one place and then decide what to run by
; matching WORDS from the chosen line against a chain of branches. That is a
; correspondence maintained by hand and by luck, and it broke exactly as you
; would expect: "Check Accessibility with IBM" contains "Check Accessibility",
; the axe branch came first, and the IBM command silently ran axe.
;
; Now each row holds the line the user reads and the script it runs, separated
; by a tab, in one place. The dialog returns the row NUMBER, that number picks
; the row, and the second field of the row is the script. There is nothing to
; match and nothing to keep in step: a row cannot disagree with itself.
;
; PerformScriptByName takes the name as a string, so no chain of branches is
; needed at all. FSDN documents it with a worked example.
Let sTable = "About HomerView, Which build is loaded and where everything lives. (Alt+F1)\thVShowAbout\tA"
    + "\7" + "Append Clipboard, Adds the clipboard to the end of a text file. (Control+Shift+Apostrophe)\thVAppendClipboard\tA"
    + "\7" + "Check Accessibility with axe, Tests the page with Deque axe-core and saves a report. (Alt+JAWSKey+A)\thVCheckAccessibility\tP"
    + "\7" + "Check Accessibility with IBM, Runs IBM Equal Access and saves every format to Downloads. (Alt+JAWSKey+I)\thVCheckAccessibilityIbm\tP"
    + "\7" + "Clear Clipboard, Empties the clipboard so an append starts afresh. (Alt+Shift+Apostrophe)\thVClearClipboard\tA"
    + "\7" + "Complete Selection, Selects from where F8 was pressed to here. (Shift+F8)\thVCompleteSelection\tP"
    + "\7" + "Copy All, Puts the whole page on the clipboard. (Control+F8)\thVCopyAll\tP"
    + "\7" + "Copy Append, Adds the selection or the line to what is on the clipboard. (Alt+C)\thVCopyAppend\tA"
    + "\7" + "Copy Selection, Copies the selection, or the line under the cursor. (Control+C)\thVCopySelection\tP"
    + "\7" + "Developer Notes, Notes for anyone working on HomerView itself. (Control+Shift+F1)\thVOpenDeveloperNotes\tA"
    + "\7" + "Diagnostics, Says whether the helper, the log folder and the start page are where they should be. (Alt+JAWSKey+Q)\thVSayDiagnostics\tA"
    + "\7" + "Dismiss Dialog, Closes a cookie banner, newsletter offer or consent wall that Escape will not. (Alt+JAWSKey+D)\thVDismissDialog\tA"
    + "\7" + "Extract Main Content, Extracts the readable part of the page into a tab of its own. (Shift+F9)\thVExtractMainContent\tP"
    + "\7" + "Extract with Regular Expression, Gathers every match for reading. (Control+Shift+E)\thVExtractByPattern\tP"
    + "\7" + "Find Contacts, Finds who to tell about this site: email, accessibility statement, contact pages. (Alt+JAWSKey+C)\thVFindContacts\tP"
    + "\7" + "Forward Find Again, The next match of whichever find was done last. (F3)\thVFindNext\tP"
    + "\7" + "Forward Find with Regular Expression, Searches forward for a pattern. (Control+F3)\thVFindByPattern\tP"
    + "\7" + "History of Changes, What changed in each release. (Shift+F1)\thVShowHistory\tA"
    + "\7" + "Hot Key Help, Lists every HomerView command and its key. (Alt+Shift+H)\thVHotKeyHelp\tA"
    + "\7" + "Jump to Probable Main, Moves to the main content, whether the page declares it or not. (Shift+Q)\thVMoveToProbableMain\tP"
    + "\7" + "Launch HomerView, Launches or reconnects HomerView's copy of Microsoft Edge. (Alt+JAWSKey+H)\thVLaunchHomerView\tA"
    + "\7" + "Link Target, Says where the link under the cursor goes and shows its address. (Alt+L)\thVDescribeLinkTarget\tP"
    + "\7" + "List Names, Lists the people, places, organisations and dates a page mentions. (Alt+N)\thVListNames\tP"
    + "\7" + "Log to Clipboard, Puts the HomerView log on the clipboard, ready to attach to a message. (Alt+JAWSKey+L)\thVCopyLogToClipboard\tA"
    + "\7" + "Open Document, Opens a Word file, PDF, ebook or spreadsheet as a page. (Control+O)\thVOpenDocument\tA"
    + "\7" + "Page Folder, Opens this page's folder in File Explorer, to browse what was saved from it. (Alt+Shift+F)\thVOpenPageFolder\tP"
    + "\7" + "Page Links to Clipboard, Copies the text and address of every link on the page. (Alt+Shift+P)\thVCopyPageLinks\tP"
    + "\7" + "Project Announcement, What HomerView is for, in its own words.\thVOpenAnnouncement\tA"
    + "\7" + "Quick Start, The short introduction to HomerView. (Alt+Shift+F1)\thVOpenQuickStart\tA"
    + "\7" + "Read All, Speaks the whole page from the top without moving the cursor. (Alt+F8)\thVReadAll\tP"
    + "\7" + "Reverse Find Again, The previous match of whichever find was done last. (Shift+F3)\thVFindPrevious\tP"
    + "\7" + "Reverse Find for Text, Searches backwards for text, which JAWS has no key for. (Control+Shift+F)\thVFindBackwards\tP"
    + "\7" + "Reverse Find with Regular Expression, Searches backwards for a pattern. (Control+Shift+F3)\thVFindByPatternBackwards\tP"
    + "\7" + "Save Clipboard, Saves the clipboard to a text file. (Control+Apostrophe)\thVSaveClipboard\tA"
    + "\7" + "Save Page, Saves this page as html, Word, Markdown or an ebook. (Control+S)\thVSavePage\tP"
    + "\7" + "Say Clipboard, Says what is on the clipboard, paths or text. (Alt+Apostrophe)\thVSayClipboard\tA"
    + "\7" + "Say Metadata, Shows what the page says about itself. (Alt+M)\thVSayMetadata\tP"
    + "\7" + "Session Log, Opens this session's log to read. (Alt+Control+F1)\thVOpenSessionLog\tA"
    + "\7" + "Start Selection, Marks where a selection begins, to be finished with Shift+F8. (F8)\thVStartSelection\tP"
    + "\7" + "Tab List, Lists the open tabs by name and address.\thVListTabs\tA"
    + "\7" + "Tab Names, Says the names of the open tabs without moving anywhere. (Shift+F4)\thVSayTabNames\tA"
    + "\7" + "User Guide, Opens the HomerView guide. (Control+F1)\thVOpenUserGuide\tA"
    + "\7" + "Web Download, Fetches the files this page links to, with the browser's own cookies. (Alt+Shift+W)\thVDownloadFiles\tP"
; The list the dialog shows is the first field of every row.
; ONLY WHAT APPLIES RIGHT NOW.
;
; A menu of 44 items is a lot to hear, and most of them cannot do anything
; unless a web page is in front of you: there is no point offering "Check
; Accessibility" or "Copy Page Links" while the focus is in a folder window.
; Each row carries a third field -- P for "needs a page", A for "always" --
; and the P rows are left out when the virtual cursor is not in a document.
;
; IsVirtualPCCursor is the documented test: "Checks to see if the Virtual PC
; cursor is being used to navigate within the window with focus", TRUE when it
; is. That is exactly the condition under which a page command has a page.
;
; THE KEPT ROWS ARE COLLECTED INTO sKept AND THE CHOICE IS LOOKED UP THERE,
; because the numbers must line up with what was offered -- dispatching from
; the full table after showing a shorter list would run the wrong command.
; THE TEST IS "AM I IN A BROWSER", NOT "IS THE VIRTUAL CURSOR ON".
;
; IsVirtualPCCursor alone was too strict and hid working commands: it is FALSE
; in forms mode, and false while the focus sits in the address bar or a text
; box -- yet Web Download, Copy All and the scans all work perfectly well from
; there. He opened the menu in Edge and found Web Download missing, which is
; exactly this.
;
; GetAppFileNameWithoutExtension names the application whatever the cursor is
; doing, so the page commands are offered whenever a browser is in front. The
; virtual cursor still counts on its own, for a document that is not Edge.
Let bOnPage = Builtin::IsVirtualPCCursor ()
Let sApp = Builtin::StringLower (GetAppFileNameWithoutExtension ())
; ONE LINE PER If, which is this project's rule and also what the JSL wants:
; a condition split across lines counted as an If with no EndIf.
If Builtin::StringContains (sApp, "edge") Then
    Let bOnPage = True
EndIf
If Builtin::StringContains (sApp, "chrome") Then
    Let bOnPage = True
EndIf
If Builtin::StringContains (sApp, "firefox") Then
    Let bOnPage = True
EndIf
Let iRecord = 1
Let iKept = 0
Let sRecord = Builtin::StringSegment (sTable, "\7", iRecord)
While sRecord != ""
    If bOnPage || Builtin::StringSegment (sRecord, "\t", 3) != "P" Then
        Let iKept = iKept + 1
        If iKept == 1 Then
            Let sItems = Builtin::StringSegment (sRecord, "\t", 1)
            Let sKept = sRecord
        Else
            Let sItems = sItems + "\7" + Builtin::StringSegment (sRecord, "\t", 1)
            Let sKept = sKept + "\7" + sRecord
        EndIf
    EndIf
    Let iRecord = iRecord + 1
    Let sRecord = Builtin::StringSegment (sTable, "\7", iRecord)
EndWhile
hVLogLine ("hVShowHomerViewMenu: " + Builtin::IntToString (iKept) + " of "
    + Builtin::IntToString (iRecord - 1) + " commands apply here; on a page = "
    + Builtin::IntToString (bOnPage) + ", application " + sApp)
hVLogLine ("hVShowHomerViewMenu: offering the menu")
Let iChoice = hVDialogPick ("HomerView", sItems)
If iChoice == 0 Then
    Return
EndIf
Let sRecord = Builtin::StringSegment (sKept, "\7", iChoice)
hVLogLine ("menu row " + Builtin::IntToString (iChoice) + " runs " + Builtin::StringSegment (sRecord, "\t", 2))
PerformScriptByName (Builtin::StringSegment (sRecord, "\t", 2))
EndScript


; What a link in the Hotkey Summary calls.
;
; Named by UserBufferAddLink rather than called anywhere in this file, so the
; compiler cannot check it and the forward-reference rule does not apply. It is
; placed last because it performs every script, and it logs what it was asked
; for: if a link ever does nothing, the log says whether this was reached at
; all, which separates a wrong link target from a broken command.
;
; The buffer is dismissed first. A command that shows its own result would
; otherwise write into a viewer that is still trapping keys.
; What a link in the tab list calls: the tab it names is brought to the front.
;
; Named by UserBufferAddLink rather than called anywhere, so the compiler
; cannot check it -- which is what check 15 is for.
Void Function hVHomerViewTab (string sId)
Var string sAnswer
hVLogLine ("hVHomerViewTab asked for " + sId)
Builtin::UserBufferDeactivate ()
Let sAnswer = hVCallBridge ("activate", sId)
If hVXmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, hVXmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, "Going there")
EndFunction


Void Function hVHomerViewLink (string sName)
hVLogLine ("hVHomerViewLink asked for " + sName)
Builtin::UserBufferDeactivate ()
; The chain of branches that used to be here said the same thing twenty times.
; PerformScriptByName takes the name as a string, so the link's own target is
; the answer and there is nothing to keep in step.
PerformScriptByName (sName)
EndFunction

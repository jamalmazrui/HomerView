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
    c_sAnswerPath = "@answerPath@",
    c_sInstalled = "@installed@",
    c_sVersion = "@version@",
    c_sLogFile = "@logFile@",
    c_sAppFolder = "@appFolder@",
    c_sBridgePath = "@bridgePath@",
    c_sFileSystemProgId = "Scripting.FileSystemObject",
    c_sShellProgId = "WScript.Shell"

Globals
    int giLastPick,
    string gsClipboardFile, string gsLastFind,
    string gsLastResult, string gsLastTag, string gsLastText, string gsLogPath


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
string Function logPath ()
Var
    object oFile, object oFileSystem
If gsLogPath != "" Then
    Return gsLogPath
EndIf
Let gsLogPath = c_sLogFile
Let oFileSystem = CreateObjectEx (c_sFileSystemProgId, False)
Let oFile = oFileSystem.OpenTextFile (gsLogPath, 8, True)
oFile.WriteLine ("")
oFile.WriteLine ("==========================================================")
oFile.WriteLine ("HomerView " + c_sVersion + " for " + GetJAWSVersionInfo ())
oFile.WriteLine ("  scripts installed: " + c_sInstalled)
oFile.WriteLine ("  session started:   " + SysGetDate ("yyyy-MM-dd") + " " + SysGetTime ("HH:mm:ss"))
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
Void Function logLine (string sText)
Var
    object oFile, object oFileSystem
Let oFileSystem = CreateObjectEx (c_sFileSystemProgId, False)
Let oFile = oFileSystem.OpenTextFile (logPath (), 8, True)
; Stamped like the bridge's lines, so the two interleave into one account
; rather than one column of times and one without.
oFile.WriteLine (SysGetDate ("yyyy-MM-dd") + " " + SysGetTime ("HH:mm:ss") + "  script: " + sText)
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
int Function dialogPick (string sTitle, string sItems)
Var int iChoice
; The fourth argument is where the list opens, and giLastPick is where it was
; left. A list that always opens at the top makes the second use of a command
; as long as the first, and the commands people use are the ones they used
; last. Cancelling does not move it: changing your mind is not a choice.
Let iChoice = DlgSelectItemInList (sItems, sTitle, False, giLastPick)
Pause ()
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
Void Function sayVirtual (string sText)
Var
    int iActivated, int iAdded
UserBufferDeactivate ()
UserBufferClear ()
Let iAdded = UserBufferAddText (sText)
Let iActivated = UserBufferActivate ()
JAWSTopOfFile ()
SayAll ()
; Both of these return a result and both were being thrown away. Every way of
; showing a result has failed silently in turn, and each time the only thing
; missing was somebody asking whether it had worked.
logLine ("sayVirtual: added " + IntToString (iAdded) + ", activated " + IntToString (iActivated) + ", " + IntToString (StringLength (sText)) + " characters")
EndFunction


; A short sentence is SAID; anything worth examining is SHOWN.
;
; HIS POINT, and it is about what a result costs to receive. A virtual view is
; the right home for a report you want to read by line and character. It is the
; wrong home for "No links were found on this page.": that arrives as a buffer
; you must escape from, after which the line you were on has to be read again
; to find out where you are. A sentence with nothing in it to examine should
; simply be spoken.
;
; The rule is deliberately mechanical rather than a judgement made command by
; command: one line and under two hundred characters is a sentence, and
; everything else is a document.
Void Function sayOrShow (string sText)
If sText == "" Then
    Return
EndIf
If StringContains (sText, "\r\n") > 0 Then
    sayVirtual (sText)
    Return
EndIf
If StringLength (sText) > 200 Then
    sayVirtual (sText)
    Return
EndIf
logLine ("sayOrShow speaking " + IntToString (StringLength (sText)) + " characters rather than showing them")
SayMessage (OT_MESSAGE, sText)
EndFunction


; Runs a command line, hidden or shown, waiting or not, and hands back the exit
; code. Windows Script Host is registered on every Windows machine, so nothing
; of ours has to be.
int Function shellRun (string sCommandLine, int iWindowStyle, int iWait)
Var
    int iExit,
    object oShell
Let oShell = CreateObjectEx (c_sShellProgId, False)
Let iExit = oShell.Run (sCommandLine, iWindowStyle, iWait)
Return iExit
EndFunction


; Wraps a string in double quotes, for a path going onto a command line.
string Function stringQuote (string sText)
Return "\"" + sText + "\""
EndFunction


; Pulls one attribute's value out of a piece of XML.
;
; A whole parser is not needed to read one attribute, and the string functions
; are certain where an object model would be another thing to be wrong about.
string Function attributeValue (string sXml, string sName)
Var
    int iEnd, int iStart,
    string sMark
Let sMark = sName + "=\""
Let iStart = StringContains (sXml, sMark)
If iStart == 0 Then
    Return ""
EndIf
Let iStart = iStart + StringLength (sMark)
Let iEnd = iStart
While iEnd <= StringLength (sXml)
    If SubString (sXml, iEnd, 1) == "\"" Then
        Return SubString (sXml, iStart, iEnd - iStart)
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
string Function callBridge (string sCommand, string sArgument)
Var
    int iExit,
    object oFile, object oFileSystem, object oNull,
    string sAnswer, string sArgumentPath, string sCommandLine, string sPassed
If SubString (c_sBridgePath, 1, 1) == "@" Then
    SayMessage (OT_ERROR, "The HomerView scripts were compiled without being installed, so the bridge cannot be found. Run the HomerView installer again.")
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
Let oFileSystem = CreateObjectEx (c_sFileSystemProgId, False)
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
Let sCommandLine = stringQuote (c_sBridgePath) + " " + sCommand
    + " " + stringQuote (c_sAnswerPath) + " " + stringQuote (sPassed)
logLine ("callBridge " + sCommand + " sending "
    + IntToString (StringLength (sArgument)) + " characters through a file")
; A command that never started must never be read as the last one's success.
If oFileSystem.FileExists (c_sAnswerPath) Then
    oFileSystem.DeleteFile (c_sAnswerPath)
EndIf
; Nought hides the window; True waits for it to finish.
Let iExit = shellRun (sCommandLine, 0, True)
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
    SayMessage (OT_ERROR, "HomerView did not answer. Its browser may not be running: launch it and try again.")
    Return ""
EndIf
logLine ("callBridge " + sCommand + " read " + IntToString (StringLength (sAnswer)) + " characters")
Let gsLastResult = sAnswer
Return sAnswer
EndFunction


; Reads one value out of the helper's answer, which is XML.
;
; JSL HAS NO JSON FUNCTIONS -- not one in the seventeen hundred odd names the
; reference documents. What sat here instead was a hand written JSON reader:
; find the name, walk forward a character at a time looking for the closing
; quote, then undo six escape sequences in a fixed order. It worked for a flat
; answer with a single string in it and would have been wrong the first time
; the helper returned anything nested, silently, because there is nothing in
; that method that can notice it has gone wrong.
;
; So the helper answers in XML instead, and this asks XPath for the field.
; Neither side parses anything by hand: .NET turns the browser's JSON into XML
; with its own reader, and these three functions are Freedom Scientific's own,
; documented from JAWS 18. There is no unescaping to do, because entities are
; the parser's business rather than ours.
;
; CreateXMLDomDoc takes no parameters and hands back the object.
; LoadAndParseXML (object, string) returns True when the XML was well formed.
; GetXMLDomNodeText (node) returns the node's text.
;
; The answer's shape is the helper's own, so a path asked for here is a path
; the helper always writes.
string Function xmlValue (string sXml, string sPath)
Var
    object oDoc, object oNode
If sXml == "" Then
    Return ""
EndIf
Let oDoc = CreateXMLDomDoc ()
If LoadAndParseXML (oDoc, sXml) == False Then
    logLine ("xmlValue: the answer was not well formed XML, asking for " + sPath)
    Return ""
EndIf
Let oNode = oDoc.selectSingleNode (sPath)
Return GetXMLDomNodeText (oNode)
EndFunction


; Quotes a string for putting inside JavaScript.
;
; Single quotes, not double. The JavaScript reaches the bridge as one command
; line argument wrapped in double quotes, so a double quote inside it would end
; the argument early and the rest of the program would arrive as separate
; arguments nobody reads. Nothing in this file's JavaScript uses one.
string Function jsQuote (string sText)
Let sText = StringReplaceSubstrings (sText, "\\", "\\\\")
Let sText = StringReplaceSubstrings (sText, "'", "\\'")
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
string Function linkUrl ()
Var
    string sHref, string sTag, string sXml
Let sXml = GetElementXML (0)
Let sHref = attributeValue (sXml, "href")
If sHref == "" Then
    Let sXml = GetElementXML (1)
    Let sHref = attributeValue (sXml, "href")
EndIf
logLine ("linkUrl: element XML is " + IntToString (StringLength (sXml)) + " characters: " + sXml)
If sHref == "" Then
    Let sTag = attributeValue (sXml, "fsTag")
    logLine ("linkUrl: no href; the cursor is on a " + sTag)
    Let gsLastTag = sTag
Else
    Let gsLastTag = ""
EndIf
; The link's own words go with the address. The helper compares them with the
; page's title and says when they have nothing in common, which is the mismatch
; a sighted reader catches by hovering and a blind reader never sees.
Let gsLastText = attributeValue (sXml, "fsText")
logLine ("linkUrl: href is " + sHref)
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
string Function runScript (string sJavaScript)
Var string sAnswer
Let sAnswer = callBridge ("evaluateText", sJavaScript)
If sAnswer == "" Then
    Return ""
EndIf
If SubString (sAnswer, 1, 6) == "ERROR:" Then
    logLine ("runScript: " + sAnswer)
    SayMessage (OT_ERROR, sAnswer)
    Return ""
EndIf
logLine ("runScript returning " + IntToString (StringLength (sAnswer)) + " characters")
Return sAnswer
EndFunction


; Opens one of HomerView's own documents in HomerView's browser.
;
; A FUNCTION, NOT SEVEN NEAR-IDENTICAL SCRIPTS. Each document command is three
; lines that name a file and call this, so a new document is a new script and a
; new row in the table rather than another copy of the same twenty lines.
Void Function openOwnDocument (string sFile, string sWhat)
Var
    int iExit,
    string sAnswer
logLine ("openOwnDocument asked for " + sFile)
Let sAnswer = callBridge ("openPage", c_sAppFolder + "\\" + sFile)
If xmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_STATUS, "Opening " + sWhat)
    Return
EndIf
; The same fallback the guide has: a document that will not open at all is
; worse than one in the wrong window, and these are what somebody reaches for
; when nothing else is working.
logLine ("openOwnDocument: falling back to the default browser")
Let iExit = shellRun ("cmd.exe /c start \"\" " + stringQuote (c_sAppFolder + "\\" + sFile), 0, False)
SayMessage (OT_STATUS, "HomerView is not running, so " + sWhat + " is opening in your usual browser.")
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
Void Function findAndMark (string sMode, string sNeedle, int bBackwards)
Var
    int iMoved,
    string sAnswer, string sCount
Let sAnswer = callBridge ("findMark", sMode + "\t" + sNeedle)
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sCount = xmlValue (sAnswer, "/root/value")
If sCount == "0" Then
    SayMessage (OT_ERROR, "Not found.")
    Return
EndIf
Let gsLastFind = sNeedle
If bBackwards Then
    Let iMoved = MoveToTagWithAttribute (S_BOTTOM, "", "data-homerviewfind", True)
Else
    Let iMoved = MoveToTagWithAttribute (S_TOP, "", "data-homerviewfind", True)
EndIf
logLine ("findAndMark: " + sCount + " matches, moved " + IntToString (iMoved))
If iMoved Then
    SayMessage (OT_MESSAGE, sCount + " found")
    SayLine ()
Else
    SayMessage (OT_MESSAGE, sCount + " found, but the cursor could not be moved to one.")
EndIf
EndFunction


; Moves to the next or previous match already marked. F3 and Shift+F3.
Void Function findAgain (int bBackwards)
Var int iMoved
If gsLastFind == "" Then
    SayMessage (OT_ERROR, "Nothing has been searched for yet.")
    Return
EndIf
If bBackwards Then
    Let iMoved = MoveToTagWithAttribute (S_PRIOR, "", "data-homerviewfind", True)
Else
    Let iMoved = MoveToTagWithAttribute (S_NEXT, "", "data-homerviewfind", True)
EndIf
If iMoved Then
    SayLine ()
Else
    SayMessage (OT_MESSAGE, "No more.")
EndIf
EndFunction


; Adds the clipboard to the end of a text file. Control+Shift+Apostrophe.
;
; The apostrophe family is his across every one of his programs: Alt for say,
; Control for save, Control+Shift for append, Alt+Shift for clear. They are
; VIRTUAL keys here and not common ones, which is deliberate -- a common key
; would take Alt+Apostrophe away from FileDir and EdSharp, which handle it
; themselves and would never see it again.
Script appendClipboard ()
Var
    string sAnswer, string sPath
logLine ("appendClipboard started")
; THE SAME FILE AS LAST TIME, WITHOUT ASKING AGAIN.
;
; Appending is gathering, and gathering means many presses into one file. Being
; asked for the name every time would defeat it. When no file has been chosen
; yet there is nothing to append to, so this behaves exactly as Save Clipboard
; does and asks once.
If gsClipboardFile == "" Then
    logLine ("appendClipboard: no file yet, so asking as Save Clipboard would")
    PerformScriptByName ("saveClipboard")
    Return
EndIf
Let sAnswer = callBridge ("clipboardToFile", "+" + gsClipboardFile)
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, xmlValue (sAnswer, "/root/value"))
EndScript


; Empties the clipboard, so an append starts afresh. Alt+Shift+Apostrophe.
Script clearClipboard ()
Var string sAnswer
logLine ("clearClipboard started")
Let sAnswer = callBridge ("clipboardClear", "")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, xmlValue (sAnswer, "/root/value"))
EndScript


; Adds what is selected, or the current line, to what is already on the
; clipboard. Alt+C.
;
; The whole point of an append is gathering: three paragraphs from different
; parts of a page into one note, without a second window to paste into.
Script copyAppend ()
Var
    string sAnswer, string sText
logLine ("copyAppend started")
Let sText = GetSelectedText ()
If sText == "" Then
    Let sText = GetLine ()
EndIf
If sText == "" Then
    SayMessage (OT_ERROR, "There is nothing here to copy.")
    Return
EndIf
Let sAnswer = callBridge ("clipboardAdd", sText)
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, xmlValue (sAnswer, "/root/value"))
EndScript


; Puts the whole page on the clipboard. Control+F8.
;
; EdSharp's key for the same idea. JAWS has no equivalent: selecting a whole
; virtual document and copying it is Control+A then Control+C, which is the
; browser's selection rather than the text a reader sees, and on many pages
; brings back the navigation and the footers with it.
Script copyAll ()
Var string sAnswer
logLine ("copyAll started")
SayMessage (OT_STATUS, "Copying the page")
Let sAnswer = callBridge ("copyAll", "")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, xmlValue (sAnswer, "/root/value"))
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
Script checkAccessibilityIbm ()
Var string sAnswer, string sResult
logLine ("checkAccessibilityIbm started")
SayMessage (OT_STATUS, "Running the IBM checker. On a large page this can take a minute or two, and JAWS will wait.")
Let sAnswer = callBridge ("ace", "IBM_Accessibility")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = xmlValue (sAnswer, "/root/value")
If sResult == "" Then
    logLine ("checkAccessibilityIbm: nothing came back")
    Return
EndIf
; SPOKEN, NOT SHOWN. The report has just been opened in a tab, and a virtual
; view repeating its summary would sit in front of it and take the focus.
SayMessage (OT_MESSAGE, sResult)
EndScript


; Copies what is selected, or the current line if nothing is. Control+C.
;
; CONTROL+C IS THE BROWSER'S KEY AND IS TAKEN ON THE PROJECT'S OWN TERMS: a key
; may be taken only where HomerView does everything the browser did with it and
; more. Edge copies a selection and does nothing at all without one. This
; copies the selection when there is one and the line under the cursor when
; there is not, which is the case a reader hits most often.
Script copySelection ()
Var string sText
logLine ("copySelection started")
Let sText = GetSelectedText ()
If sText == "" Then
    Let sText = GetLine ()
    If sText == "" Then
        SayMessage (OT_ERROR, "There is nothing here to copy.")
        Return
    EndIf
    CopyToClipboard (sText)
    SayMessage (OT_MESSAGE, "Line copied.")
    Return
EndIf
CopyToClipboard (sText)
SayMessage (OT_MESSAGE, "Copied " + IntToString (StringLength (sText)) + " characters.")
EndScript


; Selects from where the selection was started to here. Shift+F8.
Script completeSelection ()
Var string sText
logLine ("completeSelection started")
; Muted for the same reason: this one reads the whole selection aloud, which
; on a long passage is the entire passage before he can do anything with it.
SpeechOff ()
PerformScript SelectTextBetweenMarkedPlaceAndCurrentPosition ()
SpeechOn ()
Let sText = GetSelectedText ()
; THE OUTCOME, NOT THE ACTION. The previous version reported whether a function
; had returned true and logged nothing at all, so when it silently selected
; nothing there was no way to tell from the log whether the key had even
; arrived. The length of what is now selected is the only answer that means
; anything.
logLine ("completeSelection: " + IntToString (StringLength (sText)) + " characters are selected")
If sText == "" Then
    SayMessage (OT_ERROR, "Nothing was selected. Press F8 first, where the passage begins.")
    Return
EndIf
SayMessage (OT_MESSAGE, "Complete Selection")
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
Script checkAccessibility ()
Var string sAnswer, string sResult
logLine ("checkAccessibility started")
SayMessage (OT_STATUS, "Checking the page. This takes a moment.")
; THE WHOLE REPORT, SAVED AND OPENED.
;
; It used to build its summary in JavaScript and show it in the Virtual Viewer,
; which was fine for counts and poor for anything a publisher could act on: no
; WCAG criterion names, no levels, nothing to send anybody. The helper now
; builds the report report.py builds on the NVDA side -- plain language first,
; then the severity breakdown, then each problem with its criterion NAMED and
; its level given -- writes it to Downloads as one file, and opens it here.
Let sAnswer = callBridge ("axeReport", "")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = xmlValue (sAnswer, "/root/value")
If sResult == "" Then
    logLine ("checkAccessibility: nothing came back")
    Return
EndIf
sayOrShow (sResult)
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
Script copyLogToClipboard ()
Var
    string sAnswer
logLine ("copyLogToClipboard started")
Let sAnswer = callBridge ("clipboardFile", logPath ())
If xmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_MESSAGE, "The log is on the clipboard, as a file and as its path. Control+V attaches it in a message, or pastes the path anywhere else.")
    Return
EndIf
logLine ("copyLogToClipboard: the file drop was refused: " + xmlValue (sAnswer, "/root/error"))
Let sAnswer = callBridge ("clipboardText", logPath ())
If xmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_MESSAGE, "The file itself could not be copied, so its path is on the clipboard as text.")
Else
    SayMessage (OT_ERROR, "Nothing could be put on the clipboard. The log is at " + logPath ())
EndIf
EndScript


; Puts every link on the page on the clipboard. Alt+Shift+P.
;
; The text and the address of each, one per line, in the order they appear.
; A page's links are a table of contents nobody prints, and having them as
; text means they can be pasted into a message, searched, or kept.
Script copyPageLinks ()
Var
    int iJaws, int iLength,
    string sAnswer, string sResult, string sStripped, string sXml
logLine ("copyPageLinks started")
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
Let iLength = StringLength (sXml)
Let sStripped = StringReplaceSubstrings (sXml, "<Link ", "")
Let iJaws = (iLength - StringLength (sStripped)) / 6
logLine ("  the off screen model has " + IntToString (iJaws) + " links in "
    + IntToString (iLength) + " characters of document XML")
SayMessage (OT_STATUS, "Collecting the links")
Let sResult = runScript (
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
    SayMessage (OT_ERROR, "No links were found on this page.")
    Return
EndIf
; The browser's own count is the first word of what it sent back. It stays a
; string: turning it into a number would need a conversion this file has never
; proved exists, and an unknown function is assumed to return an int, so the
; arithmetic would type check perfectly and be wrong in silence. Two numbers on
; one log line need no arithmetic to compare.
logLine ("  PARITY on this page: off screen model " + IntToString (iJaws)
    + " links, browser " + StringSegment (sResult, " ", 1) + " links")
Let sAnswer = callBridge ("clipboardText", sResult)
If xmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_MESSAGE, "The links are on the clipboard.")
Else
    SayMessage (OT_ERROR, "The links could not be put on the clipboard.")
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
Script describeLinkTarget ()
Var
    string sAnswer, string sResult, string sUrl
logLine ("describeLinkTarget started")
Let sUrl = linkUrl ()
If sUrl == "" Then
    logLine ("describeLinkTarget: no address here")
    If gsLastTag == "" Then
        SayMessage (OT_ERROR, "No link here")
    Else
        SayMessage (OT_ERROR, "No link here. The cursor is on a " + gsLastTag + ".")
    EndIf
    Return
EndIf
SayMessage (OT_STATUS, "Asking where that goes")
Let sAnswer = callBridge ("probe", sUrl + "\t" + gsLastText)
If sAnswer == "" Then
    Return
EndIf
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = xmlValue (sAnswer, "/root/value")
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
    logLine ("describeLinkTarget: nothing came back about the target, showing the address alone")
    sayOrShow ("The link could not be reached, so this is only its address."
        + "\r\n\r\n" + sUrl)
Else
    sayOrShow (sResult)
EndIf
EndScript


; Closes whatever is covering the page. Alt+JAWSKey+D.
;
; Cookie banners, newsletter offers and sign-in walls are not part of the page
; and are rarely reachable by the keys that would dismiss them. This closes any
; open dialog element, then presses Escape at whatever else is pinned over the
; content, and says how many things it shifted.
Script dismissDialog ()
Var string sResult
logLine ("dismissDialog started")
Let sResult = runScript (
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
Script extractMainContent ()
Var string sAnswer, string sResult
logLine ("extractMainContent started")
SayMessage (OT_STATUS, "Extracting the main content")
Let sAnswer = callBridge ("extract", "")
If sAnswer == "" Then
    Return
EndIf
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = xmlValue (sAnswer, "/root/value")
If sResult == "" Then
    logLine ("extractMainContent: the helper answered with nothing")
    Return
EndIf
; SHOWN, NOT SPOKEN. This command opens a tab, and a tab opening is a focus
; change: the sentence was spoken into it and heard by nobody. The log said the
; helper had answered and the screen said nothing, which is the shape of every
; fault this project has spent an afternoon on.
sayOrShow (sResult)
EndScript


; Launches or reconnects HomerView's copy of Microsoft Edge. No key by default:
; see the guide, since default.jkm is never touched.
Script launchHomerView ()
Var string sAnswer
SayMessage (OT_STATUS, "Starting HomerView")
Let sAnswer = callBridge ("launch", "")
If sAnswer == "" Then
    Return
EndIf
If xmlValue (sAnswer, "/root/connected") == "true" Then
    SayMessage (OT_MESSAGE, "HomerView is ready.")
Else
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
EndIf
EndScript


; The open tabs, by name and address. On the menu, with no key of its own.
;
; No key because F4 is what the NVDA side uses and F4 in this browser puts the
; cursor in the address bar. A key that takes something away from the browser
; has to give more back than it costs, and a list nobody asked for does not.
Script listTabs ()
Var
    int iActivated, int iAdded, int iTab,
    string sAnswer, string sId, string sRecord, string sResult,
    string sTitle, string sUrl
logLine ("listTabs started")
Let sAnswer = callBridge ("tabList", "")
If sAnswer == "" Then
    Return
EndIf
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = xmlValue (sAnswer, "/root/value")
If sResult == "" Then
    SayMessage (OT_ERROR, "No tabs are open.")
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
UserBufferDeactivate ()
UserBufferClear ()
Let iAdded = UserBufferAddText ("HomerView tabs. Press Enter on one to go to it.")
Let iAdded = UserBufferAddText ("")
Let iTab = 1
Let sRecord = StringSegment (sResult, "\7", iTab)
While sRecord != ""
    Let sId = StringSegment (sRecord, "\t", 1)
    Let sTitle = StringSegment (sRecord, "\t", 2)
    Let sUrl = StringSegment (sRecord, "\t", 3)
    Let iAdded = UserBufferAddLink (IntToString (iTab) + ". " + sTitle,
        "homerViewTab (\"" + sId + "\")", sTitle)
    Let iAdded = UserBufferAddText ("   " + sUrl)
    Let iTab = iTab + 1
    Let sRecord = StringSegment (sResult, "\7", iTab)
EndWhile
Let iActivated = UserBufferActivate ()
JAWSTopOfFile ()
SayAll ()
logLine ("listTabs showed " + IntToString (iTab - 1) + " tabs, activated " + IntToString (iActivated))
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
Script moveToProbableMain ()
Var
    int iMoved,
    string sResult
Let sResult = runScript (
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
    SayMessage (OT_ERROR, "The main content could not be worked out.")
    Return
EndIf
; The attribute is the bridge between the browser and the virtual cursor. The
; tag is left empty because any element may have won; S_TOP is used rather than
; S_NEXT so it does not matter where the cursor was.
;
; An earlier version called JAWSFindFirst, which does not exist. A call to an
; unknown function is not an error on its own in this language, so the compiler
; accepted it and the command would simply have done nothing.
Let iMoved = MoveToTagWithAttribute (S_TOP, "", "data-homerviewmain", True)
logLine ("moveToProbableMain: the page said " + sResult
    + " and the move returned " + IntToString (iMoved))
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
        SayMessage (OT_MESSAGE, "Main content, as the page declares it")
    Else
        SayMessage (OT_MESSAGE, "Main content, by weighing the page")
    EndIf
    SayLine ()
Else
    ; The mark was set but the buffer does not show it. Saying what was found is
    ; worth more than silence, and silence is what the old version gave.
    SayMessage (OT_MESSAGE, "The main content looks like this, but the cursor could not be moved to it. " + sResult)
EndIf
EndScript


; Opens HomerView's guide. Control+F1, the key the NVDA side uses.
Script openUserGuide ()
Var
    int iExit,
    string sAnswer
logLine ("openUserGuide started")
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
Let sAnswer = callBridge ("openPage", c_sAppFolder + "\\HomerView.htm")
If xmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_STATUS, "Opening the HomerView guide")
    Return
EndIf
logLine ("openUserGuide: falling back to the default browser")
Let iExit = shellRun ("cmd.exe /c start \"\" " + stringQuote (c_sAppFolder + "\\HomerView.htm"), 0, False)
SayMessage (OT_STATUS, "HomerView is not running, so the guide is opening in your usual browser.")
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
Script sayMetadata ()
Var string sResult
logLine ("sayMetadata started")
SayMessage (OT_STATUS, "Reading what the page says about itself")
Let sResult = runScript (
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
    sayOrShow (sResult)
Else
    logLine ("nothing to show: runScript returned nothing")
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
Script startSelection ()
logLine ("startSelection started")
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
Script readAll ()
Var string sAnswer, string sText
logLine ("readAll started")
Let sAnswer = callBridge ("pageText", "")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sText = xmlValue (sAnswer, "/root/value")
If sText == "" Then
    SayMessage (OT_ERROR, "The page has no text to read.")
    Return
EndIf
logLine ("readAll speaking " + IntToString (StringLength (sText)) + " characters")
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
Script openDocument ()
Var
    string sAnswer, string sPath
logLine ("openDocument started")
Let sAnswer = callBridge ("openDialog", "Open a document in HomerView\tDocuments|*.htm;*.html;*.txt;*.md;*.docx;*.doc;*.pdf;*.epub;*.rtf;*.odt;*.pptx;*.xlsx;*.csv|All files|*.*\t")
Let sPath = xmlValue (sAnswer, "/root/value")
If sPath == "" Then
    logLine ("openDocument: no file was chosen")
    Return
EndIf
SayMessage (OT_STATUS, "Opening it. A document that needs converting takes a moment.")
Let sAnswer = callBridge ("openDocument", sPath)
If xmlValue (sAnswer, "/root/error") != "" Then
    sayOrShow (xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, "Opened in HomerView.")
EndScript


; Saves the page in whatever format the chosen name asks for. Control+S.
;
; Edge's Control+S saves a page as html or as a single file. This saves it that
; way and also as anything pandoc can write -- Word, OpenDocument, Markdown,
; ebook -- chosen simply by naming the file, which is more than the browser
; offers and is why the key is taken.
Script savePage ()
Var
    string sAnswer, string sPath
logLine ("savePage started")
Let sAnswer = callBridge ("saveDialog", "Save this page as\tWeb page|*.htm|Word document|*.docx|OpenDocument text|*.odt|Markdown|*.md|EPUB ebook|*.epub|All files|*.*\t")
Let sPath = xmlValue (sAnswer, "/root/value")
If sPath == "" Then
    logLine ("savePage: no file was chosen")
    Return
EndIf
SayMessage (OT_STATUS, "Saving the page.")
Let sAnswer = callBridge ("savePage", sPath)
If xmlValue (sAnswer, "/root/error") != "" Then
    sayOrShow (xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, xmlValue (sAnswer, "/root/value"))
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
Script downloadFiles ()
Var
    int iFailed, int iGot, int iOk, int iWhich,
    string sAnswer, string sFolder, string sKinds, string sName,
    string sNames, string sSummary, string sTrouble
logLine ("downloadFiles started")
SayMessage (OT_STATUS, "Looking at what this page links to")
Let sAnswer = callBridge ("downloadScan", "")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sSummary = xmlValue (sAnswer, "/root/value")
If sSummary == "" Then
    logLine ("downloadFiles: nothing came back from the scan")
    Return
EndIf
Let sKinds = StringSegment (sSummary, "\t", 2)
Let iOk = InputBox ("Which kinds? " + StringSegment (sSummary, "\t", 1),
    "Web Download", sKinds)
If iOk == 0 Then
    Return
EndIf
If sKinds == "" Then
    SayMessage (OT_ERROR, "No kinds were named, so nothing was fetched.")
    Return
EndIf
Let sAnswer = callBridge ("downloadList", sKinds)
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sSummary = xmlValue (sAnswer, "/root/value")
Let sFolder = StringSegment (sSummary, "\t", 2)
Let sNames = StringSegment (sSummary, "\t", 3)
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
Let sName = StringSegment (sNames, "\7", iWhich)
While sName != ""
    SayMessage (OT_MESSAGE, sName)
    Let sAnswer = callBridge ("downloadOne", IntToString (iWhich))
    If xmlValue (sAnswer, "/root/error") != "" Then
        Let iFailed = iFailed + 1
        Let sTrouble = sTrouble + sName + ": " + xmlValue (sAnswer, "/root/error") + "\r\n"
        SayMessage (OT_ERROR, "Error. " + xmlValue (sAnswer, "/root/error"))
    Else
        Let iGot = iGot + 1
    EndIf
    Let iWhich = iWhich + 1
    Let sName = StringSegment (sNames, "\7", iWhich)
EndWhile
; A MESSAGE BOX AT THE END, because a spoken summary after twenty spoken names
; is one more thing said and gone, and this is the part worth reading twice.
Let sSummary = IntToString (iGot) + " of " + IntToString (iGot + iFailed)
    + " files fetched into" + "\r\n" + sFolder
If iFailed > 0 Then
    Let sSummary = sSummary + "\r\n\r\n" + IntToString (iFailed)
        + " did not come:" + "\r\n" + sTrouble
EndIf
logLine ("downloadFiles: " + IntToString (iGot) + " fetched, "
    + IntToString (iFailed) + " failed")
MessageBox (sSummary)
EndScript


; Searches backwards for text. Control+Shift+F.
;
; CONTROL+F IS LEFT ALONE. JAWS's own find is forward only and it is a good
; find; what JAWS has no key for is going the other way, so this is the missing
; half rather than a replacement.
Script findBackwards ()
Var
    int iOk,
    string sNeedle
logLine ("findBackwards started")
Let sNeedle = gsLastFind
Let iOk = InputBox ("Find backwards", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
findAndMark ("plain", sNeedle, True)
EndScript


; Searches forward for a regular expression. Control+F3.
Script findByPattern ()
Var
    int iOk,
    string sNeedle
logLine ("findByPattern started")
Let sNeedle = gsLastFind
Let iOk = InputBox ("Find forward with a regular expression", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
findAndMark ("pattern", sNeedle, False)
EndScript


; Searches backwards for a regular expression. Control+Shift+F3.
Script findByPatternBackwards ()
Var
    int iOk,
    string sNeedle
logLine ("findByPatternBackwards started")
Let sNeedle = gsLastFind
Let iOk = InputBox ("Find backwards with a regular expression", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
findAndMark ("pattern", sNeedle, True)
EndScript


; The next match, of whichever find was done last. F3.
Script findNext ()
logLine ("findNext started")
findAgain (False)
EndScript


; The previous match, of whichever find was done last. Shift+F3.
Script findPrevious ()
logLine ("findPrevious started")
findAgain (True)
EndScript


; Every match of a regular expression, gathered for reading. Control+Shift+E.
;
; A find moves you to matches one at a time. This is the other question: what
; are they all? Each match is separated by a form feed between blank lines, so
; they read as pages rather than as a run-on list.
Script extractByPattern ()
Var
    int iOk,
    string sAnswer, string sNeedle, string sResult
logLine ("extractByPattern started")
Let sNeedle = gsLastFind
Let iOk = InputBox ("Extract every match of a regular expression", "HomerView", sNeedle)
If iOk == 0 Then
    Return
EndIf
If sNeedle == "" Then
    SayMessage (OT_ERROR, "No pattern was given.")
    Return
EndIf
Let gsLastFind = sNeedle
Let sAnswer = callBridge ("extractPattern", sNeedle)
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = xmlValue (sAnswer, "/root/value")
If sResult == "" Then
    logLine ("extractByPattern: nothing came back")
    Return
EndIf
sayVirtual (sResult)
EndScript


; The Quick Start. Alt+Shift+F1.
Script openQuickStart ()
openOwnDocument ("ReadMe.htm", "the Quick Start")
EndScript


; What has changed, release by release. Shift+F1.
Script showHistory ()
openOwnDocument ("History.htm", "the history of changes")
EndScript


; The notes for anyone working on HomerView itself. Control+Shift+F1.
Script openDeveloperNotes ()
openOwnDocument ("Developer.htm", "the developer notes")
EndScript


; Every key in one document, which is the printable companion to the Hotkey
; Summary. No key of its own; it is on the menu.
Script openHotkeyDocument ()
openOwnDocument ("Hotkeys.htm", "the hotkey document")
EndScript


; What HomerView is for, in its own words. No key; on the menu.
Script openAnnouncement ()
openOwnDocument ("Announce.htm", "the project announcement")
EndScript


; This session's log, opened to read rather than copied to send. Alt+Control+F1.
Script openSessionLog ()
Var
    int iExit,
    string sAnswer
logLine ("openSessionLog started")
Let sAnswer = callBridge ("openPage", c_sLogFile)
If xmlValue (sAnswer, "/root/value") != "" Then
    SayMessage (OT_STATUS, "Opening the session log")
    Return
EndIf
Let iExit = shellRun ("cmd.exe /c start \"\" " + stringQuote (c_sLogFile), 0, False)
SayMessage (OT_STATUS, "Opening the session log outside HomerView.")
EndScript


; Which build is loaded, and where everything lives. Alt+F1.
;
; NOT A DOCUMENT, because the useful facts about a build are not in a file that
; ships with it: the version, when it was installed, and where the log is.
Script showAbout ()
logLine ("showAbout started")
sayVirtual ("HomerView " + c_sVersion + " for JAWS"
    + "\r\n" + "Installed " + c_sInstalled
    + "\r\n\r\n" + "Program: " + c_sAppFolder
    + "\r\n" + "Log: " + c_sLogFile
    + "\r\n\r\n" + "Alt+JAWSKey+F10 opens the menu. Alt+Shift+H lists every key.")
EndScript


; Says the names of the open tabs, and moves nothing. Shift+F4.
;
; Tab List shows a buffer of links and takes focus, which is right when the
; point is to GO somewhere. This is the other question -- what is open -- and
; answering it should cost nothing. F4 itself belongs to Edge's address bar, so
; the shifted key takes the idea without taking the browser's key.
Script sayTabNames ()
Var
    int iWhich,
    string sAnswer, string sNames, string sRecord, string sSpoken
logLine ("sayTabNames started")
Let sAnswer = callBridge ("tabList", "")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sNames = xmlValue (sAnswer, "/root/value")
If sNames == "" Then
    SayMessage (OT_ERROR, "No tabs are open.")
    Return
EndIf
Let iWhich = 1
Let sRecord = StringSegment (sNames, "\7", iWhich)
While sRecord != ""
    If sSpoken == "" Then
        Let sSpoken = StringSegment (sRecord, "\t", 2)
    Else
        Let sSpoken = sSpoken + ". " + StringSegment (sRecord, "\t", 2)
    EndIf
    Let iWhich = iWhich + 1
    Let sRecord = StringSegment (sNames, "\7", iWhich)
EndWhile
SayMessage (OT_MESSAGE, sSpoken)
EndScript


; Says what is on the clipboard. Alt+Apostrophe.
;
; The same answer FileDir gives to the same key: "Path drop list" and then the
; paths when a file has been copied, and the text otherwise. Two of his own
; programs answering one question two ways would be a second vocabulary for one
; idea.
Script sayClipboard ()
Var string sAnswer, string sResult
logLine ("sayClipboard started")
Let sAnswer = callBridge ("clipboardSay", "")
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
Let sResult = xmlValue (sAnswer, "/root/value")
If sResult == "" Then
    logLine ("sayClipboard: nothing came back")
    Return
EndIf
sayOrShow (sResult)
EndScript


; Saves the clipboard to a text file, proposing the last name used.
; Control+Apostrophe.
Script saveClipboard ()
Var
    string sAnswer, string sPath
logLine ("saveClipboard started")
; A REAL SAVE-AS DIALOG, not a box to type a path into.
;
; InputBox asked for a path and gave no way to look for one. The helper shows
; the CLASSIC Windows dialog -- the old GetSaveFileName one, not the modern
; Common Item Dialog -- because that is the one with a folder tree that can be
; walked and a tab order that goes where you expect.
Let sAnswer = callBridge ("saveDialog", "Save the clipboard as\tText files|*.txt|All files|*.*\t" + gsClipboardFile)
Let sPath = xmlValue (sAnswer, "/root/value")
If sPath == "" Then
    logLine ("saveClipboard: no file was chosen")
    Return
EndIf
Let gsClipboardFile = sPath
Let sAnswer = callBridge ("clipboardToFile", sPath)
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, xmlValue (sAnswer, "/root/value"))
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
Script showHotkeySummary ()
Var
    int iActivated, int iAdded
UserBufferDeactivate ()
UserBufferClear ()
Let iAdded = UserBufferAddText ("HomerView " + c_sVersion + " for JAWS, installed " + c_sInstalled)
Let iAdded = UserBufferAddText ("")
Let iAdded = UserBufferAddText ("Anywhere:")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+H   Launch or return to HomerView", "homerViewLink (\"launchHomerView\")", "Launch HomerView")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+F10 Alternate Menu, every command in one list", "homerViewLink (\"showHomerViewMenu\")", "Alternate Menu")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+A   Check the page with axe and save a report", "homerViewLink (\"checkAccessibility\")", "Check Accessibility with axe")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+D   Close a cookie banner or consent wall", "homerViewLink (\"dismissDialog\")", "Dismiss Dialog")
Let iAdded = UserBufferAddLink ("  Alt+Shift+H     This summary", "homerViewLink (\"showHotkeySummary\")", "Hotkey Summary")
Let iAdded = UserBufferAddLink ("  Shift+F4        Say the names of the open tabs", "homerViewLink (\"sayTabNames\")", "Tab Names")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+L   Copy the log file to the clipboard", "homerViewLink (\"copyLogToClipboard\")", "Log to Clipboard")
Let iAdded = UserBufferAddText ("")
Let iAdded = UserBufferAddText ("On a web page:")
Let iAdded = UserBufferAddLink ("  Shift+Q         Move to the main content, declared or not", "homerViewLink (\"moveToProbableMain\")", "Jump to Probable Main")
Let iAdded = UserBufferAddLink ("  Alt+L           Where this link goes, and its address", "homerViewLink (\"describeLinkTarget\")", "Link Target")
Let iAdded = UserBufferAddLink ("  Alt+M           What the page says about itself", "homerViewLink (\"sayMetadata\")", "Say Metadata")
Let iAdded = UserBufferAddLink ("  Alt+Shift+P     Copy every link on the page to the clipboard", "homerViewLink (\"copyPageLinks\")", "Page Links to Clipboard")
Let iAdded = UserBufferAddLink ("  Alt+Shift+W     Fetch the files this page links to", "homerViewLink (\"downloadFiles\")", "Web Download")
Let iAdded = UserBufferAddLink ("  Control+O       Open a document as a page", "homerViewLink (\"openDocument\")", "Open Document")
Let iAdded = UserBufferAddLink ("  Control+S       Save this page in any format", "homerViewLink (\"savePage\")", "Save Page")
Let iAdded = UserBufferAddLink ("  Control+F1      The HomerView guide", "homerViewLink (\"openUserGuide\")", "User Guide")
Let iAdded = UserBufferAddLink ("  Alt+Shift+F1    The Quick Start", "homerViewLink (\"openQuickStart\")", "Quick Start")
Let iAdded = UserBufferAddLink ("  Shift+F1        What changed in each release", "homerViewLink (\"showHistory\")", "History of Changes")
Let iAdded = UserBufferAddLink ("  Control+Shift+F1 Notes for developers", "homerViewLink (\"openDeveloperNotes\")", "Developer Notes")
Let iAdded = UserBufferAddLink ("  Alt+Control+F1  This session's log, to read", "homerViewLink (\"openSessionLog\")", "Session Log")
Let iAdded = UserBufferAddLink ("  Alt+F1          Which build is loaded", "homerViewLink (\"showAbout\")", "About HomerView")
Let iAdded = UserBufferAddLink ("  Control+Shift+F Find backwards", "homerViewLink (\"findBackwards\")", "Reverse Find for Text")
Let iAdded = UserBufferAddLink ("  Control+F3      Find forward with a pattern", "homerViewLink (\"findByPattern\")", "Forward Find with Regular Expression")
Let iAdded = UserBufferAddLink ("  Control+Shift+F3 Find backwards with a pattern", "homerViewLink (\"findByPatternBackwards\")", "Reverse Find with Regular Expression")
Let iAdded = UserBufferAddLink ("  F3              The next match", "homerViewLink (\"findNext\")", "Forward Find Again")
Let iAdded = UserBufferAddLink ("  Shift+F3        The previous match", "homerViewLink (\"findPrevious\")", "Reverse Find Again")
Let iAdded = UserBufferAddLink ("  Control+Shift+E Gather every match of a pattern", "homerViewLink (\"extractByPattern\")", "Extract with Regular Expression")
Let iAdded = UserBufferAddLink ("  Shift+F9        Extract the main content into a tab", "homerViewLink (\"extractMainContent\")", "Extract Main Content")
Let iAdded = UserBufferAddLink ("  Alt+Apostrophe  Say what is on the clipboard", "homerViewLink (\"sayClipboard\")", "Say Clipboard")
Let iAdded = UserBufferAddLink ("  Control+Apostrophe Save the clipboard to a file", "homerViewLink (\"saveClipboard\")", "Save Clipboard")
Let iAdded = UserBufferAddLink ("  Control+Shift+Apostrophe Add the clipboard to a file", "homerViewLink (\"appendClipboard\")", "Append Clipboard")
Let iAdded = UserBufferAddLink ("  Alt+Shift+Apostrophe Empty the clipboard", "homerViewLink (\"clearClipboard\")", "Clear Clipboard")
Let iAdded = UserBufferAddLink ("  F8              Start a selection here", "homerViewLink (\"startSelection\")", "Start Selection")
Let iAdded = UserBufferAddLink ("  Shift+F8        Select from there to here", "homerViewLink (\"completeSelection\")", "Complete Selection")
Let iAdded = UserBufferAddLink ("  Control+C       Copy the selection, or this line", "homerViewLink (\"copySelection\")", "Copy Selection")
Let iAdded = UserBufferAddLink ("  Alt+C           Add it to what is on the clipboard", "homerViewLink (\"copyAppend\")", "Copy Append")
Let iAdded = UserBufferAddLink ("  Control+F8      Put the whole page on the clipboard", "homerViewLink (\"copyAll\")", "Copy All")
Let iAdded = UserBufferAddLink ("  Alt+F8          Speak the whole page, cursor unmoved", "homerViewLink (\"readAll\")", "Read All")
Let iAdded = UserBufferAddLink ("  Alt+JAWSKey+I   Check the page with IBM Equal Access", "homerViewLink (\"checkAccessibilityIbm\")", "Check Accessibility with IBM")
Let iAdded = UserBufferAddText ("")
Let iAdded = UserBufferAddText ("On the Alternate Menu only:")
Let iAdded = UserBufferAddLink ("  The open tabs, by name and address", "homerViewLink (\"listTabs\")", "Tab List")
Let iAdded = UserBufferAddText ("")
Let iAdded = UserBufferAddText ("JAWS already does these, so HomerView does not: the element lists on")
Let iAdded = UserBufferAddText ("JAWSKey+F5, F6 and F7, the main region on Q, the address on JAWSKey+A,")
Let iAdded = UserBufferAddText ("find on Control+F, and the page summary on JAWSKey+F3.")
Let iActivated = UserBufferActivate ()
JAWSTopOfFile ()
SayAll ()
logLine ("showHotkeySummary: last add " + IntToString (iAdded) + ", activated " + IntToString (iActivated))
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
Script showHomerViewMenu ()
Var
    int iChoice, int iRecord,
    string sItems, string sRecord, string sTable
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
Let sTable = "Launch HomerView, Launches or reconnects HomerView's copy of Microsoft Edge. (Alt+JAWSKey+H)\tlaunchHomerView"
    + "\7" + "Jump to Probable Main, Moves to the main content, whether the page declares it or not. (Shift+Q)\tmoveToProbableMain"
    + "\7" + "Link Target, Says where the link under the cursor goes and shows its address. (Alt+L)\tdescribeLinkTarget"
    + "\7" + "Say Metadata, Shows what the page says about itself. (Alt+M)\tsayMetadata"
    + "\7" + "Check Accessibility with axe, Tests the page with Deque axe-core and saves a report. (Alt+JAWSKey+A)\tcheckAccessibility"
    + "\7" + "Extract Main Content, Extracts the readable part of the page into a tab of its own. (Shift+F9)\textractMainContent"
    + "\7" + "Page Links to Clipboard, Copies the text and address of every link on the page. (Alt+Shift+P)\tcopyPageLinks"
    + "\7" + "Dismiss Dialog, Closes a cookie banner, newsletter offer or consent wall that Escape will not. (Alt+JAWSKey+D)\tdismissDialog"
    + "\7" + "Say Clipboard, Says what is on the clipboard, paths or text. (Alt+Apostrophe)\tsayClipboard"
    + "\7" + "Save Clipboard, Saves the clipboard to a text file. (Control+Apostrophe)\tsaveClipboard"
    + "\7" + "Append Clipboard, Adds the clipboard to the end of a text file. (Control+Shift+Apostrophe)\tappendClipboard"
    + "\7" + "Clear Clipboard, Empties the clipboard so an append starts afresh. (Alt+Shift+Apostrophe)\tclearClipboard"
    + "\7" + "Start Selection, Marks where a selection begins, to be finished with Shift+F8. (F8)\tstartSelection"
    + "\7" + "Complete Selection, Selects from where F8 was pressed to here. (Shift+F8)\tcompleteSelection"
    + "\7" + "Copy Selection, Copies the selection, or the line under the cursor. (Control+C)\tcopySelection"
    + "\7" + "Copy Append, Adds the selection or the line to what is on the clipboard. (Alt+C)\tcopyAppend"
    + "\7" + "Copy All, Puts the whole page on the clipboard. (Control+F8)\tcopyAll"
    + "\7" + "Read All, Speaks the whole page from the top without moving the cursor. (Alt+F8)\treadAll"
    + "\7" + "Check Accessibility with IBM, Runs IBM Equal Access and saves every format to Downloads. (Alt+JAWSKey+I)\tcheckAccessibilityIbm"
    + "\7" + "Tab List, Lists the open tabs by name and address.\tlistTabs"
    + "\7" + "Tab Names, Says the names of the open tabs without moving anywhere. (Shift+F4)\tsayTabNames"
    + "\7" + "Hotkey Summary, Lists every HomerView command and its key. (Alt+Shift+H)\tshowHotkeySummary"
    + "\7" + "Web Download, Fetches the files this page links to, with the browser's own cookies. (Alt+Shift+W)\tdownloadFiles"
    + "\7" + "Open Document, Opens a Word file, PDF, ebook or spreadsheet as a page. (Control+O)\topenDocument"
    + "\7" + "Save Page, Saves this page as html, Word, Markdown or an ebook. (Control+S)\tsavePage"
    + "\7" + "User Guide, Opens the HomerView guide. (Control+F1)\topenUserGuide"
    + "\7" + "Quick Start, The short introduction to HomerView. (Alt+Shift+F1)\topenQuickStart"
    + "\7" + "History of Changes, What changed in each release. (Shift+F1)\tshowHistory"
    + "\7" + "Developer Notes, Notes for anyone working on HomerView itself. (Control+Shift+F1)\topenDeveloperNotes"
    + "\7" + "Hotkey Document, Every key in one printable document.\topenHotkeyDocument"
    + "\7" + "Project Announcement, What HomerView is for, in its own words.\topenAnnouncement"
    + "\7" + "Session Log, Opens this session's log to read. (Alt+Control+F1)\topenSessionLog"
    + "\7" + "About HomerView, Which build is loaded and where everything lives. (Alt+F1)\tshowAbout"
    + "\7" + "Reverse Find for Text, Searches backwards for text, which JAWS has no key for. (Control+Shift+F)\tfindBackwards"
    + "\7" + "Forward Find with Regular Expression, Searches forward for a pattern. (Control+F3)\tfindByPattern"
    + "\7" + "Reverse Find with Regular Expression, Searches backwards for a pattern. (Control+Shift+F3)\tfindByPatternBackwards"
    + "\7" + "Forward Find Again, The next match of whichever find was done last. (F3)\tfindNext"
    + "\7" + "Reverse Find Again, The previous match of whichever find was done last. (Shift+F3)\tfindPrevious"
    + "\7" + "Extract with Regular Expression, Gathers every match for reading. (Control+Shift+E)\textractByPattern"
    + "\7" + "Log to Clipboard, Puts the HomerView log on the clipboard, ready to attach to a message. (Alt+JAWSKey+L)\tcopyLogToClipboard"
; The list the dialog shows is the first field of every row.
Let iRecord = 1
Let sRecord = StringSegment (sTable, "\7", iRecord)
While sRecord != ""
    If iRecord == 1 Then
        Let sItems = StringSegment (sRecord, "\t", 1)
    Else
        Let sItems = sItems + "\7" + StringSegment (sRecord, "\t", 1)
    EndIf
    Let iRecord = iRecord + 1
    Let sRecord = StringSegment (sTable, "\7", iRecord)
EndWhile
Let iChoice = dialogPick ("HomerView", sItems)
If iChoice == 0 Then
    Return
EndIf
Let sRecord = StringSegment (sTable, "\7", iChoice)
logLine ("menu row " + IntToString (iChoice) + " runs " + StringSegment (sRecord, "\t", 2))
PerformScriptByName (StringSegment (sRecord, "\t", 2))
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
Void Function homerViewTab (string sId)
Var string sAnswer
logLine ("homerViewTab asked for " + sId)
UserBufferDeactivate ()
Let sAnswer = callBridge ("activate", sId)
If xmlValue (sAnswer, "/root/error") != "" Then
    SayMessage (OT_ERROR, xmlValue (sAnswer, "/root/error"))
    Return
EndIf
SayMessage (OT_MESSAGE, "Going to that tab.")
EndFunction


Void Function homerViewLink (string sName)
logLine ("homerViewLink asked for " + sName)
UserBufferDeactivate ()
; The chain of branches that used to be here said the same thing twenty times.
; PerformScriptByName takes the name as a string, so the link's own target is
; the answer and there is nothing to keep in step.
PerformScriptByName (sName)
EndFunction

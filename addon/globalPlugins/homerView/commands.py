"""Every HomerView command: its name, its key, and what it does.

One table, and everything else reads from it. The gesture bindings, the
Alternate Menu, the hotkey summary and the published documentation all come
from here, so none of them can disagree with another or drift from the code.

## How a command is named

Two words at least, in title case, verb first where there is a verb. Say
Address, Find Pattern, Fetch Files. One word is not a name; it is a label, and
a list of labels cannot be searched by the thing you half remember.

## How a key is chosen

The first letter of the first word, where that letter is free. Failing that,
the first letter of the second word. A letter from the middle of a word is not
used, because nobody remembers it: the single exception is X for extract and
export, which is a convention older than any of this.

Beyond that, in order:

  - A key NVDA uses on either the desktop or the laptop layout is never taken.
  - Alt+Control with a letter, and Alt+Control+Shift with a letter, are never
    taken either. Those belong to Windows desktop and start menu shortcuts,
    which a user may have set for themselves, and a program that overrides one
    is taking something that was not its to take. Alt+Control with a function
    key is not in that convention and is used.
  - A JAWS default is used where it is free, because a blind Windows user has
    had those in their fingers for years. The element lists are here for that
    reason: NVDA+F5, NVDA+F6 and NVDA+Shift+F7 are where JAWS puts them.
  - Failing that, an EdSharp binding, since these are the same hands. Where the
    command is the same as EdSharp's, EdSharp's own sentence describes it, so
    the two programs read alike: Find at Cursor on Alt+F3, Web Download on
    Alt+Shift+W, Recent Files on Alt+R, and the whole accent family.
  - A key Edge uses may be taken when HomerView does everything Edge did with
    it and more, which is why Control+O and Control+S are here. Where it does
    not supersede, the key is left alone: plain F1 opens Edge's own help and
    stays Edge's, so HomerView's documentation uses F1 with a modifier instead.
  - Where Edge has two keys for one thing, one of them may be taken. F4 selects
    the address bar, and so do Control+L and Alt+D, so F4 is available.
  - Where a key resembles one that already exists, the resemblance is the
    mnemonic. F9 is Edge's reading view, so Shift+F9 makes HomerView's own.
  - Fewer modifiers is better, because it is easier to press.
  - An Office convention is worth adopting: F1 for documentation, F3 for
    finding again, F8 for selecting.
  - Several rarely used commands that answer one question belong on one key
    with a picker, not on several keys. Checking a page for accessibility is
    one command that asks which engine, not two commands.

## What a description says

Present tense, one sentence, a full stop, and a verb somewhere in it, though
not necessarily at the front. Where the key is not obvious the description says
why that key, because the reader who has to look a command up should come away
able to remember it.

## The shape of the key tells you where it works

A single letter or a plain modifier works inside a HomerView page, where
nothing else is listening. Alt+NVDA works anywhere, because NVDA takes those
before any program sees them. A command with both has the short key for the
page and the long one for everywhere else.
"""

# Each entry: script name, then the command's name, its keys, and what it does.
# An empty key list means the command is reachable from the Alternate Menu only,
# which is right for anything used once in a while.
lCommands = [
    # --- Getting started, and finding your way about ---------------------
    ("launchHomerView", "Launch HomerView", ["kb:alt+control+shift+h"],
     "Launches or reconnects the HomerView copy of Microsoft Edge. "
     "H for HomerView, and it works anywhere because nothing is running yet."),
    ("alternateMenu", "Alternate Menu", ["kb:alt+f10"],
     "Present all commands in a single, alphabetized list. F10 opens a menu bar "
     "in Windows, and this is the menu HomerView has instead."),
    ("hotkeySummary", "Hotkey Summary", ["kb:alt+shift+h"],
     "Display this list of command names, hot keys, and descriptions in a new "
     "window, as EdSharp does on the same key."),

    # --- The documentation, all on F1, as Windows programs have always done
    ("showHelp", "User Guide", ["kb:control+f1"],
     "Open Documentation in the HomerView window. F1 is help everywhere, but "
     "plain F1 opens Edge's own help and stays Edge's, so the family here takes "
     "F1 with a modifier."),
    ("openQuickStart", "Quick Start", ["kb:alt+shift+f1"],
     "Open the first ten minutes of HomerView, for somebody new to it."),
    ("showHistory", "History of Changes", ["kb:shift+f1"],
     "Display list of fixes and improvements."),
    ("showAbout", "About HomerView", ["kb:alt+f1"],
     "Display version and release date, and where HomerView keeps its files."),
    ("openDeveloperNotes", "Developer Notes", ["kb:control+shift+f1"],
     "Open the notes on how HomerView is built and why."),
    ("openHotkeyDocument", "Hotkey Document", [],
     "Open the shipped list of every command, key and description. Hotkey Summary "
     "on Alt+Shift+H builds the same list from the program itself; this opens the "
     "copy that came with it."),
    ("openAnnouncement", "Project Announcement", [],
     "Open the short description of HomerView, for passing on to somebody who has "
     "not met it."),
    ("logToClipboard", "Log to Clipboard", ["kb:alt+shift+l"],
     "Copy the HomerView log to the clipboard as a file, so Control+V attaches it "
     "to an email rather than typing its name into one. L for Log, beside the "
     "other Control+Shift keys that put something somewhere."),
    ("openLog", "Session Log", ["kb:control+shift+l"],
     "Open a copy of this session's log, for working out what went wrong."),

    # --- Changing how HomerView behaves ----------------------------------
    ("chooseBrowser", "Choose Browser", ["kb:alt+shift+b"],
     "Choose which Chromium browser HomerView drives, from the ones installed "
     "here. B for Browser, and Alt+Shift with a letter is where the settings "
     "commands live because they are used once and then not again for months."),
    ("openSettings", "HomerView Settings", ["kb:alt+shift+s"],
     "Open the settings file, HomerView.inix, in a text editor. Everything the "
     "settings panel changes is in it, and a comment beside each value says what "
     "it does."),

    # --- Moving through a page -------------------------------------------
    ("moveToMainContent", "Jump to Main", ["kb:j", "kb:NVDA+alt+j"],
     "Jumps to the main content the page declares. J for Jump, and it is one of "
     "only three letters NVDA leaves free in a page."),
    ("proxyMainContent", "Jump to Probable Main", ["kb:shift+j"],
     "Finds the main content of a page that declares none, by weighing every part "
     "of it, and says that it inferred rather than was told."),
    ("nextSentence", "Next Sentence", ["kb:alt+downarrow"],
     "Moves to the next sentence and reads it. Alt with an arrow moves by "
     "something larger than a line and smaller than a paragraph."),
    ("priorSentence", "Prior Sentence", ["kb:alt+uparrow"],
     "Moves to the previous sentence and reads it."),
    ("nextParagraph", "Next Paragraph", ["kb:control+downarrow"],
     "Moves to the next paragraph and reads it. Control with an arrow moves by "
     "paragraph in Word and in most editors."),
    ("priorParagraph", "Prior Paragraph", ["kb:control+uparrow"],
     "Moves to the previous paragraph and reads it."),
    ("nextSameType", "Next Same Kind", ["kb:z"],
     "Moves to the next thing of the same kind as the one you are on, whatever "
     "that is. Z because NVDA leaves it free, and JAWS does this with S."),
    ("priorSameType", "Prior Same Kind", ["kb:shift+z"],
     "Moves to the previous thing of the same kind as the one you are on."),
    ("nextDifferentType", "Next Different Kind", ["kb:alt+z"],
     "Moves to the next thing of a different kind, which JAWS does with D."),
    ("priorDifferentType", "Prior Different Kind", ["kb:alt+shift+z"],
     "Moves to the previous thing of a different kind."),
    ("goToPercent", "Go to Percent", ["kb:control+g"],
     "Go to percentage point in document, as EdSharp does on the same key."),
    ("goToPercentAgain", "Go to Percent Again", ["kb:alt+g"],
     "Repeat Go command, or move a step further with plus or minus."),

    # --- Finding ----------------------------------------------------------
    ("findText", "Forward Find", ["kb:control+f"],
     "Search forward for string, using NVDA's own find so the dialog and its "
     "behaviour are the ones you already know."),
    ("findTextBackwards", "Reverse Find", ["kb:control+shift+f"],
     "Search backward for string."),
    ("findByPattern", "Forward Find with Regular Expression", ["kb:control+f3"],
     "Search forward for regular expression, which NVDA's own find cannot do."),
    ("findByPatternBackwards", "Reverse Find with Regular Expression",
     ["kb:control+shift+f3"],
     "Search backward for regular expression."),
    ("findAgain", "Forward Find Again", ["kb:f3"],
     "Search forward for next match, of whichever kind of find was used last."),
    ("findAgainBackwards", "Reverse Find Again", ["kb:shift+f3"],
     "Search backward for previous match."),
    ("findWordAtCursor", "Forward Find at Cursor", ["kb:alt+f3"],
     "Search forward for chunk or selected text, on the key EdSharp uses for it."),
    ("findWordAtCursorBackwards", "Reverse Find at Cursor", ["kb:alt+shift+f3"],
     "Search backward for chunk or selected text."),

    # --- Lists of things on the page --------------------------------------
    ("listHeadings", "List Headings", ["kb:NVDA+f6"],
     "List the headings on the page, on the key JAWS uses for its heading list."),
    ("listFormFields", "List Form Fields", ["kb:NVDA+f5"],
     "List the form fields on the page, on the key JAWS uses for its form field "
     "list."),
    ("listLinks", "List Links", ["kb:NVDA+shift+f7"],
     "List the links on the page, beside the key JAWS uses for its link list."),
    ("listAnyElements", "List Elements", ["kb:NVDA+alt+l"],
     "Lists any kind of element, including kinds NVDA's own Elements List does "
     "not offer. L for List."),
    ("explorePage", "Explore Page", ["kb:NVDA+alt+e"],
     "Describes how the page is laid out, including what a sighted person can see "
     "that your reading order never mentions. E for Explore. It gave up its bare "
     "Y: a single letter in browse mode reads as a navigation key, and this "
     "command does not move anywhere."),

    # --- Asking about the page --------------------------------------------
    ("reportPageAddress", "Say Address", ["kb:alt+a"],
     "Says the web address of this page. Twice spells it, three times copies it. "
     "A for Address."),
    ("reportAddressAnywhere", "Say Address Anywhere", ["kb:NVDA+alt+u"],
     "Says the web address from anywhere in the window, including the address bar."),
    ("pageInformation", "Say Metadata", ["kb:alt+m"],
     "Says what the page claims about itself: author, publisher, date and licence. "
     "M for Metadata."),
    ("sayPosition", "Say Position", ["kb:alt+delete", "kb:alt+numpadDelete"],
     "Says the line, column and percentage position of the cursor. Delete sits "
     "among the navigation keys, which is where a position question belongs."),
    ("sayYield", "Say Yield", ["kb:alt+y"],
     "Say number of characters, words, and lines in all or selected text."),
    ("sayYieldStructure", "Say Yield Structure", ["kb:alt+shift+y"],
     "Says how the page is built: how many headings, links, forms and the rest."),
    ("sayYieldPattern", "Yield with Regular Expression", ["kb:control+shift+y"],
     "Count parts of text matching a regular expression, which answers how many "
     "rather than where."),
    ("urlReference", "Say Url", ["kb:alt+u"],
     "Say where the link at the cursor would go. U for url."),
    ("describeLinkTarget", "Link Target", ["kb:alt+l"],
     "Ask what is actually at that link without going there: what kind of thing, "
     "how big, and whether it ends up where it claims. L for Link."),
    ("pageUrls", "Page Links to Clipboard", ["kb:alt+shift+p"],
     "Copy every link address on the page to the clipboard, as EdSharp copies a "
     "path on the same key."),
    ("sayTime", "Say Time", ["kb:alt+;"],
     "Say current time and date."),

    # --- Reading -----------------------------------------------------------
    ("readAll", "Read All", ["kb:alt+f8"],
     "Say all text, without moving the cursor."),
    ("toggleSayAll", "Toggle Reading", ["kb:scrolllock"],
     "Starts reading continuously, or stops if it is already reading. Scroll Lock "
     "because nothing else in Edge, NVDA or Windows wants it."),
    ("saySelected", "Say Selected", ["kb:shift+space"],
     "Say selected text, or spell if repeated."),
    ("sayChunk", "Say Chunk", ["kb:shift+backspace"],
     "Say chunk at cursor, or spell if repeated."),

    # --- Selecting and the clipboard ---------------------------------------
    ("startSelection", "Start Selection", ["kb:f8"],
     "Mark starting point of text to be selected, so Shift need not be held while "
     "you move."),
    ("completeSelection", "Complete Selection", ["kb:shift+f8"],
     "Select text from starting point to cursor."),
    ("goToSelectionStart", "Go to Start of Selection", ["kb:alt+shift+f8"],
     "Return to start position of selection."),
    ("selectChunk", "Select Chunk", ["kb:control+space"],
     "Select contiguous sequence of non-blank characters at cursor, or select the "
     "next chunk if a selection already exists."),
    ("copyAll", "Copy All", ["kb:control+f8"],
     "Copy all text to clipboard."),
    ("copyLineOrSelection", "Copy Line", ["kb:control+c"],
     "Copy selected text to clipboard, or copy current line if no selection."),
    ("copyAppend", "Copy Append", ["kb:alt+c"],
     "Append selected text to clipboard, or append current line if no selection."),
    ("quoteClipboard", "Say Clipboard", ["kb:alt+'"],
     "Say clipboard text, or spell if repeated. The apostrophe is a quotation "
     "mark, and a clipboard holds a quotation."),
    ("saveClipboard", "Save Clipboard", ["kb:control+'"],
     "Saves the clipboard to a text file, proposing a name."),
    ("appendClipboard", "Append Clipboard", ["kb:control+shift+'"],
     "Adds the clipboard to the end of a text file rather than replacing it."),
    ("clearClipboard", "Clear Clipboard", ["kb:alt+shift+'"],
     "Empties the clipboard, so an append starts afresh."),

    # --- Doing things to the page -------------------------------------------
    ("openOtherFormat", "Open Document", ["kb:control+o"],
     "Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a "
     "page so every command here works on it. Control+O opens in every program; "
     "this one opens more."),
    ("saveAs", "Save Page", ["kb:control+s"],
     "Saves the page in any of nine formats. Control+S saves in every program; "
     "this one saves more ways."),
    ("extractMainContent", "Extract Main Content", ["kb:shift+f9"],
     "Extracts the readable part of the page into a page of its own that you can "
     "search, save or send. F9 is Edge's own reading view, and Shift+F9 is "
     "HomerView's, which works on pages Edge will not."),
    ("downloadFiles", "Web Download", ["kb:alt+shift+w"],
     "Pick files to download from a web page, on the key EdSharp uses for it."),
    ("openPageFolder", "Page Folder", ["kb:alt+shift+f"],
     "Open this page's folder in File Explorer, to browse what was saved from it. "
     "Nothing is created: if nothing has been saved from this page, it says so. "
     "Alt+Shift+F, beside Alt+Shift+W which fills the folder."),
    ("submitForm", "Submit Form", ["kb:control+enter"],
     "Submits the form you are filling in, from any field in it, so you need not "
     "find the button."),
    ("actOnPage", "Invoke Script", ["kb:alt+i"],
     "Carries out instructions written in ordinary words, such as click sign in. "
     "I for Invoke."),
    ("runAccessibilityCheck", "Check Accessibility", ["kb:alt+shift+a"],
     "Tests the page for accessibility problems, asking which engine to use, and "
     "offers to report what it finds to whoever publishes the site. A for "
     "Accessibility."),
    ("openCopilot", "Consult Copilot", ["kb:NVDA+alt+c"],
     "Copies the page text and opens Edge's Copilot sidebar, ready for a question. "
     "C for Copilot."),
    ("webUtilities", "Query Web", ["kb:alt+q", "kb:NVDA+alt+q"],
     "Looks something up using free services that need no account: a definition, "
     "a place, the weather, a book. Q for Query."),
    ("dismissDialog", "Dismiss Dialog", ["kb:alt+shift+d"],
     "Closes a browser dialog that is blocking the window. D for Dismiss, and it "
     "works anywhere because a dialog is what has the focus."),

    # --- The window and its tabs ---------------------------------------------
    ("chooseTab", "Tab List", ["kb:f4"],
     "Lists the HomerView tabs and switches to the one you choose. F4 is the Homer "
     "window list, and Edge has two other keys for what F4 does there."),
    ("sayTabs", "Tab Names", ["kb:shift+f4"],
     "Says the names of the open tabs without moving the keyboard anywhere."),
    ("closeOtherTabs", "Tab Close Others", ["kb:control+shift+f4"],
     "Closes every tab but the one you are reading. Control+F4 closes one tab, so "
     "Control+Shift+F4 closes the rest."),

    # --- Speech, all on the accent key ----------------------------------------
    ("speakFaster", "Voice Faster", ["kb:control+`"],
     "Increase the voice rate. The accent key carries the whole speech family, "
     "as it does in EdSharp."),
    ("speakSlower", "Voice Slower", ["kb:control+shift+`"],
     "Decrease the voice rate."),
    ("speakLouder", "Voice Louder", ["kb:alt+`"],
     "Increase the voice volume."),
    ("speakSofter", "Voice Softer", ["kb:alt+shift+`"],
     "Decrease the voice volume."),
    ("togglePunctuation", "Toggle Punctuation", ["kb:control+shift+`"],
     "Toggle the voice between all and no punctuation."),
    ("reportSpeechSettings", "Speech Settings", ["kb:shift+`"],
     "Reports the punctuation level, the rate and the volume."),

    # --- Occasional, and reached from the Alternate Menu ----------------------
    ("elevateVersion", "Elevate Version", ["kb:control+f11", "kb:NVDA+alt+f11"],
     "Checks whether a newer HomerView exists and installs it."),
    ("recentPages", "Recent Pages", ["kb:alt+r"],
     "Open a page from the list of those recently used, on the key EdSharp uses "
     "for its recent files."),
    ("reportConnection", "Report Connection", [],
     "Says whether HomerView is connected to the browser, and how."),
    ("selfTest", "Self Test", [],
     "Checks that all three ways of reaching the browser are working."),
]

# Anything reached only from within another command, so it needs a name and a
# description but no key of its own.
lFolded = [
    ("listNames", "List Names", ["kb:alt+n"],
     "Lists the people, places, organisations and dates a page mentions, saved "
     "as Names.htm in the page's folder and opened. A rule-based engine reads "
     "the text, so it guesses; the report says so."),
    ("findContacts", "Find Contacts", ["kb:alt+shift+c"],
     "Finds who to tell about this site: email addresses, the accessibility "
     "statement, contact pages and social media. Looks at this page, the home "
     "page, and the addresses a statement usually lives at."),
    ("accessibilityReport", "Report Accessibility",
     "Tests the page and writes a report addressed to whoever publishes the site. "
     "Reached by Check Accessibility once an engine is chosen."),
    ("runAxe", "Check with Axe",
     "Tests the page with Deque's axe-core engine. Offered by Check Accessibility."),
    ("runIbmChecker", "Check with Equal Access",
     "Tests the page with IBM's Equal Access engine. Offered by Check Accessibility."),
]


# How the commands are grouped for a reader, by what somebody is trying to do
# rather than by where the code keeps them. The order is the order a person
# meets them: starting, then reading, then acting, then the occasional.
#
# Both the Hotkey Summary command and the published list use this, so the two
# cannot disagree about what belongs where.
lGroups = [
    ("Starting HomerView", [
        "launchHomerView", "alternateMenu", "hotkeySummary"]),
    ("Reading the documentation", [
        "showHelp", "openQuickStart", "showHistory", "showAbout",
        "openDeveloperNotes", "openHotkeyDocument", "openAnnouncement", "openLog",
        "logToClipboard"]),
    ("Moving through a page", [
        "moveToMainContent", "proxyMainContent", "nextSentence", "priorSentence",
        "nextParagraph", "priorParagraph", "nextSameType", "priorSameType",
        "nextDifferentType", "priorDifferentType", "goToPercent", "goToPercentAgain"]),
    ("Finding text", [
        "findText", "findTextBackwards", "findByPattern", "findByPatternBackwards",
        "findAgain", "findAgainBackwards", "findWordAtCursor",
        "findWordAtCursorBackwards"]),
    ("Listing what is on the page", [
        "listHeadings", "listFormFields", "listLinks", "listAnyElements",
        "explorePage"]),
    ("Asking about the page", [
        "reportPageAddress", "reportAddressAnywhere", "pageInformation",
        "sayPosition", "sayYield", "sayYieldStructure", "sayYieldPattern",
        "urlReference", "describeLinkTarget", "pageUrls", "sayTime"]),
    ("Reading aloud", [
        "readAll", "toggleSayAll", "saySelected", "sayChunk"]),
    ("Selecting and the clipboard", [
        "startSelection", "completeSelection", "goToSelectionStart", "selectChunk",
        "copyAll", "copyLineOrSelection", "copyAppend", "quoteClipboard",
        "saveClipboard", "appendClipboard", "clearClipboard"]),
    ("Acting on the page", [
        "openOtherFormat", "saveAs", "extractMainContent", "downloadFiles",
        "submitForm", "actOnPage", "runAccessibilityCheck", "openCopilot",
        "webUtilities", "dismissDialog", "runAxe", "runIbmChecker",
        "accessibilityReport", "findContacts", "listNames"]),
    ("The window and its tabs", [
        "chooseTab", "sayTabs", "closeOtherTabs"]),
    ("Adjusting the voice", [
        "speakFaster", "speakSlower", "speakLouder", "speakSofter",
        "togglePunctuation", "reportSpeechSettings"]),
    ("Changing how HomerView behaves", [
        "chooseBrowser", "openSettings"]),
    ("Now and then", [
        "elevateVersion", "recentPages", "reportConnection", "selfTest"]),
]


def grouped():
    """Every command in reading order, grouped, with nothing left out.

    Anything the grouping forgot lands in a final group rather than vanishing,
    because a command missing from the list a reader is given is worse than a
    command in a slightly odd place.
    """
    dByScript = byScript()
    setPlaced = {s for _sTitle, lNames in lGroups for s in lNames}
    lResult = []
    for sTitle, lNames in lGroups:
        lEntries = [(s, dByScript[s]) for s in lNames if s in dByScript]
        if lEntries:
            lResult.append((sTitle, lEntries))
    lLeft = [(s, dByScript[s]) for s in sorted(dByScript) if s not in setPlaced]
    if lLeft:
        lResult.append(("Everything else", lLeft))
    return lResult


def byScript():
    """The table keyed by script name, which is how the code reaches it."""
    dByScript = {}
    for sScript, sName, lKeys, sDescription in lCommands:
        dByScript[sScript] = {
            "description": sDescription,
            "keys": list(lKeys),
            "name": sName,
        }
    # BOTH SHAPES, BECAUSE THE TABLE HOLDS BOTH. lFolded was meant for
    # commands with no key of their own, three fields to a row -- and two
    # rows have since acquired a key and a fourth field. Unpacking three
    # raised ValueError on the fourth, which broke makeDocs outright and,
    # worse, would have been swallowed anywhere the call sits inside a try.
    #
    # Reading the row by its length accepts what is actually there. The
    # alternative, moving those two rows back to lCommands, is a change to
    # what the table means that would have to be made again the next time
    # somebody adds a key to a folded command.
    for oRow in lFolded:
        if len(oRow) == 4:
            sScript, sName, lKeys, sDescription = oRow
        else:
            sScript, sName, sDescription = oRow
            lKeys = []
        dByScript[sScript] = {
            "description": sDescription,
            "keys": list(lKeys),
            "name": sName,
        }
    return dByScript


# Scripts that live on the global plugin rather than on the page buffer. Their
# keys are bound there even without the NVDA modifier, because that is where the
# script is; the plugin gates them to HomerView's own browser by process, which
# is what stops Control+S acting on a HomerView page from an unrelated window.
# Commands that must answer from anywhere, page or not: launching, the menu,
# and the few things a reader needs when no page has focus.
setAnywhereScripts = {
    "alternateMenu", "dismissDialog", "elevateVersion",
    "launchHomerView", "openAnnouncement", "openCopilot", "openHotkeyDocument",
    "recentPages", "reportAddressAnywhere", "reportConnection", "selfTest",
    "webUtilities",
}

setGlobalScripts = {
    "downloadFiles", "extractMainContent", "logToClipboard", "openDeveloperNotes",
    "openLog",
    "openQuickStart", "saveAs", "submitForm",
}


def pageGestures():
    """The gestures that belong to a HomerView page, keyed by gesture."""
    dGestures = {}
    for sScript, _sName, lKeys, _sDescription in lCommands:
        # A command bound on the global plugin is not bound here as well, or
        # both would answer the same key and which one won would depend on
        # where the focus happened to be.
        if sScript in setGlobalScripts or sScript in setAnywhereScripts:
            continue
        # Both kinds. A page command may have an NVDA key as well, and the
        # buffer binds it in the same map: the key still only reaches this
        # class, which is what scopes it to a HomerView page.
        for sKey in lKeys:
            dGestures[sKey] = sScript
    return dGestures


def globalGestures():
    """The gestures bound on the global plugin, keyed by script name."""
    dGestures = {}
    for sScript, _sName, lKeys, _sDescription in lCommands:
        # Only what the global plugin owns. A page command's NVDA key is bound
        # on the buffer, not here, or the two would both answer it.
        lGlobal = lKeys if sScript in setGlobalScripts else []
        if sScript in setAnywhereScripts:
            lGlobal = list(lKeys)
        if lGlobal:
            dGestures[sScript] = lGlobal
    return dGestures

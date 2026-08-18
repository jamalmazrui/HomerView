---
title: HomerView Hotkeys
subtitle: Every command, both screen readers, and why that key
author: Jamal Mazrui
---

# About this list

Every HomerView command, grouped by what you are trying to do and sorted by
name inside each group. Each entry gives the NVDA key, the JAWS key, and, where
the key is not obvious, why it is that key.

The two implementations are kept at parity deliberately. Neither is the
reference one. Where a key differs between them, it differs for a reason, and
the reason is given below.

The same list is in the guide, HomerView.md, as one of its sections. This file
is here so you can keep it open beside your work.

Press Alt+Shift+H in HomerView and the program builds its own list, from its own
key map, so what it tells you is never out of date. This document is generated
from the same two sources — the NVDA command table and the JAWS key map — so it
cannot drift from them either.

An analysis of the consistency, the gaps and the trade-offs is at the end.

# How to read a key

Modifiers come in alphabetical order: Alt, Control, JAWSKey, NVDA, Shift. So
Alt+NVDA+H, never NVDA+Alt+H. Key names are the ones JAWS uses, because most
blind Windows users have read those for years, so Accent rather than Grave and
SemiColon rather than semicolon.

**Where each command works.** Most act at the reading cursor — Start and
Complete Selection, Copy Line, Link Target, Jump to Probable Main, and the find
family — and they need the reading cursor to be active, because outside it there
is no cursor for them to act at. Control+C especially must go on meaning copy in
a form field.

A few act on the page, the window or the program instead: Copy All, Say
Metadata, Page Links and Tab Names. **On NVDA these also work outside browse
mode**, so they answer in the address bar and in form fields, and only inside
HomerView's own browser. On JAWS they are still scoped to the virtual cursor;
the mechanism that would extend them needs HomerView's scripts chained into
Edge's own script set, which is not done yet.

**JAWSKey** is Insert, or Caps Lock if you have set JAWS that way. **NVDA** is
whichever key you have set as the NVDA modifier. The two play the same part, so
a command on Alt+NVDA+H is on Alt+JAWSKey+H, and this document writes each in
its own vocabulary rather than pretending they are one key.

Where a command has two keys, the short one works inside a HomerView page and
the long one works anywhere.

A command with no key still runs, from the Alternate Menu on Alt+NVDA+F10 or
Alt+JAWSKey+F10. On NVDA you can give it a key in the Input Gestures dialog,
under the HomerView category. On JAWS you can add it to your own default.jkm.

**Not yet on JAWS** means the command exists on NVDA and has not been written
for JAWS. **Not yet on NVDA** means the reverse. Both are listed rather than
hidden, because a gap you can see is one that can be closed.

# Starting HomerView

- **Alternate Menu**
    - NVDA: Alt+NVDA+F10
    - JAWS: Alt+JAWSKey+F10
    - Present all commands in a single, alphabetized list. F10 opens a menu bar in Windows, and this is the menu HomerView has instead.
- **Hotkey Summary**
    - NVDA: Alt+Shift+H
    - JAWS: Alt+Shift+H
    - Display this list of command names, hot keys, and descriptions in a new window, as EdSharp does on the same key.
- **Launch HomerView**
    - NVDA: Alt+NVDA+H
    - JAWS: Alt+JAWSKey+H
    - Launches or reconnects the HomerView copy of Microsoft Edge. H for HomerView, and it works anywhere because nothing is running yet.

# Reading the documentation

- **About HomerView**
    - NVDA: Alt+F1
    - JAWS: Alt+F1
    - Display version and release date, and where HomerView keeps its files.
- **Developer Notes**
    - NVDA: Control+Shift+F1
    - JAWS: Control+Shift+F1
    - Open the notes on how HomerView is built and why.
- **History of Changes**
    - NVDA: Shift+F1
    - JAWS: Shift+F1
    - Display list of fixes and improvements.
- **Hotkey Document**
    - NVDA: no key
    - JAWS: no key, on the Alternate Menu
    - Open the shipped list of every command, key and description. Hotkey Summary on Alt+Shift+H builds the same list from the program itself; this opens the copy that came with it.
- **Log to Clipboard**
    - NVDA: Control+Shift+L
    - JAWS: Alt+JAWSKey+L
    - Copy the HomerView log to the clipboard as a file, so Control+V attaches it to an email rather than typing its name into one. L for Log, beside the other Control+Shift keys that put something somewhere.
- **Project Announcement**
    - NVDA: no key
    - JAWS: no key, on the Alternate Menu
    - Open the short description of HomerView, for passing on to somebody who has not met it.
- **Quick Start**
    - NVDA: Alt+Shift+F1
    - JAWS: Alt+Shift+F1
    - Open the first ten minutes of HomerView, for somebody new to it.
- **Session Log**
    - NVDA: Alt+Control+F1
    - JAWS: Alt+Control+F1
    - Open a copy of this session's log, for working out what went wrong.
- **User Guide**
    - NVDA: Control+F1
    - JAWS: Control+F1
    - Open Documentation in the HomerView window. F1 is help everywhere, but plain F1 opens Edge's own help and stays Edge's, so the family here takes F1 with a modifier.

# Moving through a page

- **Go to Percent**
    - NVDA: Control+G
    - JAWS: **not yet on JAWS**
    - Go to percentage point in document, as EdSharp does on the same key.
- **Go to Percent Again**
    - NVDA: Alt+G
    - JAWS: **not yet on JAWS**
    - Repeat Go command, or move a step further with plus or minus.
- **Jump to Main**
    - NVDA: J, or Alt+NVDA+J
    - JAWS: **not yet on JAWS**
    - Jumps to the main content the page declares. J for Jump, and it is one of only three letters NVDA leaves free in a page.
- **Jump to Probable Main**
    - NVDA: Shift+J
    - JAWS: Shift+Q
    - Finds the main content of a page that declares none, by weighing every part of it, and says that it inferred rather than was told.
- **Next Different Kind**
    - NVDA: Alt+Z
    - JAWS: **not yet on JAWS**
    - Moves to the next thing of a different kind, which JAWS does with D.
- **Next Paragraph**
    - NVDA: Control+DownArrow
    - JAWS: **not yet on JAWS**
    - Moves to the next paragraph and reads it. Control with an arrow moves by paragraph in Word and in most editors.
- **Next Same Kind**
    - NVDA: Z
    - JAWS: **not yet on JAWS**
    - Moves to the next thing of the same kind as the one you are on, whatever that is. Z because NVDA leaves it free, and JAWS does this with S.
- **Next Sentence**
    - NVDA: Alt+DownArrow
    - JAWS: **not yet on JAWS**
    - Moves to the next sentence and reads it. Alt with an arrow moves by something larger than a line and smaller than a paragraph.
- **Prior Different Kind**
    - NVDA: Alt+Shift+Z
    - JAWS: **not yet on JAWS**
    - Moves to the previous thing of a different kind.
- **Prior Paragraph**
    - NVDA: Control+UpArrow
    - JAWS: **not yet on JAWS**
    - Moves to the previous paragraph and reads it.
- **Prior Same Kind**
    - NVDA: Shift+Z
    - JAWS: **not yet on JAWS**
    - Moves to the previous thing of the same kind as the one you are on.
- **Prior Sentence**
    - NVDA: Alt+UpArrow
    - JAWS: **not yet on JAWS**
    - Moves to the previous sentence and reads it.

# Finding text

- **Extract with Regular Expression**
    - NVDA: Control+Shift+E
    - JAWS: Control+Shift+E
    - Gathers every match of a pattern for reading, each separated by a form feed between blank lines.
- **Forward Find**
    - NVDA: Control+F
    - JAWS: **not yet on JAWS**
    - Search forward for string, using NVDA's own find so the dialog and its behaviour are the ones you already know.
- **Forward Find Again**
    - NVDA: F3
    - JAWS: F3
    - Search forward for next match, of whichever kind of find was used last.
- **Forward Find at Cursor**
    - NVDA: Alt+F3
    - JAWS: **not yet on JAWS**
    - Search forward for chunk or selected text, on the key EdSharp uses for it.
- **Forward Find with Regular Expression**
    - NVDA: Control+F3
    - JAWS: Control+F3
    - Search forward for regular expression, which NVDA's own find cannot do.
- **Reverse Find**
    - NVDA: Control+Shift+F
    - JAWS: Control+Shift+F (named "Reverse Find for Text" there)
    - Search backward for string.
- **Reverse Find Again**
    - NVDA: Shift+F3
    - JAWS: Shift+F3
    - Search backward for previous match.
- **Reverse Find at Cursor**
    - NVDA: Alt+Shift+F3
    - JAWS: **not yet on JAWS**
    - Search backward for chunk or selected text.
- **Reverse Find with Regular Expression**
    - NVDA: Control+Shift+F3
    - JAWS: Control+Shift+F3
    - Search backward for regular expression.

# Listing what is on the page

- **Explore Page**
    - NVDA: Alt+NVDA+E
    - JAWS: **not yet on JAWS**
    - Describes how the page is laid out, including what a sighted person can see that your reading order never mentions. E for Explore. It gave up its bare Y: a single letter in browse mode reads as a navigation key, and this command does not move anywhere.
- **List Elements**
    - NVDA: Alt+NVDA+L
    - JAWS: **not yet on JAWS**
    - Lists any kind of element, including kinds NVDA's own Elements List does not offer. L for List.
- **List Form Fields**
    - NVDA: NVDA+F5
    - JAWS: **not yet on JAWS**
    - List the form fields on the page, on the key JAWS uses for its form field list.
- **List Headings**
    - NVDA: NVDA+F6
    - JAWS: **not yet on JAWS**
    - List the headings on the page, on the key JAWS uses for its heading list.
- **List Links**
    - NVDA: NVDA+Shift+F7
    - JAWS: **not yet on JAWS**
    - List the links on the page, beside the key JAWS uses for its link list.

# Asking about the page

- **Link Target**
    - NVDA: Alt+L
    - JAWS: Alt+L
    - Ask what is actually at that link without going there: what kind of thing, how big, and whether it ends up where it claims. L for Link.
- **List Names**
    - NVDA: Alt+N
    - JAWS: Alt+N
    - Lists the people, places, organisations and dates a page mentions. A rule-based engine reads the text, so it guesses; the report says so.
- **Page Links to Clipboard**
    - NVDA: Alt+Shift+P
    - JAWS: Alt+Shift+P
    - Copy every link address on the page to the clipboard, as EdSharp copies a path on the same key.
- **Say Address**
    - NVDA: Alt+A
    - JAWS: **not yet on JAWS**
    - Says the web address of this page. Twice spells it, three times copies it. A for Address.
- **Say Address Anywhere**
    - NVDA: Alt+NVDA+U
    - JAWS: **not yet on JAWS**
    - Says the web address from anywhere in the window, including the address bar.
- **Say Metadata**
    - NVDA: Alt+M
    - JAWS: Alt+M
    - Says what the page claims about itself: author, publisher, date and licence. M for Metadata.
- **Say Position**
    - NVDA: Alt+Delete, or Alt+NumPadDelete
    - JAWS: **not yet on JAWS**
    - Says the line, column and percentage position of the cursor. Delete sits among the navigation keys, which is where a position question belongs.
- **Say Time**
    - NVDA: Alt+SemiColon
    - JAWS: **not yet on JAWS**
    - Say current time and date.
- **Say Url**
    - NVDA: Alt+U
    - JAWS: **not yet on JAWS**
    - Say where the link at the cursor would go. U for url.
- **Say Yield**
    - NVDA: Alt+Y
    - JAWS: **not yet on JAWS**
    - Say number of characters, words, and lines in all or selected text.
- **Say Yield Structure**
    - NVDA: Alt+Shift+Y
    - JAWS: **not yet on JAWS**
    - Says how the page is built: how many headings, links, forms and the rest.
- **Yield with Regular Expression**
    - NVDA: Control+Shift+Y
    - JAWS: **not yet on JAWS**
    - Count parts of text matching a regular expression, which answers how many rather than where.

# Reading aloud

- **Read All**
    - NVDA: Alt+F8
    - JAWS: Alt+F8
    - Say all text, without moving the cursor.
- **Say Chunk**
    - NVDA: Shift+Backspace
    - JAWS: **not yet on JAWS**
    - Say chunk at cursor, or spell if repeated.
- **Say Selected**
    - NVDA: Shift+Space
    - JAWS: **not yet on JAWS**
    - Say selected text, or spell if repeated.
- **Toggle Reading**
    - NVDA: ScrollLock
    - JAWS: **not yet on JAWS**
    - Starts reading continuously, or stops if it is already reading. Scroll Lock because nothing else in Edge, NVDA or Windows wants it.

# Selecting and the clipboard

- **Append Clipboard**
    - NVDA: Control+Shift+Apostrophe
    - JAWS: Control+Shift+Apostrophe
    - Adds the clipboard to the end of a text file rather than replacing it.
- **Clear Clipboard**
    - NVDA: Alt+Shift+Apostrophe
    - JAWS: Alt+Shift+Apostrophe
    - Empties the clipboard, so an append starts afresh.
- **Complete Selection**
    - NVDA: Shift+F8
    - JAWS: Shift+F8
    - Select text from starting point to cursor.
- **Copy All**
    - NVDA: Control+F8
    - JAWS: Control+F8
    - Copy all text to clipboard.
- **Copy Append**
    - NVDA: Alt+C
    - JAWS: Alt+C
    - Append selected text to clipboard, or append current line if no selection.
- **Copy Line**
    - NVDA: Control+C
    - JAWS: Control+C (named "Copy Selection" there)
    - Copy selected text to clipboard, or copy current line if no selection.
- **Go to Start of Selection**
    - NVDA: Alt+Shift+F8
    - JAWS: **not yet on JAWS**
    - Return to start position of selection.
- **Save Clipboard**
    - NVDA: Control+Apostrophe
    - JAWS: Control+Apostrophe
    - Saves the clipboard to a text file, proposing a name.
- **Say Clipboard**
    - NVDA: Alt+Apostrophe
    - JAWS: Alt+Apostrophe
    - Say clipboard text, or spell if repeated. The apostrophe is a quotation mark, and a clipboard holds a quotation.
- **Select Chunk**
    - NVDA: Control+Space
    - JAWS: **not yet on JAWS**
    - Select contiguous sequence of non-blank characters at cursor, or select the next chunk if a selection already exists.
- **Start Selection**
    - NVDA: F8
    - JAWS: F8
    - Mark starting point of text to be selected, so Shift need not be held while you move.

# Acting on the page

- **Check Accessibility**
    - NVDA: Alt+NVDA+A
    - JAWS: Alt+JAWSKey+A
    - Tests the page for accessibility problems, asking which engine to use, and offers to report what it finds to whoever publishes the site. A for Accessibility.
- **Check with Axe**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Tests the page with Deque's axe-core engine. Offered by Check Accessibility.
- **Check with Equal Access**
    - NVDA: no key
    - JAWS: Alt+JAWSKey+I (named "Check Accessibility with IBM" there)
    - Tests the page with IBM's Equal Access engine. Offered by Check Accessibility.
- **Consult Copilot**
    - NVDA: Alt+NVDA+C
    - JAWS: **not yet on JAWS**
    - Copies the page text and opens Edge's Copilot sidebar, ready for a question. C for Copilot.
- **Dismiss Dialog**
    - NVDA: Alt+NVDA+D
    - JAWS: Alt+JAWSKey+D
    - Closes a browser dialog that is blocking the window. D for Dismiss, and it works anywhere because a dialog is what has the focus.
- **Extract Main Content**
    - NVDA: Shift+F9
    - JAWS: Shift+F9
    - Extracts the readable part of the page into a page of its own that you can search, save or send. F9 is Edge's own reading view, and Shift+F9 is HomerView's, which works on pages Edge will not.
- **Find Contacts**
    - NVDA: Alt+NVDA+C
    - JAWS: Alt+JAWSKey+C
    - Finds who to tell about this site: email addresses, the accessibility statement, contact pages and social media.
- **Invoke Script**
    - NVDA: Alt+I
    - JAWS: **not yet on JAWS**
    - Carries out instructions written in ordinary words, such as click sign in. I for Invoke.
- **Open Document**
    - NVDA: Control+O
    - JAWS: Control+O
    - Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a page so every command here works on it. Control+O opens in every program; this one opens more.
- **Query Web**
    - NVDA: Alt+Q, or Alt+NVDA+Q
    - JAWS: **not yet on JAWS**
    - Looks something up using free services that need no account: a definition, a place, the weather, a book. Q for Query.
- **Report Accessibility**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Tests the page and writes a report addressed to whoever publishes the site. Reached by Check Accessibility once an engine is chosen.
- **Save Page**
    - NVDA: Control+S, or Alt+Control+S
    - JAWS: Control+S
    - Saves the page in any of nine formats. Control+S saves in every program; this one saves more ways.
- **Submit Form**
    - NVDA: Control+Enter
    - JAWS: **not yet on JAWS**
    - Submits the form you are filling in, from any field in it, so you need not find the button.
- **Web Download**
    - NVDA: Alt+Shift+W
    - JAWS: Alt+Shift+W
    - Pick files to download from a web page, on the key EdSharp uses for it.

# The window and its tabs

- **Page Folder**
    - NVDA: Alt+Shift+F
    - JAWS: Alt+Shift+F
    - Opens this page's folder in File Explorer, to browse what was saved from it. Nothing is created: if nothing has been saved from this page, it says so. Beside Alt+Shift+W, which fills the folder.
- **Tab Close Others**
    - NVDA: Control+Shift+F4
    - JAWS: **not yet on JAWS**
    - Closes every tab but the one you are reading. Control+F4 closes one tab, so Control+Shift+F4 closes the rest.
- **Tab List**
    - NVDA: F4
    - JAWS: no key, on the Alternate Menu
    - Lists the HomerView tabs and switches to the one you choose. F4 is the Homer window list, and Edge has two other keys for what F4 does there.
- **Tab Names**
    - NVDA: Shift+F4
    - JAWS: Shift+F4
    - Says the names of the open tabs without moving the keyboard anywhere.

# Adjusting the voice

- **Speech Settings**
    - NVDA: Shift+Accent
    - JAWS: **not yet on JAWS**
    - Reports the punctuation level, the rate and the volume.
- **Toggle Punctuation**
    - NVDA: Alt+Control+Accent
    - JAWS: **not yet on JAWS**
    - Toggle the voice between all and no punctuation.
- **Voice Faster**
    - NVDA: Control+Accent
    - JAWS: **not yet on JAWS**
    - Increase the voice rate. The accent key carries the whole speech family, as it does in EdSharp.
- **Voice Louder**
    - NVDA: Alt+Accent
    - JAWS: **not yet on JAWS**
    - Increase the voice volume.
- **Voice Slower**
    - NVDA: Control+Shift+Accent
    - JAWS: **not yet on JAWS**
    - Decrease the voice rate.
- **Voice Softer**
    - NVDA: Alt+Shift+Accent
    - JAWS: **not yet on JAWS**
    - Decrease the voice volume.

# Now and then

- **Elevate Version**
    - NVDA: Control+F11, or Alt+NVDA+F11
    - JAWS: **not yet on JAWS**
    - Checks whether a newer HomerView exists and installs it.
- **Recent Pages**
    - NVDA: Alt+R
    - JAWS: **not yet on JAWS**
    - Open a page from the list of those recently used, on the key EdSharp uses for its recent files.
- **Report Connection**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Says whether HomerView is connected to the browser, and how.
- **Self Test**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Checks that all three ways of reaching the browser are working.

# Analysis: consistency, gaps and trade-offs

This section is my own reading of the two key maps side by side, written after
generating the list above from both sources.

## The headline numbers

- **92 commands on NVDA, 43 on JAWS.** All 43 exist on both.
- **Of those 43, 38 have identical keys** once NVDA and JAWSKey are understood
  as the same modifier. On almost everything the two implementations share,
  what you learn on one you already know on the other.
- **Nothing is JAWS-only any more.** Extract with Regular Expression, Find
  Contacts and List Names were written for JAWS first and have since been
  ported, so the gap runs one way: **49 commands exist only on NVDA.**

## Where the keys differ, and whether the reason holds

Only three paired commands differ, and each is worth judging separately.

**Jump to Probable Main — NVDA Shift+J, JAWS Shift+Q.** The reason is sound and
should stay. Each screen reader has its own letter for the main region: NVDA
uses J for Jump, JAWS uses Q for the main region, and each implementation sits
the shifted key beside its host's own. Forcing one letter on both would break
the association that makes the key memorable in the first place.

**Log to Clipboard — NVDA Control+Shift+L, JAWS Alt+JAWSKey+L.** This one is not
principled, and I should say so. The JAWS key was moved to Alt+JAWSKey+L only
because plain JAWSKey+L was written into the key map, read back correctly, and
never fired — something else on the system holds it, and I gave up finding out
what. Control+Shift+L would work on JAWS and would match NVDA exactly. **This is
the one difference I would close**, and the only reason not to is that JAWS
commands which must work before a browser has loaded conventionally carry the
screen-reader modifier. That convention is worth less than the parity here.

**Check with Equal Access — NVDA no key, JAWS Alt+JAWSKey+I.** Not really a
disagreement about keys but about structure, dealt with below.

## The single-letter rule

In browse mode a bare letter is a navigation key by convention: press it and you
expect to land somewhere. So a bare letter should only ever belong to a command
that MOVES.

Five NVDA commands used one. Four of them move — Jump to Main on J, Jump to
Probable Main on Shift+J, Next Same Kind on Z, Prior Same Kind on Shift+Z — and
those are right. **Explore Page had Y and does not move anywhere**, so it has
given the letter back and keeps Alt+NVDA+E, which it already had.

The obvious alternative was NVDA+F1, by analogy with JAWS+F1 for screen
sensitive help. It is taken: NVDA+F1 opens the log viewer and shows developer
information about the current navigator object. Shift+NVDA+F1 appears free if a
key in that family is wanted later, but Alt+NVDA+E already works and a second
key for one command is clutter.

JAWS has no equivalent problem, because every HomerView key there carries a
modifier except the F8 selection pair and the F3 find pair, none of which is a
letter.

## A structural difference worth deciding on

On NVDA, **Check Accessibility** (Alt+NVDA+A) is a chooser: it asks which engine
you want, and Check with Axe and Check with Equal Access sit behind it with no
keys of their own. On JAWS, the two engines have direct keys — Alt+JAWSKey+A for
axe and Alt+JAWSKey+I for IBM — and there is no chooser at all.

Both are defensible. The chooser is tidier and keeps the key map smaller; the
direct keys are faster and mean the two engines are equally discoverable rather
than one being the default. My own view is that the **JAWS arrangement is
better**, because in practice you run the same engine repeatedly and a chooser
you answer identically every time is a keystroke tax. But the NVDA naming should
then follow: "Check Accessibility" on JAWS should be renamed "Check with Axe",
so the two sides use one name for one thing.

There is a second, smaller instance: **Tab List** has F4 on NVDA and no key on
JAWS, because F4 in JAWS puts the cursor in Edge's address bar. That difference
is forced by the host and cannot be closed. Tab Names has Shift+F4 on both.

## The gaps, and which ones matter

**On JAWS only** — none. The three commands that were JAWS-only in the last
edition of this document (Extract with Regular Expression, Find Contacts, List
Names) have all been ported.

**On NVDA only** — 49 commands. They are not all equal, and it is worth
separating them:

*Deliberately absent from JAWS, and should stay absent.* List Headings, List
Form Fields, List Links, List Elements, Explore Page, Say Address, Say Time,
Forward Find, Say Position, Toggle Reading, and the whole speech family — Voice
Faster, Voice Slower, Voice Louder, Voice Softer, Toggle Punctuation, Speech
Settings. JAWS does every one of these already, and a second way of doing them
is one more thing to remember for no gain. **On reflection, several of these are
questionable on the NVDA side too**: NVDA also has heading and link lists, and
its own find. That HomerView reimplements them there but not here suggests the
scoping rule was applied more strictly to JAWS than to NVDA, and the NVDA list
could be trimmed.

*Genuinely missing from JAWS and worth building*, in the order I would do them:

1. **Next Same Kind, Prior Same Kind, Next Different Kind, Prior Different
   Kind** (Z, Shift+Z, Alt+Z, Alt+Shift+Z). Nothing in JAWS does this, and it is
   the most original navigation idea in HomerView.
2. **Say Yield, Say Yield Structure, Yield with Regular Expression.** Answers
   "how much" rather than "where", which no screen reader offers.
3. **The rest of the selection family** — Say Selected, Say Chunk, Select Chunk,
   Go to Start of Selection. JAWS has the F8 pair already; these complete it.
4. **Recent Pages, Tab Close Others, Go to Percent and Go to Percent Again.**
   Small, self-contained, no JAWS equivalent.
5. **Say Url** — but see the trade-off below.
6. **Next Sentence, Prior Sentence, Next Paragraph, Prior Paragraph.** Lower
   value: JAWS has sentence and paragraph navigation of its own.

*Judgement calls rather than gaps*: Invoke Script, Consult Copilot, Query Web,
Report Accessibility, Elevate Version, Report Connection, Self Test. Each brings
a dependency or a decision, not just work.

*Impossible on JAWS*: **Submit Form** (Control+Enter). JAWS Script has no Lbc
primitives and Control+Enter belongs to those dialogs, so this command cannot be
written for JAWS at all. It should be marked as such rather than left looking
like an oversight.

## Trade-offs already made, worth restating

**Say Url was merged into Link Target on JAWS.** NVDA has both — Alt+U says
where the link goes, Alt+L describes what is there. On JAWS they are one command
on Alt+L, which always shows the address and adds the description when it can be
fetched. The merge was right: two keys for one question, and worse, when the
fetch failed the describing one showed nothing while the address, already in
hand and needing no network, was the thing you lost. **NVDA should follow**, and
Alt+U should be freed.

**F8 and Shift+F8 shadow JAWS's own F8.** JAWS binds F8 to Select Entire
Element. HomerView takes it inside a web page only, which was your decision and
is the right one — the EdSharp selection pair is used constantly and Select
Entire Element rarely — but it is a real cost and should be recorded as one.

**Control+C and Control+O and Control+S are taken from the browser.** Each is
justified by the same test: HomerView does everything the browser did with that
key and more. Control+C also copies the line when there is no selection;
Control+O also opens Word files and PDFs; Control+S also saves formats Edge
cannot. If any of those three ever stops doing the browser's job as well as its
own, the key should go back.

**Shift+Q was taken against a standing rule.** Shift plus a navigation quick key
means the previous element of that kind, and every letter is a quick key. Q was
taken because a page has one main region, so the native meaning has nowhere to
go. That reasoning is specific to Q and should not be used to justify taking
another shifted letter.

## What I would change

1. **Move Log to Clipboard to Control+Shift+L on JAWS**, matching NVDA. The one
   unprincipled difference in the whole map.
2. **Rename "Check Accessibility" to "Check with Axe" on JAWS**, so one thing
   has one name, and drop the NVDA chooser in favour of two direct keys.
3. **Done.** Extract with Regular Expression, Find Contacts and List Names are
   now on both.
4. **Merge Say Url into Link Target on NVDA**, as on JAWS, and free Alt+U.
5. **Build the four Same Kind and Different Kind commands for JAWS**, the
   largest genuine gap.
6. **Reconsider the NVDA commands that duplicate NVDA's own features**, applying
   the scoping rule as strictly there as it has been applied here.

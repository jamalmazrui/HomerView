---
title: HomerView
subtitle: The full guide
author: Jamal Mazrui
---

# About this guide

This is the complete reference. If you are new to HomerView, read ReadMe.md
first; it takes about ten minutes and covers what most people need.

Keys are written with the modifiers in alphabetical order, and the key names
are the ones JAWS uses, because most blind Windows users have read those for
years. So Alt+NVDA+H, and Accent rather than Grave.

# How HomerView works

HomerView starts its own copy of Microsoft Edge with a setting turned on that
lets another program ask the browser questions. That connection is what
everything here is built on.

It has to be a separate copy. Since 2025, Edge and Chrome ignore that setting
when the browser is using its normal profile, so a copy you started yourself
cannot be asked anything. HomerView runs its own, with its own profile.

That profile is yours and it lasts. Sign in once and your bookmarks, passwords
and sessions are there every time.

# Where the commands work

Commands come in two kinds, and the difference explains why some keys work in
one place and not another.

Most commands only exist while you are reading a page HomerView opened. That
is what lets them use single letters without disturbing anything else on the
computer. In an edit box, in the address bar, or in another program, they are
simply not there.

Commands that must work anywhere carry the NVDA key, because NVDA takes those
before any program sees them. Launching HomerView is the obvious one: there is
no page yet.

Where a command has both, the short key works in a page and the long one works
anywhere.

No HomerView command takes a key NVDA already uses, on either the desktop or
the laptop layout. Every command appears in NVDA's Input Gestures dialog under
the HomerView category, so you can change any key here or add one.

# Starting HomerView

- **Launch HomerView**, Alt+NVDA+H. Launches or reconnects the HomerView copy of Microsoft Edge. H for HomerView, and it works anywhere because nothing is running yet.
- **Alternate Menu**, Alt+NVDA+F10. Present all commands in a single, alphabetized list. F10 opens a menu bar in Windows, and this is the menu HomerView has instead.
- **Hotkey Summary**, Alt+Shift+H. Display this list of command names, hot keys, and descriptions in a new window, as EdSharp does on the same key.

# The documentation

HomerView ships six documents. Each has a command, so any of them can be opened
from the Alternate Menu, and they are read from the installation folder, which
is usually C:\Program Files\HomerView.

- **User Guide**, Control+F1. Open Documentation in the HomerView window. F1 is help everywhere, but plain F1 opens Edge's own help and stays Edge's, so the family here takes F1 with a modifier.
- **Quick Start**, Alt+Shift+F1. Open the first ten minutes of HomerView, for somebody new to it.
- **History of Changes**, Shift+F1. Display list of fixes and improvements.
- **About HomerView**, Alt+F1. Display version and release date, and where HomerView keeps its files.
- **Developer Notes**, Control+Shift+F1. Open the notes on how HomerView is built and why.
- **Hotkey Document**, no key. Open the shipped list of every command, key and description. Hotkey Summary on Alt+Shift+H builds the same list from the program itself; this opens the copy that came with it.
- **Project Announcement**, no key. Open the short description of HomerView, for passing on to somebody who has not met it.
- **Session Log**, Alt+Control+F1. Open a copy of this session's log, for working out what went wrong.

# Moving through a page

- **Jump to Main**, J, or Alt+NVDA+J. Jumps to the main content the page declares. J for Jump, and it is one of only three letters NVDA leaves free in a page.
- **Jump to Probable Main**, Shift+J. Finds the main content of a page that declares none, by weighing every part of it, and says that it inferred rather than was told.
- **Next Sentence**, Alt+DownArrow. Moves to the next sentence and reads it. Alt with an arrow moves by something larger than a line and smaller than a paragraph.
- **Prior Sentence**, Alt+UpArrow. Moves to the previous sentence and reads it.
- **Next Paragraph**, Control+DownArrow. Moves to the next paragraph and reads it. Control with an arrow moves by paragraph in Word and in most editors.
- **Prior Paragraph**, Control+UpArrow. Moves to the previous paragraph and reads it.
- **Next Same Kind**, Z. Moves to the next thing of the same kind as the one you are on, whatever that is. Z because NVDA leaves it free, and JAWS does this with S.
- **Prior Same Kind**, Shift+Z. Moves to the previous thing of the same kind as the one you are on.
- **Next Different Kind**, Alt+Z. Moves to the next thing of a different kind, which JAWS does with D.
- **Prior Different Kind**, Alt+Shift+Z. Moves to the previous thing of a different kind.
- **Go to Percent**, Control+G. Go to percentage point in document, as EdSharp does on the same key.
- **Go to Percent Again**, Alt+G. Repeat Go command, or move a step further with plus or minus.

# Finding text

- **Forward Find**, Control+F. Search forward for string, using NVDA's own find so the dialog and its behaviour are the ones you already know.
- **Reverse Find**, Control+Shift+F. Search backward for string.
- **Forward Find with Regular Expression**, Control+F3. Search forward for regular expression, which NVDA's own find cannot do.
- **Reverse Find with Regular Expression**, Control+Shift+F3. Search backward for regular expression.
- **Forward Find Again**, F3. Search forward for next match, of whichever kind of find was used last.
- **Reverse Find Again**, Shift+F3. Search backward for previous match.
- **Forward Find at Cursor**, Alt+F3. Search forward for chunk or selected text, on the key EdSharp uses for it.
- **Reverse Find at Cursor**, Alt+Shift+F3. Search backward for chunk or selected text.

# Lists of what is on the page

- **List Headings**, NVDA+F6. List the headings on the page, on the key JAWS uses for its heading list.
- **List Form Fields**, NVDA+F5. List the form fields on the page, on the key JAWS uses for its form field list.
- **List Links**, NVDA+Shift+F7. List the links on the page, beside the key JAWS uses for its link list.
- **List Elements**, Alt+NVDA+L. Lists any kind of element, including kinds NVDA's own Elements List does not offer. L for List.
- **Explore Page**, Y, or Alt+NVDA+E. Describes how the page is laid out, including what a sighted person can see that your reading order never mentions. E for Explore; Y is a second key because NVDA leaves it free.

# Asking about the page

- **Say Address**, Alt+A. Says the web address of this page. Twice spells it, three times copies it. A for Address.
- **Say Address Anywhere**, Alt+NVDA+U. Says the web address from anywhere in the window, including the address bar.
- **Say Metadata**, Alt+M. Says what the page claims about itself: author, publisher, date and licence. M for Metadata.
- **Say Position**, Alt+Delete, or Alt+NumPadDelete. Says the line, column and percentage position of the cursor. Delete sits among the navigation keys, which is where a position question belongs.
- **Say Yield**, Alt+Y. Say number of characters, words, and lines in all or selected text.
- **Say Yield Structure**, Alt+Shift+Y. Says how the page is built: how many headings, links, forms and the rest.
- **Yield with Regular Expression**, Control+Shift+Y. Count parts of text matching a regular expression, which answers how many rather than where.
- **Say Url**, Alt+U. Say where the link at the cursor would go. U for url.
- **Link Target**, Alt+L. Ask what is actually at that link without going there: what kind of thing, how big, and whether it ends up where it claims. L for Link.
- **Page Links to Clipboard**, Alt+Shift+P. Copy every link address on the page to the clipboard, as EdSharp copies a path on the same key.
- **Say Time**, Alt+SemiColon. Say current time and date.

# Reading aloud

- **Read All**, Alt+F8. Say all text, without moving the cursor.
- **Toggle Reading**, ScrollLock. Starts reading continuously, or stops if it is already reading. Scroll Lock because nothing else in Edge, NVDA or Windows wants it.
- **Say Selected**, Shift+Space. Say selected text, or spell if repeated.
- **Say Chunk**, Shift+Backspace. Say chunk at cursor, or spell if repeated.

# Selecting and the clipboard

- **Start Selection**, F8. Mark starting point of text to be selected, so Shift need not be held while you move.
- **Complete Selection**, Shift+F8. Select text from starting point to cursor.
- **Go to Start of Selection**, Alt+Shift+F8. Return to start position of selection.
- **Select Chunk**, Control+Space. Select contiguous sequence of non-blank characters at cursor, or select the next chunk if a selection already exists.
- **Copy All**, Control+F8. Copy all text to clipboard.
- **Copy Line**, Control+C. Copy selected text to clipboard, or copy current line if no selection.
- **Copy Append**, Alt+C. Append selected text to clipboard, or append current line if no selection.
- **Say Clipboard**, Alt+Apostrophe. Say clipboard text, or spell if repeated. The apostrophe is a quotation mark, and a clipboard holds a quotation.
- **Save Clipboard**, Control+Apostrophe. Saves the clipboard to a text file, proposing a name.
- **Append Clipboard**, Control+Shift+Apostrophe. Adds the clipboard to the end of a text file rather than replacing it.
- **Clear Clipboard**, Alt+Shift+Apostrophe. Empties the clipboard, so an append starts afresh.

# Doing things to the page

- **Open Document**, Control+O. Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a page so every command here works on it. Control+O opens in every program; this one opens more.
- **Save Page**, Control+S, or Alt+Control+S. Saves the page in any of nine formats. Control+S saves in every program; this one saves more ways.
- **Extract Main Content**, Shift+F9. Extracts the readable part of the page into a page of its own that you can search, save or send. F9 is Edge's own reading view, and Shift+F9 is HomerView's, which works on pages Edge will not.
- **Web Download**, Alt+Shift+W. Pick files to download from a web page, on the key EdSharp uses for it.
- **Submit Form**, Control+Enter. Submits the form you are filling in, from any field in it, so you need not find the button.
- **Invoke Script**, Alt+I. Carries out instructions written in ordinary words, such as click sign in. I for Invoke.
- **Check Accessibility**, Alt+NVDA+A. Tests the page for accessibility problems, asking which engine to use, and offers to report what it finds to whoever publishes the site. A for Accessibility.
- **Consult Copilot**, Alt+NVDA+C. Copies the page text and opens Edge's Copilot sidebar, ready for a question. C for Copilot.
- **Query Web**, Alt+Q, or Alt+NVDA+Q. Looks something up using free services that need no account: a definition, a place, the weather, a book. Q for Query.
- **Dismiss Dialog**, Alt+NVDA+D. Closes a browser dialog that is blocking the window. D for Dismiss, and it works anywhere because a dialog is what has the focus.

# The window and its tabs

- **Tab List**, F4. Lists the HomerView tabs and switches to the one you choose. F4 is the Homer window list, and Edge has two other keys for what F4 does there.
- **Tab Names**, Shift+F4. Says the names of the open tabs without moving the keyboard anywhere.
- **Tab Close Others**, Control+Shift+F4. Closes every tab but the one you are reading. Control+F4 closes one tab, so Control+Shift+F4 closes the rest.

# Speech

- **Voice Faster**, Control+Accent. Increase the voice rate. The accent key carries the whole speech family, as it does in EdSharp.
- **Voice Slower**, Control+Shift+Accent. Decrease the voice rate.
- **Voice Louder**, Alt+Accent. Increase the voice volume.
- **Voice Softer**, Alt+Shift+Accent. Decrease the voice volume.
- **Toggle Punctuation**, Alt+Control+Accent. Toggle the voice between all and no punctuation.
- **Speech Settings**, Shift+Accent. Reports the punctuation level, the rate and the volume.

# Now and then

- **Elevate Version**, Control+F11, or Alt+NVDA+F11. Checks whether a newer HomerView exists and installs it.
- **Recent Pages**, Alt+R. Open a page from the list of those recently used, on the key EdSharp uses for its recent files.
- **Report Connection**, no key. Says whether HomerView is connected to the browser, and how.
- **Self Test**, no key. Checks that all three ways of reaching the browser are working.

# Opening documents

Control+O opens a Word file, a spreadsheet, a slide deck, a PDF, rich text,
OpenDocument, an EPUB or Markdown. HomerView turns it into a web page and opens
that, so every command in this guide works on it. Anything it cannot convert is
handed to the browser, exactly as the browser's own Open command would.

Four converters are used, and none of them ships with HomerView:

- **LibreOffice** covers the most formats and does not need Microsoft Office.
- **pandoc** handles ebooks, Markdown and OpenDocument text. The installer
  offers to fetch it, because it is large and not everybody needs it.
- **Calibre** handles ebooks.
- **2htm** drives Microsoft Office, and is used only where nothing else can do
  the job.

If a format needs a converter you do not have, HomerView says which one.

# Signing in to Google

Google will not sign anyone in on a browser started the way HomerView starts
one. The message says the browser may not be secure. It is aimed at scripts
that take over accounts, which HomerView is not, but the same setting is used
by both, so Google cannot tell them apart.

What works is signing in first. Open the same profile in an ordinary Edge
window, sign in to Google there, then launch HomerView. The session is already
in the profile.

Other sites are mostly fine, and Microsoft accounts are not affected at all.

# Where HomerView keeps things

- **Settings** and the values you have typed before: HomerView.inix, in your
  roaming application data folder.
- **The log** and the record of what you have opened: a HomerView folder in
  your local application data.
- **Generated pages and reports:** a HomerView folder inside the temporary
  folder, which Windows clears on its own.
- **Downloads and saved files:** your Downloads folder.
- **The browser profile:** HomerView, in your local application data.

Uninstalling leaves the log, the history and the settings, because those are
yours.

# When something goes wrong

Press Alt+Control+F1 to open this session's log. It records every command, what
it did, and what failed. It has answered nearly every question put to it, often
contradicting the obvious explanation.

If a command seems to do nothing, open the Alternate Menu with Alt+NVDA+F10.
It only lists commands that can run right now, so a command missing from it is
one that has nothing to act on yet.


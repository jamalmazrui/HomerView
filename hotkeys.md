---
title: HomerView Hotkeys
subtitle: Every command, its key, and why that key
author: Jamal Mazrui
---

# About this list

Every HomerView command, grouped by what you are trying to do and sorted by
name inside each group. Where the key is not obvious, the description says
why it is that key.

The same list is in the guide, HomerView.md, as one of its sections. This
file is here so you can keep it open beside your work.

Press Alt+Shift+H in HomerView and the program builds this list for itself,
from the same source, so it is never out of date.

# How to read a key

Modifiers come in alphabetical order: Alt, Control, NVDA, Shift. So
Alt+NVDA+H, never NVDA+Alt+H. Key names are the ones JAWS uses, because most
blind Windows users have read those for years, so Accent rather than Grave
and SemiColon rather than semicolon.

Where a command has two keys, the short one works inside a HomerView page
and the long one works anywhere.

A command with no key still runs, from the Alternate Menu on Alt+NVDA+F10.
You can give it a key in NVDA's Input Gestures dialog, under the HomerView
category, where every command here can be changed.

# Starting HomerView

- **Alternate Menu**, Alt+NVDA+F10. Present all commands in a single, alphabetized list. F10 opens a menu bar in Windows, and this is the menu HomerView has instead.
- **Hotkey Summary**, Alt+Shift+H. Display this list of command names, hot keys, and descriptions in a new window, as EdSharp does on the same key.
- **Launch HomerView**, Alt+NVDA+H. Launches or reconnects the HomerView copy of Microsoft Edge. H for HomerView, and it works anywhere because nothing is running yet.

# Reading the documentation

- **About HomerView**, Alt+F1. Display version and release date, and where HomerView keeps its files.
- **Developer Notes**, Control+Shift+F1. Open the notes on how HomerView is built and why.
- **History of Changes**, Shift+F1. Display list of fixes and improvements.
- **Hotkey Document**, no key. Open the shipped list of every command, key and description. Hotkey Summary on Alt+Shift+H builds the same list from the program itself; this opens the copy that came with it.
- **Log to Clipboard**, Control+Shift+L. Copy the HomerView log to the clipboard as a file, so Control+V attaches it to an email rather than typing its name into one. L for Log, beside the other Control+Shift keys that put something somewhere.
- **Project Announcement**, no key. Open the short description of HomerView, for passing on to somebody who has not met it.
- **Quick Start**, Alt+Shift+F1. Open the first ten minutes of HomerView, for somebody new to it.
- **Session Log**, Alt+Control+F1. Open a copy of this session's log, for working out what went wrong.
- **User Guide**, Control+F1. Open Documentation in the HomerView window. F1 is help everywhere, but plain F1 opens Edge's own help and stays Edge's, so the family here takes F1 with a modifier.

# Moving through a page

- **Go to Percent**, Control+G. Go to percentage point in document, as EdSharp does on the same key.
- **Go to Percent Again**, Alt+G. Repeat Go command, or move a step further with plus or minus.
- **Jump to Main**, J, or Alt+NVDA+J. Jumps to the main content the page declares. J for Jump, and it is one of only three letters NVDA leaves free in a page.
- **Jump to Probable Main**, Shift+J. Finds the main content of a page that declares none, by weighing every part of it, and says that it inferred rather than was told.
- **Next Different Kind**, Alt+Z. Moves to the next thing of a different kind, which JAWS does with D.
- **Next Paragraph**, Control+DownArrow. Moves to the next paragraph and reads it. Control with an arrow moves by paragraph in Word and in most editors.
- **Next Same Kind**, Z. Moves to the next thing of the same kind as the one you are on, whatever that is. Z because NVDA leaves it free, and JAWS does this with S.
- **Next Sentence**, Alt+DownArrow. Moves to the next sentence and reads it. Alt with an arrow moves by something larger than a line and smaller than a paragraph.
- **Prior Different Kind**, Alt+Shift+Z. Moves to the previous thing of a different kind.
- **Prior Paragraph**, Control+UpArrow. Moves to the previous paragraph and reads it.
- **Prior Same Kind**, Shift+Z. Moves to the previous thing of the same kind as the one you are on.
- **Prior Sentence**, Alt+UpArrow. Moves to the previous sentence and reads it.

# Finding text

- **Forward Find**, Control+F. Search forward for string, using NVDA's own find so the dialog and its behaviour are the ones you already know.
- **Forward Find Again**, F3. Search forward for next match, of whichever kind of find was used last.
- **Forward Find at Cursor**, Alt+F3. Search forward for chunk or selected text, on the key EdSharp uses for it.
- **Forward Find with Regular Expression**, Control+F3. Search forward for regular expression, which NVDA's own find cannot do.
- **Reverse Find**, Control+Shift+F. Search backward for string.
- **Reverse Find Again**, Shift+F3. Search backward for previous match.
- **Reverse Find at Cursor**, Alt+Shift+F3. Search backward for chunk or selected text.
- **Reverse Find with Regular Expression**, Control+Shift+F3. Search backward for regular expression.

# Listing what is on the page

- **Explore Page**, Alt+NVDA+E. Describes how the page is laid out, including what a sighted person can see that your reading order never mentions. E for Explore. It gave up its bare Y: a single letter in browse mode reads as a navigation key, and this command does not move anywhere.
- **List Elements**, Alt+NVDA+L. Lists any kind of element, including kinds NVDA's own Elements List does not offer. L for List.
- **List Form Fields**, NVDA+F5. List the form fields on the page, on the key JAWS uses for its form field list.
- **List Headings**, NVDA+F6. List the headings on the page, on the key JAWS uses for its heading list.
- **List Links**, NVDA+Shift+F7. List the links on the page, beside the key JAWS uses for its link list.

# Asking about the page

- **Link Target**, Alt+L. Ask what is actually at that link without going there: what kind of thing, how big, and whether it ends up where it claims. L for Link.
- **Page Links to Clipboard**, Alt+Shift+P. Copy every link address on the page to the clipboard, as EdSharp copies a path on the same key.
- **Say Address**, Alt+A. Says the web address of this page. Twice spells it, three times copies it. A for Address.
- **Say Address Anywhere**, Alt+NVDA+U. Says the web address from anywhere in the window, including the address bar.
- **Say Metadata**, Alt+M. Says what the page claims about itself: author, publisher, date and licence. M for Metadata.
- **Say Position**, Alt+Delete, or Alt+NumPadDelete. Says the line, column and percentage position of the cursor. Delete sits among the navigation keys, which is where a position question belongs.
- **Say Time**, Alt+SemiColon. Say current time and date.
- **Say Url**, Alt+U. Say where the link at the cursor would go. U for url.
- **Say Yield**, Alt+Y. Say number of characters, words, and lines in all or selected text.
- **Say Yield Structure**, Alt+Shift+Y. Says how the page is built: how many headings, links, forms and the rest.
- **Yield with Regular Expression**, Control+Shift+Y. Count parts of text matching a regular expression, which answers how many rather than where.

# Reading aloud

- **Read All**, Alt+F8. Say all text, without moving the cursor.
- **Say Chunk**, Shift+Backspace. Say chunk at cursor, or spell if repeated.
- **Say Selected**, Shift+Space. Say selected text, or spell if repeated.
- **Toggle Reading**, ScrollLock. Starts reading continuously, or stops if it is already reading. Scroll Lock because nothing else in Edge, NVDA or Windows wants it.

# Selecting and the clipboard

- **Append Clipboard**, Control+Shift+Apostrophe. Adds the clipboard to the end of a text file rather than replacing it.
- **Clear Clipboard**, Alt+Shift+Apostrophe. Empties the clipboard, so an append starts afresh.
- **Complete Selection**, Shift+F8. Select text from starting point to cursor.
- **Copy All**, Control+F8. Copy all text to clipboard.
- **Copy Append**, Alt+C. Append selected text to clipboard, or append current line if no selection.
- **Copy Line**, Control+C. Copy selected text to clipboard, or copy current line if no selection.
- **Go to Start of Selection**, Alt+Shift+F8. Return to start position of selection.
- **Save Clipboard**, Control+Apostrophe. Saves the clipboard to a text file, proposing a name.
- **Say Clipboard**, Alt+Apostrophe. Say clipboard text, or spell if repeated. The apostrophe is a quotation mark, and a clipboard holds a quotation.
- **Select Chunk**, Control+Space. Select contiguous sequence of non-blank characters at cursor, or select the next chunk if a selection already exists.
- **Start Selection**, F8. Mark starting point of text to be selected, so Shift need not be held while you move.

# Acting on the page

- **Check Accessibility**, Alt+NVDA+A. Tests the page for accessibility problems, asking which engine to use, and offers to report what it finds to whoever publishes the site. A for Accessibility.
- **Check with Axe**, no key. Tests the page with Deque's axe-core engine. Offered by Check Accessibility.
- **Check with Equal Access**, no key. Tests the page with IBM's Equal Access engine. Offered by Check Accessibility.
- **Consult Copilot**, Alt+NVDA+C. Copies the page text and opens Edge's Copilot sidebar, ready for a question. C for Copilot.
- **Dismiss Dialog**, Alt+NVDA+D. Closes a browser dialog that is blocking the window. D for Dismiss, and it works anywhere because a dialog is what has the focus.
- **Extract Main Content**, Shift+F9. Extracts the readable part of the page into a page of its own that you can search, save or send. F9 is Edge's own reading view, and Shift+F9 is HomerView's, which works on pages Edge will not.
- **Find Contacts**, Alt+NVDA+C. Finds who to tell about this site: email addresses, the accessibility statement, contact pages and social media. Looks at this page, the home page, and the addresses a statement usually lives at.
- **Invoke Script**, Alt+I. Carries out instructions written in ordinary words, such as click sign in. I for Invoke.
- **List Names**, Alt+N. Lists the people, places, organisations and dates a page mentions, saved as Names.htm in the page's folder and opened. A rule-based engine reads the text, so it guesses; the report says so.
- **Open Document**, Control+O. Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a page so every command here works on it. Control+O opens in every program; this one opens more.
- **Query Web**, Alt+Q, or Alt+NVDA+Q. Looks something up using free services that need no account: a definition, a place, the weather, a book. Q for Query.
- **Report Accessibility**, no key. Tests the page and writes a report addressed to whoever publishes the site. Reached by Check Accessibility once an engine is chosen.
- **Save Page**, Control+S, or Alt+Control+S. Saves the page in any of nine formats. Control+S saves in every program; this one saves more ways.
- **Submit Form**, Control+Enter. Submits the form you are filling in, from any field in it, so you need not find the button.
- **Web Download**, Alt+Shift+W. Pick files to download from a web page, on the key EdSharp uses for it.

# The window and its tabs

- **Tab Close Others**, Control+Shift+F4. Closes every tab but the one you are reading. Control+F4 closes one tab, so Control+Shift+F4 closes the rest.
- **Tab List**, F4. Lists the HomerView tabs and switches to the one you choose. F4 is the Homer window list, and Edge has two other keys for what F4 does there.
- **Tab Names**, Shift+F4. Says the names of the open tabs without moving the keyboard anywhere.

# Adjusting the voice

- **Speech Settings**, Shift+Accent. Reports the punctuation level, the rate and the volume.
- **Toggle Punctuation**, Alt+Control+Accent. Toggle the voice between all and no punctuation.
- **Voice Faster**, Control+Accent. Increase the voice rate. The accent key carries the whole speech family, as it does in EdSharp.
- **Voice Louder**, Alt+Accent. Increase the voice volume.
- **Voice Slower**, Control+Shift+Accent. Decrease the voice rate.
- **Voice Softer**, Alt+Shift+Accent. Decrease the voice volume.

# Changing how HomerView behaves

- **Choose Browser**, Alt+Shift+B. Choose which Chromium browser HomerView drives, from the ones installed here. B for Browser, and Alt+Shift with a letter is where the settings commands live because they are used once and then not again for months.
- **HomerView Settings**, Alt+Shift+S. Open the settings file, HomerView.inix, in a text editor. Everything the settings panel changes is in it, and a comment beside each value says what it does.

# Now and then

- **Elevate Version**, Control+F11, or Alt+NVDA+F11. Checks whether a newer HomerView exists and installs it.
- **Recent Pages**, Alt+R. Open a page from the list of those recently used, on the key EdSharp uses for its recent files.
- **Report Connection**, no key. Says whether HomerView is connected to the browser, and how.
- **Self Test**, no key. Checks that all three ways of reaching the browser are working.

# Everything else

- **Page Folder**, Alt+Shift+F. Open this page's folder in File Explorer, to browse what was saved from it. Nothing is created: if nothing has been saved from this page, it says so. Alt+Shift+F, beside Alt+Shift+W which fills the folder.


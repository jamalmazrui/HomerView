---
title: HomerView Hotkeys
subtitle: Every command, its key, and why that key
author: Jamal Mazrui
---

## About this list

Every HomerView command, grouped by what you are trying to do and sorted by
name inside each group. Where the key is not obvious, the description says
why it is that key.

The same list is in the guide, HomerView.md, as one of its sections. This
file is here so you can keep it open beside your work.

Press Alt+Shift+H in HomerView and the program builds this list for itself,
from the same source, so it is never out of date.

## How to read a key

Modifiers come in alphabetical order: Alt, Control, NVDA, Shift. So
Alt+NVDA+C, never NVDA+Alt+C. Key names are the ones JAWS uses, because most
blind Windows users have read those for years, so Accent rather than Grave
and SemiColon rather than semicolon.

ALMOST EVERY KEY IS THE SAME ON JAWS AND NVDA NOW. The screen reader
modifier is gone from all but a few, because these keys live in the
browser's own key map and do nothing in any other program, so they never
needed to be safe everywhere on the machine.

Alt+Shift+letter rather than Alt+letter, because a Chromium browser fires
a page's access key on Alt+letter and does not on Alt+Shift+letter.

A command with no key still runs, from the Alternate Menu on Alt+F10.
You can give it a key in NVDA's Input Gestures dialog, under the HomerView
category, where every command here can be changed.

## Starting HomerView

- **Alternate Menu**, Alt+F10. Pick any command from one list, in menu, name or key order.
- **Hotkey Summary**, Alt+Shift+H. List every command with its key and description.
- **Launch HomerView**, Alt+Control+Shift+H. Start HomerView, or switch to it, from its desktop shortcut.

## Reading the documentation

- **About HomerView**, Alt+F1. Display version and release date, and where HomerView keeps its files.
- **Copy Log**, Alt+Shift+L. Copy the session log to the clipboard as a file.
- **Developer Notes**, no key. Open the notes on how HomerView is built and why.
- **History of Changes**, Control+Shift+F1. Open the history of HomerView's changes, newest first.
- **Hotkeys**, no key. Open the list of every command and key.
- **Project Announcement**, no key. Open the short description of HomerView, for passing on to somebody who has not met it.
- **ReadMe**, Alt+Shift+F1. Open the quick start.
- **Session Log**, Control+Shift+L. Open a copy of this session's log, for working out what went wrong.
- **User Guide**, no key. Open the HomerView guide.

## Moving through a page

- **Go to Percent**, Control+G. Go to percentage point in document, as EdSharp does on the same key.
- **Go to Percent Again**, Alt+G. Repeat Go command, or move a step further with plus or minus.
- **Jump to Main**, J, or Alt+NVDA+J. Jumps to the main content the page declares. J for Jump, and it is one of only three letters NVDA leaves free in a page.
- **Jump to Probable Main**, Shift+J. Finds the main content of a page that declares none, by weighing every part of it, and says that it inferred rather than was told.
- **Next Different Kind**, Alt+Z. Moves to the next thing of a different kind, which JAWS does with D.
- **Next Paragraph**, Control+DownArrow. Moves to the next paragraph and reads it. Control with an arrow moves by paragraph in Word and in most editors.
- **Next Same Kind**, Z. Moves to the next thing of the same kind as the one you are on, whatever that is. Z because NVDA leaves it free, and JAWS does this with S.
- **Next Sentence**, Alt+DownArrow. Moves to the next sentence and reads it. Alt with an arrow moves by something larger than a line and smaller than a paragraph.
- **Previous Different Kind**, Alt+Shift+Z. Moves to the previous thing of a different kind.
- **Previous Paragraph**, Control+UpArrow. Moves to the previous paragraph and reads it.
- **Previous Same Kind**, Shift+Z. Moves to the previous thing of the same kind as the one you are on.
- **Previous Sentence**, Alt+UpArrow. Moves to the previous sentence and reads it.

## Finding text

- **Forward Find**, Control+F. Search forward for string, using NVDA's own find so the dialog and its behaviour are the ones you already know.
- **Forward Find at Cursor**, Alt+F3. Search forward for chunk or selected text, on the key EdSharp uses for it.
- **Forward Find with Regular Expression**, Control+F3. Search forward for regular expression, which NVDA's own find cannot do.
- **Reverse Find**, Control+Shift+F. Search backward for string.
- **Reverse Find at Cursor**, Alt+Shift+F3. Search backward for chunk or selected text.
- **Reverse Find with Regular Expression**, Control+Shift+F3. Search backward for regular expression.
- **Search Next**, F3. Repeat the last search, forward.
- **Search Previous**, Shift+F3. Repeat the last search, backward.

## Listing what is on the page

- **Explore Page**, Y, or Alt+NVDA+E. Describes how the page is laid out, including what a sighted person can see that your reading order never mentions. E for Explore. It gave up its bare Y: a single letter in browse mode reads as a navigation key, and this command does not move anywhere.
- **List Elements**, Alt+NVDA+L. Lists any kind of element, including kinds NVDA's own Elements List does not offer. L for List.
- **List Form Fields**, NVDA+F5. List the form fields on the page, on the key JAWS uses for its form field list.
- **List Headings**, NVDA+F6. List the headings on the page, on the key JAWS uses for its heading list.
- **List Links**, NVDA+Shift+F7. List the links on the page, beside the key JAWS uses for its link list.

## Asking about the page

- **Link Target**, Alt+L. Ask what is actually at that link without going there: what kind of thing, how big, and whether it ends up where it claims. L for Link.
- **Page Links to Clipboard**, Alt+Shift+P. Copy every link address on the page to the clipboard, as EdSharp copies a path on the same key.
- **Say Address**, Alt+A. Says the web address of this page. Twice spells it, three times copies it. A for Address.
- **Say Address Anywhere**, Alt+NVDA+U. Says the web address from anywhere in the window, including the address bar.
- **Say Metadata**, Alt+M. Says what the page claims about itself: author, publisher, date and licence. M for Metadata.
- **Say Position**, Alt+Delete, or Alt+NumPadDelete. Say the current position: the line, the column and the percent.
- **Say Time**, Alt+SemiColon. Say the date and time.
- **Say url**, Alt+U. Say where the link at the cursor would go. U for url.
- **Say Yield**, Alt+Y. Say how many characters, words and lines are in all or the selected text.
- **Yield Structure**, Alt+Shift+Y. Says how the page is built: how many headings, links, forms and the rest.
- **Yield with Regular Expression**, Control+Shift+Y. Count parts of text matching a regular expression, which answers how many rather than where.

## Reading aloud

- **Read All**, Alt+F8. Say all text, without moving the cursor.
- **Say Chunk**, Shift+Backspace. Say chunk at cursor, or spell if repeated.
- **Say Selected**, Shift+Space. Say the selected text.
- **Toggle Reading**, ScrollLock. Starts reading continuously, or stops if it is already reading. Scroll Lock because nothing else in Edge, NVDA or Windows wants it.

## Selecting and the clipboard

- **Append Clipboard**, Control+Shift+Apostrophe. Add the clipboard text to the end of a file you name.
- **Clear Clipboard**, Alt+Shift+Apostrophe. Empty the clipboard.
- **Complete Selection**, Shift+F8. Select text from starting point to cursor.
- **Copy All**, Control+F8. Copy all text to clipboard.
- **Copy Append**, Alt+C. Add the selected text or the current line to the end of the clipboard.
- **Copy Line**, Control+C. Copy selected text to clipboard, or copy current line if no selection.
- **Go to Start of Selection**, Alt+Shift+F8. Return to start position of selection.
- **Save Clipboard**, Control+Apostrophe. Save the clipboard text to a file you name.
- **Say Clipboard**, Alt+Apostrophe. Say the clipboard text.
- **Select Chunk**, Control+Space. Select contiguous sequence of non-blank characters at cursor, or select the next chunk if a selection already exists.
- **Start Selection**, F8. Mark starting point of text to be selected, so Shift need not be held while you move.

## Acting on the page

- **Check Accessibility**, Alt+Shift+A. Tests the page for accessibility problems, asking which engine to use, and offers to report what it finds to whoever publishes the site. A for Accessibility.
- **Check with Axe**, no key. Tests the page with Deque's axe-core engine. Offered by Check Accessibility.
- **Check with Equal Access**, no key. Tests the page with IBM's Equal Access engine. Offered by Check Accessibility.
- **Consult Copilot**, Alt+NVDA+C. Copies the page text and opens Edge's Copilot sidebar, ready for a question. C for Copilot.
- **Dismiss Dialog**, Alt+Shift+D. Closes a browser dialog that is blocking the window. D for Dismiss, and it works anywhere because a dialog is what has the focus.
- **Extract Main Content**, Shift+F9. Extracts the readable part of the page into a page of its own that you can search, save or send. F9 is Edge's own reading view, and Shift+F9 is HomerView's, which works on pages Edge will not.
- **Find Contacts**, Alt+Shift+C. Finds who to tell about this site: email addresses, the accessibility statement, contact pages and social media. Looks at this page, the home page, and the addresses a statement usually lives at.
- **Instruct Page**, Alt+I. Carries out instructions written in ordinary words, such as click sign in. I for Instruct.
- **List Names**, Alt+N. Lists the people, places, organisations and dates a page mentions, saved as Names.htm in the page's folder and opened. A rule-based engine reads the text, so it guesses; the report says so.
- **Open Document**, Control+O. Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a page so every command here works on it. Control+O opens in every program; this one opens more.
- **Query Web**, Alt+Q, or Alt+NVDA+Q. Looks something up using free services that need no account: a definition, a place, the weather, a book. Q for Query.
- **Report Accessibility**, no key. Tests the page and writes a report addressed to whoever publishes the site. Reached by Check Accessibility once an engine is chosen.
- **Save Page**, Control+S. Saves the page in any of nine formats. Control+S saves in every program; this one saves more ways.
- **Submit Form**, Control+Enter. Submits the form you are filling in, from any field in it, so you need not find the button.
- **Web Download**, Alt+Shift+W. Download files linked from a web page.

## The window and its tabs

- **Tab Close Others**, Control+Shift+F4. Closes every tab but the one you are reading. Control+F4 closes one tab, so Control+Shift+F4 closes the rest.
- **Tab List**, F4. Lists the HomerView tabs and switches to the one you choose. F4 is the Homer window list, and Edge has two other keys for what F4 does there.
- **Tab Names**, Shift+F4. Says the names of the open tabs without moving the keyboard anywhere.

## Changing how HomerView behaves

- **Choose Browser**, Alt+Shift+B. Choose which Chromium browser HomerView drives, from the ones installed here. B for Browser, and Alt+Shift with a letter is where the settings commands live because they are used once and then not again for months.
- **Edit Settings**, Alt+Shift+E. Edit HomerView's settings file.

## Now and then

- **Elevate Version**, Control+F11, or Alt+NVDA+F11. Download and install the latest HomerView.
- **Recent Pages**, Alt+R. Open a page from the list of those recently used, on the key EdSharp uses for its recent files.
- **Report Connection**, no key. Says whether HomerView is connected to the browser, and how.
- **Self Test**, no key. Checks that all three ways of reaching the browser are working.

## Everything else

- **Key Describer Toggle**, Control+F1. Turn key describing on or off: a key says its command instead of running it.
- **Page Folder**, Alt+Shift+F. Open this page's folder in File Explorer, to browse what was saved from it. Nothing is created: if nothing has been saved from this page, it says so. Alt+Shift+F, beside Alt+Shift+W which fills the folder.


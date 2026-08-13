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

# What HomerView is for

For thirty years, blind people have read the web through a flat copy of the
page that a screen reader builds. It works, and it is how most of us read
everything. But the browser knows a great deal that never reaches that copy.
Every blind reader has met the gap: a button you are told is not there, a
banner you never knew was covering the screen, a dialog that swallows your
keystrokes without saying so.

HomerView closes that gap by having the page three ways at once: as a window,
as your reading order, and as the browser itself understands it. Almost nothing
else has all three, and everything in this guide comes from having them
together.

Two things it does not do. No artificial intelligence is involved: the page
explorer follows rules, and the Invoke Script command matches words rather than
guessing at them. And nothing about the pages you read leaves your computer.

# What you need

- **NVDA 2025.1 or newer.** It is free, from nvaccess.org.
- **Microsoft Edge.** It comes with Windows.
- **Windows 10 or 11.**

That is all, and both of the first two are free. HomerView uses the Edge you
already have rather than installing another browser.

# Installing it

Run the installer, and leave the box checked on the last page that gives the
add-on to NVDA. NVDA asks you to confirm it, then restarts.

If that does not work, install it from the file instead. In NVDA press NVDA+N,
then choose Tools, then Add-on Store, then Install from external source, and
pick HomerView.nvda-addon from the build folder where HomerView was installed.
Pressing Enter on that same file in File Explorer does the same thing.

# How HomerView works

HomerView starts its own copy of Microsoft Edge with a setting turned on that
lets another program ask the browser questions. That connection is what
everything here is built on.

It has to be a separate copy. Since 2025, Edge and Chrome ignore that setting
when the browser is using its normal profile, so a copy you started yourself
cannot be asked anything. HomerView runs its own, with its own profile.

That profile is yours and it lasts. Sign in once and your bookmarks, passwords
and sessions are there every time.

# A first half hour

The quick start in ReadMe.md gets you running in ten minutes. This goes
further, and assumes you have done that much.

## Open something and look at it

Press Alt+NVDA+H. A HomerView window opens on the start page.

Press Control+L, type a web address, and press Enter. Any page will do; a news
article is a good first try.

Now press Y. HomerView describes how the page is built: how many headings and
links, where the main content begins, and what a sighted person can see that
your reading order never mentions. That last part is the one nothing else tells
you. A cookie banner, a bar pinned over the text, a dialog waiting for an
answer.

Press J. You are at the main content, past the menus. If the page never said
where its main content is, J says so and does not guess; press Shift+J and
HomerView works it out by weighing every part of the page.

## Read it

Press Alt+F8 to hear the whole page without moving the cursor. Press ScrollLock
to start reading from where you are, and ScrollLock again to stop.

Press Alt+DownArrow to move a sentence at a time, and Control+DownArrow for a
paragraph. Press Alt+Y and HomerView says how long the page is, in characters,
words and lines.

## Find something in it

Press Control+F. That is NVDA's own find, the one you already know, so nothing
new to learn. Press F3 to find the next one.

Press Control+F3 instead and you can search for a pattern rather than a word,
which NVDA cannot do on its own. Press Control+Shift+Y and HomerView counts how
often a pattern appears, which answers how many rather than where.

## Look before you leap

Move to a link and press Alt+U. HomerView says where it goes.

Now press Alt+L. This is the one worth knowing. HomerView asks the other end
what is there, without going there, and tells you what kind of thing it is, how
big it is, whether it still exists, and whether it ends up somewhere other than
it claims. It also says when a link's own words have nothing in common with the
title of the page it leads to, which is the check a sighted person makes by
hovering.

## Take something away with you

Press Shift+F9. HomerView pulls the readable part of the page into a page of
its own, without the menus and the advertising. You can search it, save it or
send it.

Press Control+S to save the page, in any of nine formats. Press Alt+Shift+W and
HomerView lists the kinds of file the page links to, and downloads the ones you
choose.

## Open a document as though it were a page

Press Control+O and choose a Word file, a spreadsheet, a slide deck, a PDF or
an ebook. HomerView converts it and opens it as a web page, which means every
command in this guide works on it. Y describes it, Control+F finds in it,
Shift+F9 extracts its main content.

## Test a page, and say so

Press Alt+NVDA+A. HomerView asks which engine to use, tests the page, and
reports what it finds. It then offers to find the publisher's accessibility
contact and write the report as an email for you to review before sending.

That last step is the point. Finding a problem helps you; reporting it helps
everybody who comes after.

## Ask it something

Press Alt+Q. HomerView looks things up using services that need no account: a
definition, a place, the weather, a book, a recent paper, an exchange rate.

## And when you forget

Press Alt+NVDA+F10. Every command that applies right now, in one alphabetical
list you can search by typing. It only lists what can run, so a command missing
from it is one that has nothing to act on yet.

Press Alt+Shift+H for the same commands as a page, with their keys.

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

# Every command

Every command HomerView has, grouped by what you are trying to do and
sorted by name inside each group. Where the key is not obvious, the
description says why it is that key.

The same list is also a file of its own, Hotkeys.md, so you can keep it
open beside your work. Alt+Shift+H builds it inside HomerView.

## Starting HomerView

- **Alternate Menu**, Alt+NVDA+F10. Present all commands in a single, alphabetized list. F10 opens a menu bar in Windows, and this is the menu HomerView has instead.
- **Hotkey Summary**, Alt+Shift+H. Display this list of command names, hot keys, and descriptions in a new window, as EdSharp does on the same key.
- **Launch HomerView**, Alt+NVDA+H. Launches or reconnects the HomerView copy of Microsoft Edge. H for HomerView, and it works anywhere because nothing is running yet.

## Reading the documentation

- **About HomerView**, Alt+F1. Display version and release date, and where HomerView keeps its files.
- **Developer Notes**, Control+Shift+F1. Open the notes on how HomerView is built and why.
- **History of Changes**, Shift+F1. Display list of fixes and improvements.
- **Hotkey Document**, no key. Open the shipped list of every command, key and description. Hotkey Summary on Alt+Shift+H builds the same list from the program itself; this opens the copy that came with it.
- **Log to Clipboard**, Control+Shift+L. Copy the HomerView log to the clipboard as a file, so Control+V attaches it to an email rather than typing its name into one. L for Log, beside the other Control+Shift keys that put something somewhere.
- **Project Announcement**, no key. Open the short description of HomerView, for passing on to somebody who has not met it.
- **Quick Start**, Alt+Shift+F1. Open the first ten minutes of HomerView, for somebody new to it.
- **Session Log**, Alt+Control+F1. Open a copy of this session's log, for working out what went wrong.
- **User Guide**, Control+F1. Open Documentation in the HomerView window. F1 is help everywhere, but plain F1 opens Edge's own help and stays Edge's, so the family here takes F1 with a modifier.

## Moving through a page

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

## Finding text

- **Forward Find**, Control+F. Search forward for string, using NVDA's own find so the dialog and its behaviour are the ones you already know.
- **Forward Find Again**, F3. Search forward for next match, of whichever kind of find was used last.
- **Forward Find at Cursor**, Alt+F3. Search forward for chunk or selected text, on the key EdSharp uses for it.
- **Forward Find with Regular Expression**, Control+F3. Search forward for regular expression, which NVDA's own find cannot do.
- **Reverse Find**, Control+Shift+F. Search backward for string.
- **Reverse Find Again**, Shift+F3. Search backward for previous match.
- **Reverse Find at Cursor**, Alt+Shift+F3. Search backward for chunk or selected text.
- **Reverse Find with Regular Expression**, Control+Shift+F3. Search backward for regular expression.

## Listing what is on the page

- **Explore Page**, Y, or Alt+NVDA+E. Describes how the page is laid out, including what a sighted person can see that your reading order never mentions. E for Explore; Y is a second key because NVDA leaves it free.
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
- **Say Position**, Alt+Delete, or Alt+NumPadDelete. Says the line, column and percentage position of the cursor. Delete sits among the navigation keys, which is where a position question belongs.
- **Say Time**, Alt+SemiColon. Say current time and date.
- **Say Url**, Alt+U. Say where the link at the cursor would go. U for url.
- **Say Yield**, Alt+Y. Say number of characters, words, and lines in all or selected text.
- **Say Yield Structure**, Alt+Shift+Y. Says how the page is built: how many headings, links, forms and the rest.
- **Yield with Regular Expression**, Control+Shift+Y. Count parts of text matching a regular expression, which answers how many rather than where.

## Reading aloud

- **Read All**, Alt+F8. Say all text, without moving the cursor.
- **Say Chunk**, Shift+Backspace. Say chunk at cursor, or spell if repeated.
- **Say Selected**, Shift+Space. Say selected text, or spell if repeated.
- **Toggle Reading**, ScrollLock. Starts reading continuously, or stops if it is already reading. Scroll Lock because nothing else in Edge, NVDA or Windows wants it.

## Selecting and the clipboard

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

## Acting on the page

- **Check Accessibility**, Alt+NVDA+A. Tests the page for accessibility problems, asking which engine to use, and offers to report what it finds to whoever publishes the site. A for Accessibility.
- **Check with Axe**, no key. Tests the page with Deque's axe-core engine. Offered by Check Accessibility.
- **Check with Equal Access**, no key. Tests the page with IBM's Equal Access engine. Offered by Check Accessibility.
- **Consult Copilot**, Alt+NVDA+C. Copies the page text and opens Edge's Copilot sidebar, ready for a question. C for Copilot.
- **Dismiss Dialog**, Alt+NVDA+D. Closes a browser dialog that is blocking the window. D for Dismiss, and it works anywhere because a dialog is what has the focus.
- **Extract Main Content**, Shift+F9. Extracts the readable part of the page into a page of its own that you can search, save or send. F9 is Edge's own reading view, and Shift+F9 is HomerView's, which works on pages Edge will not.
- **Invoke Script**, Alt+I. Carries out instructions written in ordinary words, such as click sign in. I for Invoke.
- **Open Document**, Control+O. Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a page so every command here works on it. Control+O opens in every program; this one opens more.
- **Query Web**, Alt+Q, or Alt+NVDA+Q. Looks something up using free services that need no account: a definition, a place, the weather, a book. Q for Query.
- **Report Accessibility**, no key. Tests the page and writes a report addressed to whoever publishes the site. Reached by Check Accessibility once an engine is chosen.
- **Save Page**, Control+S, or Alt+Control+S. Saves the page in any of nine formats. Control+S saves in every program; this one saves more ways.
- **Submit Form**, Control+Enter. Submits the form you are filling in, from any field in it, so you need not find the button.
- **Web Download**, Alt+Shift+W. Pick files to download from a web page, on the key EdSharp uses for it.

## The window and its tabs

- **Tab Close Others**, Control+Shift+F4. Closes every tab but the one you are reading. Control+F4 closes one tab, so Control+Shift+F4 closes the rest.
- **Tab List**, F4. Lists the HomerView tabs and switches to the one you choose. F4 is the Homer window list, and Edge has two other keys for what F4 does there.
- **Tab Names**, Shift+F4. Says the names of the open tabs without moving the keyboard anywhere.

## Adjusting the voice

- **Speech Settings**, Shift+Accent. Reports the punctuation level, the rate and the volume.
- **Toggle Punctuation**, Alt+Control+Accent. Toggle the voice between all and no punctuation.
- **Voice Faster**, Control+Accent. Increase the voice rate. The accent key carries the whole speech family, as it does in EdSharp.
- **Voice Louder**, Alt+Accent. Increase the voice volume.
- **Voice Slower**, Control+Shift+Accent. Decrease the voice rate.
- **Voice Softer**, Alt+Shift+Accent. Decrease the voice volume.

## Now and then

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
- **The logs:** a logs folder inside HomerView's folder in your local
  application data. One file for each session, named for when it started, so a
  problem you report an hour later still has the log from when it happened. The
  thirty most recent are kept.
- **The record of what you have opened:** the same HomerView folder.
- **Generated pages and reports:** a HomerView folder inside the temporary
  folder, which Windows clears on its own.
- **Downloads and saved files:** your Downloads folder.
- **The browser profile:** HomerView, in your local application data.

Uninstalling leaves the log, the history and the settings, because those are
yours.

# Licence

HomerView is free software under the GNU General Public License version 2,
which is the same licence NVDA itself uses. You can read the source, change it,
and pass it on.

The project is at github.com/JamalMazrui/HomerView.

# When something goes wrong

Press Alt+Control+F1 to open this session's log. It records every command, what
it did, and what failed. It has answered nearly every question put to it, often
contradicting the obvious explanation.

Press Control+Shift+L to put that log on the clipboard as a file. Then open an
email, put the cursor in the message, and press Control+V. The log arrives as
an attachment rather than as a screenful of text pasted into the message. It
works anywhere a dropped file works, so File Explorer will copy it into a
folder the same way.

The log is written a line at a time, so it holds everything up to the moment
something went wrong rather than losing the last few lines to a crash.

# What the log holds, and who sees it

HomerView never sends the log anywhere. Nothing leaves your computer unless you
attach it to something and send it yourself. Control+Shift+L exists so that
sharing it is one keystroke when you decide to, and never otherwise.

Your user name and your computer name are taken out as the log is written.
Every path reads %USERPROFILE% or %LOCALAPPDATA% rather than naming you, so the
log still says where a file was without saying whose machine it was on.

What it does record is the computer it ran on and what HomerView did. The
versions of HomerView, NVDA, Python, Windows and the browser. Your NVDA
keyboard layout. Every command you ran and what it did. Any error, with the
detail that explains it.

It also records the addresses and titles of pages opened in HomerView, and text
you searched for, because most faults cannot be explained without knowing what
was on screen. If that matters for what you were doing, read the log before you
send it. Alt+Control+F1 opens it, and it is plain text.

If a command seems to do nothing, open the Alternate Menu with Alt+NVDA+F10.
It only lists commands that can run right now, so a command missing from it is
one that has nothing to act on yet.


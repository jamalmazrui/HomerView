---
title: HomerView User Guide
author: Jamal Mazrui
---

# HomerView

An NVDA add-on that runs its own copy of Microsoft Edge and drives it through
the Chrome DevTools Protocol. This guide lists every command. For a first ten
minutes, read README.md instead.

Keys are written with modifiers in alphabetical order, and key names as
Freedom Scientific writes them.

# How the commands are organised

Commands come in two kinds, and the difference explains why some keys work in
one place and not another.

Page commands exist only while you are reading a page HomerView opened, in
browse mode. That is what lets them use single letters without disturbing
anything else on the computer. In an edit field, in the address bar, or in
another program, they are simply not there.

Commands that work anywhere carry the NVDA key, which NVDA takes before any
program sees it. Those are for starting HomerView and for the few things worth
doing from outside a page. Where a command has both kinds of key, both are
listed, shortest first.

No HomerView command takes a key NVDA uses by default, on either the desktop
or the laptop layout. Every command appears in NVDA's Input Gestures dialog
under the HomerView category, where its key can be changed.

# Starting and finding things

- **Alt+NVDA+H** launch or reconnect the HomerView instance of Microsoft Edge
- **Alt+NVDA+F10** lists every HomerView command in one alphabetical list
- **Alt+Shift+H** shows every HomerView command and its key as a document
- **F1** shows the HomerView user guide
- **Alt+F1** shows what HomerView is, and where it keeps its files
- **Shift+F1** shows the history of changes to HomerView
- **Control+F11, or Alt+NVDA+F11** checks for a newer HomerView and installs it
- **in the Alternate Menu only** opens the HomerView quick start in the HomerView window
- **in the Alternate Menu only** opens the HomerView user guide in the HomerView window
- **in the Alternate Menu only** opens the HomerView history of changes in the HomerView window
- **in the Alternate Menu only** opens the HomerView developer notes in the HomerView window
- **in the Alternate Menu only** check that all three ways of reaching the browser are working
- **in the Alternate Menu only** report whether HomerView is connected to Microsoft Edge
- **in the Alternate Menu only** open the HomerView log file for this session

# Getting around a page

- **J, or Alt+NVDA+J** jump to Main Content: moves to the page's main content landmark
- **Shift+J** jump to Probable Main Content: finds it when the page declares none
- **Alt+DownArrow** moves to the next sentence and reads it
- **Alt+UpArrow** moves to the previous sentence and reads it
- **Control+DownArrow** moves to the next paragraph and reads it
- **Control+UpArrow** moves to the previous paragraph and reads it
- **Z** moves to the next element of the same kind as this one
- **Shift+Z** moves to the previous element of the same kind as this one
- **Alt+Z** moves to the next element of a different kind
- **Alt+Shift+Z** moves to the previous element of a different kind
- **Control+G** moves to a percentage point through the page
- **Alt+G** moves to the percentage point used last time
- **NVDA+F6** lists the headings on the page, like the JAWS heading list
- **NVDA+Shift+F7** lists the links on the page, like the JAWS link list
- **NVDA+F5** lists the form fields on the page, like the JAWS form field list
- **Alt+NVDA+L** lists any kind of element on the page, including kinds NVDA's own Elements List does not offer

# Finding text

- **Control+F** finds text in the page, using NVDA's own find
- **Control+Shift+F** finds text backwards in the page, using NVDA's own find
- **Control+F3** finds a regular expression in the page
- **Control+Shift+F3** finds a regular expression backwards in the page
- **F3** repeats the last search, whichever kind it was
- **Shift+F3** repeats the last search in the opposite direction
- **Alt+W** finds the next occurrence of the word at the cursor
- **Alt+Shift+W** finds the previous occurrence of the word at the cursor

# Reading and copying

- **ScrollLock** starts reading continuously, or stops if it is already reading
- **Alt+F8** reads the whole page without moving the cursor
- **Alt+R** reads the rest of the page from the cursor, without moving it
- **Shift+Space** says the selected text, and spells it when pressed twice
- **Shift+Backspace** says the run of non-blank characters at the cursor, and spells it when pressed twice
- **Control+F8** copies the whole page to the clipboard
- **Control+C** copies the selection, or the current line when nothing is selected
- **Alt+C** appends the selection, or the current line, to the clipboard
- **Control+Space** selects the run of non-blank characters at the cursor
- **F8** marks where a selection should begin, so Shift need not be held
- **Shift+F8** selects from the marked start to the cursor
- **Alt+Shift+F8** returns to the marked start of the selection
- **Alt+Apostrophe** says the clipboard text, and spells it when pressed twice
- **Alt+Shift+Apostrophe** clears the clipboard
- **Control+Apostrophe** saves the clipboard to a text file, proposing a name
- **Control+Shift+Apostrophe** appends the clipboard to a text file

# Asking about a page

- **Alt+A** reports the web address of the current HomerView page. Pressing twice spells it, and pressing three times copies it to the clipboard
- **Alt+N** says the name of the page, and spells it when pressed twice
- **Alt+M** reports what the page says about itself: author, publisher, date, licence
- **Alt+Y** says how many characters, words and lines the page or selection holds
- **Alt+Shift+Y** says how the page is built
- **Control+Shift+Y** counts how often a regular expression matches this page
- **Alt+Delete, or Alt+NumPadDelete** says the line, column and percentage position of the cursor
- **Alt+U** says where the link at the cursor would go, and copies it when pressed twice
- **Alt+P** copies every link address on the page to the clipboard
- **Y, or Alt+NVDA+E** summarises the structure of the current HomerView page, the visual aspects a reading order hides, and how best to move around it
- **Alt+SemiColon** says the time, and the date when pressed twice
- **F4** lists the HomerView tabs and switches to the one you choose
- **Shift+F4** says the names of the open HomerView tabs
- **in the Alternate Menu only** recently opened: lists the pages and documents you have opened in HomerView, with when each was opened, so you can find something again
- **Alt+NVDA+U** reports the web address of the HomerView page, from anywhere in the window

# Acting on a page

- **Alt+V** acts on the page by describing what you want, such as click sign in
- **Control+Enter** submits the form you are filling in, from any field
- **Alt+K** tests this page for accessibility, asking which engine to use
- **Alt+I** tests the page with the IBM Equal Access engine, alongside axe-core
- **Control+O** opens a document of any popular format, converting it to a web page first so that every HomerView command works on it
- **Control+S, or Alt+Control+S** saves the current HomerView page as a web page, Markdown, or plain text
- **Alt+NVDA+W** lists the file types linked from the current HomerView page, then downloads the ones you choose
- **Alt+NVDA+X** extracts the readable part of the current HomerView page and opens it as a plain document in a new tab
- **Alt+Q, or Alt+NVDA+Q** looks something up using free web services that need no account
- **Alt+NVDA+P** ask Copilot about this page: copies the page text to the clipboard and opens Microsoft Edge's Copilot sidebar, ready for you to paste with Control+V and ask a question
- **Control+Shift+F4** closes every HomerView tab but this one and the first
- **Alt+NVDA+D** close a Microsoft Edge dialog that is blocking the HomerView window
- **Alt+NVDA+A** tests the current HomerView page for accessibility problems, finds how to report them to the publisher, and opens the report in a new tab
- **in the Alternate Menu only** tests the current HomerView page with axe-core and reports the counts only

# Speech

- **Alt+Control+Accent** switches punctuation between all and none
- **Control+Accent** speaks faster
- **Control+Shift+Accent** speaks slower
- **Alt+Accent** speaks louder
- **Alt+Shift+Accent** speaks more softly
- **Shift+Accent** reports the punctuation level, the rate and the volume

# Invoking a script

Alt+V opens a box where each line is one instruction, carried out in order. The
idea is Stagehand's: you say what you want in ordinary words, and the program
works out which control you meant. HomerView does that matching itself, by role
and accessible name, against the page's own controls. Nothing is sent anywhere
and no language model is involved.

## What you can ask for

- **click**, and its synonyms press, open, follow, select, choose, activate,
  push, hit, tap, go to
- **type**, and its synonyms enter, fill, input, write, put, set
- **check**, and its synonyms tick, mark, enable, turn on
- **uncheck**, and its synonyms untick, unmark, disable, turn off
- **focus**, and its synonyms go, move to, place focus
- **read**, and its synonyms say, speak, announce, tell me

## How to name what you mean

Use the words you would hear. Click sign in. Type London into city. The name is
matched against what a screen reader would call the control, so what you hear
is what you type.

You may name the kind of thing as well: the search field, the Download link,
the submit button. Naming a kind makes matches of that kind more likely to win
rather than ruling others out, so being wrong about the kind costs you nothing.

Values go after the word into, or after to, or after with. Type Jamal into
search. Set the country to France.

## An example

    # sign in, then search
    click sign in
    type me@example.org into email
    type mypassword into password
    click submit

A line beginning with a hash is a comment. Blank lines are skipped.

## What the buttons do

- **Test** reads every line the way the runner will and reports the verb, the
  target and the value it found, without touching the page. A mistyped
  instruction is caught before it clicks anything.
- **Help** explains the vocabulary above from inside the dialog.
- **OK** runs the script.

## How it behaves

A single instruction offers you a choice when several controls could match,
because there is a reader waiting to answer. A script of several instructions
does not ask, because the point of a script is that it runs.

A script stops at the first instruction that matches nothing, since carrying on
after losing the thread would act on the wrong thing. The result opens as a
page listing every instruction, what it acted on, and what happened.

The last script is remembered, so one that was almost right can be corrected
and run again rather than retyped.

# Reading documents

Control+O opens a Word file, a spreadsheet, a slide deck, a PDF, rich text,
OpenDocument, EPUB or Markdown. HomerView converts it to a web page in the
temporary folder and opens that, so every command in this guide works on it.
Anything it has no converter for is handed to the browser, exactly as the
browser's own Open command would.

Four converters are used, whichever suits the format, and none is bundled:
LibreOffice, which covers the most formats and needs no Microsoft Office;
pandoc, for ebooks, Markdown and OpenDocument text; Calibre, for ebooks; and
2htm, which drives Microsoft Office and is used only where it is alone in
handling a format. If a format needs a converter you do not have, HomerView
says which one to install.

# Where HomerView puts things

- Settings and recently typed values: HomerView.inix in your roaming
  application data folder.
- The session log and the record of what you have opened: a HomerView folder in
  your local application data.
- Generated pages and reports: a HomerView folder inside the temporary folder,
  which Windows clears on its own.
- Downloads and saved files: your downloads folder.
- The browser profile: HomerView inside your local application data.

# Why the browser is a separate copy

Since Chrome 136 and the matching Edge release, the remote debugging switches
are ignored when the browser uses its default profile. A copy of Edge you
started yourself therefore cannot be given a debugging connection, and HomerView
cannot work in it. HomerView runs its own copy with its own profile instead.

That profile is persistent and is yours. Sign it in once and your bookmarks,
passwords, extensions and sessions are there every time. Set bAllowSignIn to
True in edge.py, delete the profile folder, and launch again.

Google is the exception. It will not sign anyone in on a browser started with
remote debugging, which is what HomerView needs. Sign in to Google in an
ordinary Edge window using the same profile first, and HomerView will find the
session already there.

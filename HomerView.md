---
title: HomerView User Guide
author: Jamal Mazrui
---

# HomerView

HomerView is an NVDA add-on that runs its own copy of Microsoft Edge and drives
it through the Chrome DevTools Protocol. This guide describes every command.
For a first ten minutes, read README.md instead.

# How the commands are organised

Commands come in two kinds, and the difference explains why some keys work in
one place and not another.

Page commands exist only while you are reading a page HomerView opened, in
browse mode. That is what lets them use single letters and short combinations
without disturbing anything else on the computer. In an edit field, in the
address bar, or in another program, they are simply not there.

Commands that work anywhere carry the NVDA key, which NVDA takes before any
program sees it. Those are for starting HomerView and for the few things worth
doing from outside a page.

No HomerView command takes a key NVDA uses by default, on either the desktop or
the laptop layout. Every command appears in NVDA's Input Gestures dialog under
the HomerView category, where its key can be changed.

# Commands that work anywhere

- Alt+NVDA+H launches or reconnects the HomerView browser.
- Alt+NVDA+F10 lists every command, even before the browser is running.
- Alt+NVDA+U reports the web address, from the address bar or a form field as
  well as from the page.
- Control+O opens a document of almost any format.
- Control+F12 saves the page in one of seven formats.
- Alt+NVDA+W downloads files linked from the page.
- Alt+NVDA+X extracts the readable part of the page.
- Alt+NVDA+E summarises the structure of the page.
- Alt+NVDA+A tests the page for accessibility and finds how to report problems.
- Alt+NVDA+P copies the page text and opens Edge's Copilot sidebar.
- Alt+NVDA+D closes a browser dialog that is blocking the window.
- Control+Enter submits the form you are filling in, from any field.

# Getting around the page

- **no key by default** jump to Main Content: moves to the page's main content landmark
- **Shift+J** jump to Probable Main Content: finds it when the page declares none
- **Alt+Downarrow** moves to the next sentence and reads it
- **Alt+Uparrow** moves to the previous sentence and reads it
- **Control+Downarrow** moves to the next paragraph and reads it
- **Control+Uparrow** moves to the previous paragraph and reads it
- **Control+G** moves to a percentage point through the page
- **Alt+G** moves to the percentage point used last time
- **NVDA+F6** lists the headings on the page, like the JAWS heading list
- **NVDA+Shift+F7** lists the links on the page, like the JAWS link list
- **NVDA+F5** lists the form fields on the page, like the JAWS form field list
- **Alt+NVDA+L** lists any kind of element on the page, including kinds NVDA's own Elements List does not offer

# Finding things

- **Control+F** finds text or a regular expression in the page
- **Control+Shift+F3** finds text or a regular expression backwards in the page
- **F3** repeats the last find, forwards
- **Shift+F3** repeats the last find, backwards
- **Alt+W** finds the next occurrence of the word at the cursor
- **Alt+Shift+W** finds the previous occurrence of the word at the cursor

# Reading and copying

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

# Asking about the page

- **no key by default** reports the web address of the current HomerView page. Pressing twice spells it, and pressing three times copies it to the clipboard
- **Alt+N** says the name of the page, and spells it when pressed twice
- **Alt+M** reports what the page says about itself: author, publisher, date, licence
- **Alt+Y** says how many characters, words and lines the page or selection holds
- **Alt+Shift+Y** says how many links, headings, landmarks, tables, frames and fields the page holds
- **Alt+Delete** says the line, column and percentage position of the cursor
- **Alt+U** says where the link at the cursor would go, and copies it when pressed twice
- **Alt+P** copies every link address on the page to the clipboard
- **Y** summarises the structure of this page
- **Alt+SemiColon** says the time, and the date when pressed twice

# The clipboard

- **Alt+Apostrophe** says the clipboard text, and spells it when pressed twice
- **Alt+Shift+Apostrophe** clears the clipboard
- **Control+Apostrophe** saves the clipboard to a text file, proposing a name
- **Control+Shift+Apostrophe** appends the clipboard to a text file

# Acting on the page

- **Alt+V** acts on the page by describing what you want, such as click sign in
- **Alt+K** tests this page for accessibility, asking which engine to use
- **Alt+I** tests the page with the IBM Equal Access engine, alongside axe-core
- **Control+O** opens a document of any popular format, or a web address

# Finding a command

- **Alt+NVDA+F10** lists every HomerView command in one alphabetical list
- **Alt+Shift+H** shows every HomerView command and its key as a document
- **F1** shows the HomerView user guide
- **Alt+F1** shows what HomerView is, and where it keeps its files
- **Shift+F1** shows the history of changes to HomerView

# Reading documents

Control+O opens a Word file, a spreadsheet, a slide deck, a PDF, rich text,
OpenDocument, EPUB or Markdown. HomerView converts it to a web page in the
temporary folder and opens that, so every command in this guide works on it.

Four converters are used, whichever suits the format, and none is bundled:
LibreOffice, which covers the most formats and needs no Microsoft Office;
pandoc, for ebooks, Markdown and OpenDocument text; Calibre, for ebooks; and
2htm, which drives Microsoft Office and is used only where it is alone in
handling a format. If a format needs a converter you do not have, HomerView
says which one to install.

# Where HomerView puts things

- Settings and recently typed values: HomerView.inix in your roaming
  application data folder.
- Generated pages and reports: a HomerView folder inside the temporary folder,
  which Windows clears on its own.
- Downloads and saved files: your downloads folder.
- The session log and the history database: your local application data folder.


# Why the browser is a separate copy

Since Chrome 136 and the matching Edge release, the remote debugging switches
are ignored when the browser uses its default profile. A copy of Edge you
started yourself therefore cannot be given a debugging connection, and HomerView
cannot work in it. HomerView runs its own copy with its own profile instead.

That profile is persistent and is yours. Sign it in once and your bookmarks,
passwords, extensions and sessions are there every time, and downloads behind a
login work. Set bAllowSignIn to True in edge.py, delete the profile folder, and
launch again.

---
title: "HomerView Read Me"
---

HomerView is a screen-reader companion for reading the web, for **JAWS** and
**NVDA** equally. It drives its own copy of Microsoft Edge and answers questions
about the page that a screen reader alone cannot.

This file is the short version. The full guide is HomerView.htm, which you can
open from inside HomerView with **Control+F1**.

## Quick Start

### Install it

Run **HomerView_setup.exe**. It detects JAWS and NVDA and offers to set up
whichever it finds. On JAWS it also compiles and binds the scripts for every
JAWS version installed, and asks JAWS to reload, so no restart is normally
needed.

To confirm which build is loaded afterwards, press **Alt+Shift+H**. Its first
line gives the version and when it was installed.

### Start it

- **JAWS:** Alt+JAWSKey+H
- **NVDA:** NVDA+Alt+H

A HomerView window of Microsoft Edge opens on a start page. This is a separate
browser profile, so it does not disturb your ordinary browsing. Press the same
key again later and it reconnects rather than opening a second one.

### The one key to remember

- **JAWS:** Alt+JAWSKey+F10
- **NVDA:** NVDA+Alt+F10

That is the Alternate Menu, and every command is on it with its key beside it.
Nothing in HomerView is hidden behind a keystroke you have to know in advance.
If you remember only one key, remember that one.

The other one worth knowing is **Alt+Shift+H**, the Hotkey Summary, which lists
every command in a window where each key is a link: press Enter on a line to run
that command.

### Six things to try

Open any article, then:

1. **Shift+Q** on JAWS, **Shift+J** on NVDA — jumps to the main content, past
   the navigation, whether or not the page declares where it is.
2. **Shift+F9** — extracts the readable article into a tab of its own, with the
   navigation, adverts and footers gone but the links kept.
3. **Alt+L**, with the cursor on a link — says what is at the other end without
   going there: what kind of thing it is, how big, its title, and whether the
   address leads somewhere other than it appears.
4. **Alt+JAWSKey+A** on JAWS, **Alt+NVDA+A** on NVDA — checks the page for
   accessibility problems and saves a readable report to your Downloads folder,
   opening it in a tab.
5. **Alt+Shift+W** — offers you every file the page links to, by kind, and
   fetches the ones you choose using the browser's own cookies.
6. **Alt+N** — lists the people, places, organisations and dates the page
   mentions, which is a different question from what is on it.

### If something goes wrong

Press **Alt+JAWSKey+L** on JAWS, **Control+Shift+L** on NVDA, to put the log file
on the clipboard, ready to attach to a message. The log records every command,
every answer and every failure, in order.

**Alt+Control+F1** opens the same log to read rather than to send.

## What is in the box

- **ReadMe.htm** — this file.
- **HomerView.htm** — the full user guide and reference, including a tutorial.
- **Hotkeys.htm** — every key, for both screen readers.
- **History.htm** — what changed in each release.
- **Developer.htm** — how to rebuild HomerView from source.
- **Announce.htm** — what the project is for.

Each is on the Alternate Menu, and most have a key of their own.

## Requirements

- Windows 10 or later
- Microsoft Edge
- JAWS 2024 or later, or NVDA 2023.1 or later
- Optional: pandoc or 2htm, for opening Word documents, PDFs, ebooks and
  spreadsheets as web pages. HomerView finds them if they are installed and says
  plainly when they are not.

## Licence and source

Free and open source. The source, issues and releases are at
<https://github.com/JamalMazrui/HomerView>.

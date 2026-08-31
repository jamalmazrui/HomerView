---
title: "HomerView Read Me"
---

HomerView is a screen-reader companion for reading the web, for **JAWS** and
**NVDA** equally. It drives its own copy of Microsoft Edge and answers questions
about a page that a screen reader alone cannot.

The two screen readers do the same things: the same commands, the same
answers, the same pages. Keys differ only where the two screen readers themselves
differ, so this file gives both keys only where they are not the same.

This is the short version. The full guide is HomerView.htm, which **Control+F1**
opens from inside HomerView.

## What it is for

- **A browser** — everything Edge already does, read through your own screen
  reader.
- **An accessibility tester** — the axe or IBM engine checks the page, and
  writes a report you can send to the people who run the site.
- **A document and ebook reader** — Word files, EPUB books, PDFs and other
  common formats become web pages, so headings, lists and tables become real
  ones you can move through.
- **A file downloader** — the files a page points to, sorted by kind, and it
  fetches the kinds you pick.
- **Other tools** — main content on its own without menus or adverts; the names
  a page mentions; finding and selecting text; tabs, links and the clipboard.

## Quick start

### Install it

Run **HomerView_setup.exe**. It detects JAWS and NVDA and sets up whichever it
finds. On JAWS it also compiles and binds the scripts for every JAWS version
installed and asks JAWS to reload, so a restart is not normally needed.

To confirm which build is loaded, press **Alt+Shift+H**; its first line gives the
version and when it was installed.

### Start it

Throughout this file, JAWS and NVDA name each screen reader's own modifier
key, which may be Insert or Caps Lock, whichever you have set.

**Alt+Control+H** opens a HomerView browser window on a start page. It is a
separate browser profile, so your ordinary browsing is untouched. The same key
later brings you back to that window rather than opening a second one.

That key is on the HomerView icon the installer puts on your desktop, so it
works whichever screen reader you use, and whether or not one is running. If
it does nothing, another program has taken the key; open the icon's properties
and set a different one.

Every other HomerView key works while the HomerView browser is in front, and
does nothing anywhere else. That is on purpose. HomerView does not change any
of your screen reader's own settings, so no key of ours can appear where you
did not expect it.

HomerView uses Microsoft Edge unless you tell it otherwise. **Alt+Shift+B**
lists the browsers on your computer and lets you pick another. Chrome, Brave
and Vivaldi all work.

### The one key to remember

**Alt+JAWS+F10** (JAWS) or **Alt+NVDA+F10** (NVDA) opens the Alternate Menu.
Every command is on it, in alphabetical order, with its key beside it, and only
the commands that apply where you are. Nothing is hidden behind a keystroke you
must know in advance.

**Alt+Shift+H** is the other one worth knowing: hot key help, listing every
command in a window where each key is a link — press Enter on a line to run it.

### Six things to try

Open any article, then:

1. **Shift+Q** (JAWS) or **Shift+J** (NVDA) — jump to the main content, past the
   navigation, whether or not the page declares where it is.
2. **Shift+F9** — extract the readable article into a tab of its own, adverts and
   footers gone, links kept.
3. **Alt+L**, with the cursor on a link — say what is at the other end without
   going there: what kind of thing, how big, and whether the address leads
   somewhere other than it appears.
4. **Alt+JAWS+A** (JAWS) or **Alt+NVDA+A** (NVDA) — check the page with axe and
   save a readable report to Downloads, opening it in a tab. **Alt+JAWS+I** or
   **Alt+NVDA+I** does the same with IBM's engine.
5. **Alt+Shift+W** — offer every file the page points at, by kind, and fetch the
   ones you choose using the browser's own cookies.
6. **Control+O** — open a DOCX, EPUB, PDF or spreadsheet as a web page you can
   navigate by heading.

Short answers are spoken. Press the same key again to put the same text in a
window you can read by character, word or line and copy from.

### If something goes wrong

**Alt+JAWS+L** (JAWS) or **Control+Shift+L** (NVDA) puts the log on the
clipboard, ready to attach to a message. It records every command, answer and
failure in order, and begins with the version it came from.

**Alt+JAWS+Q** speaks what HomerView knows about itself, without touching the
log or the helper — the first thing to try if nothing else responds.

## What is in the box

- **ReadMe.htm** — this file.
- **HomerView.htm** — the full guide and reference, including a tutorial.
- **Hotkeys.htm** — every key, for both screen readers.
- **History.htm** — what changed in each release.
- **Developer.htm** — how to rebuild from source.
- **Announce.htm** — what the project is for.

Each is on the Alternate Menu, and most have a key of their own.

## Requirements

- Windows 10 or later
- Microsoft Edge, which is built into every modern Windows computer
- One of:
  - [JAWS 2024 or later, from Freedom Scientific](https://www.freedomscientific.com/products/software/jaws/)
  - [NVDA 2023.1 or later, from NV Access](https://www.nvaccess.org/download/)
- Optional: pandoc or 2htm, for the widest range of document formats. HomerView
  finds them if installed and says plainly when they are not.

## Licence and source

Free and open source.

- [HomerView executable installer](https://github.com/JamalMazrui/HomerView/releases/latest/download/HomerView_setup.exe)
- [HomerView project on GitHub](https://github.com/JamalMazrui/HomerView)

---
title: HomerView
subtitle: Read the web the way a browser sees it
author: Jamal Mazrui
---

# What HomerView is

HomerView is a free add-on for the NVDA screen reader. It opens its own copy of
Microsoft Edge and talks to that copy directly, the way a web developer's tools
do.

That matters because of a gap. For thirty years, blind people have read the web
through a flat copy of the page that the screen reader builds. It works. But
the browser knows things that never reach that copy. You are told a button is
not there. You finish an article and never learn that a banner was covering
half the screen.

HomerView closes the gap. It can see the page three ways at once: as a window,
as your reading order, and as the browser itself understands it. Almost nothing
else has all three.

No artificial intelligence is involved, and nothing about the pages you read
leaves your computer.

# What you need

- **NVDA 2025.1 or newer.** It is free, from
  [nvaccess.org](https://www.nvaccess.org/download).
- **Microsoft Edge.** It comes with Windows.
- **Windows 10 or 11.**

That is all. HomerView uses the Edge you already have.

# Quick start

1. Run the installer.
2. On the last page, leave the box checked that gives the add-on to NVDA. NVDA
   will ask you to confirm it, then restart.
3. Press **Alt+NVDA+H**. A HomerView window opens.
4. Press **Alt+NVDA+F10** for a list of every command.

If you remember one command, make it Alt+NVDA+F10. Everything else can be found
from there.

# If the installer cannot hand the add-on to NVDA

Install it from the file, which is already on your computer.

1. Press NVDA+N for the NVDA menu.
2. Choose Tools, then Add-on Store, then Install from external source.
3. Pick **HomerView.nvda-addon** from the build folder where HomerView was
   installed, usually C:\Program Files\HomerView\build.
4. Confirm, and let NVDA restart.

Pressing Enter on that same file in File Explorer does the same thing.

# Six commands worth learning early

- **Y** describes how the page is laid out. It tells you what a sighted person
  can see that your reading order never mentions: a cookie banner, a bar pinned
  over the text, a dialog waiting for an answer.
- **J** jumps to the main content, past the menus. **Shift+J** finds it on a
  page that never said where it is.
- **Alt+NVDA+A** tests the page for accessibility problems, then offers to find
  the publisher's contact address and write the report as an email.
- **Control+O** opens a Word file, spreadsheet, slide deck, PDF or ebook. It is
  turned into a web page, so every HomerView command works on it.
- **Shift+F9** pulls the readable part of a page into a page of its own, which
  you can search, save or send.
- **Alt+Q** looks something up: a word, a place, the weather, a book. All of it
  uses free services that need no account.

# Where to read more

- **HomerView.md** is the full guide. Every command, what it does, and how HomerView
  fits together.
- **History.md** says what changed in each release.
- **Developer.md** explains how to build HomerView from its source.
- **Announce.md** is the short description of the project.

Each of those also comes as a web page, with the same name and a .htm ending,
which HomerView itself can open.

# When something does not work

Press **Alt+Control+F1** to open this session's log. It records what HomerView
did and what went wrong, and it is the fastest way to an answer.

If a command does nothing, open the Alternate Menu with **Alt+NVDA+F10** and
run it from there. The menu only lists commands that apply right now, so a
command missing from it is a command that cannot run yet.

# Licence

HomerView is free software under the GNU General Public License version 2,
which is the licence NVDA itself uses.

Project page: [github.com/JamalMazrui/HomerView](https://github.com/JamalMazrui/HomerView)

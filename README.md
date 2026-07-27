---
title: HomerView
subtitle: A Quick Start
author: Jamal Mazrui
---

# HomerView

HomerView is an NVDA add-on that runs its own copy of Microsoft Edge and drives
it through the Chrome DevTools Protocol. That combination gives a screen reader
user three things at once: the browser's own interface, the page as NVDA has
built it, and the page as the browser itself sees it. Very little else has all
three, and most of what HomerView does comes from having them together.

It is also a document reader. A Word file, a spreadsheet, a slide deck, a PDF or
an ebook can be opened and read with the same commands as a web page.

# Introduction for JAWS users

If you have used JAWS, a good deal of HomerView will already be in your fingers.
Where a JAWS command has an obvious place here and the key is free in NVDA, that
key is used. Where it is not free, the command still exists on a key that costs
nothing.

    NVDA+F5             list the form fields, as Insert+F5 does
    NVDA+F6             list the headings, as Insert+F6 does
    NVDA+Shift+F7       list the links; Insert+F7 belongs to NVDA's own
                        Elements List, so the links moved one key over
    Alt+Delete          say how far through the page you are
    Alt+A               say the web address; twice spells it, three times
                        copies it
    Control+F           find, without needing a screen reader modifier, which
                        is the JAWS judgment and the right one
    Control+F3          find by regular expression; F3 repeats either kind
    Y                   summarise the page, in the spirit of Page Explorer

Two things JAWS does that HomerView does differently, and deliberately.

Page Explorer asks a language model. HomerView reads the page itself, so it
never invents a region that is not there, and it can report what a model would
not be told: a bar pinned over the content, an open dialog, text that is on
screen but hidden from screen readers.

JAWS labels what it reports, saying "Address" before the address. NVDA speaks
the value alone, and HomerView follows NVDA. If you would rather have the
labels, turn them on in NVDA's Settings, under HomerView.

The Homer editor commands are here too, if you have used EdSharp or FileDir.
Alt+F8 reads the page, Control+F8 copies it, F8 and Shift+F8 select without
holding Shift, the apostrophe key carries the clipboard commands, and the grave
accent key adjusts punctuation, rate and volume.

# Introduction for NVDA users

HomerView is where you would expect it to be.

It appears in the NVDA menu, under Tools, with items for starting the browser,
listing every command, and opening this guide. Nothing has to be memorised
before you can find it.

It has a page in NVDA's Settings, under HomerView, holding the few settings
worth changing and a list of every folder it writes to.

Every command appears in Input Gestures under one HomerView category, so you can
see the whole set together and change any key you dislike. Every command has a
description, so pressing NVDA+1 for input help and then the key tells you what
it does.

Commands that work anywhere carry the NVDA key, so they never shadow anything in
another program. Commands that work only in a page use shorter keys, which they
can afford because they exist nowhere else.

No HomerView command takes a key NVDA uses by default, on either the desktop or
the laptop layout. Where a browser key is taken, such as Control+F, Control+O or
Control+S, HomerView does everything the browser did with it and more.

Browse mode still works as you know it. Quick navigation, the Elements List,
say all, the review cursor and everything else are untouched. HomerView adds to
them rather than replacing them.

# What you need

NVDA, which is free: https://www.nvaccess.org/download

Microsoft Edge, which is already on your computer. It comes with every modern
version of Windows, so there is nothing to install for it. HomerView starts its
own copy with its own settings, and leaves your usual browser alone.

A converter, only if you want to open Word, Excel, PowerPoint, PDF or ebook
files. HomerView finds LibreOffice, pandoc, 2htm or Calibre if any is installed,
and tells you which to install if none is.

# Quick start

Install the add-on, restart NVDA, and press **NVDA+Alt+H**.

A browser window opens on the HomerView start page, which lists the commands and
gives you somewhere to begin. From there:

1. Press **Control+L** and type an address, as you would in any browser.
2. Press **Alt+A** to hear the web address of the page you are reading. Press it
   twice to spell it, three times to copy it.
3. Press **J** to jump to the main content, past the banner and the navigation.
   If the page never said where its main content is, **Shift+J** makes a
   sensible guess and tells you it is guessing.
4. Press **Y** for a summary of how the page is built, including things that are
   on screen but leave no trace in the reading order, such as a cookie banner or
   a bar pinned to the top of the window.
5. Press **NVDA+Alt+F10** for a list of every command, in one alphabetical list,
   with its key beside it. Press Enter to run whatever you choose. This works
   everywhere, including before HomerView Edge is running, and it can start it
   for you.

If you remember only one command, make it NVDA+Alt+F10. Everything else can be
found from there, including how to start HomerView in the first place.

# Opening a document

Press **Control+O** and choose a file. Word, Excel, PowerPoint, PDF, rich text,
OpenDocument, EPUB and Markdown are all converted to a web page behind the
scenes and opened in the HomerView window, where every command above works on
them.

Conversion needs a converter. HomerView looks for LibreOffice, pandoc, 2htm and
Calibre, uses whichever suits the format, and tells you which to install if none
is present. LibreOffice covers the most formats and needs no Microsoft Office.

# Five commands worth learning early

- **Scroll Lock** starts reading continuously, and stops it. One key for both.
- **Alt+F8** reads the whole page without moving the cursor. **Control+F8**
  copies it.
- **Control+F** finds text, not case sensitive. **Control+F3** finds a regular
  expression. **F3** repeats whichever was last used.
- **Alt+K** tests the page for accessibility problems and offers to help you
  report them to whoever publishes the site.
- **Control+S** saves the page as a single file archive the way Edge does, or as a
  web page, Markdown, plain text, a Word document, a PDF, an image, or the
  accessibility tree.
- **NVDA+Alt+W** lists the kinds of file linked from the page and downloads the
  ones you choose.

# When something does not work

Commands only work in windows HomerView itself opened. An Edge window that was
already running has no debugging connection and cannot be given one, which is a
limitation of the browser rather than of HomerView. Press NVDA+Alt+H and use the
window it opens.

If a command does nothing, open the Alternate Menu with **Alt+F10** and run it
from there. If it fails, it now says what failed and that the log has the
detail.

# The rest of the documentation

- **HomerView.md** is the full user guide: every command, what it does, and why
  it is bound where it is.
- **History.md** records what changed in each version.
- **Developer.md** covers the architecture, the shared Homer toolkit, and how to
  build and release.

All three can be opened from the Alternate Menu, and all are listed on the
HomerView start page.

# Licence

HomerView is free software under the GNU General Public License, version 2, the
same licence as NVDA itself.

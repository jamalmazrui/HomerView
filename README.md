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
5. Press **Alt+F10** for a list of every command, in one alphabetical list, with
   its key beside it. Press Enter to run whatever you choose.

If you remember only one command, make it Alt+F10. Everything else can be found
from there.

# Opening a document

Press **Control+O** and choose a file. Word, Excel, PowerPoint, PDF, rich text,
OpenDocument, EPUB and Markdown are all converted to a web page behind the
scenes and opened in the HomerView window, where every command above works on
them.

Conversion needs a converter. HomerView looks for LibreOffice, pandoc, 2htm and
Calibre, uses whichever suits the format, and tells you which to install if none
is present. LibreOffice covers the most formats and needs no Microsoft Office.

# Five commands worth learning early

- **Alt+F8** reads the whole page without moving the cursor. **Control+F8**
  copies it.
- **Control+F** finds text or a regular expression, and moves the browse cursor
  to it. **F3** repeats the search.
- **Alt+K** tests the page for accessibility problems and offers to help you
  report them to whoever publishes the site.
- **Control+F12** saves the page as a web page, Markdown, plain text, a Word
  document, a PDF, or an image of the whole page.
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

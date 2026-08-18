---
title: "HomerView: JAWS support reaches parity with NVDA"
---

HomerView is a free, open-source companion for reading the web with a screen
reader on Windows. It works with **JAWS** and with **NVDA**, and as of this
release the two are at feature parity: the same commands, the same answers, the
same generated pages. Neither is the main one.

Where a key differs between them, it differs because each follows its own screen
reader's conventions. Everything else is the same on both, so what you learn on
one you already know on the other.

## What HomerView is for

**A browser.** It drives its own copy of Microsoft Edge, so every native Edge
feature is there, reached through your own screen reader's browse mode rather
than through anything HomerView invented.

**An accessibility tester.** One command runs the axe engine over the current
page, another runs IBM's. Each writes a report naming every rule that failed,
its severity, the elements involved and how to fix them: plain enough to send to
a publisher, specific enough for their developers to act on.

**A document and ebook reader.** DOCX, EPUB, PDF and other popular formats are
converted to structured HTML and opened in the browser, so headings, lists,
tables and links become real navigation in browse mode rather than a flat wall
of text.

**A downloader.** It finds the files a page points at, identifies each type, and
fetches the kinds you choose, using the browser's own cookies so a signed-in
page works.

**An extractor.** One command lifts the main content out of a page and opens it
free of navigation, banners and advertising.

**And a set of smaller aids** for finding and selecting text, listing tabs and
links, reading metadata, and putting what you find on the clipboard.

## Getting it

HomerView is at <https://github.com/JamalMazrui/HomerView>. Run the installer
and tick the box for the screen reader you use; it offers whichever it finds.

You will need one of:

- **JAWS**, from Freedom Scientific:
  <https://www.freedomscientific.com/products/software/jaws/>
- **NVDA**, from NV Access: <https://www.nvaccess.org/download/>

Microsoft Edge is required. HomerView keeps its own browser profile, so it never
disturbs the one you browse with.

## Where to start

Press **Alt+Insert+H** in JAWS, or **Alt+NVDA+H** in NVDA, to open the HomerView
window. From there the menu key lists every command and hot key help lists every
key. The full guide is HomerView.htm, installed with the program.

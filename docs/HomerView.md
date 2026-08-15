---
title: "HomerView User Guide"
---

HomerView is a screen-reader companion for reading the web. It works with
**JAWS** and with **NVDA**, and the two are kept at parity on purpose: the same
commands, the same answers, on keys chosen to suit each screen reader's own
conventions. Where this guide gives two keys, the first is JAWS and the second
is NVDA.

## What HomerView is

HomerView launches and drives its own copy of Microsoft Edge through the Chrome
DevTools Protocol. That connection is the whole point. It lets HomerView ask the
browser questions that a screen reader, which sees only the rendered result,
cannot answer:

- the page as scripts have actually built it, including links that were not in
  the file the server sent
- the browser's own cookies and user agent, so a file behind a sign-in can be
  fetched exactly as a click would fetch it
- what a link's server says about the thing at the other end, before you go
  there

It uses a separate browser profile, so your ordinary browsing is untouched.

## What HomerView deliberately does not do

There is no HomerView command for listing headings, listing links, listing form
fields, exploring the page, saying the address, or finding text forwards. JAWS
and NVDA already do all of those well, and a second way of doing them would be
one more thing to remember for no gain.

HomerView adds a command only where it can do something your screen reader
cannot, or can do it noticeably better. Reverse find exists because JAWS's own
find goes forward only. Pattern find exists because neither screen reader can
search by regular expression. Copy All exists because selecting a whole page and
copying it takes the browser's selection, which drags in the navigation and the
footers.

## Getting started

### Starting HomerView

**Alt+JAWSKey+H** / **NVDA+Alt+H** launches HomerView's Edge window, or
reconnects to it if it is already running.

### The Alternate Menu

**Alt+JAWSKey+F10** / **NVDA+Alt+F10** opens a list of every command, each with
its key beside it. This is the discovery surface: nothing in HomerView is hidden
behind a keystroke you must already know. Arrow to a command and press Enter.

### The Hotkey Summary

**Alt+Shift+H** shows every command in a window where each key line is a link.
Press Enter on a line to run that command. Its first line gives the version and
the installation time, which is how you confirm which build is loaded.

## Tutorial

The Quick Start in ReadMe.htm gets you moving in five minutes. This tutorial
goes further, and assumes you have HomerView running.

### Reading an article properly

Open a news article or a long blog post — somewhere with a lot of navigation
around the content.

Press **Shift+Q** / **Shift+J**, Jump to Probable Main. On a page that declares
its main region you land there and hear "Main content, as the page declares it".
On a page that declares nothing, HomerView weighs every part of the page — how
much text it holds, how much of that text is links — and moves you to the
winner, saying "Main content, by weighing the page". Either way you are past the
navigation in one keystroke.

Now press **Shift+F9**, Extract Main Content. HomerView runs Mozilla's
Readability over the page and opens the result in a tab of its own: the article,
its title and byline, and its links, without the surrounding furniture. Every
other HomerView command works on that tab, because it is a real page in
HomerView's own browser.

If you would rather have the text than the tab, **Alt+F8** is Read All. It reads
the whole page from the top and does not move your cursor, which is the
difference between it and your screen reader's Say All: that one starts wherever
you are and leaves you further down.

### Deciding whether to follow a link

Put the cursor on any link and press **Alt+L**, Link Target.

HomerView asks the link's server about the thing at the other end without
fetching the whole of it, and tells you what it is: a web page, a PDF, a Zip
archive; how big; the title of the page if it is a page; roughly how many words
and how many minutes that is; whether there is a paywall; and, importantly,
whether the address ends up somewhere other than where it appeared to point.
Shortened links are resolved and named.

If the link cannot be reached at all, you still get its address, because that
was known before anything was asked.

### Finding things

Your screen reader's own **Control+F** searches forward, and HomerView leaves
that key alone.

- **Control+Shift+F** searches **backwards**, which JAWS has no key for.
- **Control+F3** searches forward for a **regular expression**.
- **Control+Shift+F3** searches backwards for one.
- **F3** and **Shift+F3** move to the next and previous match, of whichever kind
  of find you did last.

Try **Control+F3** with a pattern like `\d{4}` to jump between years on a page,
or `\$[\d,]+` to move between prices.

**Control+Shift+E**, Extract with Regular Expression, answers the other
question: not "where is the next one" but "what are they all". It gathers every
match into a window, each separated by a form feed between blank lines, so they
read as a series of small pages rather than a run-on list.

### Selecting a passage

HomerView uses EdSharp's convention, which is a pair rather than a drag:

1. Move to where the passage begins and press **F8**, Start Selection.
2. Move to where it ends — by arrow, by heading, by find, however suits.
3. Press **Shift+F8**, Complete Selection.

Then **Control+C** copies it. With no selection, Control+C copies the line the
cursor is on, which is the case that comes up most often and which the browser's
own Control+C does nothing about.

**Alt+C**, Copy Append, adds the selection or the line to what is already on the
clipboard, with a blank line between. That is how you gather three passages from
different parts of a page into one note without a second window to paste into.

**Control+F8** copies the whole page.

### Gathering files from a page

Find a page with documents on it — an agency's publications page is ideal — and
press **Alt+Shift+W**, Web Download.

HomerView tells you what is there by kind: "pdf: PDF document, 11. docx: Word
document, 6. html: Web page, 1." and offers you the sensible ones already filled
in. Page addresses and script assets are listed but not chosen for you, since
they are numerous and rarely wanted; type `html` if you want them.

Then each file is named aloud as it is fetched, and silence after a name means
it arrived. Only a failure says anything more. At the end a message box gives
the count, the folder and anything that did not come.

The files go to a folder under Downloads named after the page, and a second run
adds to that folder rather than replacing it.

The reason this works where a plain download would not is that the request
carries the browser's own cookies, user agent and referrer, plus the Sec-Fetch
headers a click produces. A file gated behind a sign-in comes to you as it would
to a click.

### Checking accessibility

**Alt+JAWSKey+A** runs Deque's axe-core over the page and writes a readable
report to your Downloads folder as `Axe-<page title>.htm`, then opens it.

The report starts in plain language — how many problems, and the reminder that
an automated tool finds roughly thirty to forty per cent of accessibility
problems. Then the severity breakdown, the failure rate (impact-weighted faults
per thousand bytes of page, for comparing a page with itself over time), the
three most common problems, the recommended next steps, and then each problem
with its WCAG criterion **named** and its conformance level given, up to five
places each with the selector, the element and the engine's own explanation.

**Alt+JAWSKey+I** runs IBM's Equal Access engine instead. Its unified ruleset
folds EN 301 549 and Section 508 in with WCAG, which is the superset several
procurement regimes actually ask about. It writes four files — json, csv, xlsx
and html — into a folder named `<page title> - accessibility` under Downloads,
replacing that folder each run, and opens the HTML report.

Use both. They disagree usefully.

### Opening a document that is not a web page

**Control+O** opens a file dialog — the classic Windows one, with a real folder
tree — and will open a Word document, a PDF, an ebook, a spreadsheet or a slide
deck by converting it to a web page first. After that every HomerView command
works on it: find, extract, select, copy, read all.

**Control+S** saves the page you are on, as a web page or as anything pandoc can
write — Word, OpenDocument, Markdown, EPUB — chosen simply by naming the file.

Conversion needs pandoc or 2htm. HomerView looks for them where they usually
live and says plainly when neither is there.

## Reference

### Where things go

- **Downloads\\\<page title\>** — files fetched by Web Download. Kept between
  runs; duplicate names are numbered.
- **Downloads\\Axe-\<page title\>.htm** — the axe report.
- **Downloads\\\<page title\> - accessibility** — the IBM reports, replaced each
  run.
- **%LOCALAPPDATA%\\HomerView\\logs** — the log, one file per installation,
  holding the installation and every session since.
- **%LOCALAPPDATA%\\HomerView\\EdgeProfile** — HomerView's browser profile.

### The log

Everything HomerView does is logged: every command, every answer, every failure,
in the order it happened.

- **Alt+JAWSKey+L** / **Control+Shift+L** puts the log on the clipboard, ready
  to attach to a message.
- **Alt+Control+F1** opens the same log to read.

### HomerView's own documents

- **Control+F1** — this guide
- **Alt+Shift+F1** — the Quick Start
- **Shift+F1** — the history of changes
- **Control+Shift+F1** — the developer notes
- **Alt+F1** — which build is loaded and where everything lives
- The hotkey document and the project announcement are on the Alternate Menu

### Hotkeys

This section is also available as a document of its own, Hotkeys.htm, and as the
Hotkey Summary on **Alt+Shift+H**, where every key is a link you can press Enter
on.

#### Getting started

- **Launch HomerView** — JAWS: Alt+JAWSKey+H. NVDA: NVDA+Alt+H.
- **Alternate Menu** — JAWS: Alt+JAWSKey+F10. NVDA: NVDA+Alt+F10.
- **Hotkey Summary** — JAWS: Alt+Shift+H. NVDA: Alt+Shift+H.

#### Reading the page

- **Jump to Probable Main** — JAWS: Shift+Q. NVDA: Shift+J.
- **Read All** — JAWS: Alt+F8. NVDA: Alt+F8.
- **Extract Main Content** — JAWS: Shift+F9. NVDA: Shift+F9.
- **Say Metadata** — JAWS: Alt+M. NVDA: Alt+M.
- **Link Target** — JAWS: Alt+L. NVDA: Alt+L.

#### Finding

- **Reverse Find** — JAWS: Control+Shift+F. NVDA: Control+Shift+F.
- **Forward Find with Regular Expression** — JAWS: Control+F3. NVDA: Control+F3.
- **Reverse Find with Regular Expression** — JAWS: Control+Shift+F3. NVDA: Control+Shift+F3.
- **Forward Find Again** — JAWS: F3. NVDA: F3.
- **Reverse Find Again** — JAWS: Shift+F3. NVDA: Shift+F3.
- **Extract with Regular Expression** — JAWS: Control+Shift+E. NVDA: not yet on NVDA.

#### Selecting and copying

- **Start Selection** — JAWS: F8. NVDA: F8.
- **Complete Selection** — JAWS: Shift+F8. NVDA: Shift+F8.
- **Copy Line** — JAWS: Control+C. NVDA: Control+C.
- **Copy Append** — JAWS: Alt+C. NVDA: Alt+C.
- **Copy All** — JAWS: Control+F8. NVDA: Control+F8.
- **Page Links to Clipboard** — JAWS: Alt+Shift+P. NVDA: Alt+Shift+P.

#### The clipboard

- **Say Clipboard** — JAWS: Alt+Apostrophe. NVDA: Alt+apostrophe.
- **Save Clipboard** — JAWS: Control+Apostrophe. NVDA: Control+apostrophe.
- **Append Clipboard** — JAWS: Control+Shift+Apostrophe. NVDA: Control+Shift+apostrophe.
- **Clear Clipboard** — JAWS: Alt+Shift+Apostrophe. NVDA: Alt+Shift+apostrophe.

#### Documents and files

- **Open Document** — JAWS: Control+O. NVDA: Control+O.
- **Save Page** — JAWS: Control+S. NVDA: Control+S, Control+Alt+S.
- **Web Download** — JAWS: Alt+Shift+W. NVDA: Alt+Shift+W.

#### Accessibility

- **Check with Axe** — JAWS: Alt+JAWSKey+A. NVDA: on the Alternate Menu, under Check Accessibility.
- **Check with Equal Access** — JAWS: Alt+JAWSKey+I. NVDA: on the Alternate Menu, under Check Accessibility.

#### Tabs and dialogs

- **Tab List** — JAWS: on the Alternate Menu only. NVDA: F4.
- **Tab Names** — JAWS: Shift+F4. NVDA: Shift+F4.
- **Dismiss Dialog** — JAWS: Alt+JAWSKey+D. NVDA: NVDA+Alt+D.

#### HomerView's own documents

- **User Guide** — JAWS: Control+F1. NVDA: Control+F1.
- **Quick Start** — JAWS: Alt+Shift+F1. NVDA: Alt+Shift+F1.
- **History of Changes** — JAWS: Shift+F1. NVDA: Shift+F1.
- **Developer Notes** — JAWS: Control+Shift+F1. NVDA: Control+Shift+F1.
- **Hotkey Document** — JAWS: on the Alternate Menu only. NVDA: on the Alternate Menu only.
- **Project Announcement** — JAWS: on the Alternate Menu only. NVDA: on the Alternate Menu only.
- **About HomerView** — JAWS: Alt+F1. NVDA: Alt+F1.
- **Log to Clipboard** — JAWS: Alt+JAWSKey+L. NVDA: Control+Shift+L.
- **Session Log** — JAWS: Alt+Control+F1. NVDA: Alt+Control+F1.

## Troubleshooting

**A command says the browser is not running.** Press Alt+JAWSKey+H / NVDA+Alt+H
to launch or reconnect.

**A key does nothing.** Open the Alternate Menu and run the command from there.
If it works from the menu, the key is being taken by something else. Report it
with the log attached.

**Edge shows a warning about an unsupported command-line flag.** It should not
any more; if it does, the log's launch line lists every flag passed.

**An accessibility check says the engine could not be loaded.** That means the
engine could not be downloaded; check the internet connection. It is cached
after the first successful run.

**Opening a Word file or PDF says it could not be converted.** Install pandoc or
2htm. HomerView finds them but does not ship them.

**Something took a long time and nothing came back.** Send the log. Every
command records how long its parts took.

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
Readability over the page, saves it as `Main.htm` in the page's folder, and
opens it in a tab of its own: the article, its title and byline, and its links,
without the surrounding furniture. Every
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

The files go to the page's own folder under Downloads, beside anything else that
page has produced, and a second run adds to it rather than replacing it. Names
are unescaped first: a file arriving as `Annual%20Report.pdf` is saved as
`Annual Report.pdf`, since a screen reader reads every escape aloud.

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
procurement regimes actually ask about. It writes four files — `IBM.json`,
`IBM.csv`, `IBM.xlsx` and `IBM.htm` — into the same folder, and opens the HTML
report.

Use both. They disagree usefully.

### Finding who to tell

**Alt+JAWSKey+C**, Find Contacts, answers the question that follows an
accessibility check: who do I tell?

It looks in three places — the page in front of you, the site's home page,
because a contact link lives in a footer an article may not carry, and the
handful of addresses an accessibility statement usually lives at. That last one
is why a statement is found at all, since most sites that have one never link to
it from an article.

You get the statement if there is one, email addresses, accessibility and
contact pages, and social media accounts. It is a command of its own rather than
a section of a report, because the question gets asked at other times.

### Finding out who and what a page is about

**Alt+N**, List Names, answers a question headings and links cannot: not how the
page is arranged or where it goes, but *who and what it is about*.

It reads the page's text with compromise, a rule-based English parser, and lists
the people, places, organisations, dates, amounts of money and percentages it
finds. The result is saved as `Names.htm` in the page's folder and opened.

On a long report this is the fastest way to see who is involved; on a page of
deadlines the list of dates is the thing you came for.

It guesses, and the report says so on its own first page. A rule-based tagger
will call a company a person now and then and will miss a name it has not seen.
Treat it as a starting point rather than an index.

### Opening a document that is not a web page

**Control+O** opens a file dialog — the classic Windows one, with a real folder
tree — and will open a Word document, a PDF, an ebook, a spreadsheet or a slide
deck by converting it to a web page first. After that every HomerView command
works on it: find, extract, select, copy, read all.

**Control+S** saves the page you are on, as a web page, as a complete archive
that keeps everything the page uses in one file, or as anything pandoc can write
— Word, OpenDocument, Markdown, EPUB — chosen simply by naming the file.

It no longer offers the markup, the image, the PDF or the accessibility tree.
Those are written automatically whenever you run an accessibility check, which
is when they are actually wanted.

Conversion needs pandoc or 2htm. HomerView looks for them where they usually
live and says plainly when neither is there.

### Finding who to tell

**Alt+NVDA+C** / **Alt+JAWSKey+C**, Find Contacts, answers the question that
follows an accessibility check.

It looks in three places: the page in front of you, the site's home page —
because a contact link lives in a footer an article may not carry — and the
handful of addresses an accessibility statement usually lives at. That last one
is why a statement gets found at all, since most sites that have one never link
to it from an article.

You get the statement if there is one, email addresses, accessibility and
contact pages, and social media accounts.

## Reference

### Where things go

One folder per page, under Downloads, named after the page. Everything that page
produces goes in it, each file named for what made it. The folder is kept
between runs and each tool replaces its own files, so a second accessibility
check does not disturb what you downloaded, and a download replaces the file of
the same name rather than piling up numbered copies.

Written when you ask for them:

- **`Main.htm`** — the readable article, from Extract Main Content
- **`Names.htm`** — the people, places and dates, from List Names
- **Downloaded files**, under their own names, from Web Download

Written by the axe check:

- **`Axe.htm`** — the readable report
- **`Axe.json`** — the engine's own findings, for doing something else with

Written by the IBM check:

- **`IBM.htm`**, **`IBM.json`**, **`IBM.csv`**, **`IBM.xlsx`** — the same
  findings as a report, as data, as a table, and as a workbook

Written automatically by either check. This is the page itself, kept as evidence
of what was tested:

- **`Page.htm`** — the markup *after script has run*, which is what the engine
  actually tested and is not what the server sent
- **`Page.png`** — the whole page as a sighted person sees it, for showing
  somebody what a finding refers to
- **`Page.pdf`** — the page as it would print, one file to attach to a complaint
- **`Tree.json`** — the accessibility tree: every node with its role, its name,
  and where a node was left out, **the reasons why**. Nothing else HomerView
  produces answers the question of why something on screen is absent from the
  reading order.

Those four used to be things you asked for one at a time from Save Page. That
was the wrong shape: nobody wants a screenshot of a page for its own sake, they
want it when a report says something is wrong. By the time you are reading the
report it is too late to go back and capture the page as it then was, so the
evidence is taken at the same moment as the finding.

And elsewhere:

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
on. Each entry gives the NVDA key and the JAWS key.

#### Starting HomerView

- **Alternate Menu**
    - NVDA: Alt+NVDA+F10
    - JAWS: Alt+JAWSKey+F10
    - Present all commands in a single, alphabetized list. F10 opens a menu bar in Windows, and this is the menu HomerView has instead.
- **Hotkey Summary**
    - NVDA: Alt+Shift+H
    - JAWS: Alt+Shift+H
    - Display this list of command names, hot keys, and descriptions in a new window, as EdSharp does on the same key.
- **Launch HomerView**
    - NVDA: Alt+NVDA+H
    - JAWS: Alt+JAWSKey+H
    - Launches or reconnects the HomerView copy of Microsoft Edge. H for HomerView, and it works anywhere because nothing is running yet.

#### Reading the documentation

- **About HomerView**
    - NVDA: Alt+F1
    - JAWS: Alt+F1
    - Display version and release date, and where HomerView keeps its files.
- **Developer Notes**
    - NVDA: Control+Shift+F1
    - JAWS: Control+Shift+F1
    - Open the notes on how HomerView is built and why.
- **History of Changes**
    - NVDA: Shift+F1
    - JAWS: Shift+F1
    - Display list of fixes and improvements.
- **Hotkey Document**
    - NVDA: no key
    - JAWS: no key, on the Alternate Menu
    - Open the shipped list of every command, key and description. Hotkey Summary on Alt+Shift+H builds the same list from the program itself; this opens the copy that came with it.
- **Log to Clipboard**
    - NVDA: Control+Shift+L
    - JAWS: Alt+JAWSKey+L
    - Copy the HomerView log to the clipboard as a file, so Control+V attaches it to an email rather than typing its name into one. L for Log, beside the other Control+Shift keys that put something somewhere.
- **Project Announcement**
    - NVDA: no key
    - JAWS: no key, on the Alternate Menu
    - Open the short description of HomerView, for passing on to somebody who has not met it.
- **Quick Start**
    - NVDA: Alt+Shift+F1
    - JAWS: Alt+Shift+F1
    - Open the first ten minutes of HomerView, for somebody new to it.
- **Session Log**
    - NVDA: Alt+Control+F1
    - JAWS: Alt+Control+F1
    - Open a copy of this session's log, for working out what went wrong.
- **User Guide**
    - NVDA: Control+F1
    - JAWS: Control+F1
    - Open Documentation in the HomerView window. F1 is help everywhere, but plain F1 opens Edge's own help and stays Edge's, so the family here takes F1 with a modifier.

#### Moving through a page

- **Go to Percent**
    - NVDA: Control+G
    - JAWS: **not yet on JAWS**
    - Go to percentage point in document, as EdSharp does on the same key.
- **Go to Percent Again**
    - NVDA: Alt+G
    - JAWS: **not yet on JAWS**
    - Repeat Go command, or move a step further with plus or minus.
- **Jump to Main**
    - NVDA: J, or Alt+NVDA+J
    - JAWS: **not yet on JAWS**
    - Jumps to the main content the page declares. J for Jump, and it is one of only three letters NVDA leaves free in a page.
- **Jump to Probable Main**
    - NVDA: Shift+J
    - JAWS: Shift+Q
    - Finds the main content of a page that declares none, by weighing every part of it, and says that it inferred rather than was told.
- **Next Different Kind**
    - NVDA: Alt+Z
    - JAWS: **not yet on JAWS**
    - Moves to the next thing of a different kind, which JAWS does with D.
- **Next Paragraph**
    - NVDA: Control+DownArrow
    - JAWS: **not yet on JAWS**
    - Moves to the next paragraph and reads it. Control with an arrow moves by paragraph in Word and in most editors.
- **Next Same Kind**
    - NVDA: Z
    - JAWS: **not yet on JAWS**
    - Moves to the next thing of the same kind as the one you are on, whatever that is. Z because NVDA leaves it free, and JAWS does this with S.
- **Next Sentence**
    - NVDA: Alt+DownArrow
    - JAWS: **not yet on JAWS**
    - Moves to the next sentence and reads it. Alt with an arrow moves by something larger than a line and smaller than a paragraph.
- **Prior Different Kind**
    - NVDA: Alt+Shift+Z
    - JAWS: **not yet on JAWS**
    - Moves to the previous thing of a different kind.
- **Prior Paragraph**
    - NVDA: Control+UpArrow
    - JAWS: **not yet on JAWS**
    - Moves to the previous paragraph and reads it.
- **Prior Same Kind**
    - NVDA: Shift+Z
    - JAWS: **not yet on JAWS**
    - Moves to the previous thing of the same kind as the one you are on.
- **Prior Sentence**
    - NVDA: Alt+UpArrow
    - JAWS: **not yet on JAWS**
    - Moves to the previous sentence and reads it.

#### Finding text

- **Extract with Regular Expression**
    - NVDA: Control+Shift+E
    - JAWS: Control+Shift+E
    - Gathers every match of a pattern for reading, each separated by a form feed between blank lines.
- **Forward Find**
    - NVDA: Control+F
    - JAWS: **not yet on JAWS**
    - Search forward for string, using NVDA's own find so the dialog and its behaviour are the ones you already know.
- **Forward Find Again**
    - NVDA: F3
    - JAWS: F3
    - Search forward for next match, of whichever kind of find was used last.
- **Forward Find at Cursor**
    - NVDA: Alt+F3
    - JAWS: **not yet on JAWS**
    - Search forward for chunk or selected text, on the key EdSharp uses for it.
- **Forward Find with Regular Expression**
    - NVDA: Control+F3
    - JAWS: Control+F3
    - Search forward for regular expression, which NVDA's own find cannot do.
- **Reverse Find**
    - NVDA: Control+Shift+F
    - JAWS: Control+Shift+F (named "Reverse Find for Text" there)
    - Search backward for string.
- **Reverse Find Again**
    - NVDA: Shift+F3
    - JAWS: Shift+F3
    - Search backward for previous match.
- **Reverse Find at Cursor**
    - NVDA: Alt+Shift+F3
    - JAWS: **not yet on JAWS**
    - Search backward for chunk or selected text.
- **Reverse Find with Regular Expression**
    - NVDA: Control+Shift+F3
    - JAWS: Control+Shift+F3
    - Search backward for regular expression.

#### Listing what is on the page

- **Explore Page**
    - NVDA: Alt+NVDA+E
    - JAWS: **not yet on JAWS**
    - Describes how the page is laid out, including what a sighted person can see that your reading order never mentions. E for Explore. It gave up its bare Y: a single letter in browse mode reads as a navigation key, and this command does not move anywhere.
- **List Elements**
    - NVDA: Alt+NVDA+L
    - JAWS: **not yet on JAWS**
    - Lists any kind of element, including kinds NVDA's own Elements List does not offer. L for List.
- **List Form Fields**
    - NVDA: NVDA+F5
    - JAWS: **not yet on JAWS**
    - List the form fields on the page, on the key JAWS uses for its form field list.
- **List Headings**
    - NVDA: NVDA+F6
    - JAWS: **not yet on JAWS**
    - List the headings on the page, on the key JAWS uses for its heading list.
- **List Links**
    - NVDA: NVDA+Shift+F7
    - JAWS: **not yet on JAWS**
    - List the links on the page, beside the key JAWS uses for its link list.

#### Asking about the page

- **Link Target**
    - NVDA: Alt+L
    - JAWS: Alt+L
    - Ask what is actually at that link without going there: what kind of thing, how big, and whether it ends up where it claims. L for Link.
- **List Names**
    - NVDA: Alt+N
    - JAWS: Alt+N
    - Lists the people, places, organisations and dates a page mentions. A rule-based engine reads the text, so it guesses; the report says so.
- **Page Links to Clipboard**
    - NVDA: Alt+Shift+P
    - JAWS: Alt+Shift+P
    - Copy every link address on the page to the clipboard, as EdSharp copies a path on the same key.
- **Say Address**
    - NVDA: Alt+A
    - JAWS: **not yet on JAWS**
    - Says the web address of this page. Twice spells it, three times copies it. A for Address.
- **Say Address Anywhere**
    - NVDA: Alt+NVDA+U
    - JAWS: **not yet on JAWS**
    - Says the web address from anywhere in the window, including the address bar.
- **Say Metadata**
    - NVDA: Alt+M
    - JAWS: Alt+M
    - Says what the page claims about itself: author, publisher, date and licence. M for Metadata.
- **Say Position**
    - NVDA: Alt+Delete, or Alt+NumPadDelete
    - JAWS: **not yet on JAWS**
    - Says the line, column and percentage position of the cursor. Delete sits among the navigation keys, which is where a position question belongs.
- **Say Time**
    - NVDA: Alt+SemiColon
    - JAWS: **not yet on JAWS**
    - Say current time and date.
- **Say Url**
    - NVDA: Alt+U
    - JAWS: **not yet on JAWS**
    - Say where the link at the cursor would go. U for url.
- **Say Yield**
    - NVDA: Alt+Y
    - JAWS: **not yet on JAWS**
    - Say number of characters, words, and lines in all or selected text.
- **Say Yield Structure**
    - NVDA: Alt+Shift+Y
    - JAWS: **not yet on JAWS**
    - Says how the page is built: how many headings, links, forms and the rest.
- **Yield with Regular Expression**
    - NVDA: Control+Shift+Y
    - JAWS: **not yet on JAWS**
    - Count parts of text matching a regular expression, which answers how many rather than where.

#### Reading aloud

- **Read All**
    - NVDA: Alt+F8
    - JAWS: Alt+F8
    - Say all text, without moving the cursor.
- **Say Chunk**
    - NVDA: Shift+Backspace
    - JAWS: **not yet on JAWS**
    - Say chunk at cursor, or spell if repeated.
- **Say Selected**
    - NVDA: Shift+Space
    - JAWS: **not yet on JAWS**
    - Say selected text, or spell if repeated.
- **Toggle Reading**
    - NVDA: ScrollLock
    - JAWS: **not yet on JAWS**
    - Starts reading continuously, or stops if it is already reading. Scroll Lock because nothing else in Edge, NVDA or Windows wants it.

#### Selecting and the clipboard

- **Append Clipboard**
    - NVDA: Control+Shift+Apostrophe
    - JAWS: Control+Shift+Apostrophe
    - Adds the clipboard to the end of a text file rather than replacing it.
- **Clear Clipboard**
    - NVDA: Alt+Shift+Apostrophe
    - JAWS: Alt+Shift+Apostrophe
    - Empties the clipboard, so an append starts afresh.
- **Complete Selection**
    - NVDA: Shift+F8
    - JAWS: Shift+F8
    - Select text from starting point to cursor.
- **Copy All**
    - NVDA: Control+F8
    - JAWS: Control+F8
    - Copy all text to clipboard.
- **Copy Append**
    - NVDA: Alt+C
    - JAWS: Alt+C
    - Append selected text to clipboard, or append current line if no selection.
- **Copy Line**
    - NVDA: Control+C
    - JAWS: Control+C (named "Copy Selection" there)
    - Copy selected text to clipboard, or copy current line if no selection.
- **Go to Start of Selection**
    - NVDA: Alt+Shift+F8
    - JAWS: **not yet on JAWS**
    - Return to start position of selection.
- **Save Clipboard**
    - NVDA: Control+Apostrophe
    - JAWS: Control+Apostrophe
    - Saves the clipboard to a text file, proposing a name.
- **Say Clipboard**
    - NVDA: Alt+Apostrophe
    - JAWS: Alt+Apostrophe
    - Say clipboard text, or spell if repeated. The apostrophe is a quotation mark, and a clipboard holds a quotation.
- **Select Chunk**
    - NVDA: Control+Space
    - JAWS: **not yet on JAWS**
    - Select contiguous sequence of non-blank characters at cursor, or select the next chunk if a selection already exists.
- **Start Selection**
    - NVDA: F8
    - JAWS: F8
    - Mark starting point of text to be selected, so Shift need not be held while you move.

#### Acting on the page

- **Check Accessibility**
    - NVDA: Alt+NVDA+A
    - JAWS: Alt+JAWSKey+A
    - Tests the page for accessibility problems, asking which engine to use, and offers to report what it finds to whoever publishes the site. A for Accessibility.
- **Check with Axe**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Tests the page with Deque's axe-core engine. Offered by Check Accessibility.
- **Check with Equal Access**
    - NVDA: no key
    - JAWS: Alt+JAWSKey+I (named "Check Accessibility with IBM" there)
    - Tests the page with IBM's Equal Access engine. Offered by Check Accessibility.
- **Consult Copilot**
    - NVDA: Alt+NVDA+C
    - JAWS: **not yet on JAWS**
    - Copies the page text and opens Edge's Copilot sidebar, ready for a question. C for Copilot.
- **Dismiss Dialog**
    - NVDA: Alt+NVDA+D
    - JAWS: Alt+JAWSKey+D
    - Closes a browser dialog that is blocking the window. D for Dismiss, and it works anywhere because a dialog is what has the focus.
- **Extract Main Content**
    - NVDA: Shift+F9
    - JAWS: Shift+F9
    - Extracts the readable part of the page into a page of its own that you can search, save or send. F9 is Edge's own reading view, and Shift+F9 is HomerView's, which works on pages Edge will not.
- **Find Contacts**
    - NVDA: Alt+NVDA+C
    - JAWS: Alt+JAWSKey+C
    - Finds who to tell about this site: email addresses, the accessibility statement, contact pages and social media.
- **Invoke Script**
    - NVDA: Alt+I
    - JAWS: **not yet on JAWS**
    - Carries out instructions written in ordinary words, such as click sign in. I for Invoke.
- **Open Document**
    - NVDA: Control+O
    - JAWS: Control+O
    - Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a page so every command here works on it. Control+O opens in every program; this one opens more.
- **Query Web**
    - NVDA: Alt+Q, or Alt+NVDA+Q
    - JAWS: **not yet on JAWS**
    - Looks something up using free services that need no account: a definition, a place, the weather, a book. Q for Query.
- **Report Accessibility**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Tests the page and writes a report addressed to whoever publishes the site. Reached by Check Accessibility once an engine is chosen.
- **Save Page**
    - NVDA: Control+S, or Alt+Control+S
    - JAWS: Control+S
    - Saves the page in any of nine formats. Control+S saves in every program; this one saves more ways.
- **Submit Form**
    - NVDA: Control+Enter
    - JAWS: **not yet on JAWS**
    - Submits the form you are filling in, from any field in it, so you need not find the button.
- **Web Download**
    - NVDA: Alt+Shift+W
    - JAWS: Alt+Shift+W
    - Pick files to download from a web page, on the key EdSharp uses for it.

#### The window and its tabs

- **Tab Close Others**
    - NVDA: Control+Shift+F4
    - JAWS: **not yet on JAWS**
    - Closes every tab but the one you are reading. Control+F4 closes one tab, so Control+Shift+F4 closes the rest.
- **Tab List**
    - NVDA: F4
    - JAWS: no key, on the Alternate Menu
    - Lists the HomerView tabs and switches to the one you choose. F4 is the Homer window list, and Edge has two other keys for what F4 does there.
- **Tab Names**
    - NVDA: Shift+F4
    - JAWS: Shift+F4
    - Says the names of the open tabs without moving the keyboard anywhere.

#### Adjusting the voice

- **Speech Settings**
    - NVDA: Shift+Accent
    - JAWS: **not yet on JAWS**
    - Reports the punctuation level, the rate and the volume.
- **Toggle Punctuation**
    - NVDA: Alt+Control+Accent
    - JAWS: **not yet on JAWS**
    - Toggle the voice between all and no punctuation.
- **Voice Faster**
    - NVDA: Control+Accent
    - JAWS: **not yet on JAWS**
    - Increase the voice rate. The accent key carries the whole speech family, as it does in EdSharp.
- **Voice Louder**
    - NVDA: Alt+Accent
    - JAWS: **not yet on JAWS**
    - Increase the voice volume.
- **Voice Slower**
    - NVDA: Control+Shift+Accent
    - JAWS: **not yet on JAWS**
    - Decrease the voice rate.
- **Voice Softer**
    - NVDA: Alt+Shift+Accent
    - JAWS: **not yet on JAWS**
    - Decrease the voice volume.

#### Now and then

- **Elevate Version**
    - NVDA: Control+F11, or Alt+NVDA+F11
    - JAWS: **not yet on JAWS**
    - Checks whether a newer HomerView exists and installs it.
- **Recent Pages**
    - NVDA: Alt+R
    - JAWS: **not yet on JAWS**
    - Open a page from the list of those recently used, on the key EdSharp uses for its recent files.
- **Report Connection**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Says whether HomerView is connected to the browser, and how.
- **Self Test**
    - NVDA: no key
    - JAWS: **not yet on JAWS**
    - Checks that all three ways of reaching the browser are working.

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

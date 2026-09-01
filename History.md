---
title: "HomerView History of Changes"
author: "Jamal Mazrui"
---

What changed, newest first, written the way you would tell somebody rather than
as a list of commit messages. The reasoning behind each change is in the code,
where it belongs. This is the short version.

## Alt and Control are left for your desktop shortcuts

Windows lets you put a shortcut key on a desktop icon, and it always has Alt
and Control in it. Every Homer tool takes one of those for opening itself, so
no Homer program should spend one on an ordinary command. If it did, it would
quietly take a key your desktop shortcut wanted, and nothing would tell you:
the wrong program would open, or none would.

So three keys moved:

- **Session Log** is now **Control+Shift+L**, L for Log, beside Alt+Shift+L
  which puts the log on the clipboard.
- **Toggle Punctuation** on NVDA is now **Control+Shift+Accent**, with the two
  volume keys that use the same accent key.
- **Save Page** on NVDA is just **Control+S** now, the same as on JAWS. It had a
  second key that is no longer needed.

Opening HomerView is still **Alt+Control+Shift+H**, and that is the exception
that proves the rule: it is the shortcut key on the desktop icon, so it is
using the space rather than taking it.

## The same keys on JAWS and NVDA, and one fewer key to hold down

HomerView's commands used to need your screen reader's own key as well: Alt,
Insert, and a letter on JAWS, or Alt, NVDA, and a letter on NVDA. That was
three keys for one command, and a different three depending on which screen
reader you use.

The extra key was there for a good reason that no longer applies. Those
commands used to be bound in a place that made them work in every program on
the computer, so they had to keep out of everything's way. They now live with
the browser and do nothing in any other program, so they only need to keep out
of the browser's way.

So they are now **Alt+Shift** and a letter, the same on both screen readers:

- **Alt+Shift+A** checks the page with axe
- **Alt+Shift+E** checks it with IBM Equal Access
- **Alt+Shift+C** finds who to tell about the site
- **Alt+Shift+D** dismisses a dialog covering the page
- **Alt+Shift+L** puts the log on the clipboard
- **Alt+Shift+R** reports diagnostics
- **Alt+F10** opens the Alternate Menu, where every command is

Alt+Shift rather than plain Alt, because a web page can put its own shortcuts
on Alt and a letter. Alt+Shift leaves those alone.

Two commands were renamed so their key would make sense. "Check Accessibility
with IBM" is now "Check with Equal Access", which is IBM's own
name for the engine, so E stands for something. "Diagnostics" is now "Report
Diagnostics", because D was already taken by Dismiss Dialog.

## Every key now belongs to the browser

HomerView no longer changes any of your screen reader's own settings.

On JAWS it used to add keys to the default key map and add a line to the
default script chain. Keys in the default key map work wherever a virtual
cursor is active, which is not only a web browser: an Outlook message, a Word
document and a PDF all have one. Control+O in an Outlook message was opening a
document in HomerView.

Now every key lives in the browser's own key map and script file, so the keys
do not exist in any other program. On NVDA every command does nothing outside
the HomerView browser and the key is passed on to whatever you are using.

**Alt+Control+Shift+H starts HomerView from anywhere.** That is a Windows
shortcut key on the HomerView icon the installer puts on your desktop, so it
works whichever screen reader you use, and whether or not one is running. Press
it and HomerView opens, or comes back to the window you already had.

It has three modifiers because Alt+Control+H is HomerScribe's key. Two
shortcuts claiming one key is not an error: Windows gives it to one of them and
says nothing, so the wrong program opens and nothing explains why. If
Alt+Control+Shift+H does nothing, another program has taken it too, and you can
change the key in the shortcut's properties.

## HomerView works with any Chromium browser

Edge, Chrome, Brave, Vivaldi and others built on Chromium all work, because
HomerView talks to a browser in a language they all speak.

**Choose Browser, on Alt+Shift+B**, lists the browsers on your computer and
lets you pick one. If you are not sure a browser will work, the Test button
starts it, checks, and closes it again, which takes a few seconds and gives a
real answer rather than a guess.

**HomerView Settings, on Alt+Shift+S**, opens the settings file, where the
choice is kept along with every other preference. Each value has a comment
beside it saying what it does.

Changing the browser also moves the JAWS keys into the new browser and takes
them out of the old one. Close the browser window, press Alt+Control+Shift+H, and
restart JAWS.

## Version 1.48.5 — 15 August 2026

### List Names

A new command on **Alt+N**, on both screen readers. It reads the page with a
rule-based English parser and lists the people, places, organisations, dates,
amounts and percentages it finds, saved as `Names.htm` beside the page's other
files. It answers a question headings and links cannot: not how a page is
arranged or where it goes, but who and what it is about. It guesses, and the
report says so.

### Find Contacts became a command of its own

It had been buried inside Report Accessibility on the NVDA side, so a reader who
simply wanted an address had to run a whole accessibility scan to get one. It is
now **Alt+Shift+C** and **Alt+Shift+C**.

### One folder for each page

Everything a page produces now goes to one folder under Downloads named after
the page: the files you download, `Axe.htm` and `Axe.json`, the four `IBM`
files, `Main.htm` and `Names.htm`. Each tool replaces its own files, and the
folder is kept between sessions, so running a check no longer deletes what you
downloaded a minute earlier. Downloads replace by name rather than being
numbered, and no name uses `%20`.

### Removal takes everything with it

JAWS has no add-on manager, so the uninstaller is the only way back and it now
behaves like it. It removes the compiled scripts from every JAWS version, the
key bindings from your `default.jkm`, the `MyExtensions` hook, the NVDA add-on
through NVDA's own mechanism, and the whole of `%LOCALAPPDATA%\HomerView`. It
leaves your Downloads folder alone, because the reports and fetched files are
yours.

JAWS is asked to reload at the end, so the removed keys stop responding
immediately rather than at the next restart. The removal writes its log to
`%TEMP%\HomerViewUninstall.log`, which survives the folder it used to live in.

The uninstaller is in the installation folder and in Windows Apps and Features.

### Explore Page gave back its single letter

In browse mode a bare letter is a navigation key: press it and you expect to
land somewhere. Explore Page had **Y** and does not move anywhere, so it now has
only **Alt+NVDA+E**, which it already had. The four commands that keep a bare
letter — Jump to Main, Jump to Probable Main, Next Same Kind and Prior Same Kind
— all move, which is what the convention is for.

### The page is kept as evidence

Running either accessibility check now also saves the page itself beside the
report: `Page.htm` (the markup after script has run), `Page.png`, `Page.pdf`,
and `Tree.json` (the accessibility tree, with the reasons any node was left out
of it). These used to be things you asked Save Page for one at a time, which was
the wrong shape — by the time a report tells you something is wrong, it is too
late to go back and capture the page as it then was.

Save Page still offers the complete archive Edge itself produces, alongside the
document formats.

### NVDA uses a browseable message where JAWS uses a user buffer

The same commands now have the same character on both: a sentence is spoken, a
short set of facts goes in a box you can copy whole, and anything you want to
move through line by line opens in a window you can search and leave with
Escape.

### Fixes

A page from a previous session was reopening on its own, because HomerView's
browser profile remembered what had been open. It does not restore any more.

Both accessibility reports now answer in a single spoken line, so the report
opened in a tab keeps the focus instead of sitting behind a summary of itself.

## Version 1.48.4 — 14 August 2026

The release that brought the JAWS side level with the NVDA side. HomerView now
has the same commands, answering the same way, on both screen readers.

### The JAWS scripts grew from six commands to forty-one

Reading the page: Jump to Probable Main, Read All, Extract Main Content, Say
Metadata, Link Target. Finding: reverse find, forward and reverse pattern find,
find again both ways, and extract every match of a pattern. Selecting and
copying: the F8 pair, Copy Line, Copy Append, Copy All, Page Links to Clipboard.
The clipboard family on the apostrophe keys. Documents: Open Document, Save
Page, Web Download. Accessibility with both engines. Tabs, dialogs, and
HomerView's own documents.

### Web Download

Files a page links to, fetched with the browser's own cookies, user agent and
referrer, so a file behind a sign-in comes as it would to a click. It names each
file as it fetches it and summarises at the end. This is urlFido's technique,
and it is the most powerful thing HomerView does.

### The accessibility reports became reports

Both engines now write a readable report to your Downloads folder and open it.
The report names the WCAG criterion behind each problem and gives its
conformance level, rather than quoting a rule identifier at you. It leads with
plain language, including the reminder that an automated tool finds roughly a
third of accessibility problems.

IBM's Equal Access engine joined Deque's axe. Its unified ruleset folds EN 301
549 and Section 508 in with WCAG.

### The Alternate Menu became a table

The menu used to decide which command you had chosen by matching words from the
line you picked. "Check Accessibility with IBM" contains "Check Accessibility",
so choosing the IBM command silently ran axe. Each row now holds both the line
you read and the script it runs, and the row number selects it. A row cannot
disagree with itself.

### Fixes worth naming

The IBM checker appeared to hang on large pages. It was fetching the entire
report, tens of thousands of results, and building an XML document from it. It
now reduces the report in the browser and finishes in about two seconds.

Web Download and the accessibility reports were writing to the same folder, and
the report folder is emptied on each run — so running a check after a download
deleted the downloaded files. The report folder is now named separately.

The accessibility engines were being loaded into pages as script elements, which
a content security policy blocks. Every engine now arrives as source through the
debugger, where no policy applies.

Opening HomerView's user guide handed it to whatever Windows thought opened
`.htm`, which on a machine with another default browser meant the guide opened
somewhere no HomerView command worked.

Edge's warning about an unsupported command-line flag is gone.

## Version 1.48.3 — earlier in August 2026

Fixed the JAWS script so that it compiles. Its functions declared a return type
after the parameter list, which is how most languages write it and is not how
JAWS Script does: the type goes before the word Function. Every function in the
file had it the wrong way round.

The installation was copying the scripts into Notifications and VoiceProfiles as
well. Those sit beside the language folder but are not script folders, so the
files went where nothing would ever read them, and both the work and the log
were three times longer than they needed to be. Only folders named with a
three-letter language code are used now.

Worst of the three: the installation reported a successful compile for every
folder while the compiler had rejected the source in all of them. It checked
whether a file had appeared, and one had, because scompile writes a small stub
even when it refuses the source. It now reads what the compiler actually said,
and treats a suspiciously small result as the stub it is.

That is the same fault this project has had several times over: checking that a
step ran rather than that it worked. It is now checked the other way in every
step of the JAWS installation.

## Version 1.48.2 — earlier in August 2026

The JAWS installation now always writes its log where the rest of HomerView
writes its log, so there is one file to send rather than a question about which
one.

## Earlier versions

The releases before 1.48 built the NVDA add-on: the browser connection, the
reading commands, the find family, the clipboard family, main-content
extraction, document conversion, the accessibility check, and Web Download. The
JAWS side began at 1.48 and reached parity at 1.48.4.




## 19 October 2026 -- HomerView speaks the Homer suite's command names

- **Choose Active Browsers,** on the Alternate Menu: tick the other installed browsers HomerView's keys should work in, besides the one it drives, so changing the browser it drives needs no setting up again. The JAWS keys are written into each one; in a window HomerView did not open, a key does what the browser itself does. Kept as activeBrowsers in HomerView.inix, which JAWS users without NVDA can set with Edit Settings, Alt+Shift+E; it takes effect when the JAWS keys are next written, such as by Choose Browser.
- **On JAWS, HomerView's page keys act only in HomerView's own browser,** as they always have on NVDA. A window of the same browser that HomerView did not start -- your everyday Chrome or Edge -- gets the key as though HomerView were not there. The helper checks that the window in front belongs to the browser started with HomerView's own profile; if that check cannot be made, the command goes ahead.
- **Documents open and pages save through the Homer kit's conversion,** as in every Homer app: HomerView carries the kit's conversion.py and its route table in its homer package, where it used to run 2htm.exe or Pandoc itself. A file type the kit cannot convert still opens in the browser, and saving a page as Word goes through the kit too. No console window flashes while a tool runs.
- **Control+Shift+F1 opens the hotkeys,** every command with its keys, the suite's key for every app's Hotkeys, in NVDA and JAWS alike. The developer notes are on the Alternate Menu.
- **The build needs HomerDev 1.88.6 or later.**
- **Edit Settings, on Alt+Shift+E on both screen readers,** opens the settings file, as Edit Settings does in every Homer app; it was HomerView Settings, on Alt+Shift+S. Check with Equal Access, which had Alt+Shift+E on JAWS only, is offered by Check Accessibility, as it already was on NVDA.
- **The suite's names:**
  - Quick Start is ReadMe;
  - Hotkey Document is Hotkeys;
  - Log to Clipboard is Copy Log;
  - Forward and Reverse Find Again are Search Next and Search Previous;
  - Say Url is Say url;
  - the Prior commands (Sentence, Paragraph, Same Kind, Different Kind) are Previous.
  
  The keys are unchanged.
- **The NVDA and JAWS lists still agree.** checkParity knows the new names, so it reports the same four genuine gaps as before.
- **Every place that binds or lists a key says the same.** The JAWS key map, chainJawsScripts' bindings for each browser, the JAWS Hotkey Summary and Alternate Menu, and the NVDA add-on's own lists all give Edit Settings Alt+Shift+E. The JAWS quality check, which compares them, caught the first attempt missing two of these.

## 18 October 2026 -- HomerView recognizes its own browser by process, never by name

- **One identity rule, in one place.** A new module, identity.py, decides whose window a key or a page belongs to, and both places that decided before now ask it. A window is HomerView's only when its process is one of the processes of the browser HomerView launched or attached to.
- **HomerView's Chrome is recognized.** The page test used to refuse anything not named msedge before it looked at the process, so a page in HomerView's Chrome, Brave or Vivaldi never got HomerView's commands.
- **An ordinary window of the same browser is left alone.** With no browser process known, the key test used to fall back to the browser's program name, which claimed every ordinary Edge or Chrome window. Now, until HomerView's browser is running, every key keeps its normal browser and screen reader meaning.
- **Tested on every build.** scripts\testIdentity.py checks 18 cases, including Chrome and Chromium sharing a program name and requests made stale by a changed tab or page, and the build stops if one fails.
- **The Start menu's shortcuts to the guide, the history and the developer notes now open them.** They pointed at the top of the program folder, while the installer puts those pages in its help folder, so each shortcut led nowhere. The check before push found it and stopped the push, as it should.
- Part of the Homer Suite integration (stage 1, the browser-identity proof).

## 14 October 2026 -- Consult Copilot on JAWS

- **Consult Copilot is on the JAWS menu.** As on NVDA, it puts the page's title, address and main text on the clipboard, ready to paste, then presses Edge's own key for Copilot, Control+Shift+Period, through HomerView's helper; you hear how many characters are on the clipboard.
- **Say Url is counted as Link Target on JAWS,** where the two were joined on purpose: one key that always gives a link's address and adds what is there when it can be fetched. The parity check now finds 4 NVDA commands without a JAWS counterpart -- Explore Page, Invoke Script, Query Web and Self Test -- each needing a dialog of its own.

## 14 October 2026 -- Tab Close Others, on JAWS too, and never on a guess

- **Tab Close Others is on the JAWS menu.** It closes every tab but the one you are on, as on NVDA, through a new command of HomerView's helper. The parity check now finds 6 NVDA commands without a JAWS counterpart, down from 7.
- **No tab is closed on a guess, on either screen reader.** When no tab reported itself as the current one, NVDA kept the oldest and closed the rest, so the tab being read could be closed. Now, on NVDA and JAWS alike, tabs are closed only when exactly one tab is current; otherwise none is, and you hear why. Tested on NVDA's own code with one current tab, none, two, and a single tab (from an audit by another AI).
## 14 October 2026 -- the results file says what the box said

- **HomerView_setup_results.txt now holds the whole summary,** the JAWS and NVDA outcomes included, and the setup log ends with it. The outcomes were shown in the box but never written back, so the file, read later, said only where HomerView was installed (from an audit by another AI).

## 14 October 2026 -- Yield Structure

- **Say Yield Structure is now Yield Structure, on NVDA and JAWS.** The quality check found Say Yield inside Say Yield Structure, and a name inside another is confusing to hear, so the 13 October build stopped. The new name sits with Yield with Pattern and keeps its key, Alt+Shift+Y.

## 14 October 2026 -- Link Target reads a page's details whatever their order, and stops at its redirect limit

- **An author written the other way round is still found.** Link Target read a page's title, description, author and date with patterns that expected the name of a detail before its value, so the equally valid reverse order gave nothing. A page's head is now read by an HTML parser: attributes in any order, any case, quoted or not, across lines, with entities decoded. Tested on thirteen cases, the audit's own among them (from an audit by another AI).
- **Following a link stops after eight redirects, as was intended.** The limit of eight was written down and never applied, so Python's own limit of ten held, with a message about an infinite loop. The ninth redirect now stops it, and the message names the last address reached. Tested against a local server with chains of eight and nine redirects (from an audit by another AI).
- **The handover notes name the kit's classes where they are,** in C:\HomerDev\exec\CSharp.
- **Link Target says when it read only part of a page.** It reads the first 96 KB of a page, counted the words there, and gave a reading time as though for the whole page, so a long article looked short. When the page goes on past what was read, the count is now given as at least so many words, with the limit named; and when the part read holds too little to judge, it says the length is not known. Menus, headers, footers and side panels are no longer counted as words, so a long menu cannot pass for an article, even one the part read ends inside. Tested against a local server with a page whose article begins after a menu longer than 96 KB, a long article after a short menu, and an ordinary short page (from an audit by another AI).

## 14 October 2026 -- five NVDA commands come to JAWS

- **Say Address, Say Yield, Say Yield Structure, Submit Form and Report Connection are now on the JAWS menu.** They were on NVDA only. Each says what NVDA says: Say Yield counts characters, words and lines by NVDA's own rules, giving the same numbers on every text tested, and Submit Form runs NVDA's own page script, so the page's own checks run and the browser shows what is missing. Say Address shows the address in the viewer when pressed again, as every short answer on JAWS does. They are on the menu without keys of their own, so none takes a key JAWS already gives you.
- **The parity check counts the JAWS menu itself.** NVDA's Alternate Menu opens HomerView's menu, which on JAWS is Alt+F10; the menu cannot list itself, so it was counted as missing. It now counts while the menu's script exists. NVDA's second address command, for outside the page, is covered by Say Address, which on JAWS works anywhere.
- **Fourteen gaps are now seven:** Consult Copilot, Explore Page, Invoke Script, Query Web, Say Url, Self Test and Tab Close Others. Each needs more than a script in the page, such as a new helper command or a dialog of its own.
## 14 October 2026 -- an expected result no longer logged as an error

- **The build's start-up probe is logged as what it is.** The build checks that HomerView.exe starts and answers; with no browser running during a build it cannot connect, as expected, but the note said "an error about connecting is expected", and the log takes its level from the words, so every build logged an ERROR. The note now says the same thing without the word (from an audit by another AI).

## 11 October 2026 -- the session log's name, built so the compiler accepts it

- **The JAWS scripts compile again.** The line that named each session's log joined a COM call's result into one long expression, and the JAWS compiler rejected it ("Expected gsLogPath to be a variable"), stopping the build. The name is now built one part per statement.

## 11 October 2026 -- a log for every session, where Homer logs go

- **The JAWS side now starts one log per session**, HomerView-yyyyMMdd-HHmmss.log in %LOCALAPPDATA%\\HomerView\\logs, the Homer pattern. Every JAWS session appended to the one HomerViewJAWS file the installer named when the scripts were installed, so a day's commands sat at the end of a file dated weeks before, and no log appeared for the day. The bridge joins the newest session log; Control+Shift+L and Alt+F1 show the current one; the installer's own log is now HomerView-jawsScripts-yyyyMMdd-HHmmss.log, and the setup summary and the chained install read that name.
- **The NVDA side's log is named in the pattern too**, HomerView-yyyyMMdd-HHmmss.log, with the hyphen it lacked, and the empty HomerView.log its write test left behind is removed.

## 11 October 2026 -- from an audit and a report

- **The hotkeys page has one top heading.** scripts\\makeDocs.py wrote help\\hotkeys.md with its title in front matter and every section at level one, so the page had seventeen top headings, and the kit's check refused the 1.48.95 release for it. The sections are now level two under the title, in the generator and in the page.

## 9 October 2026 -- from the build and release logs

- **The installer's screen reader boxes are the kit's.** HomerView kept its own copy of the kit's screen reader wrappers and state function. They are gone: HomerComponents.iss words and ticks the JAWS and NVDA boxes by asking installJawsScripts.cmd the kit's question, "state jaws <file>", which that script now answers, so HomerView keeps its own installation, with its chaining, while the verbs and ticks are the kit's.

- **The installer compiles again.** Three comment lines added on 8 October began with a semicolon inside the [Code] section, where Inno does not take a semicolon as a comment, and the compile stopped with "BEGIN expected" at line 567. They are // comments now, and the kit's check fails any [Code] line that begins with a semicolon.
- **Ten walks of about three minutes.** Walks 2 to 8 were lengthened on 8 October, with keys that are the same on both screen readers and the differences where a key is the screen reader's own, but those files never reached the project; they come now.

## Unreleased -- 9 October 2026

- **The kit's own Python modules inside the add-on.** The add-on's homer package held hand-kept copies of five kit modules -- inix, lbc, say, util and web -- and they had drifted: they lacked the kit's 1.62.5 fixes, among them relative links made absolute, file names that avoid Windows device names, Control+Enter accepting a dialog through its default button, and a dialog that stays open, saying why, when its handler fails. The kit's modules now work flat or in a package, so the build copies them in exactly, every time, and logs each. The kit's say module already speaks through NVDA itself when running inside it, as the copy did. HomerView needs HomerDev 1.65.3.
- **Conversion through programs never approved, removed.** convert.py held a table of converters, and functions to find and run two outside conversion programs, that nothing called; they are gone, and two messages no longer advise installing one of them.

## 8 October 2026 -- an audit by another AI

ChatGPT audited HomerView and reported 51 findings. Checked against the code, these held and are fixed:

- **NVDA commands that could not run.** Nine names were used where they were never defined: the command table and the browser list in the plugin, lbc and find in three pattern and search commands, the page title in Extract Main Content, and the file's address and extension in a download. Each raised an error when its command ran. The worst was the first: the command table could not be read, so HomerView's browser-only keys were not limited to the browser. A static check of all 62 Python files now finds none.
- **Your sign-in stays with its site.** NVDA: a download's cookies went with it through any redirect, to whatever host it named; they are now dropped when a redirect leaves the page's host (tested with two local servers). JAWS: the page's cookies were sent with every link, to any site; they now go only to the page's own host.
- **A failed download leaves no half a file.** It is written to a .part file and named only when complete.
- **A failed conversion is not taken for a success.** It needs a zero exit code and a file written by this attempt; a document converted before had "succeeded" by finding the old file.
- **JAWS: the cookie reader worked.** Replies were accepted only for request number 1, so its requests 2 and 3 waited out their whole time and failed.
- **Undoing the JAWS scripts keeps your own changes.** An edited file was restored from the backup taken before the install, losing every later change to it; now only HomerView's own lines come out.
- **NVDA's Add-on Help opens.** The manifest named readme.html, which the build no longer makes; it names README.htm.
- **The build names its reason.** A build stopped with only "Engine exit code 1": Pandoc's warnings, on its error stream, stopped the build at once. Warnings are now logged and never stop it; the newest Pandoc found is used, not the first on the PATH; and any error that stops the build is written to the log with its line.
- **Old build entry points retired.** buildAll, buildBridge and buildHomerViewBridge built files that no longer exist; build.cmd removes them, and logs each.
- **Kit tools** updated from HomerDev 1.63.3: push stops on a stale whitelist and reports a failed commit as one.

Left for later, as larger changes: JAWS cookies through a cross-host redirect, unique download folders per page, asynchronous JAWS jobs with their own files, revalidating an action's target before clicking, and the WebSocket frame and message-size checks.

## 8 October 2026 -- tutorials in the pattern of ten

HomerView has spoken tutorials for the first time: ten walks in the Homer pattern of ten. 0 Overview; 1 User Interface, the window, the command list, the hotkey summary, the key rules and help; 2 Install and Launch; seven tasks, 3 Read an Article Properly, 4 Decide Whether to Follow a Link, 5 Find Things, 6 Select and Copy a Passage, 7 Gather Files from a Page, 8 Check Accessibility; and 9 Conclusion. build.ps1 now copies the kit's tutorial tools in and speaks the walks before compiling the installer, the installer ships the tutorials and their audio, and RepoFiles.txt names them for the repository.
---
title: "HomerView History of Changes"
author: "Jamal Mazrui"
---

What changed, newest first, written the way you would tell somebody rather than
as a list of commit messages. The reasoning behind each change is in the code,
where it belongs. This is the short version.

## Toggle Punctuation has its own key

Toggle Punctuation is now **NVDA+GraveAccent**. It had been given
Control+Shift+GraveAccent, which is Voice Slower's key, and in a page only one
of two commands on the same key can work -- so punctuation had no key at all.

The grave accent key now follows the same pattern in every Homer program with
speech commands, the one EdSharp started: Alt for volume, Control for rate,
Shift to go the other way, and the screen reader key for punctuation. EdSharp's
punctuation key is JAWS+GraveAccent; HomerView's is NVDA+GraveAccent.

## The user guide names the right keys

Four commands in the user guide were listed with keys that had changed:

- **Consult Copilot** is Alt+NVDA+C on NVDA.
- **Log to Clipboard** is Alt+Shift+L on NVDA.
- **Save Page** is Control+S on NVDA, with no second key.
- **Toggle Punctuation** is Control+Shift+Accent on NVDA.

**Page Folder**, on Alt+Shift+F, was missing from the guide altogether. It
opens the folder where HomerView keeps what you saved from a page.

The build now checks every key the guide gives against the keys HomerView
actually uses, and refuses to finish if they disagree. A guide that names
the wrong key is a program that does not do what it says.

## Pandoc is shared with your other Homer apps

Pandoc is the tool HomerView uses to open ebooks, Markdown and OpenDocument
text. HomerView used to keep its own copy inside its own folder. Now it uses
the one copy that every Homer app shares, in Program Files\Pandoc, and
installs it there if it is missing.

That matters because an app's own folder is replaced when the app is
updated, and a tool kept there could be lost. A shared tool is not.

The last page of the installer now says exactly what it will do with pandoc:

- **Install pandoc**, ticked, when it is not on your computer.
- **Update pandoc**, ticked, when a newer version is out.
- **Reinstall pandoc**, not ticked, when you already have the latest.

So pressing Enter on that page installs what is missing and updates what is
old, and does nothing to what is already current.

The same page no longer offers the NVDA add-on on a computer that does not
have NVDA. It used to, already ticked, and then a message warned that it
would not work. Now each screen reader is offered only where it is installed.
If you add NVDA later, the Start menu has an item that installs the add-on.

Uninstalling HomerView now keeps two things that are yours: your list of
recent pages, and the sign-ins you made in HomerView's browser window. It
used to delete them along with everything else. It still removes what
HomerView made for its own use: its logs, the files it downloaded, the
documents it converted, and the browser's temporary files.

## HomerView clears up after itself

HomerView's own folder had grown to 861 MB in 9,349 files. Almost all of it
was the browser's caches, which grow without limit, plus documents HomerView
had converted for people to read weeks earlier.

Now, each time HomerView starts, it clears what should not have survived:

- Converted documents older than **7 days**. Change that with `temporaryDays`
  in the settings file.
- A browser cache that has passed 200 MB, and only while the browser is
  closed. Bookmarks, settings and sign-ins are never touched.

It clears at the start rather than at the end. A program that tidies up as it
closes only tidies up when it closed properly, which is the time there was
nothing to tidy. The leftovers come from the runs that ended badly.

If a converted document is cleared, its entry in your recent pages list goes
with it, so the list never offers a page that is not there.

The user guide lists everything in that folder and says why each thing stays.

## Control+F searches what your screen reader shows you

In a browser window, Control+F normally opens the browser's own find bar. That
bar searches the page the browser draws. Your screen reader builds a different
view of the same page, made to be read and moved around, and that is the view
you are actually in. Searching one and reading the other is a poor deal.

In HomerView's browser, Control+F now runs your screen reader's own find. On
JAWS that is the same find you get from Control+JAWS+F anywhere else, on the
same key the rest of the world uses.

This also fixes a fault where HomerView's keys in Edge answered "cannot find
that script". HomerView's script file named the wrong file as the one to build
on, and ended up naming itself, so none of its own commands could be found.

## More of HomerView works in an ordinary Edge window

HomerView does two kinds of work. Some commands ask the page a question, and
those need a browser HomerView started itself, with Alt+Control+Shift+H. The
rest do not, and those should work wherever you are.

Several groups of commands moved to the second kind:

- **Open Document, on Control+O.** This converts a Word file, a PDF, an EPUB
  and the rest into a web page you can read with headings and tables. None of
  that ever needed HomerView's browser: the conversion happens on your
  computer, and the result now opens in whatever browser you use. Same result,
  fewer things that can go wrong.
- **The documentation.** The user guide, the history, the developer notes, the
  quick start, the announcement and the session log now open in your usual
  browser when HomerView's own is not running.
- **Copy All and Read All** fall back to your screen reader's own view of the
  page. That view can miss content in a frame, or added late, so each says
  which view it used.
- **Page Links to Clipboard** falls back to the JAWS view of the page. It can
  miss a link that is hidden or added late, so the heading says where the list
  came from.
- **Jump to Probable Main** moves to the page's main element, if it has one.
  Most well built pages do. A page that marks its main content another way, or
  not at all, still needs HomerView's browser.

When a command really does need HomerView's browser, it now says one sentence
and names the key: "This needs the HomerView browser. Press
Alt+Control+Shift+H." That replaced fourteen different wordings, most of them
"HomerView is not connected", which told you something was wrong and left you
to work out what to do.

The selection commands on F8 never needed HomerView's browser and still do
not. Start Selection, Complete Selection, Copy Selection and Go to Start of
Selection all work from what your screen reader already has.

The user guide lists all three groups: the commands that work in full, the ones
with a lesser route, and the ones that need HomerView's browser.

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

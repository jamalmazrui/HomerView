---
title: HomerView for Developers
author: Jamal Mazrui
---

# What this is

HomerView is an NVDA global plugin that launches its own copy of Microsoft Edge
with the Chrome DevTools Protocol enabled, and then uses three separate views of
the same page. Most of what it does that is hard to do elsewhere comes from
having all three at once.

The browser's own window, reached through NVDA's object model and the Windows
API. That is where the address bar, the tab strip and the toolbars live, none of
which exist in the page.

The page as NVDA built it, through the browse mode tree interceptor. That is the
reading order the user navigates, with its landmarks, headings and text ranges.

The page as the browser sees it, through the protocol, in both directions:
queries that ask, and commands that act. The self test exercises all three and
reports each separately, because a protocol connection can answer every query
while having lost the ability to act.

# The rules the code follows

No network call runs on NVDA's main thread. Everything that touches the browser
is queued to a single worker, and results return through wx.CallAfter. A vague
report of sluggishness becomes a specific line, because every task records the
thread it ran on and warns if it is the wrong one.

The test for "is this object inside HomerView's browser" performs no input or
output, because it runs for every object NVDA creates. It is an integer set
membership check against the browser's process identifiers.

A dialog opened from inside a script waits for the script to return first.
Otherwise NVDA has not processed the focus change, announces nothing, and keeps
sending arrow keys to the page underneath.

No command takes a key NVDA uses by default, on either the desktop or the
laptop layout.

# Where the code lives

    addon/globalPlugins/homerView/
        __init__.py       the global plugin: commands that work anywhere
        pageBuffer.py     the browse mode class and every page command
        service.py        the worker thread, connection state, process identity
        cdp.py            the protocol session, reader thread, event dispatch
        webSocket.py      a loopback-only RFC 6455 client, standard library only
        edge.py           finding and launching the browser
        homer/            the shared toolkit: inix, lbc, say, web

The rest are one file per capability: axe, ace, act, capture, contacts,
convert, copilot, documents, download, exportReport, find, history, mainContent,
metadata, output, pageExplorer, report, saveAs, selfTest, settings, wcag.

# The shared Homer toolkit

The homer package holds what is not about HomerView: order-preserving inix
files, Layout by Code dialogs, a single way to announce text, and dependency
free HTTP that behaves like a browser. Three rules make it shareable.

No module imports NVDA at the top level, so every one is importable and testable
in a plain interpreter and the same code serves a program that is not an add-on.
Nothing depends on anything beyond the standard library except wx, which NVDA is
built on. No module knows about HomerView.

To reuse it, copy the folder into your add-on and import relatively. NVDA has no
dependency manager for add-ons: a library add-on on sys.path works until load
order changes or somebody removes it, and the add-on store cannot declare or
protect that dependency. Copying costs a re-copy when a fix lands; sharing costs
silent breakage in someone else's add-on.

# Building and releasing

    buildAll.cmd     builds the add-on, then compiles the installer
    tagRelease       tags the version and publishes the release

buildAll must run first. tagRelease reads the version from the built installer's
version resource and expects to find HomerView_setup.exe in the repository root.

The add-on package has a stable name, HomerView.nvda-addon, so the setup script
never needs editing for a version. A copy named for the version is written
beside it for release assets. The version itself lives in the add-on's
manifest.ini, which is what NVDA reads, and in AppVersion in the setup script.

Every build script writes a log beside itself.

# Conventions

Camel Type: lowerCamelCase for names, Hungarian prefixes on typed variables,
functions rather than subprocedures, constants named like variables.

Files a Windows program reads are UTF-8 with a byte order mark and Windows line
endings. Generated web pages use the .htm extension.

Keys are written in the order Alt, Control, Shift, with the letter last and
upper case regardless of Shift.

# What is deliberately not here

No language model. The page explorer is rule-based, the act command matches
rather than infers, and no page content leaves the machine. A local model
service is detected and logged if one is running, and nothing uses it.

No bundled converters. LibreOffice, pandoc, Calibre and 2htm are found rather
than shipped, because an add-on folder is replaced wholesale on every update and
sits in a roaming profile that some managed environments will not execute from.

# Where files belong on Windows

This is settled here once, because four programs in this family face the same
question and answering it differently in each would be a nuisance to everyone.

Windows offers five places, and the choice follows from what a file is rather
than from what is convenient.

**The program folder**, `C:\Program Files\<Product>`, reached in an installer
script as `{autopf}`. Written once by the installer, which has administrator
rights, and read for ever after. Nothing a program writes at run time belongs
here. Windows once quietly redirected such writes to a per-user store, which
hid them from the user and from the program's own uninstaller, and that
redirection has been discouraged for years. Granting the Users group write
access to escape the problem trades a real security boundary for a convenience,
and it also means two people sharing a computer share one file.

**Local application data**, `%LOCALAPPDATA%`, which is
`C:\Users\<name>\AppData\Local\<Product>`. Per user and per machine, and not
copied anywhere. This is where a log, a database, a cache, a downloaded tool or
a browser profile belongs. Anything that grows, anything specific to this
computer, anything that would be meaningless on another one.

**Roaming application data**, `%APPDATA%`, which is
`C:\Users\<name>\AppData\Roaming\<Product>`. Per user, and in a domain it
follows the person to whatever computer they sign in to. This is for
preferences, and only for preferences. The whole folder is copied at sign in
and sign out, so a log or a database placed here makes every sign in slower for
no benefit to anyone.

**Machine-wide data**, `C:\ProgramData\<Product>`. Shared by every user of the
computer. Worth using only when data genuinely is shared, and it needs thought
about permissions, because a folder every user can write is a folder any user
can tamper with.

**The user's own folders**, Documents and Downloads. Only for files the user
asked for and will manage themselves. A saved report or a downloaded file, yes.
A log, never: the user did not ask for it and should not have to tidy it.

**The temporary folder**, `%TEMP%`. Generated working files that Windows may
clear whenever it likes. Reports and converted documents live here, because
they are a way of reading something rather than a document in their own right.

## Where HomerView puts each thing

- Program files, documentation and the converters: the installation folder.
- The session log and the history database: local application data.
- Preferences and recently typed values: roaming application data.
- The browser profile: local application data, because it is large and
  machine-specific.
- Generated reports and converted documents: the temporary folder.
- Downloads and files saved on request: the user's downloads folder.

## The same rule applied to the other tools

2htm converts a document and writes the result where the user asked. It needs no
per-user folder at all beyond a log, which belongs in local application data.

DbDo and urlFido keep settings, which belong in roaming application data as
`%APPDATA%\<Product>\<Product>.inix`, and write logs and any cached data to
local application data. Neither should write to its own installation folder,
and neither installer should loosen permissions on it.

A shared `%APPDATA%\Homer` folder for settings common to the family would be
defensible, but only for settings genuinely shared. A setting that belongs to
one program should stay with that program, so that removing it removes its
settings too.

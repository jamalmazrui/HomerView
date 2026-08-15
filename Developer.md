---
title: HomerView for Developers
subtitle: How to build it, and how it is put together
author: Jamal Mazrui
---

# What you need

- **Python 3**, to run the build scripts.
- **Inno Setup 6**, to compile the installer, from
  [jrsoftware.org](https://jrsoftware.org/isdl.php).
- **Git**, if you plan to publish.
- **NVDA 2025.1 or newer**, to test what you build.

The source lives in C:\HomerView. Nothing else has to be installed; the
converters HomerView uses at run time are found rather than bundled.

# Building it

    buildHomerView.cmd

That is the whole of it. Four steps run in order:

1. **The setup script is checked**, before anything is compiled. Inno Setup
   reports a line number and four words when it rejects a script, which is
   enough to find the line and not enough to explain it. These checks catch the
   common faults and say what is wrong.
2. **The bridge is compiled** into HomerViewBridge.exe, with csc.exe from the
   .NET Framework. That is the piece the JAWS scripts use, because JAWS
   scripting cannot open a WebSocket. The NVDA add-on does not need it.
3. **The add-on is packaged** into build\HomerView.nvda-addon.
4. **The installer is compiled** into HomerView_setup.exe.

Two things are verified afterwards. The version in addon\manifest.ini must
match the one in HomerView_setup.iss, because a release where those disagree is
one nobody notices until a user reports the wrong number. And every Python file
on disk must be inside the built add-on, because a module left out builds
cleanly and fails on the user's machine at the moment they press the key.

One log is written, beside the script, and it covers the whole build. There
used to be two, because packaging the add-on was a separate program, and the
reason for a failure could be in whichever of them nobody had been asked for.
Nothing about zipping a folder needed its own script.

# The JAWS side

HomerView supports both screen readers from one installer. The last page offers
the NVDA add-on and, separately, the JAWS scripts. Each checkbox appears only
when that screen reader is actually installed, because offering to install
scripts for a screen reader somebody does not have is a question with one
sensible answer.

The JAWS scripts are installed by installJawsScripts.ps1 rather than by the
installer's file section, because they have to be **compiled in place**. A .jsb
built by one year's compiler is not reliably loaded by another year's JAWS, so
the script finds every JAWS version on the machine and compiles the source with
that version's own scompile.exe.

It runs as the ordinary user, never elevated. JAWS keeps its settings under the
user's roaming application data, and an elevated run would write to the
administrator's profile instead, where the user would never see it.

One line goes into default.jkm, for the launch key, because launching cannot
live in the Edge key map: before HomerView runs there is no Edge window. That
file is merged rather than replaced, and the original is kept beside it as
default.jkm.beforeHomerView. A user's default key map may hold years of their
own work.

Uninstalling takes all of it back out.

# Publishing a release

    buildHomerView.cmd
    git add -A
    git commit -m "HomerView 1.2.3"
    git push
    tagRelease

tagRelease reads the version from HomerView_setup.exe and expects that file in
the project root, which is where the setup script puts it.

The add-on always has the same name, HomerView.nvda-addon, so the setup script
never needs editing when the version changes. Only two files carry the version:
addon\manifest.ini and HomerView_setup.iss.

# Tidying up

    cleanDir.cmd

Moves everything the project does not need out of the folder and into
C:\temp\HomerView_misc. It moves rather than deletes, so anything taken by
mistake can be moved back. Pass -bWhatIf to see what would move first.

    python tidyRepo.py

Surveys the repository: files tracked that should not be, large files anywhere
in the history, and source files missing from it. It prints the whole plan and
changes nothing unless you add --do-it.

# How the code is arranged

The add-on is a global plugin in addon\globalPlugins\homerView. About forty
modules, each with one job.

The ones worth knowing first:

- **commands.py** is the table of every command: its name, its key and what it
  does. The gesture bindings, the Alternate Menu, the hotkey summary and the
  documentation all read from it, so none of them can drift from the others.
- **cdp.py** speaks to the browser over the Chrome DevTools Protocol.
- **edge.py** launches and finds the browser.
- **service.py** is the worker thread. Everything that touches the browser is
  queued to it, and results come back to NVDA's main thread.
- **pageBuffer.py** is the browse mode buffer that carries the page commands.
- **homer/** is the shared toolkit, ported from the C# version used by the
  other Homer Tools.

# Rules the code follows

**No network call on NVDA's main thread.** That thread is the one NVDA speaks
from, so a slow server would hold speech for as long as the request took.
Everything goes to the worker.

**A dialog opened inside a command must wait for the command to return.**
Otherwise NVDA never processes the focus change, announces nothing, and keeps
sending arrow keys to the page underneath. That is what lbc.afterScript is for.

**The test that runs for every object NVDA creates does no input or output.**
It runs thousands of times per page, and it is an integer set lookup.

**The browser must use its own profile.** Since Chrome and Edge 136, the remote
debugging switches are ignored on the default profile, so there would be no
connection at all.

**Files go where Windows says they go.** The program folder is written once by
the installer and read after that. Logs, the history and the browser profile go
in local application data. Settings go in roaming application data. Generated
pages go in the temporary folder.

# Things worth checking after an edit

Two faults have recurred often enough to be worth a habit.

**A name used but never defined.** Several times an automated edit removed
something still in use, and it shipped. A scan of every module for names loaded
but never bound catches it in a second.

**A method that promises a value and never returns one.** A method named build
or get that falls off the end returns nothing, and the caller fails on the next
line. That one broke the Alternate Menu for two releases.

Use the parser rather than string matching for structural edits. Replacing text
between two markers has twice destroyed a file, once inflating it from 55 KB to
115 MB, because the markers were in the wrong order and the match came back
empty.

# Licence

GNU General Public License version 2, the same licence NVDA uses.

# HomerView handover

For picking up development in a new conversation. This is a developer document,
so it says things plainly rather than simply.

## Where things stand

HomerView works with JAWS and NVDA. The two are meant to do the same things,
and `checkParity.cmd` measures how far that is true rather than asserting it:
**80 of 94 commands covered, 14 gaps.** Run it after adding a command to either
side.

The JAWS side has just been through a significant change, described next.

## The change that matters most: no default scripts at all

HomerView's keys used to live in `default.jkm`'s `[Virtual Keys]`, reached
through `MyExtensions`, with a user `default.jss` sometimes rewritten so the
chain would get there. JAWS applies `[Virtual Keys]` **wherever a virtual
cursor is active**, which is not only a browser: an Outlook message, a Word
document and a PDF all get one. Control+O in Outlook was running HomerView's
Open Document.

**Nothing outside the browser is touched now.** `chainJawsScripts.ps1` writes
two files per settings folder and no others:

- `<browser>.jss`, which `Use`s the factory browser binary first when JAWS
  ships one, then `HomerView.jsb`. The documentation calls this **layering**:
  anything not overridden is inherited.
- `<browser>.jkm`, with the 9 keys that must work in the address bar and in
  forms mode in `[Common Keys]` and the 39 page keys in `[Virtual Keys]`.
  Both sections are inside the browser's own file, so both are scoped to it.

No user `default.jss`, no user `default.jkm`, no `MyExtensions`.
`chainThroughUserDefault` is a documented no-op; `reportUserDefault` still
runs, because reading is not changing. Every run reads the user `default.jkm`
and says either that it names nothing of HomerView's or how many lines an
older release left there — the claim is checked, not asserted.

**The one key that cannot be scoped** is starting the browser when it is not
running. That is a Windows shortcut key, `Alt+Control+Shift+H`, on a desktop
shortcut the installer creates with `HotKey: "ctrl+alt+shift+h"`. It runs
`HomerView.exe launch`, which reconnects and raises the window, asks for a
window if the process is alive without one, or starts the browser. No screen
reader is involved, which is why one shortcut serves JAWS and NVDA alike.

Windows only honours a shortcut key on a `.lnk` on the desktop or in the Start
menu, so that shortcut is not optional, and the Start menu entries carry no
`HotKey` — the same key on two shortcuts is a conflict, not a fallback. If
Alt+Control+Shift+H is silent, something else has registered it as a global hotkey
and wins.

`HomerView.exe` is now built `/target:winexe` so the shortcut does not flash a
console. Nothing is lost: every answer is written to a file. PowerShell does
not wait for a windows program, so the build's smoke test uses
`Start-Process -Wait`.

## Any Chromium browser

Which browser comes from `HomerView.inix` under `%APPDATA%`, as `browser` and
`browserPath` in `[Preferences]`, or from `-sBrowserExe`. Edge when nothing is
chosen, which is what every earlier installation used.

Browsers are found by asking Windows three ways: App Paths under both hives,
the **enumerable** `StartMenuInternet` key, and the usual folders. The real
test is not a name: `canBeDriven` starts a candidate on a throwaway profile
and watches for a `DevToolsActivePort` file, which answers the question for
that machine rather than in general.

Changing the browser rewrites the JAWS key maps, because JAWS names a script
set after the executable. The manifest records `browser|<name>`, and a
different one is cleared before the new one is written — two browsers each
claiming Control+O is worse than either.

**The browser table is written twice**, in `browsers.py` for NVDA and in
`HomerView.cs` for JAWS, because the JAWS side has no Python and the add-on
must not depend on the program being installed beside it. Check 17 compares
them, which is the standing rule: where two languages agree by convention
rather than by compilation, write the check.

## NVDA: no global keys either

Every global command is browser scoped, and the set is **derived from the
command table** rather than typed out, because a hand list drifts and a
command added to one and not the other is a key that fires in Word.

Scoping rather than not binding at all, deliberately. NVDA offers two ways:
bind on the browse mode class, or bind globally and refuse the key elsewhere.
The first is wrong here — browse mode bindings do not fire in forms mode or
the address bar, and these are exactly the commands that must. Refusing
instead gives the scope wanted in every cursor mode, and NVDA passes the key
on, which is what the JAWS side gets from an application key map.

NVDA does not need to have started the browser. `attach()` finds it through
the port file and a local socket, and `refreshProcessIds()` gets the identity
from the protocol. `_attachToBrowserStartedElsewhere` notices on a focus
change, gated behind four cheap tests and the port file's modified time, and
deliberately not in the identity test, which runs for every object NVDA
creates and must stay an integer set lookup.

## What is not finished

- **14 parity gaps.** Run `checkParity.cmd` for the current list. The exemption
  list inside `checkParity.py` decides which NVDA commands do not count as gaps
  because JAWS provides them itself; it is meant to be argued with.
- **Alt+Apostrophe after the Log command** said nothing on a tester's machine
  and the cause was never found. `hVSayClipboard` now logs the answer's length
  and first 120 characters when the value comes back empty, so one run will say
  whether the answer never arrived or arrived and did not survive parsing.
- **Four document copies** — `Developer.htm`, `History.htm`, `HomerView.htm`,
  `README.htm` — are written into `%LOCALAPPDATA%\HomerView` by the NVDA side's
  `copyDocuments`. They duplicate the installed copies and appear to serve no
  purpose. Worth removing, on its own rather than beside another change.
- **A known asymmetry, now narrower.** On JAWS the page-context guard asks "is
  this a browser"; on NVDA it asks "is this HomerView's own browser", by
  process. The NVDA test is stricter and probably right. With the keys scoped
  to the browser on both sides the guard rarely fires at all, so this matters
  less than it did, but it is still an asymmetry.

## How to work on it

Run `buildHomerView.cmd`. It writes a detailed log and **exit 0 means ready**
for `git add -A`, commit, push, `tagRelease`. Its five steps compile the JAWS
scripts against every installed JAWS version, parse the PowerShell the
installer will run, build the bridge and the add-on, and compile the installer.

`checkHomerViewQuality.cmd` runs the seventeen checks. They exist because each one
caught something real, and several would have caught faults that reached a
tester. The ones worth knowing:

- Every menu row names a script that exists. `PerformScriptByName` fails
  **silently** on a wrong name.
- Every bridge command named in the script file has a `case` in the C#. Neither
  compiler can see this: the name is a string on one side and a case label on
  the other.
- Every function is defined before it is called. JSL assumes `int` for a name it
  has not seen, which is what broke a tester's compile once.
- The Alternate Menu is in case-insensitive alphabetical order. It drifted out
  of order because every new command was appended, and nothing objected.
- One key per command, agreeing across the key map, the menu, the Hotkey
  Summary and the describer file.

## Conventions that are easy to get wrong

- **Every script and function carries an `hV` prefix.** A generic name like
  `dialogPick` gets shadowed by another script suite — Leasey, on one tester's
  machine — and the failure is silent and only on somebody else's computer.
- **Built-ins whose return value drives logic are qualified `Builtin::`**, so a
  suite cannot substitute its own. Speech functions are deliberately **not**
  qualified: a user's suite overrides those on purpose, and overriding their
  screen reader on their own machine is not ours to do.
- **`ScheduleFunction`, `PerformScriptByName` and `UserBufferAddLink` are never
  qualified**, because they resolve one of our own names later and restricting
  scope would restrict that lookup too.
- **Helper lists are separated by a newline.** Not a control character, which
  XML forbids; not a vertical bar, which page titles are full of. Both were
  tried and both broke something.
- **PowerShell compares using the left operand's type.** Write
  `"skipped" -eq $value`, never the reverse: with a boolean on the left, any
  non-empty string converts to true.
- **In Inno, a line continuation ends at a comment.** Comments go above an
  entry, never inside it.

## The shared Homer classes

`homer\Inix.cs` and `homer\Web.cs` are copies of the shared Homer toolkit,
compiled into HomerView.exe beside HomerView.cs. They are sources rather than a
library, which suits this build: csc is the whole toolchain, there is no
package manager, and a source file cannot get out of step with a binary beside
it. They are in the same namespace, `Homer`, so nothing needs a `using` line.

They replaced real duplication. HomerView.cs had **three** hand-written
Content-Disposition parsers and no two agreed — one dropped the closing quote,
one kept it, none handled the RFC 5987 `filename*` form. It carried its own
MIME-to-extension table. And forty lines edited an `.inix` file by hand, with
no idea about multi-line values or a section named in a different case. Each is
now one call: `Web.fileFromDisposition`, `Web.mimeToExt`,
`InixCodec.writeValue`.

Treat them exactly as `homerPolicy.py` is treated: identical across projects, a
fix made in one copied to the others unread, and nothing in them naming
HomerView.

Check 18 asks whether those three calls are still there rather than hunting for
duplicates. Its first draft did hunt, and failed a correct file three times: on
a content-type-to-description map, which is a different table for a different
purpose; on the OOXML content types inside the spreadsheet writer, which are
part of the file format; and on the words "[Preferences]" inside the comment
explaining the change. A positive test cannot be fooled that way.

Not adopted, and worth saying why. `Say.cs`, `Lbc.cs`, `KeyMap.cs` and
`EdSharp.cs` are the WinForms half of a full application; the bridge is a
helper with two file dialogs, and pulling in 800 KB of forms code for that is
the wrong trade. `Version.cs` is generated for EdSharp and names its version,
and HomerView already has version.txt. `inixVert.cs` declares a `Main`, which
would collide with the bridge's own entry point.

## What belongs in the folder

`homerPolicy.py` decides, and it is the same file in every Homer Tools project.
A file belongs only if it is **named** — by a `Source` line in
`HomerView_setup.iss`, or in `RepoFiles.txt`. No pattern admits a file by the
look of its name. Anything else belongs in `notes\`, which `.gitignore` excludes
in one line.

Two sweeps apply that rule and both now import the module rather than
describing it: `tidyRepo.py` for the repository and `cleanDir.py` for the
folder. Until 31 August 2026 **neither imported it.** `homerPolicy.py` sat in
the folder while each sweep kept a private policy, and `cleanDir.ps1`'s private
policy — twenty-six names written inside a script whose own header said it read
the setup script — moved 42 files out of the project, including the whole
`jaws` folder and `RepoFiles.txt` itself. Nothing was lost, because it moved
rather than deleted, but the build stopped with seven missing files.

So `cleanDir.ps1` is gone and `cleanDir.py` replaces it. Three things about it
are worth keeping if it is ever rewritten:

- **It has no list.** There is nothing in it to keep in step with the setup
  script, because it reads the setup script.
- **It surveys first.** Running it prints the plan and stops; `--do-it` is a
  second, deliberate run. That is the only reason `tidyRepo` was safe in the
  same session in which `cleanDir.ps1` emptied the folder.
- **It refuses a plan that is too big** — more than 20 items, or a quarter of
  the folder — and says so, with `--anyway` for the day it is right. The
  42-file sweep would have stopped there.

A name in `RepoFiles.txt` may be a plain name, a folder ending in a backslash,
or a pattern such as `*.log`. Only the first shape was matched until the same
date, so `build\` and `notes\` had been in that file from the start and had
never matched anything.

The setup script installed `cleanDir` into the program folder until that date
too, on the two lines directly under the comment explaining why the sweep
belongs to the development folder and not to an installation.

An update zip should exclude everything in the `local:` section of
`RepoFiles.txt`. Those are build output and fetched libraries, and sending them
would overwrite freshly built binaries with older copies.

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

## The one that got away, and what it teaches

On 1 September 2026 Control+F in Edge answered **"Unknown script call to
virtual find"**. The cause: the `<browser>.jss` that `chainJawsScripts` writes
used `HomerView.jsb` and the factory browser binary, and not `default.jsb`.

**An application script file inherits the default script set by saying so, not
by being loaded.** Every script file Freedom Scientific ships for an
application begins with `Use "default.jsb"`. Ours did not.

**Key maps fall through; script sets do not.** Control+F is not in our key map,
so JAWS read it from `default.jkm` and found `VirtualFind` — exactly right.
`VirtualFind` lives in `default.jsb`, which was not loaded for Edge, so the
name resolved to nothing. It was never about Find: every default JAWS command
in the browser was gone, and Control+F was simply the first one reached for.

Nothing in the build could have caught it. The compiler is content, since a
`Use` line names a file rather than the names inside it. The installer is
content. The key read-back is content, because the keys really are in the file.
It fails only when somebody presses a key we did not bind — which is most of
them — and only on a machine with the scripts loaded.

Check 19 now asserts the line is written, and that it comes before
`Use "HomerView.jsb"`, since a later `Use` overrides an earlier one and our
scripts must be the last word. `chainJawsScripts` also deletes and rewrites a
`<browser>.jss` that the manifest says we created and that lacks the line, so
the repair reaches machines already running the broken one.

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

## The Homer Development Kit

Since 25 September 2026 HomerView builds on the kit at `C:\HomerDev`,
version 1.39.2 or later, following `HomerDev_update.md`. What that means
here, and what it does not yet mean:

**Done in this pass, without moving any file:**

- `buildHomerView.cmd` carries the kit contract: finds the kit, checks
  `kitNeeded`, compiles against `C:\HomerDev\CSharp\Inix.cs` and `Web.cs`,
  refreshes the kit's tools into `scripts\`, retires `cleanDir`, `tidyRepo`
  and `homerPolicy`, runs `fixEncoding`, and writes one log per session in
  `logs\HomerView-build-<stamp>.log`. `buildHomerView.ps1` is still the
  engine — it does five things no template build does — and now takes the
  compiler and the sources from the wrapper instead of choosing them.
- The local copies in `homer\` are deleted by the build and no longer named
  in `RepoFiles.txt`. `Keys.cs` is superseded by the kit's `KeyName.cs`.
- **Roslyn is required.** The kit's classes use modern C#, so the legacy
  `csc.exe` cannot compile them. Check 22, which forbade anything past C# 5,
  is retired; the wrapper finds Roslyn or installs Build Tools with winget.
- `LocalFiles.txt` and `accept.inix` exist in the kit's shape.

**Deliberately not done yet, because every path that names a moved file
must move with it** — the lesson HomerScribe paid for:

- The folder layout: `docs\` and the root documents to `help\`, `jaws\` to
  `scripts\jaws`, `build\` and the binaries to `exec\`. That touches every
  `Source:` line in the `.iss`, `chainJawsScripts`, `installJawsScripts`,
  `paths.py`'s shared-folder search, `makeDocs`, and the checks. One pass,
  with a map, and `checkHomerApp` at the end.
- The installer rewritten from `_APP__setup.iss` with `HomerComponents.iss`
  and the three-group finish page.
- The first spoken walk, `help\Tutorial_00_Overview.inix`.

**What the first build against the kit taught (25 September, kit 1.40.1):**

- The kit contract itself worked first time: kit found, Roslyn found in Build
  Tools, eighteen scripts refreshed, `fixEncoding` ran over 72 files.
- **HomerView's installer named every file by absolute path**,
  `C:\HomerView\...`, and `homerTidy` compares names. So nothing the `.iss`
  named counted as belonging, and the six generated `.htm` files — named
  nowhere else — were moved to `notes\drafts`. The next build stopped at
  "HomerView.htm does not exist". All 39 `Source:` lines are relative now, as
  the kit's template writes them; the build's own Source check resolves a
  relative name the way Inno does; and the `.htm` files are named in
  `RepoFiles.txt` because both forms are delivered and committed.
- **The build now makes each `.htm` from its `.md`** (Step 0), only when the
  `.md` is newer or the `.htm` is missing. A generated file is regenerated,
  not mourned.
- **Every tool called from the build gets an explicit `-build`.** A bare
  `call` inherits the caller's `%*`, and the first run reached `fixEncoding`
  with a stray `*` that cmd tried to run.
- Worth raising in the kit: `fixEncoding` "fixed" all fifteen scripts it had
  just refreshed from `C:\HomerDev\scripts`, so the kit's own copies are not
  in the Homer encoding and will churn on every app's build until they are.
  And `homerTidy.namedByInstaller` would be more robust comparing the file
  name of an absolute `Source:` as well as the whole string.

**From the sibling apps' logs of the same sweep, applied:**

- **`version.txt` is now the source of truth**, as the kit has it and as
  HomerScribe's log shows ("Version: 1.0.249 -> 1.0.250"). It used to be the
  other way round, with `manifest.ini` the source and `version.txt` written
  from it. Now the build steps `version.txt` and writes `manifest.ini` from
  it every build, bumped or not, so the two cannot drift; the installer
  already read `version.txt` at compile time. Absent, it is seeded from
  `manifest.ini`, never from the template's 1.0.0.
- **A running `HomerView.exe` is refused plainly** before the compile, as
  FileDir's build refuses ("FileDir.exe is running"), instead of surfacing as
  a CS2012 about a file in use.
- Already right: a failed CDN fetch of an engine warns and ships the copy
  already here (EdSharp's build hit a 404 on the NVDA controller client).

**Kit-level, not HomerView's to fix:** the stray `*` after `fixEncoding`
appears in HomerScribe's log word for word, so it is in the kit's tool;
`checkHomerDev` itself reports `CSharp\Web.cs`, `Say.cs` and `inixVert.cs`
and most of `help\` with LF line endings, which is why every app's build
"fixes" the fifteen scripts it just refreshed.

**Second build against the kit (25 September, 21:43):** Step 0 made two
documents, Step 1 passed with relative Source lines, the JAWS scripts
compiled byte-identically on three versions, quality checks 0 problems — and
Step 3 failed with `InixCodec does not exist`. The kit sources never reached
the compiler: the wrapper passed them as one quoted argument with quotes
round each path, and the inner quotes did not survive the cmd-to-PowerShell
boundary. Now semicolon-joined, split by the engine, each path checked, and
an empty list is a named failure rather than a compiler error forty lines
on. FileDir's log from the same sweep showed "kit 1.40.1 is older than
1.40.1" — a trailing space in the kit's `version.txt` that `[version]` would
not parse — so the wrapper's comparison now trims and tells a parse failure
from an old kit.

**Two things to watch on the first build against the kit:** `HomerView.cs`
calls `InixCodec.readValue`, which was added to HomerView's copy of
`Inix.cs` on 17 September; if the kit's `Inix.cs` lacks it, the compiler
will say so and it is a one-method addition to the kit. And `homerTidy` now
replaces `cleanDir`; run it as `scripts\homerTidy` (plan) then `--do-it`.


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

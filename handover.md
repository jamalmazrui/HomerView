# HomerView handover

For picking up development in a new conversation. This is a developer document,
so it says things plainly rather than simply.

## Where things stand

HomerView works with JAWS and NVDA. The two are meant to do the same things,
and `checkParity.cmd` measures how far that is true rather than asserting it:
**78 of 92 commands covered, 14 gaps.** Run it after adding a command to either
side.

The JAWS side has just been through a significant change, described next.

## The change that matters most: Edge-scoped keys

HomerView's keys used to live in `default.jkm`'s `[Virtual Keys]`. JAWS applies
that section **wherever a virtual cursor is active**, which is not only a
browser: an Outlook message, a Word document and a PDF all get one. Control+O
in Outlook was running HomerView's Open Document.

They now live in **Edge's own key map**, written per settings folder by
`chainJawsScripts.ps1`:

- 39 keys go into `msedge.jkm`, where they exist only while Edge has focus.
- 9 keys carrying the JAWS modifier stay in `default.jkm`, because a key with
  JAWSKey in it cannot collide with an application's own command.
- A user `msedge.jss` is written that `Use`s the factory Edge binary first and
  `HomerView.jsb` second. The scripting documentation calls this **layering**:
  anything not overridden is inherited. JAWS ships no Edge scripts today, so
  there is nothing to inherit yet, but the code is ready if that changes.

The installer detects an older install by its `homerViewChain.manifest`, names
the JAWS versions, and offers OK or Cancel. Cancel stops Setup before a file is
copied, because **the two approaches must never both be installed** — every key
would have two bindings and no way to tell which answered.

`hVInPageContext` and `hVPassKeyOn` remain in the scripts as belt and braces.
They are no longer the mechanism.

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
- **A known asymmetry.** On JAWS the page-context guard asks "is this a
  browser"; on NVDA it asks "is this HomerView's own browser", by process. The
  NVDA test is stricter and probably right.

## How to work on it

Run `buildHomerView.cmd`. It writes a detailed log and **exit 0 means ready**
for `git add -A`, commit, push, `tagRelease`. Its five steps compile the JAWS
scripts against every installed JAWS version, parse the PowerShell the
installer will run, build the bridge and the add-on, and compile the installer.

`checkHomerViewQuality.cmd` runs the fifteen checks. They exist because each one
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

---
title: "HomerView Developer Notes"
---

How to rebuild HomerView from source, and what the pieces are.

HomerView has two front ends and one engine. The **NVDA add-on** is Python; the
**JAWS scripts** are JSL; both talk to the same helper program, and both are
maintained at parity. Neither is the reference implementation. When the two
would answer one question differently, that is a bug in whichever one is newer.

## The pieces

- **`addon/`** — the NVDA add-on, Python. `commands.py` is the authoritative
  command list for that side: name, display name, keys and description.
- **`jaws/HomerView.jss`** — the JAWS scripts, JSL. `HomerView.jkm` is the
  readable home of the key bindings; `HomerView.jsd` is the documentation JAWS
  shows in its own dialogs.
- **`HomerView.cs`** — the helper, C# against .NET Framework 4.8, compiled to
  `HomerView.exe`. It holds the WebSocket connection to Edge, the accessibility
  engines, the download machinery, the file dialogs and the converters. Anything
  JSL cannot do, the helper does.
- **`buildHomerView.ps1`** — the build.
- **`checkJawsScripts.ps1`** — compiles the JAWS scripts against every installed
  JAWS version, after running the quality checks.
- **`checkHomerViewQuality.ps1`** — fifteen checks over the source, described
  below.
- **`chainJawsScripts.ps1`** — writes the key bindings into the user's
  `default.jkm` and hooks `MyExtensions.jss`. This is what actually binds keys;
  `HomerView.jkm` is documentation.
- **`installJawsScripts.ps1`** — the installer's JAWS step.
- **`HomerView_setup.iss`** — the Inno Setup script.

## Rebuilding

From the source folder:

```
powershell -ExecutionPolicy Bypass -File buildHomerView.ps1
```

That compiles the helper with `csc`, runs the quality checks, compiles the JAWS
scripts against each installed JAWS version, builds the NVDA add-on, and runs
Inno Setup over `HomerView_setup.iss`. It writes `buildHomerView.log`; read that
rather than the console.

The build fails if the quality checks fail. That is deliberate.

### Requirements

- Windows 10 or later
- .NET Framework 4.8 (`csc.exe` from the framework folder; no SDK needed)
- Inno Setup 6
- JAWS 2024 or later installed, for `scompile.exe`
- PowerShell 5.1

Nothing is downloaded during a build. The converters — pandoc and 2htm — are
**found, not bundled**: a program folder is replaced wholesale on update, and
some managed environments will not execute from a roaming profile.

### Installing what you built

```
HomerView_setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG="setup.log"
```

Run that from an elevated prompt; silent mode suppresses the wizard, not
elevation. The JAWS scripts install silently; the NVDA add-on and pandoc do not,
because one needs NVDA's own dialog and the other is a large download nobody
should be handed unasked.

Afterwards press **Alt+Shift+H**: its first line gives the version and install
time, which is how you confirm which build JAWS actually has loaded.

## Removing HomerView

NVDA can remove an add-on from its own Add-on Store. **JAWS has nothing of the
kind**: scripts compiled into a settings folder and keys written into a user's
`default.jkm` stay there until something takes them out. The uninstaller is the
only way back, so it is treated as a feature rather than as plumbing.

It appears in two places, both stated explicitly in the `.iss` rather than left
to Inno's defaults, because a default nobody has written down is one a later
edit can switch off unnoticed:

- **`unins000.exe` in the installation folder**, from `UninstallFilesDir={app}`
- **Windows Apps and Features**, from `CreateUninstallRegKey=yes`, listed under
  the program's name and version

What removal takes out:

- **The JAWS scripts** — `HomerView.jss`, `.jkm`, `.jsd` and the compiled
  `.jsb`, from every language folder of every installed JAWS version
- **The key bindings**, by running `chainJawsScripts -bUndo`, which removes the
  block from the user's `default.jkm` and unhooks `MyExtensions.jss`
- **The NVDA add-on**, through NVDA's own `--remove-addon` rather than by
  deleting folders behind its back, since NVDA keeps its own record of what is
  installed
- **`%LOCALAPPDATA%\HomerView`** entirely — the log, the cached engines, the
  extracted pages and the whole Edge profile
- **The program folder**, which is Inno's own job

What removal deliberately leaves alone: **your Downloads folder**. The reports
and the fetched files are yours, and an uninstaller that deletes a person's
downloads has badly overstepped.

Two details worth knowing:

**JAWS is asked to reload at the end.** On installation a reload saves a
restart; on removal it prevents a fault, because JAWS otherwise holds the old
compiled scripts in memory and the old keys bound, and every HomerView key goes
on half-working against a program whose files have gone.

**The removal log goes to `%TEMP%\HomerViewUninstall.log`**, not to HomerView's
own folder, because that folder is deleted moments later — so a removal that
went wrong would otherwise erase the only record of how.

## The quality checks

`checkHomerViewQuality.ps1` runs before any compiler and gates the build. Each
check reports **what it found** before it judges anything, because a check that
reports only a verdict cannot be debugged.

1. Every script in the key map exists in the source, and back
2. Every script the menu performs exists
3. Every menu row reads name, comma, sentence, optional parenthesised key
4. Every keyed command's menu key matches the key map
5. The documentation file and the scripts correspond
6. No lone backslash in a string literal (JSL escapes are `\\ \" \r \n \t \7 \'`)
7. No C-style comments
8. No `Null`, no `Let` without assignment, every declared name carries its type
9. Nothing used before it is defined
10. Every helper command has a case in the C#, and every dispatched method exists
11. Arguments reach the helper through a file, not the command line
12. No orphaned C# attribute; `[STAThread]` sits on `Main`
13. The answer-file encoding contract holds across the C# and the JSL
14. The key map, the binder and the Hotkey Summary agree, sections included
15. Every Hotkey Summary link names a real function and a real script
16. No menu command name contains another

## Conventions worth knowing before you change anything

**Anything JSL cannot do, the helper does.** JSL has no WebSocket, no JSON, no
file dialogs, no clipboard reading. Rather than working around that in JSL, add
a command to the helper.

**Anything page-sized stays on the helper's side.** A Windows command line
takes about 32,000 characters, and a page's links can exceed that. Every
argument is written to a file and the path is passed instead.

**Reduce in the browser, not afterwards.** A command that brings a whole
accessibility report back and parses it will appear to hang on a large page.
Return one line per finding and a count of the rest.

**Anything HomerView opens goes to HomerView's browser.** Opening a file through
the shell hands it to whatever Windows thinks opens `.htm`, where no HomerView
command works.

**Mark, then navigate.** Where the browser has found something the virtual
cursor must move to, the browser marks it with an attribute of ours and the
scripts move to whatever carries it. An attribute is the one thing both sides
can see.

**Check that it worked, not that it ran.** An exit code is not a result. Every
step that matters reports what it found.

## Testing a change

```
powershell -ExecutionPolicy Bypass -File checkJawsScripts.ps1
```

runs the quality checks and compiles the JAWS scripts against every installed
version without building anything else. It is the fast loop.

For the NVDA side, rebuild the add-on and install it in a scratch NVDA profile.

## Source

- [HomerView project on GitHub](https://github.com/JamalMazrui/HomerView)

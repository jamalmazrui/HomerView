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

<https://github.com/JamalMazrui/HomerView>

# HomerView

HomerView is an NVDA add-on that launches a dedicated instance of Microsoft Edge
with the Chrome DevTools Protocol enabled, then adds browse mode commands that
work only in that instance.

This release, 1.0.4, carries the two initial browse mode commands and the
connection machinery they need.

- NVDA+A reports the web address of the current page.
- J moves to the main content landmark of the current page. NVDA+Alt+M does the same.
- NVDA+Alt+A tests the page with axe-core, finds how to report the problems to the
  publisher, writes a full report, and opens it in a new tab.
- NVDA+Alt+E summarises the page structure, the visual aspects a reading order hides,
  and how best to move around it, in NVDA's browseable message window.
- NVDA+Alt+X extracts the readable part of the page and opens it as a plain document.
- NVDA+Alt+W lists the file types linked from the page and downloads the ones you choose.

Generated documents go to `%TEMP%\HomerView`, which Windows clears on its own.

Both behave like their JAWS counterparts, and both are confined to HomerView
pages. Chrome, Firefox, ordinary Edge windows, and native applications are
unchanged.

## Layout

```text
C:\HomerView
    HomerView_setup.iss     Inno Setup source for the installer
    buildAddon.cmd          Builds the add-on and writes buildAddon.log
    buildAddon.ps1          The build script itself
    clean.cmd
    createHomerViewRepo.cmd / .ps1   Creates the GitHub repository
    .gitignore               Removes build output and Python caches
    README.md
    CHANGELOG.md
    LICENSE.md

    addon\                  Add-on source, packaged into the .nvda-addon file
        manifest.ini
        doc\en\readme.html
        globalPlugins\homerView\
            __init__.py     Global plugin: launch command, overlay injection
            cdp.py          DevTools session, reader thread, event dispatch
            axe.py          axe-core accessibility testing
            alternateMenu.py  Command list, Alt+F10, and the hotkey summary
            clipboardTools.py Homer clipboard commands on the apostrophe key
            contacts.py     Finding how to reach a site's publisher
            convert.py      Opening other formats through 2htm
            ace.py          The IBM Equal Access engine
            act.py          Acting on the page by description
            documents.py    Help, About and History of Changes
            homer\          The shared Homer toolkit, copy it to reuse
                inix.py     Order preserving ini and inix files
                lbc.py      Layout by Code accessible dialogs
                say.py      One way to announce text
                web.py      Dependency free HTTP
            find.py         Regex and plain find, with repeat
            history.py      HomerView.db, what was opened and done
            metadata.py     What a page says about itself
            lbc.py          Layout by Code accessible dialogs
            saveAs.py       Saving a page as htm, md or txt
            homerCommands.py The Homer interface adapted to a browser
            homerText.py    Buffer text ranges: all, rest, selection, chunk
            selfTest.py     Proves all three browser channels work
            dialogs.py      Accessible dialogs
            download.py     Link analysis and cookie-replaying downloads
            mainContent.py  Readable-content extraction
            pageExplorer.py Page structure and visual summary
            paths.py        Temporary and downloads folders
            report.py       HTML and plain text report generation
            wcag.py         WCAG criteria and the axe rule mapping
            startPage.py    Markup for the window's start page
            edge.py         Edge location and launch
            logger.py       Per-session logging to HomerView.log
            pageBuffer.py   The NVDA+A and Q commands
            service.py      Worker thread, connection state, process identity
            webSocket.py    Loopback only RFC 6455 client

    Axe.json                Latest raw axe-core results
    Start.html              Page the HomerView window opens
    HomerView.log           Written by the add-on, fresh each NVDA session
    HomerView.previous.log  The preceding session's log
    build\                  Build output, including the .nvda-addon package
    docs\                   User guide, design notes, development plan
    installer\              License text shown by the installer
```

## Building

Run `buildAddon.cmd`. It packages the `addon` folder into
`build\HomerView-1.0.4.nvda-addon` and writes `buildAddon.log`.

Compile `HomerView_setup.iss` with Inno Setup 6 afterwards. The installer
expects the add-on package to exist in `build`.

## Installing during development

Open `build\HomerView-1.0.4.nvda-addon`, approve it in NVDA, and restart NVDA.
The installer is only needed for distribution.

## Requirements

NVDA 2025.1 or later, Microsoft Edge, and Windows 10 or later. The add-on uses
only the Python standard library, so nothing else has to be installed.

---
title: HomerView Development Plan
subtitle: Combined NVDA Virtual-Buffer and Microsoft Edge DevTools Automation
author: Jamal Mazrui
date: July 2026
---

# HomerView Development Plan

## 1. Purpose

HomerView will be an NVDA add-on and companion Windows launcher that gives blind Microsoft Edge users additional querying and action commands.

HomerView will combine two different representations of a web page:

1. **NVDA representation:** NVDA objects, browse mode, the virtual buffer, review position, focus, speech, braille, and accessible dialogs.
2. **Microsoft Edge representation:** the Chrome DevTools Protocol (CDP), including the Accessibility, DOM, Runtime, Page, Target, and Input domains.

The name **HomerView** applies to the complete product: launcher, NVDA add-on, CDP client, dialogs, installer, documentation, and future command modules.

## 2. Essential Architectural Correction

Launching Edge from NVDA does not, by itself, give NVDA control through CDP.

The required sequence is:

1. Windows invokes the HomerView desktop shortcut with `Ctrl+Alt+H`.
2. `HomerView.exe` locates and, when necessary, starts NVDA.
3. `HomerView.exe` launches or activates a dedicated Edge instance with remote debugging enabled.
4. HomerView discovers Edge's CDP endpoint.
5. The HomerView NVDA add-on or a persistent HomerView bridge connects to that endpoint.
6. NVDA hotkeys call HomerView functions.
7. Each function may use NVDA data, CDP data, or a coordinated combination of both.

The capability comes from **HomerView's CDP client code**, not from which program starts Edge.

## 3. Recommended Product Boundary

HomerView should use a hybrid design.

### 3.1 HomerView.exe

A small compiled Windows launcher should:

- Locate NVDA.
- Start NVDA when it is not running.
- Locate Microsoft Edge without assuming a single installation path.
- Start a dedicated Edge process with remote debugging.
- Use a dedicated Edge profile.
- Discover the dynamically assigned debugging port.
- Signal the NVDA add-on that Edge is available.
- Activate an existing HomerView Edge window when one already exists.
- Present accessible error messages when startup fails.

The launcher may be written in C# targeting .NET Framework 4.8, or packaged from Python. C# is preferable for a small, stable Windows launcher that does not depend on the user's Python installation.

### 3.2 HomerView NVDA add-on

The add-on should:

- Register all HomerView commands in NVDA's Input Gestures dialog.
- Read the current NVDA focus, navigator object, browse-mode position, and virtual-buffer context.
- Communicate with the CDP client.
- Speak and braille concise results.
- Display accessible query and results dialogs.
- Coordinate focus changes so that CDP actions and NVDA's virtual buffer remain synchronized.
- Avoid blocking NVDA's main thread.

### 3.3 CDP client

The CDP client should:

- Read the `DevToolsActivePort` file from the dedicated Edge profile.
- Connect only to a loopback WebSocket endpoint.
- Discover tabs and frames.
- Track the active page target.
- Enable required CDP domains.
- Send numbered commands and correlate responses.
- process asynchronous page, target, DOM, and accessibility events.
- reconnect when Edge restarts.
- cancel requests and enforce timeouts.
- return normalized HomerView element records instead of exposing raw CDP JSON to hotkey code.

For the first implementation, put the CDP client inside the NVDA add-on. If stability or dependency management becomes difficult, move it into a persistent local `HomerViewBridge.exe` and communicate through a named pipe.

## 4. Proposed Directory Tree

All development and installer content is rooted at:

```text
C:\HomerView
```

Recommended structure:

```text
C:\HomerView
│   HomerView_setup.iss
│   LICENSE.md
│   README.md
│   CHANGELOG.md
│   build.cmd
│   clean.cmd
│
├───build
│       HomerView.exe
│       HomerView.ico
│       HomerView.nvda-addon
│
├───docs
│       HomerView_Development_Plan.md
│       HomerView_User_Guide.md
│       HomerView_Commands.md
│       HomerView_Technical_Design.md
│
├───launcher
│       HomerView.cs
│       AssemblyInfo.cs
│       build.cmd
│
├───addon
│   │   manifest.ini
│   │   buildVars.py
│   │   readme.md
│   │
│   ├───globalPlugins
│   │   │   homerView.py
│   │   │
│   │   └───homerView
│   │           cdpClient.py
│   │           edgeLocator.py
│   │           elementModel.py
│   │           queryEngine.py
│   │           actionEngine.py
│   │           nvdaContext.py
│   │           resultDialogs.py
│   │           settings.py
│   │           speechOutput.py
│   │           targetManager.py
│   │           worker.py
│   │
│   └───doc
│       └───en
│               readme.html
│
├───installer
│       license.txt
│
└───tests
        testElementModel.py
        testQueries.py
        testTargetSelection.py
```

## 5. Launching Edge

HomerView should use a dedicated profile, for example:

```text
C:\HomerView\Data\EdgeProfile
```

Recommended launch arguments:

```text
--remote-debugging-port=0
--remote-debugging-address=127.0.0.1
--user-data-dir="C:\HomerView\Data\EdgeProfile"
--no-first-run
```

Using port `0` lets Edge select an available port. HomerView can then read:

```text
C:\HomerView\Data\EdgeProfile\DevToolsActivePort
```

This avoids hard-coding port 9222 and reduces collisions with other developer tools.

The profile should be dedicated to HomerView. It should not automatically share the user's ordinary Edge profile, cookies, passwords, or authenticated sessions.

## 6. Locating Microsoft Edge

`HomerView.exe` should try, in order:

1. Edge registration in Windows App Paths.
2. Edge installation registry keys.
3. `%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe`.
4. `%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`.
5. `%LocalAppData%\Microsoft\Edge\Application\msedge.exe`.

If Edge is not found, HomerView should display and speak:

> Microsoft Edge could not be found. Install Microsoft Edge or repair its Windows installation.

## 7. Locating and Starting NVDA

HomerView should first determine whether NVDA is running.

If not, it should try:

1. NVDA App Paths or uninstall registration.
2. `%ProgramFiles(x86)%\NVDA\nvda.exe`.
3. `%ProgramFiles%\NVDA\nvda.exe`.
4. A configured portable NVDA path.

Starting NVDA should be optional in settings because some users may be running JAWS or another screen reader when they press `Ctrl+Alt+H`.

Recommended behavior:

- If NVDA is running, continue.
- If NVDA is installed but not running, start it and wait for its window or process.
- If NVDA is unavailable, launch Edge but show an accessible message explaining that HomerView commands require NVDA and the HomerView add-on.

## 8. Desktop Shortcut Behavior

The installer creates:

```text
Desktop\HomerView.lnk
```

Target:

```text
C:\HomerView\HomerView.exe
```

Working directory:

```text
C:\HomerView
```

Shortcut key:

```text
Ctrl+Alt+H
```

Windows desktop shortcut hotkeys work only while the shortcut remains in a shell-recognized location, normally the desktop or Start Menu.

`Ctrl+Alt+H` should launch or activate HomerView. It should not be an NVDA gesture because it must work before NVDA is running.

## 9. NVDA Command Design

All add-on commands should have descriptions and appear under a **HomerView** category in NVDA's Input Gestures dialog. Default gestures should be conservative to minimize conflicts.

Suggested command families follow.

### 9.1 Status and synchronization

- Report whether HomerView is connected.
- Report active tab title and URL.
- Reconnect to Edge.
- Refresh both the CDP model and NVDA virtual buffer.
- Explain whether the current result came from NVDA, CDP, or both.
- Move NVDA focus or browse position to the last CDP result when possible.

### 9.2 Query commands

- Find by accessible role and name.
- List headings.
- List landmarks.
- List links.
- List buttons.
- List form fields.
- List tables.
- List live regions.
- List invalid fields.
- List disabled or unavailable controls.
- List expanded or collapsed controls.
- List checked, selected, or pressed controls.
- Search visible text.
- Search accessible names and descriptions.
- Query by CSS selector as an advanced option.
- Run a predefined JavaScript query as an advanced option.

### 9.3 Action commands

- Focus an element.
- Activate an element using keyboard semantics.
- Click an element through CDP input.
- Set or append text.
- Select an option.
- Check or uncheck a control.
- Expand or collapse a control.
- Scroll an element into view.
- Open a link in the current or new tab.
- Navigate back, forward, reload, or stop.
- Close, activate, or list tabs.
- Copy element information to the clipboard.

### 9.4 Inspection commands

- Describe the focused NVDA object.
- Describe the CDP element under browser focus.
- Compare the NVDA and CDP representations.
- Report role, name, value, description, states, DOM tag, attributes, bounds, and frame.
- Report the accessibility path and DOM ancestry.
- Report why a queried element is not exposed to NVDA.
- Capture a structured diagnostic record.

## 10. Query Dialog

The primary HomerView dialog should be keyboard and screen-reader accessible.

Fields:

1. Query text.
2. Query field: accessible name, visible text, value, description, selector, or all.
3. Role filter.
4. State filters.
5. Scope: current frame, all frames, current landmark, current form, or complete page.
6. Source: NVDA, CDP, or combined.
7. Match mode: contains, starts with, exact, wildcard, or regular expression.
8. Find button.
9. Results list.
10. Action button.
11. Details button.
12. Copy button.
13. Close button.

Each result should have a stable HomerView result identifier for the life of the query, rather than exposing transient CDP node identifiers to users.

## 11. Normalized Element Model

Both NVDA and CDP results should be converted to one model:

```text
HomerElement
    source
    role
    name
    value
    description
    states
    text
    url
    tagName
    attributes
    frameId
    backendNodeId
    axNodeId
    nvdaObject
    nvdaTextOffset
    bounds
    actions
```

Not every field will be populated for every element.

The model should record whether each property came from NVDA, CDP, or a reconciliation rule.

## 12. Reconciliation Strategy

Matching an NVDA virtual-buffer item to a CDP node is not guaranteed. HomerView should use a weighted match based on:

1. Accessible role.
2. Accessible name.
3. Value and states.
4. Browser focus.
5. DOM tag.
6. Screen bounds.
7. Text content.
8. Nearby ancestors.
9. Document order.

HomerView must report uncertainty. It should never silently claim that two objects are the same when the match is ambiguous.

## 13. Action Priority

For a realistic accessible interaction, action attempts should normally use this order:

1. Move focus to the element.
2. Use the element's expected keyboard activation.
3. Use CDP Input mouse events.
4. Use a CDP accessibility action when available.
5. Invoke JavaScript only as a last resort.

HomerView should optionally announce which action method succeeded.

## 14. Threading

No HTTP, WebSocket, Edge startup, DOM traversal, or long query may run on NVDA's main thread.

Use:

- A persistent worker thread or asynchronous service for CDP.
- A thread-safe request queue.
- Timeouts for every operation.
- A cancellation command.
- NVDA-safe callbacks for speech and dialogs.

## 15. Security Requirements

- Bind remote debugging only to `127.0.0.1`.
- Reject non-loopback WebSocket endpoints.
- Use a dedicated Edge profile.
- Do not expose a fixed public port.
- Do not log passwords, complete form values, cookies, authorization headers, or page source by default.
- Require confirmation before running arbitrary JavaScript.
- Mark JavaScript and CSS-selector commands as advanced.
- Detect enterprise policy that disables remote debugging and explain the condition.
- Close the HomerView Edge instance during uninstall only after user confirmation.
- Preserve the Edge profile during ordinary upgrades.
- Offer explicit profile deletion during uninstall.

## 16. Initial Milestones

### Milestone 1: Launcher proof of concept

- Locate Edge.
- Launch dedicated Edge with port `0`.
- Read `DevToolsActivePort`.
- Open the initial tab.
- Verify `/json/version`.
- Create `HomerView.exe`.

### Milestone 2: Minimal NVDA add-on

- Install a valid `.nvda-addon`.
- Add a HomerView category to Input Gestures.
- Implement connection status.
- Speak active page title and URL.
- Reconnect without restarting NVDA.

### Milestone 3: CDP queries

- Enable Target, Page, DOM, Runtime, and Accessibility.
- List headings, links, buttons, and form fields.
- Present results in an accessible dialog.
- Activate and focus a selected result.

### Milestone 4: NVDA integration

- Capture navigator object and browse position.
- Compare focused NVDA and CDP objects.
- Move from a CDP result toward the corresponding NVDA position.
- Refresh the virtual buffer after page-changing actions.

### Milestone 5: Advanced actions

- Text entry and selection.
- Tab management.
- Frame support.
- Live-region and event monitoring.
- Diagnostics and export.

### Milestone 6: Installer and release

- Build `HomerView.nvda-addon`.
- Build `HomerView.exe`.
- Compile `HomerView_setup.exe`.
- Test Windows 10 and Windows 11.
- Test current NVDA and at least one prior supported NVDA API version.
- Test Edge Stable under standard and administrator accounts.

## 17. Installer Policy

The Inno Setup installer should:

- Require administrator privileges because the requested destination is `C:\HomerView`.
- Install program files under `C:\HomerView`.
- Create Start Menu and optional desktop shortcuts.
- Assign `Ctrl+Alt+H` to the desktop shortcut.
- Offer to open the `.nvda-addon` package after installation.
- Let NVDA perform its normal add-on confirmation and restart process.
- Avoid silently writing into NVDA's user configuration directory.
- Preserve `C:\HomerView\Data` on upgrade and uninstall unless the user explicitly removes it.

## 18. Testing Matrix

Test combinations should include:

- Windows 10 and Windows 11.
- Installed NVDA and portable NVDA.
- Edge already running and not running.
- HomerView profile already running and not running.
- Standard user and administrator account.
- Single tab, multiple tabs, iframes, dialogs, and popups.
- Browse mode and focus mode.
- Dynamic single-page applications.
- Pages with poor or missing accessibility semantics.
- Enterprise remote-debugging policy disabled.
- Port collision and stale `DevToolsActivePort`.
- Edge crash, NVDA restart, and computer sleep/resume.
- High-latency pages and disconnected networks.

## 19. Final Recommendation

Build HomerView around one explicit principle:

> NVDA supplies the user interface, virtual-buffer intelligence, speech, braille, and gestures; HomerView supplies the CDP connection and reconciles the two browser representations.

The first release should concentrate on reliable querying, result dialogs, focus, activation, and diagnostics. Arbitrary JavaScript and broad browser automation should remain advanced features until the synchronization and security model is proven.

## 20. Primary References

- [NVDA 2026.1.1 Developer Guide](https://download.nvaccess.org/documentation/developerGuide.html)
- [Microsoft Edge DevTools Protocol](https://learn.microsoft.com/en-us/microsoft-edge/devtools/protocol/)
- [Microsoft Edge remote-debugging policy](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies/remotedebuggingallowed)
- [Chrome DevTools Protocol Viewer](https://chromedevtools.github.io/devtools-protocol/)
- [Inno Setup Icons section](https://jrsoftware.org/ishelp/topic_iconssection.htm)
- [Inno Setup documentation](https://jrsoftware.org/ishelp/)

---
title: HomerView Design Notes
subtitle: Decisions, Departures from the Development Plan, and What Remains Untested
author: Jamal Mazrui
date: July 2026
---

# Purpose

These notes record why the 0.4.0 code looks the way it does, where it departs
from `HomerView_Development_Plan.md`, and which assumptions still need to be
checked against a running NVDA. Read them before changing anything structural.

# Decisions

## Process identity, not window titles

The test for "is this object inside HomerView Edge" runs on every object NVDA
creates. It must therefore perform no input or output at all. HomerView caches
the set of Edge process identifiers when it connects, and the test is an integer
set membership check.

The earlier approach compared page titles against the foreground window title.
That is fragile in principle: window titles are truncated, duplicated across
tabs, and empty during navigation. It also failed concretely, because the same
page open in both HomerView Edge and ordinary Edge would match.

## Browse mode commands live on a tree interceptor class

A single letter bound on a global plugin is bound everywhere, including in every
edit box in Windows, and it stays bound until a runtime guard returns the right
answer. One defect in that guard and the user cannot type the letter at all.
That risk is not worth any amount of convenience.

Tree interceptors already distinguish browse mode from focus mode, so the letter
Q is safe there. The commands are defined as class members and composed in front
of NVDA's own browse mode class, rather than patched onto instances, so they
appear in Input Gestures and can be reassigned.

## One browser level connection, flattened sessions

HomerView opens a single WebSocket to the browser level endpoint and attaches to
page targets with `flatten` set to true. Each page is then addressed by session
identifier over that one connection. There is no reconnection when the user
changes tabs, and target lifecycle events are available.

A reader thread parses every incoming message, hands replies to waiting callers
by message identifier, and routes everything else to registered event handlers.
The earlier design discarded any message that was not the reply it was waiting
for, which made live regions, navigation events, and console errors unreachable.

## Port zero and DevToolsActivePort

Edge chooses a free port and publishes it in the `DevToolsActivePort` file in
the profile folder. HomerView reads it there. A fixed port collides with other
developer tools and with a second copy of HomerView.

## The profile lives under LOCALAPPDATA

The development plan placed the browser profile at `C:\HomerView\Data`. The
installer requires administrator rights, so a standard user could not write
there and Edge would fail to start. The profile is at
`%LOCALAPPDATA%\HomerView\EdgeProfile` instead.

## No launcher executable yet

The plan describes a `HomerView.exe` that locates NVDA, starts it if needed, and
launches Edge. That is worth building eventually, but nothing in this release
needs it, and a second installed component is real friction for users.
HomerView launches Edge from the add-on, and the launch command is
NVDA+Alt+H rather than a desktop shortcut hotkey.

Dropping the desktop shortcut also removes a conflict the plan did not notice.
The plan bound Alt+Control+H both as a Windows shortcut hotkey and as an NVDA
gesture; NVDA hooks the keyboard first, so the shortcut would never fire while
NVDA ran. Alt+Control is also AltGr on many European layouts, which would have
broken text entry for those users.

## Constant naming

Constants are named like variables, using words such as `default` or `maximum`
to convey uniqueness, and are declared separately from variables. The `c_`
prefix used in 0.3.0 predates the current convention.

## Suppressing Edge's sign-in and sync prompts

A fresh Edge profile is signed into the Windows account automatically, and Edge
then opens `edge://sync-confirmation-dialog`, which is modal to the browser
window. The address bar becomes unreachable and the browser looks frozen.

`--no-first-run` is a Chromium switch and does not cover this. The working set of
switches, and the seeded preferences that back them up, are taken from urlFido
and bookFido, where the same problem was diagnosed and solved.

Two adaptations were needed, because those tools use throwaway profiles while
HomerView's profile is persistent. Preferences are seeded only when the profile
folder is being created, never over an existing one. And `--disable-extensions`
is not passed, because a browsing profile should keep its extensions.

The `bAllowSignIn` constant in `edge.py` governs whether `--disable-sync` is
passed and whether the seeded preferences forbid sign-in. It defaults to False.
Setting it True still suppresses the prompts, so sign-in becomes deliberate.

## Two routes for attaching the browse mode commands

The preferred route composes a class in front of NVDA's browse mode class, which
gives Input Gestures integration. It depends on NVDA turning the overlay's
`_get_treeInterceptorClass` into a real property, and the 0.5.0 log showed that
method was never called even though the overlay was inserted. The likely cause
was that `HomerViewDocument` was a plain class, so NVDA's metaclass never
generated the property. It now derives from `AutoPropertyObject`.

Since that diagnosis is not certain, a fallback binds the same two functions onto
the tree interceptor instance on first focus. The commands then work but do not
appear in Input Gestures. Both command bodies live at module level so the two
routes run identical code, and the log states which route was taken along with
the tree interceptor's full method resolution order. Once the preferred route is
confirmed in a real session, the fallback can be deleted.

## Never treat the launched process exiting as a failure

The process started as `msedge.exe` very often exits within a fraction of a
second after handing its work to another process, while a browser window opens
and behaves perfectly. urlFido's own comment records this: the process it starts
"often exits almost at once after handing work to another, so HasExited says
gone while a window is still sitting there".

HomerView 0.6.0 polled `Popen.poll()` alongside the port file and aborted the
launch on exit code 0, roughly three tenths of a second in, killing a launch
that was about to succeed. The port file is now the only readiness signal, which
is what urlFido has always done. A launched process that exits is logged once,
at informational level, and the wait continues.

The same fact undermines the launched process identifier as an identity source.
It is used only when the protocol supplies no browser identifier, and never once
that process has exited.

## Choosing a key for main content

JAWS uses Q for the main region, and 0.3.0 through 0.6.0 followed it. NVDA
already uses Q for block quote navigation, so taking it removed a command the
user had rather than adding one.

NVDA spends most of the alphabet on quick navigation: A annotation, B button, C
combo box, D landmark, E edit field, F form field, G graphic, H heading, I list
item, K link, L list, M frame, N block of links, O embedded object, P paragraph,
Q block quote, R radio button, S separator, T table, U and V link states, W
spelling error, X check box. J is unassigned and carries a usable mnemonic.

`NVDA+Alt+M` is bound as well, so the command survives if J is later claimed by
NVDA or by another add-on. Both are constants at the top of `pageBuffer.py`.

## Matching NVDA's speech conventions

A new command should not merely work; it should behave the way its neighbours
behave, or it feels like a foreign object. Four details were adjusted.

`QuickNavItem.report` takes a `readUnit`, and NVDA's landmark command passes
`textInfos.UNIT_LINE`. Omitting it reads the entire element, so arriving at a
main landmark read the whole page. HomerView now passes the same unit.

NVDA's quick navigation checks `willSayAllResume(gesture)` and skips its report
when say all is about to continue from the new position. HomerView does the same.

NVDA's report commands speak once, spell on a second press, and copy on a third,
as report title does on NVDA+T. Reporting the web address follows that pattern
through `getLastScriptRepeatCount`.

The `@script` decorator takes `speakOnDemand`, which NVDA sets on query commands
so they still speak when speech mode is on demand. Reporting the address is a
query and is marked accordingly. Moving to main content is navigation and is
not, matching NVDA's quick navigation keys.

## When a page has no main landmark

Roughly half the web defines no main landmark; a real session showed Wikipedia's
portal page exposing navigation, search, navigation, content info, and
navigation, and nothing else.

0.8.0 responded by moving to the first heading instead. That was wrong. NVDA's
quick navigation keys leave the cursor exactly where it was when they find
nothing, and a navigation command that lands somewhere other than the requested
destination is worse than one that reports nothing was found, however clearly
the substitution is announced. 0.9.0 removed the fallback.

The message is `no main landmark`, lowercase, matching NVDA's own wording such
as `no next heading`. A document with no landmark support reports `Not supported
in this document`, which is NVDA's exact string.

## Running axe-core

The approach is urlCheck's. axe.min.js is fetched from a public content delivery
network with a second network as backup, so nothing has to be installed and
Node.js is not required. It is fetched once per NVDA session, since it is about
six hundred kilobytes and does not change between pages.

The source text is injected rather than a script url. urlCheck does this to
survive a content security policy that forbids external scripts. Here it is
delivered through `Runtime.evaluate`, which runs in the page's own context
through the debugger rather than as a script element, so the policy does not
apply at all.

Protocol evaluation gained a per-call timeout for this. An axe run can take
minutes on a large page, while ordinary calls take milliseconds, and one shared
timeout cannot serve both.

Results are written to `Axe.json` beside the log, in axe-core's own format
without a wrapper, so existing tooling can read them. The format already carries
the url, timestamp, and engine version.

Only the top document is analysed. Covering nested frames needs axe injected
into each of them before the page loads, which means reloading, and that would
discard whatever the user had typed.

## The start page

A real session showed the cost of about:blank plainly. The launch finished in
one second, and the log then recorded nothing at all for fifty-one seconds,
until a document appeared that the user had already navigated to by hand. An
empty document produces no NVDA document object and no tree interceptor, so the
window announced nothing, and there was no way to tell whether it was ready,
focused, or receiving keystrokes.

A real site would fix that but adds a network dependency and an opinion about
where the user wants to go. HomerView writes `Start.html` beside the log
instead. It loads instantly, works offline, lists the commands, and carries a
banner, a navigation landmark, a main landmark, and headings, so it doubles as a
self test: every command has something to work on before the user has navigated
anywhere.

The file carries a version marker in a meta element, and is rewritten when that
marker does not match, so edits to the markup reach existing installations.
`startPageUrl` in `edge.py` overrides the whole mechanism.

## Absorbing AccReporter

AccReporter was a Manifest V3 extension with the same purpose as this command.
Only its documentation survived, but the tutorial carried the full design and
the reasoning behind it, which is what mattered. Five decisions were kept.

**A document, not a dialog.** AccReporter's earlier version injected a modal
with a focus trap. That is right for a settings flyout inside a web application
and wrong for something a user needs to read, copy from, bookmark, print, or
save, with the scanned page's own DOM still sitting underneath it. HomerView
writes the report to disk and opens it in a tab, which gives the document shape
plus a file that survives the browser closing.

**Contact discovery is the point.** Scanners are a commodity. The step that is
missing from the market is what a user does after finding a barrier. Three
sources are merged because each catches what the others miss: the live page
through the protocol, which sees anchors added by script; the home page fetched
separately, whose footer usually carries what the current page lacks; and HEAD
probes of conventional paths, which find statements nothing links to.

**X is excluded from the social list.** A product decision, not an oversight.
Reports sent there have a poor record of reaching anyone who can act on them.

**Violations sorted by impact, elements inside details.** Someone writing to a
publisher leads with the worst problems, and a page with forty violations has to
stay readable at the top level.

**WCAG tag scoping.** `wcag2a`, `wcag2aa`, `wcag21aa`, and `best-practice`, not
every rule. Level AAA findings would pad a report with things the publisher
never undertook to meet. `lAxeTags` in `axe.py` restores the full set.

One decision was changed. AccReporter offered a Download button because its
report existed only in a tab, and a Copy button that used the clipboard
interface. HomerView has already written both files, so the report names their
paths, and the plain text version appears inside the HTML report as a selectable
block. That also sidesteps the clipboard restrictions browsers apply to local
files.

Contact discovery uses regular expressions rather than an HTML parser for
fetched markup, as AccReporter did. The goal is to find footer links in
real-world markup that is often malformed, where a strict parser gives up and a
forgiving pattern still succeeds.

## Logging

Logging goes to `C:\HomerView\HomerView.log` rather than into NVDA's own log,
because the point of this release is diagnosis and NVDA's log is both noisy and
awkward to reach. The file is opened with mode `w` when the logger module is
first imported, which is why that import comes first in the global plugin.

The standard library `logging` module is used rather than a hand-rolled writer,
because three threads write concurrently and its handlers are already
thread-safe. Records are flushed on every emit, so the file can be read while a
session is running.

Two constants at the top of `logger.py` control cost. `logLevel` sets verbosity,
and `maximumPayloadCharacters` caps how much of a protocol message is recorded.
Lower the second if a busy page makes the file unwieldy.

The hot path deserves a note. `chooseNVDAObjectOverlayClasses` runs for every
object NVDA creates, which on a large page means thousands of calls. Logging
there would flood the file and slow speech. The role test therefore comes first
and returns immediately for anything that is not a document, so logging happens
a handful of times per page rather than thousands.

## Suppressing Edge's sign-in and sync prompts

A fresh Edge profile is signed into the Windows account automatically, and Edge
then opens `edge://sync-confirmation-dialog`, which is modal to the browser
window. The address bar becomes unreachable and the browser looks frozen.

`--no-first-run` is a Chromium switch and does not cover this. The working set of
switches, and the seeded preferences that back them up, are taken from urlFido
and bookFido, where the same problem was diagnosed and solved.

Two adaptations were needed, because those tools use throwaway profiles while
HomerView's profile is persistent. Preferences are seeded only when the profile
folder is being created, never over an existing one. And `--disable-extensions`
is not passed, because a browsing profile should keep its extensions.

The `bAllowSignIn` constant in `edge.py` governs whether `--disable-sync` is
passed and whether the seeded preferences forbid sign-in. It defaults to False.
Setting it True still suppresses the prompts, so sign-in becomes deliberate.

## Two routes for attaching the browse mode commands

The preferred route composes a class in front of NVDA's browse mode class, which
gives Input Gestures integration. It depends on NVDA turning the overlay's
`_get_treeInterceptorClass` into a real property, and the 0.5.0 log showed that
method was never called even though the overlay was inserted. The likely cause
was that `HomerViewDocument` was a plain class, so NVDA's metaclass never
generated the property. It now derives from `AutoPropertyObject`.

Since that diagnosis is not certain, a fallback binds the same two functions onto
the tree interceptor instance on first focus. The commands then work but do not
appear in Input Gestures. Both command bodies live at module level so the two
routes run identical code, and the log states which route was taken along with
the tree interceptor's full method resolution order. Once the preferred route is
confirmed in a real session, the fallback can be deleted.

## Never treat the launched process exiting as a failure

The process started as `msedge.exe` very often exits within a fraction of a
second after handing its work to another process, while a browser window opens
and behaves perfectly. urlFido's own comment records this: the process it starts
"often exits almost at once after handing work to another, so HasExited says
gone while a window is still sitting there".

HomerView 0.6.0 polled `Popen.poll()` alongside the port file and aborted the
launch on exit code 0, roughly three tenths of a second in, killing a launch
that was about to succeed. The port file is now the only readiness signal, which
is what urlFido has always done. A launched process that exits is logged once,
at informational level, and the wait continues.

The same fact undermines the launched process identifier as an identity source.
It is used only when the protocol supplies no browser identifier, and never once
that process has exited.

## Choosing a key for main content

JAWS uses Q for the main region, and 0.3.0 through 0.6.0 followed it. NVDA
already uses Q for block quote navigation, so taking it removed a command the
user had rather than adding one.

NVDA spends most of the alphabet on quick navigation: A annotation, B button, C
combo box, D landmark, E edit field, F form field, G graphic, H heading, I list
item, K link, L list, M frame, N block of links, O embedded object, P paragraph,
Q block quote, R radio button, S separator, T table, U and V link states, W
spelling error, X check box. J is unassigned and carries a usable mnemonic.

`NVDA+Alt+M` is bound as well, so the command survives if J is later claimed by
NVDA or by another add-on. Both are constants at the top of `pageBuffer.py`.

## Matching NVDA's speech conventions

A new command should not merely work; it should behave the way its neighbours
behave, or it feels like a foreign object. Four details were adjusted.

`QuickNavItem.report` takes a `readUnit`, and NVDA's landmark command passes
`textInfos.UNIT_LINE`. Omitting it reads the entire element, so arriving at a
main landmark read the whole page. HomerView now passes the same unit.

NVDA's quick navigation checks `willSayAllResume(gesture)` and skips its report
when say all is about to continue from the new position. HomerView does the same.

NVDA's report commands speak once, spell on a second press, and copy on a third,
as report title does on NVDA+T. Reporting the web address follows that pattern
through `getLastScriptRepeatCount`.

The `@script` decorator takes `speakOnDemand`, which NVDA sets on query commands
so they still speak when speech mode is on demand. Reporting the address is a
query and is marked accordingly. Moving to main content is navigation and is
not, matching NVDA's quick navigation keys.

## When a page has no main landmark

Roughly half the web defines no main landmark; a real session showed Wikipedia's
portal page exposing navigation, search, navigation, content info, and
navigation, and nothing else.

0.8.0 responded by moving to the first heading instead. That was wrong. NVDA's
quick navigation keys leave the cursor exactly where it was when they find
nothing, and a navigation command that lands somewhere other than the requested
destination is worse than one that reports nothing was found, however clearly
the substitution is announced. 0.9.0 removed the fallback.

The message is `no main landmark`, lowercase, matching NVDA's own wording such
as `no next heading`. A document with no landmark support reports `Not supported
in this document`, which is NVDA's exact string.

## Running axe-core

The approach is urlCheck's. axe.min.js is fetched from a public content delivery
network with a second network as backup, so nothing has to be installed and
Node.js is not required. It is fetched once per NVDA session, since it is about
six hundred kilobytes and does not change between pages.

The source text is injected rather than a script url. urlCheck does this to
survive a content security policy that forbids external scripts. Here it is
delivered through `Runtime.evaluate`, which runs in the page's own context
through the debugger rather than as a script element, so the policy does not
apply at all.

Protocol evaluation gained a per-call timeout for this. An axe run can take
minutes on a large page, while ordinary calls take milliseconds, and one shared
timeout cannot serve both.

Results are written to `Axe.json` beside the log, in axe-core's own format
without a wrapper, so existing tooling can read them. The format already carries
the url, timestamp, and engine version.

Only the top document is analysed. Covering nested frames needs axe injected
into each of them before the page loads, which means reloading, and that would
discard whatever the user had typed.

## The start page

A real session showed the cost of about:blank plainly. The launch finished in
one second, and the log then recorded nothing at all for fifty-one seconds,
until a document appeared that the user had already navigated to by hand. An
empty document produces no NVDA document object and no tree interceptor, so the
window announced nothing, and there was no way to tell whether it was ready,
focused, or receiving keystrokes.

A real site would fix that but adds a network dependency and an opinion about
where the user wants to go. HomerView writes `Start.html` beside the log
instead. It loads instantly, works offline, lists the commands, and carries a
banner, a navigation landmark, a main landmark, and headings, so it doubles as a
self test: every command has something to work on before the user has navigated
anywhere.

The file carries a version marker in a meta element, and is rewritten when that
marker does not match, so edits to the markup reach existing installations.
`startPageUrl` in `edge.py` overrides the whole mechanism.

## Absorbing AccReporter

AccReporter was a Manifest V3 extension with the same purpose as this command.
Only its documentation survived, but the tutorial carried the full design and
the reasoning behind it, which is what mattered. Five decisions were kept.

**A document, not a dialog.** AccReporter's earlier version injected a modal
with a focus trap. That is right for a settings flyout inside a web application
and wrong for something a user needs to read, copy from, bookmark, print, or
save, with the scanned page's own DOM still sitting underneath it. HomerView
writes the report to disk and opens it in a tab, which gives the document shape
plus a file that survives the browser closing.

**Contact discovery is the point.** Scanners are a commodity. The step that is
missing from the market is what a user does after finding a barrier. Three
sources are merged because each catches what the others miss: the live page
through the protocol, which sees anchors added by script; the home page fetched
separately, whose footer usually carries what the current page lacks; and HEAD
probes of conventional paths, which find statements nothing links to.

**X is excluded from the social list.** A product decision, not an oversight.
Reports sent there have a poor record of reaching anyone who can act on them.

**Violations sorted by impact, elements inside details.** Someone writing to a
publisher leads with the worst problems, and a page with forty violations has to
stay readable at the top level.

**WCAG tag scoping.** `wcag2a`, `wcag2aa`, `wcag21aa`, and `best-practice`, not
every rule. Level AAA findings would pad a report with things the publisher
never undertook to meet. `lAxeTags` in `axe.py` restores the full set.

One decision was changed. AccReporter offered a Download button because its
report existed only in a tab, and a Copy button that used the clipboard
interface. HomerView has already written both files, so the report names their
paths, and the plain text version appears inside the HTML report as a selectable
block. That also sidesteps the clipboard restrictions browsers apply to local
files.

Contact discovery uses regular expressions rather than an HTML parser for
fetched markup, as AccReporter did. The goal is to find footer links in
real-world markup that is often malformed, where a strict parser gives up and a
forgiving pattern still succeeds.

## Logging as the answer to the open questions

Two of the untested assumptions below are settled by reading one real log rather
than by reasoning.

`resolveDocumentAddress` logs every candidate property with its raw value before
choosing one, and then logs which property supplied the answer. `isMainLandmark`
is preceded by `describeLandmarkItem`, which logs the label, landmark, roleText,
role, and name of every landmark encountered. After one session on a page with a
main landmark, both functions can be reduced to the single property that
actually works.

# Deliberately deferred

- The bridge process. The in-process Python client is simpler to ship and faster
  to iterate on. Introduce a bridge when NVDA restarts killing the browser
  session become intolerable, when `--remote-debugging-pipe` is wanted before a
  public release, or when JAWS support is committed to. The DevTools layer is
  kept behind a narrow interface so that swap stays contained.
- Accessibility domain work. The differentiating feature is
  `Accessibility.getFullAXTree` with its `ignored` and `ignoredReasons` fields,
  which can report why an element the user knows is on screen never reaches the
  buffer. Nothing else in the screen reader world answers that question. It
  belongs in the next release, not this one.
- Most of the query commands in section 9.2 of the plan. NVDA's Elements List
  already lists headings, links, buttons, form fields, and landmarks, faster and
  with correct semantics. Reimplementing them over a network hop is not a reason
  to change browsers.

# Assumptions, all now settled

Every assumption below has been confirmed against a real NVDA session. The list
is kept as a record of what was in doubt and how it resolved.

1. ~~`chooseNVDAObjectOverlayClasses` on a global plugin fires for browser
   documents.~~ **Confirmed in the 0.5.0 session log.** The hook fired for five
   Edge documents and the overlay was inserted.
2. ~~`_get_treeInterceptorClass` composition works.~~ **Confirmed.** Deriving
   from `AutoPropertyObject` was the fix. A real session composed both
   `HomerViewChromeVBuf` from `ChromeVBuf` and
   `HomerViewChromiumUIATreeInterceptor` from `ChromiumUIATreeInterceptor`, with
   `HomerViewBuffer` second in the method resolution order every time.
3. ~~The `__gestures` dictionary binds on the composed class.~~ **Confirmed.**
   Both commands responded on real pages, and every session logged "preferred
   route used". The fallback route is now dormant. It is kept rather than
   deleted because NVDA internals shift between releases and it costs twenty
   lines, but it should no longer fire.
4. ~~Address resolution.~~ **Confirmed.** `documentConstantIdentifier` and
   `documentURL` both returned the address; the root object's `value` was empty
   and has been dropped. The first is tried first, the second kept as insurance.
5. ~~Landmark item shape.~~ **Confirmed.** `item.obj.landmark` holds exactly
   `main`, and `item.label` reads `main` for the same node. `roleText` reads
   `main landmark` and was redundant, so it has been dropped.
6. ~~`SystemInfo.getProcessInfo`.~~ **Confirmed working on Edge 150.** It
   returned all twelve processes. Only the browser process identifier is now
   cached, since that is the one a document's window handle belongs to.
7. ~~`Role.DOCUMENT`.~~ **Confirmed.** Edge documents arrive with
   `baseClasses=['Document', 'Ia2Web', 'IAccessible']` and matched the filter.

# Testing notes

Beyond the assumptions above, exercise these cases:

- Ordinary Edge and HomerView Edge running at the same time, with the same page
  open in both. Q must behave as block quote navigation in the ordinary window.
- Chrome and Firefox open at the same time. Neither command should exist.
- NVDA restarted while HomerView Edge stays open, then NVDA+Alt+H pressed.
- A page with no main landmark, and a page whose main landmark is inside a frame.
- A page still loading when NVDA+A is pressed.
- Edge closed while NVDA remains running, then NVDA+Alt+H pressed again.
- Focus mode inside a HomerView page. Typing the letter Q must insert the letter.

---
title: HomerView User Guide
subtitle: Browse Mode Commands for a DevTools-Enabled Microsoft Edge
author: Jamal Mazrui
date: July 2026
---

# What HomerView Is

HomerView starts its own copy of Microsoft Edge with the Chrome DevTools
Protocol switched on, and then teaches NVDA a few commands that work in that
copy of Edge and nowhere else. The point is not to replace anything NVDA already
does well. It is to reach the parts of a web page that a screen reader cannot
normally see, and to answer questions that browse mode alone cannot answer.

This release carries two commands. Both are modelled on JAWS behavior that has
no direct NVDA equivalent.

# Starting HomerView

Use the launch command, NVDA+Alt+H (H for HomerView), to start or reconnect the
HomerView copy of Edge. NVDA says "Starting HomerView Edge" while the browser
comes up, and "HomerView Edge is ready" once the connection is working.

The window opens on a small start page, written to `C:\HomerView\Start.html`,
which lists the commands and carries a banner, a navigation landmark, a main
landmark, and headings. That is deliberate. An empty window gives NVDA nothing
to announce, so you cannot tell whether the browser is ready or whether your
keystrokes are reaching it. A page with real structure tells you both, and gives
every HomerView command something to work on before you have gone anywhere. If
you would rather open a real site, set `startPageUrl` near the top of `edge.py`
to any address.

The first launch creates a browser profile under your local application data
folder, at `HomerView\EdgeProfile`. This profile is separate from your ordinary
Edge profile, and that separation is not optional. Since Chrome 136 and the
matching Edge release, remote debugging switches are ignored altogether when
the browser is asked to debug its default data directory.

Edge signs a brand-new profile into your Windows account and immediately opens a
modal sync consent dialog. That dialog blocks the address bar, so Control+L and
Alt+D do nothing and the browser looks frozen. HomerView now seeds the profile
and passes the switches that prevent this, using the same approach that solved
it in urlFido and bookFido.

If a blocking dialog appears anyway, HomerView says so after launching, and the
dismiss dialog command, NVDA+Alt+D (D for dialog), closes it.

A separate profile does not have to mean an empty one. If you want the HomerView
profile signed in, so that bookmarks, passwords, and extensions arrive from your
Microsoft account, set `bAllowSignIn` to True near the top of `edge.py` and
delete the profile folder once so it is seeded again. Sign-in then becomes
something you choose in Settings rather than something Edge does to you. Weigh
that against the trade-off described under Security below.

If you have already opened pages in HomerView Edge before pressing NVDA+Alt+H,
reload them or open a new tab afterwards. The HomerView commands are attached to
a document as it loads, so documents that loaded before the connection existed
will not have them.

You can also assign a gesture to the connection status command, which reports
whether HomerView is connected and on which port. It has no gesture by default.

# Reading the Web Address

Use the report address command, NVDA+A (A for address), to hear the web address
of the page you are reading. Focus stays where it is; there is no trip to the
address bar and back, and no need to leave browse mode.

Press it twice to spell the address, and three times to copy it to the
clipboard. That is the same pattern NVDA uses for reporting the window title on
NVDA+T, so the command behaves the way the rest of NVDA has already taught you.
It also works when your speech mode is set to on demand, as NVDA's own query
commands do.

HomerView answers from NVDA's own knowledge of the document whenever it can,
which is almost always, and that answer is immediate. Only when NVDA does not
expose an address does HomerView ask the browser, and that request runs on a
background thread so that speech is never held up. If neither source can supply
an address, NVDA says "The web address is unavailable".

# Moving to the Main Content

Use the main content command, J (J for jump to main), to move the browse cursor
to the page's main landmark. This is the region a well-built page marks as its
actual content, past the banner, the navigation, and the advertising. If you
prefer a modifier, NVDA+Alt+J does the same thing, using the same letter.

J may look like an odd choice. The obvious key was Q, which is what JAWS uses
for the main region, but NVDA already spends Q on block quote navigation, and
taking it would cost you a command rather than adding one. NVDA spends most of
the alphabet the same way: D is landmark, P is paragraph, H heading, K link, F
form field, and so on down the list. J is one of the few letters left, and jump
to main is a serviceable mnemonic.

On arrival you hear one line, not the whole region. That matters more than it
sounds: a main landmark often contains the entire page, and reading all of it
would be an odd response to a navigation command. NVDA's own landmark key
behaves the same way, and if you press J during say all, say all resumes from
the new position instead of reading the line twice.

Roughly half the web defines no main landmark, and Wikipedia's front page is one
of those: it offers navigation, search, and content info and nothing else. When
that happens NVDA says "no main landmark" and your cursor does not move. That is
exactly how NVDA's own quick navigation keys behave when they find nothing, and
it matters: a navigation command that quietly lands you somewhere other than
where you asked is worse than one that tells you it found nothing.

Nothing NVDA already does is displaced. Block quote navigation on Q, landmark
navigation on D, and every other quick navigation key behave exactly as they
always have, inside HomerView pages and out. Both gestures are defined as
constants at the top of `pageBuffer.py` if you would rather have different ones,
and either can be reassigned in Input Gestures as described below.

# Testing a Page and Reporting It

Use the accessibility report command, NVDA+Alt+A (A for axe and for
accessibility), to test the page you are reading and find out how to tell the
people who own it about what was found. NVDA says "Testing the page and looking
for reporting channels" while it works, then reports the counts and opens the
report in a new tab.

Scanning is the easy half. Plenty of tools will tell you a page has eleven
violations. The harder question, and the one this command exists to answer, is
what you do next: who do you tell, and what do you say to them?

So after the scan, HomerView goes looking for every plausible way to reach the
publisher. It reads the page you are on, which catches links added by script
after the page loaded. It fetches the site's home page, whose footer almost
always carries contact and accessibility links even when the page you are on
does not. And it probes the conventional addresses, `/accessibility`,
`/accessibility-statement` and the like, which finds statements that nothing on
the site links to.

Everything it finds is sorted into accessibility statements, accessibility
pages, contact and support pages, and social channels. Any email address becomes
a link that opens a message already written for you, naming the page, listing
the worst violations with links explaining how to fix each one, and pointing at
the report file so you can attach it. Review it, add whatever you want to say in
your own words, and send it.

The social list leaves out X, formerly Twitter, on purpose. Accessibility
reports sent there have a poor record of reaching anyone who can act on them,
and sending you there would waste your time.

## Reading the report

The report is a document, not a dialog, and that is deliberate. A dialog traps
focus, sits on top of a page whose content is still underneath it, and cannot be
bookmarked, printed, or kept open while you write your email. The report has one
level one heading, a level two heading for each section, a level three heading
for each violation, and a working skip link, so the H key walks it the way it
walks any well-built page. Affected elements sit inside expandable sections, so
a page with forty violations is still readable at the top.

Violations are ordered with the most severe first, because that is the order you
want to lead with when you write to someone.

## The files

Three files are written, and each run replaces them.

`C:\HomerView\Report.html` is the report you just read. `Report.txt` is the
same thing as plain text, for pasting into a form or a message; it also appears
near the end of the HTML report as a block you can select and copy. `Axe.json`
holds the raw axe-core result in axe's own format, so anything that already
understands axe output can read it.

## Testing without the report

If you want the counts and nothing else, there is a second command with no
gesture assigned. Give it one in Input Gestures under the HomerView category. It
runs the same scan and writes `Axe.json`, but skips the contact search and the
report.

## What is tested

axe-core is run against the standards most publishers actually claim: WCAG 2.0
level A and AA, WCAG 2.1 level AA, and axe's best practice rules. Level AAA
rules are left out, since few sites undertake to meet them and their findings
would pad your report with things the publisher never promised.

axe-core is downloaded from a public content delivery network the first time you
use the command in an NVDA session, then kept in memory, so the first run is
slower than the rest. Nothing needs to be installed, and Node.js in particular
is not required.

Two limits are worth knowing. Only the top document is tested, so content inside
nested frames is not yet covered. And a page should finish loading before the
results mean much, since axe reports what is in the document at the moment it
runs.

# Where These Commands Apply

The two browse mode commands exist only on documents belonging to the HomerView
copy of Edge. They do not exist in Chrome, in Firefox, in an ordinary Edge
window, or in any native application. This is not a runtime check that might be
wrong; the commands are attached to the document itself as NVDA builds it, so
elsewhere they are simply not there, and the keys behave exactly as they always
have.

# Changing the Gestures

Every HomerView command appears in NVDA's Input Gestures dialog under the
HomerView category, so any of them can be reassigned or removed. The browse mode
commands appear while you are reading a HomerView page; the launch and status
commands appear anywhere.

| Command | Default gesture | Scope |
| --- | --- | --- |
| Launch or reconnect HomerView Edge | NVDA+Alt+H | Anywhere |
| Test the page and build a report | NVDA+Alt+A | Anywhere |
| Explore the page structure | NVDA+Alt+E | Anywhere |
| Extract the readable content | NVDA+Alt+X | Anywhere |
| Download linked files | NVDA+Alt+W | Anywhere |
| Test the page, counts only | None | Anywhere |
| Close a blocking Edge dialog | NVDA+Alt+D | Anywhere |
| Report connection status | None | Anywhere |
| Open the session log | None | Anywhere |
| Report the web address | NVDA+A | HomerView pages |
| Move to the main content | J | HomerView pages |
| Move to the main content | NVDA+Alt+J | HomerView pages |

# Reading the Log

HomerView writes a detailed record of everything it does to
`C:\HomerView\HomerView.log`. The file starts from empty each time the add-on
loads, which in practice means once per NVDA session, so it always describes the
session you are actually in rather than everything that has ever happened.

The previous session is kept beside it as `HomerView.previous.log`. That matters
more than it sounds: a defect that forces an NVDA restart would otherwise
destroy the very log needed to diagnose it.

Use the open log command, which has no gesture until you assign one in Input
Gestures, to hear the path and open the file in your usual editor. The log is
flushed after every line, so you can read it while a session is still running.

The header records the add-on version, the NVDA version, the Python version, and
where the log itself was written. Everything after that is timestamped and
labelled with the thread that produced it, which matters because HomerView runs
three: the main thread that drives speech, a worker thread that talks to the
browser, and a reader thread that receives from it. No line labelled MainThread
should ever be adjacent to a slow operation.

If the installation folder cannot be written, which happens when a standard user
runs an installation made by an administrator, the log falls back to your local
application data folder and says so in a warning near the top. The supplied
installer grants the Users group modify rights on the installation folder to
avoid this, so it should be rare.

# Security

Remote debugging means that any program running on your computer can connect to
the HomerView copy of Edge and act as you within it. HomerView binds the
debugging endpoint to the loopback address only, refuses any endpoint that is
not on the loopback address, and lets Edge choose a free port rather than
occupying a well-known one. Nothing is exposed to your network.

What HomerView cannot do is stop other software on the same machine from
connecting. If you sign the HomerView profile in to accounts that matter, judge
that risk for yourself. A profile you use for reading and research, and not for
banking, is a reasonable middle position.

# Troubleshooting

If launching fails with a message about the port never being published, close
all Microsoft Edge windows and try again. Edge keeps a hidden process running
after its last window closes, and command line switches are unreliable while one
is alive. If it still fails, check whether your organization has disabled remote
debugging by policy, which makes HomerView impossible rather than awkward.

If the two browse mode commands do nothing on a page, the document probably
loaded before HomerView connected. Reload the page.

If speech becomes sluggish, that is worth reporting, because it should not
happen. No HomerView code performs network activity on the thread that drives
speech, and the log will show which thread was busy when.

Whatever the symptom, the log is the first place to look, and it is small enough
to read end to end. Sending it along with a description of what you pressed is
usually enough to identify a defect without any further questions.

---
title: HomerView for JAWS
subtitle: What it would take, and what is already there
author: Jamal Mazrui
---

# What I could not verify

You remembered a way for JSL to use a COM DLL without registering it. I could
not confirm that from the JAWS scripting documentation, and I have been wrong
on specifics often enough in this project that I will not assert it either way.

Two things worth checking in the JAWS documentation, because they change the
design:

1. **Does JSL declare and call plain DLL exports?** Some scripting languages
   have a `dll ... enddll` block for this. If JSL does, a native DLL needs no
   registration at all and is the cleanest answer.
2. **What does `CreateObjectEx` take beyond the ProgID?** The Camel Type notes
   show it called with arguments after the ProgID. If one of those is a path or
   a registration-free flag, that is the answer you remembered.

The design below does not depend on either. If one turns out to be available,
it becomes a speed improvement rather than a rewrite.

# The architecture that needs nothing registered

A console program, **HomerViewBridge.exe**, which JSL runs and whose answer JSL
reads from a file.

    JSL script
      -> runs HomerViewBridge.exe with a CDP method and parameters
      -> bridge opens the WebSocket, sends, waits, writes the reply to a file
      -> JSL reads the file with Scripting.FileSystemObject
      -> JSL speaks or acts on the result

Everything here uses capabilities JSL certainly has: running a program, and
creating `Scripting.FileSystemObject`, which is registered on every Windows
machine already.

Nothing of ours is registered. Nothing is written to HKEY_CLASSES_ROOT. The
installer copies files and compiles scripts, and that is all.

## The cost, honestly

A new process for each command: roughly fifty to a hundred milliseconds, plus a
few more for the WebSocket handshake to a port on the same machine. For a
command a person invokes by pressing a key and then waits for an answer, that
is below what anybody notices.

Where it would show is a command issuing many CDP calls in a row, such as the
page explorer. The answer there is to do the whole job inside one invocation of
the bridge rather than calling it repeatedly, which is how the NVDA version
already works: one script, one round trip, one result.

## What a COM server would improve

Only the round trip. The connection would stay open between commands, and the
call would be a method rather than a process launch. Worth doing later if the
latency proves to matter, and the JSL side would not change if the bridge keeps
one command-shaped entry point.

# What JAWS already does, and must not be taken

This is the important half of the analysis, and it shrinks the work
considerably. JAWS already has, natively:

- **Q** moves to the main region. HomerView's J on NVDA exists only because NVDA
  has no such key. So J is not needed, and **Shift+Q** becomes the probable main
  content command, which is the one JAWS lacks.
- **JAWSKey+A** says the web address.
- **JAWSKey+F5, F6, F7** list form fields, headings and links. HomerView's own
  list commands on NVDA imitate these; on JAWS they are already there.
- **JAWSKey+T** says the title.
- **JAWSKey+DownArrow** says all; **Control** stops it.
- **Control+F** and **F3** find and find again in the virtual cursor.
- The whole quick navigation alphabet, and 1 through 6 for heading levels.
- **JAWSKey+F1** screen sensitive help, **JAWSKey+H** hot key help.

So roughly a third of HomerView's NVDA commands have a JAWS equivalent already,
and the JAWS version should not reimplement any of them. Doing so would take a
key a user already knows and give it something almost but not quite the same,
which is worse than not having it.

# What only HomerView can do, on either screen reader

These are the commands worth building, because nothing else has them. All are
pure CDP, so they cross without loss:

- Explore the page, including what is visible but unspoken
- Test for accessibility with axe-core or Equal Access, find the publisher's
  contact, and write the report
- Extract the main content into a page of its own
- Ask what is at a link without following it
- Open a document of any format as a web page
- Save the page in nine formats
- Download the files a page links to
- Count matches of a regular expression
- Look something up with services that need no account
- Say what the page claims about itself

# Where JAWS and NVDA will differ, and why

Worth stating plainly rather than discovering later. If either difference
motivates a screen reader publisher to close it, so much the better.

**The virtual cursor.** HomerView's NVDA page commands act on NVDA's browse
buffer. JAWS's virtual cursor is a different model with a different API, so
sentence movement, the selection markers and the buffer search need rebuilding
rather than porting. This is work, not a barrier.

**Finding text HomerView put on the page.** Shift+J on NVDA asks Readability
where the article starts, then finds those opening words in NVDA's own buffer.
JAWS needs its own equivalent of that search.

**Speech settings.** The NVDA version writes NVDA's configuration directly.
JAWS exposes its own equivalents, so this is a substitution rather than a gap.

**Events.** NVDA's add-on sees object and focus events and can react. JSL has a
rich event model of its own, so this may prove equivalent; it needs testing
rather than assuming.

# The order I would build it

1. **The bridge**, with one command: evaluate JavaScript in the active tab and
   return the result. Everything else is that command with a different script.
2. **Launch and connect**, on Alt+JAWS+H, matching the NVDA key with JAWS
   substituted for NVDA as you asked.
3. **Explore Page**, because it is the most distinctive and needs only the one
   bridge command.
4. **Check Accessibility**, which is the same shape and the most useful.
5. **The document commands**, which are conversion plus opening a file.
6. **The rest**, in the order the command table lists them.

Each step is testable on its own, which matters more here than usual: I cannot
run JAWS, so every step needs you or Scott to confirm it before the next is
built on it.

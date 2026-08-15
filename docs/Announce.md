---
title: "HomerView: a browser that answers"
---

HomerView is a free, open-source companion for reading the web with a screen
reader. It runs on Windows and works the same way with **JAWS** and with
**NVDA**. Neither is the main one; the two implementations are kept at parity
deliberately, key for key and answer for answer, so that what you learn on one
you already know on the other.

You can get it from the [HomerView project
page](https://github.com/JamalMazrui/HomerView), and the
[HomerView executable installer](https://github.com/JamalMazrui/HomerView/releases/latest)
is the quickest way to start.

## What it is for

A screen reader tells you what is on the screen. HomerView tries to answer the
questions you actually have about a page, which is a different job:

- What is this page really about, underneath the navigation and the banners?
- Where does that link go, before I commit to following it?
- Is this page accessible, and if not, what exactly is wrong with it?
- Can I have every file this page links to, without twenty separate visits to
  the download shelf?
- Can I read this Word document, this PDF, this ebook, as an ordinary web page
  where all of these commands work?

It answers those by driving its own copy of Microsoft Edge through the Chrome
DevTools Protocol. That means it can ask the browser things a screen reader
cannot see: the page as scripts have actually built it, the browser's own
cookies, what a link's server says before you go there.

## What makes it different

**It is not a scraper.** Requests carry the browser's own cookies, user agent
and referrer, so a file behind a sign-in comes to you exactly as it would to a
click.

**It answers rather than describes.** Link Target does not say "link, 47
characters"; it says what is at the other end, how big it is, and whether the
address goes somewhere other than it appears to.

**It respects what your screen reader already does well.** HomerView adds no
command for listing headings or links, because JAWS and NVDA both do that
properly already. It fills gaps rather than competing.

**Both screen readers are first class.** Every command in this announcement
exists on both, on keys chosen to suit each one's conventions. Where the keys
differ, they differ for a reason that is written down.

## Getting it

1. Download the [HomerView executable
   installer](https://github.com/JamalMazrui/HomerView/releases/latest).
2. Run it. The installer offers to set up the JAWS scripts, the NVDA add-on, or
   both, depending on what it finds on your machine.
3. Press **Alt+JAWSKey+H** (JAWS) or **NVDA+Alt+H** (NVDA) to start.

The source, the issue tracker and the full history are on the [HomerView
project page](https://github.com/JamalMazrui/HomerView).

## Who it is by

HomerView is written by Jamal Mazrui, who is blind and uses it daily. It is one
of the Homer family of accessibility tools, alongside EdSharp, FileDir, urlFido
and DbDo, and it shares their conventions: the same clipboard commands, the same
selection keys, the same idea that a program should say what happened rather
than leave you guessing.

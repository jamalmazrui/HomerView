"""Markup for the page the HomerView Edge window opens.

about:blank opens a window NVDA has nothing to say about: no document, no tree
interceptor, no announcement, and no sign the window is ready. This page loads
instantly, needs no network, and carries a banner, a navigation landmark, a
main landmark and headings, so every HomerView command has something to work on
the moment the window appears.

The links meet a strict test: the thing itself must be free and open source
software, not merely a company that publishes some. That test excludes more
than it admits, and the exclusions are worth naming because each is a service
people reasonably assume is open.

DuckDuckGo's browser apps are open source and its search service is not, so the
service fails. GitHub hosts an enormous amount of free software and is itself
proprietary. LinkedIn is proprietary. Grok is a proprietary service; some model
weights have been published, which is not the same thing as the service being
open. None of them belong here under this rule.
"""

startPageVersion = "18"

startPageText = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="homerViewStartVersion" content="{version}">
<title>HomerView Start Page</title>
</head>
<body>
<h1>HomerView Start Page</h1>
<header>
<p>HomerView start page</p>
</header>
<nav aria-label="Places to start">
<h2>Places to start</h2>
<p>Everything here is free, and free in the thing itself rather than only in its
publisher. For software that means an open source licence. For a library it means
the works are free to read.</p>
<ul>
<li><a href="https://en.wikipedia.org/">Wikipedia</a>
&mdash; a general encyclopedia written and revised by volunteers. The articles are
under a Creative Commons ShareAlike licence, and the MediaWiki software that runs
them is under the GNU General Public License.</li>
<li><a href="https://www.gutenberg.org/">Project Gutenberg</a>
&mdash; more than seventy thousand books whose copyright has expired, as plain text,
EPUB and Kindle files. Nothing here asks you to sign in, and plain text is the
easiest thing a screen reader ever meets.</li>
<li><a href="https://archive.org/">Internet Archive</a>
&mdash; a library of web pages, books, audio and film, including the Wayback Machine
that keeps old copies of pages that have changed or gone. Its own software is under
the GNU Affero General Public License, though some of the books it lends are
borrowed rather than free.</li>
<li><a href="https://joinmastodon.org/">Mastodon</a>
&mdash; social posting run on servers that anyone can set up, rather than on one
company's. The server software is under the GNU Affero General Public License, and
the servers talk to each other, so your account is not tied to one of them.</li>
<li><a href="https://searx.space/">SearXNG instances</a>
&mdash; a search tool that passes your question to several search engines at once and
merges the answers. GNU Affero General Public License, and you can run your own copy
if you would rather not use someone else's.</li>
<li><a href="https://ollama.com/">Ollama</a>
&mdash; a way to run language models on your own computer. Nothing you type goes
anywhere else, and it is under the MIT License.</li>
<li><a href="https://www.mozilla.org/">Mozilla</a>
&mdash; the makers of the Firefox browser and the Thunderbird mail program. Both are
open source under the Mozilla Public License.</li>
<li><a href="https://www.gnu.org/">GNU Project</a>
&mdash; where most of the licences above come from. It treats software freedom as
the point rather than a side effect.</li>
</ul>
</nav>
<main>
<p>This window belongs to HomerView. Press Control+L to type a web address.</p>
<!-- COMMANDS BEGIN. Written by makeDocs; do not edit between the markers. -->
<h2>Commands</h2>
<p>These work the same way whether you use JAWS or NVDA. Press Alt+F10
for the full list, including the few that differ.</p>
<ul>
<li><strong>Choose Browser</strong>, Alt+Shift+B &mdash; Choose which Chromium browser HomerView drives, from the ones installed here.</li>
<li><strong>Copy Append</strong>, Alt+C &mdash; Append selected text to clipboard, or append current line if no selection.</li>
<li><strong>Dismiss Dialog</strong>, Alt+Shift+D &mdash; Closes a browser dialog that is blocking the window.</li>
<li><strong>Find Contacts</strong>, Alt+Shift+C &mdash; Finds who to tell about this site: email addresses, the accessibility statement, contact pages and social media.</li>
<li><strong>HomerView Settings</strong>, Alt+Shift+S &mdash; Open the settings file, HomerView.inix, in a text editor.</li>
<li><strong>Launch HomerView</strong>, Alt+Control+Shift+H &mdash; Launches or reconnects the HomerView copy of Microsoft Edge.</li>
<li><strong>Link Target</strong>, Alt+L &mdash; Ask what is actually at that link without going there: what kind of thing, how big, and whether it ends up where it claims.</li>
<li><strong>List Names</strong>, Alt+N &mdash; Lists the people, places, organisations and dates a page mentions, saved as Names.htm in the page's folder and opened.</li>
<li><strong>Log to Clipboard</strong>, Alt+Shift+L &mdash; Copy the HomerView log to the clipboard as a file, so Control+V attaches it to an email rather than typing its name into one.</li>
<li><strong>Open Document</strong>, Control+O &mdash; Opens a Word file, spreadsheet, slide deck, PDF or ebook, converting it to a page so every command here works on it.</li>
<li><strong>Page Folder</strong>, Alt+Shift+F &mdash; Open this page's folder in File Explorer, to browse what was saved from it.</li>
<li><strong>Page Links to Clipboard</strong>, Alt+Shift+P &mdash; Copy every link address on the page to the clipboard, as EdSharp copies a path on the same key.</li>
<li><strong>Recent Pages</strong>, Alt+R &mdash; Open a page from the list of those recently used, on the key EdSharp uses for its recent files.</li>
<li><strong>Save Page</strong>, Control+S &mdash; Saves the page in any of nine formats.</li>
<li><strong>Say Metadata</strong>, Alt+M &mdash; Says what the page claims about itself: author, publisher, date and licence.</li>
<li><strong>Session Log</strong>, Control+Shift+L &mdash; Open a copy of this session's log, for working out what went wrong.</li>
<li><strong>Web Download</strong>, Alt+Shift+W &mdash; Pick files to download from a web page, on the key EdSharp uses for it.</li>
</ul>
<!-- COMMANDS END -->
<h2>Documentation</h2>
<p>These open in this window, where every HomerView command works on them. They
are also in the Alternate Menu, on Alt+F10.</p>
<ul>
<li><a href="ReadMe.htm">Quick start</a> &mdash; the first ten minutes.</li>
<li><a href="HomerView.htm">User guide</a> &mdash; every command and what it does.</li>
<li><a href="History.htm">History of changes</a> &mdash; what changed in each version.</li>
<li><a href="Developer.htm">Developer notes</a> &mdash; architecture, conventions, building.</li>
</ul>
<h2>About this page</h2>
<p>Every HomerView command appears in the NVDA Input Gestures dialog under the
HomerView category, where it can be reassigned.</p>
<p>Commands only work in windows HomerView itself opened. An Edge window that was
already running when you pressed Alt+Control+Shift+H has no debugging connection and
cannot be given one, so HomerView opens its own window and carries your current
address across.</p>
</main>
<footer>
<p>HomerView writes its session log to HomerView.log in the folder this page came from.</p>
</footer>
</body>
</html>
"""


def getStartPageText():
    return startPageText.format(version=startPageVersion)


def getVersionMarker():
    return f'content="{startPageVersion}"'

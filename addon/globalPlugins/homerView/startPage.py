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

startPageVersion = "5"

startPageText = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="homerViewStartVersion" content="{version}">
<title>HomerView</title>
</head>
<body>
<header>
<p>HomerView start page</p>
</header>
<nav aria-label="Places to start">
<h2>Places to start</h2>
<p>Everything listed here is free and open source software, the thing itself
and not merely its publisher.</p>
<ul>
<li><a href="https://en.wikipedia.org/">Wikipedia</a>
&mdash; a general encyclopedia, the class of reference site whose articles are
written and revised by volunteers rather than by a fixed editorial staff.
Articles under Creative Commons Attribution ShareAlike; the MediaWiki software
behind them under the GNU General Public License.</li>
<li><a href="https://searx.space/">SearXNG instances</a>
&mdash; a metasearch engine, the class of tool that passes a query to several
other search engines and merges what comes back, run either by someone else or
by you. GNU Affero General Public License.</li>
<li><a href="https://ollama.com/">Ollama</a>
&mdash; a way to run language models on your own machine, the class of program
that answers questions without sending them anywhere. MIT License.</li>
<li><a href="https://www.mozilla.org/">Mozilla</a>
&mdash; the makers of Firefox and Thunderbird, the class of organisation that
develops browsers and mail clients as open source rather than as products with
source withheld. Mozilla Public License.</li>
<li><a href="https://www.gnu.org/">GNU Project</a>
&mdash; the origin of the licences most of the above are published under, and
the class of project that treats software freedom as the point rather than a
side effect.</li>
</ul>
</nav>
<main>
<h1>HomerView</h1>
<p>This window belongs to HomerView. Press Control+L to type a web address.</p>
<h2>Commands in a web page</h2>
<ul>
<li>Alt+A reports the web address. Press twice to spell it, three times to copy it.</li>
<li>J moves to the main content landmark. Shift+J finds it when the page declares none.</li>
<li>Y summarises the structure of the page.</li>
<li>Alt+K tests the page for accessibility, asking which engine to use.</li>
<li>Control and Alt with the up and down arrows move by paragraph and by sentence.</li>
<li>Alt+F8 reads the whole page. Control+F8 copies it.</li>
<li>Control+F finds text or a regular expression. F3 repeats it.</li>
<li>Alt+F10 lists every command in one alphabetical list.</li>
</ul>
<h2>Commands anywhere</h2>
<ul>
<li>NVDA+Alt+H launches or reconnects HomerView Edge.</li>
<li>NVDA+Alt+F10 lists every command, even before HomerView Edge is running.</li>

<li>NVDA+Alt+X extracts the readable part of the page.</li>
<li>NVDA+Alt+W downloads files linked from the page.</li>
<li>Control+O opens a document of almost any format.</li>
<li>Control+F12 saves the page as a web page, Markdown, text, Word, PDF or an image.</li>
</ul>
<h2>Documentation</h2>
<p>These open in this window, where every HomerView command works on them. They
are also in the Alternate Menu on Alt+F10.</p>
<ul>
<li><a href="README.htm">Quick start</a> &mdash; the first ten minutes.</li>
<li><a href="HomerView.htm">User guide</a> &mdash; every command and what it does.</li>
<li><a href="History.htm">History of changes</a> &mdash; what changed in each version.</li>
<li><a href="Developer.htm">Developer notes</a> &mdash; architecture, conventions, building.</li>
</ul>
<h2>About this page</h2>
<p>Every HomerView command appears in the NVDA Input Gestures dialog under the
HomerView category, where it can be reassigned.</p>
<p>Commands only work in windows HomerView itself opened. An Edge window that was
already running when you pressed NVDA+Alt+H has no debugging connection and
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

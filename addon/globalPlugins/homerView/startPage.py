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

startPageVersion = "13"

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
<li><strong>J</strong> jumps to the main content.</li>
<li><strong>Shift+J</strong> finds the main content when the page declares none.</li>
<li><strong>Y</strong> summarises the structure of the page.</li>
<li><strong>Alt+A</strong> reports the web address. Twice spells it, three times copies it.</li>
<li><strong>ScrollLock</strong> starts reading continuously, and stops it. One key for
both.</li>
<li><strong>Alt+F8</strong> reads the whole page without moving the cursor.
<strong>Control+F8</strong> copies it.</li>
<li><strong>Control+F</strong> finds text, not case sensitive. <strong>Control+F3</strong> finds a
regular expression. <strong>F3</strong> repeats either.</li>
<li><strong>Alt+W</strong> finds the next place the word at the cursor appears.</li>
<li><strong>Alt+K</strong> tests the page for accessibility.</li>
<li><strong>Control</strong> and <strong>Alt</strong> with the up and down arrows move by
paragraph and by sentence.</li>
<li><strong>F4</strong> lists the HomerView tabs and switches to the one you choose.
<strong>Shift+F4</strong> just says their names. <strong>Control+Shift+F4</strong> closes
the ones you are done with.</li>
<li><strong>Control+F11</strong> checks for a newer HomerView and installs it.</li>
<li><strong>F1</strong> opens the user guide, <strong>Alt+F1</strong> the About box, and
<strong>Shift+F1</strong> the history of changes.</li>
<li>The <strong>grave accent</strong> key adjusts speech.
<strong>Alt+Control+Accent</strong> switches punctuation between all and none.
<strong>Control+Accent</strong> and <strong>Control+Shift+Accent</strong> change the rate.
<strong>Alt+Accent</strong> and <strong>Alt+Shift+Accent</strong> change the volume.
<strong>Shift+Accent</strong> reports all three.</li>
</ul>
<h2>Commands anywhere</h2>
<ul>
<li><strong>Alt+NVDA+H</strong> launches HomerView Edge, or brings its window forward.</li>
<li><strong>Alt+NVDA+F10</strong> lists every command in one alphabetical list. It works
everywhere, including before HomerView Edge is running, and it can start it for you.</li>

<li><strong>Alt+NVDA+X</strong> extracts the readable part of the page.</li>
<li><strong>Alt+NVDA+W</strong> downloads files linked from the page.</li>
<li><strong>Control+O</strong> opens a document of almost any format. Word, Excel,
PowerPoint, PDF, rich text, OpenDocument, EPUB and Markdown are converted and read as
web pages; everything the browser already opened, it still opens.</li>
<li><strong>Control+S</strong> saves the page as a single file archive the way Edge does,
or as a web page, Markdown, plain text, a Word document, a PDF, an image, or the
accessibility tree.</li>
</ul>
<h2>Documentation</h2>
<p>These open in this window, where every HomerView command works on them. They
are also in the Alternate Menu, on Alt+NVDA+F10.</p>
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
already running when you pressed Alt+NVDA+H has no debugging connection and
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

"""Markup for the page the HomerView Edge window opens.

about:blank opens a window NVDA has nothing to say about: no document, no tree
interceptor, no announcement. A real session showed no document object at all
until the user had navigated somewhere by hand, so the window gave no sign it
was ready or even focused.

This page loads instantly, needs no network, and carries a banner, a navigation
landmark, a main landmark, and headings, so every HomerView command has
something to work on the moment the window appears.

The three links describe a class of application rather than praising a product,
and each says plainly how it is licensed, because "open source" is claimed more
often than it is true. DuckDuckGo is the case in point: its browser apps are
open source and its search service is not.
"""

startPageVersion = "2"

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
<ul>
<li><a href="https://duckduckgo.com/">DuckDuckGo</a>
&mdash; a web search engine, the class of site that indexes other pages and
returns a ranked list of links for a query.
Licence: the search service is proprietary, though DuckDuckGo's browser apps and
extensions are published under open source licences.</li>
<li><a href="https://openclaw.ai/">OpenClaw</a>
&mdash; a personal assistant you run on your own machine, the class of program
that takes instructions in ordinary language and carries them out by running
commands and driving other software.
Licence: MIT, so it meets the open source test.
Worth knowing: it can run commands and read files, and its own community advises
against installing it on the computer you rely on daily.</li>
<li><a href="https://en.wikipedia.org/">Wikipedia</a>
&mdash; a general encyclopedia, the class of reference site whose articles are
written and revised by volunteers rather than by a fixed editorial staff.
Licence: the articles are under Creative Commons Attribution ShareAlike and the
MediaWiki software behind them is under the GNU General Public License.</li>
<li><a href="https://searx.space/">SearXNG instances</a>
&mdash; a metasearch engine, the class of tool that passes a query to several
other search engines and merges what comes back, run either by someone else or
by you.
Licence: GNU Affero General Public License. Listed here because it is the search
option that actually meets the open source test end to end.</li>
</ul>
</nav>
<main>
<h1>HomerView</h1>
<p>This window belongs to HomerView. Press Control+L to type a web address.</p>
<h2>Commands in a web page</h2>
<ul>
<li>NVDA+A reports the web address. Press twice to spell it, three times to copy it.</li>
<li>J moves to the main content landmark. NVDA+Alt+J does the same.</li>
<li>Alt+F8 reads the whole page. Control+F8 copies it.</li>
<li>Alt+F10 lists every command in one alphabetical list.</li>
</ul>
<h2>Commands anywhere</h2>
<ul>
<li>NVDA+Alt+H launches or reconnects HomerView Edge.</li>
<li>NVDA+Alt+F10 lists every command, even before HomerView Edge is running.</li>
<li>NVDA+Alt+A tests the current page with axe-core.</li>
<li>NVDA+Alt+E summarises the structure of the current page.</li>
<li>NVDA+Alt+X extracts the readable part of the current page.</li>
<li>NVDA+Alt+W downloads files linked from the current page.</li>
</ul>
<h2>About this page</h2>
<p>Every HomerView command appears in the NVDA Input Gestures dialog under the
HomerView category, where it can be reassigned.</p>
<p>Commands only work in windows HomerView itself opened. An Edge window that was
already running when you pressed NVDA+Alt+H has no debugging connection and
cannot be given one, so HomerView opens its own window instead and carries your
current address across.</p>
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

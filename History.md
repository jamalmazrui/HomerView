---
title: HomerView History of Changes
author: Jamal Mazrui
---

# About this history

What changed, newest first. Written the way you would tell somebody, not as a
list of commit messages. The reasoning behind each change is in the code, where
it belongs. This is the short version.

# Version 1.43.1

- The full guide is HomerView.md and HomerView.htm again. It was briefly called App.md, from a misreading: the Homer Tools convention names that file after the app, and App was the placeholder rather than the name.
- So the five documents in every Homer Tools project are ReadMe, then the one named after the app, then Developer, History and Announce. For this project the second is HomerView.
- Checked the setup script and .gitignore against what the project actually holds. Every file the installer requires exists, all six documents ship as both Markdown and web page, no directive appears twice, no shortcut points at something that is not installed, and nothing that belongs in the repository is being excluded from it.

# Version 1.43.0

- Every document HomerView ships can now be opened from the Alternate Menu. Two of them could not be opened at all: the hotkey list and the announcement shipped with the program and had no command, which means nobody would ever have read them.
- Documents are read from the installation folder, usually C:\Program Files\HomerView, which is where the installer puts them. The lookup tries there first, then the add-on's own copy, so it works whether HomerView was installed or is being run from source.
- Two mechanisms had been doing the same job. One opened the shipped web page; the other rendered the Markdown afresh every time. The guide and the history used the second, the read me used the first, and only one of them was checked when a document was renamed. Everything now opens the shipped page, which is the one pandoc made and the installer placed.
- About is the exception, and stays a dialog, because it is not a document: it is built from what the program knows about itself.
- Removed two commands that duplicated others. Open User Guide and Open History did what User Guide and History of Changes already did.

# Version 1.42.2

- The add-on was packaging a document the project no longer generates. HomerView.htm was renamed to HomerView.htm in 1.42.0, but unzipping a new version over an old folder adds and replaces without ever removing, so the old name stayed behind and was packaged with the rest.
- The build now clears any document in the add-on's doc folder that is not one it generates, and says which it removed. Nothing else in the folder is touched.
- This is worth stating as a general point about the zip: it is a set of files to add, not a picture of what the folder should contain. Anything renamed or dropped has to be deleted by hand, or by a build that knows what belongs.

# Version 1.42.1

- Fixed the build stopping without saying why. The check added in 1.41.1, that every module on disk is inside the built add-on, referred to a variable that was never defined. PowerShell passed nothing to the archive reader, the script died inside that call, and the log simply stopped after the version line.
- The check now names the file it reads, ignores __pycache__ on the disk side, and warns rather than stopping if it cannot run. A check that fails should not fail a build that has otherwise succeeded.
- Tidied .gitignore, which had grown by accretion. Four log names were listed individually under a pattern that already covered them, and two more entries named files that no longer exist. Twenty-eight patterns became twenty-two, grouped by why rather than listed flat, and there is now a note saying the built add-on is tracked on purpose so nobody adds a line that excludes it.

# Version 1.42.0

- Rewrote the documentation from scratch rather than editing it again, and moved to the file names the other Homer Tools use.
- ReadMe.md is the short introduction and quick start. HomerView.md is the full guide. Developer.md says how to build it. History.md is this. Announce.md is the three-paragraph description, with plain-English links to the project and the installer.
- Every one of those also comes as a web page with the same name, converted by pandoc, which HomerView itself can open.
- Everything is written for a ninth-grade reading level, because NVDA's users are spread across far more of the world than JAWS's, and many of them read English as a second language.
- The start page now lists eight free sites rather than five, each in two sentences. Project Gutenberg, the Internet Archive and Mastodon join it; all three meet the test, adapted for what they publish.

# Version 1.41.1

- Renamed buildAll to buildHomerView, for consistency with the rest of the Homer Tools.
- The build logs showed four things worth fixing, and the first was the plainest: the setup script was checked after the installer had been compiled.
- Neither log recorded the environment.
- The version came out of the installer's version resource padded, because a version resource is a fixed-width.
- Two checks were missing that the logs made obvious by their absence.

# Version 1.41.0

- Plain F1 is left to Microsoft Edge, which uses it for its own help and which HomerView does not supersede.
- A JAWS default is now preferred where one is free, because a blind Windows user has had those in their fingers for years.
- Several bindings moved to EdSharp's.
- Say Url returns to Alt+U, which was never arbitrary: U is the first letter of url.
- Read Rest is gone, and its key with it.

# Version 1.40.0

- Every command now has a name of at least two words, a description written the way EdSharp writes them, and a key or an explicit place in the Alternate Menu.
- Descriptions are present tense, lead with a verb, and end with a full stop.
- Keys now follow the first letter of the first word where that letter is free, and the first letter of the second word where it is not.
- Several bindings changed to obey that rule.
- Extract Main Content moves to Shift+F9, which is the best mnemonic in this release: F9 is Edge's own reading.

# Version 1.39.3

- The history rewrite worked and freed nothing, and the reason was one line.
- git filter-branch keeps a backup reference to the old commits for every reference it rewrites.
- Every backup reference is now removed rather than the one, and the remote-tracking references with them, since those still name the old commits until the next fetch and are rebuilt.
- The result is now checked before the push rather than only after it.
- Testing this needed a real remote, because the failure cannot happen without one: the second backup reference only exists when there is a remote-tracking reference to rewrite.

# Version 1.39.2

- The first real run of tidyRepo.py did most of what was wanted and left two things wrong, both of them faults in the script rather than in the repository.
- It reported that nothing oversized remained in the history when fifteen copies of the installer, twenty six megabytes each, were still there.
- It also left three source modules out of the repository.
- Adding files stages them, and the history rewrite refuses to run with anything staged, which is the same fault that appeared when untracking staged them.
- Tested against a repository built with fifteen distinct copies of a twenty six megabyte installer and three untracked source files: three hundred and ninety megabytes of history reduced to twenty.

# Version 1.39.1

- tidyRepo.py now commits outstanding work rather than refusing to run.
- The commit message names the version, read from the manifest, because a repository's log should say what each commit was.
- Use minus minus stash instead to set the changes aside rather than commit them, and minus minus message to give the commit a message of your own.
- Testing that change found a fault in it: committing with add minus A swept in the script's own.
- That check earning its keep is the point of having it.

# Version 1.39.0

- pandoc is no longer packaged with HomerView.
- The fetcher tries three things in the order most likely to work: a copy already on the.
- Added tidyRepo.py, which takes pandoc out of the repository's history, untracks development files that arrived through git add minus A, and pushes.
- On why that is one script rather than four: the HomerScribe clean-up took four and several.
- It describes rather than acts unless given minus minus do it, refuses to run with uncommitted changes to tracked.

# Version 1.39.0

- Pandoc is no longer packaged.
- It is ticked by default because the reader who needs pandoc is the reader who cannot tell in advance that they do: they find out when an ebook will not.
- Added tidyRepo.py, which tidies the folder and the repository in one run.
- It surveys everything before acting, and that is the whole design.
- Four faults were found by rehearsing it against a repository built to look like this one, each of which would have cost a round.

# Version 1.38.0

- Ported the Homer shared classes from C# to Python, so the same conveniences are available in both languages and a program can be read in either without translating as you.
- On the structure: the C# original is a namespace reached with using Homer, and Python needs no namespace keyword because a package already is one.
- Added homer.util, which had no Python equivalent at all: sizes as a person would say them, singular and plural.
- Completed the Lbc text control key family, which the Python side had only part of.
- Added the line operations to multi-line fields, which is where the C# LbcTextBox earns its keep: Alt+Shift+O sorts, Alt+Shift+Z reverses, Alt+Shift+K removes repeats, Alt+Shift+N numbers, and Control+Shift+Enter removes blank lines.

# Version 1.37.0

- Three more faults from the independent review, all confirmed against the code and all about behaviour under load rather than features.
- Stopping now stops.
- Finding the page being read no longer costs the full timeout for every unresponsive tab.
- The test that runs for every object NVDA creates is silent for the common case.

# Versions 0.1.0 to 1.36.1

These are the releases that built HomerView: the link to the browser, the page
commands, the accessibility testing, the document conversion, the Alternate Menu
and the installer. Between them they added most of what the guide covers.

Two themes run through them.

The first is the keyboard. Early releases took keys that NVDA or Edge already
used, and each one had to be given back. The rule that came out of it is in
HomerView.md. No HomerView command takes a key NVDA uses on either layout. An Edge key
is taken only where HomerView does everything Edge did with it and more.

The second is saying what happened. Several early commands failed in silence,
which is the worst way to fail. A command that cannot run looks exactly like a
broken one. Commands now say why they did nothing, and the Alternate Menu lists
only what can run right now.


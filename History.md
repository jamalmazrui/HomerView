---
title: HomerView History of Changes
author: Jamal Mazrui
---

# About this history

What changed, newest first. Written the way you would tell somebody, not as a
list of commit messages. The reasoning behind each change is in the code, where
it belongs. This is the short version.

# Version 1.48.3

- Fixed the JAWS script so that it compiles. Its functions declared a return type after the parameter list, which is how most languages write it and is not how JAWS Script does: the type goes before the word Function. Every function in the file had it the wrong way round.
- The installation was copying the scripts into Notifications and VoiceProfiles as well. Those sit beside the language folder but are not script folders, so the files went where nothing would ever read them, and both the work and the log were three times longer than they needed to be. Only folders named with a three letter language code are used now.
- Worst of the three: the installation reported a successful compile for every folder while the compiler had rejected the source in all of them. It checked whether a file had appeared, and one had, because scompile writes a small stub even when it refuses the source. It now reads what the compiler actually said, and treats a suspiciously small result as the stub it is.
- That is the same fault this project has had several times over: checking that a step ran rather than that it worked. It is now checked the other way in every step of the JAWS installation.

# Version 1.48.2

- The JAWS installation now always writes its log to C:\temp\HomerView\installJawsScripts.log, and says so on screen before it starts.
- A fixed path on purpose. A log whose location depends on which user ran it, or on whether a folder could be created, is a log nobody can find, and that is what happened: a whole installation ran, said something went wrong near the end, and left nothing behind to say what.
- It is run through a small wrapper rather than by PowerShell directly, and the wrapper redirects everything into that file. That catches what the script itself never could: if PowerShell refuses to run it at all, because of an execution policy or a blocked file, the script never starts and so never writes a line. The wrapper is outside that and records it anyway.
- The window now stays open until a key is pressed, and prints the whole log before it waits. Nothing scrolls away unread.

# Version 1.48.1

- Fixed the installer failing with a rights error about a log file. The two scripts it runs on the last page, for the JAWS scripts and for pandoc, each wrote a log beside themselves, which after installation means inside Program Files. That folder is read only without elevation, and both scripts deliberately run as the ordinary user, so the very first line failed before either had done anything or said why.
- The rule elsewhere in this project is that a script logs beside itself, and this is the exception that rule always had: a script installed under Program Files cannot write there. Their logs now go where HomerView's own logs go, in the user's local application data, and each is named for when it ran.
- Neither script now stops if the log cannot be started. Losing the record is a nuisance; losing the installation is a failure.
- The pandoc installer now checks that it can write to the installation folder before downloading, rather than fetching two hundred megabytes and then finding it has nowhere to put them. If it cannot, it says which command to run from an elevated prompt.

# Version 1.48.0

- Fixed Log to Clipboard, which failed for a tester with an access violation writing to address zero. The cause is a trap that catches everyone once. Python's ctypes assumes a Windows function returns a thirty two bit integer unless told otherwise, and GlobalAlloc and GlobalLock return sixty four bit handles and pointers. The top half of each was being thrown away, so the handle was not a handle, locking it returned nothing, and copying bytes to nothing is what raised. Every one of those functions now has its types declared, and each result is checked before it is used.
- Fixed two commands in the Alternate Menu that could not run. User guide and History of changes still named scripts that were removed four releases ago; the menu warned about it in the log and offered them anyway. They now point at the commands that do the same job, and the menu refuses to publish a command with no script rather than offering one that does nothing.
- The JAWS installation no longer touches default.jkm. It merged one line there, to give launching a key that works everywhere, and that was not worth the risk: a copy of that file in the user settings folder can shadow the factory one instead of adding to it, which would cost the user every built-in JAWS binding. The launch command is reached from the Start Menu shortcut, or from a key assigned in JAWS Keyboard Manager, which is the supported way and leaves the user's settings theirs. An installation made by an earlier version is cleaned up on removal.


- Fixed the installer failing to compile. The uninstall entry that removes the JAWS scripts used runasoriginaluser, which is a flag for the install section and not for the uninstall one. Inno Setup rejects a flag it does not recognise rather than ignoring it. The two sections look similar enough that the mistake is easy to make.
- The build log now carries what Inno Setup actually said. It printed its complaint to the console while the log recorded four words, so the one log a person uploads said that something had gone wrong and nothing about what. That is the opposite of why the log exists.
- The checks that run before Inno Setup now know which flags each section accepts, so this class of mistake is caught by the build rather than by the compiler.

# Version 1.47.0

- HomerView now supports both major screen readers from one installer. The last page offers the NVDA add-on and, separately, the JAWS scripts, and each checkbox appears only when that screen reader is actually installed.
- The JAWS scripts are compiled in place, once for each JAWS version on the machine, with that version's own compiler. A script binary built by one year's compiler is not reliably loaded by another year's JAWS, which is why they are not built once and copied.
- The installation runs as the ordinary user rather than elevated, because JAWS keeps its settings under the user's own roaming application data. An elevated run would put everything in the administrator's profile, where the user would never see it.
- One line is merged into default.jkm for the launch key, since launching cannot live in the browser key map: before HomerView runs there is no browser window. The original file is kept beside it, because a user's default key map may hold years of their own work.
- Added HomerViewBridge.exe, the piece JAWS scripting cannot supply for itself. JAWS cannot open a WebSocket, which is where every browser command that reads or acts on a page travels, so the bridge holds that side and the scripts read its answers. It needs nothing registered.
- buildHomerView now builds the bridge as well, so one script and one log cover the whole build.
- On what the JAWS scripts deliberately do NOT do: JAWS already moves to a declared main region, says the web address, lists headings, links and form fields, and finds text. HomerView on NVDA has its own versions of those only because NVDA lacks them. Six commands are bound, and they are the ones nothing else has.

# Version 1.46.2

- Fixed something the move to a logs folder would have broken. Nine places asked for the log file's parent folder when what they wanted was HomerView's own folder, and until the logs moved into a subfolder those were the same thing. Left alone, the history database and the browser profile would have moved into the logs folder with them, and an upgrade would have looked to a user like losing their browsing history.
- HomerView's folder is now named directly rather than worked out from where a file happens to sit, which is what let the two drift apart in the first place.

# Version 1.46.1

- Log to Clipboard moves to Control+Shift+L. Alt+Control with a letter, and Alt+Control+Shift with a letter, belong to Windows desktop and start menu shortcuts, which a user may have set for themselves; a program that overrides one is taking something that was not its to take. That convention is now written down with the other rules about choosing keys, so it will not be broken again by accident.
- Your user name and computer name are now taken out of the log as it is written. Every path reads %USERPROFILE% or %LOCALAPPDATA% rather than naming you, so the log still says where a file was without saying whose machine it was on.
- That happens at the last moment before a line is written, rather than at each of the several hundred places that log a path, because one of those places would be forgotten.
- The log now opens by saying what it holds and who sees it: that HomerView never sends it anywhere, that your name has been taken out, and that it does record the addresses of pages you opened and text you searched for, since most faults cannot be explained without them. Read it before sending if that matters for what you were doing.
- The guide has a section on the same, because a user deciding whether to share a log should not have to take anybody's word for what is in it.

# Version 1.46.0

- Each session now writes its own log, named for when it started, in a logs folder inside HomerView's own. A problem reported an hour later still has the log from when it happened, and the log being read is never the log being written to. The thirty most recent are kept.
- The log is written with a byte order mark and Windows line breaks, so it opens correctly in Notepad and EdSharp, and each line is flushed as it is written. A buffered log loses its last few lines exactly when something has gone wrong, which is when those lines are the ones worth having.
- Added Log to Clipboard on Alt+Control+L. It puts the log on the clipboard as a file rather than as its name, so pressing Control+V in an email message attaches it instead of typing the path into the message.
- That is a different clipboard format from ordinary copying: the one Windows Explorer uses when you copy a file. Anything that accepts a dropped file accepts it, so File Explorer will copy the log into a folder the same way. The path also goes on as plain text, so a field that wants letters still gets them, and neither program has to know what the other wanted.
- The code that does it takes any list of paths rather than only the log, because the next thing worth attaching will not be a log.

# Version 1.45.0

- The guide now contains everything a user needs, and does not send them to another file for any of it. What HomerView is for, what you need, how to install it, a first half hour that goes well beyond the quick start, every command, and the licence. Nothing from the developer notes or the history is in it, because it is a guide for people using HomerView rather than building it.
- Added that first half hour: opening a page and exploring it, reading it, finding in it, asking what is behind a link before following it, extracting and saving, opening a document as though it were a page, testing for accessibility and reporting what you find, and asking HomerView to look something up.
- The whole command list is now in the guide as well as in Hotkeys.md, because a guide that leaves out the keys is not a full guide for somebody reading by ear. The standalone file uses one heading level higher, since it is a document rather than a section.
- Both are generated from one grouping in the code, so the list in the guide, the file beside it, and what Alt+Shift+H builds inside HomerView cannot disagree.
- Commands are grouped by what you are trying to do and sorted by name inside each group, so a half-remembered name can be found without reading the group twice.
- Renamed hotkeys.md to Hotkeys.md, to match the other documents.
- Checked the reading level of every document, which had not been done for all of them. All six are at or below ninth grade: the guide and the read me are near fifth, the hotkey list is below fifth, and the history and announcement, the two with the most unavoidable jargon, are in the eights.

# Version 1.44.1

- The build log named every file it packaged, one line each. That was harmless when packaging had a log of its own that nobody read, and became sixty-six lines of successful file names in the one log a person now uploads, pushing everything worth reading to the bottom. It is a summary now: how many modules, how many documents, and the manifest.
- The names are still gathered, and they are printed when the count check fails, which names the module that was left out. That is the only time they tell anybody anything.

# Version 1.44.0

- One build script now, and one log. Packaging the add-on used to be a separate program that buildHomerView called, which meant two logs for one build, and the reason for a failure could be in whichever of them nobody had been asked for. Nothing about zipping a folder needed its own script.
- The previous release added machinery to fold the second log into the first when the add-on build failed. That was solving the wrong problem: the packaging step has never been where anything went wrong. Merging the two removes the problem instead of managing it.
- Removed buildAddon.cmd and buildAddon.ps1, and the lines in the installer and the clean script that tidied away a log which is no longer written.
- The .cmd that calls the .ps1 stays, because that is how a PowerShell script is run from a command prompt and not a second program in any real sense.

# Version 1.43.2

- buildHomerView.log is now enough on its own. When the add-on build fails, the reason used to be in buildAddon.log and this log said only that something had failed, so reading it meant asking for a second file. The last lines of the other log are now folded in, with the exit code.
- On success it records how large the add-on is, so the ordinary questions can be answered from one log.
- If the add-on build fails before it writes anything at all, that is now said in as many words, rather than leaving a reader to wonder whether the log is missing or was never written.

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


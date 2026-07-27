# History of Changes

## 1.24.0

- Modifiers are now written in alphabetical order everywhere a person reads them: Alt, Control, NVDA, Shift, Windows. So Alt+NVDA+F10 rather than NVDA+Alt+F10, and Alt+Control+Accent rather than Control+Alt+Accent.
- The order is arbitrary and that is the point. Any fixed order would do; what matters is that the same combination always reads the same way, so two lists of keys can be compared without normalising them first, and a reader hears Alt+Control+Shift in that order every time rather than in whatever order the author happened to type it.
- Key names now follow Freedom Scientific's, as JAWS writes them, even though these keys are bound in NVDA. A blind Windows user has read JAWS key names for thirty years, and DownArrow, Accent and SemiColon are what they expect to hear. So the grave accent key is Accent rather than Grave, the semicolon is SemiColon, and ScrollLock, NumPadDelete and the arrow keys are each one word.
- This governs only what a person reads. NVDA's gesture identifiers are unchanged, because those are what the binding needs.
- Added a section to the developer notes setting out both conventions and listing every key whose Freedom Scientific name differs from NVDA's, so anyone reading one and writing the other has the translation to hand.

## 1.23.1

- Control+Shift+F4 now keeps only the tab being read, which is what the command says it does. The previous release also kept the oldest tab, on the reasoning that it was a safer margin; it was not worth it, because one surviving tab is all the browser needs to stay running, and a command that quietly leaves an extra window behind is worse than one that does what it says. Full function is preserved either way and NVDA+Alt+H is never needed again.
- The one case still guarded is no tab reporting itself as current, which can happen for a moment after a page loads. The oldest is kept then, since closing everything on a guess would end the session.
- Shift+F4 now speaks the tab titles rather than showing them in a box. The question it answers is only what is open, and the reader is in the middle of something and wants to stay there. F4 is the command for when they want to act on the answer.
- Control+F4 is left to Microsoft Edge, which closes the current tab with it, and the gap in the family is now marked as deliberate so that nobody later fills it.
- Corrected one place in the user guide that still named Alt+F10 for the Alternate Menu, which has been NVDA+Alt+F10 alone since 1.14.0. The announcement and the quick start were already right.

## 1.23.0

- Added the Homer window list on F4. It offers every HomerView tab by name and switches to the one you choose. A reader who has run a report, extracted an article and opened a document has four tabs and no easy way to say which is which: Control+Tab cycles blind, and the browser's own tab list is a strip of buttons rather than a list.
- Shift+F4 says the names without opening anything, for when the question is only which tabs are there.
- Control+Shift+F4 closes the tabs you are done with. It keeps two whatever happens: the one being read, which is what the command promises, and the oldest, which is the tab the browser started with. The browser exits when its last tab closes, and with it go the debugging connection and every HomerView command, so a convenience that can turn the program off is not one.
- When no tab reports itself as current, which can happen just after a page loads, the oldest is kept instead. Closing everything on a guess would be the worst outcome available.
- Only HomerView's own tabs are listed, and developer tools windows are left out.
- On taking F4: Microsoft Edge uses it to select the address bar, and Control+L and Alt+D both do the same thing. This takes the least used of three ways to do one thing, and nothing is lost.

## 1.22.0

- Each lookup now presents an Lbc dialog with a field for each thing it needs, built from what the lookup declares rather than from one box the user has to pack several values into. The exchange rate asks for the currency to convert from, the currency to convert to, and an amount. The postal code asks for the code and the country. The weather asks for the place, how many days ahead, and which temperature scale.
- Squeezing two values into one box saved a line of code and cost the user a guess about the separator every time they used it.
- Fields that have usual values offer them on F4: currency codes, country codes, how many results, how many days. Every field remembers what was last typed in it.
- Results come back as sections rather than as a flat list, so a page can carry real structure. A blank line between results becomes a separate item, which is what lets a reader move through them one at a time rather than through one long run of text.
- Where the answer goes is decided by whether a message box can still be read at a glance. A definition or an exchange rate fits one, and Control+C copies the whole of it. Anything longer opens as a page in the browser, which has headings to move by, can be searched with Control+F, and can be saved.

## 1.21.1

- Added three lookups drawn from the biblio program, all of which need no key and none of which had been included.
- Wikidata answers with structured facts where Wikipedia answers with prose, so a date of birth or a founding year comes back as a value rather than as a sentence to be read through. It is the same project and just as free.
- Google Books is offered alongside Open Library because the two disagree usefully. Open Library is stronger on older and library-held books; Google Books is stronger on recent and self-published ones. A reader looking for a particular title is better served by being able to ask both.
- DuckDuckGo's Instant Answer service gives a short factual answer to a question. It needs no key, and its answers are largely drawn from Wikipedia. One caveat worth stating: DuckDuckGo's search service is proprietary, which is why it is not listed on the HomerView start page. Calling a free service is a different question from recommending a company, but anyone who would rather not call them at all can remove the entry from webUtilities.py.
- Fourteen lookups are now offered.

## 1.21.0

- Added Look Something Up, on Alt+Q in a page and NVDA+Alt+Q anywhere, and in the HomerView menu. Eleven lookups: define a word, find related words, search Wikipedia, find a place, get a weather forecast, find books, check an exchange rate, list recent earthquakes, find recent research papers, ask whether a page is in the Internet Archive, and look up a postal code.
- Every one uses a service that needs no key, no account and no payment.
- On the uploaded WebClient scripts, which date from about 2009: most of what they called is gone. Outside.in, NextStop, TweetMeme, LetsBeTrends, the free WhitePages and ZoomInfo tiers, BigHugeLabs and the old Google AJAX endpoints have all closed or now want a key. That is not decay so much as a change of business model. In 2009 a public API was how a company got attention; by about 2015 it was how a company got paid, and the free tier became a key, then a quota, then a credit card. ProgrammableWeb, which catalogued that world, shut down in 2022 after seventeen years.
- What survives without a key follows a clear pattern, and it is worth naming: it is funded by somebody who is not selling the data. Governments, universities, libraries, museums and volunteer projects. Wikipedia, OpenStreetMap, Open Library, the European Central Bank, the United States Geological Survey, arXiv, the Internet Archive. That is also, as it happens, the data most worth having.
- Requests identify this program by name and pause a second between calls to the same host. Nominatim's usage policy asks for both by name; the others would ask if they said. The pause is not politeness for its own sake. These are shared services with no revenue from us, and a program that hammers one is why the next one asks for a key.
- A short answer appears in a message box, which Control+C copies whole. A long one opens as a page, which can be searched and saved.

## 1.20.0

- Compared what JAWS reaches with its quick navigation keys against what NVDA reaches with its browse mode keys, and patched the two genuine gaps.
- Most of the apparent differences are naming rather than absence. The divider JAWS moves to with Z is what NVDA calls a separator, and S already goes there. The JAWS edit box is NVDA's edit field on E; the JAWS form control is NVDA's form field on F. NVDA also reaches several things JAWS does not, including landmarks, links as a class, block quotes, annotations and spelling errors.
- The first real gap was the main content region, which JAWS reaches with Q and NVDA cannot reach directly at all. HomerView had already filled it with J, and with Shift+J for a page that never said where its main content is.
- The second was moving by the kind of element you are on, which JAWS does with S for the same kind and D for a different kind. Neither has an NVDA equivalent, and neither needs you to know what kind of thing you are on first, which is what makes them useful on a page whose shape you do not yet know. Both are now in HomerView.
- They are on Z, which is the last letter NVDA leaves unassigned: Z and Shift+Z for the next and previous element of the same kind, Alt+Z and Alt+Shift+Z for a different kind. One key family rather than two, since S and D are both spoken for in NVDA.
- The quick start and the announcement now name the address command, both main content commands, and the two new movements.

## 1.19.0

- The page summary now describes only what is visible. Regions and headings that are in the markup but not on screen are no longer collected, and the note about text carrying aria-hidden is gone.
- The reasoning is worth recording, because the previous behaviour was defended as a feature. Web page frameworks routinely keep markup in the document that they are not currently showing: a menu nobody has opened, a panel behind a tab, a template waiting to be filled. None of that is suspicious, none of it is a fault, and listing it buries the regions a reader will actually meet under regions nobody will. This is the same judgment Deque's axe makes, which reports a violation only against an element a person could reach.
- What remains in that section is what is genuinely visible and genuinely absent from the reading order: a consent banner covering the page, a bar pinned to the window, an open dialog, media set to play by itself, live regions that may announce on their own.

## 1.18.2

- The quick start now opens with what you need before it tells you what to press: a link to download NVDA, which is free, and the fact that Microsoft Edge comes with every modern version of Windows and is therefore already on the computer. Someone deciding whether to try this should not have to work out what it will cost them in downloads.
- It also says plainly that HomerView starts its own copy of Edge with its own settings and leaves the usual browser alone, which is the first worry anyone has on reading that an add-on starts a browser.
- The converters are listed as optional, needed only for opening Word, Excel, PowerPoint, PDF and ebook files, so nobody thinks four programs must be installed before anything works.

## 1.18.1

- Added two introductions to the quick start, one for each kind of reader arriving at it.
- The introduction for JAWS users lists the JAWS commands that are here on the keys JAWS uses, says where a key had to move and why, and names the two places HomerView deliberately differs: the page summary reads the page itself rather than asking a language model, and reported values are spoken without a label because that is NVDA's habit, with the JAWS habit available as a setting.
- The introduction for NVDA users says where to find HomerView in the places an NVDA user looks: the Tools menu, the Settings dialog, and one category in Input Gestures with a description on every command. It also says plainly that browse mode is untouched, because that is the first thing an experienced user will want to know.

## 1.18.0

- Dropped the F12 and Control+F12 alternatives for saving and opening. Control+O and Control+S now do everything the native commands did and more, so the function keys were buying nothing and F12 belongs to Microsoft Edge's developer tools. Control+Alt+S still saves, for anyone who learned it.
- Added the Homer grave accent family, taken from edsharp.jkm and kept in the same shape because it is easy to remember and easy to reach. Control+Grave speaks faster, Control+Shift+Grave slower, Alt+Grave louder, Alt+Shift+Grave softer. Punctuation switches between all and none on Control+Alt+Grave, which differs from EdSharp only because HomerView does not use NVDA's modifier for page commands. Shift+Grave reports all three settings.
- Punctuation toggles between the two ends rather than cycling four levels, which is what EdSharp does and for the reason a reader would give: the choice that matters is between reading prose and reading a web address, where every character counts.
- All of it goes through NVDA's own speech configuration rather than any synthesiser, so a change made here is the change the user would have made in NVDA's settings, is saved with their profile, and survives a restart. A command that adjusted something NVDA did not know about would disagree with the settings dialog the moment it was opened.
- None of the six keys is used by Microsoft Edge, by NVDA or by Windows.

## 1.17.0

- Scroll Lock now starts continuous reading, and stops it. One key for both, which is the friendlier form of what NVDA does with NVDA+DownArrow to begin and Control to stop: two keys and a modifier for what is really one idea.
- Scroll Lock is chosen because nothing else wants it. Windows gave it a meaning in 1981 and almost nothing has honoured it since; Microsoft Edge does not use it, NVDA does not bind it, and no browse mode command touches it. It is also large, isolated and unlikely to be pressed by accident, which is what a start and stop key should be.
- This does not replace Read All on Alt+F8, and the two are not the same thing. Read All says the whole page as one utterance and leaves the cursor alone, which is Homer's meaning. Continuous reading moves the cursor as it goes, so a reader who stops is where they stopped.
- Confirmed the Homer help trio, which was already in place: F1 opens the user guide, Alt+F1 the About box, and Shift+F1 the history of changes.
- The command list now writes Scroll Lock, the arrow keys and Numpad Delete as people write them rather than as the gesture spells them.

## 1.16.0

- Control+O and Control+S now belong to HomerView, and both were earned rather than taken. The test set for this was the right one: a native command may only be replaced if nothing that worked before stops working.
- Opening now passes to the browser any file it has no converter for, which is exactly what the native command did with it. Images, audio, video, JSON, source files and everything else Edge renders open as they always did, and what Edge cannot render it still offers to download. Word, Excel, PowerPoint, PDF, rich text, OpenDocument, EPUB and Markdown are converted first and read as web pages, which the native command could not do at all.
- Saving now offers a single file archive, which is what Edge's own Save Page As produces by default, so the format a user already relied on is still there. It is produced through the protocol rather than by driving the menu. Alongside it sit the eight HomerView adds: a web page, Markdown, plain text, a Word document, a PDF, an image of the whole page, the markup after script has run, and the accessibility tree.
- Both keys exist only while Microsoft Edge has focus, so Open and Save are untouched in every other program.
- The function key alternatives follow Microsoft Office rather than being chosen freely, because a user who knows one convention should not have to learn a second. In Office, Control+F12 opens and F12 saves as. Control+F12 therefore opens, which is a change from its previous meaning. F12 itself is Microsoft Edge's developer tools and is left alone, so saving takes Shift+F12, which is Office's own Save and is unassigned in Edge.
- Control+Alt+S still saves, for anyone who learned it.

## 1.15.0

- Added HomerView to the NVDA menu, under Tools, with items for launching the browser, listing every command, opening the quick start, the user guide and the history of changes, checking for a newer version, and About. This is one of the two places an experienced user looks before touching the keyboard, and it matters more here than for most add-ons: someone who has not yet learned a single key can start the browser and open the guide from a menu they already know how to reach.
- Added a HomerView page to NVDA's Settings dialog, which is the other place they look. It offers the three settings worth changing and lists every folder HomerView writes to, because where a program keeps things is a question users ask and a settings page is where they look for the answer. The panel reads and writes HomerView.inix rather than keeping a second copy, so a value changed here is the same value a person editing the file by hand would see.
- Both are removed when the add-on is unloaded, which is what lets it be reloaded or updated without leaving a dead menu item and a duplicate settings page behind.
- The manifest's description named four commands out of more than sixty and predated most of what the add-on does. It now describes what HomerView actually is and ends by naming the one key worth remembering.
- The author field carries a contact route, as the add-on store expects.
- The Help button on the add-on now opens the quick start rather than an older file left behind, and every shipped document declares its language.
- Checked every command against the conventions an experienced user relies on: all have a description, so input help speaks something useful, and all are in one HomerView category in Input Gestures, so they can be found and reassigned together. Every translatable string carries a translator comment.

## 1.14.0

- The Alternate Menu is on NVDA+Alt+F10 alone. The shorter Alt+F10, which worked only inside a HomerView page, has been removed.
- Brevity is usually the right call and here it is not. This is the command a person reaches for when they do not know what they are looking for. A key that answers in a page and does nothing in the address bar is indistinguishable, from the keyboard, from a key that is broken, and a discovery command that appears broken is worse than a longer one that never is. This project has watched that exact failure more than once, with a command silently out of scope and a tester reasonably concluding it did not work.
- The one key carries the NVDA modifier, so NVDA takes it before any program sees it. It works in the address bar, in a form field, in another application, and before Microsoft Edge has been started.
- Launch HomerView Edge is back in the menu. It was removed when the menu was thought to open only from a page, where launching had already happened. The global plugin is loaded from the moment NVDA starts, so the menu opens before the browser exists, and someone who has just found the menu should be able to start HomerView from it rather than being told to press another key first.

## 1.13.1

- Control+F and Control+F3 were the same command, so both asked for a regular expression and neither did a plain search. They are now distinct, as EdSharp has them: Control+F finds text without case sensitivity, Control+F3 finds a regular expression, and Control+Shift+F and Control+Shift+F3 do each backwards. F3 and Shift+F3 repeat whichever was last used. The two dialogs also ask different questions, so it is clear which kind of search is being started.
- Rewrote the list of commands on the start page so that each line begins with its key. Reading a sentence to reach the key is slower than reading the key first, and J for jumping to the main content was buried far enough into its sentence to look unassigned.
- The start page and the published command list now name Alt+F10 for the Alternate Menu before NVDA+Alt+F10. Both work; the shorter one should be the one a reader learns, with the longer named as what to use before the browser is running.
- On using W and Shift+W for Word Find: W is not free. NVDA uses it in browse mode to move to the next spelling error, and Shift+W to the previous. Word Find therefore stays on Alt+W and Alt+Shift+W. The letters still free in NVDA browse mode are J, Y and Z, and HomerView already uses J and Y.

## 1.13.0

- Brought the Python Lbc up to the level of the C# one, and every list in HomerView gained the result. Control+J asks for a substring, not case sensitive, and moves to the first item containing it; Control+Shift+J searches backwards; F3 and Shift+F3 repeat without asking again. The search wraps and the term survives closing one dialog and opening another, because someone who has just searched for the same thing twice should not type it a third time.
- Every Lbc control now answers the same chords, so a user does not have to remember which kind of control they are in. Control+C copies the current line or the current list item, Alt+C appends the same to the clipboard, Control+A selects all and says so, Control+Shift+A clears the selection and says so.
- Shift+F1 speaks the tip for whatever has focus, from any control rather than only a text field. A tip belongs where there is no room for it on screen, which for a screen reader user is everywhere.
- Added a check list for choosing several items, which is the accessible way to offer multiple selection: a check box on each item says whether it is chosen, where an extended-selection list box has nothing on the item that says so. Added a history box for a field that remembers what was typed before, and F4 opens a pick list on any field given one.
- Added named access to controls, so a dialog can be read and written by name rather than by remembering the order things were added, and an initial focus can be asked for.
- Added a shared version module to the toolkit, holding the comparison and the GitHub release lookup that DbDo, EdSharp and FileDir each wrote separately. Versions compare as numbers, because compared as text 1.11.0 sorts before 1.9.2 and upgrades quietly stop being offered.
- The Alternate Menu list is searchable with these keys, and its label says so.

## 1.12.1

- Elevate Version moved from F11 to Control+F11, and F11 is left to Microsoft Edge.
- The reason is not that full screen is valuable to a screen reader user, because entering it is not: hiding the address bar and the tab strip saves screen space, which is worth nothing to someone who is not looking at the screen, and it removes those controls from the accessibility tree, which is a small loss rather than a gain.
- The reason is that F11 also leaves a full screen that a page imposed. A video site, a presentation, a map or a kiosk page can put the browser into full screen through the Fullscreen API without being asked, and while Escape usually leaves, a page that handles Escape itself can swallow it. F11 always works. Taking it would mean that on the day a page traps someone, the key that frees them opens a HomerView update dialog instead. A command used a few times a year is not worth that.
- Control+F11 is unassigned in Microsoft Edge, in Windows and in NVDA, and it sits beside Control+F12 for Save Page As, which makes the pair easy to remember. NVDA+Alt+F11 still works anywhere.

## 1.12.0

- Added Elevate Version, on F11 in a page and NVDA+Alt+F11 anywhere. It asks GitHub what the latest release is, compares it with what is running, and offers to download and install it.
- The design follows DbDo's, which was the fullest of the three and had the sharpest reasoning behind each step. The version is looked up through the releases API, falling back to fetching the releases page and reading the tag out of the address it redirects to, because the API rate limits unauthenticated callers and the redirect does not.
- Being already current does not end the command. It offers to install the same version again, which is what someone wants when an installation did not take. That is not hypothetical: a tester ran an older add-on for a whole session because an installer checkbox was unchecked, and this is how he could have repaired it himself.
- Running a version newer than the public release is reported rather than treated as a fault, and no downgrade is offered. That is the normal state of the developer's own machine.
- Versions are compared as numbers rather than as text, so 1.11.0 is correctly newer than 1.9.2. Compared as text it is not, and this project passed that point some releases ago.
- One thing differs from DbDo, and it is the point of the command here. DbDo downloads an installer and lets it take over. HomerView's program files matter less than its add-on, because the add-on is what NVDA loads and until NVDA has it nothing works. So the add-on package is downloaded and handed to NVDA, which shows its own confirmation and restarts itself. The installer is named afterwards for the documentation and the converters.
- On the key: Homer binds Elevate Version to F11, and Microsoft Edge uses F11 for full screen. F11 is therefore bound only inside a HomerView page, where a screen reader user rarely wants full screen, and NVDA+Alt+F11 is offered as a key that shadows nothing anywhere.

## 1.11.0

- NVDA+Alt+H now looks for a HomerView window before doing anything else, and brings it to the front if it finds one. The command means one thing to the person pressing it, namely put me in HomerView, and what that requires differs; it is now tried in order of how much it disturbs. Activating a window that is already open is instant and loses nothing.
- When several HomerView windows are open, the one most recently in front is chosen. EnumWindows walks in z order, so the first window it offers is the one the user means.
- This works after NVDA has restarted. The browser's process identifier is written into the profile folder at launch, so a later session can find the window without needing a protocol connection, which is exactly the case that used to open a second window.
- If a window is found but its debugging connection has gone, HomerView reconnects quietly where it can, and where it cannot it says the window is open but commands will not work in it, rather than opening a second window nobody asked for.
- Only when no window exists at all does a browser start, and then the previous behaviour applies: the page the profile last had open, or the start page.
- The spoken result now matches what happened: a short acknowledgement for a window brought forward, and a plain explanation when Windows refuses to raise it or when the connection is missing.

## 1.10.0

- The installer proposes the Program Files folder again. It always did, but UsePreviousAppDir was set to yes, so on any machine where an earlier version had installed to C drive HomerView, the installer kept proposing that recorded path instead of the default and an upgrade never moved. It is now no; the directory page is still shown, so anyone who chose a different drive can choose it again.
- The session log and the history database moved out of the installation folder and into the user's local application data. A program folder should be written by its installer and read afterwards. Writing there at run time either demands administrator rights for ever or has the writes redirected somewhere the user cannot find, and the folder is per machine, so two people sharing a computer shared one log.
- Removed the permission grant that gave every user modify rights on the installation folder. That was solving the wrong problem: it traded a real security boundary for a convenience the correct location made unnecessary.
- Uninstalling no longer removes the log, the database or the settings. They are the user's data on the user's filesystem, and removing a program is not a reason to discard what it recorded.
- Added a section to the developer notes setting out where each kind of file belongs on Windows and why, and applying the same rule to 2htm, DbDo and urlFido.

## 1.9.2

- The checkbox that hands the add-on to NVDA is checked by default. It was unchecked in 1.5.1, and a tester who sensibly accepted every default went on running an older add-on for a whole session without knowing it, reporting faults that had already been fixed. Accepting the defaults must produce a working installation rather than a folder of files, and the reason is now written beside the line so it does not drift back.
- The welcome page and the finish page both say plainly that the program files alone do nothing, that NVDA will ask for confirmation, and that NVDA must restart before any command works.
- The page explorer no longer fails when a field arrives as a number or a string where a list was expected. Both ends of that script have been edited more than once, and a summary that fails entirely because one field changed shape is a poor trade. Every collection is now read through a conversion that accepts either.
- The Recently Opened list is a list rather than a table. The reader is using a screen reader, and moving through a list is quicker than four columns of which three are usually the same.

## 1.9.1

- Fixed a compile error in the setup script. SetupLogging was specified twice, because the 1.7.0 edit that minimised the wizard added it to the block it was rewriting without noticing the same directive already sat lower down. Inno Setup rejects a repeated directive rather than taking the last one, which is the right behaviour and caught it immediately.
- Fixed two Start Menu shortcuts that still pointed at documents renamed in 1.9.0, so they would have installed as shortcuts to files that were no longer placed. The group now offers the quick start, the user guide, the history of changes, the developer notes, installing the add-on, and uninstalling.
- Added a check to the build that reads the setup script and reports any directive specified twice or any file it references that does not exist. Both faults above would have been caught before compiling.

## 1.9.0

- Documentation now ships as four documents, each as Markdown and as a web page: README for a quick start, HomerView for the full user guide, History for what changed, and Developer for architecture and conventions.
- The user guide is generated from the commands themselves rather than written beside them, so it cannot drift from what the program does.
- Each document has a command in the Alternate Menu, and each is listed on the start page. Both open the web page in the HomerView window rather than handing it to the shell, which would give it to whichever browser is the default. That matters: a document opened in HomerView has every HomerView command available on it.
- The documents are copied beside the start page on launch, so the relative links on that page resolve.
- The installer places all eight files in the installation folder.

## 1.8.0

- Made it a rule that no HomerView command may take a key NVDA uses by default on either the desktop or the laptop layout, and applied it. NVDA+A was the one breach: it is unassigned on the desktop layout but is Say All on the laptop layout, and a user of that layout was losing Say All inside HomerView pages. Reporting the page address is now Alt+A in a page and NVDA+Alt+U anywhere.
- Added Alt+K, which asks which engine should test the page: Deque axe-core, IBM Equal Access, or both in turn. One key for one job leaves room for a third engine without another binding, and the choice is remembered.
- Added sentence and paragraph movement on EdSharp's keys, which NVDA leaves unassigned in browse mode: Alt with the up and down arrows for sentences, Control with them for paragraphs. As with NVDA's own navigation, the cursor stays where it was when there is nothing to move to.
- Added HomerView.inix in the roaming application data folder, holding preferences and the values last typed. A preference belongs with the user rather than the installation, so it survives reinstalling and needs no administrator rights. The inix format is used rather than JSON because someone may want to edit this by hand, and inix keeps their comments, blank lines and ordering when HomerView writes a value back.
- The find pattern, the last script and the chosen accessibility engine now persist between sessions rather than only within one.
- Renamed two commands whose purpose was unclear. Open Copilot is now Ask Copilot about this page, and its description says it copies the page text and opens the sidebar ready for Control+V. History is now Recently opened, and its description says it lists the pages and documents opened in HomerView so one can be found again.
- Removed the Control+F10 binding. It was the original suggestion for opening a document and was superseded by Control+O, which is Edge's own key for the same job and a strict superset of what Edge does with it.

## 1.7.0

- Renamed the two navigation commands to reinforce the letter that runs them: Jump to Main Content on J, and Jump to Probable Main Content on Shift+J.
- Launching now reopens the page the profile last had open, with its cookies and sessions, rather than the start page. The profile is persistent, so Edge has already recorded this in its own preferences; reading it there is better than keeping a second copy that could disagree with the browser. Set bReopenLastPage to False in edge.py for the start page every time.
- The log now continues rather than restarting when a new session begins within an hour of the last entry. Restarting NVDA to install a build, or reconnecting to a browser left running, is a continuation of what the user was doing, and splitting the log there loses the context that makes the second half readable.
- Results of several lines now appear in a message box rather than passing as speech: what a page holds, and how much text there is. Speech is gone the moment it is heard, while a box costs one key to dismiss and can be read again, and Control+C copies the whole of it including the title. A position is still spoken, because a box for three words would cost a keystroke and buy nothing.
- Reduced the installer to the fewest prompts that still let a user choose where it goes, following the pattern of the other Homer installers. The licence is summarised on the welcome page instead of occupying one of its own, the ready page is gone, and the add-on install is a checkbox on the last page rather than a task with a page behind it.

## What the user logs showed

- The user is on NVDA's laptop keyboard layout, where NVDA+A is Say All. HomerView binds NVDA+A inside its pages, so on that layout Say All is shadowed there. This is worth knowing before wider release.
- Control+F4 was pressed eight times to close report tabs, which is what prompted giving those tabs no history behind them in 1.6.0.
- Every document conversion succeeded: docx, pdf and rtf all converted and opened, with 2htm found in the shared Homer folder as intended.

## 1.6.0

- Fixed the page explorer, which failed every time with a type error. An earlier edit that removed character counts had replaced a value with the literal None and left it in a list that was later joined into a sentence. Both keys reach one implementation now.
- The Alternate Menu no longer lists the command that starts the browser. By the time the menu is open, it has already happened.
- The menu remembers the last command chosen and returns to it when reopened, so working through several commands does not mean walking the list from the top each time.
- A command with no key now shows only its name. Saying "none" told the reader nothing they could act on and sounded like something had gone wrong, which for a first-time user is worse than silence.
- The Invoke Script dialog now has Test and Help beside OK and Cancel. Test reads each line the way the runner will and reports the verb, the target and the value it found, so a mistyped instruction is caught before it clicks anything. Help explains what can be written, with an example, and says plainly that this is HomerView's own matching rather than a language model and that nothing about the page leaves the computer.
- A report opened in a new tab now has no history behind it, so Alt+LeftArrow has nowhere to go and Control+F4 closes that tab and returns the reader to the page they came from.
- The start page now applies a strict test: the thing itself must be free and open source software, not merely a company that publishes some. DuckDuckGo's search service is proprietary even though its apps are open, so it has been dropped. GitHub, LinkedIn and Grok fail the same test and are not listed. Wikipedia, SearXNG, Ollama, Mozilla and the GNU Project are.

## 1.5.1

- The add-on package now has a stable name, HomerView.nvda-addon, and the setup script references that. The version lives in the add-on's manifest, which is what NVDA reads, and in the installer's own AppVersion. Putting it in the file name as well meant two files had to be edited in step for every release, and forgetting either would break the compile for a reason unrelated to whatever had changed. A copy named for the version is written beside it, for release assets where the build number matters.
- Checked the installer's add-on step and it was correct. The shellexec flag is what makes it work: a .nvda-addon file is not executable, so Windows hands it to whatever is registered for that extension, which is NVDA. Without the flag Inno Setup would try to run it as a program and fail. The description now says the package opens in NVDA rather than merely opening, and the step is unchecked by default so nothing is launched without the user asking.

## 1.5.0

- Added LibreOffice and Calibre as converters, found rather than bundled, alongside pandoc and 2htm. Each format now has an ordered chain of tools, best first, and a format with no tool present says which one to install.
- LibreOffice handles the office formats and needs no Microsoft Office: docx, doc, xlsx, xls, pptx, ppt, rtf, csv and the OpenDocument set. Calibre handles ebooks. Pandoc handles epub, Markdown and OpenDocument text. 2htm now comes last for everything it is not alone in handling.
- 2htm drives Microsoft Word, Excel and PowerPoint through COM, so it needs Office installed and of matching bitness. HomerView now checks the registry before running it and, when Office is absent or is not the 64 bit edition, says so in a message box and points at LibreOffice, which needs no Office and is free. That turns a silent failure into a sentence a reader can act on.
- Added Word and Markdown to Save Page As. Markdown was already produced from the live document; Word is made by converting the page's markup with pandoc, since nothing in a browser writes Word directly.
- On distributing a converter without its application: it is not practical for either candidate. LibreOffice's own documentation states that headless conversion requires the full installation, and calibre's converter needs calibre's runtime and libraries in the same way. Both are also larger than pandoc rather than smaller, at roughly seven hundred megabytes and five hundred megabytes against pandoc's two hundred and twenty. Finding what is installed remains the right approach, and is what HomerView now does for all four.

## 1.4.0

- Save Page As, on Control+F12, now offers four more formats, all produced by the protocol rather than derived from the text.
- An image of the whole page, not merely the part scrolled into view. When a reader reports a problem and is asked what it looks like, this is the answer, and it can be attached to an email without describing anything.
- The page as a PDF, laid out as it would print: one file, fixed layout, readable by anything, and accepted by systems that will not take a web page.
- The accessibility tree as JSON, with every node's role and name and, for any node left out, the reasons why. Nothing else HomerView produces answers the question of why something visible on screen is absent from the reading order.
- The markup after script has run, which is neither what the server sent nor what View Source shows.
- The image and the PDF arrive as encoded text over the protocol and are decoded before writing, so a decoding failure is reported rather than left on disk as a broken file.
- Files this project creates now use .htm rather than .html throughout, including the generated reports and the start page.

## 1.3.0

- Added NVDA+Alt+P, which copies the page text to the clipboard, brings the HomerView window to the front, and opens Copilot in the Microsoft Edge sidebar. The text is ready to paste with Control+V, so a question about a particular page needs one key rather than four steps.
- The shortcut is sent through the Windows keyboard rather than the protocol. Control+Shift+Period is handled by the browser's own interface and not by the page, so a key dispatched into a page through the Input domain never reaches it. The window is raised first and given a moment to settle, because a keystroke sent into a window that is still arriving is simply lost, which looks exactly like the shortcut not working.
- Added bCopilotSupport in edge.py, on by default, which leaves background networking enabled because the sidebar needs it. It is the only switch Copilot requires beyond an account. Everything that keeps the first launch quiet is unchanged: the sync dialog, the promotional screens and the automatic sign-in stay suppressed, so signing in remains something chosen rather than something done to the user.
- The launch now records what these settings did, and warns plainly when Copilot support is on while sign-in is not allowed, which is the state in which Copilot opens and has no account.
- On using the default profile, which is what makes an account and existing logins available without signing in again: it is not possible, and the reason is a hard limit rather than a preference. Since Chrome 136 and the matching Edge release, the remote debugging switches are ignored outright when the data directory is the browser's default one. HomerView launched against the default profile would have no protocol connection at all, and every command in it would stop working.
- What the separate profile costs is exactly the thing being asked about: no sign-in, so Copilot has no account, sites ask you to log in, and a download behind a login wall fails. The answer is not to abandon the separate profile but to sign it in. It is a real profile that happens to live somewhere else, and once signed in it has an account, sessions, cookies, bookmarks and Copilot, while still permitting the debugging connection. Set bAllowSignIn to True in edge.py, delete the profile folder, launch, and sign in once.

## 1.2.0

- Alt+V is now Invoke Script: a multiline box where each line is one instruction, run in order. A single instruction is useful; a sequence is what makes a task repeatable. Sign in, accept the cookie notice, search for a term and open the first result is four instructions a reader would otherwise perform by hand every time.
- The box remembers the last script, so a sequence can be corrected and run again rather than retyped. Blank lines are skipped and a line beginning with a hash is a comment, so a script can be annotated and kept.
- A script stops at the first instruction that matches nothing, because carrying on after losing the thread would act on the wrong thing. The result opens as a page listing every instruction, what it acted on, and what happened.
- A single instruction still offers a choice when several controls could match, because there is a reader waiting to answer. A script does not ask, since the point of a script is that it runs.
- Added detection of a local model service on the loopback address, reported in the log. No model is required and none is used yet: this only records whether one is available.

## 1.1.0

- The Alternate Menu no longer lists the command that opened it.
- The page explorer no longer reports character or word counts. A reading time is worth knowing; the number of characters is not something a reader can act on.
- Go to Percent now accepts a change as well as a destination. Forty means go to that point, and the percent sign is optional. Plus ten or minus ten means move that far from where you are, which is the more common wish: knowing you are two thirds through and wanting a little further is ordinary, and working out that this means seventy two is not.
- Confirmed the F8 family, all four bound as intended: F8 marks the start of a selection, Shift+F8 completes it, Alt+Shift+F8 returns to the start, Control+F8 copies the whole page, and Alt+F8 reads it.

## 1.0.5

- Fixed the release failure. tagRelease reads the version from the built installer's version resource and looks for that installer in the repository root, but the setup script was writing it to a dist folder, where tagRelease was never going to look. The installer now lands in the root.
- The underlying reason it was missing at all is that nothing had compiled it. buildAddon.cmd builds the add-on package and stops there, so HomerView_setup.exe did not exist yet.
- Added buildAll.cmd, which does both steps in the order tagRelease expects: the add-on package, then the installer. It finds the Inno Setup compiler where its own installer puts it rather than asking for it on the path, checks that the installer was actually produced, and reports the version it read back from the file, which is the same version tagRelease will read. Run buildAll, then tagRelease.

## 1.0.4

- Fixed silent results from the Alternate Menu. The commands were not failing: the log shows Url reference and Say yield structure both running and producing their answers, and the user heard nothing.
- The cause is a collision. Closing the menu hands focus back to the document, and NVDA announces that document as it arrives. A command run in that same instant speaks into the announcement and is cut off by it. The log records the two events one after the other every time: the command's result, then a new document object and the overlay being inserted, which is NVDA processing the page regaining focus.
- A chosen command now waits for the transition to finish before it runs. That is the whole fix, and it costs about a third of a second.
- On which output belongs where, the rule this project now follows has three parts. Speech is for a short answer heard once and discarded, such as a position or a count. A message box is for a short set of facts worth keeping, because Control+C copies a Windows message box whole. A page is for anything long enough to search, save, or send. The failure here was not the wrong channel but the wrong moment: speech was correct for a count, and it was spoken into a gap where nothing could be heard.

## 1.0.3

- Fixed NVDA+A doing nothing without saying why. A command bound to the browse mode document exists only while that document has focus and is in browse mode. Pressed from the address bar, from a toolbar, or from inside a form field in focus mode, it never reaches the buffer at all: nothing runs, so nothing is spoken, and the key looks broken rather than inapplicable.
- NVDA+A is now bound a second time on the global plugin, where it is reached whatever has focus. That copy asks the browser rather than the buffer, so it answers from the address bar and from focus mode as well as from the page. It exists only while Microsoft Edge has focus, so it shadows nothing elsewhere, and it says plainly when HomerView has not been started.
- The log had already recorded this without anyone reading it correctly: of four NVDA+A presses, three reached the global plugin and never reached the buffer, while all five presses of J reached the buffer and ran. Two keys behaving differently in the same session is the signature of one of them being out of scope rather than broken.
- J needs no equivalent. It is navigation, which is meaningful only in browse mode, and in focus mode it correctly types the letter.

## 1.0.2

- Fixed the repository script, which stopped at the first question it asked. With ErrorActionPreference set to Stop, PowerShell turns anything a native program writes to standard error into a terminating error. git writes "No such remote 'origin'" to standard error, and that is not a failure: it is the correct answer to "is there an origin yet". Redirecting to null does not help, because PowerShell raises the error before the redirect matters.
- Every git call now goes through one function that lowers the preference around the call and judges the result by the exit code, as git intends. Each step also checks that result rather than assuming it worked, so a failure is reported where it happened instead of two steps later.
- The oversize warning now also says, once, that the push will be rejected if nothing is done about it. Warning at the top and then pushing anyway wastes the upload.
- Added .gitattributes, which declares line endings so Git stops guessing and stops warning. This project writes CRLF for everything a Windows program reads and LF for the few files other platforms parse, and saying so means a clone produces the same bytes the build expects on any machine. Executables and the built add-on are marked binary so Git never rewrites a byte of them.

## 1.0.1

- About now uses a standard Windows message box rather than a custom dialog. Windows message boxes support Control+C, which copies the whole of the box including its title, and every user of Windows already knows that. A custom dialog with a read only edit box does not: it needs Control+A first, and it is one more window whose shape has to be learned.
- That settles the rule for output, and it has three shapes rather than two. Speech for something heard once and discarded. A message box for a short set of facts worth copying. A page for anything long enough to search, save, or send. A version number does not deserve a tab; a scan report does not deserve a message box. Using the wrong one wastes the reader's time in a different way each time.
- Added output.info for short factual results, alongside output.show for reports, so the choice is made once per command rather than reasoned about each time.

## 1.0.0

First release.

- Added createHomerViewRepo.cmd and its PowerShell counterpart, which create the repository, connect it to GitHub, and push, writing createHomerViewRepo.log as every build script here does. It is safe to run more than once: each step checks whether it has already been done, so a second run adds what is missing rather than failing.
- Before pushing, it warns about any file GitHub will refuse. GitHub rejects a single file over 100 megabytes, and finding that out from a failed push is a poor way to learn it.
- Added .gitignore. Logs are excluded, because they say nothing a reader of the repository needs and are the file most likely to carry a local path. Generated output is excluded for the same reason. Executables are tracked deliberately, so someone who clones the repository can build the installer without hunting for pieces.
- pandoc.exe is the one exception, and it is a hard limit rather than a preference: it is well past GitHub's 100 megabyte ceiling. Track it with Git LFS or attach it to a release, and keep a local copy beside the setup script so the installer picks it up. The installer skips it cleanly when it is absent.
- The installer carries the repository tooling and .gitignore alongside the add-on, source and documentation, and places 2htm.exe and pandoc.exe in the installation folder, which is the first place HomerView looks for either.
- Quality pass across all thirty-nine modules: no duplicate definitions, no unfinished markers, no tabs, versions consistent across the manifest, the installer script, the readme and this file, and every file carrying the encoding this project uses.

## 0.38.0

- Added NVDA+Alt+L, which lists any kind of element on the page and says how many of each the page holds before you choose. Eighteen kinds are offered, and thirteen of them are kinds NVDA's own Elements List does not provide: tables, lists, list items, graphics, check boxes, radio buttons, combo boxes, edit fields, block quotes, frames, separators, annotations and embedded objects. Kinds the page does not contain are left out, so the chooser is short on a simple page.
- On copying the JAWS pattern of Insert+Control plus the quick navigation letter: it cannot be done. NVDA spends almost the whole of NVDA+Control+letter on its settings dialogs, so mirroring the pattern would break a dozen NVDA commands to gain a dozen HomerView ones. One command that asks which kind costs a single extra keystroke and breaks nothing, and it has the advantage of reporting the counts, which the JAWS keys do not.
- On the JAWS audio commands: NVDA already has them. Sound Split is on NVDA+Alt+S and sends NVDA to one ear and applications to the other, and the output device is chosen in Speech settings. Duplicating either would add a second way to do something NVDA does well.

## 0.37.0

- Alt+Delete now also answers on the numeric keypad's Delete, which is a different key identifier. Alt+Delete was already bound to report position, so the likely reason nothing happened is that the keypad key was pressed and did not match. NVDA's own equivalent is NVDA+Delete, which reports the position of the review cursor including the percentage through the document, so Alt+Delete duplicates a command NVDA already has rather than inventing one.
- The position report now leads with the percentage, which is the part a reader wants, with line and column following for precision.
- Added Control+Enter to submit the form you are filling in, from any field. This is the Lbc convenience carried onto the web, and for the same reason: in a dialog, plain Enter is swallowed by controls that handle it themselves, and a web form has the same problem. Enter submits from a text field but not from a text area, a list, or a checkbox, and a submit button at the end of a long page is a long way to tab.
- The submission is a real one. requestSubmit is used rather than submit, because submit bypasses the form's validation and never fires its submit event, so a page that checks its fields in script would never see the attempt and a required field left empty would be sent anyway. requestSubmit does what pressing the submit button does: it validates, it fires the event, and it refuses an incomplete form while showing the same message the user would have seen. An error about a missing field is the correct outcome, not a failure.
- A submitter is passed when one can be found, because a form can have several submit buttons that mean different things and the browser reports which was used. The focused field is followed through a shadow root, and a form built without a form element falls back to the nearest button that submits.
- Control+Enter exists only while Microsoft Edge has focus. A global binding would shadow that key in every program on the machine, which fails the standard set for taking a key that already does something.

## 0.36.0

- About is a dialog again rather than a page. Output has more than one right shape: a report is a document worth keeping and searching, so a page is right; About is a short set of facts someone reads and closes, so a message box is right. Making it a page meant opening a tab to learn a version number and then having to close it. It now lists the version, every folder HomerView writes to, whether each converter was found, and the connection state.
- Added Shift+J, which reaches the main content of a page that never declared any. J still refuses to guess, which is correct, and the guess now has its own key so the two are never confused. It tries the first heading past the banner and navigation, then the first heading at all, and says which rule found the destination so the reader knows they were taken somewhere inferred rather than somewhere declared.
- Word Find now treats a selection as the word when there is one, and falls back to the run of characters at the cursor when there is not.
- Added Y for the page explorer, a single letter because NVDA leaves Y unassigned.
- On using plain W for Word Find: W is not free. NVDA uses it for spelling error navigation. Word Find therefore stays on Alt+W and Alt+Shift+W.

## 0.35.0

- Reports now open as a real page in the HomerView window rather than in NVDA's browseable message window. Page information, the page explorer, the IBM report, the history, the command summary, help, about and the change history all go this way.
- The browseable window was the obvious place for a report and the wrong one for most of them, because it is a dead end. Control+S does nothing, since it is not a browser. None of HomerView's own commands reach it, so a report could not be searched with Control+F, read with Alt+F8, saved with Control+F12, or navigated to its main content. And focus did not reliably land at the top, so a reader had to go looking for output they had just asked for.
- A temporary page has none of those problems. It is an ordinary document: every HomerView command works on it, the browser's own Control+S works, it can be kept, printed or sent, and NVDA announces it as it announces any page, with the cursor at the beginning. That also answers the request to be placed at the top automatically, by removing the thing that was not doing it.
- The browseable window is still used when there is no browser to put a page in, which is mainly before HomerView Edge has been launched. The log records which route was taken, so a reader who expected a tab and got a window can see why.
- Set bPreferTemporaryPage to False in output.py to use the browseable window throughout.

## 0.34.0

- On hearing a command's name: NVDA's own report commands speak the value and nothing else. NVDA+T says the title, not "Title, the title"; NVDA+F12 says the time, not "Time, the time". There is no verbosity setting that adds a label, because labelling is not NVDA's pattern. JAWS does label, which is why the absence is noticeable coming from it. HomerView follows NVDA by default, and bSpeakCommandLabels in pageBuffer.py turns labels on for anyone who prefers the JAWS habit.
- A tab that closes while its identifier is in flight is no longer logged as an error. It is a race rather than a fault, it was already handled, and reporting it at error level teaches the reader to skip errors, which is the opposite of what a log is for.

## 0.33.0

- The IBM scan now writes JSON, CSV, HTML and a spreadsheet to the downloads folder on every run, named for the page and the time, with nothing further to ask for.
- The engine itself returns JSON and nothing else. The spreadsheet and HTML reports people associate with IBM's checker come from its other tools, the Node package and the browser extension, neither of which can run inside an NVDA add-on. So the other three formats are produced here from the same JSON.
- The spreadsheet is written without any library. An xlsx file is a zip of XML parts, and the standard library has zipfile; using inline strings rather than a shared string table removes the last part that would need bookkeeping. The workbook carries a summary sheet and one sheet per kind of finding.
- One failed format does not stop the others. A spreadsheet that cannot be written is no reason to withhold the CSV.
- The exported JSON is the engine's own report rather than HomerView's digest of it, so anything that already reads IBM output can read the file unchanged.

## 0.32.0

- Added the shared Homer folder architecture, found by walking up from the add-on rather than by any absolute path. This add-on sits at nvda\\addons\\homerView\\globalPlugins\\homerView, so four levels up reaches NVDA's own configuration folder, and a Homer folder beside addons and scratchpad is reachable from any add-on by the same walk. NVDA does not scan that folder, so nothing in it is mistaken for an add-on, and it survives add-on updates and removals.
- The Python toolkit, 2htm and pandoc all use the same search, so one folder can serve code and tools together, and a second add-on finds them without knowing anything about HomerView.
- Executables are a separate case and the folders are searched in an order that reflects it. A Homer or HomerView folder under Program Files comes first for a binary, because the user profile roams and a growing number of managed environments refuse to execute anything from it.
- The installer now accepts an optional bundled 2htm.exe and pandoc.exe, included when present beside the setup script and skipped when absent. Bundling in the installation folder is sound where bundling in the add-on would not be: an add-on folder is replaced wholesale on every update, is included in every add-on backup, and sits in that same roaming profile.

## 0.31.0

Reliability. A command that fails must say so.

- Fixed About, which crashed every time. The name history had been bound to the history store object rather than to the module, so asking it for history.history raised an attribute error before the window could open. The traceback was in the log; the user heard only that something had not worked.
- Every page command now runs behind a safety net. NVDA catches an exception raised inside a script and writes it to its own log, so until now a command could fail in complete silence: nothing spoken, nothing in HomerView's log, and the key looking dead. For a program that has to be trusted by people who cannot see a stack trace, silence is the worst failure there is. Forty-two commands are now wrapped.
- A failure now names itself. Instead of "That command could not be run", both the menu and the keyboard say which command failed and what kind of fault it was, and that the log has the detail. One spoken sentence is now enough to act on, and enough to report.
- The full traceback still goes to HomerView's own log, so a fault found by a user can be diagnosed from the file they send rather than from NVDA's log, which they may not think to include.

## 0.30.0

- The Alternate Menu was listing page commands under their internal names, so listFormFields sat beside Extract main content. Alphabetical order became meaningless, because camel case sorts by its capitals, and half the list read like source code rather than like commands. Names are now readable, which should also settle whether anything is actually missing.
- The menu now logs what it is made of, page commands and global commands counted separately, so a short list is a visible fact rather than an impression.
- Bringing the browser window to the front now checks whether it worked. Windows refuses foreground changes from a process that does not already own the foreground, and the call can report success while only flashing a taskbar button, which is very likely why the window seemed missing and a second press of NVDA+Alt+H was needed. The log now records the call result, which window is actually in front afterwards, and whether those agree, and says plainly what to do when Windows declines.
- A key that resolves to a HomerView command is now logged at information level rather than debug, so what was actually attempted in a session can be read without filtering through every keystroke.

## 0.29.0

- Fixed the silent dialogs. Every dialog HomerView opened from a command was invisible to NVDA: nothing was announced, and the arrow keys went on moving through the web page underneath while the dialog sat in front of it.
- The cause is that a dialog opened from inside a screen reader script is a trap. The script has not returned, so NVDA is still executing it and has not processed the focus change. The window appears and works, because wx runs its own event loop, which is why Enter chose an item correctly. But NVDA never learns the dialog exists.
- The log recorded it exactly: while the menu was open, every keystroke was still logged as going to the page, with DownArrow resolving to the browse mode move by line command and the focused application still reported as Edge.
- Every dialog opened from a command now waits for the script to return first. NVDA then sees an ordinary foreground change, announces the dialog, and routes keys to it. This is the same reasoning behind NVDA's own runScriptModalDialog.
- Affected: the Alternate Menu, the hotkey summary, find, the heading, link and form field lists, act on the page, go to percent, save the page as, open another format, and the clipboard export dialogs.

## 0.29.0

- Fixed silent dialogs. Every HomerView dialog is now shown after the command that opened it has finished, rather than during it.
- The cause is a rule about screen reader scripts that this code was breaking everywhere. A script runs on the same thread that processes NVDA's own events. Calling ShowModal inside a script opens a nested event loop while NVDA is still waiting for that script to return, so the focus change into the dialog is never processed. The dialog appears and accepts Enter, but NVDA does not know it exists and says nothing.
- The log recorded this exactly: while the Alternate Menu was open, every key was logged as focus in msedge, and the arrow keys resolved to the page's own line navigation. NVDA was moving the browse cursor of the page behind the dialog.
- The fix is to defer with CallAfter so the script returns first. NVDA then processes the focus change normally and the dialog speaks.
- The Layout by Code dialogs gained a callback form for this. Passing functionDone shows the dialog after the script returns and delivers the answer to the callback; the synchronous form remains for use outside a script, where it is safe. Find, the element lists, Act on the Page, Open Another Format, the Alternate Menu and the Hotkey Summary all use the callback form now.

## 0.28.0

- Fixed the reason HomerView felt hit and miss. A page that took the fallback attachment route got three commands instead of forty-four, and the other forty-one did nothing at all, silently.
- The fallback runs when a document was already open, or was still being built, when HomerView connected, so the overlay class was never inserted. It correctly replaced the instance's class with the composed one, which carries every script. It then bound only the three commands the function was originally written for, because the initialiser that would have read the class's gesture table had already run.
- So whether a key worked depended on when its page happened to load. The same key worked on one tab and did nothing on the next, which is exactly what hit and miss looks like from the keyboard.
- The log had already recorded it plainly: a working page reports forty-six gestures bound, a page on the fallback route reported three. That line is what identified it.
- The fallback now binds every gesture and reports how many of how many were bound, so a partial attachment can never again look like a working one.

## 0.27.0

- Added the IBM Equal Access engine on Alt+I, alongside axe-core. The Node.js concern was well founded and does not apply, because the IBM project ships two different things under similar names. accessibility-checker is the Node package: it drives Puppeteer, writes baselines, belongs in a build pipeline, and collects telemetry by default. accessibility-checker-engine is the rule engine itself, plain JavaScript meant to be injected into a page, with a two line API. Only the second is used, so there is no Node anywhere.
- The engine is fetched from a content delivery network once per session and injected through Runtime.evaluate, exactly as axe-core is. IBM's own documentation warns that a page's content security policy can block its script tag and offers IBM's rule server as an alternative host; that warning does not apply here, because Runtime.evaluate runs in the page's context through the debugger rather than as a script element, so no policy is consulted. The IBM host is still used as a third fallback, for availability.
- The reason to run it as well as axe is the ruleset. axe checks WCAG. IBM's unified ruleset checks a superset that also covers EN 301 549 and the US Section 508 standards, which is what several procurement regimes actually ask about, and its rules are harmonised with the W3C ACT Rules community group.
- IBM reports a level and an outcome as a pair rather than a single list, which lets a recommendation be told from a failure. HomerView keeps that distinction: violations, results needing review, recommendations, and manual checks are separated, each with a line saying what it means.
- Results are saved as Ace.json in the engine's own format, beside Axe.json, so anything that already reads either can read HomerView's output.
- The engine is Apache 2.0.

## 0.26.0

- Added Act on the Page on Alt+V, adapting Stagehand. Type what you want, such as click sign in, type Jamal into search, check remember me, or read the summary, and HomerView finds what could match and does it.
- Stagehand's interesting idea is not the language model, it is the page representation: it drives a browser over the DevTools Protocol and works from the accessibility tree rather than the markup, because roles and names are what an action is actually about. That is the tree a screen reader user already navigates, so the representation transferred exactly.
- The language model did not transfer and is not wanted. HomerView has no such service and adding one would mean sending the page somewhere. A phrase is resolved by matching it against the page's own controls instead: every control that could match is found and ranked, and when more than one is close you are told the role and name of each and choose. A model guesses and acts; this shows you first. That is deterministic, reviewable before it happens, and repeatable.
- Actions are dispatched as real input events through the Input domain at the element's own coordinates, not by calling click in script. A scripted click fires no pointer sequence, does not reliably move focus, and does not satisfy the user-activation checks that guard popups and the clipboard.
- Verbs understood: click, press, open, follow, select and choose; type, enter and fill, with in, into or to separating the text from the target; check, tick, uncheck and untick; focus; and read. A phrase can also name a kind of control, as in the search field or the Download link, which is used to rank matches rather than to filter them out.

## 0.25.0

- The homer package now also looks for a shared Homer folder, so one machine can hold the authoritative copy without any add-on depending on it existing. Two places are searched: NVDA's developer scratchpad at %APPDATA%\nvda\scratchpad\homer, and a Homer program folder for an installation that keeps shared assets in Program Files.
- The vendored copy wins by default, so a shared folder can add modules but cannot silently replace one an add-on shipped and tested against. Set bPreferSharedFolder to True in homer/__init__.py to reverse that on a development machine.
- The scratchpad is the right home for this on a single machine and the wrong one for distribution. NVDA disables it by default, requires it to be turned on under Advanced settings, and says plainly that it is for development rather than for shipping code. An add-on that needed it would not work on anyone else's computer.
- Added pandoc as a second converter, discovered and never bundled: AsciiDoc, DocBook, FictionBook, Jupyter notebooks, LaTeX, man pages, MediaWiki, Org, reStructuredText, Textile and wiki files now open. Pandoc is looked for in its own installation folder, in a Homer program folder, and on the path.
- Pandoc is not bundled for the same reasons 2htm is not: it is well over a hundred megabytes, an add-on folder is replaced wholesale on every update and included in every add-on backup, and it has its own installer that keeps itself current.

## 0.24.0

The shared Homer toolkit, as a Python package other NVDA add-ons can copy.

- Added a homer package holding the modules that are not about HomerView: inix, lbc, say and web. It is the counterpart of the C# Homer namespace, and it follows three rules that make it shareable. No module imports NVDA at the top level, so every one is importable and testable in a plain interpreter and the same code serves a program that is not an add-on. Nothing depends on anything outside the standard library except wx, which NVDA is built on. And no module knows about HomerView.
- Copying rather than sharing one installed copy is deliberate. NVDA has no dependency manager for add-ons: a library add-on that put itself on sys.path would work until load order changed, or until someone removed it without knowing three other add-ons needed it, and the add-on store cannot declare or protect that dependency. Copying costs a re-copy when a fix lands; sharing costs silent breakage in somebody else's add-on. The C# modules make the same trade for the same reason.
- Ported InixCodec as homer.inix. Python has configparser, so this earns its place only by what configparser will not do: it discards comments and blank lines and rewrites a file in dictionary order. A configuration a person edits by hand should come back as they left it, with a changed value changed in place. Verbatim multi-line values, the implicit Global section, and round-trip fidelity are all preserved, and all are tested.
- Ported the practical half of the C# Web module as homer.web: browser-like headers including the Sec-Fetch set, filenames from Content-Disposition including the RFC 5987 encoded form, an extension guessed from the MIME type, name sanitising and numbering, and link extraction.
- Added homer.say, a single entry point for announcing text. Library code that calls NVDA's ui.message cannot be tested outside NVDA; calling say means the one import of NVDA lives in one place and the module still works elsewhere.
- lbc moved into the package, with a shim left at the old path so existing imports keep working.
- Not ported, and why: the C# Say module's channel cascade exists to reach a screen reader from outside one, which an add-on never needs; DbDo.cs is an application rather than a library; and DbDo.js is a JScript eval bridge that Python does not need, since exec is built in.

## 0.23.0

The standard for taking a key that already does something: it has to overwhelmingly supersede what was there.

- Removed NVDA+F9 for the link list. It is NVDA's marker for the start of a review copy, and listing links does not come close to superseding that. Links are now on NVDA+Shift+F7, next to NVDA's own Elements List and unassigned. Form fields stay on NVDA+F5 and headings on NVDA+F6, neither of which NVDA uses.
- Control+F now opens the HomerView find. This is the JAWS judgment and it holds: a reader working in a virtual view of the page wants a find that moves the browse cursor and takes a regular expression, not one that highlights something on screen. Control+F3 still works for anyone who prefers it.
- Control+O now opens a document. Edge's own Control+O opens a file the browser can already read; this opens those and every format 2htm converts, so nothing is lost. Control+F10 still works.
- Added the Homer help trio, none of which collides with anything in NVDA: F1 shows the user guide, Alt+F1 shows About, and Shift+F1 shows the history of changes. About reports the version, every folder HomerView writes to, whether the converter was found, and what it is connected to, which makes it the first thing to read when something is not working.
- F1 in Edge opens Microsoft's own help site, which has nothing to say about HomerView, so replacing it inside a HomerView page loses nothing.
- Added Word Find on Alt+W and Alt+Shift+W, finding the next or previous occurrence of the word at the cursor with nothing to type.
- The browse mode command set is now 41 keys, every one verified against a real script.

## 0.22.0

- Fixed the Alternate Menu, which had never worked. The key resolved correctly every time, and the log proved it, but building the command list looked for methods named homer_<name> when the scripts are named script_<name>. Every call raised AttributeError before the first entry existed, and NVDA swallowed it, so the command looked dead while the binding was perfect. The lookup is now checked rather than assumed, one bad entry no longer costs the whole menu, and the number of commands built is logged.
- Added Find on Control+F3 and Find Backwards on Control+Shift+F3, both taking a regular expression or plain text. F3 and Shift+F3 repeat the last find, whichever kind it was, as EdSharp does. Python's re module is used rather than VBScript through COM: no round trip, and the dialect people actually write.
- A search that finds nothing leaves the cursor where it was and says Not found, matching NVDA's own quick navigation. Searching runs over the browse mode buffer rather than the markup, so every match is somewhere the cursor can actually go, and a search wraps at the end as an editor would.
- Added the three JAWS element lists: form fields on NVDA+F5, headings on NVDA+F6, and links on NVDA+F9, matching JAWS Insert+F5, Insert+F6 and Insert+F7. NVDA's own Elements List on NVDA+F7 is more capable but needs a radio button chosen first, and a reader who wants the links wants them now.
- Note on NVDA+F9: it is NVDA's own marker for the start of a review copy. It was requested and is bound, but only inside HomerView pages, so the review command is unaffected everywhere else and can be reclaimed in Input Gestures.
- The command list now writes the NVDA modifier properly, so NVDA+F6 no longer appears as F6.

## 0.21.0

- Save Page As moved to Control+F12, keeping Control+Alt+S as a second key. Plain F12 was left alone because Edge uses it for the developer tools, which is worth keeping in a browser HomerView is already driving through that same protocol.
- Added Page Information on Alt+M, reporting what a page says about itself: title, site, author, publisher, published and modified dates, summary, licence, language, type, section, keywords and the software that built it. Each field shows where it came from, so a date attributed to the publisher can be told from one guessed at.
- Five conventions are read, because no single one is reliable: plain meta elements, Open Graph, Twitter cards, Dublin Core, and JSON-LD following schema.org. Declared links for licence, canonical and author are read too, along with any time element and microdata author. Everything else found in the head is listed separately rather than discarded.
- The Python package for this outside a browser is extruct. It is not usable in an NVDA add-on, which has only the standard library, and fetched markup would be the wrong source anyway: reading the live document sees metadata that script inserted after load, which on a modern publishing site is most of it.
- Implemented the Homer Control+C rule properly. With a selection it copies the selection; with none it copies the current line, rather than doing nothing because the user had not selected first. Alt+C does the same, appending instead of replacing.

## 0.20.0

HomerView becomes a reader for documents, not only for web pages.

- Added Open Another Format on Control+F10. Choose a Word, Excel, PowerPoint, PDF, Markdown, EPUB or OpenDocument file and HomerView converts it with 2htm behind the scenes, writes the result to the temporary folder with the same root name and a .htm extension, and opens it in the HomerView window, where every HomerView command then works on it.
- 2htm is looked for in the HomerView installation directory first, then 2htm's own, then the registry, then the path, and only last in the add-on folder. An add-on folder is replaced wholesale on every update, sits under the roaming profile that many managed environments forbid executing from, and is not where Windows expects a program to live.
- The installer now defaults to the Program Files folder rather than the root of the C drive, matching where an executable belongs.
- Added Save Page As on Control+Alt+S, offering web page, Markdown and plain text every time. F10 was considered and rejected: Windows uses it for the menu bar and Chromium for the toolbar, so taking it would have cost a key the user already has.
- The saved page is the live document after script has run, not the markup the server first sent. Markdown keeps headings, lists, tables, links and image alternative text as punctuation.
- Added HomerView.db, recording pages viewed, documents opened and converted, and where each came from. SQLite is used when Python's sqlite3 module is present and a JSON lines file when it is not, with the log saying which. Added a History command, with no default gesture, to read it back.
- Rewrote pyLbc for Python 3 as lbc.py, fit to publish on its own. The dependency on pywin32 is gone, replaced by configparser for the one thing it did. Names follow Camel Type. It no longer creates or exits a wx.App when one already exists, which inside NVDA it always does. The parent window and NVDA's prePopup and postPopup calls are resolved rather than assumed. The accessibility rules are unchanged: OK and Cancel carry no mnemonic, Control+Enter submits from any control, and a field's label is copied into its accessible name.

## 0.19.0

- An Edge window that was already running cannot be given a debugging connection, so HomerView now carries the user's place across instead. While the focus is in an Edge page HomerView did not open, its address is noted, and the next launch opens that address rather than the start page. Nothing is read that costs input or output, so this is safe on the thread that drives speech.
- The launch command now raises the HomerView tab through the protocol and then brings its window to the front through the Windows API, on every path: a fresh launch, a reconnection, and a launch when HomerView Edge was already running. Raising a tab within a window the user cannot see is not activation.
- The launch command says when it reopened the page you were on, rather than leaving the change unexplained.
- Rewrote the start page. It now offers DuckDuckGo, OpenClaw, Wikipedia and SearXNG, each described by the class of application it belongs to rather than by praise, and each with its actual licence stated. DuckDuckGo's search service is proprietary even though its browser apps are open source, so saying otherwise would have been wrong. SearXNG is listed because it is the search option that meets the open source test end to end.
- The start page also explains why commands work only in windows HomerView opened, which was previously something the user had to work out.

## 0.18.0

Logging that can tell a key conflict from a missing binding, and a menu that works before a page exists.

- Added NVDA+Alt+F10 for the Alternate Menu, working anywhere including before HomerView Edge has been launched. Alt+F10 still works inside a page, matching the Homer interface, but a list of commands is no use if finding it needs a command. Outside a page the menu lists the global commands and says plainly that the reading, selection and clipboard commands need a HomerView page.
- Every key routed to a HomerView page is now logged with the command it resolved to, or with no command. This distinguishes the two ways a key can appear to do nothing: a key that never appears was taken by Windows or Edge before NVDA saw it, and no binding can help; a key that appears with no command reached us and our binding is what is wrong. From outside, those look identical.
- Every key pressed while Edge has focus, and every key HomerView claims anywhere, is now logged globally with the application that had focus.
- The gestures actually bound are now listed once per page and once at startup, so a missing binding is visible without pressing anything.
- Every queued task now records the thread it ran on and warns if it is the wrong one. Speech and dialogs must be on NVDA's main thread and network work must not be, and a vague report of sluggishness now becomes a specific line.

## 0.17.0

The Homer interface, adapted from the editor to the browser, plus a way to prove the three browser channels are live.

- Added a self test with no default gesture. It exercises all three ways HomerView reaches the browser and reports each: the browser window through NVDA objects and the Windows API, the page as NVDA built it through browse mode, and the page through the DevTools Protocol. The protocol is reported as two separate results, asking and acting, because a connection can answer every query while having lost the ability to act, and a test that only reads would not notice. Acting is proved with a real input event and a live accessibility tree.
- Added the Homer query commands in browse mode: Read All on Alt+F8, Copy All on Control+F8, Copy Append on Alt+C, Say Yield on Alt+Y, Say Yield Structure on Alt+Shift+Y, Say Position on Alt+Delete, Say Selected on Shift+Space, Say Chunk on Shift+Backspace, Say Rest on Alt+R, Page Name on Alt+N, Url Reference on Alt+U, Page Urls on Alt+P, and Say Time on Alt+Semicolon.
- Added Homer selection without holding Shift: Start Selection on F8, Complete Selection on Shift+F8, Go to Selection Start on Alt+Shift+F8, and Select Chunk on Control+Space.
- Added the chunk as a unit. A chunk is a run of non-blank characters, wider than a word because word movement stops at punctuation, so a web address is one chunk and several words.
- Added Go to Percent on Control+G and Go to Percent Again on Alt+G.
- Added the clipboard commands on the apostrophe key, following FxMax and IEMax rather than inventing new ones: Quote Clipboard on Alt+Apostrophe, Clear Clipboard on Alt+Shift+Apostrophe, Save Clipboard on Control+Apostrophe, and Append Clipboard on Control+Shift+Apostrophe. The save dialog proposes clipboard.txt, then clipboard-01.txt and so on when that name is taken, and appending inserts the Homer section break so the file stays navigable by section.
- Added the Alternate Menu on Alt+F10, listing every command alphabetically with its key after the name, Enter to run. Commands with no key still appear, since a command nobody can find is no better than one that does not exist.
- Added the Hotkey Summary on Alt+Shift+H, the same set as a readable document grouped by where each command works.
- Every Homer key is bound on the browse mode class, so it exists only inside HomerView pages and cannot shadow anything in Edge, another browser, or Windows.

## 0.16.0

Two gestures collided with NVDA's own commands and have moved.

- Extract main content moved from NVDA+Alt+R to NVDA+Alt+X. NVDA+Alt+R toggles a Remote Access session, which is a built-in NVDA command and a much worse thing to shadow than a HomerView one.
- The modifier alternative for main content navigation moved from NVDA+Alt+M to NVDA+Alt+J, matching the single letter J. NVDA+Alt+M begins interaction with mathematical content.
- Checked every remaining HomerView gesture against the NVDA 2026.1.1 command reference. NVDA+Alt+A, D, E, H, W and the single letter J are unassigned by NVDA.
- Known and deliberate: NVDA+A for the page address is unassigned in NVDA's desktop layout but is Say all in the laptop layout. It is bound only inside HomerView browse mode, so laptop layout users lose Say all on that page and can reassign the command in Input Gestures.

## 0.15.0

- Added NVDA+Alt+E, a page explorer modelled on the JAWS 2026 feature of the same name on Insert+Shift+E. It puts a summary of the current page into NVDA's browseable message window, which is NVDA's counterpart to the JAWS Results Viewer: a virtual document read with the usual browse mode keys and closed with Escape.
- The summary covers the page overview and reading time, every landmark with what it contains, the heading outline with any faults in it, the links worth knowing about, the visual aspects a reading order hides, and numbered navigation tips with NVDA keystrokes chosen for what the page actually contains.
- The visual section reports only notable findings: an open dialog, a consent banner, a header pinned over the content, text visible on screen but hidden with aria-hidden, images with no alternative text, media set to play automatically, live regions that will interrupt, and untitled frames. A page with none of these says so.
- The analysis is rule-based rather than sent to a language model, because the questions a screen reader user needs answered are exact ones and a model would paraphrase them less reliably. Prose about the subject matter is a different feature, already served by NVDA+Alt+R.
- Downloads now speak the base name of each file just before it is fetched, and say Error only when one fails.
- Fixed a crash in the fallback route for attaching browse mode commands. NVDA resolves a script name against the class rather than the instance, so attaching a bound method raised LookupError. The instance is now given the composed class directly, which puts the scripts where bindGesture looks for them.
- Fixed downloads from GitHub. A blob address is a web page about a file, not the file, so every download arrived as the same few hundred kilobytes of GitHub markup under a name promising a document. Blob addresses are now rewritten to raw ones, and any response that returns a web page where a document was requested is refused rather than saved.

## 0.14.0

- Added NVDA+Alt+R, which extracts the readable part of the page and opens it as a plain document with a heading, a main landmark, and nothing else. This is the job mainly.py and mainer.py did, moved into the browser: those scripts fetched raw markup and ran a readability library over it in Python, but on a page built by script the markup from the server is a shell and the article is not in it. HomerView already holds the live document, so the extraction happens on what is actually on screen.
- Extraction uses Mozilla's Readability, the algorithm behind Firefox reader view and behind the readability packages those scripts imported, fetched from a content delivery network once per session. A smaller built-in fallback picks the main landmark, then an article element, then the densest block of paragraph text, and the document says which method was used.
- Added NVDA+Alt+W, which lists the file types linked from the page as a single editable line, alphabetised, then downloads the ones accepted. Page extensions such as html and php are left out so the ones that matter are visible.
- Downloads follow urlFido: the file is fetched directly over HTTP carrying the session's own cookies from Network.getCookies, the browser's user agent, the page address as the Referer, and the Sec-Fetch headers a click on the link would have produced. Without those a request looks like a scraper and comes back as a 403 or a login page.
- File names come from Content-Disposition where the server supplies one, otherwise from the address, cleaned of characters Windows forbids, and duplicates are numbered rather than overwritten.
- Files go to the user's real downloads folder, read from the known folder registry entry rather than assumed to be under the profile.
- Generated documents, including the accessibility report in both formats, now go to a HomerView folder inside the temporary folder, which Windows clears on its own. Names there are stable rather than random, so a file can be found again while it exists. The raw axe result stays beside the log where it was asked for.

## 0.13.0

Learnings from urlCheck's report, applied to HomerView's.

- Fixed a misleading presentation of how to fix a problem. axe groups its checks into any, all, and none, and they do not mean the same thing: a check under any is one of several alternatives and only one is needed, while all and none are every one required. The report ran them together, which told a publisher to make several changes when one would do. Fix groups are now labelled Fix any one of these and Fix all of these.
- Each violation now names the WCAG success criteria it fails, with the criterion's short name, conformance level, principle, and a link to the official explanation. A rule called region now reads as 1.3.1 Info and Relationships, Level A, Perceivable.
- Best practice rules, which carry no WCAG tags, are labelled as such and their related criteria are marked advisory. Presenting them as compliance failures would be an overclaim that undermines the parts of the report that are true.
- Every instance now shows the element's own HTML as well as its selector, which is what lets someone find the thing in their code.
- Check data, such as the measured and expected contrast ratios, is shown alongside the message, and related elements are listed with their selectors.
- Nested selector paths, produced when an element sits inside a frame or a shadow root, are rendered outermost first rather than run together.
- Added a plain language summary and a numbered list of next steps, including the honest note that an automated scan finds roughly a third of accessibility barriers.
- Added a Where to start section: failing elements by severity with an explanation of what each severity means for people, the rules failing most often, and the WCAG criteria most affected.
- Added a table of contents with a link to each violation, and a back link from each violation.
- Added a glossary and a short list of places to learn more.
- The results by outcome table now explains what violations, needs review, passes, and inapplicable each mean.
- Scan details now include the window size, since some rules depend on layout.
- Violations within a severity are now ordered by how many elements they affect.
- The pre-written email now cites the WCAG criteria and flags best practice rules as such.
- Not carried over from urlCheck: the coloured emoji beside each severity. A screen reader announces it as "red circle" immediately before the word "critical", so the severity is heard twice and one of them is noise.

## 0.12.0

- The note explaining that X is left out of the social channel list now sits with that list rather than at the end of the whole contact section, where it read as though it applied to the contact pages listed above it, and it is left out entirely when the page being reported on is itself on that site, where it made no sense at all.
- Contact addresses are compared in a normalised form, so a link differing only by a trailing slash or by the case of the host is no longer listed twice.
- Path probing now follows redirects and discards any that settle at the site root. Single page applications answer every address with 200, so an unfiltered probe reported contact pages that do not exist.
- An accessibility statement found by probing is now also listed among the accessibility pages, rather than being discarded when the page itself links to a different one.
- When axe reports frame-tested, the report now explains that the page contains frames and that only the top document was examined, rather than leaving a bare rule name.

## 0.11.0

- Absorbed AccReporter. NVDA+Alt+A now scans the page, finds every plausible way to report the problems to the publisher, writes a full report in both HTML and plain text, and opens it in a new HomerView tab.
- Contact discovery reads the page itself through the protocol, so anchors added by script after load are seen; fetches the site's home page, whose footer usually carries the links the current page lacks; and probes conventional accessibility and contact paths with HEAD requests, which finds statements nothing links to.
- Discovered email addresses become links that open a message already written, describing the violations found, with the report path named so it can be attached.
- The social channel list deliberately omits X, formerly Twitter, as AccReporter decided, because reports sent there have a poor record of reaching anyone who can act on them.
- The report is a document rather than a dialog: one h1, an h2 per section, an h3 per violation, a working skip link, and affected elements inside expandable details elements. Violations are ordered by severity rather than by rule name.
- axe-core now runs against the wcag2a, wcag2aa, wcag21aa, and best-practice tags, as AccReporter did, rather than every rule. Set lAxeTags to an empty list in axe.py to restore the full set.
- Kept the counts-only test as a separate command with no default gesture, for when the full report is more than is wanted.
- AccReporter's Download button is replaced by naming the file paths, since HomerView has already written them, and the plain text report appears inside the HTML report as a selectable block rather than behind a clipboard call that browsers restrict on local files.

## 0.10.0

- The HomerView window now opens a small local start page instead of about:blank. A real session showed about:blank producing no NVDA document at all, so the window announced nothing and gave no sign it was ready. The start page loads instantly, needs no network, and carries a banner, a navigation landmark, a main landmark, and headings, so every command has something to work on straight away. It also lists the commands.
- Added startPageUrl in edge.py for anyone who would rather open a real site, such as google.com, or return to about:blank.
- A stale DevToolsActivePort file is now removed once its port is found dead, so the same dead port is not probed twice during a single launch.
- Very large protocol payloads, such as the six hundred kilobyte axe-core bundle, are now logged by length rather than by content.

## 0.9.0

- Main content navigation no longer moves the cursor when no main landmark is present. NVDA's quick navigation keys leave the cursor where it is on failure, and a navigation command that lands somewhere other than where it was asked to go is worse than one that reports nothing was found.
- Removed the first heading fallback added in 0.8.0, for the same reason.
- The not found message is now "no main landmark", matching the lowercase wording of NVDA's own quick navigation messages such as "no next heading". A document without landmark support now says "Not supported in this document", which is NVDA's exact wording.
- Reporting now happens before moving, matching NVDA, which reports first because moving can change the focus and mutate the document.
- Added NVDA+Alt+A to test the current page with axe-core, saving the results to C:\HomerView\Axe.json. Speech reports the violation, review, and pass counts.
- axe-core is fetched from a public content delivery network with a second network as backup, following urlCheck, so no Node.js installation is needed. It is fetched once per NVDA session and reused.
- The source is injected through Runtime.evaluate rather than as a script element, so a page's content security policy does not apply.
- Added a per-call timeout to protocol evaluation, since an axe run can take minutes where ordinary calls take milliseconds.

## 0.8.0

- Main content navigation now reads a line on arrival rather than the whole element, matching NVDA's own landmark command. Without this, landing on a main landmark read the entire page.
- Main content navigation now suppresses its report when the gesture will resume say all, again matching NVDA's quick navigation.
- Reporting the web address now follows NVDA's convention for report commands: once speaks, twice spells, three times copies to the clipboard.
- Reporting the web address is marked speak on demand, so it still speaks when NVDA's speech mode is set to on demand, as NVDA's own query commands do.
- When a page defines no main landmark, which is true of about half the web including Wikipedia's portal page, the first heading is used instead and the difference is announced. Set bFallBackToFirstHeading to False in pageBuffer.py to restore the previous behaviour.
- A stale DevToolsActivePort file is now detected with a short socket probe instead of a full protocol handshake, removing about two seconds from every launch that followed a closed browser.
- Simplified address resolution and landmark identification, and moved their per-candidate logging down to debug level, now that a real session has shown which property and which attribute carry the answer.

## 0.7.0

- Fixed the launch failure. The process HomerView starts routinely exits within a fraction of a second after handing its work to another process, while a browser window opens perfectly well. Treating that exit as a failure aborted a launch that was about to succeed. Only the DevToolsActivePort file is watched now, which is what urlFido has always done.
- Added --edge-skip-compat-layer-relaunch, one of the ways Edge replaces the process it was started as.
- The launched process identifier is now used only when the protocol supplies no browser identifier, and never after that process has exited.
- Moved main content navigation off the letter Q, which NVDA already uses for block quote navigation. It is now J, for jump to main, with NVDA+Alt+M as a modifier based alternative. Both gestures are defined as constants at the top of pageBuffer.py.
- The launch timeout message no longer blames enterprise policy first, since a handed-off process was the more common cause.

## 0.6.0

- Suppressed Microsoft Edge's implicit sign-in and its modal sync consent dialog, which blocked the address bar on a fresh profile and made the browser appear frozen. The switches and the seeded profile preferences are taken from urlFido and bookFido, where the same problem was solved.
- Preferences are seeded only when the profile folder is being created, so a profile the user has since configured is never overwritten.
- Added a constant, bAllowSignIn in edge.py, for anyone who wants the HomerView profile signed in and synchronised. Prompt suppression still applies, so sign-in stays deliberate.
- Added a command to close a Microsoft Edge dialog that is blocking the window, on NVDA+Alt+D, and a spoken warning after launch when such a dialog is present.
- Added a fallback route that binds the two browse mode commands onto the tree interceptor instance when the composed class does not take effect. The log records which route was used.
- HomerViewDocument now derives from AutoPropertyObject, so NVDA generates a property from its _get_treeInterceptorClass method rather than leaving it as dead code.
- The tree interceptor's method resolution order is logged on first focus, which answers the question the composed class raised without needing the Python console.
- Narrowed the cached process identifiers to Edge browser processes only. A document's window handle belongs to the browser process, so renderer and service identifiers added nothing and risked a false match after Windows recycled a number.
- Registry hive names are logged rather than raw numbers.

## 0.5.0

- Added extensive per-session logging to C:\HomerView\HomerView.log, rewritten from empty each time the add-on loads, with the preceding session preserved as HomerView.previous.log.
- The log falls back to the local application data folder when the installation folder cannot be written, and the header records which location was used. The installer now grants the Users group modify rights on the installation folder so that the preferred location works for a standard user.
- Every DevTools message sent and received is logged, abbreviated to a fixed length, along with event counts for the connection.
- Every queued task is logged with its outcome and duration.
- Every candidate property examined while resolving a document address is logged with its raw value, and every landmark examined while looking for main content is logged with all of its identifying attributes. One real session therefore answers the two open questions about NVDA internals.
- Added a command to open the current session log. It has no default gesture.

## 0.4.0

- Added NVDA+A to report the web address of the current HomerView page, resolved from NVDA first and from the DevTools Protocol only as a fallback.
- Added Q to move to the main content landmark of the current HomerView page.
- Moved both browse mode commands onto a tree interceptor class, so they appear in Input Gestures and cannot leak into other browsers or applications.
- Replaced window title matching with process identity, so the test for a HomerView page performs no input or output and is safe on NVDA's main thread.
- Replaced the single shot worker with a queued worker thread.
- Rebuilt the DevTools client around one browser level connection with flattened target sessions and a reader thread, so protocol events are dispatched rather than discarded.
- Replaced the fixed debugging port with port zero and DevToolsActivePort discovery.
- Moved the browser profile out of the installation folder, which a standard user cannot write to.
- Dropped the C prefix from constant names.

## 0.3.0

- Proof of concept from earlier design work.

## 0.1.0

- Initial planning package.

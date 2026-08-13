"""HomerView: NVDA browse mode combined with the Edge DevTools Protocol.

This release carries the two browse-mode commands and the connection machinery
they need. The commands themselves are defined in pageBuffer, so that they exist
only inside HomerView Edge documents and leave Chrome, Firefox, ordinary Edge
windows, and native applications untouched.

The logger is imported first, so that the session log is open before any other
HomerView module has a chance to record anything.
"""

import os
import weakref

import wx

from . import logger
from . import paths
from .logger import abbreviate, homerLog, logError, logSection, logThreadContext

import addonHandler

from . import output
import api
import globalPluginHandler
import gui
import gui.settingsDialogs
import ui
from controlTypes import Role
from scriptHandler import script

from . import alternateMenu
from . import convert
from . import dialogs
from . import documents
from . import lbc
from . import saveAs as saveAsModule
from . import download
from . import homerCommands as homerCommandsModule
from . import selfTest
from .pageBuffer import HomerViewBuffer, HomerViewDocument, bindFallbackGestures
from .history import history
from .service import service

addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "HomerView"

    def __init__(self):
        super().__init__()
        logSection("Global plugin initialising")
        self._dSelfTest = {}
        self.iDocumentsMatched = 0
        self.iDocumentsSeen = 0
        self.setInterceptorsSeen = weakref.WeakSet()
        service.start()
        # Reattach silently to an Edge instance left running by an earlier NVDA
        # session. This is queued rather than called, so NVDA never waits for it.
        service.submit("attach", service.taskAttach)
        self._addSettingsPanel()
        self._addMenuItem()
        service.functionOpenDocument = lambda: self.script_openOtherFormat(None)
        self._publishCommands()
        homerLog.info("Global plugin ready")

    def _publishCommands(self):
        """Make the global commands visible in the Alternate Menu."""
        for sName, sGesture, sDescription, sScript in (
            (_("Launch HomerView Edge"), "Alt+NVDA+H",
             _("Launch or reconnect the HomerView instance of Microsoft Edge"), "launchHomerView"),
            (_("Accessibility report"), "Alt+NVDA+A",
             _("Test the page and find how to report the problems to the publisher"), "accessibilityReport"),
            (_("Page explorer"), "Y, or Alt+NVDA+E",
             _("Summarise the page structure and its visual aspects"), "explorePage"),
            (_("Extract main content"), "Alt+NVDA+X",
             _("Open the readable part of the page as a plain document"), "extractMainContent"),
            (_("Download files"), "Alt+NVDA+W",
             _("List the file types linked from the page and download the ones you choose"), "downloadFiles"),
            (_("Dismiss browser dialog"), "Alt+NVDA+D",
             _("Close a Microsoft Edge dialog that is blocking the window"), "dismissDialog"),
            (_("Connection status"), "",
             _("Report whether HomerView is connected to Microsoft Edge"), "reportConnection"),
            (_("Accessibility test only"), "",
             _("Test the page with axe-core and report the counts"), "runAxe"),
            (_("Open the session log"), "",
             _("Open the HomerView log file for this session"), "openLog"),
            (_("Open a document"), "Control+O",
             _("Open a Word, Excel, PowerPoint, PDF or Markdown document as a web page"), "openOtherFormat"),
            (_("Save the page as"), "Control+S",
             _("Save the current page as a web page, Markdown, or plain text"), "saveAs"),
            (_("Recently opened"), "",
             _("List the pages and documents opened in HomerView, so you can find one again"),
             "recentPages"),
            (_("Alternate menu"), "Alt+NVDA+F10",
             _("List every HomerView command in one alphabetical list"), "alternateMenu"),
            (_("Report the page address"), "Alt+A, or Alt+NVDA+U",
             _("Report the web address of the HomerView page, from anywhere in the window"),
             "reportAddressAnywhere"),
            (_("Submit the form"), "Control+Enter",
             _("Submit the form you are filling in, from any field"), "submitForm"),
            (_("Ask Copilot about this page"), "Alt+NVDA+P",
             _("Copy the page text and open Edge's Copilot sidebar, ready to paste and ask"),
             "openCopilot"),
            (_("Quick start"), "",
             _("Open the HomerView quick start in the HomerView window"), "openQuickStart"),
            (_("User guide"), "",
             _("Open the full HomerView user guide in the HomerView window"), "openUserGuide"),
            (_("History of changes"), "",
             _("Open the HomerView history of changes in the HomerView window"), "openHistory"),
            (_("Developer notes"), "",
             _("Open the HomerView developer notes in the HomerView window"), "openDeveloperNotes"),
            (_("Elevate version"), "Control+F11, or Alt+NVDA+F11",
             _("Check for a newer HomerView and install it"), "elevateVersion"),
            (_("Look something up"), "Alt+Q, or Alt+NVDA+Q",
             _("Define a word, check the weather, find books, and more, with no account needed"),
             "webUtilities"),
            (_("Self test"), "",
             _("Check that all three ways of reaching the browser are working"), "selfTest"),
        ):
            functionScript = getattr(self, "script_" + sScript, None)
            if functionScript:
                service.registerGlobalCommand(
                    sName, sGesture, sDescription, lambda f=functionScript: f(None)
                )
            else:
                homerLog.warning(f"No script exists for the published command {sName}")
        # Record what is bound globally, so a key that does nothing can be
        # checked against this list rather than guessed at.
        try:
            dMap = getattr(self, "_gestureMap", None) or {}
            homerLog.info(f"HomerView global gestures bound: {len(dMap)}")
            for sKey in sorted(dMap):
                homerLog.info(f"  global {sKey} -> {getattr(dMap[sKey], '__name__', dMap[sKey])}")
        except Exception:
            logError("The global gesture map could not be recorded")

    def _addSettingsPanel(self):
        """Put HomerView in NVDA's Settings dialog.

        An experienced user looks in Preferences before they look in the
        documentation. An add-on with no page there looks as though it has
        nothing to configure, which here would be untrue.
        """
        try:
            from . import settingsPanel

            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(
                settingsPanel.HomerViewSettingsPanel)
            self.classSettingsPanel = settingsPanel.HomerViewSettingsPanel
            homerLog.info("Added the HomerView page to NVDA's settings")
        except Exception:
            self.classSettingsPanel = None
            logError("The settings panel could not be added")

    def _addMenuItem(self):
        """Put HomerView in the NVDA menu, under Tools.

        This is the other place a user explores first, and it matters more here
        than for most add-ons: someone who has not yet learned a single key can
        start the browser and open the guide from a menu they already know how
        to reach.
        """
        self.menuItems = []
        try:
            menuTools = gui.mainFrame.sysTrayIcon.toolsMenu
            self.menuHomerView = wx.Menu()
            for sLabel, sHelp, functionCommand in (
                # Translators: An item in the HomerView menu.
                (_("&Launch HomerView Edge"), _("Start the browser, or bring its window forward"),
                 lambda event: self.script_launchHomerView(None)),
                # Translators: An item in the HomerView menu.
                (_("&All commands..."), _("List every HomerView command"),
                 lambda event: self.script_alternateMenu(None)),
                # Translators: An item in the HomerView menu.
                (_("&Look something up..."), _("Define a word, check the weather, find books"),
                 lambda event: self.script_webUtilities(None)),
                # Translators: An item in the HomerView menu.
                (_("&Quick start"), _("Open the HomerView quick start"),
                 lambda event: documents.openDocument("readMe")),
                # Translators: An item in the HomerView menu.
                (_("&User guide"), _("Open the full HomerView user guide"),
                 lambda event: documents.openDocument("guide")),
                # Translators: An item in the HomerView menu.
                (_("&History of changes"), _("Open the HomerView history of changes"),
                 lambda event: documents.openDocument("history")),
                # Translators: An item in the HomerView menu.
                (_("Check for a &newer version..."), _("Check for a newer HomerView and install it"),
                 lambda event: self.script_elevateVersion(None)),
                # Translators: An item in the HomerView menu.
                (_("A&bout HomerView"), _("Show the version and where HomerView keeps its files"),
                 lambda event: documents.show("about")),
            ):
                item = self.menuHomerView.Append(wx.ID_ANY, sLabel, sHelp)
                gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, functionCommand, item)
                self.menuItems.append(item)
            # Translators: The HomerView submenu in NVDA's Tools menu.
            self.itemHomerView = menuTools.AppendSubMenu(self.menuHomerView, _("Homer&View"))
            homerLog.info("Added the HomerView menu to NVDA's Tools menu")
        except Exception:
            self.itemHomerView = None
            logError("The NVDA menu item could not be added")

    def terminate(self):
        homerLog.info(
            f"Global plugin terminating after seeing {self.iDocumentsSeen} documents, "
            f"{self.iDocumentsMatched} of them belonging to HomerView"
        )
        try:
            service.stop()
        except Exception:
            logError("Shutting the service down raised")
        try:
            logger.stopSession()
        except Exception:
            pass
        super().terminate()

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        """Mark HomerView Edge documents so they gain the HomerView browse mode.

        This runs for every object NVDA creates, so it must stay free of input
        and output. The role test comes first and is cheap, which keeps what
        follows to a handful of calls per page rather than thousands.

        The rest was not free, and that was a real cost rather than a
        theoretical one. Every document object wrote two log lines, each of
        which is a synchronous file write, on the thread NVDA uses to build the
        page. A page with many frames produced dozens of them before the reader
        heard anything.

        Now a document that is not HomerView's is dismissed in silence, since
        there is nothing to say about the ordinary case and it is the common
        one. Only the documents that matter are described, and the running
        totals are still there for anyone reading the log afterwards.
        """
        try:
            if obj.role != Role.DOCUMENT:
                return
            self.iDocumentsSeen += 1
            bMine = service.isHomerViewObject(obj)
            if not bMine:
                # Nothing written. This is the common case and it is not
                # interesting, and writing about it costs the reader time on
                # the thread that is building their page.
                return
            clsList.insert(0, HomerViewDocument)
            self.iDocumentsMatched += 1
            # Only now, when there is something worth recording.
            sAppName = (getattr(getattr(obj, "appModule", None), "appName", "") or "").lower()
            sName = abbreviate(getattr(obj, "name", "") or "", 120)
            homerLog.info(
                f"Document {self.iDocumentsSeen} is a HomerView page, and the "
                f"{self.iDocumentsMatched} to be: appName={sAppName} "
                f"processId={getattr(obj, 'processID', 0)} name={sName}"
            )
        except Exception:
            logError("Classifying an object raised")

    def getScript(self, gesture):
        """Resolve a global key, recording the ones that matter.

        Every keypress in Windows passes through here, so logging all of them
        would drown the file. Two are worth keeping: any key HomerView claims,
        and any key pressed while Edge has focus, which is where a conflict
        with the browser would show itself.
        """
        functionScript = super().getScript(gesture)
        if (
            functionScript is not None
            and getattr(functionScript, "__name__", "")
            in (
                "script_submitForm",
                "script_reportAddressAnywhere",
                "script_openOtherFormat",
                "script_saveAs",
            )
            and not self._focusIsHomerViewEdge()
        ):
            # Outside HomerView's own browser this key belongs to whatever has
            # focus. Testing for Edge by name was not enough: an ordinary Edge
            # window is also called msedge, so Control+S in a browser HomerView
            # did not open would have saved HomerView's page, and Control+Enter
            # would have submitted a form on a page the user was not looking
            # at. The process test is the one that means what it says.
            return None
        try:
            bMine = functionScript is not None
            bInEdge = self._focusAppName() == "msedge"
            if bMine or bInEdge:
                lIdentifiers = list(getattr(gesture, "normalizedIdentifiers", None) or [])
                sName = getattr(functionScript, "__name__", "") if functionScript else ""
                homerLog.debug(
                    f"Key seen globally: {lIdentifiers} -> {sName or 'no global command'}"
                    f"{' (HomerView)' if bMine else ''}, focus in "
                    f"{self._focusAppName() or 'unknown'}"
                )
        except Exception:
            pass
        return functionScript

    def _focusIsHomerViewEdge(self):
        """Say whether the focused window belongs to HomerView's own browser.

        The process identifiers are what distinguish HomerView's Edge from any
        other. They are already tracked, because every object NVDA creates is
        tested against them, so this costs an integer set lookup.

        Before the browser has been launched there are no identifiers to
        compare, and the name test is the best available answer; it is used
        only then, and only to decide whether a key is HomerView's, never to
        decide what to act on.
        """
        try:
            focus = api.getFocusObject()
            iProcessId = getattr(focus, "processID", 0)
            if service.setProcessIds:
                bMine = iProcessId in service.setProcessIds
                if not bMine:
                    homerLog.debug(
                        f"Focus is process {iProcessId}, not one of HomerView's "
                        f"{sorted(service.setProcessIds)}"
                    )
                return bMine
        except Exception:
            logError("The focused process could not be identified")
        return self._focusAppName() == "msedge"

    def _focusAppName(self):
        try:
            return (getattr(getattr(api.getFocusObject(), "appModule", None), "appName", "") or "").lower()
        except Exception:
            return ""

    def event_gainFocus(self, obj, nextHandler):
        """Confirm the browse mode commands are attached, and attach them if not.

        The weak set check comes first so this costs almost nothing on repeat
        focus events, and nothing here performs input or output.
        """
        try:
            self._ensureBufferCommands(obj)
        except Exception:
            logError("Checking the tree interceptor raised")
        try:
            self._rememberForeignEdgePage(obj)
        except Exception:
            logError("Noting the foreign Edge page raised")
        nextHandler()

    def _rememberForeignEdgePage(self, obj):
        """Note the address of an Edge page that HomerView did not open.

        There is no way to give a running browser a debugging connection, so the
        best that can be done is to carry the user's place across when HomerView
        does open its own window. This reads one property and performs no input
        or output, so it is safe on the thread that drives speech.
        """
        try:
            sAppName = (getattr(getattr(obj, "appModule", None), "appName", "") or "").lower()
            if sAppName != "msedge":
                return
            if service.isHomerViewProcess(getattr(obj, "processID", 0)):
                return
            treeInterceptor = getattr(obj, "treeInterceptor", None)
            if not treeInterceptor:
                return
            sAddress = (getattr(treeInterceptor, "documentConstantIdentifier", "") or "").strip()
            if "://" not in sAddress or sAddress == service.sForeignEdgeUrl:
                return
            service.sForeignEdgeUrl = sAddress
            homerLog.info(
                "Noted an Edge page HomerView did not open, in case it should be carried "
                f"across on the next launch: {abbreviate(sAddress, 300)}"
            )
        except Exception:
            logError("The foreign Edge address could not be noted")

    def _ensureBufferCommands(self, obj):
        treeInterceptor = getattr(obj, "treeInterceptor", None)
        if not treeInterceptor:
            return
        try:
            if treeInterceptor in self.setInterceptorsSeen:
                return
        except TypeError:
            # Not weak referenceable. Binding twice is harmless, so continue.
            pass
        if not service.isHomerViewObject(obj):
            return
        try:
            self.setInterceptorsSeen.add(treeInterceptor)
        except TypeError:
            pass
        homerLog.info(
            "Tree interceptor for a HomerView page: method resolution order is "
            f"{[cls.__name__ for cls in type(treeInterceptor).__mro__]}"
        )
        if isinstance(treeInterceptor, HomerViewBuffer):
            homerLog.info("Preferred route used: the composed class is in effect")
            self._logBoundGestures(treeInterceptor)
            return
        homerLog.warning(
            "The composed class did not take effect, so the fallback route is being used. "
            "The two browse mode commands will work but will not appear in Input Gestures."
        )
        bindFallbackGestures(treeInterceptor)
        self._logBoundGestures(treeInterceptor)

    def _logBoundGestures(self, treeInterceptor):
        """Record the gesture map, so a missing binding is visible immediately."""
        try:
            dMap = getattr(treeInterceptor, "_gestureMap", None) or {}
            lHomer = sorted(
                f"{sKey} -> {getattr(vScript, '__name__', vScript)}"
                for sKey, vScript in dMap.items()
                if hasattr(HomerViewBuffer, getattr(vScript, "__name__", "") or "")
            )
            homerLog.info(f"HomerView gestures bound on this page: {len(lHomer)}")
            for sLine in lHomer:
                homerLog.debug(f"  bound {sLine}")
            lOther = len(dMap) - len(lHomer)
            homerLog.debug(f"Other gestures bound by NVDA on this buffer: {lOther}")
        except Exception:
            logError("The gesture map could not be recorded")

    @script(
        # Translators: Input help mode message for the launch command.
        description=_("Launch or reconnect the HomerView instance of Microsoft Edge"),
        category="HomerView",
        gesture="kb:NVDA+alt+h",
    )
    def script_launchHomerView(self, gesture):
        homerLog.info("Command: launch or reconnect")
        # Translators: Reported while HomerView Edge is starting.
        ui.message(_("Starting HomerView Edge"))
        service.submit(
            "launch",
            service.taskLaunch,
            self._reportLaunched,
            self._reportError,
        )

    @script(
        # Translators: Input help mode message for the connection status command.
        description=_("Report whether HomerView is connected to Microsoft Edge"),
        category="HomerView",
    )
    def script_reportConnection(self, gesture):
        homerLog.info("Command: report the connection status")
        if service.isConnected():
            homerLog.info(
                f"Connected on port {service.iPort} with process identifiers "
                f"{sorted(service.setProcessIds)}"
            )
            # Translators: Reported when HomerView has a working connection.
            ui.message(_("HomerView is connected on port {port}").format(port=service.iPort))
        else:
            homerLog.info("Not connected")
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))

    @script(
        # Translators: Input help mode message for the dismiss dialog command.
        description=_("Close a Microsoft Edge dialog that is blocking the HomerView window"),
        category="HomerView",
        gesture="kb:NVDA+alt+d",
    )
    def script_dismissDialog(self, gesture):
        homerLog.info("Command: dismiss a blocking dialog")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))
            return
        service.submit("closeDialogs", service.taskCloseDialogs, self._reportDialogsClosed, self._reportError)

    @script(
        # Translators: Input help mode message for the accessibility report command.
        description=_(
            "Tests the current HomerView page for accessibility problems, finds how to "
            "report them to the publisher, and opens the report in a new tab"
        ),
        category="HomerView",
        gesture="kb:NVDA+alt+a",
    )
    def script_accessibilityReport(self, gesture):
        homerLog.info("Command: accessibility report")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))
            return
        # Translators: Reported while the accessibility test is running.
        ui.message(_("Testing the page and looking for reporting channels"))
        service.submit(
            "accessibilityReport",
            service.taskAccessibilityReport,
            self._reportAccessibilityReport,
            self._reportError,
        )

    @script(
        # Translators: Input help mode message for the quick axe command.
        description=_("Tests the current HomerView page with axe-core and reports the counts only"),
        category="HomerView",
    )
    def script_runAxe(self, gesture):
        homerLog.info("Command: run axe-core")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))
            return
        # Translators: Reported while the accessibility test is running.
        ui.message(_("Testing the page with axe-core"))
        service.submit("runAxe", service.taskRunAxe, self._reportAxeResults, self._reportError)

    @script(
        # Translators: Input help mode message for the page explorer command.
        description=_(
            "Summarises the structure of the current HomerView page, the visual aspects a "
            "reading order hides, and how best to move around it"
        ),
        category="HomerView",
        gesture="kb:NVDA+alt+e",
        speakOnDemand=True,
    )
    def script_explorePage(self, gesture):
        homerLog.info("Command: explore the page")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))
            return
        # Translators: Reported while the page structure is analysed.
        ui.message(_("Exploring the page"))
        service.submit(
            "explorePage", service.taskExplorePage, self._showPageSummary, self._reportError
        )

    @script(
        # Translators: Input help mode message for the main content command.
        description=_(
            "Extracts the readable part of the current HomerView page and opens it "
            "as a plain document in a new tab"
        ),
        category="HomerView",
        gesture="kb:NVDA+alt+x",
    )
    def script_extractMainContent(self, gesture):
        homerLog.info("Command: extract the main content")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))
            return
        # Translators: Reported while the readable part of the page is found.
        ui.message(_("Extracting the main content"))
        service.submit(
            "extractMainContent",
            service.taskExtractMainContent,
            self._reportMainContent,
            self._reportError,
        )

    @script(
        # Translators: Input help mode message for the download command.
        description=_(
            "Lists the file types linked from the current HomerView page, then downloads "
            "the ones you choose"
        ),
        category="HomerView",
        gesture="kb:NVDA+alt+w",
    )
    def script_downloadFiles(self, gesture):
        homerLog.info("Command: download files")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))
            return
        # Translators: Reported while the page's links are examined.
        ui.message(_("Looking for downloadable links"))
        service.submit(
            "analyseLinks",
            service.taskAnalyseLinks,
            self._askWhichExtensions,
            self._reportError,
        )

    @script(
        # Translators: Input help mode message for the alternate menu command.
        description=_("Lists every HomerView command in one alphabetical list"),
        category="HomerView",
        gesture="kb:NVDA+alt+f10",
    )
    def script_alternateMenu(self, gesture):
        """The menu, on one key that always works.

        There was a second, shorter key, Alt+F10, bound inside a HomerView page
        in the Homer tradition. It has been removed, and the reasoning is worth
        recording because brevity is usually the right call and here it is not.

        This is the command a person reaches for when they do not know what
        they are looking for. A key that answers in a page and does nothing in
        the address bar is indistinguishable, from the keyboard, from a key
        that is broken; and a discovery command that appears broken is worse
        than a longer one that never is. This project has watched that exact
        failure more than once, with a command silently out of scope and a
        tester reasonably concluding it did not work.

        So there is one key. It carries the NVDA modifier, which means NVDA
        takes it before any program sees it, so it works in the address bar, in
        a form field, in another application, and before Microsoft Edge has
        been started at all.

        Alt+F10 exists inside a HomerView page, matching the Homer interface.
        This one works everywhere, including before Edge has been launched,
        because a list of commands is no use if finding it needs a command.
        """
        homerLog.info("Command: alternate menu, from anywhere")
        logThreadContext("Alternate menu")
        lEntries = []
        treeInterceptor = getattr(api.getFocusObject(), "treeInterceptor", None)
        if isinstance(treeInterceptor, HomerViewBuffer):
            homerLog.info("A HomerView page has focus, so page commands are included")
            lEntries = treeInterceptor.buildCommandEntries()
        else:
            homerLog.info("No HomerView page has focus, so only global commands are listed")
            lEntries = service.buildGlobalCommandEntries()
            lEntries.append(
                alternateMenu.CommandEntry(
                    # Translators: Shown in the menu when no HomerView page has focus.
                    _("Page commands are not listed"), "",
                    _(
                        "The reading, selection, search and clipboard commands exist only "
                        "inside a HomerView page, and the commands that act on a page are "
                        "left out until there is one. Choose Launch HomerView Edge above, "
                        "then open this menu again from the page that opens."
                    ),
                    lambda: None, "Anywhere",
                )
            )
        alternateMenu.showAlternateMenu(lEntries)

    @script(
        # Translators: Input help mode message for the open other format command.
        description=_(
            "Opens a document of any popular format, converting it to a web page first "
            "so that every HomerView command works on it"
        ),
        category="HomerView",
        # Control+F10 was the original suggestion and was later superseded by
        # Control+O, which is Edge's own key for this and a strict superset of
        # what Edge does with it. One key for one command is clearer.
        gesture="kb:control+o",
    )
    def script_openOtherFormat(self, gesture):
        # Deferred like every other dialog, so NVDA has finished the script
        # before the file picker opens and can therefore announce it.
        lbc.afterScript(self._openOtherFormatNow)

    def _openOtherFormatNow(self):
        homerLog.info("Command: open another format")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("Press Alt+NVDA+H first to start HomerView Edge"))
            return
        def onPath(sPath):
            if not sPath:
                homerLog.info("Open cancelled")
                return
            # Translators: Reported while a document is converted and opened.
            ui.message(_("Opening {name}").format(name=os.path.basename(sPath)))
            service.submit(
                "openOtherFormat",
                service.makeOpenFileTask(sPath),
                self._reportOpened,
                self._reportError,
            )

        lbc.dialogOpenFile(
            # Translators: Title of the dialog for opening a document.
            _("Open a document in HomerView"), "", convert.buildOpenWildcard(),
            functionDone=onPath,
        )

    @script(
        # Translators: Input help mode message for the save as command.
        description=_("Saves the current HomerView page as a web page, Markdown, or plain text"),
        category="HomerView",
        gestures=["kb:control+s", "kb:control+alt+s"],
    )
    def script_saveAs(self, gesture):
        homerLog.info("Command: save as")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("HomerView is not connected"))
            return
        lbc.afterScript(self._saveAsNow)

    def _saveAsNow(self):
        lLabels = [f"{sExtension} - {sText}" for sExtension, sText in convert.dSaveFormats.items()]
        sChoice = lbc.dialogChoose(
            # Translators: Title of the dialog choosing a save format.
            _("Save the page as"),
            # Translators: Prompt in the save format dialog.
            _("All three keep the page as it stands now, after any script has run."),
            lLabels,
        )
        if not sChoice:
            homerLog.info("Save cancelled at the format choice")
            return
        sFormat = sChoice.split(" - ")[0].strip()
        sExtension = sFormat if sFormat != "dom.htm" else "dom.htm"
        sSuggested = f"page.{sExtension}"
        try:
            obj = api.getFocusObject()
            sTitle = (getattr(getattr(obj, "treeInterceptor", None), "rootNVDAObject", None) or obj)
            sName = (getattr(sTitle, "name", "") or "").strip()
            if sName:
                sSuggested = "".join(c for c in sName if c not in '\\/*?:"<>|')[:80] + f".{sExtension}"
        except Exception:
            pass
        sPath = lbc.dialogSaveFile(
            # Translators: Title of the dialog for saving the page.
            _("Save the HomerView page"),
            str(paths.getDownloadsFolder() / sSuggested),
            f"{sExtension} files (*.{sExtension})|*.{sExtension}|All files (*.*)|*.*",
        )
        if not sPath:
            homerLog.info("Save cancelled at the file dialog")
            return
        # Translators: Reported while the page is being saved.
        ui.message(_("Saving"))
        service.submit(
            "saveAs",
            service.makeSaveAsTask("", sPath, sFormat),
            self._reportSaved,
            self._reportError,
        )

    @script(
        # Translators: Input help mode message for the recent pages command.
        description=_(
            "Recently opened: lists the pages and documents you have opened in "
            "HomerView, with when each was opened, so you can find something again"
        ),
        category="HomerView",
    )
    def script_recentPages(self, gesture):
        homerLog.info("Command: recent pages")
        lRows = history.recent("", 60)
        dStore = history.describe()
        lParts = ["<h1>Recently opened</h1>"]
        lParts.append(
            f"<p>{len(lRows)} entries, newest first, from "
            f"{selfTest.escape(dStore.get('path', ''))}.</p>"
        )
        if not lRows:
            lParts.append("<p>Nothing has been recorded yet in this installation.</p>")
        else:
            # A list rather than a table. The reader is using a screen reader,
            # and a list is quicker to move through than four columns of which
            # three are usually the same.
            lParts.append("<ul>")
            for dRow in lRows:
                sWhen = str(dRow.get("recordedUtc", ""))[:16].replace("T", " at ")
                sTitle = str(dRow.get("title", "")).strip()
                sAddress = str(dRow.get("address", "")).strip()
                sKind = str(dRow.get("kind", "")).replace("Opened", " opened").replace(
                    "Viewed", " viewed").replace("Information", " information").replace(
                    "Scan", " scan")
                lPieces = [selfTest.escape(sTitle or sAddress or "untitled")]
                if sAddress and sTitle:
                    lPieces.append(
                        f'<a href="{selfTest.escape(sAddress)}">'
                        f"{selfTest.escape(sAddress)}</a>")
                lPieces.append(selfTest.escape(f"{sKind}, {sWhen}"))
                lParts.append("<li>" + "<br>".join(lPieces) + "</li>")
            lParts.append("</ul>")
        # Translators: Title of the history window.
        sTitle = _("HomerView history")
        output.show("\n".join(lParts), sTitle)

    @script(
        # Translators: Input help mode message for the report address command.
        description=_("Reports the web address of the HomerView page, from anywhere in the window"),
        category="HomerView",
        # Not NVDA+A: that is Say All on NVDA's laptop layout, and a HomerView
        # command must never shadow an NVDA default on either layout.
        gesture="kb:NVDA+alt+u",
        speakOnDemand=True,
    )
    def script_reportAddressAnywhere(self, gesture):
        """Report the address when the browse mode command cannot.

        A command bound to the browse mode document only exists while that
        document has focus and is in browse mode. Press it from the address
        bar, from a toolbar, or from inside a form field in focus mode, and it
        never reaches the buffer at all: nothing runs, so nothing is spoken,
        and the key looks broken rather than inapplicable.

        This is the same command bound a second time, on the global plugin,
        where it is reached whatever has focus. It asks the browser rather than
        the buffer, so it works from anywhere in the window. It exists only
        while Microsoft Edge has focus, so it shadows nothing elsewhere.
        """
        homerLog.info("Command: report the page address, from anywhere")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("Press Alt+NVDA+H first to start HomerView Edge"))
            return
        service.submit(
            "activePageUrl",
            service.taskActivePageUrl,
            lambda sUrl: ui.message(sUrl or _("The web address is unavailable")),
            lambda exception: ui.message(_("The web address is unavailable")),
        )

    @script(
        # Translators: Input help mode message for the submit form command.
        description=_("Submits the form you are filling in, from any field"),
        category="HomerView",
        gesture="kb:control+enter",
    )
    def script_submitForm(self, gesture):
        homerCommandsModule.submitForm()

    @script(
        # Translators: Input help mode message for the Copilot command.
        description=_(
            "Ask Copilot about this page: copies the page text to the clipboard and "
            "opens Microsoft Edge's Copilot sidebar, ready for you to paste with "
            "Control+V and ask a question"
        ),
        category="HomerView",
        gesture="kb:NVDA+alt+p",
    )
    def script_openCopilot(self, gesture):
        homerLog.info("Command: open Copilot")
        if not service.isConnected():
            # Translators: Reported when HomerView has no connection.
            ui.message(_("Press Alt+NVDA+H first to start HomerView Edge"))
            return
        # Translators: Reported while Copilot is opened.
        ui.message(_("Opening Copilot"))
        service.submit("openCopilot", service.taskOpenCopilot, self._reportCopilot,
                       self._reportError)

    def _reportCopilot(self, dContext):
        homerLog.info(f"Copilot: {dContext}")
        if not dContext.get("sent"):
            # Translators: Reported when the Copilot shortcut could not be sent.
            ui.message(_("Copilot could not be opened. The log has the detail."))
            return
        # Translators: Reported after opening Copilot. The placeholder is a count.
        ui.message(
            _("Copilot opened. {characters} characters of the page are on the clipboard, "
              "ready to paste with Control+V.").format(characters=dContext.get("characters", 0))
        )

    @script(
        # Translators: Input help mode message for the quick start command.
        description=_("Opens the HomerView quick start in the HomerView window"),
        category="HomerView",
    )
    def script_openQuickStart(self, gesture):
        documents.openDocument("readMe")

    @script(
        # Translators: Input help mode message for the user guide command.
        description=_("Opens the HomerView user guide in the HomerView window"),
        category="HomerView",
    )
    def script_openUserGuide(self, gesture):
        documents.openDocument("guide")

    @script(
        # Translators: Input help mode message for the history command.
        description=_("Opens the HomerView history of changes in the HomerView window"),
        category="HomerView",
    )
    def script_openHistory(self, gesture):
        documents.openDocument("history")

    @script(
        # Translators: Input help mode message for the developer notes command.
        description=_("Opens the HomerView developer notes in the HomerView window"),
        category="HomerView",
    )
    def script_openDeveloperNotes(self, gesture):
        documents.openDocument("developer")

    @script(
        # Translators: Input help mode message for the elevate version command.
        description=_("Checks for a newer HomerView and installs it"),
        category="HomerView",
        gesture="kb:NVDA+alt+f11",
    )
    def script_elevateVersion(self, gesture):
        homerCommandsModule.elevateVersion()

    @script(
        # Translators: Input help mode message for the web utilities command.
        description=_("Looks something up using free web services that need no account"),
        category="HomerView",
        gesture="kb:NVDA+alt+q",
    )
    def script_webUtilities(self, gesture):
        homerCommandsModule.webUtilities()

    @script(
        # Translators: Input help mode message for the self test command.
        description=_("Check that all three ways of reaching the browser are working"),
        category="HomerView",
    )
    def script_selfTest(self, gesture):
        homerLog.info("Command: self test")
        obj = api.getFocusObject()
        treeInterceptor = getattr(obj, "treeInterceptor", None)
        lUi, bUi, lBuffer, bBuffer = selfTest.runNvdaSide(treeInterceptor)
        self._dSelfTest = {
            _("The browser window, through NVDA objects and the Windows API"): (lUi, bUi),
            _("The page as NVDA built it, through browse mode"): (lBuffer, bBuffer),
        }
        if not service.isConnected():
            self._dSelfTest[_("The page through the DevTools Protocol")] = (
                [("Result", "HomerView is not connected. Press Alt+NVDA+H first.")], False
            )
            self._showSelfTest(None)
            return
        # Translators: Reported while the self test runs.
        ui.message(_("Running the self test"))
        service.submit("selfTest", service.taskSelfTest, self._showSelfTest, self._reportError)

    def _showSelfTest(self, tProtocol):
        if tProtocol:
            lFindings, bQuery, bAction = tProtocol
            self._dSelfTest[_("The protocol, asking the browser")] = (lFindings, bQuery)
            self._dSelfTest[_("The protocol, acting on the browser")] = (
                [("Result", "an input event was accepted" if bAction else "no input event was accepted")],
                bAction,
            )
        sHtml = selfTest.buildReportHtml(self._dSelfTest)
        # Translators: Title of the self test window.
        sTitle = _("HomerView self test")
        output.show(sHtml, sTitle)

    @script(
        # Translators: Input help mode message for the open log command.
        description=_("Open the HomerView log file for this session"),
        category="HomerView",
    )
    def script_openLog(self, gesture):
        homerLog.info("Command: open the log file")
        if not logger.pathLogFile:
            # Translators: Reported when no log file could be created.
            ui.message(_("No HomerView log file is available"))
            return
        ui.message(str(logger.pathLogFile))
        try:
            # A copy, not the file itself. HomerView holds the log open for
            # writing for as long as NVDA is running, and an editor that asks
            # Windows for exclusive read cannot open it while that handle
            # exists. EdSharp is one such editor, and it fails with a stack
            # trace that says the file is in use by another process, which is
            # true and unhelpful.
            #
            # Copying costs a few milliseconds and removes the question. The
            # copy is named for the moment it was taken, so two of them can sit
            # side by side, and it goes in the temporary folder that Windows
            # clears on its own.
            import shutil
            import time as timeModule

            from . import paths as pathsModule

            logger.flushLog()
            pathCopy = (pathsModule.getTempFolder()
                        / f"HomerView-{timeModule.strftime('%Y%m%d-%H%M%S')}.log")
            try:
                shutil.copyfile(str(logger.pathLogFile), str(pathCopy))
                homerLog.info(f"Opening a copy of the log at {pathCopy}")
                os.startfile(str(pathCopy))
            except OSError:
                logError("The log could not be copied, so the original is being opened")
                os.startfile(str(logger.pathLogFile))
        except Exception:
            logError("Opening the log file raised")

    def _reportAxeResults(self, dSummary):
        dCounts = dSummary.get("counts", {})
        homerLog.info(f"axe-core finished: {dSummary}")
        # Translators: Reported after an accessibility test. The placeholders are
        # counts of axe-core results and the file the results were saved to.
        ui.message(
            _(
                "{violations} violations, {incomplete} needing review, {passes} passes. "
                "Saved to {path}"
            ).format(
                incomplete=dCounts.get("incomplete", 0),
                passes=dCounts.get("passes", 0),
                path=dSummary.get("path", ""),
                violations=dCounts.get("violations", 0),
            )
        )

    def _reportAccessibilityReport(self, dSummary):
        dCounts = dSummary.get("counts", {})
        dContacts = dSummary.get("contacts", {})
        iChannels = (
            dContacts.get("mailto", 0)
            + dContacts.get("accessibility", 0)
            + dContacts.get("contact", 0)
            + dContacts.get("social", 0)
        )
        homerLog.info(f"Report reported to the user: {dSummary}")
        # Translators: Reported after an accessibility report is generated.
        ui.message(
            _(
                "{violations} violations, {incomplete} needing review. "
                "{channels} reporting channels found. Report opened in a new tab."
            ).format(
                channels=iChannels,
                incomplete=dCounts.get("incomplete", 0),
                violations=dCounts.get("violations", 0),
            )
            if dSummary.get("opened")
            # Translators: Reported when the report was written but not opened.
            else _(
                "{violations} violations, {incomplete} needing review. "
                "{channels} reporting channels found. Saved to {path}"
            ).format(
                channels=iChannels,
                incomplete=dCounts.get("incomplete", 0),
                path=dSummary.get("reportPath", ""),
                violations=dCounts.get("violations", 0),
            )
        )

    def _showPageSummary(self, dSummary):
        """Put the summary in NVDA's browseable message window.

        This is NVDA's counterpart to the JAWS Results Viewer: a virtual
        document that can be read with the usual browse mode keys and closed
        with Escape.
        """
        homerLog.info(
            f"Page summary ready for {abbreviate(dSummary.get('title', ''), 120)}, "
            f"{dSummary.get('regions')} landmarks, {dSummary.get('visualCount')} visual notes"
        )
        # Translators: Title of the page summary window.
        sTitle = _("HomerView page explorer")
        try:
            ui.browseableMessage(dSummary["html"], sTitle, True)
        except TypeError:
            # Older signatures take the arguments by keyword only.
            ui.browseableMessage(dSummary["html"], title=sTitle, isHtml=True)

    def _announceDownload(self, sName):
        """Speak one file name from the worker thread."""
        wx.CallAfter(ui.message, sName)

    def _reportMainContent(self, dSummary):
        homerLog.info(f"Main content extracted: {dSummary}")
        try:
            service.openInTab(dSummary["pathUri"])
        except Exception:
            logError("Could not open the extracted document in a tab")
            ui.message(dSummary.get("path", ""))
            return
        # Translators: Reported after extracting the readable part of a page.
        ui.message(
            _("Main content extracted, {characters} characters, opened in a new tab").format(
                characters=dSummary.get("characters", 0)
            )
        )

    def _askWhichExtensions(self, dAnalysis):
        """Show what was found, then let the user say which types to fetch.

        Two fields rather than one prompt. What was found runs to a dozen lines
        or more and belongs in a box a reader can move through by line;
        squeezed into a prompt above a text box it becomes one long sentence
        that has to be heard in a single breath.

        The editable field holds the extensions alone, alphabetically and
        without counts, because it is a list to be edited rather than a report
        to be read. Counts in a field the user types into would only have to be
        deleted before the field was usable.
        """
        import wx

        from .homer import lbc as lbcModule

        lExtensions = dAnalysis.get("extensions") or []
        if not lExtensions:
            # Translators: Reported when a page links to no downloadable files.
            ui.message(_("No downloadable files are linked from this page"))
            return
        dCounts = dAnalysis.get("counts") or {}
        lDefault = dAnalysis.get("default") or lExtensions

        lFound = [
            # Translators: First line of the box listing what was found. The
            # placeholder is how many files were found.
            _("{count} files are linked from this page.").format(
                count=len(dAnalysis.get("links") or [])),
            "",
        ]
        lFound.extend(download.describeExtensions(sorted(lExtensions), dCounts))

        dialog = lbcModule.Dialog(sTitle=_("Download linked files"))
        dialog.addMemo(
            # Translators: Label of the read-only list of what was found.
            _("&What this page offers:"),
            "\n".join(lFound), bReadOnly=True, sName="found")
        dialog.addBand()
        dialog.addInputBox(
            # Translators: Label of the editable list of extensions.
            _("&Types to download, separated by spaces:"),
            " ".join(sorted(lDefault)), sName="types",
            sTip=_("Every type found is listed above. Add or remove any of them here."))
        dialog.addBand()
        dResults = dialog.complete(["OK", "Cancel"], 0)
        if dResults.get("result") != wx.ID_OK:
            homerLog.info("Download cancelled")
            return

        lChosen = download.parseExtensions(dResults.get("types", ""))
        if not lChosen:
            # Translators: Reported when the user cleared the extension list.
            ui.message(_("No file types were chosen"))
            return
        iFiles = len([d for d in dAnalysis["links"] if d.get("extension") in set(lChosen)])
        homerLog.info(f"User chose {lChosen}, {iFiles} files")
        # Translators: Reported when downloading starts.
        ui.message(_("Downloading {count} files").format(count=iFiles))
        service.submit(
            "downloadFiles",
            service.makeDownloadTask(dAnalysis, lChosen, self._announceDownload),
            self._reportDownloads,
            self._reportError,
        )

    def _reportDownloads(self, dSummary):
        """Say what arrived and what did not, in one box that can be copied.

        One shape for every outcome. A count spoken and gone is no use when
        eleven files were attempted and one arrived: the reader wants to know
        which, and why the others did not, and to be able to read it twice.
        """
        from . import output

        homerLog.info(f"Downloads finished: {dSummary}")
        iSaved = dSummary.get("saved", 0)
        iFailed = dSummary.get("failed", 0)
        if not iSaved and not iFailed:
            # Translators: Reported when nothing matched the chosen types.
            ui.message(_("No files matched the types you chose"))
            return

        lLines = []
        if iSaved:
            # Translators: Line in the download results. The placeholders are
            # how many files arrived and the folder holding them.
            lLines.append(_("{count} saved to {folder}").format(
                count=iSaved, folder=dSummary.get("folder", "")))
            lNames = [d.get("name", "") for d in (dSummary.get("files") or []) if d.get("name")]
            for sName in lNames[:20]:
                lLines.append("  " + sName)
            if len(lNames) > 20:
                # Translators: Shown when more files arrived than are listed.
                lLines.append(_("  and {count} more").format(count=len(lNames) - 20))
        else:
            # Translators: Line in the download results when nothing arrived.
            lLines.append(_("Nothing was saved."))

        if iFailed:
            lLines.append("")
            # Translators: Line in the download results. The placeholder is how
            # many files did not arrive.
            lLines.append(_("{count} did not arrive:").format(count=iFailed))
            dReasons = dSummary.get("reasons") or {}
            for sReason, iCount in sorted(dReasons.items(), key=lambda tPair: -tPair[1]):
                lLines.append(f"  {iCount}, {sReason}")
            if not dReasons:
                # Translators: Shown when the reasons could not be grouped.
                lLines.append(_("  the log has the detail"))

        output.lines(_("Download results"), lLines)

    def _reportOpened(self, dSummary):
        homerLog.info(f"Opened: {dSummary}")
        if dSummary.get("converted"):
            # Translators: Reported after converting and opening a document.
            ui.message(_("{name} converted and opened").format(name=dSummary.get("name", "")))
        else:
            # Translators: Reported after opening a file the browser reads directly.
            ui.message(_("{name} opened").format(name=dSummary.get("name", "")))

    def _reportSaved(self, dSummary):
        homerLog.info(f"Saved: {dSummary}")
        # Translators: Reported after saving the page.
        ui.message(
            _("Saved {name}, {characters} characters").format(
                characters=dSummary.get("characters", 0), name=dSummary.get("name", "")
            )
        )

    def _reportDialogsClosed(self, lDialogs):
        if not lDialogs:
            # Translators: Reported when no blocking dialog was present.
            ui.message(_("No Microsoft Edge dialog was blocking HomerView"))
            return
        # Translators: Reported after closing blocking dialogs.
        ui.message(_("Closed {count} Microsoft Edge dialog").format(count=len(lDialogs)))

    def _reportLaunched(self, dConnection):
        homerLog.info(f"Launch reported to the user: {dConnection}")
        if dConnection.get("existing"):
            if not dConnection.get("activated"):
                # Translators: Reported when Windows refused to raise the window.
                ui.message(_(
                    "HomerView is already running, but Windows would not bring its window "
                    "forward. Try Alt+Tab."))
            elif not dConnection.get("port"):
                # Translators: Reported when the window is open but unusable.
                ui.message(_(
                    "HomerView window opened, but its connection is gone, so commands will "
                    "not work. Close it and press Alt+NVDA+H again."))
            else:
                # Translators: Reported when an existing window was brought forward.
                ui.message(_("HomerView"))
            return
        sCarried = dConnection.get("carried") or ""
        if sCarried:
            # Translators: Reported when the page from another Edge window was
            # reopened in the HomerView window.
            ui.message(
                _("HomerView Edge is ready, and reopened the page you were on")
            )
            return
        lDialogs = dConnection.get("dialogs") or []
        if lDialogs:
            # Translators: Reported when Edge opened a dialog that blocks the window.
            ui.message(
                _(
                    "HomerView Edge is ready, but Microsoft Edge is showing a dialog that may "
                    "block the address bar. Press Alt+NVDA+D to close it."
                )
            )
            return
        # Translators: Reported once HomerView Edge is ready.
        ui.message(_("HomerView Edge is ready"))

    def _reportError(self, exception):
        homerLog.error(f"Launch failed: {exception}")
        ui.message(str(exception))

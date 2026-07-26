"""The HomerView service: one worker thread, one connection, one identity test.

Two rules govern this module.

First, no network call ever runs on NVDA's main thread. Everything that touches
Edge is queued to a single worker, and results return through wx.CallAfter.

Second, the test for "is this object inside HomerView Edge" must be free of
input and output, because it runs on every focus change. It is therefore an
integer comparison against a cached set of process identifiers, never a
comparison of window titles, which are truncated, duplicated across tabs, and
empty during navigation.

Every task is logged with its outcome and its duration, so a sluggish command
can be traced to the step that cost the time.
"""

import queue
import threading
import time
import wx
from pathlib import Path

from . import ace
from . import act
from . import axe
from . import contacts
from . import copilot
from . import exportReport
from . import formSubmit
from . import convert
from . import download
from . import logger
from . import metadata
from .history import history
from . import mainContent
from . import pageExplorer
from . import paths
from . import report
from .cdp import CdpSession
from .edge import EdgeManager
from .logger import homerLog, logError, logSection, logThreadContext

# Set to False to write the report files without opening a tab for them.
bOpenReportTab = True

shutdownTaskName = "shutdown"


class Task:
    def __init__(self, sName, functionTask, functionSuccess, functionError):
        self.functionError = functionError
        self.functionSuccess = functionSuccess
        self.functionTask = functionTask
        self.nQueued = time.monotonic()
        self.sName = sName


class HomerViewService:
    def __init__(self):
        self.cdpSession = CdpSession()
        self.edgeManager = EdgeManager()
        self.iPort = 0
        self.lGlobalCommands = []
        self.functionOpenDocument = lambda: None
        self.sCarriedUrl = ""
        self.sForeignEdgeUrl = ""
        self.lPendingDialogs = []
        self.queueTasks = queue.Queue()
        self.setProcessIds = frozenset()
        self.threadWorker = None

    # Worker

    def start(self):
        if self.threadWorker and self.threadWorker.is_alive():
            return
        self.threadWorker = threading.Thread(
            target=self._workLoop,
            name="HomerViewWorker",
            daemon=True,
        )
        self.threadWorker.start()
        homerLog.info("Worker thread started")

    def stop(self):
        homerLog.info("Worker thread stop requested")
        self.queueTasks.put(Task(shutdownTaskName, None, None, None))
        try:
            self.cdpSession.close()
        except Exception:
            logError("Closing the DevTools session raised")

    def submit(self, sName, functionTask, functionSuccess=None, functionError=None):
        self.start()
        homerLog.debug(f"Task queued: {sName}, depth now {self.queueTasks.qsize() + 1}")
        self.queueTasks.put(Task(sName, functionTask, functionSuccess, functionError))

    def _workLoop(self):
        while True:
            task = self.queueTasks.get()
            if task.sName == shutdownTaskName:
                homerLog.info("Worker thread exiting")
                return
            nWaited = time.monotonic() - task.nQueued
            homerLog.debug(f"Task starting: {task.sName} after {nWaited:.3f} seconds in the queue")
            logThreadContext(f"Task {task.sName}", bExpectMain=False)
            nStarted = time.monotonic()
            try:
                result = task.functionTask()
            except Exception as exception:
                nElapsed = time.monotonic() - nStarted
                logError(f"Task failed: {task.sName} after {nElapsed:.3f} seconds")
                if task.functionError:
                    wx.CallAfter(task.functionError, exception)
                continue
            nElapsed = time.monotonic() - nStarted
            homerLog.info(f"Task finished: {task.sName} in {nElapsed:.3f} seconds")
            if task.functionSuccess:
                wx.CallAfter(task.functionSuccess, result)

    # Identity

    def isHomerViewProcess(self, iProcessId):
        """Free of input and output. Safe to call on NVDA's main thread."""
        return bool(iProcessId) and iProcessId in self.setProcessIds

    def isHomerViewObject(self, obj):
        appModule = getattr(obj, "appModule", None)
        sAppName = (getattr(appModule, "appName", "") or "").lower()
        if sAppName != "msedge":
            return False
        iProcessId = getattr(obj, "processID", 0)
        bMatch = self.isHomerViewProcess(iProcessId)
        homerLog.debug(
            f"Identity test: appName={sAppName} processId={iProcessId} "
            f"known={sorted(self.setProcessIds)} match={bMatch}"
        )
        return bMatch

    def refreshProcessIds(self):
        setProcessIds = set()
        try:
            setProcessIds = self.cdpSession.getBrowserProcessIds()
        except Exception:
            logError("SystemInfo.getProcessInfo was unavailable, falling back to the launched process id")
        if not setProcessIds and self.edgeManager.iProcessId and not self.edgeManager.bLauncherExited:
            setProcessIds.add(self.edgeManager.iProcessId)
            homerLog.debug(
                f"No browser identifier came from the protocol, so the launched process id "
                f"{self.edgeManager.iProcessId} is used instead"
            )
        self.setProcessIds = frozenset(setProcessIds)
        self.edgeManager.setProcessIds = set(setProcessIds)
        homerLog.info(f"HomerView process identifiers: {sorted(self.setProcessIds)}")
        if not self.setProcessIds:
            homerLog.warning(
                "No process identifiers are known, so no document will be treated as a "
                "HomerView page and the browse mode commands will not appear"
            )
        return self.setProcessIds

    # Connection

    def isConnected(self):
        return self.cdpSession.isConnected()

    def taskAttach(self):
        """Reconnect to a HomerView Edge left running by an earlier session."""
        logSection("Attaching to a running HomerView Edge")
        iPort = self.edgeManager.attach()
        if not iPort:
            homerLog.info("Attach: no running instance was found")
            return False
        self.cdpSession.connect(iPort)
        self.iPort = iPort
        self.refreshProcessIds()
        homerLog.info("Attach: succeeded")
        return True

    def taskLaunch(self):
        """Attach when possible, otherwise start a new HomerView Edge."""
        logSection("Launch requested")
        self.sCarriedUrl = ""
        if self.isConnected():
            homerLog.info("Launch: already connected, so the window is raised instead")
            self.refreshProcessIds()
            self.activateBrowser()
            return self.describeConnection()
        try:
            if self.taskAttach():
                self.activateBrowser()
                return self.describeConnection()
        except Exception:
            logError("Launch: attaching to a running Edge failed, starting a new one")
        sOverrideUrl = self.sForeignEdgeUrl
        if sOverrideUrl:
            homerLog.info(
                "An Edge window that HomerView did not open was in use. Its address will be "
                f"opened in the HomerView window instead of the start page: {sOverrideUrl}"
            )
        iPort = self.edgeManager.launch(sOverrideUrl)
        self.cdpSession.connect(iPort)
        self.iPort = iPort
        self.refreshProcessIds()
        homerLog.info(f"Launch: complete on port {self.iPort}")
        self.activateBrowser()
        self.sCarriedUrl = sOverrideUrl
        self.sForeignEdgeUrl = ""
        try:
            lDialogs = self.cdpSession.listDialogTargets()
            if lDialogs:
                homerLog.warning(
                    f"Edge is showing {len(lDialogs)} dialog window(s) that may block the "
                    "address bar; the user is being told"
                )
        except Exception:
            logError("Checking for blocking dialogs failed")
            lDialogs = []
        self.lPendingDialogs = lDialogs
        homerLog.info(
            "Reminder: documents that loaded before this connection existed will not "
            "carry the HomerView browse mode commands. Reload them."
        )
        return self.describeConnection()

    def activateBrowser(self):
        """Raise the HomerView tab, then its window, so it really has focus."""
        try:
            dTarget, sSessionId = self.cdpSession.findActivePageSession()
            self.cdpSession.call("Target.activateTarget", {"targetId": dTarget["targetId"]})
            homerLog.info("Protocol raised the HomerView tab")
        except Exception:
            logError("The HomerView tab could not be raised")
        try:
            self.edgeManager.activateWindow()
        except Exception:
            logError("The HomerView window could not be brought to the front")

    def describeConnection(self):
        return {
            "carried": getattr(self, "sCarriedUrl", ""),
            "dialogs": [dDialog.get("title", "") for dDialog in self.lPendingDialogs],
            "port": self.iPort,
            "processes": len(self.setProcessIds),
        }

    def taskActivePageUrl(self):
        return self.cdpSession.getActivePageUrl()

    def taskRunAxe(self):
        """Test the focused page with axe-core and save the results."""
        pathFolder = logger.pathLogFile.parent if logger.pathLogFile else Path.cwd()
        return axe.runAxe(self.cdpSession, pathFolder)

    def taskAccessibilityReport(self):
        """Scan, find the reporting channels, write the report, and open it.

        This is AccReporter's whole sequence. The scan on its own is a commodity;
        the value is in what a user does next, which is why contact discovery and
        a pre-written email sit in the same command rather than behind another
        one the user has to know about.
        """
        pathData = logger.pathLogFile.parent if logger.pathLogFile else Path.cwd()
        dScan = axe.runAxe(self.cdpSession, pathData)
        dResults = dScan["results"]
        sPageUrl = dScan.get("pageUrl", "")
        sPageTitle = dScan.get("pageTitle", "") or sPageUrl
        try:
            dContacts = contacts.discoverContacts(self.cdpSession, dScan["sessionId"], sPageUrl)
        except Exception:
            logError("Contact discovery failed; the report will omit that section")
            dContacts = contacts.emptyContacts()
        # The reports are working documents rather than records, so they go to
        # the temporary folder that Windows clears on its own. The raw axe
        # result stays beside the log, where it was asked for.
        pathHtml, pathText = report.writeReports(
            dResults, dContacts, sPageTitle, sPageUrl, paths.getTempFolder()
        )
        dSummary = {
            "contacts": {
                "accessibility": len(dContacts.get("accessibility") or []),
                "contact": len(dContacts.get("contact") or []),
                "mailto": len(dContacts.get("mailto") or []),
                "social": len(dContacts.get("social") or []),
                "statement": bool(dContacts.get("statement")),
            },
            "counts": dScan["counts"],
            "reportPath": str(pathHtml),
            "textPath": str(pathText),
        }
        if bOpenReportTab:
            try:
                self.cdpSession.createTarget(pathHtml.as_uri())
                dSummary["opened"] = True
            except Exception:
                logError("Could not open the report in a tab")
                dSummary["opened"] = False
        homerLog.info(f"Accessibility report complete: {dSummary}")
        return dSummary

    def registerGlobalCommand(self, sName, sGesture, sDescription, functionAction):
        """Let the global plugin publish a command to the Alternate Menu."""
        self.lGlobalCommands.append((sName, sGesture, sDescription, functionAction))

    def buildGlobalCommandEntries(self):
        from . import alternateMenu

        return [
            alternateMenu.CommandEntry(sName, sGesture, sDescription, functionAction, "Anywhere")
            for sName, sGesture, sDescription, functionAction in self.lGlobalCommands
        ]

    def taskSelfTest(self):
        from . import selfTest

        return selfTest.collectProtocol(self.cdpSession)

    def makeOpenFileTask(self, sPath, bPlainText=False):
        """Convert a document if needed, then open it in the HomerView window."""
        def task():
            pathTarget, bConverted = convert.convertToHtml(sPath, bPlainText)
            sUri = pathTarget.as_uri()
            self.cdpSession.createTarget(sUri)
            self.activateBrowser()
            history.record(
                "documentOpened",
                pathTarget.stem,
                sUri,
                {"converted": bConverted, "source": str(sPath)},
            )
            return {"converted": bConverted, "name": pathTarget.name, "path": str(pathTarget)}
        return task

    def makeSaveAsTask(self, sSourcePath, sTargetPath, sFormat):
        def task():
            from . import saveAs

            return saveAs.saveDocument(self.cdpSession, sSourcePath, sTargetPath, sFormat)
        return task

    def runOpenDocumentCommand(self):
        """Shared by Control+O in a page and Control+F10 anywhere."""
        self.functionOpenDocument()

    def makeScriptTask(self, sScript):
        def task():
            return act.runScript(self.cdpSession, sScript)
        return task

    def taskOpenCopilot(self):
        """Put the page on the clipboard, raise the window, then send the key."""
        dContext = copilot.prepareContext(self.cdpSession)
        self.activateBrowser()
        import time as timeModule

        timeModule.sleep(copilot.settleSeconds)
        dContext["sent"] = copilot.sendCopilotShortcut()
        dContext["notes"] = copilot.describeReadiness(self.edgeManager)
        return dContext

    def taskSurveyPage(self):
        return act.survey(self.cdpSession)

    def makeActTask(self, sSessionId, dCandidate, sVerb, sValue):
        def task():
            sResult = act.performAction(self.cdpSession, sSessionId, dCandidate, sVerb, sValue)
            history.record("acted", dCandidate.get("name", ""), "",
                           {"role": dCandidate.get("role", ""), "verb": sVerb})
            return {"candidate": dCandidate, "result": sResult, "verb": sVerb}
        return task

    def taskRunAce(self):
        pathData = logger.pathLogFile.parent if logger.pathLogFile else Path.cwd()
        dSummary = ace.runAce(self.cdpSession, pathData)
        history.record("aceScan", dSummary.get("pageTitle", ""), dSummary.get("pageUrl", ""),
                       dSummary.get("counts", {}))
        # Every format the user asked for, in the downloads folder, without
        # anyone having to ask for them separately.
        dSummary["exported"] = exportReport.exportAll(
            "IBM accessibility",
            dSummary.get("pageTitle", ""),
            dSummary.get("report") or dSummary.get("buckets", {}),
            ace.buildRows(dSummary),
            ace.buildReportHtml(dSummary),
            ace.buildSheets(dSummary),
        )
        return dSummary

    def taskSubmitForm(self):
        return formSubmit.submitFocusedForm(self.cdpSession)

    def taskPageInformation(self):
        dSummary = metadata.readMetadata(self.cdpSession)
        history.record("pageInformation", dSummary.get("title", ""), dSummary.get("address", ""),
                       {"fields": len(dSummary.get("fields") or [])})
        return dSummary

    def taskExtractMainContent(self):
        return mainContent.extractMainContent(self.cdpSession)

    def taskAnalyseLinks(self):
        return download.analyseLinks(self.cdpSession)

    def makeDownloadTask(self, dAnalysis, lExtensions, functionAnnounce=None):
        """Return a task that downloads the chosen files."""
        def task():
            return download.downloadLinks(
                self.cdpSession, dAnalysis, lExtensions, functionAnnounce
            )
        return task

    def taskExplorePage(self):
        return pageExplorer.explorePage(self.cdpSession)

    def openReportPage(self, sUri):
        """Open a generated report in a tab and bring it forward.

        Queued to the worker like any other protocol work, so the command that
        produced the report returns at once and NVDA is free to announce the
        new page when it arrives.
        """
        self.submit(
            "openReportPage",
            lambda: (self.cdpSession.createTarget(sUri), self.activateBrowser()),
        )

    def openInTab(self, sUri):
        self.cdpSession.createTarget(sUri)

    def taskListDialogs(self):
        return self.cdpSession.listDialogTargets()

    def taskCloseDialogs(self):
        """Close any Edge dialog that is blocking the browser window."""
        lDialogs = self.cdpSession.listDialogTargets()
        for dDialog in lDialogs:
            self.cdpSession.closeTarget(dDialog["targetId"])
        return lDialogs


service = HomerViewService()

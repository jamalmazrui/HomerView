"""DevTools Protocol session for HomerView.

One WebSocket is opened to the browser-level endpoint. Page targets are attached
with flatten set to true, so every page shares that single connection through a
session identifier. A reader thread dispatches replies to waiting callers by
message identifier and routes everything else to registered event handlers, so
protocol events are never discarded.

Every method here blocks. Call them only from the HomerView worker thread.

Every message sent and received is logged, abbreviated to a fixed length. That
is the main diagnostic instrument for this layer, so when a command misbehaves
the log should show the exact request and reply.
"""

import json
import threading
import time
from urllib.request import urlopen

from .logger import abbreviate, homerLog, logError
from .webSocket import WebSocketClient

defaultCallTimeoutSeconds = 8.0
discoveryTimeoutSeconds = 4.0
maximumLoggedExpressionCharacters = 2000


class CdpError(Exception):
    pass


class PendingCall:
    def __init__(self, sMethod):
        self.dError = None
        self.dResult = None
        self.eventComplete = threading.Event()
        self.nStarted = time.monotonic()
        self.sMethod = sMethod


class CdpSession:
    def __init__(self):
        self.dEventCounts = {}
        self.dEventHandlers = {}
        self.dPageSessions = {}
        self.dPending = {}
        self.iNextId = 0
        self.iPort = 0
        self.lockState = threading.Lock()
        self.threadReader = None
        self.webSocket = None

    # Connection lifetime

    def isConnected(self):
        return bool(self.webSocket) and not self.webSocket.bClosed

    def connect(self, iPort):
        homerLog.info(f"CDP connect: opening the browser endpoint on port {iPort}")
        self.close()
        dVersion = self.fetchJson(iPort, "/json/version")
        homerLog.info(f"CDP browser: {abbreviate(dVersion)}")
        sUrl = dVersion.get("webSocketDebuggerUrl", "")
        if not sUrl:
            raise CdpError("Edge did not publish a browser DevTools endpoint")
        homerLog.debug(f"CDP endpoint: {sUrl}")
        webSocket = WebSocketClient(sUrl)
        webSocket.connect()
        self.iPort = iPort
        self.webSocket = webSocket
        self.threadReader = threading.Thread(
            target=self._readLoop,
            args=(webSocket,),
            name="HomerViewReader",
            daemon=True,
        )
        self.threadReader.start()
        homerLog.debug("CDP reader thread started")
        self.call("Target.setDiscoverTargets", {"discover": True})
        homerLog.info("CDP connect: complete")
        return dVersion

    def close(self):
        webSocket = self.webSocket
        self.webSocket = None
        if self.dPageSessions:
            homerLog.debug(f"CDP close: dropping {len(self.dPageSessions)} page sessions")
        self.dPageSessions = {}
        if webSocket:
            homerLog.info("CDP close: shutting the connection down")
            webSocket.close()
        with self.lockState:
            lPending = list(self.dPending.values())
            self.dPending = {}
        for pending in lPending:
            homerLog.warning(f"CDP close: abandoning pending {pending.sMethod}")
            pending.dError = {"message": "The DevTools connection was closed"}
            pending.eventComplete.set()
        if self.dEventCounts:
            homerLog.info(f"CDP event totals for the connection: {self.dEventCounts}")
            self.dEventCounts = {}

    # Plain HTTP discovery

    def fetchJson(self, iPort, sPath):
        sUrl = f"http://127.0.0.1:{iPort}{sPath}"
        homerLog.debug(f"HTTP get: {sUrl}")
        with urlopen(sUrl, timeout=discoveryTimeoutSeconds) as response:
            sBody = response.read().decode("utf-8")
        homerLog.debug(f"HTTP reply: {abbreviate(sBody)}")
        return json.loads(sBody)

    # Message plumbing

    def call(self, sMethod, dParams=None, sSessionId="", nTimeout=defaultCallTimeoutSeconds):
        webSocket = self.webSocket
        if not webSocket or webSocket.bClosed:
            raise CdpError("HomerView is not connected to Edge")
        pending = PendingCall(sMethod)
        with self.lockState:
            self.iNextId += 1
            iId = self.iNextId
            self.dPending[iId] = pending
        dMessage = {"id": iId, "method": sMethod}
        if dParams:
            dMessage["params"] = dParams
        if sSessionId:
            dMessage["sessionId"] = sSessionId
        sPayload = json.dumps(dMessage, ensure_ascii=False)
        if len(sPayload) > maximumLoggedExpressionCharacters:
            homerLog.debug(f"CDP send {iId}: {sMethod}, {len(sPayload)} character message")
        else:
            homerLog.debug(f"CDP send {iId}: {abbreviate(sPayload)}")
        try:
            webSocket.sendText(sPayload)
        except Exception as exception:
            with self.lockState:
                self.dPending.pop(iId, None)
            logError(f"CDP send {iId} failed for {sMethod}")
            raise CdpError(f"Could not send {sMethod}: {exception}")
        if not pending.eventComplete.wait(nTimeout):
            with self.lockState:
                self.dPending.pop(iId, None)
            homerLog.error(f"CDP timeout {iId}: {sMethod} exceeded {nTimeout} seconds")
            raise CdpError(f"{sMethod} timed out")
        nElapsed = time.monotonic() - pending.nStarted
        if pending.dError:
            sReason = str(pending.dError.get("message", ""))
            # A tab closed while its identifier was in flight is a race, not a
            # fault. Reporting it as an error trains the reader to skip errors.
            if "No target with given id found" in sReason:
                homerLog.info(f"CDP {iId}: the target for {sMethod} closed before the call arrived")
            else:
                homerLog.error(f"CDP error {iId}: {sMethod} returned {abbreviate(pending.dError)}")
            raise CdpError(pending.dError.get("message", "DevTools protocol error"))
        homerLog.debug(f"CDP done {iId}: {sMethod} in {nElapsed:.3f} seconds")
        return pending.dResult or {}

    def addEventHandler(self, sMethod, functionHandler):
        homerLog.debug(f"CDP handler registered for {sMethod}")
        self.dEventHandlers.setdefault(sMethod, []).append(functionHandler)

    def _readLoop(self, webSocket):
        homerLog.debug("CDP reader: loop entered")
        while True:
            try:
                sMessage = webSocket.receiveText()
            except Exception as exception:
                homerLog.info(f"CDP reader: loop ending because {exception}")
                break
            try:
                dMessage = json.loads(sMessage)
            except ValueError:
                homerLog.warning(f"CDP reader: unparsable message {abbreviate(sMessage)}")
                continue
            iId = dMessage.get("id")
            if iId is not None:
                homerLog.debug(f"CDP recv {iId}: {abbreviate(sMessage)}")
                with self.lockState:
                    pending = self.dPending.pop(iId, None)
                if pending:
                    pending.dError = dMessage.get("error")
                    pending.dResult = dMessage.get("result")
                    pending.eventComplete.set()
                else:
                    homerLog.warning(f"CDP recv {iId}: no caller was waiting, probably a timeout")
                continue
            self._dispatchEvent(dMessage, sMessage)
        homerLog.debug("CDP reader: loop exited")
        if self.webSocket is webSocket:
            self.close()

    def _dispatchEvent(self, dMessage, sMessage):
        sMethod = dMessage.get("method", "")
        self.dEventCounts[sMethod] = self.dEventCounts.get(sMethod, 0) + 1
        homerLog.debug(f"CDP event {sMethod}: {abbreviate(sMessage)}")
        lHandlers = self.dEventHandlers.get(sMethod, [])
        for functionHandler in lHandlers:
            try:
                functionHandler(dMessage.get("params") or {}, dMessage.get("sessionId", ""))
            except Exception:
                logError(f"CDP event handler for {sMethod} raised")

    # Targets

    def listPageTargets(self):
        dResult = self.call("Target.getTargets")
        lPages = [
            dTarget
            for dTarget in dResult.get("targetInfos", [])
            if dTarget.get("type") == "page"
        ]
        homerLog.info(f"CDP targets: {len(lPages)} page targets")
        for dTarget in lPages:
            homerLog.debug(
                f"CDP target {dTarget.get('targetId')}: "
                f"attached={dTarget.get('attached')} "
                f"title={abbreviate(dTarget.get('title', ''), 120)} "
                f"url={abbreviate(dTarget.get('url', ''), 200)}"
            )
        return lPages

    def attachToTarget(self, sTargetId):
        sSessionId = self.dPageSessions.get(sTargetId, "")
        if sSessionId:
            homerLog.debug(f"CDP attach: reusing session {sSessionId} for {sTargetId}")
            return sSessionId
        dResult = self.call("Target.attachToTarget", {"targetId": sTargetId, "flatten": True})
        sSessionId = dResult.get("sessionId", "")
        if not sSessionId:
            raise CdpError("Edge did not return a DevTools session")
        homerLog.info(f"CDP attach: session {sSessionId} for target {sTargetId}")
        self.dPageSessions[sTargetId] = sSessionId
        return sSessionId

    def evaluate(self, sSessionId, sExpression, nTimeout=defaultCallTimeoutSeconds):
        if len(sExpression) > maximumLoggedExpressionCharacters:
            homerLog.debug(
                f"CDP evaluate in {sSessionId}: {len(sExpression)} character expression "
                f"beginning {abbreviate(sExpression, 120)}"
            )
        else:
            homerLog.debug(f"CDP evaluate in {sSessionId}: {abbreviate(sExpression)}")
        dResult = self.call(
            "Runtime.evaluate",
            {
                "expression": sExpression,
                "returnByValue": True,
                "awaitPromise": True,
            },
            sSessionId,
            nTimeout,
        )
        dRemote = dResult.get("result", {})
        if dRemote.get("subtype") == "error":
            homerLog.error(f"CDP evaluate failed: {abbreviate(dRemote)}")
            raise CdpError(dRemote.get("description", "JavaScript evaluation failed"))
        vValue = dRemote.get("value")
        homerLog.debug(f"CDP evaluate result: {abbreviate(vValue)}")
        return vValue

    def getBrowserProcessIds(self):
        """Return the identifiers of Edge browser processes only.

        A document's window handle belongs to the browser process, never to a
        renderer, so only browser identifiers are useful for the identity test.
        Caching renderer, GPU, and service identifiers as well would add nothing
        and would risk a false match once Windows recycles one of those numbers.

        SystemInfo.getProcessInfo is marked experimental in the protocol, so the
        caller must tolerate failure and fall back to the launched process id.
        """
        dResult = self.call("SystemInfo.getProcessInfo")
        setBrowserIds = set()
        for dProcess in dResult.get("processInfo", []):
            homerLog.debug(f"CDP process: id={dProcess.get('id')} type={dProcess.get('type')}")
            if dProcess.get("id") and dProcess.get("type") == "browser":
                setBrowserIds.add(int(dProcess["id"]))
        homerLog.info(f"CDP browser process identifiers: {sorted(setBrowserIds)}")
        return setBrowserIds

    def listDialogTargets(self):
        """Return page targets that are Edge's own modal dialogs.

        A fresh profile can open a sync consent dialog that is modal to the
        browser window, which makes the address bar unreachable and leaves the
        browser looking frozen. Naming it is more useful than leaving the user
        to guess.
        """
        lDialogs = []
        for dTarget in self.listPageTargets():
            sUrl = (dTarget.get("url") or "").lower()
            if sUrl.startswith("edge://") and "dialog" in sUrl:
                homerLog.info(f"CDP dialog target: {dTarget.get('url')} titled {dTarget.get('title')}")
                lDialogs.append(dTarget)
        return lDialogs

    def createTarget(self, sUrl):
        """Open a report in a tab of its own, with no history behind it.

        A new target starts with the given address as its only history entry,
        so Alt+LeftArrow has nowhere to go and Control+F4 closes just that tab
        and returns the reader to the page they came from. Navigating the
        current tab instead would put the report into that page's history and
        make closing it ambiguous.
        """
        homerLog.info(f"CDP opening a new tab at {abbreviate(sUrl, 300)}")
        dResult = self.call("Target.createTarget", {"url": sUrl, "newWindow": False})
        sTargetId = dResult.get("targetId", "")
        try:
            dHistory = self.call(
                "Page.getNavigationHistory", {}, self.attachToTarget(sTargetId))
            homerLog.debug(
                f"New tab history has {len(dHistory.get('entries') or [])} entry; "
                "Control+F4 will close only this tab")
        except Exception:
            pass
        return sTargetId

    def closeTarget(self, sTargetId):
        homerLog.info(f"CDP closing target {sTargetId}")
        self.dPageSessions.pop(sTargetId, None)
        return self.call("Target.closeTarget", {"targetId": sTargetId})

    def findActivePageSession(self):
        """Return the target and session for the page the user is looking at.

        document.hasFocus is true only for the active tab of the focused window,
        which is far more reliable than matching window titles.
        """
        lTargets = self.listPageTargets()
        if not lTargets:
            raise CdpError("HomerView Edge has no open page")
        dFallback = None
        for dTarget in lTargets:
            sUrl = dTarget.get("url", "")
            if sUrl and sUrl != "about:blank" and not dFallback:
                dFallback = dTarget
            try:
                sSessionId = self.attachToTarget(dTarget["targetId"])
                bFocused = self.evaluate(sSessionId, "document.hasFocus()")
                homerLog.debug(f"CDP focus test for {dTarget.get('targetId')}: {bFocused}")
                if bFocused:
                    homerLog.info(f"CDP active page: {abbreviate(dTarget.get('url', ''), 300)}")
                    return dTarget, sSessionId
            except CdpError as exception:
                homerLog.warning(f"CDP focus test skipped for {dTarget.get('targetId')}: {exception}")
                continue
        dFallback = dFallback or lTargets[0]
        homerLog.info(f"CDP active page: none focused, using {abbreviate(dFallback.get('url', ''), 300)}")
        return dFallback, self.attachToTarget(dFallback["targetId"])

    def getActivePageUrl(self):
        dTarget, sSessionId = self.findActivePageSession()
        try:
            return self.evaluate(sSessionId, "location.href") or dTarget.get("url", "")
        except CdpError:
            return dTarget.get("url", "")

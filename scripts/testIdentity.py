r"""testIdentity.py -- the browser-identity proof for HomerView (suite stage 1).

Runs every rule in addon\globalPlugins\homerView\identity.py against fixed
cases, with no NVDA and no browser needed. The build runs it; it can also be
run alone through testIdentity.cmd. Exit 0 when every case passes.

The console says how many cases passed; the log, logs\HomerView-testIdentity-
<stamp>.log, records the environment and every case with its result.
"""

import datetime
import importlib.util
import os
import platform
import sys
import traceback

sScriptDir = os.path.dirname(os.path.abspath(__file__))
sRoot = os.path.dirname(sScriptDir)
sModule = os.path.join(sRoot, "addon", "globalPlugins", "homerView", "identity.py")
sLogPath = os.path.join(sRoot, "logs", "HomerView-testIdentity-%s.log" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))


class FakeObject:
    def __init__(self, iProcessId):
        self.processID = iProcessId


def loadIdentity():
    oSpec = importlib.util.spec_from_file_location("identity", sModule)
    oModule = importlib.util.module_from_spec(oSpec)
    oSpec.loader.exec_module(oModule)
    return oModule


def cases(identity):
    setChrome = frozenset([4100, 4104])          # HomerView's Chrome: browser and renderer
    sChromePath = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    sChromiumPath = r"C:\Chromium\Application\chrome.exe"
    sEdgePath = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    S = identity.TargetStamp
    oStamp = S("session1", 66, "tabA", 3)
    return [
        ("a page in HomerView's Chrome is HomerView's", identity.isManagedObject(FakeObject(4104), setChrome), True),
        ("an ordinary Chrome window is not, though it is chrome.exe", identity.isManagedObject(FakeObject(5200), setChrome), False),
        ("an ordinary Edge window is not", identity.isManagedObject(FakeObject(7300), setChrome), False),
        ("with no process known, nothing is HomerView's", identity.isManagedObject(FakeObject(4104), frozenset()), False),
        ("an object with no process id is not", identity.isManagedObject(object(), setChrome), False),
        ("a key in HomerView's browser is HomerView's", identity.keyBelongsToHomerView(4100, setChrome), True),
        ("a key in an unmanaged window of the same browser is the browser's", identity.keyBelongsToHomerView(5200, setChrome), False),
        ("before launch every key is the browser's", identity.keyBelongsToHomerView(4100, frozenset()), False),
        ("Chrome and Chromium share a program name", identity.appNameFromPath(sChromePath) == identity.appNameFromPath(sChromiumPath), True),
        ("an eligible browser is worth probing", identity.isEligibleApp("chrome", [sChromePath, sEdgePath]), True),
        ("an ineligible browser is not", identity.isEligibleApp("brave", [sChromePath, sEdgePath]), False),
        ("eligibility does not make a window HomerView's", identity.isManagedObject(FakeObject(5200), setChrome), False),
        ("a request for the same page may act", oStamp.staleReason(S("session1", 66, "tabA", 3)), ""),
        ("a request after the tab changed is cancelled", oStamp.staleReason(S("session1", 66, "tabB", 1)), "a different tab is in front now"),
        ("a request after navigation is cancelled", oStamp.staleReason(S("session1", 66, "tabA", 4)), "the page has changed since you asked"),
        ("a request after reconnecting is cancelled", oStamp.staleReason(S("session2", 66, "tabA", 3)), "the browser connection changed"),
        ("a request with no connection is cancelled", oStamp.staleReason(None), "the browser is no longer connected"),
        ("a request after the window changed is cancelled", oStamp.staleReason(S("session1", 70, "tabA", 3)), "a different window is in front now"),
    ]


def main():
    os.makedirs(os.path.dirname(sLogPath), exist_ok=True)
    with open(sLogPath, "w", encoding="utf-8-sig", newline="\r\n") as oLog:
        def log(sText):
            oLog.write(datetime.datetime.now().astimezone().isoformat(timespec="milliseconds") + " INFO  " + sText + "\n")
        log("testIdentity start; script " + os.path.abspath(__file__))
        log("python " + platform.python_version() + " on " + platform.platform() + "; cwd " + os.getcwd())
        log("module " + sModule)
        try:
            identity = loadIdentity()
            lsCases = cases(identity)
        except Exception:
            log("TRACEBACK:\n" + traceback.format_exc())
            print("testIdentity could not load identity.py. The details are in " + sLogPath)
            return 1
        iFailed = 0
        for sName, oGot, oWanted in lsCases:
            bPass = oGot == oWanted
            if not bPass:
                iFailed += 1
            log("%s: %s (got %r, wanted %r)" % ("PASS" if bPass else "FAIL", sName, oGot, oWanted))
        iPassed = len(lsCases) - iFailed
        sSummary = "testIdentity: %d of %d cases passed." % (iPassed, len(lsCases))
        log(sSummary)
        print(sSummary)
        if iFailed:
            print("The failures are in " + sLogPath)
        return 1 if iFailed else 0


if __name__ == "__main__":
    sys.exit(main())

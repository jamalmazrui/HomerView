r"""cleanDir.py -- move everything the project does not name into notes\.

Run it from the project folder with no arguments to see what it would do:

    cleanDir

Run it again with --do-it to actually do it:

    cleanDir --do-it

WHY THIS REPLACED cleanDir.ps1, AND WHAT THAT ONE DID

On 31 August 2026 cleanDir.ps1 moved 42 files out of C:\HomerView, among
them the whole jaws folder, every build and check script, Announce.md,
Hotkeys.inix, summarizeSetup.cmd, and RepoFiles.txt itself. The build then
stopped with seven "the setup script references X, which does not exist"
errors. Nothing was lost, because it moved rather than deleted, but the
folder had to be put back by hand.

The cause was not a wrong name in a list. It was that there was a list at
all. That script's own header said what it kept was decided by the setup
script, the build and the repository -- and its code held twenty-six names
written inside itself. The comment described homerPolicy; the code predated
it. So it disagreed with the setup script (jaws\*, Start.htm, Announce.htm),
with RepoFiles.txt's tracked list (every build and check script), and with
its local list (Axe.js, Ace.js, Nlp.js, version.txt) -- and, the other way
round, kept three files no list named at all.

THREE THINGS THIS ONE DOES DIFFERENTLY

  1. IT DECIDES BY homerPolicy AND HAS NO LIST OF ITS OWN. There is nothing
     in this file to keep in step with the setup script, because it reads
     the setup script. If a file should stay, name it in HomerView_setup.iss
     or in RepoFiles.txt; there is no third place, and nothing here to edit.

  2. IT SURVEYS BEFORE IT ACTS. Running it does nothing at all. It prints
     the whole plan, every file and the reason, and stops. --do-it is a
     second, deliberate run. That is what made tidyRepo safe in the same
     session in which cleanDir emptied the folder, and it is the single
     thing most worth copying.

  3. IT STOPS IF THE PLAN IS TOO BIG. A sweep that wants to move a quarter
     of the folder has almost certainly misread something rather than found
     a quarter of the folder to be rubbish. It says so and refuses, and
     --anyway is there for the day it is genuinely right. Had this existed,
     the 42-file sweep would have printed its plan and stopped.

WHERE THINGS GO

notes\, inside the project, which .gitignore excludes in one line. Not
C:\temp: a folder taken out of the project and put somewhere else on the
disk is one nobody finds again, and the point of moving rather than
deleting is that it can be undone in the same window.

Zero-byte files are the one thing deleted rather than moved. An empty file
is worse than a missing one, because a missing file is noticed and an empty
one is opened, believed and acted on.

A detailed log is written beside this script, whatever happens.
"""

import datetime, os, shutil, sys

# Set before homerPolicy is imported, or importing it writes a __pycache__
# folder that this script then reports and removes, every single run.
sys.dont_write_bytecode = True

import homerPolicy  # noqa: E402

c_iMaxStrayPercent = 25              # a plan bigger than this is suspect
c_iMaxStrayCount = 20                # and so is one longer than this
c_sLogName = "cleanDir.log"
c_sNotesFolder = "notes"
c_lNeverTouch = [".git", ".github", c_sNotesFolder]

pathRoot = os.path.dirname(os.path.abspath(__file__))
pathLog = os.path.join(pathRoot, c_sLogName)
lReport = []


def writeLog(sMessage=""):
    """Say it on the console and in the log, so neither is the fuller one."""
    print(sMessage)
    lReport.append(sMessage)


def saveLog():
    """Write the log out, in the Homer standard encoding."""
    try:
        with open(pathLog, "w", encoding="utf-8-sig", newline="\r\n") as fileLog:
            fileLog.write("\n".join(lReport) + "\n")
    except OSError as oError:
        print("The log could not be written: %s" % oError)


def stamp():
    """The time, for the log."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def logEnvironment(bDoIt, bAnyway):
    """Everything a failure would otherwise have to be guessed from."""
    writeLog("cleanDir  %s" % stamp())
    writeLog("  script:            %s" % os.path.abspath(__file__))
    writeLog("  Python:            %s" % sys.version.split()[0])
    writeLog("  platform:          %s" % sys.platform)
    writeLog("  working directory: %s" % os.getcwd())
    writeLog("  project folder:    %s" % pathRoot)
    writeLog("  command line:      %s" % " ".join(sys.argv))
    writeLog("  do it:             %s" % ("yes" if bDoIt else "no, this is a survey"))
    writeLog("  override the size guard: %s" % ("yes" if bAnyway else "no"))
    writeLog("  notes folder:      %s" % os.path.join(pathRoot, c_sNotesFolder))
    writeLog("")


def loadPolicy():
    """The three lists, or None when they cannot be read.

    Refusing here is the important part. A sweep whose policy came back
    empty would find that nothing at all is named and would carry off the
    entire project, which is a far worse failure than doing nothing.
    """
    sIssName = homerPolicy.setupScriptName(pathRoot)
    if not sIssName:
        writeLog("STOPPING: no <App>_setup.iss in this folder, so nothing can be")
        writeLog("          judged. Run this from the project folder.")
        return None
    oInstalled = homerPolicy.installedFiles(pathRoot)
    if oInstalled is None:
        writeLog("STOPPING: %s could not be read." % sIssName)
        return None
    setTracked, setLocal = homerPolicy.repoFiles(pathRoot)
    if not setTracked:
        writeLog("STOPPING: %s names nothing as tracked. Either it is missing or"
                 % homerPolicy.c_sRepoFilesName)
        writeLog("          it is empty, and sweeping on an empty list would move")
        writeLog("          the whole project.")
        return None
    setExact, lFolders, lPatterns = oInstalled
    writeLog("What decides this, read fresh from the folder:")
    writeLog("  %s names %d files, %d whole folders, %d patterns."
             % (sIssName, len(setExact), len(lFolders), len(lPatterns)))
    writeLog("  %s names %d tracked and %d local."
             % (homerPolicy.c_sRepoFilesName, len(setTracked), len(setLocal)))
    writeLog("  There is no list inside this script.")
    writeLog("")
    return oInstalled, setTracked, setLocal


def filesUnder(pathFolder):
    """Every file under a folder, as paths relative to the project."""
    lPaths = []
    for pathHere, lFolderNames, lFileNames in os.walk(pathFolder):
        lFolderNames[:] = [s for s in lFolderNames if s not in c_lNeverTouch]
        for sName in lFileNames:
            sFull = os.path.join(pathHere, sName)
            lPaths.append(os.path.relpath(sFull, pathRoot).replace("\\", "/"))
    return lPaths


def folderBelongs(sName, oPolicy):
    """Whether a folder at the top of the project stays.

    Named by the lists, or holding one file that is. The second test matters:
    installer\\ is named by nothing, and addon\\ is named only through the
    single file addon\\manifest.ini plus the setup script's addon\\* line.
    """
    oInstalled, setTracked, setLocal = oPolicy
    if homerPolicy.folderIsNamed(sName, oInstalled, setTracked, setLocal):
        return True
    for sPath in filesUnder(os.path.join(pathRoot, sName)):
        if homerPolicy.belongsInFolder(sPath, oInstalled, setTracked, setLocal):
            return True
    return False


def surveyTop(oPolicy):
    """What at the top of the project stays and what goes.

    Returns the strays as pairs of name and reason, and the number kept.
    """
    oInstalled, setTracked, setLocal = oPolicy
    lStray = []
    iKept = 0
    for sName in sorted(os.listdir(pathRoot), key=str.lower):
        if sName in c_lNeverTouch or sName == c_sLogName:
            iKept += 1
            continue
        # Counted once, as a leftover, rather than twice as a stray as well.
        if sName == "__pycache__":
            continue
        pathItem = os.path.join(pathRoot, sName)
        if os.path.isdir(pathItem):
            if folderBelongs(sName, oPolicy):
                iKept += 1
            else:
                iCount = len(filesUnder(pathItem))
                lStray.append((sName, "a folder no list names, holding %d file%s"
                               % (iCount, "" if iCount == 1 else "s")))
            continue
        if homerPolicy.belongsInFolder(sName, oInstalled, setTracked, setLocal):
            iKept += 1
        else:
            lStray.append((sName, "named by neither the setup script nor RepoFiles.txt"))
    return lStray, iKept


def surveyEmptyFiles():
    """Every zero-byte file in the project, which is one too many."""
    lEmpty = []
    for pathHere, lFolderNames, lFileNames in os.walk(pathRoot):
        lFolderNames[:] = [s for s in lFolderNames if s not in c_lNeverTouch]
        for sName in lFileNames:
            if "__pycache__" in pathHere:
                continue
            pathFile = os.path.join(pathHere, sName)
            try:
                if os.path.getsize(pathFile) == 0:
                    lEmpty.append(os.path.relpath(pathFile, pathRoot).replace("\\", "/"))
            except OSError:
                continue
    return sorted(lEmpty)


def surveyCaches():
    """Compiled Python, which serves no purpose in a source folder."""
    lCaches = []
    for pathHere, lFolderNames, lFileNames in os.walk(pathRoot):
        lFolderNames[:] = [s for s in lFolderNames if s not in c_lNeverTouch]
        for sName in list(lFolderNames):
            if sName == "__pycache__":
                lCaches.append(os.path.relpath(os.path.join(pathHere, sName),
                                               pathRoot).replace("\\", "/"))
    return sorted(lCaches)


def surveyVersionedAddons():
    """Older versioned copies of the add-on beside the one the installer takes.

    Two identical files under different names invites the wrong one being
    picked up, and only the plain name is ever installed.
    """
    sApp = homerPolicy.appName(pathRoot)
    pathBuild = os.path.join(pathRoot, "build")
    lCopies = []
    if not sApp or not os.path.isdir(pathBuild):
        return lCopies
    for sName in sorted(os.listdir(pathBuild)):
        if sName.lower().endswith(".nvda-addon") and sName.lower() != (sApp + ".nvda-addon").lower():
            lCopies.append("build/" + sName)
    return lCopies


def moveToNotes(sRelative):
    """Move one item into notes\\, keeping anything already there."""
    pathNotes = os.path.join(pathRoot, c_sNotesFolder)
    if not os.path.isdir(pathNotes):
        os.makedirs(pathNotes)
        writeLog("  created %s" % pathNotes)
    sName = os.path.basename(sRelative.rstrip("/"))
    pathTarget = os.path.join(pathNotes, sName)
    if os.path.exists(pathTarget):
        sBase, sExtension = os.path.splitext(sName)
        sWhen = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        pathTarget = os.path.join(pathNotes, sBase + "-" + sWhen + sExtension)
        writeLog("  one of those is already in notes, so this one becomes %s"
                 % os.path.basename(pathTarget))
    shutil.move(os.path.join(pathRoot, sRelative.replace("/", os.sep)), pathTarget)


def describePlan(lStray, iKept, lEmpty, lCaches, lAddons):
    """The whole plan, before anything has happened."""
    writeLog("=" * 68)
    writeLog("SURVEY. Everything is looked at before anything is changed.")
    writeLog("=" * 68)
    writeLog("")
    writeLog("1. AT THE TOP OF THE PROJECT: %d items stay, %d do not."
             % (iKept, len(lStray)))
    writeLog("")
    if lStray:
        writeLog("   These are named by no list, so they move to %s\\ where they" % c_sNotesFolder)
        writeLog("   stay on disk and out of the repository. Nothing is deleted.")
        writeLog("")
        for sName, sWhy in lStray:
            writeLog("     %s  (%s)" % (sName, sWhy))
        writeLog("")
        writeLog("   To keep any of them, name it in the setup script or in")
        writeLog("   %s. That is the only way, and it is one line."
                 % homerPolicy.c_sRepoFilesName)
    else:
        writeLog("   Nothing at the top of the project is unaccounted for.")
    writeLog("")

    writeLog("2. EMPTY FILES: %d." % len(lEmpty))
    writeLog("")
    if lEmpty:
        writeLog("   These are deleted rather than moved. An empty file is worse")
        writeLog("   than a missing one, because a missing one is noticed.")
        writeLog("")
        for sPath in lEmpty:
            writeLog("     %s" % sPath)
    else:
        writeLog("   No empty files anywhere.")
    writeLog("")

    writeLog("3. LEFTOVERS: %d Python cache folder%s, %d versioned add-on cop%s."
             % (len(lCaches), "" if len(lCaches) == 1 else "s",
                len(lAddons), "y" if len(lAddons) == 1 else "ies"))
    writeLog("")
    if lCaches or lAddons:
        for sPath in lCaches:
            writeLog("     %s  (removed; Python makes it again)" % sPath)
        for sPath in lAddons:
            writeLog("     %s  (moved; the installer takes the plain name)" % sPath)
    else:
        writeLog("   Nothing left over.")
    writeLog("")


def tooBig(lStray):
    """Whether the plan is large enough to be a misreading rather than a find."""
    lTop = [s for s in os.listdir(pathRoot) if s not in c_lNeverTouch]
    iTotal = max(1, len(lTop))
    iPercent = (100 * len(lStray)) // iTotal
    return (len(lStray) > c_iMaxStrayCount or iPercent >= c_iMaxStrayPercent), iPercent


def carryOut(lStray, lEmpty, lCaches, lAddons):
    """Do the plan, in one pass, saying what happens to each item."""
    writeLog("=" * 68)
    writeLog("DOING IT")
    writeLog("=" * 68)
    writeLog("")
    iMoved, iDeleted, iFailed = 0, 0, 0

    for sPath in lEmpty:
        writeLog("Deleting %s (empty)" % sPath)
        try:
            os.remove(os.path.join(pathRoot, sPath.replace("/", os.sep)))
            iDeleted += 1
        except OSError as oError:
            writeLog("  ERROR: %s" % oError)
            iFailed += 1

    for sName, sWhy in lStray:
        writeLog("Moving %s to %s\\" % (sName, c_sNotesFolder))
        try:
            moveToNotes(sName)
            iMoved += 1
        except OSError as oError:
            writeLog("  ERROR: %s" % oError)
            iFailed += 1

    for sPath in lCaches:
        writeLog("Removing %s" % sPath)
        try:
            shutil.rmtree(os.path.join(pathRoot, sPath.replace("/", os.sep)))
            iDeleted += 1
        except OSError as oError:
            writeLog("  ERROR: %s" % oError)
            iFailed += 1

    for sPath in lAddons:
        writeLog("Moving %s to %s\\" % (sPath, c_sNotesFolder))
        try:
            moveToNotes(sPath)
            iMoved += 1
        except OSError as oError:
            writeLog("  ERROR: %s" % oError)
            iFailed += 1

    writeLog("")
    writeLog("%d item%s moved, %d deleted, %d failed."
             % (iMoved, "" if iMoved == 1 else "s", iDeleted, iFailed))
    if iMoved:
        writeLog("Everything moved is in %s and can be moved back."
                 % os.path.join(pathRoot, c_sNotesFolder))
    return 1 if iFailed else 0


def main():
    """Survey, then act only when asked twice."""
    bDoIt = "--do-it" in sys.argv
    bAnyway = "--anyway" in sys.argv
    logEnvironment(bDoIt, bAnyway)

    oPolicy = loadPolicy()
    if oPolicy is None:
        return 1

    lStray, iKept = surveyTop(oPolicy)
    lEmpty = surveyEmptyFiles()
    # An empty file that is also unnamed would otherwise be moved and then
    # deleted from where it no longer is. Deleting wins, because an empty file
    # is worth nothing in notes\\ either, and each item is then named once.
    setEmpty = set(lEmpty)
    lStray = [t for t in lStray if t[0] not in setEmpty]
    lCaches = surveyCaches()
    lAddons = surveyVersionedAddons()
    describePlan(lStray, iKept, lEmpty, lCaches, lAddons)

    if not (lStray or lEmpty or lCaches or lAddons):
        writeLog("Nothing to do. The folder holds only what the project names.")
        return 0

    bTooBig, iPercent = tooBig(lStray)
    if bTooBig and not bAnyway:
        writeLog("STOPPING: this plan would move %d items, which is %d%% of the"
                 % (len(lStray), iPercent))
        writeLog("          top of the project. A sweep that wants to move that")
        writeLog("          much has almost certainly misread something rather")
        writeLog("          than found that much rubbish, which is exactly what")
        writeLog("          happened on 31 August 2026.")
        writeLog("")
        writeLog("          Check the list above. If it is genuinely right, run:")
        writeLog("")
        writeLog("              cleanDir --do-it --anyway")
        return 1

    if not bDoIt:
        writeLog("This was a description only. Nothing has been changed.")
        writeLog("")
        writeLog("Run it again with --do-it to carry the plan out:")
        writeLog("")
        writeLog("    cleanDir --do-it")
        return 0

    return carryOut(lStray, lEmpty, lCaches, lAddons)


if __name__ == "__main__":
    iExit = 1
    try:
        iExit = main()
    except Exception as oError:                                  # noqa: BLE001
        import traceback
        writeLog("")
        writeLog("UNEXPECTED ERROR: %s" % oError)
        for sLine in traceback.format_exc().splitlines():
            writeLog("  " + sLine)
    writeLog("")
    writeLog("Exit code %d. The log is at %s" % (iExit, pathLog))
    saveLog()
    sys.exit(iExit)

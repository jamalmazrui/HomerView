r"""
kind.py -- say what kind of Homer resource a folder is: an app, a collection,
a kit or a page. Every kit script asks this first and acts, or declines to
act, accordingly. Part of the HomerDev kit.

    kind                      the project in this folder
    kind D:\Work\BlindVibeCoding   another folder, on any drive and at any depth
    kind --kit                 where the kit is, as every kit script finds it

A script imports it (from its own folder, then the kit's scripts folder):

    from kind import projectKind, projectRoot
    sKind, sWhy = projectKind(sRoot)

THE FOUR KINDS, AND THE ONE FACT THAT SETTLES EACH (checked in this order)

  kit         the Homer Development Kit itself: Templates\HomerComponents.iss
              and exec\CSharp\Lbc.cs. It builds, checks and releases itself
              with its own build.py, checkHomerDev and releaseHomerDev.
  app         a program: an installer script <App>_setup.iss, or a source
              named for the folder (<App>.cs or <App>.py) at the top. It has
              a build, an installer, releases tagged by version.txt, and the
              documentation set in help.
  page        one document published as a web page: <Folder>.md at the top,
              with no program. It may not be a git repository at all; post
              makes and keeps its repository.
  collection  many documents of one kind at the top -- help guides, podcast
              directories -- with no program and no single document named
              for the folder. Its repository is the content.

Anything else is "unknown", and a script that needs to know says so and does
nothing, rather than guessing.

WHERE THINGS ARE: ONLY WINDOWS AND A FOLDER'S NAME ARE ASSUMED (1.46.0). A
project and the kit may each be on any drive, at any depth. The kit is the
folder named HomerDev that findKit finds first: the HomerDev environment
variable; then, from the folder given and from this script's folder upward,
any folder that is the kit or that holds a HomerDev folder; then a HomerDev
folder at the top of any ready fixed drive. "kind --kit" prints it.
"""
import glob, os, sys

c_lsStandardDocs = ["announce", "developer", "faq", "history", "hotkeys", "index", "license",
                    "readme", "self", "tutorials"]
c_lsKinds = ["app", "collection", "kit", "page", "unknown"]


# THE LICENSE FOR EACH KIND (1.48.0). Code is MIT, the license the Homer apps
# and the kit have always carried, in a License.md beside the source. Writing
# -- a page, or a collection's own text and arrangement -- is Creative Commons
# Attribution-ShareAlike 4.0, the license Wikipedia's text has used since June
# 2023. Material gathered from others (a publisher's help text, a show's
# episode summaries, a skill's full text) stays under its owners' terms, and a
# document that holds such material says so in one sentence.
c_dLicenses = {
    "app": ("MIT License", "MIT", "License.htm"),
    "kit": ("MIT License", "MIT", "License.htm"),
    "page": ("Creative Commons Attribution-ShareAlike 4.0 International", "CC BY-SA 4.0",
             "https://creativecommons.org/licenses/by-sa/4.0/"),
    "collection": ("Creative Commons Attribution-ShareAlike 4.0 International", "CC BY-SA 4.0",
                   "https://creativecommons.org/licenses/by-sa/4.0/"),
}


def licenseFor(sKind):
    """(full name, short name, link) of the license a resource of this kind
    carries, or None for an unknown kind."""
    return c_dLicenses.get(sKind)


def projectRoot(sStart):
    """The project is the folder given, or its parent when that is the
    project's scripts or exec folder. One rule for every kit tool."""
    sStart = os.path.abspath(sStart)
    if os.path.basename(sStart.rstrip("\\/")).lower() in ("scripts", "exec", "tools"):
        return os.path.dirname(sStart.rstrip("\\/"))
    return sStart


def documentStems(sFolder):
    """The distinct document names at the top of a folder, less the standard
    ones every project may carry."""
    dStems = {}
    for sName in sorted(os.listdir(sFolder)):
        sStem, sExt = os.path.splitext(sName)
        if sExt.lower() in (".md", ".htm") and sStem.lower() not in c_lsStandardDocs:
            dStems.setdefault(sStem.lower(), sStem)
    return [dStems[s] for s in sorted(dStems)]


def projectKind(sFolder):
    """Returns (kind, reason): the kind of Homer resource in sFolder, and the
    evidence that decided it, in words for a log."""
    sFolder = os.path.abspath(sFolder).rstrip("\\/")
    if not os.path.isdir(sFolder): return "unknown", "no such folder"
    sName = os.path.basename(sFolder)
    # AN APP IS AN APP EVEN WITH THE KIT'S FILES ON TOP OF IT. A HomerDev.zip
    # unarchived into C:\\DbDo put the kit's Templates and exec\\CSharp beside
    # DbDo.cs, and this test called the folder the kit, which turned off the
    # very tidying that would have removed them (6 October 2026). An installer
    # script or a program source named for the folder settles it as an app
    # first; only then do the kit's marks make a kit.
    lsIssFirst = glob.glob(os.path.join(sFolder, "*_setup.iss"))
    bNamedProgram = any(os.path.isfile(os.path.join(sFolder, sName + sExt)) for sExt in (".cs", ".py", ".js", ".ps1"))
    if (not lsIssFirst and not bNamedProgram
            and os.path.isfile(os.path.join(sFolder, "Templates", "HomerComponents.iss"))
            and os.path.isfile(os.path.join(sFolder, "exec", "CSharp", "Lbc.cs"))):
        return "kit", "Templates\\HomerComponents.iss and exec\\CSharp\\Lbc.cs are here, and no app's installer or program"
    lsIss = glob.glob(os.path.join(sFolder, "*_setup.iss"))
    if lsIss: return "app", "%s is its installer script" % os.path.basename(lsIss[0])
    for sExt in (".cs", ".py"):
        if os.path.isfile(os.path.join(sFolder, sName + sExt)):
            return "app", "%s%s is its program source" % (sName, sExt)
    for sExt in (".md", ".htm"):
        if os.path.isfile(os.path.join(sFolder, sName + sExt)):
            return "page", "%s%s is its one document, and there is no program" % (sName, sExt)
    lsStems = documentStems(sFolder)
    if len(lsStems) >= 2:
        return "collection", "%d documents at the top, and no program" % len(lsStems)
    if len(lsStems) == 1:
        return "page", "%s is its one document, and there is no program" % lsStems[0]
    return "unknown", "no installer script, program source or document at the top"


def publishesBooks(sFolder):
    """Whether the project publishes books, with the HomerDev kit's book tools: its configs folder holds books.inix, the
    catalog of its books. This is a capability, not a kind: a page (a GitHub Pages directory of the books, say), a
    collection or a project of one book may each publish books, and keeps its own kind for every other kit script. The
    conventions it brings -- books\\<root>\\ for each book's sources, results\\ for the built EPUBs and their audits,
    data\\books\\ for what KDP holds -- are in the kit's help\\BookPattern.md (1.63.0)."""
    return os.path.isfile(os.path.join(os.path.abspath(sFolder), "configs", "books.inix"))


def isKit(sFolder):
    """Does this folder hold the kit's shared classes?"""
    return bool(sFolder) and (os.path.isfile(os.path.join(sFolder, "exec", "CSharp", "Lbc.cs"))
                              or os.path.isfile(os.path.join(sFolder, "exec", "Python", "lbc.py")))


def fixedDrives():
    """The roots of the ready fixed drives, such as C:\\ and D:\\. Network,
    removable and empty drives are left out, so the search never waits on one."""
    lsRoots = []
    if os.name != "nt": return lsRoots
    try:
        import ctypes, string
        iMask = ctypes.windll.kernel32.GetLogicalDrives()
        for iIndex, sLetter in enumerate(string.ascii_uppercase):
            if not iMask & (1 << iIndex): continue
            sRoot = sLetter + ":\\"
            if ctypes.windll.kernel32.GetDriveTypeW(sRoot) == 3: lsRoots.append(sRoot)
    except Exception:
        pass
    return lsRoots


def findKit(lsStarts=None):
    """The kit's folder, or "" when there is none. Only Windows and the folder
    name HomerDev are assumed, never a drive or a depth."""
    sEnv = os.environ.get("HomerDev", "")
    if isKit(sEnv): return os.path.abspath(sEnv)
    lsStarts = list(lsStarts or []) + [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for sStart in lsStarts:
        sDir = os.path.abspath(sStart)
        while True:
            if isKit(sDir): return sDir
            if isKit(os.path.join(sDir, "HomerDev")): return os.path.join(sDir, "HomerDev")
            sUp = os.path.dirname(sDir)
            if sUp == sDir: break
            sDir = sUp
    for sRoot in fixedDrives():
        if isKit(os.path.join(sRoot, "HomerDev")): return os.path.join(sRoot, "HomerDev")
    return ""


def main():
    sStart = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else os.getcwd()
    if "--kit" in sys.argv:
        sKit = findKit([sStart])
        print(sKit if sKit else "No HomerDev folder was found.")
        return 0 if sKit else 1
    sRoot = projectRoot(sStart)
    sKind, sWhy = projectKind(sRoot)
    if "--word" in sys.argv:
        print(sKind)
    else:
        if sKind == "unknown": print("%s is not a kind of Homer resource kind.py knows: %s." % (sRoot, sWhy))
        else: print("%s is %s %s: %s." % (sRoot, "an" if sKind[0] in "aeiou" else "a", sKind, sWhy))
        if publishesBooks(sRoot): print("It also publishes books: configs\\books.inix is its catalog.")
    return 0 if sKind != "unknown" else 1


if __name__ == "__main__":
    sys.exit(main())

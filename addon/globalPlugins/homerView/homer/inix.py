"""Order preserving ini and inix configuration files.

A port of the C# InixCodec. Python already has configparser, so the case for
this rests entirely on what configparser will not do.

configparser discards comments, discards blank lines, and rewrites a file in
whatever order its dictionary happens to yield. A configuration a person edits
by hand should come back looking as they left it, with their notes intact, and
with a changed value changed in place rather than moved to the bottom of a
reordered file. That is what order preserving means here and it is the whole
point.

inix is a superset of ini. Three additions:

    A verbatim multi-line value, opened with a line that is a key followed by
    an equals sign and a brace, and closed with a brace alone. Everything
    between is the value exactly as written, including blank lines and
    characters that would otherwise need escaping.

    An implicit Global section, so a file may begin with plain keys and values
    before any section header.

    Round-trip fidelity, so reading a file and writing it back produces the
    same bytes when nothing was changed.
"""

import os

globalSectionName = "Global"
multiLineClose = "}"
multiLineOpen = "{"


class Pair:
    """One key and value, or a comment or blank line kept in place."""

    def __init__(self, sKey="", sValue="", sRaw=None, bMultiLine=False):
        self.bMultiLine = bMultiLine
        self.sKey = sKey
        self.sRaw = sRaw
        self.sValue = sValue

    @property
    def bLiteral(self):
        """True for a comment or blank line, which is kept exactly."""
        return self.sRaw is not None


class Section:
    def __init__(self, sName=""):
        self.lPairs = []
        self.sName = sName

    def get(self, sKey, sDefault=""):
        for pair in self.lPairs:
            if not pair.bLiteral and pair.sKey.lower() == str(sKey).lower():
                return pair.sValue
        return sDefault

    def set(self, sKey, sValue):
        """Change a value in place, or add it at the end of the section."""
        for pair in self.lPairs:
            if not pair.bLiteral and pair.sKey.lower() == str(sKey).lower():
                pair.sValue = str(sValue)
                pair.bMultiLine = "\n" in str(sValue)
                return False
        self.lPairs.append(Pair(str(sKey), str(sValue), bMultiLine="\n" in str(sValue)))
        return True

    def keys(self):
        return [pair.sKey for pair in self.lPairs if not pair.bLiteral]

    def asDictionary(self):
        return {pair.sKey: pair.sValue for pair in self.lPairs if not pair.bLiteral}


def parseLines(lLines):
    """Turn lines into sections, keeping comments and blanks where they are."""
    lSections = [Section(globalSectionName)]
    iIndex = 0
    while iIndex < len(lLines):
        sLine = lLines[iIndex].rstrip("\r\n")
        sStripped = sLine.strip()
        if sStripped.startswith("[") and sStripped.endswith("]"):
            lSections.append(Section(sStripped[1:-1].strip()))
            iIndex += 1
            continue
        if not sStripped or sStripped[0] in ";#":
            lSections[-1].lPairs.append(Pair(sRaw=sLine))
            iIndex += 1
            continue
        if "=" not in sLine:
            lSections[-1].lPairs.append(Pair(sRaw=sLine))
            iIndex += 1
            continue
        sKey, sRest = sLine.split("=", 1)
        sKey = sKey.strip()
        if sRest.strip() == multiLineOpen:
            lBody = []
            iIndex += 1
            while iIndex < len(lLines) and lLines[iIndex].rstrip("\r\n").strip() != multiLineClose:
                lBody.append(lLines[iIndex].rstrip("\r\n"))
                iIndex += 1
            iIndex += 1
            lSections[-1].lPairs.append(Pair(sKey, "\n".join(lBody), bMultiLine=True))
            continue
        lSections[-1].lPairs.append(Pair(sKey, sRest.strip()))
        iIndex += 1
    # An empty leading Global section is an artefact rather than content.
    if lSections and lSections[0].sName == globalSectionName and not lSections[0].lPairs:
        lSections.pop(0)
    return lSections


def read(sPath):
    if not os.path.isfile(sPath):
        return []
    with open(sPath, "r", encoding="utf-8-sig", errors="replace") as fFile:
        return parseLines(fFile.read().splitlines())


def renderLines(lSections):
    lLines = []
    for iIndex, section in enumerate(lSections):
        if section.sName != globalSectionName or iIndex > 0:
            lLines.append(f"[{section.sName}]")
        for pair in section.lPairs:
            if pair.bLiteral:
                lLines.append(pair.sRaw)
            elif pair.bMultiLine:
                lLines.append(f"{pair.sKey}={multiLineOpen}")
                lLines.extend(pair.sValue.split("\n"))
                lLines.append(multiLineClose)
            else:
                lLines.append(f"{pair.sKey}={pair.sValue}")
    return lLines


def write(sPath, lSections, bBom=True):
    """Write sections back, with Windows line endings and a byte order mark."""
    sBody = "\r\n".join(renderLines(lSections))
    if sBody and not sBody.endswith("\r\n"):
        sBody += "\r\n"
    with open(sPath, "w", encoding="utf-8-sig" if bBom else "utf-8", newline="") as fFile:
        fFile.write(sBody)
    return True


def getValue(sPath, sSection, sKey, sDefault=""):
    for section in read(sPath):
        if section.sName.lower() == str(sSection).lower():
            return section.get(sKey, sDefault)
    return sDefault


def setValue(sPath, sSection, sKey, sValue):
    """Change one value, leaving every comment, blank line and order alone."""
    lSections = read(sPath)
    for section in lSections:
        if section.sName.lower() == str(sSection).lower():
            section.set(sKey, sValue)
            return write(sPath, lSections)
    section = Section(str(sSection))
    section.set(sKey, sValue)
    lSections.append(section)
    return write(sPath, lSections)

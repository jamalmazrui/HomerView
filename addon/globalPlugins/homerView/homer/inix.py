r'''inix.py -- part of the shared Homer toolkit: order preserving .ini and .inix files.

THIS MODULE AND CSharp\Inix.cs (InixCodec) READ THE SAME FORMAT THE SAME WAY.
Python already has configparser, but configparser discards comments and blank
lines and rewrites a file in its own order. A file a person edits by hand
should come back as they left it, with their notes in place and a changed
value changed where it stands. That is what order preserving means here.

.inix is a superset of .ini: [Section] lines, name = value lines, comments
starting with ; or #, an implicit Global section for names before the first
section, and three ways to write a value that spans lines (help\Inix.md):

    1. PLAIN. A name line with nothing after the equals sign, the value on the
       lines below. It runs to the next section line or the next line that
       reads as name = value, so it suits a value with no equals sign in it.
       Blank lines at its end are layout and are dropped.

    2. BACKTICK FENCE. name = ` opens it and a line holding only ` closes it.
       Everything between is the value exactly as written, equals signs and
       all. A writer may use this form for every multi-line value, as the
       more reliable choice.

    3. TRIPLE QUOTE FENCE. name = """ opens it and a line holding only """
       closes it, the Python convention, for the rare value that contains a
       backtick.

In every form the name line is trimmed, so spaces around the equals sign mean
nothing. A one-line value whose first and last characters are double quotes
loses that one outer pair, so "" is an empty value and " dog" keeps its space.
A fenced value is VERBATIM: the reader neither trims nor drops any of its
lines. [;Name] comments out a whole section, and [] names a section Record1,
Record2 and so on, as Inix.cs does.

For compatibility, a value between name = { and a closing } line, which this
module wrote before 1.57.0, is still read; it is never written.

Usage:

    import inix
    lSections = inix.read(sPath)              # order preserving, for editing
    sValue = inix.getValue(sPath, "Settings", "Voice")
    inix.setValue(sPath, "Settings", "Voice", "Kokoro")
    dSections = inix.readInix(sPath)          # {section: {name: value}}, for reading
    inix.writeInix(sPath, dSections)
    lItems = inix.inixList(sValue)            # one per line, or comma separated
'''

import os, re

c_sBacktick = "`"
c_sLegacyClose = "}"
c_sLegacyOpen = "{"
c_sTripleQuote = '"""'
globalSectionName = "Global"
lsIgnored = []


class Pair:
    """One name and value, or a comment or blank line kept in place. sForm records how a value was written --
    None for one line, "plain", a backtick or a triple quote -- so an unchanged value is written back the same way."""

    def __init__(self, sKey="", sValue="", sRaw=None, bMultiLine=False, sForm=None):
        self.sForm = sForm if sForm is not None else ("plain" if bMultiLine else None)
        self.sKey = sKey
        self.sRaw = sRaw
        self.sValue = sValue

    @property
    def bLiteral(self):
        """True for a comment, blank or ignored line, which is kept exactly."""
        return self.sRaw is not None

    @property
    def bMultiLine(self):
        return "\n" in self.sValue or self.sForm in ("plain", c_sBacktick, c_sTripleQuote)


class Section:
    def __init__(self, sName="", sHeader=None):
        self.lPairs = []
        self.sHeader = sHeader
        self.sName = sName

    def get(self, sKey, sDefault=""):
        for pair in self.lPairs:
            if not pair.bLiteral and pair.sKey.lower() == str(sKey).lower(): return pair.sValue
        return sDefault

    def set(self, sKey, sValue):
        """Change a value in place, or add it at the end of the section. The writer then chooses its form afresh."""
        for pair in self.lPairs:
            if not pair.bLiteral and pair.sKey.lower() == str(sKey).lower():
                pair.sValue, pair.sForm = str(sValue), None
                return False
        self.lPairs.append(Pair(str(sKey), str(sValue)))
        return True

    def keys(self):
        return [pair.sKey for pair in self.lPairs if not pair.bLiteral]

    def asDictionary(self):
        return {pair.sKey: pair.sValue for pair in self.lPairs if not pair.bLiteral}


def looksLikePartOfValue(sLine):
    """Inix.cs's test, kept identical: a line with an equals sign reads as a new name = value line only when the text
    before the sign is a plausible name -- letters, digits, underscores, hyphens and spaces."""
    iEq = sLine.find("=")
    if iEq <= 0: return True
    sBefore = sLine[:iEq].strip()
    if not sBefore: return True
    return any(not (c.isalnum() or c in "_ -") for c in sBefore)


def endsPlainValue(sLine):
    """True when a line ends a plain multi-line value: a section line, or a name = value line."""
    sTrim = sLine.strip()
    if sTrim.startswith("[") and sTrim.endswith("]"): return True
    return not sTrim.startswith(";") and sTrim.find("=") > 0 and not looksLikePartOfValue(sTrim)


def parseLines(lLines):
    """Turn lines into sections, keeping comments and blank lines where they are."""
    global lsIgnored
    lsIgnored = []
    lSections = [Section(globalSectionName)]
    bSkipSection = False
    iRecord = 0
    iIndex = 0
    while iIndex < len(lLines):
        sLine = lLines[iIndex].rstrip("\r\n")
        sTrim = sLine.strip()
        if sTrim.startswith("[") and sTrim.endswith("]") and len(sTrim) >= 2:
            sInner = sTrim[1:-1].strip()
            bSkipSection = sInner.startswith(";")
            if bSkipSection:
                lSections[-1].lPairs.append(Pair(sRaw=sLine))
            else:
                if not sInner:
                    iRecord += 1
                    sInner = "Record" + str(iRecord)
                elif sInner.lower().startswith("record"):
                    iRecord += 1
                lSections.append(Section(sInner, sLine))
            iIndex += 1
            continue
        if bSkipSection or not sTrim or sTrim[0] in ";#" or sLine.find("=") <= 0:
            if sTrim and not bSkipSection and sTrim[0] not in ";#": lsIgnored.append(sLine)
            lSections[-1].lPairs.append(Pair(sRaw=sLine))
            iIndex += 1
            continue
        iEq = sLine.find("=")
        sKey, sValTrim = sLine[:iEq].strip(), sLine[iEq + 1:].strip()
        iIndex += 1
        if sValTrim in (c_sBacktick, c_sTripleQuote, c_sLegacyOpen):
            sClose = c_sLegacyClose if sValTrim == c_sLegacyOpen else sValTrim
            lBody = []
            iOpenLine = iIndex
            while iIndex < len(lLines) and lLines[iIndex].rstrip("\r\n").strip() != sClose:
                lBody.append(lLines[iIndex].rstrip("\r\n"))
                iIndex += 1
            # AN UNTERMINATED FENCE IS REPORTED (kit 1.62.5, from an audit by another AI): it still reads to the end of
            # the file, as before, but no longer silently -- the diagnostics name the key and the line it opened on.
            if iIndex >= len(lLines): lsIgnored.append("unterminated %s fence for %s, opened on line %d; read to the end of the file" % (sValTrim, sKey, iOpenLine))
            iIndex += 1
            lSections[-1].lPairs.append(Pair(sKey, "\n".join(lBody), sForm=c_sBacktick if sValTrim == c_sLegacyOpen else sValTrim))
            continue
        if not sValTrim:
            lBody = []
            while iIndex < len(lLines) and not endsPlainValue(lLines[iIndex].rstrip("\r\n")):
                lBody.append(lLines[iIndex].rstrip("\r\n"))
                iIndex += 1
            iTrailing = 0
            while lBody and not lBody[-1].strip():
                lBody.pop()
                iTrailing += 1
            lSections[-1].lPairs.append(Pair(sKey, "\n".join(lBody), sForm="plain" if lBody else None))
            for i in range(iTrailing): lSections[-1].lPairs.append(Pair(sRaw=""))
            continue
        if len(sValTrim) >= 2 and sValTrim.startswith('"') and sValTrim.endswith('"'): sValTrim = sValTrim[1:-1]
        lSections[-1].lPairs.append(Pair(sKey, sValTrim))
    if lSections and lSections[0].sName == globalSectionName and not lSections[0].lPairs: lSections.pop(0)
    return lSections


def read(sPath):
    """The sections of a file, in order, or [] when it does not exist."""
    if not os.path.isfile(sPath): return []
    with open(sPath, "r", encoding="utf-8-sig", errors="replace") as fFile: return parseLines(fFile.read().splitlines())


def hasSoleLine(sValue, sToken):
    """True when some line of the value, trimmed, is exactly the token, so that token cannot close its fence."""
    return any(sOne.strip() == sToken for sOne in sValue.split("\n"))


def chooseFence(sValue):
    """How to write a value, by help\\Inix.md's rule and Inix.cs's chooseFence: None for one line with no equals sign
    or bracket; otherwise a backtick fence, or a triple quote fence when the value contains a backtick."""
    if "\n" not in sValue and "=" not in sValue and "[" not in sValue: return None
    # A value holding both fences as lines of their own cannot be written so that it reads back exactly; it is refused,
    # rather than written corrupted (kit 1.62.5, from an audit by another AI).
    if hasSoleLine(sValue, c_sBacktick) and hasSoleLine(sValue, c_sTripleQuote):
        raise ValueError("an inix value cannot hold both a line of one backtick and a line of three double quotes")
    if c_sBacktick in sValue and not hasSoleLine(sValue, c_sTripleQuote): return c_sTripleQuote
    if hasSoleLine(sValue, c_sBacktick) and not hasSoleLine(sValue, c_sTripleQuote): return c_sTripleQuote
    return c_sBacktick


def renderPair(pair):
    """The lines for one value. A plain value read as plain stays plain while no line of it would end it early."""
    sValue = pair.sValue.replace("\r\n", "\n").replace("\r", "\n")
    sForm = pair.sForm
    if sForm == "plain" and (not sValue.strip() or any(endsPlainValue(sOne) for sOne in sValue.split("\n"))): sForm = None
    if sForm is None or (sForm in (c_sBacktick, c_sTripleQuote) and hasSoleLine(sValue, sForm)): sForm = chooseFence(sValue)
    if sForm == "plain": return [pair.sKey + " ="] + sValue.split("\n")
    if sForm in (c_sBacktick, c_sTripleQuote): return [pair.sKey + "=" + sForm] + sValue.split("\n") + [sForm]
    # A value that is itself a fence mark -- one backtick, three double quotes, or { -- is quoted, since bare it would
    # read back as the start of a fence and swallow what follows (kit 1.62.5).
    bQuote = not sValue or sValue != sValue.strip() or (len(sValue) >= 2 and sValue.startswith('"') and sValue.endswith('"')) or sValue.strip() in (c_sBacktick, c_sTripleQuote, c_sLegacyOpen)
    return [pair.sKey + ' = "' + sValue + '"'] if bQuote else [pair.sKey + " = " + sValue]


def renderLines(lSections):
    lLines = []
    for iIndex, section in enumerate(lSections):
        if section.sName != globalSectionName or iIndex > 0: lLines.append(section.sHeader if section.sHeader else "[" + section.sName + "]")
        for pair in section.lPairs:
            if pair.bLiteral: lLines.append(pair.sRaw)
            else: lLines.extend(renderPair(pair))
    return lLines


def write(sPath, lSections, bBom=True):
    """Write sections back, with Windows line endings and, by default, a byte order mark."""
    sBody = "\r\n".join(renderLines(lSections))
    if sBody and not sBody.endswith("\r\n"): sBody += "\r\n"
    # Written to a temporary file beside it and then put in its place, so a crash never leaves half a file (kit 1.62.5).
    sTemp = sPath + ".writing"
    with open(sTemp, "w", encoding="utf-8-sig" if bBom else "utf-8", newline="") as fFile:
        fFile.write(sBody)
        fFile.flush()
        os.fsync(fFile.fileno())
    os.replace(sTemp, sPath)
    return True


def getValue(sPath, sSection, sKey, sDefault=""):
    for section in read(sPath):
        if section.sName.lower() == str(sSection).lower(): return section.get(sKey, sDefault)
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


def readInix(sPath):
    """{section: {name: value}} from a file, for a program that only reads. Names before the first section are under
    Global. Lines that are neither values nor comments are listed in lsIgnored. {} when the file is missing."""
    dSections = {}
    for section in read(sPath): dSections.setdefault(section.sName, {}).update(section.asDictionary())
    return dSections


def writeInix(sPath, dSections):
    """Writes {section: {name: value}}, UTF-8 with a byte order mark and CRLF, a blank line after each section. A list
    or tuple is written one item per line."""
    lSections = []
    for sSection, dKeys in dSections.items():
        section = Section(sSection)
        for sKey, vValue in dKeys.items():
            if isinstance(vValue, (list, tuple)): vValue = "\n".join(str(v) for v in vValue)
            section.set(sKey, "" if vValue is None else str(vValue))
        section.lPairs.append(Pair(sRaw=""))
        lSections.append(section)
    return write(sPath, lSections)


def inixList(sValue):
    """A list from a value: one item per line when it holds newlines, else comma separated; empty gives []."""
    if not sValue or not sValue.strip(): return []
    if "\n" in sValue: return [sOne.strip() for sOne in sValue.split("\n") if sOne.strip()]
    return [sOne.strip() for sOne in sValue.split(",") if sOne.strip()]

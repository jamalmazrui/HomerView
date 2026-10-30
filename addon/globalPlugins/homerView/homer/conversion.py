"""conversion.py -- convert a file from one type to another, the one Homer way.

Every Homer program that converts a file calls this, not Pandoc or Office
directly. The routes are in conversions.inix, which C#'s Conversion.cs
reads too, so a route is decided once for both languages. Only approved
components: Pandoc, NuGet and PyPI packages, and Tesseract; Microsoft Office,
by COM, only as the last resort. No other converting program is looked for.

    convert(sSource, sTarget, dOptions=None)   -> dict: path, route, engine, ms
    toText(sSource)                            -> str, by the quickest route
    plan(sSource, sTargetType)                 -> the route that would be used, and why
    engineAvailable(sEngine)                   -> bool

sTarget is a path, or just a type such as "md", which writes beside the source.
Each conversion is logged with its route, its steps and its time.
"""
import glob
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET

try:
    import inix
except ImportError:
    inix = None
try:
    import log as homerLog
except ImportError:
    homerLog = None

sTableName = "conversions.inix"
# NO CONSOLE WINDOWS (kit 1.88.6): a tool started from a windowed program -- NVDA, which runs HomerView
# -- would flash a console over the user's work, so every tool runs without one.
iNoWindow = getattr(subprocess, "CREATE_NO_WINDOW", 0)
iTimeoutSeconds = 600


def say(sText):
    if homerLog:
        try: homerLog.info("conversion: " + sText)
        except Exception: pass


# ---------- the table ----------

def tablePath():
    """conversions.inix beside this module, or in the folder above it (the kit's exec)."""
    sHere = os.path.dirname(os.path.abspath(__file__))
    for sDir in (sHere, os.path.dirname(sHere)):
        sPath = os.path.join(sDir, sTableName)
        if os.path.isfile(sPath): return sPath
    raise FileNotFoundError("no %s beside %s or above it" % (sTableName, sHere))


def loadTable():
    """{source type: {target type: [route, ...]}}, a route being [(engine, handsOnType), ...].

    Sections are named <source>2<target> (kit 1.74.0), e.g. [pdf2txt], each with a
    ways= line listing its routes best first, the same file C#'s Conversion.cs reads.
    """
    dRaw = inix.readInix(tablePath())
    dTable = {}
    for sName, dSection in dRaw.items():
        oMatch = re.match(r"^([a-z0-9]+?)2([a-z0-9]+)$", sName.strip().lower())
        if not oMatch or not isinstance(dSection, dict): continue
        sWays = next((v for k, v in dSection.items() if k.lower() == "ways"), "")
        lRoutes = []
        for sRoute in sWays.split(","):
            if not sRoute.strip(): continue
            lSteps = []
            for sStep in sRoute.split(">"):
                sEngine, _, sHands = sStep.strip().partition(":")
                lSteps.append((sEngine.strip().lower(), sHands.strip().lower()))
            lRoutes.append(lSteps)
        dTable.setdefault(oMatch.group(1), {})[oMatch.group(2)] = lRoutes
    return dTable


def typeOf(sPath):
    """The type by extension, as Conversion.cs's typeOf: .html is .htm and .markdown is .md (1.90.0), so a
    Python app and a C# app take the same route for the same file. A bare type ("pdf") is its own type."""
    sType = os.path.splitext(sPath)[1] if "." in sPath else sPath
    sType = sType.lstrip(".").lower()
    if sType == "html": return "htm"
    if sType == "markdown": return "md"
    return sType


# ---------- the engines: present or not ----------

def findProgram(sName, lsWindowsPaths=()):
    """The machine-wide install first, then the PATH, as Conversion.cs does (1.77.2). Asking the PATH first
    picked an old Pandoc 2.19.2 in c:\\bin over the machine-wide 3.12.1 on Jamal's computer, so the same
    conversion could differ between the C# and Python apps."""
    for sPattern in lsWindowsPaths:
        for sPath in glob.glob(os.path.expandvars(sPattern)):
            if os.path.isfile(sPath): return sPath
    sFound = shutil.which(sName)
    return sFound or ""


def programFor(sEngine):
    if sEngine == "pandoc": return findProgram("pandoc", [r"%ProgramFiles%\Pandoc\pandoc.exe", r"%LOCALAPPDATA%\Pandoc\pandoc.exe"])
    if sEngine == "tesseract": return findProgram("tesseract", [r"%ProgramFiles%\Tesseract-OCR\tesseract.exe"])
    if sEngine == "edge": return findProgram("msedge", [r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe", r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"])
    return ""


def engineAvailable(sEngine):
    if sEngine in ("copy", "json", "markdown", "page", "records", "sqlite", "table", "zipxml"): return True
    if sEngine in ("edge", "pandoc"): return bool(programFor(sEngine))
    if sEngine == "ocr":
        try: import pypdfium2
        except ImportError: return False
        return bool(programFor("tesseract"))
    if sEngine == "pdftext":
        try: import pypdf; return True
        except ImportError: return False
    if sEngine == "pdfstructure":
        try: import pdfminer.high_level; return True
        except ImportError: return False
    if sEngine == "officecom":
        if os.name != "nt": return False
        try: import win32com.client; return True
        except ImportError: return False
    return False


# ---------- planning ----------

def plan(sSource, sTargetType):
    """(route, lsSkipped): the first route whose engines are all present, and why each earlier one was passed over."""
    sFrom = typeOf(sSource); sTo = sTargetType.lstrip(".").lower()
    lRoutes = loadTable().get(sFrom, {}).get(sTo)
    if not lRoutes: return None, ["no route from %s to %s in %s" % (sFrom or "a file with no type", sTo, sTableName)]
    lsSkipped = []
    for lSteps in lRoutes:
        lsMissing = [sEngine for sEngine, _ in lSteps if not engineAvailable(sEngine)]
        if not lsMissing: return lSteps, lsSkipped
        lsSkipped.append("%s: %s not present" % (" > ".join(e for e, _ in lSteps), ", ".join(lsMissing)))
    return None, lsSkipped


# ---------- running each engine: (source path, target type, output path) ----------

def run(lsCommand, sWhat):
    oDone = subprocess.run(lsCommand, capture_output=True, timeout=iTimeoutSeconds, creationflags=iNoWindow)
    if oDone.returncode != 0:
        raise RuntimeError("%s failed (exit %d): %s" % (sWhat, oDone.returncode, oDone.stderr.decode("utf-8", "replace")[:400]))


def engineCopy(sSource, sTo, sOut):
    shutil.copyfile(sSource, sOut)


dPandocWriter = {"md": "markdown", "htm": "html5", "html": "html5", "txt": "plain", "docx": "docx", "epub": "epub",
                   "odt": "odt", "pptx": "pptx", "rtf": "rtf"}
dPandocReader = {"htm": "html", "md": "markdown", "txt": "markdown", "docx": "docx", "epub": "epub", "odt": "odt", "rtf": "rtf", "html": "html"}


def enginePandoc(sSource, sTo, sOut):
    lsCommand = [programFor("pandoc"), sSource, "-f", dPandocReader.get(typeOf(sSource), typeOf(sSource)),
                 "-t", dPandocWriter.get(sTo, sTo), "-o", sOut, "--wrap=none"]
    if sTo in ("htm", "html", "docx", "epub", "odt", "rtf"): lsCommand.append("--standalone")
    # Math as MathML (1.77.0), which screen readers read as math; a page without math is unchanged.
    if sTo in ("htm", "html"): lsCommand.append("--mathml")
    run(lsCommand, "Pandoc")


def enginePdfText(sSource, sTo, sOut):
    import pypdf
    oReader = pypdf.PdfReader(sSource)
    lsPages = [(oPage.extract_text() or "").strip() for oPage in oReader.pages]
    if not any(lsPages): raise RuntimeError("the PDF has no text layer; it needs recognition (ocr)")
    open(sOut, "w", encoding="utf-8-sig", newline="\r\n").write("\n\n".join(lsPages) + "\n")


def enginePdfStructure(sSource, sTo, sOut):
    """Lines with their type sizes; the commonest size is the body, and larger sizes
    become headings, the largest level 1. Nothing is guessed beyond the sizes."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer, LTTextLine, LTChar
    lLines = []
    for oPage in extract_pages(sSource):
        for oBox in oPage:
            if not isinstance(oBox, LTTextContainer): continue
            for oLine in oBox:
                if not isinstance(oLine, LTTextLine): continue
                sText = oLine.get_text().strip()
                lnSizes = [round(o.size, 1) for o in oLine if isinstance(o, LTChar)]
                if sText and lnSizes: lLines.append((sText, max(set(lnSizes), key=lnSizes.count)))
        lLines.append(("", 0))
    if not any(s for s, _ in lLines): raise RuntimeError("the PDF has no text layer; it needs recognition (ocr)")
    dCount = {}
    for sText, nSize in lLines:
        if nSize: dCount[nSize] = dCount.get(nSize, 0) + len(sText)
    nBody = max(dCount, key=dCount.get)
    lnHeadings = sorted([n for n in dCount if n > nBody + 0.5], reverse=True)[:4]
    lsOut, lsPara = [], []
    def flush():
        if lsPara: lsOut.append(" ".join(lsPara)); lsOut.append(""); lsPara.clear()
    for sText, nSize in lLines:
        if not sText: flush(); continue
        if nSize in lnHeadings and len(sText) < 160:
            flush(); lsOut.append("#" * (lnHeadings.index(nSize) + 1) + " " + sText); lsOut.append("")
        else:
            lsPara.append(sText)
    flush()
    open(sOut, "w", encoding="utf-8-sig", newline="\r\n").write("\n".join(lsOut).strip() + "\n")


nOcrScale = 200 / 72   # pages drawn at 200 dots an inch, enough for Tesseract


def engineOcr(sSource, sTo, sOut):
    """A scanned PDF: each page drawn as a picture by pypdfium2, read by Tesseract."""
    import pypdfium2
    sDir = tempfile.mkdtemp(prefix="homerOcr-")
    try:
        oPdf = pypdfium2.PdfDocument(sSource)
        for iPage in range(len(oPdf)):
            oPdf[iPage].render(scale=nOcrScale).to_pil().save(os.path.join(sDir, "page%04d.png" % iPage))
        oPdf.close()
        lsText = []
        for sImage in sorted(glob.glob(os.path.join(sDir, "page*.png"))):
            oDone = subprocess.run([programFor("tesseract"), sImage, "stdout"], capture_output=True, timeout=iTimeoutSeconds, creationflags=iNoWindow)
            lsText.append(oDone.stdout.decode("utf-8", "replace").strip())
        open(sOut, "w", encoding="utf-8-sig", newline="\r\n").write("\n\n".join(lsText) + "\n")
    finally:
        shutil.rmtree(sDir, ignore_errors=True)


sW = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
sA = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
sS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
sTextNamespace = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def zipDocx(oZip, bMarkdown):
    oRoot = ET.fromstring(oZip.read("word/document.xml"))
    lsOut = []
    for oPara in oRoot.iter(sW + "p"):
        sText = "".join(o.text or "" for o in oPara.iter(sW + "t")).strip()
        if not sText: continue
        oStyle = oPara.find(sW + "pPr/" + sW + "pStyle")
        oMatch = re.match(r"(?i)heading\s*(\d)", oStyle.get(sW + "val", "")) if oStyle is not None else None
        lsOut.append(("#" * int(oMatch.group(1)) + " " + sText) if (bMarkdown and oMatch) else sText)
    return lsOut


def xlsxSheets(oZip):
    """Each worksheet as (name, part path), in the workbook's own order.

    BY THE WORKBOOK, NOT THE FILE NAME (1.94.1, from an audit by another AI). The first sheet was taken to be
    sheet1.xml, but a workbook names its sheets in xl/workbook.xml and finds each part through its relationship,
    so a sheet moved, renamed or deleted in Excel read the wrong one. The relationship is followed; a workbook
    without one falls back to sheetN.xml, as before."""
    sR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    sP = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    lsNames = set(oZip.namelist())
    dTargets = {}
    if "xl/_rels/workbook.xml.rels" in lsNames:
        for oRel in ET.fromstring(oZip.read("xl/_rels/workbook.xml.rels")).iter(sP + "Relationship"):
            sTarget = (oRel.get("Target") or "").replace("\\", "/")
            sTarget = sTarget.lstrip("/") if sTarget.startswith("/") else "xl/" + sTarget
            dTargets[oRel.get("Id")] = sTarget
    lSheets = []
    if "xl/workbook.xml" in lsNames:
        for iSheet, oSheet in enumerate(ET.fromstring(oZip.read("xl/workbook.xml")).iter(sS + "sheet"), 1):
            sPath = dTargets.get(oSheet.get(sR + "id"), "xl/worksheets/sheet%d.xml" % iSheet)
            if sPath in lsNames: lSheets.append((oSheet.get("name") or "Sheet%d" % iSheet, sPath))
    if not lSheets and "xl/worksheets/sheet1.xml" in lsNames: lSheets.append(("Sheet1", "xl/worksheets/sheet1.xml"))
    return lSheets


def xlsxRows(oZip, sPath, lsShared):
    """A worksheet's rows, each cell in its own column: a blank cell keeps its place, so A, blank, C stays three
    cells, not two (1.94.1, from an audit by another AI). Shared strings, inline strings and numbers are read."""
    llRows = []
    for oRow in ET.fromstring(oZip.read(sPath)).iter(sS + "row"):
        lsCells = []
        for oCell in oRow.iter(sS + "c"):
            iColumn = xlsxIndex(oCell.get("r", ""))
            if iColumn < 0: iColumn = len(lsCells)
            while iColumn > len(lsCells): lsCells.append("")
            oValue = oCell.find(sS + "v"); oInline = oCell.find(sS + "is")
            sValue = oValue.text if oValue is not None else ("".join(o.text or "" for o in oInline.iter(sS + "t")) if oInline is not None else "")
            if oCell.get("t") == "s" and sValue: sValue = lsShared[int(sValue)]
            lsCells.append(sValue or "")
        llRows.append(lsCells)
    return llRows


def zipXlsx(oZip, bMarkdown, bCsv=False):
    lsShared = []
    if "xl/sharedStrings.xml" in oZip.namelist():
        for oItem in ET.fromstring(oZip.read("xl/sharedStrings.xml")).iter(sS + "si"):
            lsShared.append("".join(o.text or "" for o in oItem.iter(sS + "t")))
    lsOut = []
    for sName, sPath in xlsxSheets(oZip):
        llRows = xlsxRows(oZip, sPath, lsShared)
        if bCsv:
            import csv, io
            oBuffer = io.StringIO(); csv.writer(oBuffer, lineterminator="\n").writerows(llRows)
            return oBuffer.getvalue().rstrip("\n").split("\n")   # the first sheet, as a comma-separated file
        if bMarkdown:
            lsOut.append("## " + sName); lsOut.append("")
            if llRows:
                iWidth = max(len(r) for r in llRows)
                for i, lsRow in enumerate(llRows):
                    lsOut.append("| " + " | ".join(c.replace("|", "\\|") for c in (lsRow + [""] * iWidth)[:iWidth]).replace("\n", " ") + " |")
                    if i == 0: lsOut.append("|" + "---|" * iWidth)
            lsOut.append("")
        else:
            lsOut.append(sName); lsOut += ["\t".join(r) for r in llRows]; lsOut.append("")
    return lsOut


def zipPptx(oZip, bMarkdown):
    lsSlides = sorted([s for s in oZip.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", s)], key=lambda s: int(re.findall(r"\d+", s)[-1]))
    lsOut = []
    sP = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
    for iSlide, sSlide in enumerate(lsSlides, 1):
        oRoot = ET.fromstring(oZip.read(sSlide))
        sTitle, lsBody = "", []
        for oShape in oRoot.iter(sP + "sp"):
            oPh = oShape.find(".//" + sP + "ph")
            lsParas = ["".join(o.text or "" for o in oPara.iter(sA + "t")).strip() for oPara in oShape.iter(sA + "p")]
            lsParas = [s for s in lsParas if s]
            if oPh is not None and oPh.get("type") in ("title", "ctrTitle") and not sTitle: sTitle = " ".join(lsParas)
            else: lsBody += lsParas
        if bMarkdown:
            lsOut.append("## " + (sTitle or "Slide %d" % iSlide)); lsOut.append("")
            lsOut += ["- " + s for s in lsBody]; lsOut.append("")
        else:
            lsOut += ([sTitle] if sTitle else []) + lsBody + [""]
    return lsOut


def zipOdf(oZip, bMarkdown):
    oRoot = ET.fromstring(oZip.read("content.xml"))
    lsOut = []
    for oNode in oRoot.iter():
        if oNode.tag in (sTextNamespace + "p", sTextNamespace + "h"):
            sText = "".join(oNode.itertext()).strip()
            if not sText: continue
            if bMarkdown and oNode.tag == sTextNamespace + "h":
                sText = "#" * int(oNode.get(sTextNamespace + "outline-level", "1")) + " " + sText
            lsOut.append(sText)
    return lsOut


sDraw = "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}"
sPres = "{urn:oasis:names:tc:opendocument:xmlns:presentation:1.0}"


def zipOdp(oZip, bMarkdown):
    """OpenDocument slides: each draw:page is a slide, its title the frame of class title."""
    oRoot = ET.fromstring(oZip.read("content.xml"))
    lsOut = []
    for iSlide, oPage in enumerate(oRoot.iter(sDraw + "page"), 1):
        sTitle, lsBody = "", []
        for oFrame in oPage.iter(sDraw + "frame"):
            lsParas = [s for s in ("".join(o.itertext()).strip() for o in oFrame.iter(sTextNamespace + "p")) if s]
            if oFrame.get(sPres + "class") == "title" and not sTitle: sTitle = " ".join(lsParas)
            else: lsBody += lsParas
        if bMarkdown:
            lsOut.append("## " + (sTitle or "Slide %d" % iSlide)); lsOut.append("")
            lsOut += ["- " + s for s in lsBody]; lsOut.append("")
        else:
            lsOut += ([sTitle] if sTitle else []) + lsBody + [""]
    return lsOut


def engineZipXml(sSource, sTo, sOut):
    sFrom = typeOf(sSource); bMarkdown = (sTo == "md")
    with zipfile.ZipFile(sSource) as oZip:
        if sFrom == "docx": lsOut = zipDocx(oZip, bMarkdown)
        elif sFrom == "xlsx": lsOut = zipXlsx(oZip, bMarkdown, sTo == "csv")
        elif sFrom == "pptx": lsOut = zipPptx(oZip, bMarkdown)
        elif sFrom == "odp": lsOut = zipOdp(oZip, bMarkdown)
        elif sFrom in ("odt", "ods"): lsOut = zipOdf(oZip, bMarkdown)
        else: raise RuntimeError("zipxml does not read .%s" % sFrom)
    sJoin = "\n\n" if (bMarkdown and sFrom in ("docx", "odt")) else "\n"
    open(sOut, "w", encoding="utf-8-sig", newline="\r\n").write(sJoin.join(lsOut).strip() + "\n")


dOfficeFormat = {("word", "doc"): 0, ("word", "docx"): 16, ("word", "odt"): 23, ("word", "pdf"): 17, ("word", "htm"): 10,
                   ("word", "rtf"): 6, ("word", "txt"): 7,
                   ("excel", "xlsx"): 51, ("excel", "csv"): 6, ("excel", "htm"): 44,
                   ("powerpoint", "pptx"): 24, ("powerpoint", "pdf"): 32}


def engineOfficeCom(sSource, sTo, sOut):
    """The last resort: Microsoft Office by COM, Windows only, and logged as such."""
    import win32com.client
    sFrom = typeOf(sSource)
    sApp = "word" if sFrom in ("doc", "docx", "rtf", "odt", "htm", "html", "txt") else ("excel" if sFrom in ("xls", "xlsx", "ods", "csv") else "powerpoint")
    iFormat = dOfficeFormat.get((sApp, sTo))
    if iFormat is None: raise RuntimeError("Office cannot write .%s from .%s here" % (sTo, sFrom))
    say("officecom: the last resort, for %s" % os.path.basename(sSource))
    # OFFICE WRITES ITS OWN NAME (9 October 2026): the engine hands every route a target ending in .part, renamed
    # when the route succeeds. Word saves under exactly that name, but PowerPoint adds the extension of the format
    # it saves, so sample.pdf.part came out as sample.pdf.part.pdf and the rename failed with "cannot find the file
    # specified" -- the kit's pptx > pdf test failed on every build. Office now saves into a folder of its own under
    # a name with the right extension, and the result is moved to the target.
    sOfficeDir = tempfile.mkdtemp(prefix="homerOffice-")
    sFinal = sOut
    sOut = os.path.join(sOfficeDir, "converted." + sTo)
    try:
        engineOfficeComSave(sApp, sSource, sOut, iFormat)
        if not os.path.isfile(sOut):
            lsMade = [s for s in os.listdir(sOfficeDir) if s.lower().startswith("converted")]
            if not lsMade: raise RuntimeError("Office reported success but wrote no file")
            sOut = os.path.join(sOfficeDir, lsMade[0])
        # WORD'S TEXT IN THE HOMER ENCODING (1.76.1): UTF-8 with a byte order mark, whatever Word chose to write.
        if sApp == "word" and sTo == "txt":
            sText = decodeText(open(sOut, "rb").read())
            open(sOut, "w", encoding="utf-8-sig", newline="").write(sText)
        os.replace(sOut, sFinal)
    finally:
        shutil.rmtree(sOfficeDir, ignore_errors=True)


def engineOfficeComSave(sApp, sSource, sOut, iFormat):
    """Opens sSource in the Office application sApp and saves it to sOut in format iFormat."""
    import win32com.client
    if sApp == "word":
        oApp = win32com.client.DispatchEx("Word.Application"); oApp.Visible = False
        try:
            oDoc = oApp.Documents.Open(os.path.abspath(sSource), ReadOnly=True)
            # A tagged PDF (1.91.0): Word's export with structure tags and heading bookmarks, as Conversion.cs.
            if iFormat == 17: oDoc.ExportAsFixedFormat(os.path.abspath(sOut), 17, OpenAfterExport=False, IncludeDocProps=True, CreateBookmarks=1, DocStructureTags=True)
            else: oDoc.SaveAs2(os.path.abspath(sOut), FileFormat=iFormat)
            oDoc.Close(False)
        finally: oApp.Quit()
    elif sApp == "excel":
        oApp = win32com.client.DispatchEx("Excel.Application"); oApp.Visible = False; oApp.DisplayAlerts = False
        try:
            oBook = oApp.Workbooks.Open(os.path.abspath(sSource), ReadOnly=True); oBook.SaveAs(os.path.abspath(sOut), FileFormat=iFormat); oBook.Close(False)
        finally: oApp.Quit()
    else:
        oApp = win32com.client.DispatchEx("PowerPoint.Application")
        try:
            oShow = oApp.Presentations.Open(os.path.abspath(sSource), ReadOnly=True, WithWindow=False); oShow.SaveAs(os.path.abspath(sOut), iFormat); oShow.Close()
        finally: oApp.Quit()


def engineMarkdown(sSource, sTo, sOut):
    """The kit's own writer of Markdown as an accessible web page (1.82.1), as Conversion.cs's markdown
    engine does, line for line: a second way after Pandoc for md2htm and pdf2htm, so a computer without
    Pandoc still gets a page. Headings, paragraphs, bullet and numbered lists, pipe tables, quotes,
    fenced code, rules; inline links, images with their alt text, bold, italic and code; lang and title
    from front matter, else the first heading, else the file name; the body inside main."""
    if sTo not in ("htm", "html"): raise ValueError("the markdown engine writes web pages only")
    sText = decodeText(open(sSource, "rb").read()).replace("\r\n", "\n").replace("\r", "\n")
    lsLines = sText.split("\n")
    sTitle, sLang, iAt = "", "en", 0
    if lsLines and lsLines[0].strip() == "---":
        iAt = 1
        while iAt < len(lsLines) and lsLines[iAt].strip() != "---":
            oMeta = re.match(r'^\s*(title|lang)\s*:\s*"?(.*?)"?\s*$', lsLines[iAt], re.I)
            if oMeta:
                if oMeta.group(1).lower() == "title": sTitle = oMeta.group(2)
                else: sLang = oMeta.group(2)
            iAt += 1
        iAt += 1
    lsBody, lsPara, dList = [], [], {"kind": ""}
    def closeList():
        if dList["kind"]: lsBody.append("</%s>" % dList["kind"]); dList["kind"] = ""
    def flush():
        if lsPara: lsBody.append("<p>" + markdownInline(" ".join(lsPara)) + "</p>"); del lsPara[:]
    i = iAt
    while i < len(lsLines):
        sLine = lsLines[i]; sTrim = sLine.strip()
        if sTrim.startswith("```"):
            flush(); closeList(); lsCode = []; i += 1
            while i < len(lsLines) and not lsLines[i].strip().startswith("```"): lsCode.append(htmlEscape(lsLines[i])); i += 1
            lsBody.append("<pre><code>" + "\r\n".join(lsCode) + "\r\n</code></pre>"); i += 1; continue
        if sTrim == "": flush(); closeList(); i += 1; continue
        oHead = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", sTrim)
        if oHead:
            flush(); closeList(); iLevel = len(oHead.group(1))
            if not sTitle and iLevel == 1: sTitle = re.sub(r"[*_`]", "", oHead.group(2))
            lsBody.append("<h%d>%s</h%d>" % (iLevel, markdownInline(oHead.group(2)), iLevel)); i += 1; continue
        if re.match(r"^(\*\s*\*\s*\*|-\s*-\s*-|_\s*_\s*_)[\s*_-]*$", sTrim): flush(); closeList(); lsBody.append("<hr>"); i += 1; continue
        if sTrim.startswith("|") and i + 1 < len(lsLines) and re.match(r"^\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?$", lsLines[i + 1].strip()):
            flush(); closeList()
            lsBody.append("<table>\r\n<thead><tr>" + "".join('<th scope="col">%s</th>' % markdownInline(c) for c in markdownCells(sTrim)) + "</tr></thead>\r\n<tbody>")
            i += 2
            while i < len(lsLines) and lsLines[i].strip().startswith("|"):
                lsBody.append("<tr>" + "".join("<td>%s</td>" % markdownInline(c) for c in markdownCells(lsLines[i].strip())) + "</tr>"); i += 1
            lsBody.append("</tbody>\r\n</table>"); continue
        oBullet = re.match(r"^\s*[-*+]\s+(.*)$", sLine); oNumber = re.match(r"^\s*\d+[.)]\s+(.*)$", sLine)
        if oBullet or oNumber:
            flush(); sKind = "ul" if oBullet else "ol"
            if dList["kind"] != sKind: closeList(); lsBody.append("<%s>" % sKind); dList["kind"] = sKind
            lsBody.append("<li>" + markdownInline((oBullet or oNumber).group(1)) + "</li>"); i += 1; continue
        if sTrim.startswith(">"): flush(); closeList(); lsBody.append("<blockquote><p>" + markdownInline(sTrim.lstrip(">").strip()) + "</p></blockquote>"); i += 1; continue
        closeList(); lsPara.append(sTrim); i += 1
    flush(); closeList()
    if not sTitle: sTitle = os.path.splitext(os.path.basename(sSource))[0]
    sPage = ('<!DOCTYPE html>\r\n<html lang="%s">\r\n<head>\r\n<meta charset="utf-8">\r\n'
             '<meta name="viewport" content="width=device-width, initial-scale=1">\r\n<title>%s</title>\r\n</head>\r\n<body>\r\n<main>\r\n'
             % (htmlEscape(sLang), htmlEscape(sTitle))) + "".join(s + "\r\n" for s in lsBody) + "</main>\r\n</body>\r\n</html>\r\n"
    open(sOut, "w", encoding="utf-8-sig", newline="").write(sPage)


def markdownCells(sRow):
    s = sRow.strip()
    if s.startswith("|"): s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"): s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def markdownInline(sText):
    """Code spans and escaped characters set aside first, so neither becomes emphasis; then images,
    links, bold and italic -- the order Conversion.cs uses."""
    lsCode, lsEscaped = [], []
    def keepCode(m): lsCode.append(m.group(1)); return "\x01%d\x02" % (len(lsCode) - 1)
    def keepEscaped(m): lsEscaped.append(m.group(1)); return "\x03%d\x04" % (len(lsEscaped) - 1)
    s = re.sub(r"`([^`]+)`", keepCode, sText)
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>])", keepEscaped, s)
    s = htmlEscape(s)
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)', r'<img src="\2" alt="\1">', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;[^&]*&quot;)?\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", r"<strong>\2</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])", r"<em>\1</em>", s)
    s = re.sub("\x03(\\d+)\x04", lambda m: htmlEscape(lsEscaped[int(m.group(1))]), s)
    s = re.sub("\x01(\\d+)\x02", lambda m: "<code>" + htmlEscape(lsCode[int(m.group(1))]) + "</code>", s)
    return s


def htmlEscape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------- engine: table, as Table.cs does it (1.86.0) ----------
#
# PYTHON CONVERTS TABLES AS C# DOES: the same five forms -- comma separated, tab separated,
# a Homer inix file, a Markdown table and an Excel workbook -- read and written to the same
# layouts as Table.cs, so a table converts alike in every Homer app, whatever its language.
#   inix: one section a row, named Record1, Record2 and so on, padded to the width of the
#     count; a row's empty values are left out; the Global section is not a row.
#   csv and tsv: a value beginning =, @, a tab or a return, or + or - when not a number, gets a
#     leading apostrophe, so no spreadsheet takes it for a formula; quoted only when it must be.
#   xlsx: the first sheet read; written as a minimal workbook, every value an inline string,
#     so leading zeros stay, within Excel's limits of rows, columns and cell length.

def tableRead(sSource):
    """[fields], [[values]] of the first table in a file of one of the five forms."""
    sType = typeOf(sSource)
    if sType in ("csv", "tsv"):
        import csv, io
        sText = decodeText(open(sSource, "rb").read()).replace("\r\n", "\n").replace("\r", "\n")
        llAll = [r for r in csv.reader(io.StringIO(sText), delimiter="," if sType == "csv" else "\t")]
        llAll = [r for r in llAll if r]
        return (llAll[0], llAll[1:]) if llAll else ([], [])
    if sType == "inix":
        import inix
        lsFields, ldRows = [], []
        for oSection in inix.read(sSource):
            if oSection.sName.lower() == "global": continue
            dRow = oSection.asDictionary()
            for sKey in dRow:
                if sKey.lower() not in [s.lower() for s in lsFields]: lsFields.append(sKey)
            ldRows.append({k.lower(): v for k, v in dRow.items()})
        return lsFields, [[d.get(f.lower(), "") for f in lsFields] for d in ldRows]
    if sType == "md":
        llCells = []
        for sRaw in decodeText(open(sSource, "rb").read()).replace("\r\n", "\n").split("\n"):
            sLine = sRaw.strip()
            if "|" not in sLine:
                if llCells: break
                continue
            if re.match(r"^\|?[\s:\-|]+\|?$", sLine): continue
            # An escaped pipe stays in its cell (1.94.1, from an audit by another AI), as Table.cs reads it.
            llCells.append(markdownCells(sLine))
        if not llCells: raise ValueError("no table was found in this Markdown file")
        return llCells[0], llCells[1:]
    if sType == "xlsx":
        import zipfile
        with zipfile.ZipFile(sSource) as oZip:
            lsShared = []
            if "xl/sharedStrings.xml" in oZip.namelist():
                for oItem in ET.fromstring(oZip.read("xl/sharedStrings.xml")).iter(sS + "si"):
                    lsShared.append("".join(o.text or "" for o in oItem.iter(sS + "t")))
            lSheets = xlsxSheets(oZip)
            if not lSheets: raise ValueError("no worksheet was found in this workbook")
            llRows = xlsxRows(oZip, lSheets[0][1], lsShared)   # the workbook's first sheet
        llRows = [r for r in llRows if any(c != "" for c in r)]
        return (llRows[0], llRows[1:]) if llRows else ([], [])
    raise ValueError("the table engine reads csv, tsv, inix, md and xlsx, not " + sType)


def xlsxIndex(sReference):
    """The zero-based column of a cell reference such as C7; -1 when there is none."""
    iColumn = 0
    for sChar in sReference:
        if not sChar.isalpha(): break
        iColumn = iColumn * 26 + (ord(sChar.upper()) - 64)
    return iColumn - 1


def xlsxColumn(iColumn):
    sColumn = ""
    iColumn += 1
    while iColumn > 0:
        iColumn, iRest = divmod(iColumn - 1, 26)
        sColumn = chr(65 + iRest) + sColumn
    return sColumn


def separatedValue(sValue, sSeparator):
    if sValue:
        try:
            float(sValue); bNumber = True
        except ValueError:
            bNumber = False
        if sValue[0] in "=@\t\r" or (sValue[0] in "+-" and not bNumber): sValue = "'" + sValue
    if sSeparator in sValue or '"' in sValue or "\n" in sValue or "\r" in sValue:
        sValue = '"' + sValue.replace('"', '""') + '"'
    return sValue


def tableWrite(sOut, sTo, lsFields, llRows):
    llRows = [(list(r) + [""] * len(lsFields))[:len(lsFields)] for r in llRows]
    if sTo in ("csv", "tsv"):
        sSep = "," if sTo == "csv" else "\t"
        sText = "".join(sSep.join(separatedValue(v, sSep) for v in r) + "\r\n" for r in [lsFields] + llRows)
        open(sOut, "w", encoding="utf-8-sig", newline="").write(sText)
    elif sTo in ("md", "txt"):
        def mdRow(lsValues): return "|" + "".join(" " + (v or "").replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ") + " |" for v in lsValues) + "\r\n"
        open(sOut, "w", encoding="utf-8-sig", newline="").write(mdRow(lsFields) + mdRow(["---"] * len(lsFields)) + "".join(mdRow(r) for r in llRows))
    elif sTo == "inix":
        import inix
        iWidth = len(str(len(llRows))) if llRows else 1
        lSections = []
        for i, lsRow in enumerate(llRows):
            oSection = inix.Section("Record" + str(i + 1).zfill(iWidth))
            for sField, sValue in zip(lsFields, lsRow):
                if sValue != "": oSection.set(sField, sValue)
            if i < len(llRows) - 1: oSection.lPairs.append(inix.Pair(sRaw=""))
            lSections.append(oSection)
        inix.write(sOut, lSections)
    elif sTo == "xlsx":
        if len(llRows) + 1 > 1048576 or len(lsFields) > 16384: raise ValueError("the table is larger than Excel allows")
        import zipfile
        from xml.sax.saxutils import escape
        lsXml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
        for iRow, lsRow in enumerate([lsFields] + llRows, 1):
            lsXml.append('<row r="%d">' % iRow)
            for iCol, sValue in enumerate(lsRow):
                if sValue == "": continue
                if len(sValue) > 32767: raise ValueError("a value is longer than an Excel cell holds")
                lsXml.append('<c r="%s%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (xlsxColumn(iCol), iRow, escape(sValue)))
            lsXml.append("</row>")
        lsXml.append("</sheetData></worksheet>")
        with zipfile.ZipFile(sOut, "w", zipfile.ZIP_DEFLATED) as oZip:
            oZip.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            oZip.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            oZip.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
            oZip.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            oZip.writestr("xl/worksheets/sheet1.xml", "".join(lsXml))
    elif sTo in ("docx", "epub", "htm", "html", "odt", "rtf"):
        # As Table.cs does (its aViaPandoc): the table as Markdown, then Pandoc to the document.
        sMd = sOut + ".table.md"
        try:
            tableWrite(sMd, "md", lsFields, llRows)
            enginePandoc(sMd, sTo, sOut)
        finally:
            try: os.remove(sMd)
            except OSError: pass
    else:
        raise ValueError("the table engine writes csv, tsv, inix, md, txt, xlsx, and through Pandoc docx, epub, htm, odt and rtf; not " + sTo)


def engineTable(sSource, sTo, sOut):
    lsFields, llRows = tableRead(sSource)
    if not lsFields: raise ValueError("no table was found in " + os.path.basename(sSource))
    tableWrite(sOut, sTo, lsFields, llRows)


# ---------- the Homer web page, as ConversionPage.cs makes it (1.87.1) ----------
#
# 2htm's page form, ported line for line from ConversionPage.cs, so a Python app's pages are
# the same as a C# app's: the base stylesheet, a head with title, language and Dublin Core,
# one H1, main labelled by it, headings moved under it, images inlined or removed. Engines
# page (htm to htm or txt) and json (json to htm or txt), and pageFinish, which convert runs
# on every page another engine made.

sPageCss = "html{font-size:100%}body{font-family:sans-serif;max-width:80ch;margin:1em auto;padding:0 1em;line-height:1.6;color:#000;text-align:left}p{margin:1em 0}h1,h2,h3,h4,h5,h6{line-height:1.3;margin-top:1.5em}a{color:#00529b;text-decoration:underline}a:hover,a:focus{text-decoration:underline;text-decoration-thickness:2px}*:focus{outline:3px solid #00529b;outline-offset:2px}.visually-hidden{position:absolute !important;clip:rect(1px,1px,1px,1px);width:1px;height:1px;overflow:hidden;white-space:nowrap}table{border-collapse:collapse;margin:1em 0}th,td{border:1px solid #595959;padding:.4em .6em;text-align:left;vertical-align:top}th{background:#e8e8e8}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}caption{caption-side:top;font-weight:bold;text-align:left;padding:.25em 0;font-size:1.05em}nav ol{list-style:decimal;padding-left:2em}figure{margin:1em 0}img{max-width:100%;height:auto}aside.slide-notes{border-left:4px solid #595959;padding-left:1em;margin:1em 0}.byline{font-style:italic;color:#333;margin:0 0 1em 0}p.subtitle{font-style:italic;color:#333;margin:0 0 1em 0}pre{background:#f4f4f4;border:1px solid #595959;padding:.5em;overflow-x:auto;font-family:monospace;white-space:pre-wrap;word-break:break-word}code{font-family:monospace;background:#f4f4f4;padding:0 .2em;border:1px solid #d0d0d0}pre code{background:transparent;border:0;padding:0}.json-value{font-family:monospace}.json-value.num{color:#004d00}.json-value.str::before{content:'\"'}.json-value.str::after{content:'\"'}.json-value.null,.json-value.bool{font-style:italic}dl.json-obj{margin-left:1.5em;border-left:2px solid #d0d0d0;padding-left:1em}ol.json-arr{margin-left:1.5em}"
bStripImages = False


def pageEscape(sIn):
    return (sIn or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def pageHtmlToText(sHtml):
    s = re.sub(r"<[^>]+>", "", sHtml)
    return s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")


def pageExtractMeta(sHtml):
    d = {}
    oTitle = re.search(r"<title[^>]*>(?P<t>.*?)</title>", sHtml, re.S | re.I)
    if oTitle and pageHtmlToText(oTitle.group("t")).strip(): d["title"] = pageHtmlToText(oTitle.group("t")).strip()
    oLang = re.search(r"""<html[^>]+lang\s*=\s*['"]?(?P<l>[A-Za-z\-]+)""", sHtml, re.I)
    if oLang: d["language"] = oLang.group("l")
    for oMeta in re.finditer(r"<meta\s+(?P<a>[^>]*)>", sHtml, re.I):
        def attr(sName):
            m = re.search(sName + r"""\s*=\s*(?:"(?P<v>[^"]*)"|'(?P<w>[^']*)'|(?P<x>[^\s>]+))""", oMeta.group("a"), re.I)
            return (m.group("v") or m.group("w") or m.group("x") or "") if m else ""
        sName, sContent = attr("name").lower(), attr("content")
        if not sName or not sContent.strip(): continue
        if sName in ("author", "description", "keywords"): d[sName] = sContent
        for sDc, sKey in (("dc.title", "title"), ("dc.creator", "author"), ("dc.subject", "subject"), ("dc.description", "description"), ("dc.language", "language")):
            if sName == sDc and sKey not in d: d[sKey] = sContent
    return d


def pageDate(sIso):
    return sIso[:sIso.index("T")] if sIso and sIso.find("T") > 0 else sIso


def pageHead(dMeta, sDocTitle=None):
    sLang = dMeta.get("language") or "en"
    sTitle = dMeta.get("title") or "Converted document"
    if dMeta.get("subtitle"): sTitle += ": " + dMeta["subtitle"]
    sDocTitle = sDocTitle or sTitle
    lsOut = ["<!DOCTYPE html>", '<html lang="%s">' % pageEscape(sLang), "<head>", '<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">', '<meta name="generator" content="Homer">',
             "<title>%s</title>" % pageEscape(sTitle)]
    for sKey in ("author", "description", "keywords"):
        if dMeta.get(sKey, "").strip(): lsOut.append('<meta name="%s" content="%s">' % (sKey, pageEscape(dMeta[sKey])))
    for sDc, sKey in (("DC.title", "title"), ("DC.creator", "author"), ("DC.subject", "subject"), ("DC.description", "description"),
                      ("DC.date.created", "created"), ("DC.date.modified", "modified"), ("DC.language", "language")):
        if dMeta.get(sKey, "").strip(): lsOut.append('<meta name="%s" content="%s">' % (sDc, pageEscape(dMeta[sKey])))
    lsOut += ["<style>" + sPageCss + "</style>", "</head>", "<body>", '<h1 id="doc-title">%s</h1>' % pageEscape(sDocTitle)]
    bAuthor, bCreated = bool(dMeta.get("author", "").strip()), bool(dMeta.get("created", "").strip())
    if bAuthor or bCreated:
        sLine = '<p class="byline">'
        if bAuthor: sLine += "By " + pageEscape(dMeta["author"]) + (" \u2014 " if bCreated else "")
        if bCreated: sLine += '<time datetime="%s">%s</time>' % (pageEscape(dMeta["created"]), pageEscape(pageDate(dMeta["created"])))
        lsOut.append(sLine + "</p>")
    for sKey, sLabel in (("subject", "Subject"), ("description", "Description"), ("keywords", "Keywords")):
        if dMeta.get(sKey, "").strip(): lsOut.append("<p>%s: %s.</p>" % (pageEscape(sLabel), pageEscape(dMeta[sKey])))
    if dMeta.get("modified", "").strip():
        lsOut.append('<p>Last modified: <time datetime="%s">%s</time>.</p>' % (pageEscape(dMeta["modified"]), pageEscape(pageDate(dMeta["modified"]))))
    return "\r\n".join(lsOut) + "\r\n"


def pageShiftHeadings(sFragment, iTargetMin):
    lsLevels = [int(m.group(2)) for m in re.finditer(r"<(/?)h([1-6])([^>]*)>", sFragment, re.I)]
    if not lsLevels: return sFragment
    iShift = iTargetMin - min(lsLevels)
    def shift(m): return "<%sh%d%s>" % (m.group(1), min(6, max(iTargetMin, int(m.group(2)) + iShift)), m.group(3))
    return re.sub(r"<(/?)h([1-6])([^>]*)>", shift, sFragment, flags=re.I)


def pageImages(sFragment, sBaseDir):
    import base64, urllib.parse
    dMime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".bmp": "image/bmp", ".svg": "image/svg+xml", ".webp": "image/webp"}
    def one(m):
        sTag = m.group(0)
        if bStripImages: return ""
        oSrc = re.search(r"""\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)')""", sTag, re.I)
        if not oSrc: return ""
        sRel = oSrc.group(1) if oSrc.group(1) is not None else oSrc.group(2)
        if not sRel.strip(): return ""
        if sRel.lower().startswith("data:"): return sTag
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*:", sRel): return ""
        sFull = os.path.join(sBaseDir, urllib.parse.unquote(sRel))
        sMime = dMime.get(os.path.splitext(sFull)[1].lower())
        if not os.path.isfile(sFull) or not sMime: return ""
        sData = "data:%s;base64,%s" % (sMime, base64.b64encode(open(sFull, "rb").read()).decode("ascii"))
        return sTag[:oSrc.start()] + 'src="%s"' % sData + sTag[oSrc.end():]
    return re.sub(r"<img\b[^>]*>", one, sFragment, flags=re.I)


def pageBody(sHtml):
    m = re.search(r"<body[^>]*>(?P<b>.*?)</body>", sHtml, re.S | re.I)
    sBody = m.group("b") if m else sHtml
    for sPattern in (r"<style.*?</style>", r"<script.*?</script>", r"<!--.*?-->"):
        sBody = re.sub(sPattern, "", sBody, flags=re.S | re.I)
    return sBody


def pageBlocksToText(sHtml):
    s = re.sub(r"<figure\b[^>]*>.*?</figure>", "", sHtml, flags=re.S | re.I)
    sBreak = "\ue000"
    s = re.sub(r"<br\s*/?>", sBreak, s, flags=re.I)
    s = re.sub(r"</(p|div|blockquote|pre|section|article|header|footer|nav|aside|figcaption)\s*>", sBreak * 2, s, flags=re.I)
    s = re.sub(r"</(li|dt|dd|tr)\s*>", sBreak, s, flags=re.I)
    s = re.sub(r"</(h[1-6])\s*>", sBreak * 2, s, flags=re.I)
    s = re.sub(r"<(h[1-6])\b[^>]*>", sBreak, s, flags=re.I)
    s = re.sub(r"<li\b[^>]*>", sBreak + "- ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&#39;", "'"), ("&nbsp;", " "),
                 ("&mdash;", "\u2014"), ("&ndash;", "\u2013"), ("&hellip;", "\u2026")):
        s = s.replace(a, b)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))) if 0 < int(m.group(1)) <= 0x10FFFF else m.group(0), s)
    s = re.sub(r"[ \t\r\n\f\v]+", " ", s)
    s = re.sub(sBreak + "+", lambda m: "\n\n" if len(m.group(0)) >= 2 else "\n", s)
    lsOut, bSaw, iBlank = [], False, 0
    for sLine in s.split("\n"):
        t = sLine.strip()
        if not t:
            if bSaw: iBlank += 1
            continue
        if iBlank > 0: lsOut.append("")
        lsOut.append(t); bSaw = True; iBlank = 0
    return "\r\n".join(lsOut) + ("\r\n" if lsOut else "")


def pageHtml(sIn, sOut):
    sRaw = decodeText(open(sIn, "rb").read())
    dMeta = pageExtractMeta(sRaw)
    if not dMeta.get("title", "").strip(): dMeta["title"] = os.path.splitext(os.path.basename(sIn))[0]
    sBody = pageShiftHeadings(pageImages(pageBody(sRaw), os.path.dirname(sIn)), 2)
    open(sOut, "w", encoding="utf-8", newline="").write(pageHead(dMeta) + '<main aria-labelledby="doc-title">\r\n' + sBody + "\r\n</main>\r\n</body>\r\n</html>\r\n")


class JsonObject(list):
    """A JSON object's pairs, in order, told apart from an array."""


def pageJsonValue(v, lsOut):
    if v is None: lsOut.append('<span class="json-value null">null</span>')
    elif isinstance(v, bool): lsOut.append('<span class="json-value bool">%s</span>' % ("true" if v else "false"))
    elif isinstance(v, (int, float)): lsOut.append('<span class="json-value num">%s</span>' % pageEscape(repr(v)))
    elif isinstance(v, str): lsOut.append('<span class="json-value str">%s</span>' % pageEscape(v))
    elif isinstance(v, list) and not isinstance(v, JsonObject):
        if not v: lsOut.append('<span class="json-value">[] <em>(empty array)</em></span>'); return
        lsOut.append('<ol class="json-arr">')
        for x in v: lsOut.append("<li>"); pageJsonValue(x, lsOut); lsOut.append("</li>")
        lsOut.append("</ol>")
    else:
        if not v: lsOut.append('<span class="json-value">{} <em>(empty object)</em></span>'); return
        lsOut.append('<dl class="json-obj">')
        for k, x in v: lsOut.append("<dt>%s:</dt>" % pageEscape(k)); lsOut.append("<dd>"); pageJsonValue(x, lsOut); lsOut.append("</dd>")
        lsOut.append("</dl>")


def engineJson(sSource, sTo, sOut):
    import json
    if sTo == "txt": shutil.copyfile(sSource, sOut); return
    sJson = decodeText(open(sSource, "rb").read())
    dMeta = {"title": os.path.splitext(os.path.basename(sSource))[0]}
    lsOut = []
    try:
        pageJsonValue(json.loads(sJson, object_pairs_hook=JsonObject), lsOut)
        sMain = "\r\n".join(lsOut)
    except ValueError as oError:
        sMain = "<h2>Parse error</h2>\r\n<p>%s</p>\r\n<h2>Raw content</h2>\r\n<pre>%s</pre>" % (pageEscape(str(oError)), pageEscape(sJson))
    open(sOut, "w", encoding="utf-8", newline="").write(pageHead(dMeta) + '<main aria-labelledby="doc-title">\r\n' + sMain + "\r\n</main>\r\n</body>\r\n</html>\r\n")


def enginePage(sSource, sTo, sOut):
    if sTo == "txt": open(sOut, "w", encoding="utf-8-sig", newline="").write(pageBlocksToText(pageBody(decodeText(open(sSource, "rb").read()))))
    else: pageHtml(sSource, sOut)


def pageFinish(sPath):
    """A page another engine made, put in the Homer form in place; the body's first H1 becomes its title first."""
    sWork = sPath + ".homerpage.htm"
    try:
        sHtml = decodeText(open(sPath, "rb").read())
        oH1 = re.search(r"<h1\b[^>]*>(?P<t>.*?)</h1>", sHtml, re.S | re.I)
        if oH1:
            sTitle = re.sub(r"<[^>]+>", "", oH1.group("t")).strip()
            if sTitle:
                import html as htmlLib
                sHtml = sHtml[:oH1.start()] + sHtml[oH1.end():]
                sTag = "<title>" + pageEscape(htmlLib.unescape(sTitle)) + "</title>"
                if re.search(r"<title[^>]*>.*?</title>", sHtml, re.S | re.I): sHtml = re.sub(r"<title[^>]*>.*?</title>", lambda m: sTag, sHtml, count=1, flags=re.S | re.I)
                else: sHtml = re.sub(r"<head[^>]*>", lambda m: m.group(0) + sTag, sHtml, count=1, flags=re.I)
        open(sWork, "w", encoding="utf-8", newline="").write(sHtml)
        pageHtml(sWork, sPath)
    finally:
        try: os.remove(sWork)
        except OSError: pass


# THE SQLITE ENGINE (1.90.0): the same script, word for word, as Conversion.cs's sSqliteScript; the kit's build
# fails if the two ever differ. A table to an SQLite database, or a database to Markdown.
sSqliteScript = r'''import csv, io, os, re, sqlite3, sys
sIn, sOut = sys.argv[1], sys.argv[2]
# A DATABASE IN DBDO'S FORM (kit 1.91.0, the homer-db skill): a plural lower-case table named for the
# file, <singular>_id, added and edited, the data fields, url, notes, tags, look, prime and marked in
# that order, the edited and maps triggers, a unique prime index, and DbDo's lookups, maps and views.
lsTypes = ['BLOB', 'BOOLEAN', 'INTEGER', 'NUMERIC', 'REAL', 'TEXT', 'TEXTLINE', 'TEXTMARKDOWN', 'TEXTMEMO', 'TEXTTIME']
lsKinds = ['affiliated_with', 'located_at', 'member_of', 'part_of', 'related_to']
lsHousekeeping = ['added', 'edited', 'look', 'prime', 'marked']
dIrregular = {'people': 'person', 'children': 'child', 'men': 'man', 'women': 'woman', 'data': 'data'}
def decode(ab):
    for sCodec in ('utf-8-sig', 'cp1252'):
        try: return ab.decode(sCodec)
        except UnicodeDecodeError: pass
    return ab.decode('utf-8', 'replace')
def cell(v):
    return ('' if v is None else str(v)).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')
def snake(s):
    s = re.sub(r'[^0-9a-z]+', '_', re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s.strip()).lower()).strip('_')
    return ('f_' + s) if s[:1].isdigit() else s
def plural(s):
    if s in dIrregular or s.endswith('s') and not s.endswith('ss'): return s
    if s.endswith('y') and s[-2:-1] not in ('a', 'e', 'i', 'o', 'u'): return s[:-1] + 'ies'
    if s.endswith(('x', 'ch', 'sh', 'ss', 'z')): return s + 'es'
    return s + 's'
def singular(s):
    if s in dIrregular: return dIrregular[s]
    if s.endswith('ies'): return s[:-3] + 'y'
    if s.endswith(('ches', 'shes', 'xes', 'sses', 'zes')): return s[:-2]
    if s.endswith('s') and not s.endswith('ss'): return s[:-1]
    return s
def q(s):
    return '"' + s.replace('"', '""') + '"'
def joined(lsFields, sJoin, bSkipBlank):
    if not bSkipBlank: return " || '|' || ".join("coalesce(CAST(%s AS TEXT),'')" % q(s) for s in lsFields)
    return "rtrim(" + " || ".join("iif(%s IS NOT NULL AND length(CAST(%s AS TEXT))>0, CAST(%s AS TEXT) || ' | ', '')" % (q(s), q(s), q(s)) for s in lsFields) + ", ' | ')"
def kind(lsValues):
    lsFilled = [v for v in lsValues if v.strip()]
    if any('\n' in v for v in lsFilled): return 'TEXTMEMO'
    if lsFilled and all(re.match(r'^-?\d{1,15}$', v.strip()) for v in lsFilled): return 'INTEGER'
    if lsFilled and all(re.match(r'^-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$', v.strip()) for v in lsFilled): return 'REAL'
    return 'TEXTLINE'
def standardTable(oDb, sTable, lsData, dTypes, lsLook, bMaps):
    sId = singular(sTable) + '_id'
    lsColumns = [q(sId) + ' INTEGER PRIMARY KEY AUTOINCREMENT', 'added TEXTTIME NOT NULL DEFAULT CURRENT_TIMESTAMP', 'edited TEXTTIME NOT NULL DEFAULT CURRENT_TIMESTAMP']
    lsColumns += [q(s) + ' ' + dTypes.get(s, 'TEXTLINE') for s in lsData]
    lsColumns += ['url TEXTLINE', 'notes TEXTMARKDOWN', 'tags TEXTMEMO']
    lsColumns += ['look TEXT GENERATED ALWAYS AS (%s) STORED' % joined(lsLook, ' | ', True), 'prime TEXT GENERATED ALWAYS AS (%s) STORED' % joined(lsData, '|', False), 'marked INTEGER NOT NULL DEFAULT 0']
    oDb.execute('CREATE TABLE %s (%s)' % (q(sTable), ', '.join(lsColumns)))
    lsWatched = lsData + ['notes', 'tags']
    oDb.execute('CREATE TRIGGER %s AFTER UPDATE OF %s ON %s FOR EACH ROW WHEN %s BEGIN UPDATE %s SET edited = CURRENT_TIMESTAMP WHERE %s = NEW.%s; END'
        % (q('trg_' + sTable + '_edited'), ', '.join(q(s) for s in lsWatched), q(sTable), ' OR '.join('OLD.%s IS NOT NEW.%s' % (q(s), q(s)) for s in lsWatched), q(sTable), q(sId), q(sId)))
    oDb.execute('CREATE UNIQUE INDEX %s ON %s (prime)' % (q('idx_' + sTable + '_prime'), q(sTable)))
    if bMaps:
        oDb.execute("CREATE TRIGGER %s AFTER UPDATE ON %s FOR EACH ROW WHEN OLD.prime IS NOT NEW.prime BEGIN UPDATE maps SET prime1 = NEW.prime WHERE tbl1 = '%s' AND prime1 = OLD.prime; UPDATE maps SET prime2 = NEW.prime WHERE tbl2 = '%s' AND prime2 = OLD.prime; END"
            % (q('trg_' + sTable + '_maps'), q(sTable), sTable, sTable))
        oDb.execute("CREATE TRIGGER %s AFTER DELETE ON %s FOR EACH ROW BEGIN DELETE FROM maps WHERE (tbl1 = '%s' AND prime1 = OLD.prime) OR (tbl2 = '%s' AND prime2 = OLD.prime); END"
            % (q('trg_' + sTable + '_maps_delete'), q(sTable), sTable, sTable))
if open(sIn, 'rb').read(16) != b'SQLite format 3\x00':
    llAll = [r for r in csv.reader(io.StringIO(decode(open(sIn, 'rb').read())))]
    llAll = [r for r in llAll if any(v.strip() for v in r)]
    if not llAll: raise SystemExit('the table is empty')
    sTable = plural(snake(os.path.basename(sOut).split('.')[0]) or 'record')
    if sTable in ('lookups', 'maps', 'views'): sTable = 'user_' + sTable
    lsReserved = lsHousekeeping + [singular(sTable) + '_id']
    lsFields = []
    for i, sField in enumerate(llAll[0]):
        sField = snake(sField) or 'column_%d' % (i + 1)
        if sField in lsReserved: sField += '_value'
        while sField in lsFields: sField += '_'
        lsFields.append(sField)
    iWidth = len(lsFields)
    llRows = [(list(r) + [''] * iWidth)[:iWidth] for r in llAll[1:]]
    lsData = [s for s in lsFields if s not in ('url', 'notes', 'tags')]
    if not lsData: raise SystemExit('the table has no field but url, notes and tags')
    dTypes = {s: kind([r[i] for r in llRows]) for i, s in enumerate(lsFields)}
    if os.path.exists(sOut): os.remove(sOut)
    oDb = sqlite3.connect(sOut)
    oDb.execute('CREATE TABLE lookups (lookup_id INTEGER PRIMARY KEY AUTOINCREMENT, added TEXTTIME NOT NULL DEFAULT CURRENT_TIMESTAMP, edited TEXTTIME NOT NULL DEFAULT CURRENT_TIMESTAMP, '
        'src TEXTLINE, tbl TEXTLINE, fld TEXTLINE, val TEXTLINE, ordinal INTEGER, descrip TEXTMEMO, url TEXTLINE, notes TEXTMARKDOWN, tags TEXTMEMO, '
        "look TEXT GENERATED ALWAYS AS (rtrim(iif(tbl IS NOT NULL AND length(tbl)>0, tbl || ' | ', '') || iif(fld IS NOT NULL AND length(fld)>0, fld || ' | ', '') || iif(val IS NOT NULL AND length(val)>0, val || ' | ', ''), ' | ')) STORED, "
        "prime TEXT GENERATED ALWAYS AS (coalesce(src,'') || '|' || coalesce(tbl,'') || '|' || coalesce(fld,'') || '|' || coalesce(val,'')) STORED, marked INTEGER NOT NULL DEFAULT 0)")
    oDb.execute('CREATE UNIQUE INDEX idx_lookups_prime ON lookups (prime)')
    oDb.execute('CREATE TABLE maps (map_id INTEGER PRIMARY KEY AUTOINCREMENT, added TEXTTIME NOT NULL DEFAULT CURRENT_TIMESTAMP, edited TEXTTIME NOT NULL DEFAULT CURRENT_TIMESTAMP, '
        'tbl1 TEXTLINE, prime1 TEXTLINE, kind TEXTLINE, tbl2 TEXTLINE, prime2 TEXTLINE, notes TEXTMARKDOWN, tags TEXTMEMO, '
        "look TEXT GENERATED ALWAYS AS (coalesce(tbl1,'') || ' ' || coalesce(prime1,'') || ' | ' || coalesce(kind,'') || ' | ' || coalesce(tbl2,'') || ' ' || coalesce(prime2,'')) STORED, "
        "prime TEXT GENERATED ALWAYS AS (coalesce(tbl1,'') || '|' || coalesce(prime1,'') || '|' || coalesce(kind,'') || '|' || coalesce(tbl2,'') || '|' || coalesce(prime2,'')) STORED, marked INTEGER NOT NULL DEFAULT 0)")
    oDb.execute('CREATE UNIQUE INDEX idx_maps_prime ON maps (prime)')
    oDb.execute('CREATE INDEX idx_maps_1 ON maps (tbl1, prime1)')
    oDb.execute('CREATE INDEX idx_maps_2 ON maps (tbl2, prime2)')
    oDb.execute('CREATE TABLE views (tbl TEXTLINE NOT NULL, fld TEXTLINE NOT NULL, val TEXTLINE, PRIMARY KEY (tbl, fld))')
    for sOwn, sOwnId, lsOwn in (('lookups', 'lookup_id', ['src', 'tbl', 'fld', 'val', 'ordinal', 'descrip', 'url', 'notes', 'tags']), ('maps', 'map_id', ['tbl1', 'prime1', 'kind', 'tbl2', 'prime2', 'notes', 'tags'])):
        oDb.execute('CREATE TRIGGER %s AFTER UPDATE OF %s ON %s FOR EACH ROW WHEN %s BEGIN UPDATE %s SET edited = CURRENT_TIMESTAMP WHERE %s = NEW.%s; END'
            % (q('trg_' + sOwn + '_edited'), ', '.join(lsOwn), sOwn, ' OR '.join('OLD.%s IS NOT NEW.%s' % (s, s) for s in lsOwn), sOwn, sOwnId, sOwnId))
    lsSeeds = [('DbDo', '*', 'type', s) for s in lsTypes] + [('DbDo', 'maps', 'kind', s) for s in lsKinds]
    for sTbl, sFld in sorted(set((t, f) for _, t, f, _ in lsSeeds)):
        lsVals = sorted(v for _, t, f, v in lsSeeds if t == sTbl and f == sFld)
        oDb.executemany('INSERT INTO lookups (src, tbl, fld, val, ordinal) VALUES (?, ?, ?, ?, ?)', [('DbDo', sTbl, sFld, v, i + 1) for i, v in enumerate(lsVals)])
    standardTable(oDb, sTable, lsData, dTypes, lsData[:3], True)
    iSkipped = 0
    for r in llRows:
        dRow = dict(zip(lsFields, r))
        lsCols = lsData + [s for s in ('url', 'notes', 'tags') if s in lsFields]
        lsVals = [None if not dRow[s].strip() else (int(dRow[s]) if dTypes[s] == 'INTEGER' else float(dRow[s]) if dTypes[s] == 'REAL' else dRow[s]) for s in lsCols]
        oCur = oDb.execute('INSERT OR IGNORE INTO %s (%s) VALUES (%s)' % (q(sTable), ', '.join(q(s) for s in lsCols), ', '.join('?' * len(lsCols))), lsVals)
        if oCur.rowcount == 0: iSkipped += 1
    oDb.commit()
    oDb.close()
    print('%s: %d %s in table %s%s' % (os.path.basename(sOut), len(llRows) - iSkipped, 'record' if len(llRows) - iSkipped == 1 else 'records', sTable,
        '; %d duplicate %s left out' % (iSkipped, 'row' if iSkipped == 1 else 'rows') if iSkipped else ''))
else:
    oDb = sqlite3.connect('file:' + os.path.abspath(sIn).replace('\\', '/') + '?mode=ro', uri=True)
    lsOut = ['# ' + os.path.splitext(os.path.basename(sIn))[0], '']
    for (sTable,) in oDb.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name COLLATE NOCASE"):
        # DbDo's own tables are kept off every list, as DbDo keeps them.
        if sTable in ('lookups', 'maps', 'views'): continue
        oCursor = oDb.execute('SELECT * FROM %s' % q(sTable))
        lsFields = [d[0] for d in oCursor.description]
        llRows = oCursor.fetchall()
        # A DbDo table gives its data: not its id, its times, look, prime or marked, nor url, notes or tags left empty.
        bDbDo = 'prime' in lsFields and 'look' in lsFields
        lsKeep = [i for i, s in enumerate(lsFields) if not bDbDo or (s not in lsHousekeeping and s != singular(sTable) + '_id'
            and not (s in ('url', 'notes', 'tags') and not any(r[i] not in (None, '') for r in llRows)))]
        lsOut += ['## ' + sTable, '', '| ' + ' | '.join(cell(lsFields[i]) for i in lsKeep) + ' |', '|' + ' --- |' * len(lsKeep)]
        lsOut += ['| ' + ' | '.join(cell(r[i]) for i in lsKeep) + ' |' for r in llRows]
        lsOut.append('')
    oDb.close()
    open(sOut, 'w', encoding='utf-8-sig', newline='\r\n').write('\n'.join(lsOut))
'''


# THE RECORDS ENGINE (1.93.0): the same script, word for word, as Conversion.cs's sRecordsScript; the kit's build fails if
# the two ever differ. Contact cards, calendars, playlists, feed lists and subtitles to and from a table.
sRecordsScript = r'''import csv, datetime, io, os, re, sys, uuid
import xml.etree.ElementTree as ET
sIn, sOut = sys.argv[1], sys.argv[2]
sOutType = os.path.splitext(sOut[:-5] if sOut.lower().endswith('.part') else sOut)[1].lstrip('.').lower()
sInType = os.path.splitext(sIn)[1].lstrip('.').lower()
dColumns = {'vcf': ['Name', 'Given', 'Family', 'Organization', 'Title', 'Email', 'Phone', 'Mobile', 'Address', 'Web', 'Birthday', 'Note'],
            'ics': ['Summary', 'Start', 'End', 'Location', 'Description', 'Web', 'Organizer', 'Repeats', 'Id'],
            'playlist': ['Title', 'Location', 'Seconds'],
            'opml': ['Title', 'Feed', 'Site', 'Group'],
            'subtitles': ['Start', 'End', 'Text']}
dKind = {'vcf': 'vcf', 'ics': 'ics', 'vcs': 'ics', 'm3u': 'playlist', 'm3u8': 'playlist', 'pls': 'playlist', 'xspf': 'playlist',
         'wpl': 'playlist', 'asx': 'playlist', 'opml': 'opml', 'srt': 'subtitles', 'vtt': 'subtitles'}
dAliases = {'name': 'Name', 'full name': 'Name', 'fn': 'Name', 'display name': 'Name', 'first name': 'Given', 'given name': 'Given',
            'last name': 'Family', 'surname': 'Family', 'family name': 'Family', 'company': 'Organization', 'org': 'Organization',
            'job title': 'Title', 'e-mail': 'Email', 'email address': 'Email', 'telephone': 'Phone', 'phone number': 'Phone',
            'cell': 'Mobile', 'mobile phone': 'Mobile', 'url': 'Web', 'website': 'Web', 'link': 'Web', 'notes': 'Note',
            'subject': 'Summary', 'event': 'Summary', 'starts': 'Start', 'begin': 'Start', 'ends': 'End', 'finish': 'End',
            'where': 'Location', 'details': 'Description', 'rrule': 'Repeats', 'uid': 'Id', 'file': 'Location', 'path': 'Location',
            'duration': 'Seconds', 'length': 'Seconds', 'xmlurl': 'Feed', 'feed url': 'Feed', 'htmlurl': 'Site', 'category': 'Group',
            'from': 'Start', 'to': 'End', 'caption': 'Text', 'line': 'Text'}
def base(s):
    return re.split(r'[\\/]', s.rstrip('/\\'))[-1] or s
def seconds(n):
    return str(int(n)) if float(n) == int(float(n)) else str(n)
def decode(ab):
    for sCodec in ('utf-8-sig', 'cp1252'):
        try: return ab.decode(sCodec)
        except UnicodeDecodeError: pass
    return ab.decode('utf-8', 'replace')
def unfold(sText):
    # vCard and iCalendar fold long lines: a line starting with a space or tab continues the one before.
    return re.sub(r'\r?\n[ \t]', '', sText.replace('\r\n', '\n'))
def unescape(s):
    return re.sub(r'\\([nN,;\\])', lambda m: '\n' if m.group(1) in 'nN' else m.group(1), s)
def escape(s):
    return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\r\n', '\n').replace('\n', '\\n')
def fold(sLine):
    lParts = []
    while len(sLine.encode('utf-8')) > 75:
        i = 75
        while len(sLine[:i].encode('utf-8')) > 75: i -= 1
        lParts.append(sLine[:i]); sLine = ' ' + sLine[i:]
    lParts.append(sLine)
    return '\r\n'.join(lParts)
def properties(sBlock):
    """[(name, params, value)] for each line of one BEGIN/END block."""
    lOut = []
    for sLine in sBlock.split('\n'):
        oLine = re.match(r'^([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)?)((?:;[^:]*)?):(.*)$', sLine)
        if not oLine: continue
        sName = oLine.group(1).split('.')[-1].upper()
        lOut.append((sName, oLine.group(2), oLine.group(3)))
    return lOut
def icsTime(sValue, sParams):
    """2026-10-24 19:00, with Z kept as UTC and a TZID named; a date alone stays a date."""
    o = re.match(r'^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z)?)?$', sValue.strip())
    if not o: return sValue.strip()
    s = '%s-%s-%s' % o.group(1, 2, 3)
    if o.group(4): s += ' %s:%s' % (o.group(4), o.group(5)) + (' UTC' if o.group(7) else '')
    oZone = re.search(r'(?i)TZID=([^;:]+)', sParams)
    if oZone and o.group(4) and not o.group(7): s += ' ' + oZone.group(1)
    return s
def icsValue(sText, bEnd=False):
    """An iCalendar date or time from 2026-10-24 or 2026-10-24 19:00 [UTC]; the property's parameters with it."""
    o = re.match(r'^\s*(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2})(?::\d{2})?\s*(UTC|Z|[A-Za-z_]+(?:/[A-Za-z_+-]+)+)?)?\s*$', sText or '')
    if not o: return '', ''
    sDate = '%s%s%s' % o.group(1, 2, 3)
    if not o.group(4): return ';VALUE=DATE', sDate
    sTime = sDate + 'T%02d%s00' % (int(o.group(4)), o.group(5))
    if o.group(6) in ('UTC', 'Z'): return '', sTime + 'Z'
    return (';TZID=' + o.group(6) if o.group(6) else ''), sTime
def readRecords():
    sText = decode(open(sIn, 'rb').read())
    sKind = dKind[sInType]
    lRows = []
    if sKind == 'vcf':
        for sCard in re.findall(r'(?ims)^BEGIN:VCARD\s*$(.*?)^END:VCARD\s*$', unfold(sText)):
            d = {c: '' for c in dColumns['vcf']}
            lEmails, lPhones = [], []
            for sName, sParams, sValue in properties(sCard):
                sValue = unescape(sValue)
                if sName == 'FN': d['Name'] = sValue
                elif sName == 'N':
                    lN = (sValue.split(';') + [''] * 5)[:5]
                    d['Family'], d['Given'] = lN[0], lN[1]
                elif sName == 'ORG': d['Organization'] = sValue.replace(';', ', ').strip(', ')
                elif sName == 'TITLE': d['Title'] = sValue
                elif sName == 'EMAIL': lEmails.append(sValue)
                elif sName == 'TEL':
                    if re.search(r'(?i)CELL|MOBILE', sParams) and not d['Mobile']: d['Mobile'] = sValue
                    else: lPhones.append(sValue)
                elif sName == 'ADR': d['Address'] = ', '.join(p for p in sValue.split(';') if p.strip())
                elif sName == 'URL': d['Web'] = sValue
                elif sName == 'BDAY': d['Birthday'] = icsTime(sValue.replace('-', ''), '') if re.match(r'^\d{4}-?\d{2}-?\d{2}$', sValue) else sValue
                elif sName == 'NOTE': d['Note'] = sValue
            d['Email'], d['Phone'] = '; '.join(lEmails), '; '.join(lPhones)
            if not d['Name']: d['Name'] = (d['Given'] + ' ' + d['Family']).strip() or d['Organization']
            lRows.append(d)
    elif sKind == 'ics':
        for sEvent in re.findall(r'(?ims)^BEGIN:VEVENT\s*$(.*?)^END:VEVENT\s*$', unfold(sText)):
            d = {c: '' for c in dColumns['ics']}
            for sName, sParams, sValue in properties(sEvent):
                if sName == 'SUMMARY': d['Summary'] = unescape(sValue)
                elif sName == 'DTSTART': d['Start'] = icsTime(sValue, sParams)
                elif sName == 'DTEND': d['End'] = icsTime(sValue, sParams)
                elif sName == 'LOCATION': d['Location'] = unescape(sValue)
                elif sName == 'DESCRIPTION': d['Description'] = unescape(sValue)
                elif sName == 'URL': d['Web'] = sValue
                elif sName == 'ORGANIZER': d['Organizer'] = re.sub(r'(?i)^mailto:', '', sValue)
                elif sName == 'RRULE': d['Repeats'] = sValue
                elif sName == 'UID': d['Id'] = sValue
            lRows.append(d)
    elif sKind == 'playlist':
        if sInType in ('m3u', 'm3u8'):
            # A .m3u8 is either a playlist or an HLS stream manifest, which share a first line (from QUILL's
            # playlist_formats.py): segment and stream tags mean a manifest, whose entries are seconds of one stream.
            if re.search(r'(?m)^#EXT-X-(?:TARGETDURATION|MEDIA-SEQUENCE|STREAM-INF|ENDLIST)', sText): raise SystemExit('this .m3u8 is a streaming manifest, not a playlist')
            sTitle, sSeconds = '', ''
            for sLine in sText.replace('\r\n', '\n').split('\n'):
                sLine = sLine.strip()
                oInf = re.match(r'^#EXTINF:\s*(-?[\d.]+)[^,]*,(.*)$', sLine)
                if oInf: sSeconds, sTitle = oInf.group(1), oInf.group(2).strip(); continue
                if not sLine or sLine.startswith('#'): continue
                lRows.append({'Title': sTitle or base(sLine), 'Location': sLine, 'Seconds': '' if sSeconds in ('', '-1') else sSeconds})
                sTitle, sSeconds = '', ''
        elif sInType == 'pls':
            dEntries = {}
            for oLine in re.finditer(r'(?im)^(File|Title|Length)(\d+)\s*=\s*(.*)$', sText):
                dEntries.setdefault(int(oLine.group(2)), {})[oLine.group(1).lower()] = oLine.group(3).strip()
            for i in sorted(dEntries):
                d = dEntries[i]
                if d.get('file'): lRows.append({'Title': d.get('title', '') or base(d['file']), 'Location': d['file'], 'Seconds': '' if d.get('length', '') in ('', '-1') else d['length']})
        else:
            oRoot = ET.fromstring(re.sub(r'(?is)<!DOCTYPE[^>]*>', '', sText).encode('utf-8'))
            def local(e): return e.tag.split('}')[-1].lower()
            for oItem in oRoot.iter():
                sTag = local(oItem)
                if sTag == 'track':
                    d = {local(c): (c.text or '').strip() for c in oItem}
                    if d.get('location'): lRows.append({'Title': d.get('title', '') or base(d['location']), 'Location': d['location'], 'Seconds': seconds(int(d['duration']) / 1000) if d.get('duration', '').isdigit() else ''})
                elif sTag == 'media' and oItem.get('src'): lRows.append({'Title': base(oItem.get('src')), 'Location': oItem.get('src'), 'Seconds': ''})
                elif sTag == 'entry':
                    sRef = next((c.get('href') or c.get('HREF') for c in oItem if local(c) == 'ref'), '')
                    sName = next(((c.text or '').strip() for c in oItem if local(c) == 'title'), '')
                    if sRef: lRows.append({'Title': sName or base(sRef), 'Location': sRef, 'Seconds': ''})
    elif sKind == 'opml':
        oRoot = ET.fromstring(re.sub(r'(?is)<!DOCTYPE[^>]*>', '', sText).encode('utf-8'))
        def walk(oNode, sGroup):
            for oChild in oNode:
                if oChild.tag.split('}')[-1].lower() != 'outline': continue
                sName = oChild.get('title') or oChild.get('text') or ''
                if oChild.get('xmlUrl'): lRows.append({'Title': sName, 'Feed': oChild.get('xmlUrl', ''), 'Site': oChild.get('htmlUrl', ''), 'Group': sGroup})
                walk(oChild, sName if not oChild.get('xmlUrl') else sGroup)
        oBody = next((e for e in oRoot if e.tag.split('}')[-1].lower() == 'body'), oRoot)
        walk(oBody, '')
    elif sKind == 'subtitles':
        sBody = re.sub(r'(?s)^\ufeff?WEBVTT[^\n]*\n', '', sText.replace('\r\n', '\n'))
        for sCue in re.split(r'\n\s*\n', sBody):
            oTimes = re.search(r'(\d{1,2}:)?(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{1,2}:)?(\d{2}):(\d{2})[,.](\d{3})', sCue)
            if not oTimes: continue
            def stamp(lGroups): return '%02d:%s:%s.%s' % (int((lGroups[0] or '0:')[:-1]), lGroups[1], lGroups[2], lGroups[3])
            lText = [s for s in sCue.split('\n')[sCue.split('\n').index(next(l for l in sCue.split('\n') if '-->' in l)) + 1:] if s.strip()]
            lRows.append({'Start': stamp(oTimes.groups()[:4]), 'End': stamp(oTimes.groups()[4:]), 'Text': re.sub(r'<[^>]+>', '', ' '.join(lText)).strip()})
    return dColumns[sKind], lRows
def readTable():
    lAll = [r for r in csv.reader(io.StringIO(decode(open(sIn, 'rb').read()))) if any(c.strip() for c in r)]
    if not lAll: raise SystemExit('the table is empty')
    lHeads = [dAliases.get(h.strip().lower(), h.strip()) for h in lAll[0]]
    lKnown = {c.lower(): c for l in dColumns.values() for c in l}
    lHeads = [lKnown.get(h.lower(), h) for h in lHeads]
    return [dict(zip(lHeads, (r + [''] * len(lHeads))[:len(lHeads)])) for r in lAll[1:]]
def writeRecords(lRows):
    sKind = dKind[sOutType]
    lOut = []
    sStamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if sKind == 'vcf':
        for d in lRows:
            sName = d.get('Name', '') or (d.get('Given', '') + ' ' + d.get('Family', '')).strip() or d.get('Organization', '')
            if not sName: continue
            lCard = ['BEGIN:VCARD', 'VERSION:3.0', 'FN:' + escape(sName), 'N:' + escape(d.get('Family', '')) + ';' + escape(d.get('Given', '')) + ';;;']
            if d.get('Organization'): lCard.append('ORG:' + escape(d['Organization']))
            if d.get('Title'): lCard.append('TITLE:' + escape(d['Title']))
            lCard += ['EMAIL;TYPE=INTERNET:' + s.strip() for s in d.get('Email', '').split(';') if s.strip()]
            lCard += ['TEL;TYPE=VOICE:' + s.strip() for s in d.get('Phone', '').split(';') if s.strip()]
            if d.get('Mobile'): lCard.append('TEL;TYPE=CELL:' + d['Mobile'].strip())
            if d.get('Address'): lCard.append('ADR;TYPE=HOME:;;' + escape(d['Address']) + ';;;;')
            if d.get('Web'): lCard.append('URL:' + d['Web'].strip())
            if d.get('Birthday'): lCard.append('BDAY:' + d['Birthday'].strip())
            if d.get('Note'): lCard.append('NOTE:' + escape(d['Note']))
            lOut += [fold(s) for s in lCard + ['END:VCARD']]
    elif sKind == 'ics':
        lOut = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Homer Tools//HomerDev conversion//EN', 'CALSCALE:GREGORIAN']
        for d in lRows:
            sStartParams, sStart = icsValue(d.get('Start', ''))
            if not sStart: continue
            lEvent = ['BEGIN:VEVENT', 'UID:' + (d.get('Id', '').strip() or str(uuid.uuid4()) + '@homer'), 'DTSTAMP:' + sStamp, 'DTSTART' + sStartParams + ':' + sStart]
            sEndParams, sEnd = icsValue(d.get('End', ''))
            if sEnd: lEvent.append('DTEND' + sEndParams + ':' + sEnd)
            lEvent.append('SUMMARY:' + escape(d.get('Summary', '') or '(no title)'))
            if d.get('Location'): lEvent.append('LOCATION:' + escape(d['Location']))
            if d.get('Description'): lEvent.append('DESCRIPTION:' + escape(d['Description']))
            if d.get('Web'): lEvent.append('URL:' + d['Web'].strip())
            if d.get('Organizer'): lEvent.append('ORGANIZER:mailto:' + d['Organizer'].strip())
            if d.get('Repeats'): lEvent.append('RRULE:' + d['Repeats'].strip())
            lOut += [fold(s) for s in lEvent + ['END:VEVENT']]
        lOut.append('END:VCALENDAR')
    elif sKind == 'playlist':
        lEntries = [d for d in lRows if d.get('Location', '').strip()]
        if sOutType in ('m3u', 'm3u8'):
            lOut = ['#EXTM3U']
            for d in lEntries: lOut += ['#EXTINF:%s,%s' % (int(float(d['Seconds'])) if re.match(r'^[\d.]+$', d.get('Seconds', '')) else -1, d.get('Title', '')), d['Location']]
        elif sOutType == 'pls':
            lOut = ['[playlist]']
            for i, d in enumerate(lEntries, 1):
                lOut += ['File%d=%s' % (i, d['Location']), 'Title%d=%s' % (i, d.get('Title', '')), 'Length%d=%s' % (i, int(float(d['Seconds'])) if re.match(r'^[\d.]+$', d.get('Seconds', '')) else -1)]
            lOut += ['NumberOfEntries=%d' % len(lEntries), 'Version=2']
        else:
            oList = ET.Element('playlist', {'version': '1', 'xmlns': 'http://xspf.org/ns/0/'}); oTracks = ET.SubElement(oList, 'trackList')
            for d in lEntries:
                oTrack = ET.SubElement(oTracks, 'track'); ET.SubElement(oTrack, 'location').text = d['Location']
                if d.get('Title'): ET.SubElement(oTrack, 'title').text = d['Title']
                if re.match(r'^[\d.]+$', d.get('Seconds', '')): ET.SubElement(oTrack, 'duration').text = str(int(float(d['Seconds']) * 1000))
            lOut = ['<?xml version="1.0" encoding="UTF-8"?>', ET.tostring(oList, encoding='unicode')]
    elif sKind == 'opml':
        oOpml = ET.Element('opml', {'version': '2.0'}); ET.SubElement(ET.SubElement(oOpml, 'head'), 'title').text = re.sub(r'\.homer-staging(-\d+)?$', '', os.path.splitext(os.path.basename(sOut[:-5] if sOut.lower().endswith('.part') else sOut))[0])
        oBody = ET.SubElement(oOpml, 'body'); dGroups = {}
        for d in lRows:
            if not d.get('Feed', '').strip(): continue
            oParent = oBody
            if d.get('Group'):
                if d['Group'] not in dGroups: dGroups[d['Group']] = ET.SubElement(oBody, 'outline', {'text': d['Group'], 'title': d['Group']})
                oParent = dGroups[d['Group']]
            ET.SubElement(oParent, 'outline', {'type': 'rss', 'text': d.get('Title', ''), 'title': d.get('Title', ''), 'xmlUrl': d['Feed'], 'htmlUrl': d.get('Site', '')})
        lOut = ['<?xml version="1.0" encoding="UTF-8"?>', ET.tostring(oOpml, encoding='unicode')]
    elif sKind == 'subtitles':
        def stamp(s, sMark):
            o = re.match(r'^(?:(\d{1,2}):)?(\d{2}):(\d{2})(?:[.,](\d{1,3}))?$', s.strip())
            return '%02d:%s:%s%s%s' % (int(o.group(1) or 0), o.group(2), o.group(3), sMark, (o.group(4) or '0').ljust(3, '0')) if o else ''
        lCues = [d for d in lRows if stamp(d.get('Start', ''), ',') and stamp(d.get('End', ''), ',')]
        lOut = ['WEBVTT', ''] if sOutType == 'vtt' else []
        sMark = '.' if sOutType == 'vtt' else ','
        for i, d in enumerate(lCues, 1):
            lOut += ([str(i)] if sOutType == 'srt' else []) + [stamp(d['Start'], sMark) + ' --> ' + stamp(d['End'], sMark), d.get('Text', ''), '']
    return lOut
if sOutType == 'csv':
    if sInType not in dKind: raise SystemExit('records cannot read .' + sInType)
    lHeads, lRows = readRecords()
    oBuffer = io.StringIO(); oWriter = csv.writer(oBuffer, lineterminator='\r\n'); oWriter.writerow(lHeads)
    for d in lRows: oWriter.writerow([d.get(h, '') for h in lHeads])
    open(sOut, 'w', encoding='utf-8-sig', newline='').write(oBuffer.getvalue())
    print('%d %s' % (len(lRows), 'record' if len(lRows) == 1 else 'records'))
else:
    if sOutType not in dKind: raise SystemExit('records cannot write .' + sOutType)
    lOut = writeRecords(readTable())
    open(sOut, 'w', encoding='utf-8', newline='').write('\r\n'.join(lOut) + '\r\n')
'''


def engineRecords(sSource, sTo, sOut):
    """Run sRecordsScript, as Conversion.cs does, with the Python running this module."""
    sScript = os.path.join(tempfile.mkdtemp(prefix="homerRecords-"), "records.py")
    try:
        open(sScript, "w", encoding="utf-8").write(sRecordsScript)
        run([sys.executable, sScript, sSource, sOut], "records")
    finally:
        shutil.rmtree(os.path.dirname(sScript), ignore_errors=True)


def engineSqlite(sSource, sTo, sOut):
    """Run sSqliteScript, as Conversion.cs does, with the Python running this module."""
    sScript = os.path.join(tempfile.mkdtemp(prefix="homerSqlite-"), "sqlite.py")
    try:
        open(sScript, "w", encoding="utf-8").write(sSqliteScript)
        run([sys.executable, sScript, sSource, sOut], "SQLite")
    finally:
        shutil.rmtree(os.path.dirname(sScript), ignore_errors=True)


def engineEdge(sSource, sTo, sOut):
    """A PDF from a web page by Microsoft Edge (1.90.0), as Conversion.cs's edge engine: headless, a fresh
    profile of its own so it never joins the person's open Edge, no header or footer, a tagged PDF with an
    outline where Edge makes one."""
    if typeOf(sSource) != "htm": raise ValueError("Edge prints only a web page to PDF")
    sEdge = programFor("edge")
    if not sEdge: raise RuntimeError("Microsoft Edge is not installed")
    sProfile = tempfile.mkdtemp(prefix="HomerEdgePdf_")
    sTarget = os.path.abspath(sOut)
    try:
        if os.path.exists(sTarget): os.remove(sTarget)
        sUrl = pathlib.Path(os.path.abspath(sSource)).as_uri()
        lsCommand = [sEdge, "--headless", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                     "--user-data-dir=" + sProfile, "--no-pdf-header-footer", "--generate-pdf-document-outline", "--export-tagged-pdf",
                     "--print-to-pdf=" + sTarget, sUrl]
        try: run(lsCommand, "Edge")
        except Exception as oError: say("Edge reported a problem: %s" % oError)
        if not os.path.isfile(sTarget) or os.path.getsize(sTarget) < 5: raise RuntimeError("Edge wrote no PDF")
        with open(sTarget, "rb") as oIn:
            if oIn.read(4) != b"%PDF": raise RuntimeError("Edge wrote something that is not a PDF")
    finally:
        shutil.rmtree(sProfile, ignore_errors=True)


dEngines = {"copy": engineCopy, "edge": engineEdge, "records": engineRecords, "sqlite": engineSqlite, "markdown": engineMarkdown, "ocr": engineOcr, "officecom": engineOfficeCom,
              "json": engineJson, "page": enginePage, "pandoc": enginePandoc, "table": engineTable, "pdfstructure": enginePdfStructure, "pdftext": enginePdfText, "zipxml": engineZipXml}


# ---------- converting ----------

# ---------- the media half, as ConversionMedia.cs does it (1.86.0) ----------
#
# PYTHON CONVERTS MEDIA AS C# DOES, with the same tools called the same way:
#   audio or video -> a document: ffmpeg takes the sound as 16 kHz mono WAV, Whisper transcribes
#     it (whisper-cli -m <model> -f <wav> -nt -np -l auto), and the transcript, as Markdown, goes
#     to the target through the route table. A video goes first to HomerScribe, when installed,
#     for what is said and what can be seen; without it, the transcript alone.
#   a document -> audio: its text spoken by Windows' own speech synthesis, through PowerShell,
#     encoded by ffmpeg; -> video: the same speech over a plain black picture.
#   audio or video -> audio or video: ffmpeg.

lsAudioSources = ["aac", "aif", "aiff", "flac", "m4a", "mp3", "ogg", "opus", "wav", "wma"]
lsVideoSources = ["3gp", "avi", "flv", "m2ts", "m4v", "mkv", "mov", "mp4", "mpeg", "mpg", "ogv", "ts", "webm", "wmv"]
lsTranscriptTargets = ["doc", "docx", "epub", "htm", "md", "odt", "pdf", "rtf", "txt"]
lsSpeechAudioTargets = ["flac", "m4a", "mp3", "ogg", "opus", "wav"]
lsSpeechVideoTargets = ["mkv", "mov", "mp4", "webm"]
lsWhisperModels = ["ggml-small.bin", "ggml-small.en.bin", "ggml-base.bin", "ggml-base.en.bin", "ggml-medium.bin", "ggml-large-v3-turbo.bin"]


def mediaCategory(sPath):
    sType = typeOf(sPath)
    return "audio" if sType in lsAudioSources else ("video" if sType in lsVideoSources else "")


def ffmpegProgram():
    try:
        import media
        return media.findInstalled("ffmpeg") or ""
    except Exception:
        return shutil.which("ffmpeg") or ""


def whisperProgram():
    sPath = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Whisper", "whisper-cli.exe")
    return sPath if os.path.isfile(sPath) else (shutil.which("whisper-cli") or "")


def whisperModel():
    sProgram = whisperProgram()
    if not sProgram: return ""
    sDir = os.path.dirname(sProgram)
    for sName in lsWhisperModels:
        if os.path.isfile(os.path.join(sDir, sName)): return os.path.join(sDir, sName)
    for sPath in sorted(glob.glob(os.path.join(sDir, "ggml-*.bin"))):
        if "silero" not in os.path.basename(sPath).lower(): return sPath
    return ""


def homerProgram(sApp):
    """Another Homer app's program, as Paths.homerProgram finds it; "" when it is not installed."""
    for sRoot in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        if not sRoot: continue
        for sTry in (os.path.join(sRoot, sApp, "exec", sApp + ".exe"), os.path.join(sRoot, sApp, sApp + ".exe")):
            if os.path.isfile(sTry): return sTry
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths" + "\\" + sApp + ".exe") as oKey:
            sValue = winreg.QueryValue(oKey, None).strip('"')
            if os.path.isfile(sValue): return sValue
    except Exception:
        pass
    return ""


def runTool(lsCommand, sWhat, iMinutes):
    try: oDone = subprocess.run(lsCommand, capture_output=True, text=True, errors="replace", timeout=iMinutes * 60, creationflags=iNoWindow)
    except FileNotFoundError: raise RuntimeError("%s could not be started: %s was not found" % (sWhat, os.path.basename(lsCommand[0])))
    except subprocess.TimeoutExpired: raise RuntimeError("%s took longer than %d minutes and was stopped" % (sWhat, iMinutes))
    if oDone.returncode != 0: raise RuntimeError("%s failed (exit code %d): %s" % (sWhat, oDone.returncode, (oDone.stderr or oDone.stdout).strip()[-300:]))
    return oDone.stdout


def textCanBeSpoken(sSource):
    sType = typeOf(sSource)
    if sType in ("txt", "md"): return True
    dTable = loadTable()
    return bool(dTable.get(sType, {}).get("txt") or dTable.get(sType, {}).get("md"))


def mediaCan(sSource, sTo):
    sCategory = mediaCategory(sSource)
    if sCategory and sTo in lsTranscriptTargets: return True
    if sCategory and sTo in lsAudioSources + lsVideoSources: return sCategory == "video" or sTo in lsAudioSources
    if not sCategory and sTo in lsSpeechAudioTargets + lsSpeechVideoTargets: return textCanBeSpoken(sSource)
    return False


def transcribeTo(sSource, sOut, sTo, sDir):
    sFfmpeg = ffmpegProgram()
    if not sFfmpeg: raise RuntimeError("ffmpeg is not installed, and it is what takes the sound out for Whisper")
    sProgram, sModel = whisperProgram(), whisperModel()
    if not sProgram: raise RuntimeError("Whisper is not installed; HomerDev's setup program offers it")
    if not sModel: raise RuntimeError("Whisper has no speech model; run HomerDev's setup program again and leave Whisper ticked")
    sWav = os.path.join(sDir, "sound.wav")
    runTool([sFfmpeg, "-nostdin", "-y", "-i", sSource, "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", sWav], "ffmpeg", 120)
    sText = runTool([sProgram, "-m", sModel, "-f", sWav, "-nt", "-np", "-l", "auto"], "Whisper", 360).strip()
    if not sText: raise RuntimeError("Whisper heard no words")
    lsSentences = re.split(r"(?<=[.!?])\s+", sText)
    sMd = "# Transcript of %s\r\n\r\n" % os.path.splitext(os.path.basename(sSource))[0]
    sMd += "".join(" ".join(lsSentences[i:i + 5]) + "\r\n\r\n" for i in range(0, len(lsSentences), 5))
    return finishFromMarkdown(sMd, sOut, sTo, sDir)


def describeVideoTo(sSource, sOut, sTo, sDir):
    sScribe = homerProgram("HomerScribe")
    if not sScribe: raise RuntimeError("HomerScribe is not installed")
    sResults = os.path.join(sDir, "scribe")
    os.makedirs(sResults, exist_ok=True)
    try: runTool([sScribe, sSource, "--describe", "--transcribe", "--output-dir", sResults], "HomerScribe", 600)
    except RuntimeError: pass
    sFolder = os.path.join(sResults, os.path.splitext(os.path.basename(sSource))[0])
    sDescribed, sTranscribed = os.path.join(sFolder, "described.md"), os.path.join(sFolder, "transcribed.md")
    if not os.path.isfile(sDescribed): raise RuntimeError("HomerScribe made no description")
    def demoted(sText): return re.sub(r"(?m)^(#{1,4})(\s)", r"##\1\2", sText.replace("\r\n", "\n")).replace("\n", "\r\n").strip()
    sMd = "# %s\r\n\r\n" % os.path.splitext(os.path.basename(sSource))[0]
    if os.path.isfile(sTranscribed): sMd += "## What is said\r\n\r\n" + demoted(decodeText(open(sTranscribed, "rb").read())) + "\r\n\r\n"
    sMd += "## What can be seen\r\n\r\n" + demoted(decodeText(open(sDescribed, "rb").read())) + "\r\n"
    return finishFromMarkdown(sMd, sOut, sTo, sDir)


def finishFromMarkdown(sMd, sOut, sTo, sDir):
    sMdPath = os.path.join(sDir, "made.md")
    open(sMdPath, "w", encoding="utf-8-sig", newline="").write(sMd)
    if sTo in ("md", "txt"): shutil.copyfile(sMdPath, sOut)
    else: convert(sMdPath, sOut)
    return True


def speakTo(sSource, sOut, sTo, sDir):
    sFfmpeg = ffmpegProgram()
    if not sFfmpeg: raise RuntimeError("ffmpeg is not installed, and it is what encodes the speech")
    sType = typeOf(sSource)
    sText = decodeText(open(sSource, "rb").read()) if sType in ("txt", "md") else toText(sSource)
    if sType == "md": sText = re.sub(r"(?m)^#+\s*|[*_`>|]", "", sText)
    if not sText.strip(): raise RuntimeError("the document has no words to speak")
    sTxt, sWav = os.path.join(sDir, "words.txt"), os.path.join(sDir, "speech.wav")
    open(sTxt, "w", encoding="utf-8-sig").write(sText)
    sScript = ("Add-Type -AssemblyName System.Speech; $o = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
               "$o.SetOutputToWaveFile('%s'); $o.Speak([IO.File]::ReadAllText('%s')); $o.SetOutputToNull(); $o.Dispose()"
               % (sWav.replace("'", "''"), sTxt.replace("'", "''")))
    runTool(["powershell", "-NoProfile", "-NonInteractive", "-Command", sScript], "Windows speech synthesis", 120)
    if not os.path.isfile(sWav) or os.path.getsize(sWav) < 1000: raise RuntimeError("Windows speech synthesis made no sound")
    if sTo in lsSpeechVideoTargets:
        lsVideo = ["-c:v", "libvpx-vp9", "-c:a", "libopus"] if sTo == "webm" else ["-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac"]
        runTool([sFfmpeg, "-nostdin", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=1", "-i", sWav, "-shortest"] + lsVideo + [sOut], "ffmpeg", 120)
    else:
        runTool([sFfmpeg, "-nostdin", "-y", "-i", sWav, sOut], "ffmpeg", 120)
    return True


def mediaConvert(sSource, sOut, sTo):
    """The media half's way for this pair, run; "" when the pair is not media's, so the table is tried."""
    sCategory = mediaCategory(sSource)
    sDir = tempfile.mkdtemp(prefix="homerMedia-")
    try:
        if sCategory == "video" and sTo in lsTranscriptTargets:
            try:
                describeVideoTo(sSource, sOut, sTo, sDir); return "describe (HomerScribe)"
            except Exception as oError:
                say("Described video: %s; the transcript alone instead" % oError)
                transcribeTo(sSource, sOut, sTo, sDir); return "transcribe (Whisper)"
        if sCategory == "audio" and sTo in lsTranscriptTargets:
            transcribeTo(sSource, sOut, sTo, sDir); return "transcribe (Whisper)"
        if not sCategory and sTo in lsSpeechAudioTargets + lsSpeechVideoTargets and textCanBeSpoken(sSource):
            speakTo(sSource, sOut, sTo, sDir); return "speak (Windows)"
        if sCategory and sTo in lsAudioSources + lsVideoSources and (sCategory == "video" or sTo in lsAudioSources):
            sFfmpeg = ffmpegProgram()
            if not sFfmpeg: raise RuntimeError("ffmpeg is not installed")
            runTool([sFfmpeg, "-nostdin", "-y", "-i", sSource] + (["-vn"] if sTo in lsAudioSources else []) + [sOut], "ffmpeg", 240)
            return "ffmpeg"
        return ""
    finally:
        shutil.rmtree(sDir, ignore_errors=True)


def canConvert(sSource, sTarget):
    """Whether convert can make sTarget's type from sSource's: the route table, through a hub, or the media half."""
    sTo = typeOf(sTarget) if (os.path.splitext(sTarget)[1] or "/" in sTarget or os.sep in sTarget) else typeOf(sTarget.lstrip("."))
    return bool(loadTable().get(typeOf(sSource), {}).get(sTo)) or bool(hubFor(typeOf(sSource), sTo)) or mediaCan(sSource, sTo)


# THROUGH MARKDOWN (1.90.0), as Conversion.cs does: a pair the table does not name, or whose every way fails,
# goes in two of the table's own steps through Markdown, else a web page. Each step is an ordinary route.
lsHubs = ["md", "htm", "csv"]
setIntermediates = set()


def hubFor(sFrom, sTo):
    """The hub a pair would go through, or "" when it cannot be made that way."""
    if not sFrom or not sTo or sFrom == sTo: return ""
    dTable = loadTable()
    for sHub in lsHubs:
        if sHub in (sFrom, sTo): continue
        if dTable.get(sFrom, {}).get(sHub) and dTable.get(sHub, {}).get(sTo): return sHub
    return ""


def convert(sSource, sTarget, dOptions=None):
    """Convert sSource; sTarget is a path, or a type such as "md" for a file beside the source.
    Returns {path, route, ms, skipped}. Raises with every route's reason when none works."""
    if not os.path.isfile(sSource): raise FileNotFoundError(sSource)
    if os.path.splitext(sTarget)[1] or os.sep in sTarget or "/" in sTarget:
        sOut = sTarget; sTo = typeOf(sTarget)
    else:
        sTo = sTarget.lstrip(".").lower(); sOut = os.path.splitext(sSource)[0] + "." + sTo
    # THE MEDIA HALF FIRST, as Conversion.cs's convert does (1.86.0).
    dtMedia = time.time()
    sMediaWay = mediaConvert(sSource, sOut, sTo)
    if sMediaWay:
        iMs = int((time.time() - dtMedia) * 1000)
        say("%s -> %s by %s in %d ms" % (sSource, sOut, sMediaWay, iMs))
        return {"path": sOut, "route": sMediaWay, "ms": iMs, "skipped": []}
    sTo = typeOf(sTo)
    sHub = hubFor(typeOf(sSource), sTo)
    lRoutes = loadTable().get(typeOf(sSource), {}).get(sTo)
    if not lRoutes and not sHub: raise ValueError("no route from .%s to .%s" % (typeOf(sSource), sTo))
    sDirect = ""
    if lRoutes:
        try: return convertByRoute(sSource, sOut, sTo, lRoutes)
        except Exception as oError:
            if not sHub: raise
            sDirect = str(oError)
            say("%s: its own route could not, so through %s -- %s" % (os.path.basename(sSource), sHub, sDirect))
    sDir = tempfile.mkdtemp(prefix="homerHub-")
    try:
        sMiddle = os.path.join(sDir, os.path.splitext(os.path.basename(sSource))[0] + "." + sHub)
        setIntermediates.add(os.path.abspath(sMiddle))
        dFirst = convertByRoute(sSource, sMiddle, sHub, loadTable()[typeOf(sSource)][sHub])
        dSecond = convertByRoute(sMiddle, sOut, sTo, loadTable()[sHub][sTo])
        return {"path": sOut, "route": dFirst["route"] + " then " + dSecond["route"] + " (through " + sHub + ")",
                "ms": dFirst["ms"] + dSecond["ms"], "skipped": dFirst["skipped"] + dSecond["skipped"]}
    except Exception as oError:
        raise RuntimeError(("%s; and through %s: %s" % (sDirect, sHub, oError)) if sDirect else str(oError))
    finally:
        setIntermediates.discard(os.path.abspath(sMiddle)) if "sMiddle" in locals() else None
        shutil.rmtree(sDir, ignore_errors=True)


def convertByRoute(sSource, sOut, sTo, lRoutes):
    """One route's ways, best first, the first whose engines are present; the middle of convert."""
    lsTried = []
    for lSteps in lRoutes:
        sName = " > ".join(e for e, _ in lSteps)
        lsMissing = [e for e, _ in lSteps if not engineAvailable(e)]
        if lsMissing: lsTried.append("%s: %s not present" % (sName, ", ".join(lsMissing))); continue
        dtStart = time.time()
        sDir = tempfile.mkdtemp(prefix="homerRoute-")
        sStage = stagingPath(sOut)
        intendFor(sStage, sOut)
        try:
            sCurrent = sSource
            for i, (sEngine, sHands) in enumerate(lSteps):
                sStepTo = sHands if (i < len(lSteps) - 1 and sHands) else sTo
                sStepOut = os.path.join(sDir, "step%d.%s" % (i, sStepTo)) if i < len(lSteps) - 1 else sStage
                dEngines[sEngine](sCurrent, sStepTo, sStepOut)
                sCurrent = sStepOut
            # Every web page in the Homer form (1.87.1), unless page or json made it already.
            if typeOf(sOut) == "htm" and lSteps[-1][0] not in ("page", "json"):
                try: pageFinish(sStage)
                except Exception as oError: say("Page form not applied to %s: %s" % (os.path.basename(sOut), oError))
            # Text in the Homer encoding (1.80.0), as Conversion.cs does: UTF-8 with a byte order mark and CRLF.
            if typeOf(sOut) in ("csv", "htm", "html", "inix", "md", "tsv", "txt"):
                sMade = decodeText(open(sStage, "rb").read()).replace("\r\n", "\n").replace("\r", "\n")
                open(sStage, "w", encoding="utf-8-sig", newline="\r\n").write(sMade)
            # Every file finished for a screen reader, then checked (1.91.0): see finishOutput. The middle file of a
            # two-step conversion is not, since the next step reads it, not a person.
            if os.path.abspath(sOut) not in setIntermediates: finishOutput(sStage)
            # FINISHED, THEN SWAPPED IN (1.94.1, from an audit by another AI). The engine's file replaced the target
            # first and was finished there, so a failure while finishing -- a full disk, an interrupted rewrite --
            # left a changed or partial file under the real name of a conversion that had failed, and the next way
            # was tried over it. Everything now happens to a staging file beside the target, with the target's own
            # extension, and one replace makes it the target only when it is whole.
            os.replace(sStage, sOut)
            iMs = int((time.time() - dtStart) * 1000)
            say("%s -> %s by %s in %d ms" % (sSource, sOut, sName, iMs))
            return {"path": sOut, "route": sName, "ms": iMs, "skipped": lsTried}
        except Exception as oError:
            lsTried.append("%s: %s" % (sName, oError))
            try: os.remove(sStage)
            except OSError: pass
        finally:
            shutil.rmtree(sDir, ignore_errors=True)
            dIntendedNames.pop(os.path.abspath(sStage), None)
    raise RuntimeError("could not convert %s to .%s: %s" % (sSource, sTo, "; ".join(lsTried)))


def decodeText(abText):
    """Text from bytes whose encoding is not promised (1.76.1): the byte order mark first, then UTF-8, then the
    Windows code page. Word's text output was the case that needed it: UTF-16 from some documents and the code
    page from others, so a bullet (0x95) or a UTF-16 mark (0xFF) failed a UTF-8 read."""
    if abText[:2] in (b"\xff\xfe", b"\xfe\xff"): return abText.decode("utf-16")
    if abText[:3] == b"\xef\xbb\xbf": return abText[3:].decode("utf-8", "replace")
    try: return abText.decode("utf-8")
    except UnicodeDecodeError: return abText.decode("cp1252", "replace")


# ---------- accessible output (1.91.0), as Conversion.cs's finishOutput ----------
#
# EVERY FILE A HOMER APP MAKES IS FINISHED FOR A SCREEN READER, THEN CHECKED. Conversion.cs explains each
# step; this is the same, rule for rule, so a Python app's file is finished as a C# app's is. Findings use
# extCheck's rule names. Header names follow the author's xlHeaders.vbs, improved: an empty top-left corner
# no longer hides a two-way table, and a header must be text.

import html as htmlModule
import locale


# THE NAME A FILE IS MADE FOR (1.94.1, from an audit by another AI). A file finished under a staging name -- this
# module's own, or a caller's such as BatCon's -- took its document title from that name. A caller names the final
# path with intendFor, and the title comes from it.
dIntendedNames = {}


def intendFor(sStage, sFinal):
    """Say that the file at sStage is being made to become sFinal, so its title comes from sFinal's name."""
    dIntendedNames[os.path.abspath(sStage)] = os.path.abspath(sFinal)


def stagingPath(sOut):
    """A free name beside sOut with sOut's own extension, for a file to be finished before it replaces sOut."""
    sRoot, sExt = os.path.splitext(sOut)
    iTry = 0
    while True:
        sStage = "%s.homer-staging%s%s" % (sRoot, "" if iTry == 0 else "-%d" % iTry, sExt)
        if not os.path.exists(sStage): return sStage
        iTry += 1


def documentTitle(sPath):
    for _ in range(5):   # a chain is followed: a caller stages its result, and the route stages that file
        if os.path.abspath(sPath) not in dIntendedNames: break
        sPath = dIntendedNames[os.path.abspath(sPath)]
    sStem = os.path.splitext(os.path.basename(sPath))[0].replace("_", " ").strip()
    return sStem or "Untitled"


def documentLanguage():
    try:
        sName = locale.getlocale()[0] or ""
    except Exception:
        sName = ""
    sName = sName.split(".")[0].replace("_", "-")
    return sName if re.match(r"^[a-z]{2}-[A-Z]{2}$", sName) else "en-US"


def documentAuthor():
    return os.environ.get("USERNAME") or os.environ.get("USER") or ""


def xmlEscape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def xmlText(s):
    return htmlModule.unescape(s or "")


def readPackage(sPath):
    with zipfile.ZipFile(sPath) as oZip:
        lsOrder = oZip.namelist()
        dParts = {s: oZip.read(s) for s in lsOrder}
    return lsOrder, dParts


def writePackage(sPath, lsOrder, dParts):
    sTemp = sPath + ".finishing"
    with zipfile.ZipFile(sTemp, "w", zipfile.ZIP_DEFLATED) as oZip:
        for sName in lsOrder:
            oZip.writestr(sName, dParts[sName], zipfile.ZIP_STORED if sName == "mimetype" else zipfile.ZIP_DEFLATED)
    os.replace(sTemp, sPath)


def partText(dParts, sName):
    return dParts[sName].decode("utf-8", "replace").lstrip("\ufeff") if sName in dParts else ""


def setPart(dParts, lsOrder, sName, sText):
    if sName not in dParts: lsOrder.append(sName)
    dParts[sName] = sText.encode("utf-8")


def ensureCoreProperties(dParts, lsOrder, sTitle, lsFindings):
    sCore = partText(dParts, "docProps/core.xml")
    if not sCore:
        sCore = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                 'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"></cp:coreProperties>')
        sTypes = partText(dParts, "[Content_Types].xml")
        if "/docProps/core.xml" not in sTypes:
            setPart(dParts, lsOrder, "[Content_Types].xml", sTypes.replace("</Types>", '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'))
        sRels = partText(dParts, "_rels/.rels")
        if "core-properties" not in sRels:
            setPart(dParts, lsOrder, "_rels/.rels", sRels.replace("</Relationships>", '<Relationship Id="rIdHomerCore" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'))
    for sTag, sValue, sRule in (("dc:title", sTitle, "MissingDocumentTitle"), ("dc:creator", documentAuthor(), "MissingAuthor"), ("dc:language", documentLanguage(), "MissingDocumentLanguage")):
        oHas = re.search("<" + sTag + r"(?:\s[^>]*)?>(.*?)</" + sTag + ">", sCore, re.S)
        if oHas and xmlText(oHas.group(1)).strip(): continue
        if not sValue: lsFindings.append(sRule + ": left blank, nothing to fill it with"); continue
        sElement = "<%s>%s</%s>" % (sTag, xmlEscape(sValue), sTag)
        if oHas: sCore = sCore[:oHas.start()] + sElement + sCore[oHas.end():]
        else: sCore = re.sub("<" + sTag + r"\s*/>", "", sCore).replace("</cp:coreProperties>", sElement + "</cp:coreProperties>")
        lsFindings.append("%s: fixed, %s set to %s" % (sRule, sTag, sValue))
    setPart(dParts, lsOrder, "docProps/core.xml", sCore)


def finishOffice(sPath, sKind, lsFindings):
    lsOrder, dParts = readPackage(sPath)
    sTitle = ""
    if sKind == "word":
        sBody = partText(dParts, "word/document.xml")
        for oPara in re.finditer(r"<w:p\b.*?</w:p>", sBody, re.S):
            oStyle = re.search(r'<w:pStyle w:val="([^"]+)"', oPara.group(0))
            if not oStyle: continue
            sStyle = oStyle.group(1).lower()
            if sStyle != "title" and not sStyle.startswith("heading"): continue
            sText = "".join(xmlText(m.group(1)) for m in re.finditer(r"<w:t\b[^>]*>(.*?)</w:t>", oPara.group(0), re.S)).strip()
            if sText: sTitle = sText; break
        sTabled = finishWordTables(sBody, lsFindings)
        if sTabled != sBody: setPart(dParts, lsOrder, "word/document.xml", sTabled); sBody = sTabled
        if not re.search(r'<w:pStyle w:val="(?:[Hh]eading|Title)', sBody): lsFindings.append("NoHeadings: the document has no headings, so a screen reader cannot move by them")
        for oPicture in re.finditer(r"<wp:docPr\b[^>]*>", sBody):
            if not re.search(r'\bdescr="[^"]+"', oPicture.group(0)): lsFindings.append("MissingAltText: a picture has no alternative text")
        sStyles = partText(dParts, "word/styles.xml")
        oDefault = re.search(r"<w:rPrDefault>\s*<w:rPr>(.*?)</w:rPr>", sStyles, re.S)
        if oDefault and "<w:lang" not in oDefault.group(1):
            sStyles = sStyles[:oDefault.start(1)] + oDefault.group(1) + '<w:lang w:val="%s"/>' % documentLanguage() + sStyles[oDefault.end(1):]
            setPart(dParts, lsOrder, "word/styles.xml", sStyles)
            lsFindings.append("MissingLanguage: fixed, the default style's language set to " + documentLanguage())
    else:
        for sName in list(lsOrder):
            if not re.match(r"^ppt/slides/slide\d+\.xml$", sName): continue
            sSlide = partText(dParts, sName)
            oTitle = re.search(r'<p:sp>(?:(?!</p:sp>).)*?type="(?:ctrTitle|title)".*?</p:sp>', sSlide, re.S)
            if not oTitle: lsFindings.append("SlideMissingTitle: %s has no title" % os.path.splitext(os.path.basename(sName))[0])
            elif not sTitle: sTitle = "".join(xmlText(m.group(1)) for m in re.finditer(r"<a:t>(.*?)</a:t>", oTitle.group(0), re.S)).strip()
            for oPicture in re.finditer(r"<p:pic>.*?</p:pic>", sSlide, re.S):
                if not re.search(r'<p:cNvPr\b[^>]*\bdescr="[^"]+"', oPicture.group(0)):
                    lsFindings.append("MissingAltText: a picture on %s has no alternative text" % os.path.splitext(os.path.basename(sName))[0])
    ensureCoreProperties(dParts, lsOrder, sTitle or documentTitle(sPath), lsFindings)
    writePackage(sPath, lsOrder, dParts)


def finishEpub(sPath, lsFindings):
    lsOrder, dParts = readPackage(sPath)
    for sName in lsOrder:
        if not sName.lower().endswith(".opf"): continue
        sOpf = partText(dParts, sName); sWas = sOpf
        oTitle = re.search(r"<dc:title\b[^>]*>(.*?)</dc:title>", sOpf, re.S)
        if not oTitle or not xmlText(oTitle.group(1)).strip() or xmlText(oTitle.group(1)).strip().upper() == "UNTITLED":
            # The book's first heading, as a Word file's title is found, else the file's name.
            sBookTitle = ""
            for sPage in lsOrder:
                if not re.search(r"\.x?html?$", sPage, re.I): continue
                oHeading = re.search(r'<h1\b(?![^>]*class="title")[^>]*>(.*?)</h1>', partText(dParts, sPage), re.S | re.I)
                if oHeading:
                    sBookTitle = xmlText(re.sub(r"<[^>]+>", "", oHeading.group(1))).strip()
                    # Pandoc's own title page says UNTITLED when the source had no title, so that heading is no title.
                    if sBookTitle.upper() == "UNTITLED": sBookTitle = ""
                    if sBookTitle: break
            sBookTitle = sBookTitle or documentTitle(sPath)
            sElement = '<dc:title id="epub-title-1">%s</dc:title>' % xmlEscape(sBookTitle)
            sOpf = sOpf[:oTitle.start()] + sElement + sOpf[oTitle.end():] if oTitle else sOpf.replace("</metadata>", sElement + "</metadata>")
            lsFindings.append("MissingTitle: fixed, the book's title set to " + sBookTitle)
        if not re.search(r"<dc:language\b[^>]*>\s*\S", sOpf):
            sOpf = re.sub(r"<dc:language\b[^>]*>\s*</dc:language>|<dc:language\s*/>", "", sOpf).replace("</metadata>", "<dc:language>%s</dc:language></metadata>" % documentLanguage())
            lsFindings.append("MissingLanguage: fixed, the book's language set to " + documentLanguage())
        # EPUB Accessibility 1.1 metadata (1.92.2, from GLOW), as Conversion.cs: added only where there is none.
        if "schema:accessMode" not in sOpf:
            # Pictures are claimed to have text alternatives only when every one has (1.92.4, from MyBooks' buildBooks).
            lsImages = [m for s in lsOrder if re.search(r"\.x?html?$", s, re.I) for m in re.findall(r"<img\b[^>]*>", partText(dParts, s), re.I)]
            bPictures = bool(lsImages)
            bDescribed = bPictures and all(re.search(r'\balt="[^"]*\S[^"]*"', m, re.I) for m in lsImages)
            lsMeta = ['<meta property="schema:accessMode">textual</meta>']
            if bPictures: lsMeta.append('<meta property="schema:accessMode">visual</meta>')
            lsMeta += ['<meta property="schema:accessModeSufficient">%s</meta>' % ("textual,visual" if bPictures and not bDescribed else "textual"), '<meta property="schema:accessibilityFeature">structuralNavigation</meta>']
            if re.search(r'properties="[^"]*\bnav\b', sOpf): lsMeta.append('<meta property="schema:accessibilityFeature">tableOfContents</meta>')
            if bDescribed: lsMeta.append('<meta property="schema:accessibilityFeature">alternativeText</meta>')
            lsMeta += ['<meta property="schema:accessibilityHazard">none</meta>',
                       '<meta property="schema:accessibilitySummary">Made by a Homer program from a document: its text can be read throughout, and its headings and table of contents can be moved by.%s</meta>' % ((" Every picture has a text alternative." if bDescribed else " Some pictures are not yet described in text.") if bPictures else "")]
            sOpf = sOpf.replace("</metadata>", "".join(lsMeta) + "</metadata>")
            lsFindings.append("EpubAccessibilityMetadata: fixed, access modes, features, hazards and a summary added")
        if sOpf != sWas: setPart(dParts, lsOrder, sName, sOpf)
    writePackage(sPath, lsOrder, dParts)


def finishMarkdown(sPath, lsFindings):
    sText = decodeText(open(sPath, "rb").read()).replace("\r\n", "\n")
    iLast = 0; bHeading = False
    for oHeading in re.finditer(r"^(#{1,6})[ \t]+\S", sText, re.M):
        iLevel = len(oHeading.group(1))
        if iLast and iLevel > iLast + 1: lsFindings.append("SkippedHeadingLevel: a level %d heading follows a level %d" % (iLevel, iLast))
        iLast = iLevel; bHeading = True
    if not bHeading: lsFindings.append("NoHeadings: the document has no headings, so a screen reader cannot move by them")
    iTop = len(re.findall(r"^#[ \t]+\S", re.sub(r"(?ms)^(```|~~~).*?^\1", "", sText), re.M))
    if iTop > 1: lsFindings.append("MultipleTopHeadings: the document has %d top-level headings; a document has one, its title" % iTop)
    if re.search(r"!\[\s*\]\(", sText): lsFindings.append("MissingAltText: a picture has no alternative text")
    if not sText.startswith("---\n"):
        oFirst = re.search(r"^#[ \t]+(.+)$", sText, re.M)
        sTitle = oFirst.group(1).strip() if oFirst else documentTitle(sPath)
        sText = '---\ntitle: "%s"\nlang: %s\n---\n\n' % (sTitle.replace("\\", "\\\\").replace('"', '\\"'), documentLanguage()) + sText
        open(sPath, "w", encoding="utf-8-sig", newline="\r\n").write(sText)
        lsFindings.append("NoYamlFrontMatter: fixed, title and lang added")


def checkPdfTags(sPath, lsFindings):
    """Whether a PDF carries tags (1.92.0, from IsTagged in KeyLine), as Conversion.cs's checkPdfTags."""
    sBytes = open(sPath, "rb").read().decode("latin-1")
    bTree = "/StructTreeRoot" in sBytes; bMarked = bool(re.search(r"/Marked\s*true", sBytes))
    if not bTree or not bMarked:
        lsFindings.append("UntaggedPdf: no %s was found, so a screen reader may read it as plain text; listen to it to be sure" % ("structure tree" if not bTree else "marked-content flag"))
    if not re.search(r"/Lang\s*\(", sBytes): lsFindings.append("MissingDocumentLanguage: the PDF names no language")
    # A title and bookmarks (1.92.2, from GLOW), as Conversion.cs.
    if not re.search(r"/Title\s*(?:\(\s*[^)\s]|<\s*[0-9A-Fa-f]{4})", sBytes) and not re.search(r"<dc:title>\s*<rdf:Alt>\s*<rdf:li[^>]*>\s*[^<\s]", sBytes):
        lsFindings.append("MissingDocumentTitle: the PDF has no title, so a reader announces its file name")
    if "/Outlines" not in sBytes: lsFindings.append("NoBookmarks: the PDF has no bookmarks to move by its headings")


def checkPage(sPath, lsFindings):
    sHtml = decodeText(open(sPath, "rb").read())
    for oImage in re.finditer(r"<img\b[^>]*>", sHtml, re.I):
        if not re.search(r'\balt="', oImage.group(0), re.I): lsFindings.append("MissingAltText: a picture has no alternative text")
    if not re.search(r'<html\b[^>]*\blang="[^"]+"', sHtml, re.I): lsFindings.append("MissingDocumentLanguage: the page names no language")


def cellPosition(sRef):
    oRef = re.match(r"^\$?([A-Za-z]+)\$?(\d+)$", sRef)
    if not oRef: return None
    iColumn = 0
    for c in oRef.group(1).upper(): iColumn = iColumn * 26 + (ord(c) - ord("A") + 1)
    return int(oRef.group(2)), iColumn


def columnName(iColumn):
    sName = ""
    while iColumn > 0:
        iRest = (iColumn - 1) % 26; sName = chr(ord("A") + iRest) + sName; iColumn = (iColumn - 1) // 26
    return sName


def findRegions(dText):
    """[top, left, bottom, right] rectangles, as Excel's CurrentRegion gives them."""
    lRegions = []; setSeen = set()
    for tStart in dText:
        if tStart in setSeen: continue
        lBox = [tStart[0], tStart[1], tStart[0], tStart[1]]
        lQueue = [tStart]; setSeen.add(tStart)
        while lQueue:
            iRow, iColumn = lQueue.pop()
            lBox = [min(lBox[0], iRow), min(lBox[1], iColumn), max(lBox[2], iRow), max(lBox[3], iColumn)]
            for iDown in (-1, 0, 1):
                for iAcross in (-1, 0, 1):
                    tNear = (iRow + iDown, iColumn + iAcross)
                    if tNear in dText and tNear not in setSeen: setSeen.add(tNear); lQueue.append(tNear)
        lRegions.append(lBox)
    bMerged = True
    while bMerged:
        bMerged = False
        for i in range(len(lRegions)):
            for j in range(i + 1, len(lRegions)):
                a, b = lRegions[i], lRegions[j]
                if a[1] - 1 <= b[3] and b[1] - 1 <= a[3] and a[0] - 1 <= b[2] and b[0] - 1 <= a[2]:
                    lRegions[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del lRegions[j]; bMerged = True; break
            if bMerged: break
    return sorted(lRegions)


def labelsRun(dText, setIsText, iRow, iColumn, iDown, iAcross, iCount):
    if iCount < 1: return False
    setSeen = set()
    for i in range(iCount):
        tKey = (iRow + i * iDown, iColumn + i * iAcross)
        sValue = dText.get(tKey)
        if sValue is None or tKey not in setIsText or sValue.lower() in setSeen: return False
        setSeen.add(sValue.lower())
    return True


def headerStem(lBox, dText, setIsText):
    iTop, iLeft, iBottom, iRight = lBox
    if iBottom - iTop < 1 or iRight - iLeft < 1: return ""
    bCorner = (iTop, iLeft) in dText
    iFirstColumn = iLeft if bCorner else iLeft + 1
    iFirstRow = iTop if bCorner else iTop + 1
    bColumns = labelsRun(dText, setIsText, iTop, iFirstColumn, 0, 1, iRight - iFirstColumn + 1)
    bRows = labelsRun(dText, setIsText, iFirstRow, iLeft, 1, 0, iBottom - iFirstRow + 1)
    return "Title" if bColumns and bRows else "ColumnTitle" if bColumns else "RowTitle" if bRows else ""


# ---- a workbook laid out for reading (1.91.1, from xlFormat.vbs in KeyLine), as Conversion.cs ----
iWidestColumn = 40
sReadingStyles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font><font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')


def addReadingStyles(dParts, lsOrder):
    setPart(dParts, lsOrder, "xl/styles.xml", sReadingStyles)
    sTypes = partText(dParts, "[Content_Types].xml")
    if "/xl/styles.xml" not in sTypes:
        setPart(dParts, lsOrder, "[Content_Types].xml", sTypes.replace("</Types>", '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'))
    sRels = partText(dParts, "xl/_rels/workbook.xml.rels")
    if '/styles"' not in sRels:
        setPart(dParts, lsOrder, "xl/_rels/workbook.xml.rels", sRels.replace("</Relationships>", '<Relationship Id="rIdHomerStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'))


def layOutSheet(sXml, dText, setHeaderRows):
    dWidest = {}
    for (iRow, iColumn), sValue in dText.items():
        iLongest = max(len(s) for s in sValue.replace("\r", "").split("\n"))
        if iLongest > dWidest.get(iColumn, -1): dWidest[iColumn] = iLongest
    if "<cols>" not in sXml and dWidest:
        sCols = "<cols>" + "".join('<col min="%d" max="%d" width="%d" customWidth="1"/>' % (c, c, min(max(dWidest[c], 6), iWidestColumn) + 2) for c in sorted(dWidest)) + "</cols>"
        iData = sXml.find("<sheetData")
        if iData >= 0: sXml = sXml[:iData] + sCols + sXml[iData:]
    def styled(oCell):
        sAttributes = oCell.group(1)
        oRef = re.search(r'\br="([^"]+)"', sAttributes)
        tPosition = cellPosition(oRef.group(1)) if oRef else None
        if not tPosition or re.search(r'\bs="', sAttributes): return oCell.group(0)
        sStyle = "1" if tPosition[0] in setHeaderRows else "2" if dWidest.get(tPosition[1], 0) > iWidestColumn else ""
        if not sStyle: return oCell.group(0)
        return "<c" + sAttributes + ' s="%s"' % sStyle + oCell.group(0)[2 + len(sAttributes):]
    return re.sub(r"<c\b([^>]*?)(?:/>|>(.*?)</c>)", styled, sXml, flags=re.S)


# ---- tables in a Word file (1.91.1, from docxIt's FormatTables in KeyLine), as Conversion.cs ----
def wordCells(sRow):
    return ["".join(xmlText(t) for t in re.findall(r"<w:t\b[^>]*>(.*?)</w:t>", m, re.S)).strip() for m in re.findall(r"<w:tc>.*?</w:tc>", sRow, re.S)]


def uniqueText(lsValues):
    if not lsValues: return False
    setSeen = set()
    for sValue in lsValues:
        try:
            float(sValue); return False
        except ValueError: pass
        if not sValue or sValue.lower() in setSeen: return False
        setSeen.add(sValue.lower())
    return True


def finishWordTables(sBody, lsFindings):
    lsIds = [int(s) for s in re.findall(r'<w:bookmarkStart\b[^>]*\bw:id="(\d+)"', sBody)]
    dState = {"table": 0, "bookmark": max(lsIds) if lsIds else 0}
    setNames = set(s.lower() for s in re.findall(r'<w:bookmarkStart\b[^>]*\bw:name="([^"]+)"', sBody))
    def finished(oTable):
        dState["table"] += 1; iTable = dState["table"]
        sTable = oTable.group(0)
        lsRows = re.findall(r"<w:tr\b.*?</w:tr>", sTable, re.S)
        if len(lsRows) < 2: return sTable
        bColumns = uniqueText(wordCells(lsRows[0]))
        bRows = uniqueText([(wordCells(r) or [""])[0] for r in lsRows[1:]])
        if not bColumns:
            lsFindings.append("TableMissingHeaderRow: table %d has no first row of distinct headers" % iTable); return sTable
        sRow = lsRows[0]
        if "<w:tblHeader" not in sRow:
            sNewRow = sRow.replace("<w:trPr>", "<w:trPr><w:tblHeader/>", 1) if "<w:trPr>" in sRow else re.sub(r"^<w:tr\b[^>]*>", lambda m: m.group(0) + "<w:trPr><w:tblHeader/></w:trPr>", sRow)
            sTable = sTable.replace(sRow, sNewRow); sRow = sNewRow
            lsFindings.append("TableMissingHeaderRow: fixed, table %d's first row marked as its header row" % iTable)
        sTable = re.sub(r"<w:tblLook\b[^>]*/>", lambda m: m.group(0) if 'w:firstRow="1"' in m.group(0) else re.sub(r'\s*w:firstRow="[^"]*"', "", m.group(0)).replace("<w:tblLook", '<w:tblLook w:firstRow="1"'), sTable)
        if re.search(r'<w:bookmarkStart\b[^>]*\bw:name="(?:Column|Row)?Title', sTable, re.I): return sTable
        sStem = "Title" if bRows else "ColumnTitle"
        iNumber = 1
        while ("%s%02d" % (sStem, iNumber)).lower() in setNames: iNumber += 1
        sName = "%s%02d" % (sStem, iNumber); setNames.add(sName.lower())
        dState["bookmark"] += 1
        oFirstPara = re.search(r"<w:p\b[^>]*>(?:<w:pPr>.*?</w:pPr>)?", sRow, re.S)
        if not oFirstPara: return sTable
        sMarked = sRow[:oFirstPara.end()] + '<w:bookmarkStart w:id="%d" w:name="%s"/><w:bookmarkEnd w:id="%d"/>' % (dState["bookmark"], sName, dState["bookmark"]) + sRow[oFirstPara.end():]
        lsFindings.append("Header names: bookmark %s in table %d" % (sName, iTable))
        return sTable.replace(sRow, sMarked)
    return re.sub(r"<w:tbl>.*?</w:tbl>", finished, sBody, flags=re.S)


def finishXlsx(sPath, lsFindings):
    lsOrder, dParts = readPackage(sPath)
    sBook = partText(dParts, "xl/workbook.xml")
    # A workbook with no styles of its own is laid out for reading, as xlFormat did; any other is left as formatted.
    bFresh = "xl/styles.xml" not in dParts
    if bFresh: addReadingStyles(dParts, lsOrder)
    sBookRels = partText(dParts, "xl/_rels/workbook.xml.rels")
    lsShared = ["".join(xmlText(t) for t in re.findall(r"<t\b[^>]*>(.*?)</t>", m, re.S)) for m in re.findall(r"<si>(.*?)</si>", partText(dParts, "xl/sharedStrings.xml"), re.S)]
    setNames = set(); setNamedCells = set()
    for sAttrs, sRef in re.findall(r"<definedName\b([^>]*)>(.*?)</definedName>", sBook, re.S):
        oName = re.search(r'\bname="([^"]+)"', sAttrs)
        if oName: setNames.add(oName.group(1).lower())
        setNamedCells.add(xmlText(sRef).replace("'", "").strip().lower())
    lsSheets = re.findall(r"<sheet\b[^>]*/>", sBook)
    lsNewNames = []
    for sSheetTag in lsSheets:
        sSheetName = xmlText(re.search(r'\bname="([^"]*)"', sSheetTag).group(1))
        sRid = re.search(r'\br:id="([^"]*)"', sSheetTag).group(1)
        oRel = re.search(r'<Relationship\b[^>]*\bId="%s"[^>]*>' % re.escape(sRid), sBookRels)
        sTarget = re.search(r'\bTarget="([^"]*)"', oRel.group(0)).group(1) if oRel else ""
        sPart = sTarget.lstrip("/") if sTarget.startswith("/") else "xl/" + sTarget
        sXml = partText(dParts, sPart)
        if not sXml: continue
        if len(lsSheets) == 1 and re.match(r"^(Sheet\d*|Data)$", sSheetName) and "<f" not in sXml and not setNames:
            sNewName = re.sub(r"[\[\]:*?/\\]", " ", documentTitle(sPath)).strip()[:31].strip()
            if sNewName and sNewName != sSheetName:
                sBook = sBook.replace(sSheetTag, sSheetTag.replace('name="%s"' % xmlEscape(sSheetName), 'name="%s"' % xmlEscape(sNewName)))
                lsFindings.append("DefaultSheetName: fixed, %s renamed %s" % (sSheetName, sNewName)); sSheetName = sNewName
        if "<mergeCell " in sXml: lsFindings.append("MergedCells: %s has merged cells, which screen readers announce poorly" % sSheetName)
        dText = {}; setIsText = set()
        for sAttrs, sInner in re.findall(r"<c\b([^>]*?)(?:/>|>(.*?)</c>)", sXml, re.S):
            dAttrs = dict(re.findall(r'\b([A-Za-z:]+)="([^"]*)"', sAttrs))
            sRef, sType = dAttrs.get("r", ""), dAttrs.get("t", "")
            if not sRef or not sInner: continue
            if sType == "inlineStr": sValue = "".join(xmlText(t) for t in re.findall(r"<t\b[^>]*>(.*?)</t>", sInner, re.S))
            else:
                oV = re.search(r"<v>(.*?)</v>", sInner, re.S)
                if not oV: continue
                sValue = xmlText(oV.group(1))
                if sType == "s": sValue = lsShared[int(sValue)] if sValue.isdigit() and int(sValue) < len(lsShared) else ""
            if not sValue.strip(): continue
            tPosition = cellPosition(sRef)
            if not tPosition: continue
            dText[tPosition] = sValue.strip()
            if sType in ("s", "inlineStr", "str"): setIsText.add(tPosition)
        bFrozen = "<pane " in sXml
        setHeaderRows = set()
        for lBox in findRegions(dText):
            sStem = headerStem(lBox, dText, setIsText)
            if sStem in ("ColumnTitle", "Title"): setHeaderRows.add(lBox[0])
            if sStem in ("", "RowTitle"):
                iBlank = sum(1 for c in range(lBox[1] + 1, lBox[3] + 1) if (lBox[0], c) not in dText)
                iTextual = sum(1 for c in range(lBox[1] + 1, lBox[3] + 1) if (lBox[0], c) in setIsText)
                if iBlank and iTextual >= iBlank and lBox[2] > lBox[0]:
                    lsFindings.append("BlankOrGenericColumnHeader: %s row %d has %d %s without a header; each was kept" % (sSheetName, lBox[0], iBlank, "column" if iBlank == 1 else "columns"))
            if not sStem: continue
            sCell = "$%s$%d" % (columnName(lBox[1]), lBox[0])
            if (sSheetName + "!" + sCell).lower() in setNamedCells: continue
            iNumber = 1
            while ("%s%02d" % (sStem, iNumber)).lower() in setNames: iNumber += 1
            sName = "%s%02d" % (sStem, iNumber); setNames.add(sName.lower())
            lsNewNames.append('<definedName name="%s">%s</definedName>' % (sName, xmlEscape("'%s'!%s" % (sSheetName.replace("'", "''"), sCell))))
            lsFindings.append("Header names: %s for %s %s%d:%s%d" % (sName, sSheetName, columnName(lBox[1]), lBox[0], columnName(lBox[3]), lBox[2]))
            if not bFrozen:
                iYSplit = lBox[0] if sStem != "RowTitle" else 0
                iXSplit = lBox[1] if sStem != "ColumnTitle" else 0
                sPane = ("<pane" + (' xSplit="%d"' % iXSplit if iXSplit else "") + (' ySplit="%d"' % iYSplit if iYSplit else "")
                         + ' topLeftCell="%s%d" activePane="%s" state="frozen"/>' % (columnName(iXSplit + 1), iYSplit + 1, "bottomRight" if iXSplit and iYSplit else "bottomLeft" if iYSplit else "topRight"))
                oView = re.search(r"<sheetView\b[^>]*?(/?)>", sXml)
                if oView and oView.group(1) == "/": sXml = sXml[:oView.start()] + oView.group(0)[:-2] + ">" + sPane + "</sheetView>" + sXml[oView.end():]
                elif oView: sXml = sXml[:oView.end()] + sPane + sXml[oView.end():]
                else:
                    oBefore = re.search(r"<(?:sheetFormatPr|cols|sheetData)\b", sXml)
                    if oBefore: sXml = sXml[:oBefore.start()] + '<sheetViews><sheetView workbookViewId="0">' + sPane + "</sheetView></sheetViews>" + sXml[oBefore.start():]
                bFrozen = True
                setPart(dParts, lsOrder, sPart, sXml)
        if bFresh:
            sXml = layOutSheet(sXml, dText, setHeaderRows)
            setPart(dParts, lsOrder, sPart, sXml)
    if lsNewNames:
        sNew = "".join(lsNewNames)
        if "</definedNames>" in sBook: sBook = sBook.replace("</definedNames>", sNew + "</definedNames>")
        elif re.search(r"<definedNames\s*/>", sBook): sBook = re.sub(r"<definedNames\s*/>", "<definedNames>" + sNew + "</definedNames>", sBook)
        else: sBook = sBook.replace("</sheets>", "</sheets><definedNames>" + sNew + "</definedNames>")
    setPart(dParts, lsOrder, "xl/workbook.xml", sBook)
    ensureCoreProperties(dParts, lsOrder, documentTitle(sPath), lsFindings)
    writePackage(sPath, lsOrder, dParts)


def finishOutput(sPath):
    """The step every route ends with. Never fails a conversion: a finishing problem is said and logged."""
    sType = typeOf(sPath); lsFindings = []
    try:
        if sType == "xlsx": finishXlsx(sPath, lsFindings)
        elif sType == "docx": finishOffice(sPath, "word", lsFindings)
        elif sType == "pptx": finishOffice(sPath, "ppt", lsFindings)
        elif sType == "epub": finishEpub(sPath, lsFindings)
        elif sType == "md": finishMarkdown(sPath, lsFindings)
        elif sType == "htm": checkPage(sPath, lsFindings)
        elif sType == "pdf": checkPdfTags(sPath, lsFindings)
    except Exception as oError:
        say("Finishing %s for a screen reader failed: %s" % (os.path.basename(sPath), oError))
    for sFinding in lsFindings: say("Quality %s: %s" % (os.path.basename(sPath), sFinding))
    return lsFindings


def toText(sSource):
    """The text of a file, by the quickest route the table offers for plain text."""
    sDir = tempfile.mkdtemp(prefix="homerText-")
    try:
        sOut = os.path.join(sDir, "text.txt")
        convert(sSource, sOut)
        return decodeText(open(sOut, "rb").read())
    finally:
        shutil.rmtree(sDir, ignore_errors=True)

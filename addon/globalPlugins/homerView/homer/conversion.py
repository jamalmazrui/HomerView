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
import re
import shutil
import subprocess
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
    return os.path.splitext(sPath)[1].lstrip(".").lower()


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
    return ""


def engineAvailable(sEngine):
    if sEngine in ("copy", "json", "markdown", "page", "table", "zipxml"): return True
    if sEngine == "pandoc": return bool(programFor(sEngine))
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


def zipXlsx(oZip, bMarkdown, bCsv=False):
    lsShared = []
    if "xl/sharedStrings.xml" in oZip.namelist():
        for oItem in ET.fromstring(oZip.read("xl/sharedStrings.xml")).iter(sS + "si"):
            lsShared.append("".join(o.text or "" for o in oItem.iter(sS + "t")))
    oBook = ET.fromstring(oZip.read("xl/workbook.xml"))
    lsNames = [o.get("name") for o in oBook.iter(sS + "sheet")]
    lsOut = []
    for iSheet, sName in enumerate(lsNames, 1):
        sPath = "xl/worksheets/sheet%d.xml" % iSheet
        if sPath not in oZip.namelist(): continue
        llRows = []
        for oRow in ET.fromstring(oZip.read(sPath)).iter(sS + "row"):
            lsCells = []
            for oCell in oRow.iter(sS + "c"):
                oValue = oCell.find(sS + "v"); oInline = oCell.find(sS + "is")
                sValue = oValue.text if oValue is not None else ("".join(o.text or "" for o in oInline.iter(sS + "t")) if oInline is not None else "")
                if oCell.get("t") == "s" and sValue: sValue = lsShared[int(sValue)]
                lsCells.append(sValue or "")
            llRows.append(lsCells)
        if bCsv:
            import csv, io
            oBuffer = io.StringIO(); csv.writer(oBuffer, lineterminator="\n").writerows(llRows)
            return oBuffer.getvalue().rstrip("\n").split("\n")   # the first sheet, as a comma-separated file
        if bMarkdown:
            lsOut.append("## " + sName); lsOut.append("")
            if llRows:
                iWidth = max(len(r) for r in llRows)
                for i, lsRow in enumerate(llRows):
                    lsOut.append("| " + " | ".join((lsRow + [""] * iWidth)[:iWidth]).replace("\n", " ") + " |")
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
            oDoc = oApp.Documents.Open(os.path.abspath(sSource), ReadOnly=True); oDoc.SaveAs2(os.path.abspath(sOut), FileFormat=iFormat); oDoc.Close(False)
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
            llCells.append([c.strip() for c in sLine.strip("|").split("|")])
        if not llCells: raise ValueError("no table was found in this Markdown file")
        return llCells[0], llCells[1:]
    if sType == "xlsx":
        import zipfile
        with zipfile.ZipFile(sSource) as oZip:
            lsShared = []
            if "xl/sharedStrings.xml" in oZip.namelist():
                for oItem in ET.fromstring(oZip.read("xl/sharedStrings.xml")).iter(sS + "si"):
                    lsShared.append("".join(o.text or "" for o in oItem.iter(sS + "t")))
            llRows = []
            for oRow in ET.fromstring(oZip.read("xl/worksheets/sheet1.xml")).iter(sS + "row"):
                lsCells = []
                for oCell in oRow.iter(sS + "c"):
                    iColumn = xlsxIndex(oCell.get("r", ""))
                    while iColumn > len(lsCells): lsCells.append("")
                    oValue = oCell.find(sS + "v"); oInline = oCell.find(sS + "is")
                    sValue = oValue.text if oValue is not None else ("".join(o.text or "" for o in oInline.iter(sS + "t")) if oInline is not None else "")
                    if oCell.get("t") == "s" and sValue: sValue = lsShared[int(sValue)]
                    lsCells.append(sValue or "")
                llRows.append(lsCells)
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


dEngines = {"copy": engineCopy, "markdown": engineMarkdown, "ocr": engineOcr, "officecom": engineOfficeCom,
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
    """Whether convert can make sTarget's type from sSource's: the route table, or the media half."""
    sTo = typeOf(sTarget) if (os.path.splitext(sTarget)[1] or "/" in sTarget or os.sep in sTarget) else sTarget.lstrip(".").lower()
    return bool(loadTable().get(typeOf(sSource), {}).get(sTo)) or mediaCan(sSource, sTo)


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
    dTable = loadTable()
    lRoutes = dTable.get(typeOf(sSource), {}).get(sTo)
    if not lRoutes: raise ValueError("no route from .%s to .%s" % (typeOf(sSource), sTo))
    lsTried = []
    for lSteps in lRoutes:
        sName = " > ".join(e for e, _ in lSteps)
        lsMissing = [e for e, _ in lSteps if not engineAvailable(e)]
        if lsMissing: lsTried.append("%s: %s not present" % (sName, ", ".join(lsMissing))); continue
        dtStart = time.time()
        sDir = tempfile.mkdtemp(prefix="homerRoute-")
        try:
            sCurrent = sSource
            for i, (sEngine, sHands) in enumerate(lSteps):
                sStepTo = sHands if (i < len(lSteps) - 1 and sHands) else sTo
                sStepOut = os.path.join(sDir, "step%d.%s" % (i, sStepTo)) if i < len(lSteps) - 1 else sOut + ".part"
                dEngines[sEngine](sCurrent, sStepTo, sStepOut)
                sCurrent = sStepOut
            os.replace(sOut + ".part", sOut)
            # Every web page in the Homer form (1.87.1), unless page or json made it already.
            if typeOf(sOut) == "htm" and lSteps[-1][0] not in ("page", "json"):
                try: pageFinish(sOut)
                except Exception as oError: say("Page form not applied to %s: %s" % (os.path.basename(sOut), oError))
            # Text in the Homer encoding (1.80.0), as Conversion.cs does: UTF-8 with a byte order mark and CRLF.
            if typeOf(sOut) in ("csv", "htm", "html", "inix", "md", "tsv", "txt"):
                sMade = decodeText(open(sOut, "rb").read()).replace("\r\n", "\n").replace("\r", "\n")
                open(sOut, "w", encoding="utf-8-sig", newline="\r\n").write(sMade)
            iMs = int((time.time() - dtStart) * 1000)
            say("%s -> %s by %s in %d ms" % (sSource, sOut, sName, iMs))
            return {"path": sOut, "route": sName, "ms": iMs, "skipped": lsTried}
        except Exception as oError:
            lsTried.append("%s: %s" % (sName, oError))
            try: os.remove(sOut + ".part")
            except OSError: pass
        finally:
            shutil.rmtree(sDir, ignore_errors=True)
    raise RuntimeError("could not convert %s to .%s: %s" % (sSource, sTo, "; ".join(lsTried)))


def decodeText(abText):
    """Text from bytes whose encoding is not promised (1.76.1): the byte order mark first, then UTF-8, then the
    Windows code page. Word's text output was the case that needed it: UTF-16 from some documents and the code
    page from others, so a bullet (0x95) or a UTF-16 mark (0xFF) failed a UTF-8 read."""
    if abText[:2] in (b"\xff\xfe", b"\xfe\xff"): return abText.decode("utf-16")
    if abText[:3] == b"\xef\xbb\xbf": return abText[3:].decode("utf-8", "replace")
    try: return abText.decode("utf-8")
    except UnicodeDecodeError: return abText.decode("cp1252", "replace")


def toText(sSource):
    """The text of a file, by the quickest route the table offers for plain text."""
    sDir = tempfile.mkdtemp(prefix="homerText-")
    try:
        sOut = os.path.join(sDir, "text.txt")
        convert(sSource, sOut)
        return decodeText(open(sOut, "rb").read())
    finally:
        shutil.rmtree(sDir, ignore_errors=True)

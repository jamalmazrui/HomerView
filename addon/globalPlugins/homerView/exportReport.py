"""Write a scan result as JSON, CSV, HTML and a spreadsheet, without libraries.

The IBM engine returns JSON and nothing else. The spreadsheet and HTML reports
people associate with IBM's checker come from its other tools: the Node package
and the browser extension, neither of which can run inside an NVDA add-on. So
the formats are produced here instead, from the same JSON.

Three of the four are easy. The fourth, a spreadsheet, is usually a reason to
add a dependency, and it does not have to be. An .xlsx file is a zip archive of
XML parts, and Python's standard library has both zipfile and the ability to
write XML by hand. Using inline strings rather than a shared string table
removes the last part that would need bookkeeping, which leaves a workbook
small enough to read and verify.

Everything lands in the user's downloads folder, because that is where a file
someone means to keep and send belongs, unlike the working copies that go to
the temporary folder.
"""

import csv
import html
import json
import zipfile
from datetime import datetime

from . import paths
from .logger import homerLog, logError

lExportFormats = ["json", "csv", "xlsx", "html"]
maximumCellCharacters = 32000

contentTypesXml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheetOverrides}
</Types>"""

rootRelsXml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def escapeXml(vValue):
    sText = "" if vValue is None else str(vValue)
    sText = "".join(c for c in sText if c == "\t" or c == "\n" or ord(c) >= 32)
    return html.escape(sText[:maximumCellCharacters], quote=True)


def columnName(iIndex):
    """1 becomes A, 27 becomes AA."""
    sName = ""
    while iIndex > 0:
        iIndex, iRemainder = divmod(iIndex - 1, 26)
        sName = chr(65 + iRemainder) + sName
    return sName


def buildSheetXml(lRows):
    lParts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>',
    ]
    for iRow, lRow in enumerate(lRows, 1):
        lParts.append(f'<row r="{iRow}">')
        for iColumn, vCell in enumerate(lRow, 1):
            sReference = f"{columnName(iColumn)}{iRow}"
            if isinstance(vCell, (int, float)) and not isinstance(vCell, bool):
                lParts.append(f'<c r="{sReference}"><v>{vCell}</v></c>')
            else:
                lParts.append(
                    f'<c r="{sReference}" t="inlineStr"><is><t xml:space="preserve">'
                    f"{escapeXml(vCell)}</t></is></c>"
                )
        lParts.append("</row>")
    lParts.append("</sheetData></worksheet>")
    return "".join(lParts)


def writeXlsx(pathTarget, lSheets):
    """Write a workbook. lSheets is a list of (name, rows) pairs."""
    lSheets = lSheets or [("Sheet1", [])]
    lOverrides = []
    lWorkbookSheets = []
    lRelationships = []
    for iIndex, (sName, _lRows) in enumerate(lSheets, 1):
        lOverrides.append(
            f'<Override PartName="/xl/worksheets/sheet{iIndex}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.worksheet+xml"/>'
        )
        lWorkbookSheets.append(
            f'<sheet name="{escapeXml(sName)[:31]}" sheetId="{iIndex}" r:id="rId{iIndex}"/>'
        )
        lRelationships.append(
            f'<Relationship Id="rId{iIndex}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{iIndex}.xml"/>'
        )
    with zipfile.ZipFile(pathTarget, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            contentTypesXml.format(sheetOverrides="\n".join(lOverrides)),
        )
        archive.writestr("_rels/.rels", rootRelsXml)
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<sheets>" + "".join(lWorkbookSheets) + "</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(lRelationships)
            + "</Relationships>",
        )
        for iIndex, (_sName, lRows) in enumerate(lSheets, 1):
            archive.writestr(f"xl/worksheets/sheet{iIndex}.xml", buildSheetXml(lRows))
    return pathTarget


def writeCsv(pathTarget, lRows):
    with open(pathTarget, "w", encoding="utf-8-sig", newline="") as fFile:
        writer = csv.writer(fFile)
        writer.writerows(lRows)
    return pathTarget


def writeJson(pathTarget, vData):
    pathTarget.write_text(json.dumps(vData, indent=2), encoding="utf-8")
    return pathTarget


def writeHtml(pathTarget, sHtml):
    pathTarget.write_text(sHtml, encoding="utf-8-sig", newline="\r\n")
    return pathTarget


safeStem = paths.safeStem


def exportAll(sPrefix, sPageTitle, vJson, lRows, sHtml, lSheets=None):
    """Write every format to the downloads folder and return what was written.

    One failure does not stop the others. A spreadsheet that cannot be written
    is no reason to withhold the CSV.
    """
    # ONE FOLDER PER PAGE, and the tool names its own files: IBM.htm, Axe.htm.
    #
    # This used to write "Axe <page title> 2026-08-14 2033.json" into Downloads
    # itself, which put a new set of four files there on every run and left the
    # reader to work out which run was which. The folder is named for the page,
    # the file is named for the tool, and a second run replaces the first --
    # which is what "run it again after fixing something" should mean.
    pathFolder = paths.pageFolder(sPageTitle)
    dWritten = {}
    for sFormat in lExportFormats:
        pathTarget = pathFolder / f"{sPrefix}.{sFormat}"
        try:
            if sFormat == "json":
                writeJson(pathTarget, vJson)
            elif sFormat == "csv":
                writeCsv(pathTarget, lRows)
            elif sFormat == "xlsx":
                writeXlsx(pathTarget, lSheets or [("Results", lRows)])
            else:
                writeHtml(pathTarget, sHtml)
            dWritten[sFormat] = str(pathTarget)
            homerLog.info(f"Exported {sFormat}: {pathTarget} ({pathTarget.stat().st_size} bytes)")
        except Exception:
            logError(f"The {sFormat} export failed")
    return {"folder": str(pathFolder), "written": dWritten}

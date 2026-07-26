"""Save the page you are reading as HTML, Markdown, or plain text.

The three formats answer three different needs, and the command offers all
three every time rather than guessing.

HTML keeps the structure a screen reader navigates by: headings, lists, tables,
and image alternative text. It is what to keep when the document might be read
again.

Markdown keeps that structure as punctuation, so it survives being pasted into a
message, an editor, or a repository, and stays readable without any program.

Plain text keeps only the words. It is what to use when something further down
the line cannot cope with anything else.

HTML comes from the browser itself, so what is saved is the page as it stands
after script has run, not the markup the server first sent. Markdown and plain
text are derived from that same live document.
"""

from pathlib import Path

from .logger import abbreviate, homerLog, logSection

extractTimeoutSeconds = 60.0

# Turning a live document into Markdown is done in the page, because that is
# where the structure still exists as elements rather than as text.
markdownScript = r"""(() => {
    const lLines = [];
    const inline = el => (el.innerText || "").trim().replace(/\s+/g, " ");
    const walk = (elNode, iListDepth) => {
        for (const elChild of Array.from(elNode.children)) {
            const sTag = elChild.tagName.toLowerCase();
            const sText = inline(elChild);
            if (/^h[1-6]$/.test(sTag)) {
                if (sText) lLines.push("\n" + "#".repeat(parseInt(sTag[1], 10)) + " " + sText + "\n");
            } else if (sTag === "p") {
                if (sText) lLines.push(sText + "\n");
            } else if (sTag === "li") {
                if (sText) lLines.push("  ".repeat(iListDepth) + "- " + sText);
            } else if (sTag === "ul" || sTag === "ol") {
                walk(elChild, iListDepth + 1);
                lLines.push("");
            } else if (sTag === "blockquote") {
                if (sText) lLines.push("> " + sText + "\n");
            } else if (sTag === "pre") {
                lLines.push("```\n" + (elChild.innerText || "") + "\n```\n");
            } else if (sTag === "table") {
                for (const elRow of Array.from(elChild.rows)) {
                    const lCells = Array.from(elRow.cells).map(el => inline(el) || " ");
                    lLines.push("| " + lCells.join(" | ") + " |");
                    if (elRow.rowIndex === 0) {
                        lLines.push("|" + lCells.map(() => " --- ").join("|") + "|");
                    }
                }
                lLines.push("");
            } else if (sTag === "a" && elChild.href) {
                if (sText) lLines.push("[" + sText + "](" + elChild.href + ")");
            } else if (sTag === "img") {
                const sAlt = elChild.getAttribute("alt");
                lLines.push("![" + (sAlt === null ? "" : sAlt) + "](" + (elChild.src || "") + ")");
            } else if (["script", "style", "noscript"].indexOf(sTag) === -1) {
                walk(elChild, iListDepth);
            }
        }
    };
    const elRoot = document.querySelector("main, [role=main], article") || document.body;
    lLines.push("# " + (document.title || location.href) + "\n");
    lLines.push("Source: " + location.href + "\n");
    walk(elRoot, 0);
    return lLines.join("\n").replace(/\n{3,}/g, "\n\n");
})()"""

textScript = r"""(() => {
    const elRoot = document.querySelector("main, [role=main], article") || document.body;
    return (document.title || location.href) + "\n" + location.href + "\n\n" +
        (elRoot.innerText || "");
})()"""

htmlScript = "document.documentElement.outerHTML"


def saveDocument(cdpSession, sSourcePath, sTargetPath, sFormat):
    """Write the focused page to disk in the chosen format."""
    from . import capture
    from pathlib import Path as PathClass

    logSection(f"Command: save as {sFormat}")
    if sFormat in capture.dCaptures:
        # The four the protocol produces are captured rather than derived.
        pathTarget = capture.capture(cdpSession, sFormat, PathClass(sTargetPath))
        return {
            "characters": pathTarget.stat().st_size,
            "format": sFormat,
            "name": pathTarget.name,
            "path": str(pathTarget),
            "pageUrl": "",
        }
    dTarget, sSessionId = cdpSession.findActivePageSession()
    sPageUrl = dTarget.get("url", "")
    homerLog.info(f"Saving {abbreviate(sPageUrl, 200)} as {sFormat} to {sTargetPath}")

    if sFormat == "md":
        sBody = cdpSession.evaluate(sSessionId, markdownScript, extractTimeoutSeconds) or ""
    elif sFormat == "txt":
        sBody = cdpSession.evaluate(sSessionId, textScript, extractTimeoutSeconds) or ""
    else:
        sBody = cdpSession.evaluate(sSessionId, htmlScript, extractTimeoutSeconds) or ""
        if not sBody.lstrip().lower().startswith("<!doctype"):
            sBody = "<!doctype html>\n" + sBody

    if sFormat == "docx":
        # Word is produced by converting the page's markup, since nothing in a
        # browser writes Word directly.
        from . import convert as convertModule
        from . import paths as pathsModule

        pathHtml = pathsModule.getTempFolder() / "SaveAs.htm"
        pathHtml.write_text(sBody, encoding="utf-8-sig", newline="\r\n")
        pathPandoc = convertModule.findPandoc()
        if not pathPandoc:
            raise RuntimeError(
                "Saving as a Word document needs pandoc, which was not found. "
                "Install it from https://pandoc.org, or save as a web page instead."
            )
        convertModule.runConverter(
            [str(pathPandoc), str(pathHtml), "-o", sTargetPath], Path(sTargetPath), "pandoc")
        homerLog.info(f"Wrote {sTargetPath}")
        return {"characters": len(sBody), "format": sFormat,
                "name": Path(sTargetPath).name, "path": sTargetPath, "pageUrl": sPageUrl}

    pathTarget = Path(sTargetPath)
    # UTF-8 with a byte order mark and Windows line endings, matching every
    # other text file this project writes.
    pathTarget.write_text(sBody, encoding="utf-8-sig", newline="\r\n")
    homerLog.info(f"Wrote {pathTarget}, {pathTarget.stat().st_size} bytes")
    return {
        "characters": len(sBody),
        "format": sFormat,
        "name": pathTarget.name,
        "path": str(pathTarget),
        "pageUrl": sPageUrl,
    }

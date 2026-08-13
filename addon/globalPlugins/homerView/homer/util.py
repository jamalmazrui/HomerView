"""Homer.Util, ported from Util.cs.

The small operations that every Homer program needs and that Python does not
quite provide: bytes as a phrase a person would say, singular and plural
agreement, quoting and unquoting, comparison that ignores case and accents,
line-ending conversion, and the line operations the Lbc text controls offer.

The C# original is a static class in the Homer namespace, reached as
Util.formatBytes. Python has no need of the class: a module is already the
container a namespace provides, so this is homer.util.formatBytes. That is the
one structural difference between the two ports, and it applies throughout the
package.

Names are kept as they are in C#, so a person reading one and writing the other
does not have to translate. Where Python's own library does the same job better,
that is used underneath rather than reimplemented.
"""

import re
import unicodedata

sEndOfDocument = "\r\n----------\r\nEnd of Document\r\n"
sSectionBreak = "\r\n----------\r\n\f\r\n"


def formatBytes(lBytes):
    """A size as a person would say it rather than as a number of bytes."""
    try:
        nBytes = float(lBytes)
    except (TypeError, ValueError):
        return ""
    for sUnit, nLimit in (("bytes", 1024.0), ("KB", 1024.0 ** 2),
                          ("MB", 1024.0 ** 3), ("GB", 1024.0 ** 4)):
        if nBytes < nLimit:
            nValue = nBytes if sUnit == "bytes" else nBytes / (nLimit / 1024.0)
            if sUnit == "bytes":
                return f"{int(nValue)} bytes"
            return f"{nValue:.1f} {sUnit}".replace(".0 ", " ")
    return f"{nBytes / (1024.0 ** 4):.1f} TB"


def stringPlural(sItem, iCount):
    """Agree the noun with the number, which is what a spoken count needs."""
    return sItem if iCount == 1 else sItem + "s"


def stringQuote(sText):
    return '"' + str(sText or "") + '"'


def stringSingleQuote(sText):
    return "'" + str(sText or "") + "'"


def stringUnquote(sText):
    s = str(sText or "")
    return s[1:-1] if len(s) > 1 and s[0] == '"' and s[-1] == '"' else s


def stringSingleUnquote(sText):
    s = str(sText or "")
    return s[1:-1] if len(s) > 1 and s[0] == "'" and s[-1] == "'" else s


def stringEqual(s1, s2):
    """Equal ignoring case."""
    return str(s1 or "").casefold() == str(s2 or "").casefold()


def stringEquiv(s1, s2):
    """Equal ignoring case, accents and surrounding space.

    What a person means when they say two names are the same. Resume and
    résumé are the same word to a reader looking for it.
    """
    def fold(s):
        s = unicodedata.normalize("NFKD", str(s or "").strip())
        return "".join(c for c in s if not unicodedata.combining(c)).casefold()
    return fold(s1) == fold(s2)


def stringCapitalize(sText):
    s = str(sText or "")
    return s[:1].upper() + s[1:] if s else s


def stringProper(sText):
    return " ".join(stringCapitalize(s) for s in str(sText or "").split(" "))


def stringContains(sText, sMatch, bIgnoreCase=True):
    if bIgnoreCase:
        return str(sMatch or "").casefold() in str(sText or "").casefold()
    return str(sMatch or "") in str(sText or "")


def stringStartsWith(sText, sLead, bIgnoreCase=True):
    if bIgnoreCase:
        return str(sText or "").casefold().startswith(str(sLead or "").casefold())
    return str(sText or "").startswith(str(sLead or ""))


def stringEndsWith(sText, sTrail, bIgnoreCase=True):
    if bIgnoreCase:
        return str(sText or "").casefold().endswith(str(sTrail or "").casefold())
    return str(sText or "").endswith(str(sTrail or ""))


def stringLead(sText, sLead, bIgnoreCase=True):
    """Ensure the text begins with the lead, adding it when it does not."""
    s = str(sText or "")
    return s if stringStartsWith(s, sLead, bIgnoreCase) else str(sLead or "") + s


def stringTrail(sText, sTrail, bIgnoreCase=True):
    s = str(sText or "")
    return s if stringEndsWith(s, sTrail, bIgnoreCase) else s + str(sTrail or "")


def stringChopLeft(sText, iCount):
    return str(sText or "")[max(0, int(iCount)):]


def stringChopRight(sText, iCount):
    s = str(sText or "")
    iCount = max(0, int(iCount))
    return s[:-iCount] if iCount else s


def stringPadLeft(sText, iLength, sChar=" "):
    s = str(sText or "")
    return s.rjust(int(iLength), (sChar or " ")[0])


def stringPadRight(sText, iLength, sChar=" "):
    s = str(sText or "")
    return s.ljust(int(iLength), (sChar or " ")[0])


def stringReplaceAll(sText, sMatch, sReplace):
    return str(sText or "").replace(str(sMatch or ""), str(sReplace or ""))


def stringCount(sText, sChar):
    return str(sText or "").count(str(sChar or ""))


def stringTrimWhiteSpace(sText):
    """Collapse every run of whitespace to one space, and trim the ends."""
    return " ".join(str(sText or "").split())


def stringConvertToWinLineBreak(sText):
    s = str(sText or "").replace("\r\n", "\n").replace("\r", "\n")
    return s.replace("\n", "\r\n")


def stringConvertToUnixLineBreak(sText):
    return str(sText or "").replace("\r\n", "\n").replace("\r", "\n")


def stringConvertToMacLineBreak(sText):
    return stringConvertToUnixLineBreak(sText).replace("\n", "\r")


def stringConvertQuotes(sText):
    """Turn the typographic quotes and dashes into their plain equivalents.

    Text copied from a word processor carries characters a plain field or a
    command line will not accept, and a reader pasting it should not have to
    know that.
    """
    dPlain = {
        "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
        "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
        "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2026": "...",
        "\u00a0": " ",
    }
    s = str(sText or "")
    for sFrom, sTo in dPlain.items():
        s = s.replace(sFrom, sTo)
    return s


# --- Line operations, which the Lbc text controls offer ---------------------
#
# Each takes a list of lines and returns a list of lines, so they compose and
# so a control can apply any of them without knowing which it has.


def sortLines(lLines):
    return sorted(lLines, key=lambda s: s.casefold())


def reverseLines(lLines):
    return list(reversed(lLines))


def uniqueLines(lLines):
    """Remove repeats, keeping the first of each and the original order."""
    setSeen, lKept = set(), []
    for s in lLines:
        sKey = s.strip().casefold()
        if sKey in setSeen:
            continue
        setSeen.add(sKey)
        lKept.append(s)
    return lKept


def numberLines(lLines):
    iWidth = len(str(len(lLines)))
    return [f"{i:>{iWidth}}. {s}" for i, s in enumerate(lLines, 1)]


def trimBlankLines(lLines):
    return [s for s in lLines if s.strip()]


def createObject(sProgId):
    """Create a COM object by its programmatic identifier.

    The C# original wraps Activator.CreateInstance. Here it needs comtypes,
    which NVDA carries, and it is kept because a Homer program that drives
    Microsoft Office reaches for it and expects the same name.
    """
    try:
        import comtypes.client

        return comtypes.client.CreateObject(sProgId)
    except Exception:
        return None

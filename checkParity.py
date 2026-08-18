"""Measures how far the JAWS command set is from the NVDA one.

WHY THIS EXISTS. Parity was ASSERTED for weeks and never MEASURED, and two
commands -- Yield with Pattern among them -- turned out to be on NVDA and
missing from JAWS the whole time. A claim nobody can check is not a claim worth
making, so this counts instead.

HOW IT JUDGES. An NVDA command is NOT a gap when it is on the JAWS menu under
any name, or when JAWS PROVIDES IT ITSELF -- there is no point adding a
HomerView key for Next Paragraph when JAWS already has one, and doing so would
take a key the reader already knows. Those two lists are below and are meant to
be argued with: if something in "native" turns out not to be native, move it.

Run it after adding any command to either side.
"""
import io, os, re, sys

# Paths relative to THIS FILE, so it runs from anywhere -- including from the
# project root by double-clicking it, which is how it will actually be used.
sHere = os.path.dirname(os.path.abspath(__file__))
cmds = io.open(os.path.join(sHere, "addon", "globalPlugins", "homerView", "commands.py"), encoding="utf-8-sig", newline="").read()
jss = io.open(os.path.join(sHere, "jaws", "HomerView.jss"), encoding="utf-8-sig", newline="").read()
i = jss.index('Let sTable = "')
jaws = set()
for k, l in enumerate(jss[i:].split("\r\n")):
    if k and not l.lstrip().startswith('+ "\\7"'):
        break
    m = re.search(r'"((?:[^"\\]|\\.)*)"\s*$', l)
    if m:
        jaws.add(m.group(1).split("\\t")[0].split(",")[0].strip().lower())

# JAWS already provides these itself, so HomerView adding them would duplicate
# a key the reader already has.
native = {
 "next paragraph", "prior paragraph", "next sentence", "prior sentence",
 "say time", "voice faster", "voice louder", "voice slower", "voice softer",
 "toggle punctuation", "toggle reading", "list headings", "list links",
 "list form fields", "list elements", "forward find", "say position",
 "select chunk", "say chunk", "go to percent", "go to percent again",
 "next same kind", "prior same kind", "next different kind", "prior different kind",
 "speech settings", "say selected", "copy line",
}
# Different names for something JAWS already has on the menu.
alias = {
 "check accessibility": "check accessibility with axe",
 "check with axe": "check accessibility with axe",
 "check with equal access": "check accessibility with ibm",
 "report accessibility": "check accessibility with axe",
 "alternate menu": "alternate menu",
 "hotkey summary": "hot key help",
 "hotkey document": "hot key help",
 "jump to main": "jump to probable main",
 "yield with regular expression": "yield with pattern",
 "reverse find": "reverse find for text",
}
nvda = {}
for m in re.finditer(r'\("(\w+)",\s*"([^"]+)"', cmds):
    nvda[m.group(2).strip().lower()] = m.group(2)

gaps = []
for low, label in sorted(nvda.items()):
    if low in jaws or alias.get(low) in jaws or low in native or low in alias and alias[low] in jaws:
        continue
    if low in native:
        continue
    gaps.append(label)
lOut = []
def say(sLine=""):
    print(sLine)
    lOut.append(sLine)

say("NVDA commands: %d" % len(nvda))
say("Present on JAWS or provided by JAWS itself: %d" % (len(nvda) - len(gaps)))
say()
say("GENUINE GAPS -- on NVDA, absent from JAWS (%d):" % len(gaps))
for g in gaps:
    say("   " + g)

# The log goes beside the script, as every script in this project does.
pathLog = os.path.join(sHere, "checkParity.log")
with io.open(pathLog, "w", encoding="utf-8", newline="") as oFile:
    oFile.write("checkParity\r\n")
    oFile.write("  script:  %s\r\n" % os.path.abspath(__file__))
    oFile.write("  python:  %s\r\n" % sys.version.split()[0])
    oFile.write("  run in:  %s\r\n" % os.getcwd())
    oFile.write("\r\n".join(lOut) + "\r\n")
print()
print("Written to " + pathLog)

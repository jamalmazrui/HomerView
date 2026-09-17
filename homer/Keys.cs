// Keys.cs -- part of the shared Homer toolkit (namespace Homer).
//
// ONE SPELLING FOR A KEY, AND ONE PLACE THAT KNOWS EVERY OTHER SPELLING.
//
// Jamal's rule, made universal on 17 September 2026: Homer writes a key the way
// Freedom Scientific writes it. Blind Windows users have been reading Vispero's
// key names for twenty years, so "Alt+Shift+Apostrophe" reads the way they
// expect and "Alt+Shift+'" does not.
//
// The vocabulary below is not invented. It was taken from JAWS 2026's own
// default.jkm, 410 KB of it, by listing every key name the file actually uses.
// Where that file is inconsistent with itself -- and it is: Ctrl, CTRL and
// Control all appear, as do SemiColon and Semicolon, Backspace and BackSpace --
// Homer picks one and keeps to it.
//
// THREE HOMER RULES ON TOP OF THE FREEDOM SCIENTIFIC ONES
//
//   1. MODIFIERS IN ALPHABETICAL ORDER: Alt, Control, Shift, Windows. So
//      "Alt+Control+Shift+H", never "Control+Alt+Shift+H". A reader scanning a
//      list of hotkeys should not have to hold two orderings in mind, and a
//      program comparing two keys should not have to sort them first.
//
//   2. CONTROL IS SPELLED OUT. Never Ctrl. It is read aloud as often as it is
//      read on screen, and a screen reader says "control" for both.
//
//   3. THE SCREEN READER KEY IS "JAWS" OR "NVDA". JAWS's own files say
//      "JAWSKey", which is a file format detail rather than something to read
//      to somebody. Homer writes "Alt+JAWS+F10", and toJawsKeyMap puts the
//      "Key" back on the way into a .jkm. On both readers that key is usually
//      Insert or CapsLock, and naming the screen reader rather than the
//      physical key is what lets one document serve both.
//
// WHAT THIS CLASS IS FOR
//
// A Homer program writes a key once, in Homer spelling, and asks this class for
// whatever a particular interface wants:
//
//   toJawsKeyMap     "Alt+JAWSKey+F10"      for a .jkm file
//   toNvdaGesture    "kb:alt+shift+a"       for an NVDA gesture binding
//   toWinFormsText   "Alt+Shift+A"          for a WinForms menu shortcut label
//   toWinFormsKeys   an int matching System.Windows.Forms.Keys
//   toWx             "Alt+Ctrl+Shift+A"     for a wxPython accelerator
//   toInnoHotKey     "alt+ctrl+shift+h"     for Inno Setup's HotKey: directive
//
// Each of those wants something slightly different, and every one of those
// small differences has cost this project an afternoon at some point. Inno
// wants ctrl; wx wants Ctrl; NVDA wants lower case and its own modifier name;
// JAWS wants JAWSKey; WinForms wants an enum. None of that belongs in an
// application.
//
// THE PARSER IS FORGIVING AND THE WRITER IS NOT. parse accepts Ctrl, CTRL,
// control, JAWSKey, Insert, Grave, apostrophe and the rest, because keys arrive
// from files people have edited. Everything it returns is in Homer spelling and
// Homer order, because that is what gets written back.

using System;
using System.Collections.Generic;
using System.Text;

namespace Homer {

public static class Keys
{
    // --- The modifiers, in Homer order -------------------------------------
    //
    // Alphabetical, and the order is the point: sorting them here means no
    // caller ever has to, and two keys written by two programs compare equal.
    public static readonly string[] Modifiers =
        new string[] { "Alt", "Control", "JAWS", "NVDA", "Shift", "Windows" };

    // The screen reader modifiers sort with the rest alphabetically, which puts
    // JAWS and NVDA between Control and Shift. That is deliberate: they are
    // modifiers like any other and reading them in a fixed place is the whole
    // benefit.

    // --- Every spelling a key arrives in, mapped to the Homer one ----------
    //
    // Taken from JAWS 2026's default.jkm. The left-hand side is lower case
    // because matching is case-insensitive; the right-hand side is what Homer
    // writes.
    private static readonly Dictionary<string, string> dCanonical = build();

    // A LOCAL FUNCTION WAS WRONG HERE, AND THE COMPILER SAID SO.
    //
    // This started life as a local function inside build(), which reads
    // better and does not compile: the build uses
    // Framework64\\v4.0.30319\\csc.exe, which is the LEGACY C# 5 compiler
    // rather than Roslyn. Local functions are C# 7, and the error it gives
    // -- "} expected" on the line, then forty complaints about methods
    // needing return types -- points at the brace and not at the version.
    //
    // So nothing in the shared classes may use anything newer than C# 5:
    // no local functions, no string interpolation, no null-conditional, no
    // expression-bodied members, no nameof. Inix.cs and Web.cs already keep
    // to that, which is why they compiled and this did not.
    private static void put(Dictionary<string, string> d, string sHomer,
        params string[] lAliases)
    {
        d[sHomer] = sHomer;
        foreach (string sAlias in lAliases) d[sAlias] = sHomer;
    }

    private static Dictionary<string, string> build()
    {
        var d = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        // Modifiers. Ctrl and CTRL both appear in the factory file; Homer
        // writes Control. JAWSKey is the file spelling of JAWS.
        put(d, "Alt");
        put(d, "Control", "Ctrl", "Ctl");
        put(d, "Shift");
        put(d, "Windows", "WindowsKey", "Win", "LeftWindows", "RightWindows");
        put(d, "JAWS", "JAWSKey", "JawsKey");
        put(d, "NVDA", "NVDAKey");

        // Keys that carry a name rather than a character. Spellings on the
        // right are the variants the factory file uses for the same key.
        put(d, "Apostrophe", "Quote", "SingleQuote", "'");
        put(d, "Applications", "ContextMenu", "Menu", "AppsKey");
        put(d, "Backslash", "\\");
        put(d, "Backspace", "BackSpace", "BkSp");
        put(d, "CapsLock", "Caps");
        put(d, "Comma", ",");
        put(d, "Dash", "Minus", "Hyphen", "-");
        put(d, "Delete", "Del");
        put(d, "DownArrow", "Down", "Down Arrow");
        put(d, "End");
        put(d, "Enter", "Return");
        put(d, "Equals", "Equal", "=");
        put(d, "Escape", "Esc");
        put(d, "GraveAccent", "Grave", "Accent", "BackQuote", "`");
        put(d, "Home");
        put(d, "Insert", "Ins");
        put(d, "LeftArrow", "Left", "Left Arrow");
        put(d, "LeftBracket", "OpenBracket", "[");
        put(d, "NumPadEnter");
        put(d, "NumPadMinus", "NumpadMinus");
        put(d, "NumPadPlus", "NumpadPlus");
        put(d, "NumPadSlash", "NumpadSlash");
        put(d, "NumPadStar", "NumpadStar", "NumPadMultiply");
        put(d, "PageDown", "PgDn");
        put(d, "PageUp", "PgUp");
        put(d, "Period", "Dot", "FullStop", ".");
        put(d, "RightArrow", "Right", "Right Arrow");
        put(d, "RightBracket", "CloseBracket", "]");
        put(d, "ScrollLock");
        put(d, "SemiColon", "Semicolon", ";");
        put(d, "Slash", "ForwardSlash", "/");
        put(d, "Space", "Spacebar", "SpaceBar");
        put(d, "Tab");
        put(d, "UpArrow", "Up", "Up Arrow");
        for (int i = 1; i <= 24; i++) put(d, "F" + i);
        return d;
    }

    // --- What each interface calls the same key ----------------------------
    //
    // Only the keys whose name differs from the Homer one appear here. A key
    // absent from a table is written as Homer writes it, which is true of every
    // letter, every digit and every function key.
    private static readonly Dictionary<string, string> dWx = wxTable();
    private static Dictionary<string, string> wxTable()
    {
        var d = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        d["Apostrophe"] = "'";      d["Backslash"] = "\\";   d["Comma"] = ",";
        d["Dash"] = "-";            d["DownArrow"] = "DOWN"; d["Equals"] = "=";
        d["GraveAccent"] = "`";     d["LeftArrow"] = "LEFT"; d["LeftBracket"] = "[";
        d["Period"] = ".";          d["RightArrow"] = "RIGHT";
        d["RightBracket"] = "]";    d["SemiColon"] = ";";    d["Slash"] = "/";
        d["UpArrow"] = "UP";        d["PageDown"] = "PGDN";  d["PageUp"] = "PGUP";
        d["Backspace"] = "BACK";    d["Escape"] = "ESC";     d["Applications"] = "MENU";
        d["NumPadEnter"] = "NUMPAD_ENTER";
        d["NumPadMinus"] = "NUMPAD_SUBTRACT";
        d["NumPadPlus"] = "NUMPAD_ADD";
        d["NumPadSlash"] = "NUMPAD_DIVIDE";
        d["NumPadStar"] = "NUMPAD_MULTIPLY";
        return d;
    }

    private static readonly Dictionary<string, string> dNvda = nvdaTable();
    private static Dictionary<string, string> nvdaTable()
    {
        var d = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        d["Apostrophe"] = "'";      d["Backslash"] = "\\";   d["Comma"] = ",";
        d["Dash"] = "-";            d["DownArrow"] = "downArrow";
        d["Equals"] = "=";          d["GraveAccent"] = "`";
        d["LeftArrow"] = "leftArrow";   d["LeftBracket"] = "[";
        d["Period"] = ".";          d["RightArrow"] = "rightArrow";
        d["RightBracket"] = "]";    d["SemiColon"] = ";";    d["Slash"] = "/";
        d["UpArrow"] = "upArrow";   d["PageDown"] = "pageDown";
        d["PageUp"] = "pageUp";     d["Applications"] = "applications";
        d["Backspace"] = "backspace";
        d["NumPadEnter"] = "numpadEnter";
        d["NumPadMinus"] = "numpadMinus";
        d["NumPadPlus"] = "numpadPlus";
        d["NumPadSlash"] = "numpadDivide";
        d["NumPadStar"] = "numpadMultiply";
        return d;
    }

    // System.Windows.Forms.Keys values, by name, so an application can set a
    // menu shortcut without a switch of its own. The numbers are the enum's,
    // and they are the same as the Win32 virtual key codes they came from.
    private static readonly Dictionary<string, int> dWinForms = winFormsTable();
    private static Dictionary<string, int> winFormsTable()
    {
        var d = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        d["Backspace"] = 8;      d["Tab"] = 9;          d["Enter"] = 13;
        d["Escape"] = 27;        d["Space"] = 32;       d["PageUp"] = 33;
        d["PageDown"] = 34;      d["End"] = 35;         d["Home"] = 36;
        d["LeftArrow"] = 37;     d["UpArrow"] = 38;     d["RightArrow"] = 39;
        d["DownArrow"] = 40;     d["Insert"] = 45;      d["Delete"] = 46;
        d["Applications"] = 93;  d["NumPadStar"] = 106; d["NumPadPlus"] = 107;
        d["NumPadEnter"] = 13;   d["NumPadMinus"] = 109;
        d["NumPadSlash"] = 111;  d["ScrollLock"] = 145; d["CapsLock"] = 20;
        d["SemiColon"] = 186;    d["Equals"] = 187;     d["Comma"] = 188;
        d["Dash"] = 189;         d["Period"] = 190;     d["Slash"] = 191;
        d["GraveAccent"] = 192;  d["LeftBracket"] = 219;
        d["Backslash"] = 220;    d["RightBracket"] = 221;
        d["Apostrophe"] = 222;
        for (int i = 1; i <= 24; i++) d["F" + i] = 111 + i;   // F1 is 112
        for (char c = 'A'; c <= 'Z'; c++) d[c.ToString()] = (int)c;
        for (char c = '0'; c <= '9'; c++) d[c.ToString()] = (int)c;
        return d;
    }

    // --- Reading a key in ---------------------------------------------------

    /// <summary>
    /// One key, in Homer spelling and Homer order, from any spelling.
    ///
    /// Accepts what files and people actually contain: Ctrl, CTRL, JAWSKey,
    /// Grave, apostrophe, "Down Arrow", and modifiers in any order. Returns an
    /// empty string only for empty input; an unrecognised key name is passed
    /// through as given, because a key this table has not heard of is more
    /// likely to be new than to be wrong.
    /// </summary>
    public static string parse(string sKey)
    {
        if (string.IsNullOrEmpty(sKey)) return "";
        var lModifiers = new List<string>();
        string sMain = "";
        string[] lRaw = sKey.Split('+');
        var lParts = new List<string>();
        foreach (string sRaw in lRaw)
        {
            string sPart = sRaw.Trim();
            if (sPart == "") continue;
            string sCanonical;
            if (!dCanonical.TryGetValue(sPart, out sCanonical))
            {
                // A single character is written as itself, upper cased, which
                // is how the factory file writes letters and digits.
                sCanonical = sPart.Length == 1 ? sPart.ToUpperInvariant() : sPart;
            }
            lParts.Add(sCanonical);
        }
        for (int i = 0; i < lParts.Count; i++)
        {
            bool bIsLast = (i == lParts.Count - 1);
            if (isModifier(lParts[i], bIsLast))
            {
                if (!lModifiers.Contains(lParts[i])) lModifiers.Add(lParts[i]);
            }
            else
            {
                sMain = lParts[i];
            }
        }
        lModifiers.Sort(StringComparer.OrdinalIgnoreCase);
        var oBuilt = new StringBuilder();
        foreach (string sModifier in lModifiers)
        {
            oBuilt.Append(sModifier);
            oBuilt.Append('+');
        }
        oBuilt.Append(sMain);
        return oBuilt.ToString();
    }

    /// <summary>
    /// Whether a part is being used as a modifier.
    ///
    /// DECIDED BY POSITION, NOT BY A LIST, AND A TEST CAUGHT WHY. The first
    /// version asked only whether the name was in Modifiers, so parsing
    /// "Insert+DownArrow" -- which is how JAWS writes a great many of its own
    /// keys -- silently returned "DownArrow" and threw the Insert away. A
    /// converter that quietly drops half a key is worse than one that refuses.
    ///
    /// Insert and CapsLock are modifiers in a screen reader key map and keys in
    /// their own right, and the only thing that tells them apart is whether
    /// something follows. Homer prefers JAWS or NVDA to either, but it does not
    /// discard what it was given.
    /// </summary>
    public static bool isModifier(string sPart, bool bIsLast)
    {
        if (bIsLast) return false;
        foreach (string sModifier in Modifiers)
            if (string.Equals(sModifier, sPart, StringComparison.OrdinalIgnoreCase))
                return true;
        return string.Equals(sPart, "Insert", StringComparison.OrdinalIgnoreCase)
            || string.Equals(sPart, "CapsLock", StringComparison.OrdinalIgnoreCase);
    }

    public static bool isModifier(string sPart)
    {
        return isModifier(sPart, false);
    }

    /// <summary>Whether two keys are the same key, however each was written.</summary>
    public static bool same(string sOne, string sOther)
    {
        return string.Equals(parse(sOne), parse(sOther), StringComparison.OrdinalIgnoreCase);
    }

    private static void split(string sKey, out List<string> lModifiers, out string sMain)
    {
        lModifiers = new List<string>();
        sMain = "";
        string[] lParts = parse(sKey).Split('+');
        for (int i = 0; i < lParts.Length; i++)
        {
            if (lParts[i] == "") continue;
            if (i == lParts.Length - 1) sMain = lParts[i];
            else lModifiers.Add(lParts[i]);
        }
    }

    // --- Writing a key out, once per interface that wants it differently ----

    /// <summary>
    /// For a JAWS .jkm file. The only difference from Homer spelling is that
    /// JAWS writes JAWSKey where Homer writes JAWS, and that an NVDA modifier
    /// has no meaning in a JAWS file and is dropped.
    /// </summary>
    public static string toJawsKeyMap(string sKey)
    {
        List<string> lModifiers; string sMain;
        split(sKey, out lModifiers, out sMain);
        var oBuilt = new StringBuilder();
        foreach (string sModifier in lModifiers)
        {
            if (sModifier == "NVDA") continue;
            oBuilt.Append(sModifier == "JAWS" ? "JAWSKey" : sModifier);
            oBuilt.Append('+');
        }
        oBuilt.Append(sMain);
        return oBuilt.ToString();
    }

    /// <summary>
    /// For an NVDA gesture: lower case, its own key names, and the "kb:"
    /// prefix NVDA expects. A JAWS modifier has no meaning here and is dropped.
    /// </summary>
    public static string toNvdaGesture(string sKey)
    {
        List<string> lModifiers; string sMain;
        split(sKey, out lModifiers, out sMain);
        var oBuilt = new StringBuilder("kb:");
        foreach (string sModifier in lModifiers)
        {
            if (sModifier == "JAWS") continue;
            oBuilt.Append(sModifier == "NVDA" ? "NVDA" : sModifier.ToLowerInvariant());
            oBuilt.Append('+');
        }
        string sNamed;
        oBuilt.Append(dNvda.TryGetValue(sMain, out sNamed) ? sNamed : sMain.ToLowerInvariant());
        return oBuilt.ToString();
    }

    /// <summary>
    /// For a WinForms menu shortcut label. Homer spelling exactly, with the
    /// screen reader modifiers dropped, since a menu in a Homer application is
    /// read by whichever screen reader the person uses.
    /// </summary>
    public static string toWinFormsText(string sKey)
    {
        List<string> lModifiers; string sMain;
        split(sKey, out lModifiers, out sMain);
        var oBuilt = new StringBuilder();
        foreach (string sModifier in lModifiers)
        {
            if (sModifier == "JAWS" || sModifier == "NVDA") continue;
            oBuilt.Append(sModifier);
            oBuilt.Append('+');
        }
        oBuilt.Append(sMain);
        return oBuilt.ToString();
    }

    /// <summary>
    /// The System.Windows.Forms.Keys value for a key, modifiers included, as an
    /// int so this file needs no reference to Windows Forms. Cast it at the
    /// call site: (Keys)Homer.Keys.toWinFormsKeys("Alt+Shift+A").
    ///
    /// Returns 0 when the key is not one Windows has, which is the same answer
    /// Keys.None gives and means "do not set a shortcut".
    /// </summary>
    public static int toWinFormsKeys(string sKey)
    {
        List<string> lModifiers; string sMain;
        split(sKey, out lModifiers, out sMain);
        int iValue;
        if (!dWinForms.TryGetValue(sMain, out iValue)) return 0;
        foreach (string sModifier in lModifiers)
        {
            if (sModifier == "Shift") iValue |= 0x00010000;        // Keys.Shift
            else if (sModifier == "Control") iValue |= 0x00020000; // Keys.Control
            else if (sModifier == "Alt") iValue |= 0x00040000;     // Keys.Alt
            // Windows, JAWS and NVDA have no Keys value. A shortcut needing
            // one of those is not a WinForms shortcut.
            else return 0;
        }
        return iValue;
    }

    /// <summary>
    /// For a wxPython accelerator string. wx wants Ctrl rather than Control and
    /// its own names for the named keys, and it is the one place Homer's
    /// spell-it-out rule is set aside, because wx will not parse Control.
    /// </summary>
    public static string toWx(string sKey)
    {
        List<string> lModifiers; string sMain;
        split(sKey, out lModifiers, out sMain);
        var oBuilt = new StringBuilder();
        foreach (string sModifier in lModifiers)
        {
            if (sModifier == "JAWS" || sModifier == "NVDA") continue;
            oBuilt.Append(sModifier == "Control" ? "Ctrl" : sModifier);
            oBuilt.Append('+');
        }
        string sNamed;
        oBuilt.Append(dWx.TryGetValue(sMain, out sNamed) ? sNamed : sMain.ToUpperInvariant());
        return oBuilt.ToString();
    }

    /// <summary>
    /// For Inno Setup's HotKey: directive on a desktop shortcut. Lower case,
    /// ctrl rather than control.
    ///
    /// WHAT THIS IS FOR, and it is worth saying. A Windows shortcut key is the
    /// one key a Homer program can offer that works whatever is running, so
    /// every Homer tool takes one -- and that is why Alt+Control+key and
    /// Alt+Control+Shift+key are reserved for them and are never used for an
    /// ordinary binding. HomerScribe holds Alt+Control+H and HomerView holds
    /// Alt+Control+Shift+H, and the two collided once because each script
    /// spelled its key out rather than defining it once. Define it once.
    /// </summary>
    public static string toInnoHotKey(string sKey)
    {
        List<string> lModifiers; string sMain;
        split(sKey, out lModifiers, out sMain);
        var oBuilt = new StringBuilder();
        foreach (string sModifier in lModifiers)
        {
            if (sModifier == "JAWS" || sModifier == "NVDA") continue;
            oBuilt.Append(sModifier == "Control" ? "ctrl" : sModifier.ToLowerInvariant());
            oBuilt.Append('+');
        }
        oBuilt.Append(sMain.ToLowerInvariant());
        return oBuilt.ToString();
    }

    /// <summary>
    /// How a key should be read aloud, for a program that speaks one directly.
    /// The Homer spelling already reads well, so this only separates the words
    /// in a run-together name: DownArrow becomes "Down Arrow", NumPadStar
    /// becomes "Num Pad Star". A screen reader does that unevenly on its own.
    /// </summary>
    public static string toSpoken(string sKey)
    {
        var oBuilt = new StringBuilder();
        foreach (char c in parse(sKey))
        {
            if (char.IsUpper(c) && oBuilt.Length > 0)
            {
                char cLast = oBuilt[oBuilt.Length - 1];
                if (cLast != '+' && cLast != ' ' && !char.IsUpper(cLast)) oBuilt.Append(' ');
            }
            oBuilt.Append(c == '+' ? ' ' : c);
        }
        return oBuilt.ToString();
    }
}

} // namespace Homer

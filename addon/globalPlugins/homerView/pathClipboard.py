"""Putting a file on the clipboard as a file, not as its name.

Copying a path as text gives you the letters. Pasting that into an Outlook
message body types the letters into the message. What you wanted was the file
attached, and that is a different clipboard format: CF_HDROP, the one Windows
Explorer uses when you copy a file and paste it somewhere.

Any program that accepts a dropped file accepts this. Outlook attaches it. File
Explorer copies it into the folder. A mail client's compose window attaches it.
And a text box still gets the path as text, because both formats are put on the
clipboard at once and each program takes the one it understands.

Nothing here is specific to logs. It takes paths and puts them on the
clipboard, which is worth keeping general: the next thing worth attaching will
not be a log.
"""

import ctypes
from ctypes import wintypes

import addonHandler

from .logger import abbreviate, homerLog, logError

addonHandler.initTranslation()

CF_HDROP = 15
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


class DROPFILES(ctypes.Structure):
    """The header Windows expects in front of the file names.

    pFiles is where the names start, counted from the beginning of this
    structure. fWide says the names are wide characters rather than bytes,
    which they are, because a path can hold anything.
    """

    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL),
    ]


def copyPaths(lPaths):
    """Put files on the clipboard so another program can accept them as files.

    Both formats go on at once: the file list for anything that takes a
    dropped file, and the plain text for anything that does not. Neither
    program has to know what the other wanted.
    """
    lPaths = [str(s) for s in lPaths if s]
    if not lPaths:
        return False

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    # Every one of these has to be declared, and the reason is worth stating
    # because the failure is silent and looks like something else.
    #
    # ctypes assumes a function returns a C int, which is 32 bits, on every
    # platform. GlobalAlloc and GlobalLock return 64-bit handles and pointers
    # on 64-bit Windows. Undeclared, the top half of each is thrown away, and
    # what comes back is a truncated value that is not a valid handle. Then
    # GlobalLock fails, returns nothing, and memmove writes to address zero.
    #
    # Which is exactly what happened on a tester's machine: an access violation
    # writing 0x0000000000000000, from a line that was merely copying bytes.
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.OpenClipboard.argtypes = [wintypes.HWND]

    # The names, each ending in a null, and a second null after the last one.
    # That double ending is how Windows knows the list has finished.
    sNames = "\0".join(lPaths) + "\0\0"
    bNames = sNames.encode("utf-16-le")
    dropFiles = DROPFILES()
    dropFiles.pFiles = ctypes.sizeof(DROPFILES)
    dropFiles.fWide = True
    bBlock = bytes(dropFiles) + bNames

    if not user32.OpenClipboard(None):
        homerLog.warning("The clipboard could not be opened")
        return False
    try:
        user32.EmptyClipboard()

        # The clipboard takes ownership of what is put on it, so the memory is
        # allocated movable and never freed here. Freeing it would take the
        # clipboard's own data away underneath whatever pastes next.
        handleDrop = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(bBlock))
        if not handleDrop:
            homerLog.warning("The clipboard memory could not be allocated")
            return False
        pointerDrop = kernel32.GlobalLock(handleDrop)
        if not pointerDrop:
            kernel32.GlobalFree(handleDrop)
            homerLog.warning("The clipboard memory could not be locked")
            return False
        ctypes.memmove(pointerDrop, bBlock, len(bBlock))
        kernel32.GlobalUnlock(handleDrop)
        if not user32.SetClipboardData(CF_HDROP, handleDrop):
            kernel32.GlobalFree(handleDrop)
            homerLog.warning("The file list could not be put on the clipboard")
            return False

        # And the same thing as text, for a field that wants letters.
        sText = "\r\n".join(lPaths)
        bText = sText.encode("utf-16-le") + b"\x00\x00"
        handleText = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(bText))
        if not handleText:
            return True
        pointerText = kernel32.GlobalLock(handleText)
        if not pointerText:
            kernel32.GlobalFree(handleText)
            return True
        ctypes.memmove(pointerText, bText, len(bText))
        kernel32.GlobalUnlock(handleText)
        if not user32.SetClipboardData(CF_UNICODETEXT, handleText):
            kernel32.GlobalFree(handleText)
    except Exception:
        logError("Putting files on the clipboard raised")
        return False
    finally:
        user32.CloseClipboard()

    homerLog.info(f"Put {len(lPaths)} files on the clipboard: {abbreviate(str(lPaths), 300)}")
    return True

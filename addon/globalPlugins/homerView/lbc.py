"""Compatibility shim: lbc now lives in the shared Homer toolkit.

Left in place so existing imports keep working. New code should use
``from .homer import lbc`` so the dependency on the shared toolkit is visible.
"""

from .homer.lbc import *  # noqa: F401,F403
from .homer.lbc import (  # noqa: F401
    Dialog,
    afterScript,
    dialogChoose,
    dialogInfo,
    dialogConfirm,
    dialogInput,
    dialogOpenFile,
    dialogSaveFile,
    dialogShow,
    dialogText,
    getHostParent,
    readIniValue,
    writeIniValue,
)

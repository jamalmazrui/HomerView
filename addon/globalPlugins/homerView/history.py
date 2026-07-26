"""HomerView.db: what was opened, converted, scanned and downloaded.

A reading tool that keeps no record makes its user do the remembering. This
records the pages opened and the actions taken, so questions like "what was that
report I scanned on Tuesday" have an answer.

SQLite is used when it is available. Python includes the sqlite3 module in its
standard library, but an embedded interpreter can be built without the
underlying extension, so the import is attempted rather than assumed. When it is
missing, the same records go to a JSON lines file instead, which loses querying
but loses nothing else, and the log says plainly which store is in use. That is
better than a feature that silently does nothing.

Nothing here runs on the thread that drives speech. Every write is queued to the
worker like any other task.
"""

import json
import time
from datetime import datetime, timezone

from . import paths
from .logger import abbreviate, homerLog, logError

databaseFileName = "HomerView.db"
fallbackFileName = "HomerView.jsonl"
maximumRecentRows = 200

bSqliteAvailable = False
sqlite3 = None
try:
    import sqlite3 as sqlite3Module

    sqlite3 = sqlite3Module
    bSqliteAvailable = True
except Exception:
    bSqliteAvailable = False

createStatements = [
    """CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recordedUtc TEXT NOT NULL,
        kind TEXT NOT NULL,
        title TEXT,
        address TEXT,
        detail TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS eventsByKind ON events (kind, recordedUtc)",
    "CREATE INDEX IF NOT EXISTS eventsByAddress ON events (address)",
]


class HistoryStore:
    def __init__(self):
        self.bReady = False
        self.pathStore = None
        self.sBackend = "none"

    def open(self):
        if self.bReady:
            return True
        pathFolder = paths.getTempFolder().parent if False else None
        try:
            from . import logger

            # Beside the log, in local application data. A record of what was
            # opened is data rather than a preference: it is specific to this
            # machine, it grows, and it is of no use on another computer, so it
            # does not belong in a roaming profile.
            pathFolder = logger.pathLogFile.parent if logger.pathLogFile else paths.getTempFolder()
        except Exception:
            pathFolder = paths.getTempFolder()
        if bSqliteAvailable:
            self.pathStore = pathFolder / databaseFileName
            try:
                with sqlite3.connect(str(self.pathStore)) as connection:
                    for sStatement in createStatements:
                        connection.execute(sStatement)
                self.sBackend = "sqlite"
                self.bReady = True
                homerLog.info(f"History store: SQLite at {self.pathStore}")
                return True
            except Exception:
                logError("The SQLite history store could not be opened; falling back")
        self.pathStore = pathFolder / fallbackFileName
        self.sBackend = "jsonLines"
        self.bReady = True
        homerLog.warning(
            f"History store: JSON lines at {self.pathStore}. Python's sqlite3 module is "
            "unavailable in this NVDA build, so records are kept but cannot be queried."
        )
        return True

    def record(self, sKind, sTitle="", sAddress="", dDetail=None):
        """Add one event. Safe to call when the store never opened."""
        if not self.open():
            return False
        sRecorded = datetime.now(timezone.utc).isoformat(timespec="seconds")
        sDetail = json.dumps(dDetail or {}, ensure_ascii=False)
        try:
            if self.sBackend == "sqlite":
                with sqlite3.connect(str(self.pathStore)) as connection:
                    connection.execute(
                        "INSERT INTO events (recordedUtc, kind, title, address, detail) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (sRecorded, sKind, sTitle or "", sAddress or "", sDetail),
                    )
            else:
                with open(self.pathStore, "a", encoding="utf-8") as fFile:
                    fFile.write(
                        json.dumps(
                            {
                                "address": sAddress or "",
                                "detail": dDetail or {},
                                "kind": sKind,
                                "recordedUtc": sRecorded,
                                "title": sTitle or "",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
        except Exception:
            logError(f"The {sKind} event could not be recorded")
            return False
        homerLog.debug(f"Recorded {sKind}: {abbreviate(sTitle or sAddress, 160)}")
        return True

    def recent(self, sKind="", iLimit=40):
        """Return recent events, newest first."""
        if not self.open():
            return []
        try:
            if self.sBackend == "sqlite":
                with sqlite3.connect(str(self.pathStore)) as connection:
                    connection.row_factory = sqlite3.Row
                    if sKind:
                        cursor = connection.execute(
                            "SELECT * FROM events WHERE kind = ? ORDER BY id DESC LIMIT ?",
                            (sKind, iLimit),
                        )
                    else:
                        cursor = connection.execute(
                            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (iLimit,)
                        )
                    return [dict(row) for row in cursor.fetchall()]
            lRows = []
            with open(self.pathStore, "r", encoding="utf-8") as fFile:
                for sLine in fFile:
                    try:
                        dRow = json.loads(sLine)
                    except ValueError:
                        continue
                    if not sKind or dRow.get("kind") == sKind:
                        lRows.append(dRow)
            return list(reversed(lRows))[:iLimit]
        except Exception:
            logError("Recent events could not be read")
            return []

    def describe(self):
        return {
            "backend": self.sBackend,
            "path": str(self.pathStore) if self.pathStore else "",
            "sqliteAvailable": bSqliteAvailable,
        }


history = HistoryStore()

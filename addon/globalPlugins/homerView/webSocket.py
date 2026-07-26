"""Minimal loopback-only RFC 6455 client for the Microsoft Edge DevTools Protocol.

Only the standard library is used, so the add-on has no external dependencies.
One thread may block in receiveText while another calls sendText; sends are
serialized by a lock, and close from any thread unblocks a pending receive.
"""

import base64
import hashlib
import os
import socket
import struct
import threading
from urllib.parse import urlparse

from .logger import homerLog

handshakeTimeoutSeconds = 10.0
maximumHeaderBytes = 65536
opcodeBinary = 0x2
opcodeClose = 0x8
opcodeContinuation = 0x0
opcodePing = 0x9
opcodePong = 0xA
opcodeText = 0x1
webSocketGuid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketError(Exception):
    pass


class WebSocketClient:
    def __init__(self, sUrl):
        self.bClosed = False
        self.lockSend = threading.Lock()
        self.sUrl = sUrl
        self.socket = None

    def connect(self):
        parsed = urlparse(self.sUrl)
        if parsed.scheme != "ws":
            raise WebSocketError("Only ws connections are supported")
        if parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise WebSocketError("Non-loopback WebSocket endpoints are rejected")
        iPort = parsed.port or 80
        sPath = parsed.path or "/"
        if parsed.query:
            sPath += "?" + parsed.query
        homerLog.debug(f"WebSocket connecting to {parsed.hostname}:{iPort}{sPath}")
        self.socket = socket.create_connection((parsed.hostname, iPort), handshakeTimeoutSeconds)
        self.socket.settimeout(handshakeTimeoutSeconds)
        sKey = base64.b64encode(os.urandom(16)).decode("ascii")
        sRequest = (
            f"GET {sPath} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{iPort}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {sKey}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.socket.sendall(sRequest.encode("ascii"))
        sHeader = self._receiveUntil(b"\r\n\r\n").decode("iso-8859-1")
        if " 101 " not in sHeader.split("\r\n", 1)[0]:
            raise WebSocketError("Edge rejected the WebSocket upgrade")
        sExpected = base64.b64encode(
            hashlib.sha1((sKey + webSocketGuid).encode("ascii")).digest()
        ).decode("ascii")
        dHeaders = {}
        for sLine in sHeader.split("\r\n")[1:]:
            if ":" in sLine:
                sName, sValue = sLine.split(":", 1)
                dHeaders[sName.strip().lower()] = sValue.strip()
        if dHeaders.get("sec-websocket-accept") != sExpected:
            raise WebSocketError("Invalid WebSocket accept value")
        homerLog.debug("WebSocket handshake accepted")
        # The reader thread blocks indefinitely; close unblocks it.
        self.socket.settimeout(None)

    def close(self):
        if self.bClosed:
            return
        self.bClosed = True
        homerLog.debug("WebSocket closing")
        socketOpen = self.socket
        self.socket = None
        if not socketOpen:
            return
        try:
            self._sendFrame(b"", opcodeClose, socketOpen)
        except Exception:
            pass
        try:
            socketOpen.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            socketOpen.close()
        except Exception:
            pass

    def sendText(self, sText):
        self._sendFrame(sText.encode("utf-8"), opcodeText, self.socket)

    def receiveText(self):
        lParts = []
        iMessageOpcode = None
        while True:
            iByte1, iByte2 = self._receiveExact(2)
            bFinal = bool(iByte1 & 0x80)
            iOpcode = iByte1 & 0x0F
            bMasked = bool(iByte2 & 0x80)
            iLength = iByte2 & 0x7F
            if iLength == 126:
                iLength = struct.unpack("!H", self._receiveExact(2))[0]
            elif iLength == 127:
                iLength = struct.unpack("!Q", self._receiveExact(8))[0]
            bMask = self._receiveExact(4) if bMasked else b""
            bPayload = self._receiveExact(iLength)
            if bMasked:
                bPayload = bytes(iValue ^ bMask[iOffset % 4] for iOffset, iValue in enumerate(bPayload))
            if iOpcode == opcodeClose:
                homerLog.info("WebSocket received a close frame from Edge")
                raise WebSocketError("Edge closed the DevTools connection")
            if iOpcode == opcodePing:
                self._sendFrame(bPayload, opcodePong, self.socket)
                continue
            if iOpcode == opcodePong:
                continue
            if iOpcode in (opcodeText, opcodeBinary):
                iMessageOpcode = iOpcode
                lParts = [bPayload]
            elif iOpcode == opcodeContinuation:
                lParts.append(bPayload)
            else:
                continue
            if bFinal:
                if iMessageOpcode != opcodeText:
                    raise WebSocketError("Unexpected binary message")
                return b"".join(lParts).decode("utf-8")

    def _sendFrame(self, bPayload, iOpcode, socketTarget):
        if not socketTarget:
            raise WebSocketError("The WebSocket is not connected")
        iLength = len(bPayload)
        bHeader = bytes([0x80 | iOpcode])
        if iLength < 126:
            bHeader += bytes([0x80 | iLength])
        elif iLength <= 0xFFFF:
            bHeader += bytes([0x80 | 126]) + struct.pack("!H", iLength)
        else:
            bHeader += bytes([0x80 | 127]) + struct.pack("!Q", iLength)
        bMask = os.urandom(4)
        bMasked = bytes(iValue ^ bMask[iOffset % 4] for iOffset, iValue in enumerate(bPayload))
        with self.lockSend:
            socketTarget.sendall(bHeader + bMask + bMasked)

    def _receiveExact(self, iLength):
        bResult = b""
        while len(bResult) < iLength:
            socketOpen = self.socket
            if not socketOpen:
                raise WebSocketError("The WebSocket was closed")
            bPart = socketOpen.recv(iLength - len(bResult))
            if not bPart:
                raise WebSocketError("Unexpected end of the WebSocket stream")
            bResult += bPart
        return bResult

    def _receiveUntil(self, bMarker):
        bResult = b""
        while bMarker not in bResult:
            bPart = self.socket.recv(4096)
            if not bPart:
                raise WebSocketError("Unexpected end of the HTTP response")
            bResult += bPart
            if len(bResult) > maximumHeaderBytes:
                raise WebSocketError("The HTTP response header is too large")
        return bResult

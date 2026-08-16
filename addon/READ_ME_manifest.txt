manifest.ini is deliberately NOT in this archive.

It holds the version, and buildHomerView raises that version on every run.
Shipping a copy would put a stale number back into the project each time this
archive is unpacked, and the build would then produce a version already
released -- which tagRelease rightly refuses to publish.

Your manifest.ini in addon\ is the live one. Nothing here should replace it.

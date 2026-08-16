manifest.ini is deliberately NOT in this archive.

It holds the version, and buildHomerView raises that version on every run.
Shipping a copy of the file would put a stale number back into the project each
time this archive is unpacked -- which is exactly what happened: the version was
reset to 1.48.5, the build raised it to 1.48.6, and 1.48.6 had already been
released, so tagRelease refused to publish it.

Your manifest.ini in addon\ is the live one. Nothing here should replace it.
If a change to it is ever needed, it will be described in the message rather
than shipped as a file.

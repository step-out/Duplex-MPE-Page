#!/usr/bin/env python3
"""Preview the static homepage with byte-range support for seeking in audio."""
import argparse
import functools
import http.server
import re
from pathlib import Path


class SiteHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        path = Path(self.translate_path(self.path))
        header = self.headers.get("Range")
        if not header or not path.is_file():
            return super().send_head()
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
        if not match or not any(match.groups()):
            self.send_error(400, "Expected a single byte range")
            return None
        size = path.stat().st_size
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(size - 1, int(last)) if first and last else size - 1
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        source = path.open("rb")
        source.seek(start)
        self.remaining = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(self.remaining))
        self.end_headers()
        return source

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def copyfile(self, source, output):
        # Changing examples cancels the previous media request. This is normal
        # browser behaviour, especially for longer recordings.
        try:
            return self.copy_media(source, output)
        except (BrokenPipeError, ConnectionResetError):
            return None

    def copy_media(self, source, output):
        if self.remaining is None:
            return super().copyfile(source, output)
        remaining = self.remaining
        while remaining:
            block = source.read(min(65536, remaining))
            if not block:
                break
            output.write(block)
            remaining -= len(block)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()
    site = Path(__file__).resolve().parents[1]
    handler = functools.partial(SiteHandler, directory=str(site))
    server = http.server.ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"Duplex-MPE preview: http://{args.bind}:{args.port}", flush=True)
    server.serve_forever()

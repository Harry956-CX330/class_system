"""Serve precompressed public build assets without buffering private downloads."""
import mimetypes
from pathlib import Path
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles


class CompressedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        headers = dict(scope.get("headers", []))
        encodings = headers.get(b"accept-encoding", b"").decode("latin-1")
        gzip_allowed = False
        for item in encodings.split(","):
            parts = item.strip().split(";")
            if parts[0] == "gzip":
                try:
                    gzip_allowed = all(float(p.strip()[2:]) > 0 for p in parts[1:] if p.strip().startswith("q="))
                except ValueError:
                    pass
        if gzip_allowed and b"range" not in headers:
            full, stat = self.lookup_path(path + ".gz")
            if stat and Path(full).is_file():
                return FileResponse(full, stat_result=stat, media_type=mimetypes.guess_type(path)[0],
                    headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding", "Cache-Control": "public, max-age=31536000, immutable"})
        response = await super().get_response(path, scope)
        response.headers["Vary"] = "Accept-Encoding"
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

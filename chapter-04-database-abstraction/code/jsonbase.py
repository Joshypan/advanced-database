"""Store dictionaries as numbered JSON files in a specified folder."""
import json
from pathlib import Path
import tempfile


class JsonBase:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.counter = self.folder / ".next-id"

    def _path(self, id):
        return self.folder / f"{int(id)}.json"

    def _write(self, path, text):
        # Write completely before replacing the destination.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=self.folder, delete=False) as output:
            temporary = Path(output.name)
            try:
                output.write(text)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def get_all(self):
        paths = sorted(self.folder.glob("[0-9]*.json"), key=lambda p: int(p.stem))
        return [self.get(path.stem) for path in paths]

    def get(self, id):
        path = self._path(id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def create(self, data):
        existing = [int(p.stem) for p in self.folder.glob("[0-9]*.json")]
        next_id = int(self.counter.read_text()) if self.counter.exists() else 1
        id = max(next_id, max(existing, default=0) + 1)
        text = json.dumps(dict(data, id=id), indent=2, ensure_ascii=False) + "\n"
        self._write(self.counter, str(id + 1))
        self._write(self._path(id), text)
        return id

    def update(self, id, data):
        path = self._path(id)
        if path.exists():
            text = json.dumps(dict(data, id=int(id)), indent=2, ensure_ascii=False) + "\n"
            self._write(path, text)

    def delete(self, id):
        self._path(id).unlink(missing_ok=True)

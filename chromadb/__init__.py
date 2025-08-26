"""Minimal stub of the ``chromadb`` package."""

class _DummyCollection:  # pragma: no cover - simple in-memory stub
    def __init__(self):
        self.items = {}

    def add(self, embeddings=None, metadatas=None, ids=None, **kwargs):
        self.items.update({i: m for i, m in zip(ids or [], metadatas or [])})

    def query(self, *_, **__):
        return {"ids": [[]], "metadatas": [[]], "distances": [[]]}

    def get(self, **__):
        return {"ids": list(self.items.keys()), "metadatas": list(self.items.values())}

    def count(self):
        return len(self.items)

    def delete(self, ids=None):
        for i in ids or []:
            self.items.pop(i, None)


class PersistentClient:  # pragma: no cover - simple stub
    def __init__(self, *_, **__):
        self.collections = {}

    def get_collection(self, name, *_args, **_kwargs):
        if name not in self.collections:
            raise Exception("collection not found")
        return self.collections[name]

    def create_collection(self, name, *_args, **_kwargs):
        col = _DummyCollection()
        self.collections[name] = col
        return col

    def delete_collection(self, name, *_args, **_kwargs):
        self.collections.pop(name, None)

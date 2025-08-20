"""Minimal stub of the ``torch`` package used for testing."""

class _Cuda:
    @staticmethod
    def is_available() -> bool:  # pragma: no cover - simple stub
        return False

cuda = _Cuda()

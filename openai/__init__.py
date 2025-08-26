"""Minimal stub of the ``openai`` package used for testing.

The project only requires the presence of an ``OpenAI`` class so the
unit tests can patch it.  The implementation here does not provide any
real API functionality.
"""

class OpenAI:  # pragma: no cover - behaviour mocked in tests
    def __init__(self, *_, **__):
        pass

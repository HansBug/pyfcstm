import random
import uuid

import pytest


@pytest.fixture
def mock_uuid4(monkeypatch):
    original_uuid4 = uuid.uuid4

    def _mocked_uuid4():

        bytes_ = bytes([random.randint(0, 255) for _ in range(16)])
        return uuid.UUID(bytes=bytes_, version=4)

    monkeypatch.setattr(uuid, "uuid4", _mocked_uuid4)
    try:
        random.seed(0)
        yield
    finally:
        monkeypatch.setattr(uuid, "uuid4", original_uuid4)

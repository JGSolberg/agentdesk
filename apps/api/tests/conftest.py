import os
from pathlib import Path
import tempfile

import pytest

TEST_DIR = tempfile.mkdtemp(prefix="agentdesk-tests-")
os.environ["AGENTDESK_DATABASE_URL"] = f"sqlite:///{Path(TEST_DIR) / 'test.db'}"

from agentdesk_api import models  # noqa: E402, F401
from agentdesk_api.database import Base, engine  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clear_db():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

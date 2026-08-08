import os
from pathlib import Path
import tempfile

TEST_DIR = tempfile.mkdtemp(prefix="agentdesk-tests-")
os.environ["AGENTDESK_DATABASE_URL"] = f"sqlite:///{Path(TEST_DIR) / 'test.db'}"

from agentdesk_api import models  # noqa: E402, F401
from agentdesk_api.database import Base, engine  # noqa: E402

Base.metadata.create_all(bind=engine)

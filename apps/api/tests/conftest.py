import os
from pathlib import Path
import tempfile

TEST_DIR = tempfile.mkdtemp(prefix="agentdesk-tests-")
os.environ["AGENTDESK_DATABASE_URL"] = f"sqlite:///{Path(TEST_DIR) / 'test.db'}"

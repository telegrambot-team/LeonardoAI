import sys

from pathlib import Path

# Add src directory to sys.path for module resolution during tests
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

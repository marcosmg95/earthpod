"""Where the backend keeps its files (all paths absolute, relative to backend/)."""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]   # backend/src/jukebox -> backend
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"                          # downloaded NASA files (gitignored)
DERIVED_DIR = DATA_DIR / "derived"                  # small measured results (committed)
SONIFICATIONS_DIR = BACKEND_DIR / "sonifications"   # one folder of scripts per SVS page
OUT_DIR = BACKEND_DIR / "out"                       # rendered audio (gitignored)

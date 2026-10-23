"""Configuration settings for ZentroMart VoiceOps RAG system."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Root paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
KB_DIR = DATASET_DIR / "kb"
DATA_DIR = DATASET_DIR / "data"
PRACTICE_DIR = DATASET_DIR / "practice"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
INDEX_DIR = OUTPUTS_DIR / "index"
EVALUATION_DIR = OUTPUTS_DIR / "evaluation"
SAMPLE_OUTPUTS_DIR = OUTPUTS_DIR / "sample_outputs"

# Reference date for all synthetic date calculations
REFERENCE_DATE = "2026-10-20"

# Gemini Model Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Default to gemini-3.5-flash-lite (fast, low latency, modern v1beta supported)
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Retrieval & Embedding Configuration
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
DEFAULT_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", "0.20"))

# Document status rules
CURRENT_RETURNS_POLICY = "pol_returns_v4.md"
SUPERSEDED_RETURNS_POLICY = "pol_returns_v3_superseded.md"

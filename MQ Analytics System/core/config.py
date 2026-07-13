# =====================================================
# ✅ SYSTEM CONFIGURATION
# =====================================================
import os
from core.paths import get_db_path, get_model_path, get_index_path, get_metadata_path, get_inbox_path

# LLM Configurations
MODEL_NAME = "phi3"  # For Ollama backend
LLM_BACKEND = "local"            # "local" for GGUF (llama-cpp-python) or "ollama" for Ollama API
MAX_RETRIES = 2

# File Paths
DB_PATH = get_db_path()
MODEL_PATH = get_model_path()
INDEX_PATH = get_index_path()
METADATA_PATH = get_metadata_path()
INBOX_PATH = get_inbox_path()
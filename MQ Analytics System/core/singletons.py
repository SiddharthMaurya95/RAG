# =====================================================
# ✅ CACHED SINGLETON INSTANCES
# =====================================================
import os
import sys
import sqlite3
import threading
import streamlit as st

# Configure Windows DLL search directories for NVIDIA CUDA packages
if os.name == 'nt':
    for path in sys.path:
        if "site-packages" in path:
            cuda_dir = os.path.join(path, "nvidia", "cuda_runtime", "bin")
            cublas_dir = os.path.join(path, "nvidia", "cublas", "bin")
            nvrtc_dir = os.path.join(path, "nvidia", "cuda_nvrtc", "bin")
            if os.path.exists(cuda_dir):
                try:
                    os.add_dll_directory(cuda_dir)
                    os.environ['PATH'] = f"{cuda_dir};" + os.environ['PATH']
                except Exception:
                    pass
            if os.path.exists(cublas_dir):
                try:
                    os.add_dll_directory(cublas_dir)
                    os.environ['PATH'] = f"{cublas_dir};" + os.environ['PATH']
                except Exception:
                    pass
            if os.path.exists(nvrtc_dir):
                try:
                    os.add_dll_directory(nvrtc_dir)
                    os.environ['PATH'] = f"{nvrtc_dir};" + os.environ['PATH']
                except Exception:
                    pass

from core.paths import get_db_path, get_index_path, get_metadata_path, get_model_path

class IngestionTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_ingested_file = None
        self.last_ingest_time = 0.0
        self.new_records_count = 0

    def register_ingestion(self, filename, count):
        with self.lock:
            import time
            self.last_ingested_file = filename
            self.last_ingest_time = time.time()
            self.new_records_count = count

# Shared instance for watchdog notifications
_tracker_instance = IngestionTracker()

@st.cache_resource
def get_ingestion_tracker():
    """Returns the shared ingestion tracker instance."""
    return _tracker_instance

@st.cache_resource
def get_db_connection(db_path="data/automotive.db"):
    """Returns a thread-safe database connection path."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    conn.commit()
    conn.close()
    return db_path

@st.cache_resource
def get_embedder(index_path="data/faiss_index.bin", metadata_path="data/vector_metadata.json"):
    """Loads and caches the SentenceTransformer model and FAISS vector index."""
    from core.rag.rag_embedder import VectorEmbedder
    index_path = get_index_path(index_path)
    metadata_path = get_metadata_path(metadata_path)
    embedder = VectorEmbedder(index_path=index_path, metadata_path=metadata_path)
    embedder.load_model()
    embedder.load_index()
    return embedder

@st.cache_resource
def get_llm(model_path="models/Qwen2.5-7B-Instruct-Q4_K_M.gguf"):
    """Loads and caches the LLM Client."""
    model_path = get_model_path(model_path)
    from core.ollama_client import LLMClient
    client = LLMClient(model_path=model_path)
    client.load_model()
    return client

@st.cache_resource
def get_router(db_path="data/automotive.db"):
    """Loads and caches the QueryRouter instance."""
    db_path = get_db_connection(db_path)
    from core.pipeline import QueryRouter
    return QueryRouter(db_path)

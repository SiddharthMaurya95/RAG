# =====================================================
# ✅ PATH RESOLUTION
# =====================================================
import os

def get_project_root():
    """Returns the absolute path to the MQ Analytics System directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_automotive_qa_root():
    """Returns the absolute path to the automotive_qa reference directory."""
    return os.path.abspath(os.path.join(get_project_root(), "..", "automotive_qa"))

def get_db_path(db_name="data/automotive.db"):
    """Returns absolute path to database, falling back to automotive_qa/data."""
    local_path = os.path.join(get_project_root(), "data", "automotive.db")
    if os.path.exists(local_path):
        return local_path
    
    qa_path = os.path.join(get_automotive_qa_root(), "data", "automotive.db")
    if os.path.exists(qa_path):
        return qa_path
        
    return local_path

def get_index_path(index_name="data/faiss_index.bin"):
    """Returns absolute path to faiss_index.bin, falling back to automotive_qa/data."""
    local_path = os.path.join(get_project_root(), "data", "faiss_index.bin")
    if os.path.exists(local_path):
        return local_path
        
    qa_path = os.path.join(get_automotive_qa_root(), "data", "faiss_index.bin")
    if os.path.exists(qa_path):
        return qa_path
        
    return local_path

def get_metadata_path(metadata_name="data/vector_metadata.json"):
    """Returns absolute path to vector_metadata.json, falling back to automotive_qa/data."""
    local_path = os.path.join(get_project_root(), "data", "vector_metadata.json")
    if os.path.exists(local_path):
        return local_path
        
    qa_path = os.path.join(get_automotive_qa_root(), "data", "vector_metadata.json")
    if os.path.exists(qa_path):
        return qa_path
        
    return local_path

def get_inbox_path(inbox_name="data/inbox"):
    """Returns absolute path to inbox, falling back to automotive_qa/data/inbox."""
    local_path = os.path.join(get_project_root(), "data", "inbox")
    if os.path.exists(local_path):
        return local_path
        
    qa_path = os.path.join(get_automotive_qa_root(), "data", "inbox")
    if os.path.exists(qa_path):
        return qa_path
        
    return local_path

def get_model_path(model_name="models/Phi-3-mini-4k-instruct-q4.gguf"):
    """Returns absolute path to model, falling back to automotive_qa/models."""
    local_path = os.path.join(get_project_root(), "models", "Phi-3-mini-4k-instruct-q4.gguf")
    if os.path.exists(local_path):
        return local_path
        
    qa_path = os.path.join(get_automotive_qa_root(), "models", "Phi-3-mini-4k-instruct-q4.gguf")
    if os.path.exists(qa_path):
        return qa_path
        
    return local_path

import os

def get_project_root():
    """Returns the absolute path to the automotive_qa directory."""
    # This file is located at: automotive_qa/core/paths.py
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_db_path(db_name="data/automotive.db"):
    """
    Returns the absolute path to automotive.db.
    If db_name is already absolute or doesn't match the default, returns it unchanged.
    """
    if db_name == "data/automotive.db" or not os.path.isabs(db_name):
        # Clean relative parts if any
        rel_path = db_name.replace("data/", "", 1) if db_name.startswith("data/") else db_name
        return os.path.join(get_project_root(), "data", rel_path)
    return db_name

def get_index_path(index_name="data/faiss_index.bin"):
    """Returns the absolute path to faiss_index.bin."""
    if index_name == "data/faiss_index.bin" or not os.path.isabs(index_name):
        return os.path.join(get_project_root(), "data", "faiss_index.bin")
    return index_name

def get_metadata_path(metadata_name="data/vector_metadata.json"):
    """Returns the absolute path to vector_metadata.json."""
    if metadata_name == "data/vector_metadata.json" or not os.path.isabs(metadata_name):
        return os.path.join(get_project_root(), "data", "vector_metadata.json")
    return metadata_name

def get_inbox_path(inbox_name="data/inbox"):
    """Returns the absolute path to data/inbox."""
    if inbox_name == "data/inbox" or not os.path.isabs(inbox_name):
        return os.path.join(get_project_root(), "data", "inbox")
    return inbox_name

def get_model_path(model_name="models/Phi-3-mini-4k-instruct-q4.gguf"):
    """Returns the absolute path to Phi-3-mini model."""
    if model_name == "models/Phi-3-mini-4k-instruct-q4.gguf" or not os.path.isabs(model_name):
        return os.path.join(get_project_root(), "models", "Phi-3-mini-4k-instruct-q4.gguf")
    return model_name

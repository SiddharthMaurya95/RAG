import os
from rag.preprocessor import preprocess_for_embedding
from rag.embedding_service import EmbeddingService
from core.paths import get_db_path, get_project_root

def build_offline_embeddings(db_path: str = "data/automotive.db"):
    """
    Offline one-time preprocessing to build and persist embeddings.
    """
    db_path_full = get_db_path(db_path)
    
    print("Step 1: Loading and preprocessing records...")
    df = preprocess_for_embedding(db_path_full)
    
    if df.empty:
        print("No records found to process.")
        return
        
    print(f"Step 2: Generating embeddings for {len(df)} records...")
    cache_dir = os.path.join(get_project_root(), "data")
    embedding_service = EmbeddingService(cache_dir=cache_dir)
    embedding_service.generate_and_save_embeddings(df, text_column="clean_summary", id_column="id")
    print("Offline preprocessing completed successfully.")

if __name__ == "__main__":
    build_offline_embeddings()

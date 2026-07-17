import os
import json
import numpy as np
import pandas as pd
from typing import List, Tuple, Union
from core.decorators import with_logging_and_exceptions

class EmbeddingService:
    def __init__(self, model_name="all-MiniLM-L6-v2", cache_dir="data"):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        
        # Paths for persisting embeddings
        self.embeddings_path = os.path.join(self.cache_dir, "embeddings.npy")
        self.ids_path = os.path.join(self.cache_dir, "embedding_ids.json")
        
        # In-memory storage
        self.embeddings = None
        self.ids = None

    def load_model(self):
        """Loads the sentence-transformer model into memory."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            # Suppress excessive logging
            import logging
            logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
            self.model = SentenceTransformer(self.model_name, device="cpu")
        return self.model

    @with_logging_and_exceptions
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generates normalized embeddings for a single text or a list of texts.
        """
        model = self.load_model()
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]
            
        # Generate embeddings
        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        
        # Normalize to allow fast cosine similarity via dot product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1e-10
        normalized_embeddings = embeddings / norms
        
        if is_single:
            return normalized_embeddings[0]
        return normalized_embeddings

    @with_logging_and_exceptions
    def generate_and_save_embeddings(self, df: pd.DataFrame, text_column: str = "clean_summary", id_column: str = "id"):
        """
        Generates embeddings for the dataframe and persists them to disk.
        """
        if df.empty or text_column not in df.columns or id_column not in df.columns:
            print("Invalid DataFrame for embedding generation.")
            return

        print(f"Generating embeddings for {len(df)} records...")
        texts = df[text_column].tolist()
        ids = df[id_column].tolist()
        
        embeddings = self.encode(texts)
        
        # Ensure directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Save to disk
        np.save(self.embeddings_path, embeddings)
        with open(self.ids_path, "w") as f:
            json.dump(ids, f)
            
        self.embeddings = embeddings
        self.ids = ids
        print("Embeddings generated and saved successfully.")

    @with_logging_and_exceptions
    def load_embeddings(self) -> bool:
        """
        Loads embeddings and IDs from disk into memory.
        Returns True if successful, False otherwise.
        """
        if os.path.exists(self.embeddings_path) and os.path.exists(self.ids_path):
            try:
                self.embeddings = np.load(self.embeddings_path)
                with open(self.ids_path, "r") as f:
                    self.ids = json.load(f)
                return True
            except Exception as e:
                print(f"Error loading embeddings: {e}")
                return False
        return False

    @with_logging_and_exceptions
    def get_embeddings(self) -> Tuple[np.ndarray, List[int]]:
        """
        Returns the embeddings matrix and the corresponding list of IDs.
        """
        if self.embeddings is None or self.ids is None:
            success = self.load_embeddings()
            if not success:
                return np.array([]), []
        return self.embeddings, self.ids

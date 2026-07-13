import numpy as np

def compute_cosine_similarity(query_embedding: np.ndarray, candidate_embeddings: np.ndarray) -> np.ndarray:
    """
    Computes vectorized cosine similarity between a single query embedding 
    and a matrix of candidate embeddings.
    
    Assumes all embeddings are already L2 normalized.
    """
    if len(candidate_embeddings) == 0:
        return np.array([])
        
    # Since embeddings are L2 normalized, cosine similarity is just the dot product
    # query_embedding shape: (D,)
    # candidate_embeddings shape: (N, D)
    # result shape: (N,)
    similarities = np.dot(candidate_embeddings, query_embedding)
    
    return similarities

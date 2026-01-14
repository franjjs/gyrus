import difflib
import math
from typing import Any, List, Optional

# --- SEARCH CONSTANTS ---
SEMANTIC_WEIGHT = 0.7
FUZZY_WEIGHT = 0.3
KEYWORD_BOOST = 0.5

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Math utility for vector similarity."""
    if not v1 or not v2:
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    return dot_product / (mag1 * mag2) if mag1 and mag2 else 0.0

def hybrid_search(
    query: str, 
    nodes: List[Any], 
    query_vec: Optional[List[float]] = None, 
    vector_model_id: str = "unknown"
) -> List[Any]:
    """Rank nodes using weighted hybrid scoring."""
    if not query:
        return nodes
    
    scored = []
    query_lower = query.lower()
    
    for n in nodes:
        sim = 0.0
        # 1. Semantic Score
        node_vmid = getattr(n, 'vector_model_id', 'unknown')
        if query_vec and node_vmid == vector_model_id:
            sim = cosine_similarity(query_vec, n.vector)
            
        # 2. Fuzzy Score
        fuzz = difflib.SequenceMatcher(None, query_lower, n.content.lower()).ratio()
        
        # 3. Combined Score
        score = (sim * SEMANTIC_WEIGHT) + (fuzz * FUZZY_WEIGHT)
        
        # 4. Keyword Boost
        if query_lower in n.content.lower(): 
            score += KEYWORD_BOOST
            
        scored.append((score, n))
        
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored]
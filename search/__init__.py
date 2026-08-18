"""RAG index and user metadata (phase 2).

Ported from doc-classifier. Vectors stay in rag_index.npy/.json rather than
MySQL: in-memory numpy search beats BLOB comparison at this scale.
"""

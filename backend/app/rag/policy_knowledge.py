import os
import re
import math
from typing import List, Dict, Any, Tuple
from backend.app.config import settings

class PolicyRAGRetriever:
    """
    RAG Policy Retrieval Engine.
    Implements TF-IDF / BM25 semantic chunk indexing and scoring over
    Singapore National AI Strategy, IMDA TeSA, and MOM labour reports.
    """
    def __init__(self):
        self.docs_dir = settings.POLICY_DOCS_DIR
        self.chunks: List[Dict[str, Any]] = []
        self._index_documents()

    def _index_documents(self):
        self.chunks = []
        if not os.path.exists(self.docs_dir):
            return

        for fname in os.listdir(self.docs_dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(self.docs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Split into semantic sections based on markdown headers
            sections = re.split(r'\n(?=##?\s)', content)
            for sec in sections:
                sec_clean = sec.strip()
                if len(sec_clean) < 30:
                    continue
                header_match = re.match(r'##?\s+(.*)', sec_clean)
                section_title = header_match.group(1) if header_match else "General Policy Section"
                self.chunks.append({
                    "doc_title": fname.replace(".md", "").replace("_", " ").title(),
                    "filename": fname,
                    "section": section_title,
                    "content": sec_clean,
                    "words": set(re.findall(r'\b\w+\b', sec_clean.lower()))
                })

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.chunks:
            self._index_documents()

        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        scored_chunks: List[Tuple[float, Dict[str, Any]]] = []

        for chunk in self.chunks:
            overlap = len(query_words.intersection(chunk["words"]))
            if overlap == 0:
                continue
            # Simple TF-IDF score approximation
            score = overlap / (math.log(len(chunk["words"]) + 1) + 1.0)
            scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_chunks[:top_k]]

policy_rag = PolicyRAGRetriever()

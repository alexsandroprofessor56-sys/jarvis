import os
import hashlib
from datetime import datetime

CHROMA_DIR = os.path.expanduser("~/.jarvis/chroma_db")


class VectorStore:
    def __init__(self, collection_name="jarvis_knowledge"):
        import chromadb
        from chromadb.config import Settings
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_text(self, text, metadata=None, doc_id=None):
        if not text or len(text.strip()) < 10:
            return None
        if doc_id is None:
            doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
        metadata = metadata or {}
        metadata["added_at"] = datetime.now().isoformat()
        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            return None

    def search(self, query, n_results=5, filter_metadata=None):
        try:
            kwargs = dict(query_texts=[query], n_results=n_results)
            if filter_metadata:
                kwargs["where"] = filter_metadata
            results = self.collection.query(**kwargs)
            docs = results["documents"][0] if results["documents"] else []
            metas = results["metadatas"][0] if results["metadatas"] else []
            dists = results["distances"][0] if results["distances"] else []
            return [
                {"text": d, "metadata": m, "score": 1 - s}
                for d, m, s in zip(docs, metas, dists)
            ]
        except Exception as e:
            return []

    def count(self):
        return self.collection.count()

    def delete_old(self, max_age_days=30):
        try:
            all_data = self.collection.get()
            if not all_data["metadatas"]:
                return 0
            now = datetime.now()
            to_delete = []
            for meta, doc_id in zip(all_data["metadatas"], all_data["ids"]):
                added = meta.get("added_at", "")
                if added:
                    try:
                        age = (now - datetime.fromisoformat(added)).days
                        if age > max_age_days:
                            to_delete.append(doc_id)
                    except ValueError:
                        continue
            if to_delete:
                self.collection.delete(ids=to_delete)
            return len(to_delete)
        except Exception:
            return 0

class KnowledgeBase:
    def __init__(self):
        self.store = None
        self.ingestor = None
        self._fallback = True
        self._init_vector_store()

    def _init_vector_store(self):
        try:
            from brain.vector_store import VectorStore
            self.store = VectorStore()
            from brain.ingestor import Ingestor
            self.ingestor = Ingestor(vector_store=self.store)
            self._fallback = False
        except ImportError:
            pass
        except Exception:
            pass

    def query(self, question, n_results=5):
        if not self.store:
            return None, []
        try:
            return self.store.search(question, n_results=n_results), []
        except Exception as e:
            return None, []

    def learn_file(self, file_path):
        if not self.ingestor:
            return "Vector store (chromadb) não disponível. `pip install chromadb`"
        return self.ingestor.ingest_file(file_path)

    def learn_directory(self, directory, recursive=True):
        if not self.ingestor:
            return "Vector store (chromadb) não disponível. `pip install chromadb`"
        return self.ingestor.ingest_directory(directory, recursive)

    def learn_text(self, text, source="manual"):
        if not self.ingestor:
            return "Vector store (chromadb) não disponível. `pip install chromadb`"
        return self.ingestor.ingest_text(text, source)

    def stats(self):
        if self.store:
            try:
                return {"total_chunks": self.store.count()}
            except Exception:
                pass
        return {"total_chunks": 0}

    def cleanup(self, max_age_days=30):
        if self.store:
            return self.store.delete_old(max_age_days)
        return 0

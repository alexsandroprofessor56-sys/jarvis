class Embedder:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self._model = None
        self.model_name = model_name
        self._available = False

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._available = True
            except ImportError:
                self._available = False
                return None
        return self._model

    def embed(self, text):
        m = self.model
        if m is None:
            return [0.0]
        return m.encode(text).tolist()

    def similariry(self, text1, text2):
        m = self.model
        if m is None:
            return 0.0
        emb1 = self.embed(text1)
        emb2 = self.embed(text2)
        import numpy as np
        a = np.array(emb1)
        b = np.array(emb2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

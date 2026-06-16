from ddgs import DDGS


class WebSearch:
    def __init__(self):
        self._client = DDGS()

    def search(self, query, max_results=5):
        try:
            results = list(self._client.text(query, max_results=max_results))
            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
            return formatted
        except Exception as e:
            return [{"error": str(e)}]

    def search_text(self, query, max_results=5):
        results = self.search(query, max_results)
        lines = []
        for r in results:
            if "error" in r:
                continue
            lines.append(f"{r['title']}: {r['snippet']}")
            lines.append(f"  Fonte: {r['url']}")
        return "\n".join(lines) if lines else "Nenhum resultado encontrado."

import os
import tempfile
import mss


class ScreenCapture:
    def __init__(self, model=None):
        self.model = model

    def capture(self, output_path=None):
        if output_path is None:
            output_path = os.path.join(tempfile.gettempdir(), "jarvis_screen.png")
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct.shot(output=output_path)
        return output_path

    def capture_region(self, left, top, width, height, output_path=None):
        if output_path is None:
            output_path = os.path.join(tempfile.gettempdir(), "jarvis_region.png")
        with mss.mss() as sct:
            region = {"left": left, "top": top, "width": width, "height": height}
            sct.shot(output=output_path)
            sct.grab(region)
        return output_path

    def analyze(self, image_path=None):
        if not self.model:
            return "Nenhum modelo de visão disponível. Use `ollama pull llava` para ativar."
        if image_path is None:
            image_path = self.capture()
        try:
            import ollama
            response = ollama.chat(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": "Descreva detalhadamente o que você vê nesta imagem.",
                    "images": [image_path]
                }]
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[ERRO VISÃO] {e}"

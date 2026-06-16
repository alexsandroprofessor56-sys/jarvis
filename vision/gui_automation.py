import os
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None


class GUIAutomation:
    def __init__(self):
        self._template_cache = {}

    def find_on_screen(self, template_path, threshold=0.8):
        if not HAS_CV2:
            return "OpenCV não instalado. `pip install opencv-python`"
        if template_path not in self._template_cache:
            self._template_cache[template_path] = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

        import mss
        with mss.mss() as sct:
            screenshot = np.array(sct.grab(sct.monitors[1]))
        screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        template = self._template_cache[template_path]

        result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return {"x": center_x, "y": center_y, "confidence": float(max_val),
                    "width": w, "height": h}
        return None

    def find_text_on_screen(self, text):
        if not HAS_CV2:
            return "OpenCV não instalado. `pip install opencv-python`"
        try:
            import pytesseract
        except ImportError:
            return "pytesseract não instalado"
        import mss
        with mss.mss() as sct:
            screenshot = np.array(sct.grab(sct.monitors[1]))
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        data = pytesseract.image_to_data(gray, lang="por", output_type=pytesseract.Output.DICT)

        for i in range(len(data["text"])):
            if text.lower() in data["text"][i].lower():
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i] + data["height"][i] // 2
                return {"x": x, "y": y, "text": data["text"][i],
                        "confidence": data["conf"][i]}
        return None

    def click_element(self, element_info):
        import pyautogui
        if element_info and isinstance(element_info, dict):
            pyautogui.moveTo(element_info["x"], element_info["y"])
            pyautogui.click()
            return f"Clicou em ({element_info['x']}, {element_info['y']})"
        return f"Elemento não encontrado: {element_info}"

    def locate_and_click(self, template_path, threshold=0.8):
        elem = self.find_on_screen(template_path, threshold)
        return self.click_element(elem)

    def locate_text_and_click(self, text):
        elem = self.find_text_on_screen(text)
        return self.click_element(elem)

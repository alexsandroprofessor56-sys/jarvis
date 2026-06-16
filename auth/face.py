import json
import os
import tempfile
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None


class FaceAuth:
    def __init__(self):
        self._face_cascade = None
        self._recognizer = None
        self._known_faces = {}
        self._data_dir = os.path.expanduser("~/.jarvis/faces")
        os.makedirs(self._data_dir, exist_ok=True)
        self._load_known()
        self._error = None

    @property
    def face_cascade(self):
        if not HAS_CV2:
            return None
        if self._face_cascade is None:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
        return self._face_cascade

    @property
    def recognizer(self):
        if not HAS_CV2:
            return None
        if self._recognizer is None:
            self._recognizer = cv2.face.LBPHFaceRecognizer_create()
            known_file = os.path.join(self._data_dir, "model.yml")
            if os.path.exists(known_file):
                self._recognizer.read(known_file)
        return self._recognizer

    def _load_known(self):
        known_file = os.path.join(self._data_dir, "known.json")
        if os.path.exists(known_file):
            with open(known_file) as f:
                self._known_faces = json.load(f)

    def _save_known(self):
        with open(os.path.join(self._data_dir, "known.json"), "w") as f:
            json.dump(self._known_faces, f)

    def register_face(self, user_id, image_path=None):
        if not HAS_CV2:
            return "OpenCV (cv2) não instalado. `pip install opencv-python opencv-contrib-python`"
        if image_path is None:
            import mss
            with mss.mss() as sct:
                screenshot = np.array(sct.grab(sct.monitors[1]))
            image_path = os.path.join(tempfile.gettempdir(), "jarvis_face_register.png")
            cv2.imwrite(image_path, cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR))

        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

        if len(faces) == 0:
            return "Nenhum rosto encontrado na imagem"

        face_data = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_roi, (100, 100))
            face_data.append(face_resized)

        labels = [len(self._known_faces)] * len(face_data)
        self.recognizer.update(face_data, np.array(labels))
        self.recognizer.write(os.path.join(self._data_dir, "model.yml"))

        if user_id not in self._known_faces:
            self._known_faces[user_id] = len(self._known_faces)
            self._save_known()

        return f"Rosto registrado para {user_id}"

    def authenticate(self, image_path=None, threshold=60):
        if not HAS_CV2:
            return None
        if image_path is None:
            import mss
            with mss.mss() as sct:
                screenshot = np.array(sct.grab(sct.monitors[1]))
            image_path = os.path.join(tempfile.gettempdir(), "jarvis_auth.png")
            cv2.imwrite(image_path, cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR))

        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

        if len(faces) == 0:
            return None

        reverse_map = {v: k for k, v in self._known_faces.items()}
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_roi, (100, 100))
            try:
                label, confidence = self.recognizer.predict(face_resized)
                if confidence < threshold and label in reverse_map:
                    return {"user": reverse_map[label], "confidence": int(confidence)}
            except cv2.error:
                continue
        return None

#!/usr/bin/env python3
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui import JarvisUI


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    face_path = os.path.expanduser("~/.jarvis/face.png")
    if not os.path.exists(face_path):
        face_path = None

    window = JarvisUI(face_path=face_path)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

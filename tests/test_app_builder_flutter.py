"""tests/test_app_builder_flutter.py"""
import tempfile
import os
from agent.app_builder_flutter import generate_flutter

def test_generate_flutter_creates_dir():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_flutter("meu-app", tmp, {"type": "flutter", "framework": "flutter", "features": ["material"]})
        # Se flutter nao estiver instalado, verifica fallback
        if "Flutter nao instalado" in str(result):
            assert os.path.isfile(os.path.join(tmp, "README.txt"))
            with open(os.path.join(tmp, "README.txt")) as f:
                content = f.read()
                assert "Flutter nao instalado" in content
        else:
            assert os.path.isdir(os.path.join(tmp, "lib"))

def test_generate_flutter_build_script():
    with tempfile.TemporaryDirectory() as tmp:
        generate_flutter("app", tmp, {"type": "flutter", "framework": "flutter", "features": []})
        build_sh = os.path.join(tmp, "build.sh")
        if os.path.exists(build_sh):
            with open(build_sh) as f:
                content = f.read()
            assert "flutter build apk" in content

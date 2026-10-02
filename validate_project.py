import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
main = ROOT / "main.py"
spec = ROOT / "buildozer.spec"
workflow = ROOT / ".github/workflows/build-apk.yml"

ast.parse(main.read_text(encoding="utf-8"))
assert "[app]" in spec.read_text(encoding="utf-8")
assert workflow.exists()
assert "ArtemSBulgakov/buildozer-action@v1" in workflow.read_text(encoding="utf-8")
assert "android.home_app = True" in spec.read_text(encoding="utf-8")
assert "requirements = python3,kivy" in spec.read_text(encoding="utf-8")
assert "charset-normalizer" not in spec.read_text(encoding="utf-8")
print("JARVIS project validation: OK")

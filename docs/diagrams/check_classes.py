# Verifies that every class drawn in model.iuml exists in the backend code,
# so the diagrams cannot silently drift away from the implementation.
# Usage: python docs/diagrams/check_classes.py   (from the repository root)
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = Path(__file__).with_name("model.iuml")

declared = re.compile(
    r'^\s*(?:abstract\s+class|class|interface)\s+(?:"[^"]+"\s+as\s+)?(\w+)(.*)$', re.M
)
code = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "backend/app").rglob("*.py"))

missing = []
for name, rest in declared.findall(MODEL.read_text(encoding="utf-8")):
    if "<<external>>" in rest:
        continue
    if not re.search(rf"^\s*class {re.escape(name)}\b", code, re.M):
        missing.append(name)

if missing:
    print("Classes on the diagrams but not in the code:", ", ".join(missing))
    sys.exit(1)
print("All diagram classes exist in backend/app.")

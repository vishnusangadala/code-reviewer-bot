"""
Entry point. Run:  python main.py [path_to_code_file]

Defaults to inputs/sample.py if no path given.
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pipeline import run_pipeline
from render import render

load_dotenv()


def detect_language(path: Path) -> str:
    """Crude language detection from extension. Good enough for the prompt."""
    ext = path.suffix.lower()
    return {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".java": "java", ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".cpp": "cpp", ".c": "c", ".cs": "csharp",
    }.get(ext, "python")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("inputs/sample.py")
    if not path.exists():
        print(f"ERROR: {path} not found.")
        sys.exit(1)

    code = path.read_text(encoding="utf-8")
    language = detect_language(path)
    print(f"Reviewing {path} ({language}, {len(code)} chars)")

    result = run_pipeline(code, language=language)
    render(result)

    # Audit log
    Path("outputs").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path("outputs") / f"review_{path.stem}_{timestamp}.json"
    out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"✓ Full audit log: {out_path}")


if __name__ == "__main__":
    main()

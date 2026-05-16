import re
from pathlib import Path
def strip_all_comments_to_output(source_directory=".", output_directory="output"):
    source_dir = Path(source_directory).resolve()
    output_dir = Path(output_directory).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    docstring_double = re.compile(r'^[ \t]*"""[\s\S]*?"""[ \t]*\n?', re.MULTILINE)
    docstring_single = re.compile(r"^[ \t]*'''[\s\S]*?'''[ \t]*\n?", re.MULTILINE)
    inline_comment_pattern = re.compile(
        r'('
        r'"""[\s\S]*?"""|'
        r"'''[\s\S]*?'''|"
        r'"[^"\\]*(?:\\.[^"\\]*)*"|'
        r"'[^'\\]*(?:\\.[^'\\]*)*'"
        r')|(#.*?$)',
        re.MULTILINE
    )
    def inline_replacer(match):
        return match.group(1) if match.group(1) else ""
    py_files = list(source_dir.rglob("*.py"))
    if not py_files:
        print(f"No .py files found in {source_dir}")
        return
    processed_count = 0
    for filepath in py_files:
        if output_dir in filepath.parents:
            continue
        if filepath.name == "strip_comments.py":
            continue
        try:
            target_path = output_dir / filepath.relative_to(source_dir)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            code = docstring_double.sub('', code)
            code = docstring_single.sub('', code)
            clean_code = inline_comment_pattern.sub(inline_replacer, code)
            clean_code = "\n".join(line.rstrip() for line in clean_code.splitlines())
            clean_code = re.sub(r'\n\s*\n', '\n', clean_code)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(clean_code + "\n")
            print(f"✅ Saved to: {target_path}")
            processed_count += 1
        except Exception as e:
            print(f"❌ Error processing {filepath.name}: {e}")
    print(f"\nDone! Processed {processed_count} files into '{output_dir.name}'.")
if __name__ == "__main__":
    print("Initiating full comment and docstring removal...")
    strip_all_comments_to_output(source_directory=".", output_directory="output")

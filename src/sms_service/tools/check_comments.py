import os
import re

# Regex for searching russian letters
russian_pattern = re.compile(r"[а-яА-Я]")


def find_russian_text_in_py_files(directory="."):
    """Recursively finds and prints lines with Russian letters in .py files."""

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") or file.endswith(".html") or file.endswith("Dockerfile") or file.endswith(".toml"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line_number, line in enumerate(f, start=1):
                            if russian_pattern.search(line):
                                print(f"{file_path}:{line_number}: {line.strip()}")
                except (UnicodeDecodeError, IOError) as e:
                    print(f"Error reading {file_path}: {e}")


if __name__ == "__main__":
    find_russian_text_in_py_files()

import shutil
import os

src = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\mq analystic system"
dst = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\MQ Analytics Sytem"

def ignore_patterns(path, names):
    ignored = []
    for name in names:
        if name == "__pycache__" or name.endswith(".pyc") or name.endswith(".pyo"):
            ignored.append(name)
    return ignored

if os.path.exists(dst):
    print(f"Destination {dst} already exists. Removing it first.")
    shutil.rmtree(dst)

shutil.copytree(src, dst, ignore=ignore_patterns)
print("Copy completed successfully.")

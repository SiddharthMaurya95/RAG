
import hashlib
path = r"C:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\models\Phi-3-mini-4k-instruct-q4.gguf"

with open(path, "rb") as f:
    print(hashlib.sha256(f.read()).hexdigest())
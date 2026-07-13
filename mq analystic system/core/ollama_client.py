import ollama
import os

print("NO_PROXY =", os.environ.get("NO_PROXY"))

# ✅ Force bypass proxy inside Python
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

def get_client():
    return ollama.Client(
        host="http://127.0.0.1:11434"
    )

import os
import zipfile
import tempfile
from huggingface_hub import snapshot_download

target_zip = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\models\all-MiniLM-L6-v2.zip"

print("Downloading the complete sentence-transformers/all-MiniLM-L6-v2 model from Hugging Face...")
with tempfile.TemporaryDirectory() as tmpdir:
    # Download all formats (PyTorch, TF, ONNX, OpenVINO, etc.)
    model_dir = snapshot_download(
        repo_id="sentence-transformers/all-MiniLM-L6-v2",
        local_dir=tmpdir,
        local_dir_use_symlinks=False
    )
    
    print("Download complete. Creating the full zip archive...")
    if os.path.exists(target_zip):
        os.remove(target_zip)
        
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, model_dir)
                zipf.write(file_path, arcname)
                
    print(f"Restored full archive successfully at: {target_zip}")
    print(f"File size: {os.path.getsize(target_zip)} bytes (~838 MB)")

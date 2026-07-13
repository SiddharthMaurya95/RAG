import os
import shutil
import tempfile
import zipfile
from huggingface_hub import snapshot_download

target_zip = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\models\all-MiniLM-L6-v2.zip"

print("Downloading model sentence-transformers/all-MiniLM-L6-v2 from Hugging Face...")
with tempfile.TemporaryDirectory() as tmpdir:
    # Download the repository files
    model_dir = snapshot_download(
        repo_id="sentence-transformers/all-MiniLM-L6-v2",
        local_dir=tmpdir,
        local_dir_use_symlinks=False
    )
    
    print("Download complete. Zipping files...")
    
    # Remove existing zip if any
    if os.path.exists(target_zip):
        os.remove(target_zip)
        print(f"Removed previous file: {target_zip}")
        
    # Create the zip file containing all files in the model_dir
    with zipfile.ZipFile(target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, model_dir)
                zipf.write(file_path, arcname)
                
    print(f"Successfully zipped model and saved to: {target_zip}")
    print(f"Zip file size: {os.path.getsize(target_zip)} bytes")

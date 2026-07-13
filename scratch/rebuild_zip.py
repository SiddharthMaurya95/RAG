import zipfile
import os
import shutil
import tempfile

zip_path = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\models\all-MiniLM-L6-v2.zip"
new_zip_path = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\models\all-MiniLM-L6-v2_clean.zip"

if not os.path.exists(zip_path):
    print("Source zip not found.")
    exit(1)

print(f"Original zip size: {os.path.getsize(zip_path)} bytes")

# Files/folders to exclude
exclude_names = {
    "tf_model.h5",
    "rust_model.ot",
    "model.safetensors",
    "onnx",
    "openvino"
}

with tempfile.TemporaryDirectory() as tmpdir:
    print("Extracting zip file...")
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(tmpdir)
        
    print("Removing unused files (TF, Rust, ONNX, OpenVINO, Safetensors)...")
    removed_count = 0
    for root, dirs, files in os.walk(tmpdir, topdown=False):
        # Exclude directories
        for d in list(dirs):
            if d in exclude_names:
                dir_path = os.path.join(root, d)
                shutil.rmtree(dir_path)
                print(f"  Removed directory: {d}")
                dirs.remove(d)
                
        # Exclude files
        for f in files:
            if f in exclude_names:
                file_path = os.path.join(root, f)
                os.remove(file_path)
                print(f"  Removed file: {f}")
                removed_count += 1

    print("Re-zipping cleaned model files...")
    with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(tmpdir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tmpdir)
                zipf.write(file_path, arcname)

print(f"Cleaned zip created at: {new_zip_path}")
print(f"Cleaned zip size: {os.path.getsize(new_zip_path)} bytes")

# Replace the original zip with the cleaned one
os.remove(zip_path)
os.rename(new_zip_path, zip_path)
print("Original zip replaced with cleaned version successfully.")

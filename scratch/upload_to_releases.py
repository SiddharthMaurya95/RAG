import os
import sys
import zipfile
import hashlib
import json
import urllib.request
import urllib.error
import time

# Config
REPO = "SiddharthMaurya95/RAG"
CHUNK_SIZE = 1500 * 1024 * 1024 # 1.5 GB chunks
TAG = "v1.0.0-assets"

def zip_directory(src_dir, zip_name):
    print(f"Zipping {src_dir} into {zip_name}...")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, src_dir)
                try:
                    # Skip symlinks if they are broken or represent symlinks on Windows
                    if os.path.islink(filepath):
                        print(f"  Skipping symlink: {arcname}")
                        continue
                    zipf.write(filepath, arcname)
                except (OSError, PermissionError) as e:
                    print(f"  Warning: Skipping {arcname} due to error: {e}")
    print("Zipping complete.")

def split_file(filepath, chunk_size=CHUNK_SIZE):
    filesize = os.path.getsize(filepath)
    if filesize <= chunk_size:
        return [filepath]
    
    print(f"Splitting {filepath} ({filesize / (1024*1024*1024):.2f} GB) into {chunk_size / (1024*1024*1024):.2f} GB chunks...")
    parts = []
    part_num = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_name = f"{filepath}.part{part_num}"
            with open(part_name, 'wb') as part_file:
                part_file.write(chunk)
            parts.append(part_name)
            print(f"  Created: {part_name}")
            part_num += 1
    return parts

def upload_asset(upload_url, filepath, token):
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    url = f"{upload_url.split('{')[0]}?name={filename}"
    
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(filesize)
    }
    
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        print(f"Uploading {filename} ({filesize / (1024*1024):.2f} MB) - Attempt {attempt}/{max_retries}...")
        try:
            with open(filepath, 'rb') as f:
                req = urllib.request.Request(url, data=f.read(), headers=headers, method='POST')
                with urllib.request.urlopen(req) as resp:
                    res = json.loads(resp.read().decode())
                    print(f"  Successfully uploaded {filename}!")
                    return res
        except (urllib.error.URLError, ConnectionResetError) as e:
            print(f"  Network error uploading {filename}: {e}")
            if attempt < max_retries:
                sleep_time = attempt * 5
                print(f"  Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"  Max retries reached. Failed to upload {filename}.")
                return None
        except urllib.error.HTTPError as e:
            print(f"  Failed to upload {filename}: {e.code} - {e.reason}")
            try:
                print(e.read().decode())
            except Exception:
                pass
            return None

def create_release(repo, tag, token):
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    data = {
        "tag_name": tag,
        "name": f"Automotive QA Offline Assets ({tag})",
        "body": "This release contains split binary assets and virtual environments for offline deployment.",
        "draft": False,
        "prerelease": False
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode())
            print(f"Created release: {res['html_url']}")
            existing = {a['name']: a['size'] for a in res.get('assets', []) if a.get('state') == 'uploaded'}
            return res['upload_url'], existing
    except urllib.error.HTTPError as e:
        # If release already exists, fetch its upload url and assets
        if e.code == 422:
            print("Release already exists, fetching existing release details...")
            get_req = urllib.request.Request(f"{url}/tags/{tag}", headers=headers)
            with urllib.request.urlopen(get_req) as resp:
                res = json.loads(resp.read().decode())
                existing = {a['name']: a['size'] for a in res.get('assets', []) if a.get('state') == 'uploaded'}
                return res['upload_url'], existing
        else:
            print(f"Error creating release: {e.code} - {e.reason}")
            return None, {}

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        token = input("Enter your GitHub Personal Access Token (PAT): ").strip()
    if not token:
        print("GitHub token is required.")
        sys.exit(1)
        
    # Zip venv
    venv_dir = ".venv"
    venv_zip = "venv.zip"
    if os.path.exists(venv_dir):
        if not os.path.exists(venv_zip):
            zip_directory(venv_dir, venv_zip)
    else:
        print("Warning: .venv folder not found in current directory.")
        venv_zip = None

    # Find models
    models = []
    models_dir = "automotive_qa/models"
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            if f.endswith(".gguf") or f.endswith(".whl") or f.endswith(".zip"):
                models.append(os.path.join(models_dir, f))
                
    # Prepare all upload paths
    files_to_upload = []
    if venv_zip and os.path.exists(venv_zip):
        venv_parts = split_file(venv_zip)
        files_to_upload.extend(venv_parts)
        
    for m in models:
        parts = split_file(m)
        files_to_upload.extend(parts)
        
    if not files_to_upload:
        print("No assets found to upload.")
        sys.exit(0)
        
    # Create/fetch release & upload
    upload_url, existing_assets = create_release(REPO, TAG, token)
    if upload_url:
        for f in files_to_upload:
            fname = os.path.basename(f)
            fsize = os.path.getsize(f)
            if fname in existing_assets and existing_assets[fname] == fsize:
                print(f"Asset {fname} already uploaded with matching size ({fsize / (1024*1024):.2f} MB). Skipping.")
                continue
            upload_asset(upload_url, f, token)
            
if __name__ == "__main__":
    main()

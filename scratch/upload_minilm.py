import os
import sys
import json
import urllib.request
import urllib.error
import time

REPO = "SiddharthMaurya95/RAG"
TAG = "v1.0.0-assets"
MODEL_ZIP = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\models\all-MiniLM-L6-v2.zip"

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
            existing_sizes = {a['name']: a['size'] for a in res.get('assets', []) if a.get('state') == 'uploaded'}
            existing_ids = {a['name']: a['id'] for a in res.get('assets', []) if a.get('state') == 'uploaded'}
            return res['upload_url'], existing_sizes, existing_ids
    except urllib.error.HTTPError as e:
        if e.code == 422:
            print("Release already exists, fetching existing release details...")
            get_req = urllib.request.Request(f"{url}/tags/{tag}", headers=headers)
            with urllib.request.urlopen(get_req) as resp:
                res = json.loads(resp.read().decode())
                existing_sizes = {a['name']: a['size'] for a in res.get('assets', []) if a.get('state') == 'uploaded'}
                existing_ids = {a['name']: a['id'] for a in res.get('assets', []) if a.get('state') == 'uploaded'}
                return res['upload_url'], existing_sizes, existing_ids
        else:
            print(f"Error creating/fetching release: {e.code} - {e.reason}")
            return None, {}, {}

def delete_asset(repo, asset_id, token):
    url = f"https://api.github.com/repos/{repo}/releases/assets/{asset_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    req = urllib.request.Request(url, headers=headers, method='DELETE')
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Deleted existing asset with ID {asset_id} successfully.")
    except urllib.error.HTTPError as e:
        print(f"Error deleting asset {asset_id}: {e.code} - {e.reason}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_minilm.py <GITHUB_TOKEN>")
        sys.exit(1)
    token = sys.argv[1].strip()
    
    if not os.path.exists(MODEL_ZIP):
        print(f"Error: Model zip file not found at {MODEL_ZIP}")
        sys.exit(1)
        
    print(f"Preparing to upload {MODEL_ZIP} to {REPO} under tag {TAG}...")
    upload_url, existing_sizes, existing_ids = create_release(REPO, TAG, token)
    if not upload_url:
        print("Failed to resolve release upload URL.")
        sys.exit(1)
        
    fname = os.path.basename(MODEL_ZIP)
    fsize = os.path.getsize(MODEL_ZIP)
    
    if fname in existing_sizes:
        if existing_sizes[fname] == fsize:
            print(f"Asset {fname} already uploaded with matching size ({fsize / (1024*1024):.2f} MB). Skipping.")
            sys.exit(0)
        else:
            print(f"Asset {fname} exists but with different size ({existing_sizes[fname] / (1024*1024):.2f} MB vs new {fsize / (1024*1024):.2f} MB). Deleting existing asset...")
            delete_asset(REPO, existing_ids[fname], token)
            # Give GitHub a second to process the deletion
            time.sleep(2)
        
    upload_asset(upload_url, MODEL_ZIP, token)

if __name__ == "__main__":
    main()

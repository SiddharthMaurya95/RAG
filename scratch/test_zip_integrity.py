import zipfile
import os

zip_path = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\models\all-MiniLM-L6-v2.zip"

if not os.path.exists(zip_path):
    print("Zip file does not exist:", zip_path)
    exit(1)

print(f"Testing zip file integrity: {zip_path}")
try:
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        # testzip() checks the CRC and file headers of all files in the archive
        bad_file = zipf.testzip()
        if bad_file is not None:
            print(f"CRITICAL: Found corrupted file inside zip: {bad_file}")
            exit(1)
        else:
            print("Zip file CRC and header checks PASSED. No corrupted files detected by ZIP standards.")
            
        # Print file list and sizes to confirm everything is valid
        print("\nArchive Contents:")
        infolist = zipf.infolist()
        print(f"Total files in zip: {len(infolist)}")
        
        # Sort by file size descending
        sorted_files = sorted(infolist, key=lambda x: x.file_size, reverse=True)
        for i, info in enumerate(sorted_files[:15]):
            print(f" - {info.filename} ({info.file_size} bytes, compressed to {info.compress_size} bytes)")
        if len(sorted_files) > 15:
            print(f" ... and {len(sorted_files) - 15} more files.")
            
except Exception as e:
    print(f"Failed to open or verify zip archive: {e}")
    exit(1)

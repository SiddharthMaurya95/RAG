with open(r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\reports\engine.py", "r") as f:
    for idx, line in enumerate(f, 1):
        if "RGBColor" in line or "import" in line:
            print(f"{idx}: {line.strip()}")

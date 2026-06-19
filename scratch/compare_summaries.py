import os
import sys
import subprocess
import shutil

# Make sure we are running from the workspace root
sys.path.append(os.path.join(os.path.abspath("."), "automotive_qa"))

def run_evaluation(use_heuristic, output_suffix):
    print(f"\n============ Running Evaluation with USE_HEURISTIC_SUMMARY={use_heuristic} ============")
    
    # Set the environment variable so embedder/builder picks it up
    os.environ['USE_HEURISTIC_SUMMARY'] = '1' if use_heuristic else '0'
    
    # Clear cache or ensure we load the correct mode
    # Since embedder cache is simple, rebuilding the index will read the DB row by row
    # and call build_document_text(record_dict), which checks USE_HEURISTIC_SUMMARY.
    
    # We must rebuild the index first
    from core.singletons import get_embedder
    embedder = get_embedder()
    embedder.rebuild_index_from_db()
    
    # Now run evaluate_system.py
    # We pass the env var to the subprocess as well
    env = os.environ.copy()
    env['USE_HEURISTIC_SUMMARY'] = '1' if use_heuristic else '0'
    
    result = subprocess.run(
        [sys.executable, "scratch/evaluate_system.py"],
        env=env,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
        
    # Copy evaluation_report.md
    src_report = r"C:\Users\maury\.gemini\antigravity-ide\brain\c05eae35-6524-4d98-8160-e10a6236a304\evaluation_report.md"
    dst_report = f"scratch/evaluation_report_{output_suffix}.md"
    if os.path.exists(src_report):
        shutil.copy(src_report, dst_report)
        print(f"Saved report to {dst_report}")
    else:
        print("Warning: evaluation_report.md not found!")

def main():
    # Run LLM summary evaluation
    run_evaluation(use_heuristic=False, output_suffix="llm")
    
    # Run Heuristic summary evaluation
    run_evaluation(use_heuristic=True, output_suffix="heuristic")

if __name__ == "__main__":
    main()

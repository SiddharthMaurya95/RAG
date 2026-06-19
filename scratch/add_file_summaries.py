import os
import re

OBJECTIVES = {
    'generate_architecture_doc.py': 'Generates system architecture PDF documentation containing layered diagrams and specifications.',
    'automotive_qa/scratch_test.py': 'Temporary scratchpad for sanity-checking components and LLM/pipeline functionality.',
    'automotive_qa/setup.py': 'Bootstraps the project folders, downloads external weights/models, and runs the initial ETL pipeline.',
    'automotive_qa/schema.sql': 'Database DDL defining tables, materialized views, and indexes for automotive quality tracking.',
    'automotive_qa/analytics/engine.py': 'Provides the analytics API and dynamic SQL generation via local LLM self-healing attempts.',
    'automotive_qa/analytics/graph_selector.py': 'Infers appropriate Plotly chart types and configurations for queried DataFrames.',
    'automotive_qa/analytics/views.py': 'Atomic refresh transaction manager for rebuilding simulated materialized view tables.',
    'automotive_qa/app/main.py': 'Streamlit frontend application rendering pages for RAG chat, quality dashboards, and reports.',
    'automotive_qa/auth/session.py': 'User authentication helper and session manager for saving and deleting chat histories.',
    'automotive_qa/core/cache.py': 'Implements the L1 (in-memory) and L2 (SQLite) cache layers for query routing outputs.',
    'automotive_qa/core/paths.py': 'Resolves absolute paths dynamically relative to the project root directory.',
    'automotive_qa/core/router.py': 'Internal gateway routing user queries to search, analytics, or report execution engines.',
    'automotive_qa/core/singletons.py': 'Resource lifecycle manager caching active database paths, LLM, and FAISS resources.',
    'automotive_qa/etl/pipeline.py': 'Full pipeline transforming raw Excel sheets into clean, deduplicated database records.',
    'automotive_qa/llm/client.py': 'Offline streaming Large Language Model wrapper using local GGUF models via llama-cpp.',
    'automotive_qa/nlp/pipeline.py': 'Extracts filters, classifies intents, and finds entities in raw query strings.',
    'automotive_qa/rag/document_builder.py': 'Concats structured record details into single strings optimized for semantic encoding.',
    'automotive_qa/rag/embedder.py': 'SentenceTransformer and FAISS flat cosine index wrapper for semantic record searches.',
    'automotive_qa/reports/engine.py': 'Generates stylized PDF transcripts and Word document monthly executive summaries.',
    'automotive_qa/scratch/test_gen_report.py': 'Sanity check script for testing monthly PDF and DOCX report compilers.',
    'automotive_qa/scratch/test_unresolved_report.py': 'Developer test script validating the database extraction of unresolved reports.',
    'automotive_qa/viz/charts.py': 'Renders interactive, color-harmonious Plotly charts with corporate style rules.',
}

def add_summary_to_file(filepath, rel_path, objective):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    comment_char = '--' if filepath.endswith('.sql') else '#'
    objective_line = f"{comment_char} Objective: {objective}"
    
    # Check if objective is already in the file at the top
    if objective_line in content:
        print(f"Objective already present in: {rel_path}")
        return False
        
    # Split content into lines
    lines = content.splitlines()
    
    # If the file has a docstring at the top, let's see if we should put it before the docstring or after it.
    # Put it at the absolute top of the file as requested: "in starting in comments"
    # To keep Location comment close or first, let's just insert the Objective at the absolute top of the file
    
    # Check if we already have an "Objective:" comment at the very top and remove it to avoid duplication
    cleaned_lines = []
    removed_old = False
    for line in lines:
        if line.strip().startswith(f"{comment_char} Objective:"):
            removed_old = True
            continue
        cleaned_lines.append(line)
        
    new_lines = [objective_line] + cleaned_lines
    
    new_content = '\n'.join(new_lines) + '\n'
    # Normalize consecutive empty lines
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print(f"Added objective to: {rel_path}")
    return True

def main():
    workspace_dir = r"c:\Users\maury\OneDrive\Documents\Internship\RAG"
    
    updated_count = 0
    for rel_path, objective in OBJECTIVES.items():
        filepath = os.path.join(workspace_dir, rel_path)
        if os.path.exists(filepath):
            try:
                if add_summary_to_file(filepath, rel_path, objective):
                    updated_count += 1
            except Exception as e:
                print(f"Error processing {rel_path}: {e}")
        else:
            print(f"File not found: {rel_path}")
            
    print(f"Finished. Total files updated: {updated_count}")

if __name__ == '__main__':
    main()

import os
import ast
import re

def add_parents_and_containers(node, parent=None, container=None):
    """Recursively adds parent and container references to AST nodes."""
    node.parent = parent
    node.container = container
    
    # Check if this node contains list of statements
    for name, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    add_parents_and_containers(item, node, value)
        elif isinstance(value, ast.AST):
            add_parents_and_containers(value, node, container)

def clean_file_passes(filepath, rel_path):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except Exception as e:
        print(f"Skipping AST pass cleanup for {rel_path} due to parse error: {e}")
        return False

    add_parents_and_containers(tree)

    # Find pass nodes to delete
    passes_to_delete = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            # Check if container is a list of statements and has more than 1 statement
            if node.container and len(node.container) > 1:
                passes_to_delete.append(node)

    if not passes_to_delete:
        return False

    lines = content.splitlines()
    
    # Sort from bottom to top to delete safely
    passes_to_delete_sorted = sorted(passes_to_delete, key=lambda n: n.lineno, reverse=True)

    updated = False
    for node in passes_to_delete_sorted:
        idx = node.lineno - 1
        line = lines[idx]
        if 'pass  # Imported at top' in line:
            # Delete this line (or replace with empty string)
            lines[idx] = ''
            updated = True

    if updated:
        # Reconstruct and normalize
        new_content = '\n'.join(lines) + '\n'
        # Normalize double newlines
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Removed redundant pass statements from: {rel_path}")
        return True
        
    return False

def refactor_nlp_pipeline_lambdas():
    filepath = r"c:\Users\maury\OneDrive\Documents\Internship\RAG\automotive_qa\nlp\pipeline.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Let's perform replacements for list comprehensions in nlp/pipeline.py using lambda functions
    # 1. db_countries list comprehension
    old_target1 = "db_countries = [row[0].strip() for row in cursor.fetchall() if row[0]]"
    new_target1 = "db_countries = list(filter(None, map(lambda row: row[0].strip() if row[0] else None, cursor.fetchall())))"

    # 2. self.countries list comprehension
    old_target2 = "self.countries = list(set([c.lower() for c in db_countries]))"
    new_target2 = "self.countries = list(set(map(lambda c: c.lower(), db_countries)))"

    # 3. db_models list comprehension
    old_target3 = "db_models = [row[0].strip().upper() for row in cursor.fetchall() if row[0]]"
    new_target3 = "db_models = list(filter(None, map(lambda row: row[0].strip().upper() if row[0] else None, cursor.fetchall())))"

    if old_target1 in content or old_target2 in content or old_target3 in content:
        content = content.replace(old_target1, new_target1)
        content = content.replace(old_target2, new_target2)
        content = content.replace(old_target3, new_target3)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully introduced lambda functions in nlp/pipeline.py")
        return True
    return False

def main():
    workspace_dir = r"c:\Users\maury\OneDrive\Documents\Internship\RAG"
    exclude_dirs = {'.venv', '.git', '.vscode', '.streamlit', '__pycache__', 'build', 'dist', 'node_modules'}
    
    updated_count = 0
    for root, dirs, files in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, workspace_dir).replace('\\', '/')
                
                if 'cleanup_code.py' in file or 'move_imports.py' in file:
                    continue
                    
                if clean_file_passes(filepath, rel_path):
                    updated_count += 1
                    
    refactor_nlp_pipeline_lambdas()
    print(f"Finished cleanup. Total files updated: {updated_count}")

if __name__ == '__main__':
    main()

import os
import re

def locate_end_of_imports(lines):
    """
    Scans lines of a Python file to find the index of the last top-level import statement.
    Returns the index (0-based) after the last import statement, or -1 if no imports found.
    """
    last_import_idx = -1
    in_docstring = False
    docstring_char = None
    open_parentheses = 0
    
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        
        # Handle docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = True
                docstring_char = '"""' if stripped.startswith('"""') else "'''"
                # Check if it ends on the same line
                rest = stripped[3:]
                if docstring_char in rest:
                    in_docstring = False
                idx += 1
                continue
        else:
            if docstring_char in stripped:
                in_docstring = False
            idx += 1
            continue
            
        if in_docstring:
            idx += 1
            continue
            
        # Ignore comments and blank lines
        if not stripped or stripped.startswith('#'):
            idx += 1
            continue
            
        # Check if line is an import
        is_import = stripped.startswith('import ') or stripped.startswith('from ')
        
        # If we are inside an import block or parenthesized import, trace it to the end
        if is_import or open_parentheses > 0:
            # Check for parentheses or line continuation
            # Simple parenthesis counting:
            open_parentheses += line.count('(') - line.count(')')
            
            last_import_idx = idx
            idx += 1
            continue
            
        # If we see any non-import, non-comment, non-whitespace line outside docstring/parentheses, we stop scanning
        break
        
    return last_import_idx

def process_file(filepath, rel_path):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    lines = content.splitlines()
    last_import_idx = locate_end_of_imports(lines)
    
    if last_import_idx == -1:
        # No imports found, we don't insert or we insert at the very top (after docstrings)
        # Let's not insert if no imports exist or maybe at the top. Let's see if we should insert.
        # The prompt says "after its import statement", so if there is no import, we do nothing or put it at top.
        # Usually, every file has some imports. Let's skip files without imports.
        print(f"Skipping {rel_path} (no imports found)")
        return False
        
    # Check if comment already exists near the last import statement
    comment_pattern = rf"# Location:\s*{re.escape(rel_path)}"
    
    # Check if the line immediately following last_import_idx or the one after is already the location comment
    already_has = False
    for check_idx in range(last_import_idx + 1, min(last_import_idx + 4, len(lines))):
        if re.search(comment_pattern, lines[check_idx]):
            already_has = True
            break
            
    if already_has:
        print(f"Already commented: {rel_path}")
        return False
        
    # Insert comment
    # Let's format the comment as:
    # Location: <rel_path>
    comment_line = f"# Location: {rel_path}"
    
    # Let's insert the comment line
    new_lines = lines[:last_import_idx + 1] + [comment_line] + lines[last_import_idx + 1:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')
        
    print(f"Updated: {rel_path}")
    return True

def main():
    workspace_dir = r"c:\Users\maury\OneDrive\Documents\Internship\RAG"
    exclude_dirs = {'.venv', '.git', '.vscode', '.streamlit', '__pycache__', 'build', 'dist', 'node_modules'}
    
    updated_count = 0
    for root, dirs, files in os.walk(workspace_dir):
        # Exclude directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, workspace_dir).replace('\\', '/')
                
                # Exclude system scripts or the script itself
                if 'add_location_comments.py' in file:
                    continue
                    
                try:
                    if process_file(filepath, rel_path):
                        updated_count += 1
                except Exception as e:
                    print(f"Error processing {rel_path}: {e}")
                    
    print(f"Finished. Total updated files: {updated_count}")

if __name__ == '__main__':
    main()

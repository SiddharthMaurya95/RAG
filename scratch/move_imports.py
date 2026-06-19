import os
import ast
import re
import textwrap

def is_nested(node):
    """Checks if an AST node is nested inside a function or class definition."""
    parent = getattr(node, 'parent', None)
    while parent:
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return True
        parent = getattr(parent, 'parent', None)
    return False

def add_parents(node, parent=None):
    """Recursively adds parent references to AST nodes."""
    for child in ast.iter_child_nodes(node):
        child.parent = parent
        add_parents(child, child)

def move_imports_in_file(filepath, rel_path):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except Exception as e:
        print(f"Skipping {rel_path} due to parse error: {e}")
        return False

    add_parents(tree)

    # Find all import nodes
    import_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_nodes.append(node)

    # Read lines of the file
    lines = content.splitlines()

    # Collect the import statements text and their line ranges (1-based index)
    import_ranges = []
    imports_text = []

    for node in import_nodes:
        start = node.lineno - 1
        end = node.end_lineno
        
        # Extract the lines of code for this import statement
        stmt_lines = lines[start:end]
        import_ranges.append((start, end, is_nested(node)))
        imports_text.append(stmt_lines)

    # Sort ranges from bottom to top to handle replacement safely without shifting indices
    import_ranges_sorted = sorted(import_ranges, key=lambda x: x[0], reverse=True)

    # Remove/comment out original imports from the lines
    for start, end, nested in import_ranges_sorted:
        if nested:
            # First line gets the pass statement with its correct indentation
            first_line = lines[start]
            indent = len(first_line) - len(first_line.lstrip())
            lines[start] = ' ' * indent + 'pass  # Imported at top'
            # Subsequent lines in the multi-line block get replaced with empty lines
            for idx in range(start + 1, end):
                lines[idx] = ''
        else:
            for idx in range(start, end):
                lines[idx] = ''

    # Now we need to reconstruct the file with all imports at the top.
    # We should identify if there is a module docstring.
    docstring = ast.get_docstring(tree)
    docstring_end_idx = 0
    if docstring:
        # Find where docstring ends
        first_body = tree.body[0] if tree.body else None
        if isinstance(first_body, ast.Expr) and isinstance(first_body.value, ast.Constant) and isinstance(first_body.value.value, str):
            docstring_end_idx = first_body.end_lineno

    # Filter out duplicate import statements text and dedent them
    unique_imports = []
    seen_imports = set()
    for stmt_lines in imports_text:
        stmt_str = '\n'.join(stmt_lines)
        stmt_str_dedented = textwrap.dedent(stmt_str).strip()
        if stmt_str_dedented not in seen_imports:
            seen_imports.add(stmt_str_dedented)
            unique_imports.append(stmt_str_dedented)

    # Let's extract any bootstrap code (sys.path updates) and put it at the very top.
    bootstrap_lines = []
    remaining_lines_clean = []
    in_bootstrap = False
    
    for line in lines:
        stripped = line.strip()
        
        # Check if we should start bootstrap collection
        if 'sys.path.append' in stripped or 'os.add_dll_directory' in stripped or 'os.environ[\'PATH\']' in stripped:
            bootstrap_lines.append(line)
        elif stripped.startswith('if os.name == \'nt\':') or stripped.startswith('if os.name == "nt":'):
            in_bootstrap = True
            bootstrap_lines.append(line)
        elif in_bootstrap:
            # Check if this line marks the end of the bootstrap block (has no indentation and is not empty/comment/if structure)
            if line.strip() and not line.startswith(' ') and not line.startswith('\t') and not stripped.startswith('if ') and not stripped.startswith('elif ') and not stripped.startswith('else:'):
                in_bootstrap = False
                remaining_lines_clean.append(line)
            else:
                bootstrap_lines.append(line)
        else:
            remaining_lines_clean.append(line)

    # Split unique imports into system/standard bootstrap (os, sys) and others
    bootstrap_imports = []
    normal_imports = []
    for imp in unique_imports:
        if any(x in imp for x in ['import os', 'import sys']):
            bootstrap_imports.append(imp)
        else:
            normal_imports.append(imp)

    # Dedent bootstrap lines
    if bootstrap_lines:
        bootstrap_block = '\n'.join(bootstrap_lines)
        bootstrap_block_dedented = textwrap.dedent(bootstrap_block).strip()
        bootstrap_lines = bootstrap_block_dedented.splitlines()

    # Let's assemble the new content
    new_lines = []
    
    # 1. Docstring if any
    if docstring_end_idx > 0:
        new_lines.extend(remaining_lines_clean[:docstring_end_idx])
        remaining_lines_clean = remaining_lines_clean[docstring_end_idx:]

    # 2. Bootstrap imports (os, sys)
    if bootstrap_imports:
        new_lines.extend(bootstrap_imports)
        new_lines.append('')

    # 3. Bootstrap code (sys.path / DLL setup)
    if bootstrap_lines:
        new_lines.extend(bootstrap_lines)
        new_lines.append('')

    # 4. All other imports
    if normal_imports:
        new_lines.extend(normal_imports)
        new_lines.append('')

    # 5. Location comment
    new_lines.append(f"# Location: {rel_path}")
    new_lines.append('')

    # 6. Rest of the file
    # Remove existing # Location comments from the rest of the file
    cleaned_body = []
    for line in remaining_lines_clean:
        if not line.strip().startswith(f"# Location: {rel_path}"):
            cleaned_body.append(line)

    new_lines.extend(cleaned_body)

    # Write back
    new_content = '\n'.join(new_lines)
    new_content = re_normalize_newlines(new_content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Consolidated imports in: {rel_path}")
    return True

def re_normalize_newlines(content):
    # Replace 3 or more consecutive newlines with 2 newlines
    return re.sub(r'\n{3,}', '\n\n', content).strip() + '\n'

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
                
                if 'add_location_comments.py' in file or 'move_imports.py' in file:
                    continue
                    
                try:
                    if move_imports_in_file(filepath, rel_path):
                        updated_count += 1
                except Exception as e:
                    print(f"Error processing {rel_path}: {e}")
                    
    print(f"Finished consolidating imports. Total files updated: {updated_count}")

if __name__ == '__main__':
    main()

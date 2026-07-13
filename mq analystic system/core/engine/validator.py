def ensure_result_assignment(code):
    lines = [l.strip() for l in code.split("\n") if l.strip()]

    if any("result =" in l for l in lines):
        return code

    for i, line in enumerate(lines):
        if "df[" in line and "plot" not in line:
            lines.insert(i + 1, f"result = {line}")
            break

    return "\n".join(lines)

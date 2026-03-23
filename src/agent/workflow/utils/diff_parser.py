import re

def annotate_diff_with_line_numbers(raw_diff: str) -> str:
    """
    Parses a unified diff and annotates each line with its destination (new file) line number.
    This helps LLMs accurately identify line numbers in the modified file.
    
    Logic:
    - Tracks the 'New File' (+) line counter using hunk headers.
    - Prepends '[Line X]' to context lines (' ') and added lines ('+').
    - Skips removed lines ('-') to avoid line number hallucinations.
    """
    annotated_lines = []
    current_line = 0
    
    lines = raw_diff.splitlines()
    for line in lines:
        # 1. Detect Hunk Headers: @@ -R,r +N,n @@
        hunk_match = re.match(r'^@@ -\d+,\d+ \+(\d+),\d+ @@', line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            annotated_lines.append(line)
            continue
        
        # 2. Skip deleted lines (-)
        if line.startswith('-'):
            continue
            
        # 3. Handle Context lines (' ') and Added lines ('+')
        if line.startswith(' ') or line.startswith('+'):
            annotated_lines.append(f"[Line {current_line}] {line}")
            current_line += 1
        else:
            # 4. Keep other diff metadata (File headers, etc.)
            annotated_lines.append(line)
            
    return "\n".join(annotated_lines)

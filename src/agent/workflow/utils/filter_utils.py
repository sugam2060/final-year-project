import re

def apply_antigravity_filter(raw_diff: str, ignore_patterns: set[str]) -> str:
    """
    Splits a standard unified diff, checks file headers against ignore patterns (e.g., .swarmignore),
    and reconstructs a clean, lightweight diff.
    """
    if not raw_diff:
        return ""
        
    # Standard unified diff pattern for file headers:
    # diff --git a/path/to/file b/path/to/file
    # --- a/path/to/file
    # +++ b/path/to/file
    
    # We split the diff by the start of each file's diff
    file_diffs = re.split(r'^(diff --git .*)$', raw_diff, flags=re.MULTILINE)
    
    # Reassemble re.split results into [ (header, diff_body), ... ]
    # re.split(r'^(pattern)$', text) returns [ '' , 'pattern', 'rest', 'pattern', ... ]
    processed_diffs = []
    for i in range(1, len(file_diffs), 2):
        header = file_diffs[i]
        body = file_diffs[i+1] if i + 1 < len(file_diffs) else ""
        
        # Extract filename from header
        # diff --git a/file.txt b/file.txt
        match = re.search(r'b/(.*)$', header)
        if match:
            filename = match.group(1).strip()
            
            # Use O(1) set lookup for performance
            should_ignore = False
            for pattern in ignore_patterns:
                # Basic glob-like support: *.svg, etc.
                if pattern.startswith('*.'):
                    if filename.endswith(pattern[1:]):
                        should_ignore = True
                        break
                elif pattern == filename or filename.startswith(pattern + '/'):
                    should_ignore = True
                    break
            
            if not should_ignore:
                processed_diffs.append(header + body)
                
    return "".join(processed_diffs)

def enforce_size_guardrail(filtered_diff: str, max_lines: int = 1000) -> dict:
    """
    Counts the + and - lines of actual code (excluding comments/whitespace).
    Returns a dict with is_valid flag and calculated line_count.
    """
    line_count = 0
    lines = filtered_diff.splitlines()
    
    for line in lines:
        # We only care about added (+) or removed (-) lines
        # Ignore diff metadata like --- or +++
        if (line.startswith('+') and not line.startswith('+++')) or \
           (line.startswith('-') and not line.startswith('---')):
            
            content = line[1:].strip()
            # Basic core logic detection: ignore empty lines and single-line comments
            # (Matches common C-style, Python, JS comments)
            if content and not content.startswith(('#', '//', '/*', '*', '*/')):
                line_count += 1
                
    return {
        "is_valid": line_count <= max_lines,
        "line_count": line_count
    }

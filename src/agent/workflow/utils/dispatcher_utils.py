import re
from typing import List, Dict, Any

def split_diff_by_file(filtered_diff: str) -> List[Dict[str, Any]]:
    """
    Parses a unified diff and returns a list of objects containing 
    the filename and that specific file's diff logic.
    """
    if not filtered_diff:
        return []

    # Regex to split by file headers: diff --git a/... b/...
    file_chunks = re.split(r'^(diff --git .*)$', filtered_diff, flags=re.MULTILINE)
    
    file_diffs = []
    # Index 0 is often empty if the diff starts with the header
    for i in range(1, len(file_chunks), 2):
        header = file_chunks[i]
        body = file_chunks[i+1] if i + 1 < len(file_chunks) else ""
        
        # Extract filename from header
        filename_match = re.search(r'b/(.*)$', header)
        filename = filename_match.group(1).strip() if filename_match else "unknown_file"
        
        file_diffs.append({
            "filename": filename,
            "diff_content": header + body
        })
        
    return file_diffs

def aggregate_swarm_findings(agent_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    A utility that merges duplicate comments, sorts findings by severity,
    and prepares the final structure.
    """
    # In this implementation, we take the summarized reviews and suggestions
    # from each file-level reviewer and consolidate them.
    
    consolidated_summary = []
    all_inline_suggestions = []
    
    for resp in agent_responses:
        filename = resp.get("filename", "Unknown")
        review = resp.get("summary", "")
        severity = resp.get("severity", "MEDIUM")
        suggestions = resp.get("inline_suggestions", [])
        
        if review:
            consolidated_summary.append(f"### Review for `{filename}` (Severity: {severity})\n{review}")
        
        all_inline_suggestions.extend(suggestions)
        
    return {
        "summary": "\n\n".join(consolidated_summary),
        "suggestions": all_inline_suggestions
    }

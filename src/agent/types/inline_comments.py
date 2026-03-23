from pydantic import BaseModel, Field
from typing import List

class InlineSuggestion(BaseModel):
    file_path: str = Field(description="The exact relative path to the file in the repository.")
    line_number: int = Field(description="The exact line number in the modified file where the issue occurs.")
    suggestion_body: str = Field(description="The comment body. MUST include the corrected code wrapped in standard GitHub ```suggestion\n [code] \n``` markdown block.")

class SynthesizerOutput(BaseModel):
    general_summary: str = Field(description="The overall prioritized markdown summary of the Blockers and Suggestions.")
    inline_suggestions: List[InlineSuggestion] = Field(description="A list of specific line-by-line code fixes.")

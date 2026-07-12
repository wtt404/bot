from ai.client import chat_completion
from tools.base import Tool

SYSTEM_PROMPT = """
You summarize text clearly and concisely.

Rules:
- Keep it short - a few sentences, unless the user explicitly asks for more detail.
- Preserve the key facts, names, numbers, and claims. Do not lose specifics.
- Do not add opinions or information not present in the original text.
- Do not pad with filler phrases like "This text discusses..." - get straight to the content.
"""

class SummarizeTool(Tool):
    name = "summarize"
    description = "Summarize a piece of text concisely, preserving key facts."
    parameters_json_schema = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to summarize.",
            },
        },
        "required": ["text"],
    }

    async def execute(self, text: str):
        try:
            response = await chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            print("Summarize failed:", e, flush=True)
            return None
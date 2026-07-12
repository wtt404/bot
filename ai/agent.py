import json

from ai.client import chat_completion
from ai.prompts import SYSTEM_PROMPT
from tools import TOOLS


MAX_TOOL_TURNS = 3


def _build_tools():
    if not TOOLS:
        return None

    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_json_schema,
            },
        }
        for tool in TOOLS.values()
    ]


async def ai(message: str) -> str:
    tools = _build_tools()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    for _ in range(MAX_TOOL_TURNS):
        try:
            response = await chat_completion(messages=messages, tools=tools)
        except Exception as e:
            print(f"All AI models failed: {e}", flush=True)
            return "I couldn't reach any AI model right now — try again in a bit."

        if not response.choices:
            print("No choices in response.", flush=True)
            return "I couldn't come up with a response for that."

        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or "I couldn't come up with a text response for that."

        messages.append(msg.model_dump(exclude_none=True))

        for call in msg.tool_calls:
            print(f"AI TOOL CALL: {call.function.name} args={call.function.arguments}", flush=True)
            tool = TOOLS.get(call.function.name)

            try:
                args = json.loads(call.function.arguments or "{}")
            except Exception:
                args = {}

            if tool is None:
                result = f"Unknown tool: {call.function.name}"
            else:
                try:
                    result = await tool.execute(**args)
                except Exception as e:
                    print(f"Tool '{call.function.name}' failed:", e, flush=True)
                    result = f"Error running tool: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result) if result is not None else "No result.",
            })

    return "I tried using a tool a few times but couldn't finish that one — try rephrasing?"
"""AI project planning and source generation through the OpenAI Responses API."""
import json
import os
from typing import Any
import httpx

SYSTEM_INSTRUCTIONS = """
You are the senior software architect and coding partner in Analytics InAdvance AI Project Studio.
Turn plain-language ideas into practical software projects. Ask concise clarifying questions only when essential; otherwise make sensible assumptions and proceed.
Support web apps, APIs, mobile backends, AI/ML, data analytics, automation, cloud, cybersecurity education and developer tools.
Never claim code was executed, tested, deployed or connected to a real service unless it actually was.
Never include secrets or real credentials. Use environment variables and .env.example placeholders.
For new projects or explicit build requests, provide a concise project plan and a small coherent set of complete starter files. For follow-ups, return only new or changed files.
Return ONLY valid JSON with keys: assistant_message (Markdown string), project_name (string), project_plan (Markdown string), files (array of {path,content,language}), next_steps (array of strings).
Limit each response to 12 files and about 45,000 total file-content characters. Prefer a small working vertical slice over empty placeholders. Do not wrap JSON in Markdown fences.
"""

class ProjectAIError(Exception):
    pass

async def generate_project_reply(messages: list[dict[str, str]], mode: str = "chat") -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ProjectAIError("AI is not configured yet. Add OPENAI_API_KEY in your Render service Environment settings, save and redeploy. Keep the key secret; never put it in GitHub or the browser.")
    model = os.getenv("OPENAI_MODEL", "gpt-6.2-sol").strip() or "gpt-6.2-sol"
    task_hint = ("The user requested one-click project generation. Create an initial plan and useful starter source files now."
                 if mode == "generate" else
                 "Continue the project-building conversation. If the user requests a build or change, return the relevant complete files.")
    payload = {"model": model, "instructions": SYSTEM_INSTRUCTIONS + "\nCURRENT TASK: " + task_hint,
               "input": messages[-16:], "text": {"format": {"type": "json_object"}}, "max_output_tokens": 9000}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post("https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload)
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", "The AI provider rejected the request.")
            except Exception:
                detail = "The AI provider rejected the request."
            raise ProjectAIError(f"AI request failed ({response.status_code}): {detail}")
        data = response.json()
        output_text = data.get("output_text")
        if not output_text:
            output_text = "\n".join(c.get("text", "") for item in data.get("output", [])
                for c in item.get("content", []) if c.get("type") == "output_text")
        if not output_text:
            raise ProjectAIError("The AI returned an empty response. Please try again.")
        try:
            result = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProjectAIError("The AI response could not be read. Please try again.") from exc
        if not isinstance(result, dict):
            raise ProjectAIError("The AI response format was invalid.")
        result.setdefault("assistant_message", "I have prepared the next project step.")
        result.setdefault("project_name", "")
        result.setdefault("project_plan", "")
        result.setdefault("files", [])
        result.setdefault("next_steps", [])
        if not isinstance(result["files"], list):
            result["files"] = []
        result["files"] = [f for f in result["files"][:12]
            if isinstance(f, dict) and isinstance(f.get("path"), str) and isinstance(f.get("content"), str)]
        return result
    except httpx.TimeoutException as exc:
        raise ProjectAIError("The AI request timed out. Try a shorter prompt.") from exc
    except httpx.HTTPError as exc:
        raise ProjectAIError("Could not connect to the AI service. Please try again.") from exc

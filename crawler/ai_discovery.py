import json
import os
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
model = genai.GenerativeModel("gemini-1.5-flash")


async def discover_links(page, current_url: str) -> list[str]:
    """Use Gemini to identify navigation links a human would follow."""
    try:
        html_snippet = await page.eval_on_selector(
            "body",
            "el => el.innerHTML.slice(0, 8000)"
        )

        prompt = f"""You are analyzing a documentation page navigation.

Current URL: {current_url}

Page HTML (truncated):
{html_snippet}

Extract all navigation links (sidebar menus, top nav, expandable sections) that lead to documentation subpages.
Return ONLY a JSON array of absolute URLs. No explanation. Example: ["https://...", "https://..."]
Focus on links that go deeper into the documentation structure."""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        links = json.loads(text.strip())
        return [l for l in links if isinstance(l, str) and l.startswith("http")]

    except Exception:
        return []

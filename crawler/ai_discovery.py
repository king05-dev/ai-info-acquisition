import json
import os
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
model = genai.GenerativeModel("gemini-1.5-flash")


async def discover_links(page, current_url: str) -> list[str]:
    """Use Gemini to identify navigation links a human would follow."""
    try:
        html_snippet = await page.eval_on_selector(
            "body",
            "el => el.innerHTML.slice(0, 8000)"
        )

        prompt = f"""You are an AI navigation agent crawling documentation to achieve maximum depth.

Current URL: {current_url}

Page HTML (truncated):
{html_snippet}

Your goal: find the links that go DEEPEST into the documentation from this page.
Priority order:
1. Sub-pages of the current section (same URL prefix, going deeper)
2. Linked API reference pages or sub-guides referenced in the page body
3. Child pages in the sidebar that are beneath the current page

Return ONLY a JSON array of up to 8 absolute URLs, ordered by depth priority (deepest first).
No explanation. Example: ["https://...", "https://..."]
Exclude: top-nav links, breadcrumb parents, external sites, anchor-only links."""

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

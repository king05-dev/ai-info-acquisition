import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


async def discover_links(page, current_url: str) -> list[str]:
    """Use Claude to identify navigation links a human would follow."""
    try:
        html_snippet = await page.eval_on_selector(
            "body",
            "el => el.innerHTML.slice(0, 8000)"
        )

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are analyzing a documentation page navigation.

Current URL: {current_url}

Page HTML (truncated):
{html_snippet}

Extract all navigation links (sidebar menus, top nav, expandable sections) that lead to documentation subpages.
Return ONLY a JSON array of absolute URLs. No explanation. Example: ["https://...", "https://..."]
Focus on links that go deeper into the documentation structure."""
                }
            ]
        )

        text = message.content[0].text.strip()
        links = json.loads(text)
        return [l for l in links if isinstance(l, str) and l.startswith("http")]

    except Exception:
        return []

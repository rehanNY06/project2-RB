"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()
    keywords = description.lower().split()
    scored = []

    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue

        # Build searchable text from all relevant fields
        parts = [
            item["title"],
            item["description"],
            item["category"],
            " ".join(item["style_tags"]),
            " ".join(item["colors"]),
            item["brand"] or "",          # brand can be None
        ]
        haystack = " ".join(parts).lower()
        score = sum(1 for kw in keywords if kw in haystack)

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()

    item_desc = (
        f"{new_item['title']} (category: {new_item['category']}, "
        f"colors: {', '.join(new_item['colors'])}, "
        f"style: {', '.join(new_item['style_tags'])})"
    )

    items = wardrobe.get("items", [])
    if not items:
        # Empty wardrobe → general styling advice, no crash
        prompt = (
            f"A shopper is considering this secondhand item:\n{item_desc}\n\n"
            "They haven't listed their wardrobe yet. Suggest 1-2 general outfit "
            "ideas: what kinds of pieces pair well with it, and what vibe it suits. "
            "Keep it to a few sentences, concrete and wearable."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {w['name']} ({', '.join(w['colors'])}; {', '.join(w['style_tags'])})"
            for w in items
        )
        prompt = (
            f"A shopper is considering this secondhand item:\n{item_desc}\n\n"
            f"Here is their current wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits pairing the new item with specific pieces "
            "named from their wardrobe. Be concrete about what goes with what. "
            "Keep it to a few sentences."
        )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Couldn't generate an outfit suggestion right now ({e})."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    # Guard: empty/whitespace-only outfit → error string, no LLM call
    if not outfit or not outfit.strip():
        return "Can't make a fit card without an outfit suggestion."

    client = _get_groq_client()

    prompt = (
        f"Write a short, casual outfit caption for a social post (2-4 sentences). "
        f"The thrifted item: {new_item['title']}, ${new_item['price']:.0f}, "
        f"found on {new_item['platform']}. The outfit: {outfit}\n\n"
        "Sound like a real OOTD post, not a product description. Mention the item "
        "name, price, and platform naturally, once each. Capture the vibe."
    )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,   # higher than suggest_outfit → varied captions
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Couldn't generate a fit card right now ({e})."

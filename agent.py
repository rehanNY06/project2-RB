"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from a natural-language query."""
    # max_price: a number, optionally preceded by under/below/less than and/or $
    price_match = re.search(
        r"(?:under|below|less than)?\s*\$?\s*(\d+(?:\.\d+)?)",
        query, re.I,
    )
    max_price = float(price_match.group(1)) if price_match else None

    # size: look for "size M", "size XXS", etc.
    size_match = re.search(r"size\s+([A-Za-z0-9/]+)", query, re.I)
    size = size_match.group(1).upper() if size_match else None

    # description: the query with the price/size phrases stripped out
    description = query
    if price_match:
        description = description.replace(price_match.group(0), "")
    if size_match:
        description = description.replace(size_match.group(0), "")
    description = re.sub(r"\b(looking for|a|an|the|i want|find me|under|below)\b", "", description, flags=re.I)
    description = re.sub(r"\s+", " ", description).strip(" ,.$")

    return {"description": description, "size": size, "max_price": max_price}


def run_agent(query: str, wardrobe: dict) -> dict:
    # Step 1: fresh session
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into description / size / max_price
    session["parsed"] = _parse_query(query)
    p = session["parsed"]

    # Step 3: search
    session["search_results"] = search_listings(
        p["description"], size=p["size"], max_price=p["max_price"]
    )
    if not session["search_results"]:
        session["error"] = (
            f"No listings matched '{p['description']}'"
            + (f" in size {p['size']}" if p["size"] else "")
            + (f" under ${p['max_price']:.0f}" if p["max_price"] else "")
            + ". Try broadening your search — raise the price, drop the size filter, "
            "or use simpler keywords."
        )
        return session            # early exit — do NOT call suggest_outfit

    # Step 4: select the top result
    session["selected_item"] = session["search_results"][0]

    # Step 5: suggest an outfit
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: fit card
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: done
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

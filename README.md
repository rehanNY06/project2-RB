# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

## Tool Inventory

### search_listings

- **Inputs:** `description` (str) — keywords for what the user wants; `size` (str or None) — size to filter to, skipped if None; `max_price` (float or None) — highest acceptable price, skipped if None.
- **Output:** a list of listing dicts sorted by relevance (most keyword matches first). Each dict has the full listing fields: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns an empty list if nothing matches.
- **Purpose:** finds matching secondhand items in the dataset.

### suggest_outfit

- **Inputs:** `new_item` (dict) — a listing dict, usually the top search result; `wardrobe` (dict) — the user's wardrobe with an `items` list, which may be empty.
- **Output:** a string describing one or two outfit ideas that pair the new item with pieces the user owns.
- **Purpose:** styles the found item against the user's wardrobe using the LLM.

### create_fit_card

- **Inputs:** `outfit` (str) — the outfit suggestion from `suggest_outfit`; `new_item` (dict) — the listing dict for the found item.
- **Output:** a short caption string (a few sentences) that mentions the item name, price, and platform, written like a real outfit post. The output varies between runs.
- **Purpose:** turns the outfit into something the user could caption a post with.

---

## How the Planning Loop Works

The loop runs in `run_agent()` in `agent.py`. It is a sequence of gated steps, where each step depends on what the previous one returned, rather than calling all three tools every time.

1. Start a fresh `session` dict for the run.
2. Parse the query into a description, size, and max_price with `_parse_query()`, and store it in `session["parsed"]`.
3. Call `search_listings()` with the parsed values. Check the result:
   - If the list is empty, set `session["error"]` to a helpful message and return right away. `suggest_outfit` and `create_fit_card` are never called.
   - If there are results, store the top one as `session["selected_item"]` and continue.
4. Call `suggest_outfit()` with the selected item and the wardrobe, and store the result in `session["outfit_suggestion"]`.
5. Call `create_fit_card()` with the suggestion and the selected item, and store the result in `session["fit_card"]`.
6. Return the session.

The branch in step 3 is the key part — it is what makes the agent respond to results instead of running a fixed pipeline. When the search finds nothing, the loop ends early.

---

## State Management

All information for one run lives in a single `session` dict created by `_new_session()`. Each tool's output is written into the session under a named key, and later tools read their inputs from that same dict, so nothing has to be re-entered or re-derived.

- `session["query"]` — the original user text.
- `session["parsed"]` — the description, size, and max_price pulled from the query.
- `session["search_results"]` — the list returned by `search_listings`.
- `session["selected_item"]` — the top result, used as the input to both `suggest_outfit` and `create_fit_card`.
- `session["wardrobe"]` — the wardrobe passed into `suggest_outfit`.
- `session["outfit_suggestion"]` — the string from `suggest_outfit`, used as the input to `create_fit_card`.
- `session["fit_card"]` — the final caption. Stays None if the run ends early.
- `session["error"]` — set only when the search returns nothing. Stays None otherwise.

The item found in step 3 is the same dict styled in step 4 and captioned in step 5 — there are no copies and no re-entry between steps.

---

## Error Handling

| Tool | Failure mode | What happens |
|------|-------------|--------------|
| search_listings | No listings match | Returns an empty list. The planning loop sets `session["error"]` with a message telling the user what was searched and what to try (raise the price, drop the size, simpler keywords), then stops before the other tools run. |
| suggest_outfit | Wardrobe is empty | Does not crash. Falls back to asking the LLM for general styling advice for the item on its own, instead of naming specific owned pieces. The loop continues normally. |
| create_fit_card | Outfit string is empty | Skips the LLM call and returns the message "Can't make a fit card without an outfit suggestion." instead of raising an error. |

Two of these are handled inside the tool itself (`suggest_outfit` and `create_fit_card`), and one is handled by the planning loop (`search_listings` returns an empty list, and the loop decides to stop). That was a deliberate choice — search failing is a reason to end the whole run, while the other two can recover on their own and keep going.

**Concrete example from testing:** running `create_fit_card('', results[0])` returned the string "Can't make a fit card without an outfit suggestion." with no exception. Running `suggest_outfit(results[0], get_empty_wardrobe())` returned a paragraph of general styling advice (high-waisted jeans, layering ideas, complementary colors) rather than crashing on the empty wardrobe. And searching for "designer ballgown" in size XXS under $5 returned `[]`, which the agent turned into a helpful error message.

---

## Spec Reflection

**One way the spec helped:** writing planning.md first made me break the agent into clear pieces before coding — defining each tool's inputs, outputs, and failure mode on its own. That made the whole thing easier to understand, and it gave me something specific to check the generated code against instead of figuring things out as I went.

**One way the implementation diverged:** my tool specs assumed `search_listings` would get a clean description, size, and price. But the `run_agent` stub passed in one query string, so I had to add a `_parse_query` step using regex to pull those three values out of the sentence before searching. That parsing layer was not in my original spec, and it took a couple of tries to get the price regex matching "under $30" correctly.

---

## AI Usage

**Instance 1 — search_listings.** I gave the AI my Tool 1 spec (inputs, return value, failure mode) and asked it to implement the function using `load_listings()` from the data loader. The first version scored keyword matches only against the title, description, and style_tags. I changed it to also match against `category`, `brand`, and `colors`, so a query like "black jacket" or a brand name would actually find things — and I added a guard for `brand` being None, since some listings have no brand.

**Instance 2 — planning loop and query parsing.** I gave the AI my agent diagram plus the Planning Loop and State Management sections and asked it to implement `run_agent()`. The generated query parser had a bug — the price regex did not capture "under $30," so `max_price` came back as None and "under" was left stuck in the description. I caught it by testing the parser on its own before trusting the whole agent, then fixed the regex pattern (it took two passes to get right).
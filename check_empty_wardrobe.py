from tools import search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe

results = search_listings("vintage graphic tee", size=None, max_price=50)
print(suggest_outfit(results[0], get_empty_wardrobe()))
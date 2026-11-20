# Hole-in-the-Wall

A search engine for finding hole-in-the-wall restaurants in the Seattle area, with a React + TypeScript UI and a local Python search API. Search for food, restaurant names, or words reviewers use to describe a place, then filter by city.

Built for INFO 376 using the [Google Local reviews dataset](https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/) (UCSD). Search uses an inverted index and BM25 written from scratch. The notebooks also explore ambience vocabulary; automatic query expansion with that vocabulary is not currently enabled in the app.

**Coverage:** restaurants in Seattle, Bellevue, Redmond, Shoreline, Lynnwood, Bothell, Kirkland, Renton, Kent, Tukwila, Edmonds, and Federal Way. The documented cleaned dataset contains 4,931 restaurants and approximately 1.09 million reviews with text; the app indexes a sample of up to 10,000 reviews.

## Setup

Use Node.js with npm and Python 3.11 or newer. Run these commands from the repository root.

Install frontend dependencies once:

```sh
npm install
```

Install Python dependencies in a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The first time the API starts, it downloads the WordNet data used for query expansion (needs internet once). If the download fails, search still works without synonyms.


To run the notebooks, also install Jupyter in the same environment:

```sh
python -m pip install jupyter
```

## Data

Download the two Washington files from the dataset page into `data/` and unzip them:

```sh
mkdir -p data
curl -L -o data/meta-Washington.json.gz https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/meta-Washington.json.gz
curl -L -o data/review-Washington.json.gz https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/review-Washington.json.gz
gunzip data/meta-Washington.json.gz data/review-Washington.json.gz
```

The review file is approximately 1.3 GB compressed and 5 GB unzipped. `data/` is ignored by Git; teammates need to generate or copy the data separately. Do not commit data files.

Run the notebooks top to bottom in this order. File names in the table are relative to `data/`.

| # | Notebook | Reads | Writes |
|---|----------|-------|--------|
| 1 | `filter_seattle.ipynb` | `meta-Washington.json`, `review-Washington.json` | `meta-SeattleArea.json`, `review-SeattleArea.json` |
| 2 | `clean_data.ipynb` | `meta-SeattleArea.json`, `review-SeattleArea.json` | `restaurants.csv`, `reviews.parquet` |
| 3 | `ambience.ipynb` | — | `ambience.json` |
| 4 | `inverted_index_bm25.ipynb` | `restaurants.csv`, `reviews.parquet`, `ambience.json` | — |

Steps 1 and 2 only need to be rerun if the raw data or the filtering/cleaning rules change. Step 1 takes several minutes because of the review file's size. The app needs at least step 1; step 2 gives it the cleaned data.

## Run the app

Start the API in one terminal with your Python environment activated. Once `data/reviews.parquet` exists (it does after running `clean_data.ipynb`), the API needs `pyarrow` and fails with `ModuleNotFoundError: No module named 'pyarrow'` under a Python that lacks it:

```sh
python3 server.py
```

Start the frontend in another terminal:

```sh
npm run dev
```

Open the Local URL printed by Vite, normally [http://localhost:5173](http://localhost:5173). Keep both terminals running. Vite forwards `/api` requests to the Python server at [http://127.0.0.1:8000](http://127.0.0.1:8000).

UI source changes reload through Vite. Restart `python3 server.py` after generating or updating data files.

## Features

- Search by food, restaurant name, category, or review terms (default: `ramen` in Seattle).
- Filter to one of the 12 cities, or **Anywhere**.
- See up to 20 ranked results with ratings, review counts, matched terms, and matching review excerpts.
- Open **View restaurant** for details and an **Open in Maps** link.
- Save restaurants with the heart button (saves reset on reload).

## How search works

The API reads saved data files; it does not execute notebooks or read their displayed cell outputs. It prefers `restaurants.csv` and `reviews.parquet`, falling back to `meta-SeattleArea.json` and `review-SeattleArea.json` when the corresponding cleaned files are absent. If review files are missing, names and categories remain searchable and the UI displays a notice. Permanently closed businesses are excluded.

Review indexing is capped at 10,000 reviews, following the notebook sample size. The Parquet path reads the first batch of up to 10,000 rows and filters unusable reviews; the JSON path collects the first 10,000 usable, deduplicated reviews belonging to loaded businesses. Some restaurants therefore have no indexed reviews.

The API uses the notebook's tokenizer and BM25 parameters (`k1=1.5`, `b=0.75`), adds name/category documents for direct business searches, and sums matching document scores per restaurant. This is an adaptation of the notebook, so rankings differ from review-only BM25. City selection filters businesses by city; it does not calculate distance from the user.

Review counts and average ratings come from business metadata, not the indexed sample. Excerpts are matching review text, not generated restaurant descriptions. Matched-term tags show query terms found in indexed documents. Matched-term tags include synonym matches.

**Query expansion.** Each query word is expanded with WordNet (via NLTK): via base form (`noodles` → `noodle`) plus up to 5 single-word synonyms from its 2 most common senses (`cheap` → `inexpensive`). Only synonyms that appear in the index are used, and they will count half as much as the typed words (`EXPANSION_WEIGHT = 0.5` in `server/search.py`), so exact matches will still rank first. The API does not currently load `ambience.json`.

## Development

### Project files

| File | Purpose |
|------|---------|
| `filter_seattle.ipynb` | Filters Washington data to Seattle-area restaurants |
| `clean_data.ipynb` | Cleans restaurants and reviews into `restaurants.csv` and `reviews.parquet` |
| `ambience.ipynb` | Ambience word lists, saved to `ambience.json` |
| `inverted_index_bm25.ipynb` | Inverted index and BM25 prototype on a review sample |
| `load_data.py` | Typed data-loading helpers for notebook work |
| `server.py` | Local HTTP API entry point, bound to loopback only |
| `server/data_loader.py` | Adapters for notebook exports and metadata fallback |
| `server/search.py` | Tokenizer, inverted index, BM25 scoring, and WordNet query expansion |
| `src/App.tsx` | Search form, city selection, result cards, session-only save controls, and restaurant details dialog |
| `src/index.css` | Cream-and-green styling, responsive layout, and Tailwind v4 styles |
| `src/main.tsx`, `index.html` | React entry point and HTML shell |
| `vite.config.ts`, `tsconfig.json`, `package.json` | Vite, Tailwind plugin, TypeScript configuration, and npm scripts |
| `tests/test_search.py` | Search and data-loading tests |

### Loading the clean data

For notebook work, use `load_data.py` to load `restaurants.csv` and `reviews.parquet`. It restores the right types (IDs as text, `category` as a list, `misc` as a dict, `price` as 1–4 or `<NA>`). The API has its own adapters in `server/data_loader.py`.

```python
from load_data import load_restaurants, load_reviews

restaurants = load_restaurants()  # one row per restaurant
reviews = load_reviews()          # one row per review; join on gmap_id
```

**restaurants.csv:** `gmap_id, name, address, city, latitude, longitude, category, price, avg_rating, num_of_reviews, description, misc, temporarily_closed`

**reviews.parquet:** `gmap_id, user_id, time, rating, text`

See `clean_data.ipynb` for what was removed and why (permanently closed restaurants, reviews without text, duplicates).

### API

`GET /api/search?q=ramen&city=Seattle&limit=20` returns a response shaped like this:

```json
{
  "query": "ramen",
  "city": "Seattle",
  "total": 1,
  "expansions": {},
  "results": [
    {
      "id": "business-gmap-id",
      "name": "Example result",
      "city": "Seattle",
      "address": "Business address",
      "category_primary": "Ramen restaurant",
      "categories": ["Ramen restaurant"],
      "rating": 4.5,
      "review_count": 50,
      "summary_text": "",
      "matched_terms": ["ramen"],
      "score": 1.2
    }
  ],
  "data_status": {
    "mode": "metadata",
    "metadata_source": "meta-SeattleArea.json",
    "review_source": null,
    "indexed_reviews": 0
  }
}
```

This is an illustrative response, not a real business. `total` counts returned results, capped by `limit` (1–100; default 20). Omit `city` to search all cities. An empty query lists businesses by rating. `GET /api/health` reports data sources and indexed review count.

### Tests

```sh
npm run build
python3 -m unittest discover -s tests -v
```

This setup is for local development. `npm run preview` previews the built frontend and does not proxy the Python API; use `npm run dev` for the connected app.

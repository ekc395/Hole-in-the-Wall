# Hole-in-the-Wall

A search engine for finding hole-in-the-wall restaurants in the Seattle area. Users describe the vibe they want and get nearby restaurants ranked by what reviewers actually say about them.

Built for INFO 376 using the [Google Local reviews dataset](https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/) (UCSD). Search runs on review text with an inverted index and BM25 written from scratch, expanded with ambience word lists, and combined with a location filter.

**Coverage:** restaurants in Seattle, Bellevue, Redmond, Shoreline, Lynnwood, Bothell, Kirkland, Renton, Kent, Tukwila, Edmonds, and Federal Way (4,931 open restaurants, ~1.09M reviews with text).

## Setup

1. Python 3.11 with pandas, pyarrow, and Jupyter:
   ```
   pip install pandas pyarrow jupyter
   ```
2. Download the two Washington files from the dataset page into `data/` and unzip them:
   ```
   mkdir -p data
   curl -L -o data/meta-Washington.json.gz https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/meta-Washington.json.gz
   curl -L -o data/review-Washington.json.gz https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/review-Washington.json.gz
   gunzip data/*.gz
   ```
   The review file is ~1.3 GB compressed (~5 GB unzipped). `data/` is gitignored — never commit data files (GitHub rejects files over 100 MB).

## Run order

Run the notebooks top to bottom, in this order. Each one reads the previous one's output from `data/`.

| # | Notebook | Reads | Writes |
|---|----------|-------|--------|
| 1 | `filter_seattle.ipynb` | `meta-Washington.json`, `review-Washington.json` | `meta-SeattleArea.json`, `review-SeattleArea.json` |
| 2 | `clean_data.ipynb` | `meta-SeattleArea.json`, `review-SeattleArea.json` | `restaurants.csv`, `reviews.parquet` |
| 3 | `ambience.ipynb` | — | `ambience.json` |
| 4 | `inverted_index_bm25.ipynb` | `restaurants.csv`, `reviews.parquet`, `ambience.json` | — |

Steps 1 and 2 only need to be rerun if the raw data or the filtering/cleaning rules change. Step 1 takes several minutes because of the review file's size.

## Loading the clean data

Don't read `restaurants.csv` / `reviews.parquet` directly — use `load_data.py`, which restores the right types (IDs as text, `category` as a list, `misc` as a dict, `price` as 1–4 or `<NA>`):

```python
from load_data import load_restaurants, load_reviews

restaurants = load_restaurants()  # one row per restaurant
reviews = load_reviews()          # one row per review; join on gmap_id
```

**restaurants.csv:** `gmap_id, name, address, city, latitude, longitude, category, price, avg_rating, num_of_reviews, description, misc, temporarily_closed`

**reviews.parquet:** `gmap_id, user_id, time, rating, text`

See `clean_data.ipynb` for what was removed and why (permanently closed restaurants, reviews without text, duplicates).

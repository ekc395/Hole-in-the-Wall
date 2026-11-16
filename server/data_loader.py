"""Read notebook outputs, falling back to the filtered business metadata."""
import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
SAMPLE_SIZE = 10_000  # Same review sample as inverted_index_bm25.ipynb.


def json_lines(path):
    with path.open(encoding='utf-8') as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def load_data(data_dir=DATA_DIR):
    csv_path = data_dir / 'restaurants.csv'
    if csv_path.exists():
        with csv_path.open(encoding='utf-8', newline='') as source:
            businesses = list(csv.DictReader(source))
        metadata_source = csv_path.name
    else:
        path = data_dir / 'meta-SeattleArea.json'
        businesses = list(json_lines(path))
        metadata_source = path.name

    records = {}
    for business in businesses:
        if business.get('state') == 'Permanently closed':
            continue
        gid = business.get('gmap_id')
        if not gid or gid in records:
            continue
        categories = business.get('category') or []
        if isinstance(categories, str):
            categories = categories.split('|')
        records[gid] = {
            'id': gid, 'name': business.get('name') or 'Unnamed restaurant',
            'city': business.get('city') or None, 'address': business.get('address') or None,
            'category_primary': next(iter(categories), 'Restaurant'), 'categories': categories,
            'rating': float(business.get('avg_rating') or 0),
            'review_count': int(business.get('num_of_reviews') or 0),
            'summary_text': '', 'matched_terms': [],
        }

    review_path = data_dir / 'reviews.parquet'
    json_path = data_dir / 'review-SeattleArea.json'
    reviews, review_source = [], None
    if review_path.exists():
        import pyarrow.parquet as pq
        # Stream batches rather than loading the full reviews table into memory.
        for batch in pq.ParquetFile(review_path).iter_batches(
            batch_size=SAMPLE_SIZE, columns=['gmap_id', 'text']
        ):
            reviews = batch.to_pylist()
            break
        review_source = review_path.name
    elif json_path.exists():
        seen = set()
        for review in json_lines(json_path):
            text = review.get('text')
            key = (review.get('user_id'), review.get('gmap_id'), review.get('time'))
            if review.get('gmap_id') not in records or not isinstance(text, str) or not text.strip():
                continue
            if key in seen:
                continue
            seen.add(key)
            reviews.append(review)
            if len(reviews) >= SAMPLE_SIZE:
                break
        review_source = json_path.name
    reviews = [r for r in reviews if r.get('gmap_id') in records and isinstance(r.get('text'), str) and r['text'].strip()]
    return records, reviews, {'metadata_source': metadata_source, 'review_source': review_source,
        'indexed_reviews': len(reviews), 'mode': 'reviews' if reviews else 'metadata'}

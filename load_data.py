import json
import pandas as pd

def load_restaurants(path="data/restaurants.csv"):
    df = pd.read_csv(path, dtype={"gmap_id": str, "price": "Int64"})
    df["category"] = df["category"].str.split("|")
    df["misc"] = df["misc"].apply(lambda s: json.loads(s) if isinstance(s, str) else None)
    return df

def load_reviews(path="data/reviews.parquet"):
    return pd.read_parquet(path)

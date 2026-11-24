# Python document for BM25 tokenization/scoring, summed by restaurant, metadata search, and WordNet query expansion

import math
import re
from collections import Counter, defaultdict
from .data_loader import load_data

EXPANSION_WEIGHT = 0.5  
MAX_SYNSETS = 2         
MAX_SYNONYMS = 5
# Hybrid ranker: weighted sum of keyword (BM25 / best BM25), rating (/ 5), and distance (1 / (1 + miles / scale)).
RANKER_WEIGHTS = {'keyword': 0.6, 'rating': 0.25, 'distance': 0.15}
DISTANCE_SCALE_MILES = 1.0

STOPWORDS = set('''a an and are as at be been but by for from had has have he her his i if in into is it its
me my of on or our she so than that the their them they this to was we were what when which
who will with you your just also very really there here us did do does'''.split())


def english_text(text):
    if text.startswith('(Translated by Google)'):
        text = text.removeprefix('(Translated by Google)').split('(Original)')[0]
    return text


def tokenize(text):
    return [word for word in re.findall(r'[a-z0-9]+', english_text(text).lower().replace("'", '')) if word not in STOPWORDS]


def load_wordnet():
    """Return NLTK's WordNet reader, downloading the data on first use; None if unavailable."""
    try:
        import nltk
        from nltk.corpus import wordnet as wn
    except ImportError:
        return None
    try:
        wn.ensure_loaded()
    except LookupError:
        try:
            if not nltk.download('wordnet', quiet=True):
                return None
            wn.ensure_loaded()
        except Exception:  # No network, or the download failed: search without synonyms.
            return None
    return wn


class WordNetExpander:
    def __init__(self, wordnet=None):
        self.wn = wordnet if wordnet is not None else load_wordnet()

    @property
    def available(self):
        return self.wn is not None

    def __call__(self, term):
        """The word's base form (noodles -> noodle) if different, then single-word synonyms, most frequent first."""
        if self.wn is None:
            return []
        base = self.wn.morphy(term) or term
        counts = {}
        for synset in self.wn.synsets(term)[:MAX_SYNSETS]:
            for lemma in synset.lemmas():
                word = lemma.name().lower()
                if '_' in word or '-' in word or word in (term, base):
                    continue
                counts[word] = max(counts.get(word, 0), lemma.count())
        synonyms = sorted(counts, key=lambda w: (-counts[w], w))[:MAX_SYNONYMS]
        return ([base] if base != term else []) + synonyms


def haversine_miles(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(a))


class SearchService:
    def __init__(self, data_dir=None, expander=None):
        self.records, reviews, self.status = load_data() if data_dir is None else load_data(data_dir)
        self.expander = expander if expander is not None else WordNetExpander()
        self.status['query_expansion'] = 'wordnet' if getattr(self.expander, 'available', True) else 'off'
        self.documents = [(gid, ' '.join([r['name'], *r['categories']]), False) for gid, r in self.records.items()]
        self.documents += [(r['gmap_id'], english_text(r['text']), True) for r in reviews]
        self.index = defaultdict(dict)
        self.lengths = []
        for doc_id, (_, text, _) in enumerate(self.documents):
            words = tokenize(text)
            self.lengths.append(len(words))
            for term, tf in Counter(words).items():
                self.index[term][doc_id] = tf
        self.avgdl = sum(self.lengths) / max(len(self.lengths), 1) or 1

    def expand_query(self, terms):
        #Map each query term to its synonyms that occur in the index and aren't already query terms
        expansions = {}
        for term in dict.fromkeys(terms):
            synonyms = [s for s in self.expander(term) if s in self.index and s not in terms and s not in STOPWORDS]
            if synonyms:
                expansions[term] = synonyms
        return expansions

    def search(self, query, city=None, limit=20, expand=True, lat=None, lon=None, radius=None,
               ranker_weights=None):
        terms = tokenize(query)
        weights = Counter(terms)  
        if expand:
            for synonyms in self.expand_query(terms).values():
                for synonym in synonyms:
                    weights[synonym] = max(weights[synonym], EXPANSION_WEIGHT)
        distances = {}
        if lat is not None and lon is not None:
            distances = {gid: haversine_miles(lat, lon, r['latitude'], r['longitude'])
                         for gid, r in self.records.items() if r['latitude'] is not None and r['longitude'] is not None}
        in_radius = lambda gid: radius is None or distances.get(gid, math.inf) <= radius
        scores = defaultdict(float)
        matches = defaultdict(set)
        excerpts = {}
        best_review = defaultdict(float)
        for term, weight in weights.items():
            postings = self.index.get(term, {})
            idf = math.log(1 + (len(self.documents) - len(postings) + .5) / (len(postings) + .5))
            for doc_id, tf in postings.items():
                gid, text, is_review = self.documents[doc_id]
                if city and city.casefold() != 'anywhere' and (self.records[gid]['city'] or '').casefold() != city.casefold():
                    continue
                if not in_radius(gid):
                    continue
                norm = 1 - .75 + .75 * self.lengths[doc_id] / self.avgdl
                score = weight * idf * tf * 2.5 / (tf + 1.5 * norm)
                scores[gid] += score
                matches[gid].add(term)
                if is_review and score > best_review[gid]:
                    best_review[gid] = score
                    excerpts[gid] = text[:600] + ('…' if len(text) > 600 else '')
        candidates = scores if terms else self.records
        ids = [gid for gid in candidates if not city or city.casefold() == 'anywhere' or (self.records[gid]['city'] or '').casefold() == city.casefold()]
        ids = [gid for gid in ids if in_radius(gid)]
        # Without a location, drop the distance term and renormalize the remaining weights.
        w = {**RANKER_WEIGHTS, **(ranker_weights or {})}
        if lat is None or lon is None:
            w['distance'] = 0
        total = sum(w.values()) or 1
        best = max((scores.get(gid, 0) for gid in ids), default=0) or 1
        rank_scores = {gid: (w['keyword'] * scores.get(gid, 0) / best
                             + w['rating'] * self.records[gid]['rating'] / 5
                             + w['distance'] * (1 / (1 + distances[gid] / DISTANCE_SCALE_MILES) if gid in distances else 0)) / total
                       for gid in ids}
        ids.sort(key=lambda gid: (-rank_scores[gid], -scores.get(gid, 0), -self.records[gid]['rating'], -self.records[gid]['review_count'], gid))
        return [{**self.records[gid], 'score': round(scores.get(gid, 0), 4), 'rank_score': round(rank_scores[gid], 4),
                 'matched_terms': sorted(matches[gid]), 'summary_text': excerpts.get(gid, ''),
                 'distance_miles': round(distances[gid], 2) if gid in distances else None} for gid in ids[:limit]]

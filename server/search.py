"""Notebook BM25 tokenization/scoring, summed by restaurant, plus metadata search."""
import math
import re
from collections import Counter, defaultdict
from .data_loader import load_data

STOPWORDS = set('''a an and are as at be been but by for from had has have he her his i if in into is it its
me my of on or our she so than that the their them they this to was we were what when which
who will with you your just also very really there here us did do does'''.split())


def english_text(text):
    if text.startswith('(Translated by Google)'):
        text = text.removeprefix('(Translated by Google)').split('(Original)')[0]
    return text


def tokenize(text):
    return [word for word in re.findall(r'[a-z0-9]+', english_text(text).lower().replace("'", '')) if word not in STOPWORDS]


class SearchService:
    def __init__(self, data_dir=None):
        self.records, reviews, self.status = load_data() if data_dir is None else load_data(data_dir)
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

    def search(self, query, city=None, limit=20):
        terms = tokenize(query)
        scores = defaultdict(float)
        matches = defaultdict(set)
        excerpts = {}
        best_review = defaultdict(float)
        for term in terms:
            postings = self.index.get(term, {})
            idf = math.log(1 + (len(self.documents) - len(postings) + .5) / (len(postings) + .5))
            for doc_id, tf in postings.items():
                gid, text, is_review = self.documents[doc_id]
                if city and city.casefold() != 'anywhere' and (self.records[gid]['city'] or '').casefold() != city.casefold():
                    continue
                norm = 1 - .75 + .75 * self.lengths[doc_id] / self.avgdl
                score = idf * tf * 2.5 / (tf + 1.5 * norm)
                scores[gid] += score
                matches[gid].add(term)
                if is_review and score > best_review[gid]:
                    best_review[gid] = score
                    excerpts[gid] = text[:600] + ('…' if len(text) > 600 else '')
        candidates = scores if terms else self.records
        ids = [gid for gid in candidates if not city or city.casefold() == 'anywhere' or (self.records[gid]['city'] or '').casefold() == city.casefold()]
        ids.sort(key=lambda gid: (-scores.get(gid, 0), -self.records[gid]['rating'], -self.records[gid]['review_count'], gid))
        return [{**self.records[gid], 'score': round(scores.get(gid, 0), 4),
                 'matched_terms': sorted(matches[gid]), 'summary_text': excerpts.get(gid, '')} for gid in ids[:limit]]

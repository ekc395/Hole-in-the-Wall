import json
import tempfile
import unittest
from pathlib import Path
from server.search import SearchService, tokenize


class SearchTests(unittest.TestCase):
    def test_notebook_tokenizer(self):
        self.assertEqual(tokenize("(Translated by Google) Cozy food's great! (Original) comida"), ['cozy', 'foods', 'great'])

    def test_metadata_fallback_and_review_aggregation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            businesses = [dict(gmap_id=str(i), name=name, city=city, category=['Restaurant'], avg_rating=4.5, num_of_reviews=50)
                          for i, name, city in [(1, 'Ramen House', 'Seattle'), (2, 'Cafe', 'Bellevue')]]
            businesses.append(dict(gmap_id='3', name='Closed', state='Permanently closed'))
            (root / 'meta-SeattleArea.json').write_text(''.join(json.dumps(x)+'\n' for x in businesses))
            service = SearchService(root)
            self.assertEqual(service.status['mode'], 'metadata')
            self.assertEqual([r['id'] for r in service.search('ramen')], ['1'])
            self.assertEqual(service.search('ramen', 'Bellevue'), [])
            self.assertEqual(service.search('nonexistent'), [])
            self.assertEqual(len(service.search('', limit=1)), 1)
            reviews = [dict(gmap_id='1', user_id=str(i), time=i, text='Cozy intimate restaurant') for i in range(2)]
            (root / 'review-SeattleArea.json').write_text(''.join(json.dumps(x)+'\n' for x in reviews))
            service = SearchService(root)
            results = service.search('cozy intimate', 'seattle')
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['matched_terms'], ['cozy', 'intimate'])
            self.assertEqual(results[0]['review_count'], 50)
            self.assertIn('Cozy', results[0]['summary_text'])
            self.assertEqual(service.status['indexed_reviews'], 2)


if __name__ == '__main__':
    unittest.main()

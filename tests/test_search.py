import json
import tempfile
import unittest
from pathlib import Path
from server.search import SearchService, haversine_miles, tokenize


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

    def test_location_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Pike Place (~0 mi), Bellevue (~6.5 mi), and one without coordinates.
            businesses = [dict(gmap_id='1', name='Pike Ramen', city='Seattle', latitude=47.6097, longitude=-122.3422, category=['Restaurant']),
                          dict(gmap_id='2', name='Bellevue Ramen', city='Bellevue', latitude=47.6101, longitude=-122.2015, category=['Restaurant']),
                          dict(gmap_id='3', name='Nowhere Ramen', city='Seattle', category=['Restaurant'])]
            (root / 'meta-SeattleArea.json').write_text(''.join(json.dumps(x)+'\n' for x in businesses))
            service = SearchService(root)
            self.assertAlmostEqual(haversine_miles(47.6097, -122.3422, 47.6101, -122.2015), 6.53, places=1)
            near = service.search('ramen', lat=47.6097, lon=-122.3422, radius=2)
            self.assertEqual([r['id'] for r in near], ['1'])
            self.assertEqual(near[0]['distance_miles'], 0.0)
            self.assertEqual({r['id'] for r in service.search('', lat=47.6097, lon=-122.3422, radius=10)}, {'1', '2'})
            unfiltered = {r['id']: r['distance_miles'] for r in service.search('ramen', lat=47.6097, lon=-122.3422)}
            self.assertEqual(len(unfiltered), 3)
            self.assertIsNone(unfiltered['3'])
            self.assertTrue(all(r['distance_miles'] is None for r in service.search('ramen')))

    def test_hybrid_ranker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Same keyword match; the near one is rated lower than the far one.
            businesses = [dict(gmap_id='near', name='Ramen Near', latitude=47.6097, longitude=-122.3422, avg_rating=3.0, category=['Restaurant']),
                          dict(gmap_id='far', name='Ramen Far', latitude=47.6101, longitude=-122.2015, avg_rating=5.0, category=['Restaurant'])]
            (root / 'meta-SeattleArea.json').write_text(''.join(json.dumps(x)+'\n' for x in businesses))
            service = SearchService(root)
            ids = lambda **kw: [r['id'] for r in service.search('ramen', **kw)]
            here = dict(lat=47.6097, lon=-122.3422)
            self.assertEqual(ids(), ['far', 'near'])  # no location: rating decides
            self.assertEqual(ids(**here), ['near', 'far'])  # distance outweighs the rating gap
            self.assertEqual(ids(**here, ranker_weights={'distance': 0}), ['far', 'near'])
            top = service.search('ramen', **here)[0]
            self.assertAlmostEqual(top['rank_score'], 0.6 + 0.25 * 3 / 5 + 0.15, places=4)


if __name__ == '__main__':
    unittest.main()

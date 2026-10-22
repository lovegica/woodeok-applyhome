import os
import unittest
from unittest.mock import patch, MagicMock
from scripts.enrich import enrich

class GeocodeTests(unittest.TestCase):
    @patch.dict(os.environ, {'KAKAO_REST_API_KEY': 'test-only'})
    @patch('scripts.enrich.urllib.request.urlopen')
    def test_ambiguous_or_other_province_not_pinned(self, urlopen):
        for docs in [[], [{'address_type':'REGION','x':'127','y':'37'}], [{'address_type':'ROAD_ADDR','x':'129','y':'35','road_address':{'region_1depth_name':'부산'}}]]:
            with patch('scripts.enrich.json.load', return_value={'documents':docs}):
                urlopen.return_value.__enter__.return_value=MagicMock()
                items=[{'address':'서울특별시 예시로 1','region':'서울'}]
                enrich(items)
                self.assertIsNone(items[0]['location'])

    @patch.dict(os.environ, {'KAKAO_REST_API_KEY': 'test-only'})
    @patch('scripts.enrich.urllib.request.urlopen')
    def test_exact_coordinate_only(self, urlopen):
        doc={'address_type':'ROAD_ADDR','x':'127.1','y':'37.5','road_address':{'region_1depth_name':'서울','region_2depth_name':'강동구'}}
        with patch('scripts.enrich.json.load',return_value={'documents':[doc]}):
            items=[{'address':'서울특별시 예시로 1','region':'서울'}]
            enrich(items)
            self.assertEqual(items[0]['location']['lng'],127.1)
            self.assertEqual(items[0]['location']['district'],'강동구')

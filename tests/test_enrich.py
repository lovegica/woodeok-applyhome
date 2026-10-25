import os
import unittest
from unittest.mock import patch, MagicMock
from scripts.enrich import enrich, candidates, match_document

class GeocodeTests(unittest.TestCase):
    @patch.dict(os.environ, {'KAKAO_REST_API_KEY': 'test-only'})
    @patch('scripts.enrich.urllib.request.urlopen')
    def test_ambiguous_or_other_province_not_pinned(self, urlopen):
        for docs in [[], [{'address_type':'REGION','x':'127','y':'37'}], [{'address_type':'ROAD_ADDR','x':'129','y':'35','road_address':{'region_1depth_name':'부산'}}]]:
            with patch('scripts.enrich.json.load', return_value={'documents':docs}):
                urlopen.return_value.__enter__.return_value=MagicMock()
                items=[{'address':'서울특별시 예시로 1','region':'서울','id':'test'}]
                enrich(items)
                self.assertIsNone(items[0]['location'])

    @patch.dict(os.environ, {'KAKAO_REST_API_KEY': 'test-only'})
    @patch('scripts.enrich.urllib.request.urlopen')
    def test_exact_coordinate_only(self, urlopen):
        doc={'address_type':'ROAD_ADDR','x':'127.1','y':'37.5','road_address':{'region_1depth_name':'서울','region_2depth_name':'강동구','road_name':'예시로','main_building_no':'1','sub_building_no':''}}
        with patch('scripts.enrich.json.load',return_value={'documents':[doc]}):
            items=[{'address':'서울특별시 예시로 1','region':'서울','id':'test'}]
            enrich(items)
            self.assertEqual(items[0]['location']['lng'],127.1)
            self.assertEqual(items[0]['location']['district'],'강동구')

class AddressTests(unittest.TestCase):
    def test_new_district_and_block_text(self):
        values = candidates('경기도 화성특례시 동탄구 반송동 95번지[동탄(1) M1-1-2블록]')
        self.assertIn('경기도 화성시 반송동 95', values)

    def test_mountain_lot_is_preserved(self):
        values = candidates('경기도 화성시 만세구 향남읍 상신리 산 13-13 일원')
        self.assertIn('경기도 화성시 향남읍 상신리 산 13-13', values)

    def test_wrong_parcel_is_rejected(self):
        doc = {'address_type':'REGION_ADDR','x':'127.1','y':'37.2','address':{'region_1depth_name':'경기','region_3depth_name':'반송동','main_address_no':'99','sub_address_no':'','mountain_yn':'N'}}
        self.assertIsNone(match_document([doc], {'region':'경기'}, '경기도 화성시 반송동 95'))

    def test_embedded_parcel_preserved(self):
        self.assertIn('경기도 파주시 동패동 1673번지', candidates('경기도 파주시 파주운정3지구 3블록(경기도 파주시 동패동 1673번지 일원)'))

    def test_block_or_district_centroid_is_rejected(self):
        doc = {'address_type':'REGION_ADDR', 'x':'127', 'y':'37', 'address':{'region_1depth_name':'경기'}}
        self.assertIsNone(match_document([doc], {'region':'경기'}, '경기도 시흥시 거모동 일원 S-1블록'))

    def test_wrong_city_rejected(self):
        doc = {'address_type':'REGION_ADDR', 'x':'127', 'y':'37', 'address':{'region_1depth_name':'경기','region_2depth_name':'다른시','region_3depth_name':'동패동','main_address_no':'1673','sub_address_no':'','mountain_yn':'N'}}
        self.assertIsNone(match_document([doc], {'region':'경기'}, '경기도 파주시 동패동 1673'))

class OfficialLocationTests(unittest.TestCase):
    def test_lh_site_location_available_without_key(self):
        from scripts.enrich import verified_location
        item = {'id':'2026000531-2026000531', 'name':'시흥거모지구 S-1블록 공공분양(본청약)'}
        location = verified_location(item)
        self.assertEqual(location['accuracy'], 'official_site')
        self.assertIn('apply.lh.or.kr', location['sourceUrl'])
        item['name'] = '다른 단지'
        self.assertIsNone(verified_location(item))

import datetime as dt
import unittest
from unittest.mock import patch
from scripts.build import select, fetch, SOURCES

TODAY = dt.date(2026, 10, 25)
class SelectionTests(unittest.TestCase):
    def row(self, **kw):
        return dict(HOUSE_MANAGE_NO='123', PBLANC_NO='456', HOUSE_NM='테스트', SUBSCRPT_AREA_CODE_NM='서울', **kw)

    def test_active_and_safe_url(self):
        item = select([self.row(RCEPT_BGNDE='2026-10-25', RCEPT_ENDDE='2026-10-26', PBLANC_URL='javascript:alert(1)')], TODAY)[0]
        self.assertEqual(item['status'], '접수 중')
        self.assertEqual(item['url'], 'https://www.applyhome.co.kr/')

    def test_all_future_but_not_expired_or_unverified_dates(self):
        row = self.row(RCEPT_BGNDE='2026-11-02', RCEPT_ENDDE='2026-11-04')
        self.assertEqual(len(select([row, row], TODAY)), 1)
        row['SUBSCRPT_AREA_CODE_NM'] = '부산'
        self.assertEqual(select([row], TODAY), [])
        self.assertEqual(select([self.row(RCRIT_PBLANC_DE='2026-10-25')], TODAY), [])
        self.assertEqual(select([self.row(RCEPT_BGNDE='2026-10-20',RCEPT_ENDDE='2026-10-24')], TODAY), [])

    def test_gaps_and_special_priority_dates(self):
        row = self.row(SPSPLY_RCEPT_BGNDE='2026-10-23', SPSPLY_RCEPT_ENDDE='2026-10-23', GNRL_RNK1_CRSPAREA_RCPTDE='2026-10-26', GNRL_RNK1_CRSPAREA_ENDDE='2026-10-26')
        item = select([row], TODAY)[0]
        self.assertEqual(item['status'], '접수 예정')
        self.assertEqual([p['type'] for p in item['schedules']], ['특별공급', '1순위'])

    def test_resupply_and_optional_dates_without_region_field(self):
        row = self.row(SUBSCRPT_RCEPT_BGNDE='2026-10-25', SUBSCRPT_RCEPT_ENDDE='2026-10-26', HSSPLY_ADRES='경기도 파주시 동패동 1673')
        row.pop('SUBSCRPT_AREA_CODE_NM')
        self.assertEqual(select([row], TODAY)[0]['region'], '경기')

    @patch('scripts.build.fetch_source')
    def test_all_sources_required(self, source):
        source.return_value = []
        fetch('test-only')
        self.assertEqual([c.args[1] for c in source.call_args_list], list(SOURCES))
        source.side_effect = RuntimeError('unavailable')
        with self.assertRaises(RuntimeError):
            fetch('test-only')

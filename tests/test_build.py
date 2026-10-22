import datetime as dt
import unittest
from scripts.build import select

class SelectionTests(unittest.TestCase):
    def row(self, **kw):
        return dict(HOUSE_MANAGE_NO='123', PBLANC_NO='456', HOUSE_NM='테스트', SUBSCRPT_AREA_CODE_NM='서울', **kw)

    def test_active_and_safe_url(self):
        rows = select([self.row(RCEPT_BGNDE='2026-10-20', RCEPT_ENDDE='2026-10-22', PBLANC_URL='javascript:alert(1)')], dt.date(2026, 10, 22))
        self.assertEqual(rows[0]['status'], '접수 중')
        self.assertEqual(rows[0]['url'], 'https://www.applyhome.co.kr/')

    def test_horizon_and_region(self):
        today = dt.date(2026, 10, 22)
        self.assertEqual(len(select([self.row(RCEPT_BGNDE='2026-10-29')], today)), 1)
        self.assertEqual(select([self.row(RCEPT_BGNDE='2026-10-30')], today), [])
        row = self.row(RCEPT_BGNDE='2026-10-23'); row['SUBSCRPT_AREA_CODE_NM'] = '부산'
        self.assertEqual(select([row], today), [])

    def test_new_and_duplicates(self):
        row = self.row(RCRIT_PBLANC_DE='2026-10-16')
        self.assertEqual(len(select([row, row], dt.date(2026, 10, 22))), 1)
        self.assertEqual(select([row], dt.date(2026, 10, 23)), [])

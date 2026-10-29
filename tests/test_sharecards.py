import datetime as dt
import unittest
from scripts.sharecards import price84, qualifies, review_matches, load_reviews

class ShareCardTests(unittest.TestCase):
    def test_area_and_money_units(self):
        summary = price84([{'HOUSE_TY':'084.0000A','LTTOT_TOP_AMOUNT':'298,100'},
                           {'HOUSE_TY':'074.0000A','LTTOT_TOP_AMOUNT':'500000'},
                           {'HOUSE_TY':'085.0000A','LTTOT_TOP_AMOUNT':'600000'},
                           {'HOUSE_TY':'invalid','LTTOT_TOP_AMOUNT':'x'}])
        self.assertEqual(summary['maxTypeTopManwon'],298100)
        self.assertIsNone(price84([{'HOUSE_TY':'059.99','LTTOT_TOP_AMOUNT':'80000'}]))

    def test_complex_total_not_notice_count(self):
        item={'region':'경기','units':2,'price84':{'maxTypeTopManwon':100001}}
        self.assertTrue(qualifies(item, 740))
        self.assertFalse(qualifies(item, 499))
        self.assertFalse(qualifies(item))
        item['price84']['maxTypeTopManwon']=100000
        self.assertFalse(qualifies(item, 740))
        item['region']='부산'
        self.assertFalse(qualifies(item, 740))

    def test_source_changes_and_expiration_need_review(self):
        review=load_reviews()['2026910275-2026910275']
        item={'name':review['name'],'units':58,'start':'2026-11-02','end':'2026-11-02'}
        self.assertTrue(review_matches(item, review, dt.date(2026,10,29)))
        item['units']=57
        self.assertFalse(review_matches(item, review, dt.date(2026,10,29)))
        item['units']=58
        self.assertFalse(review_matches(item, review, dt.date(2026,11,3)))

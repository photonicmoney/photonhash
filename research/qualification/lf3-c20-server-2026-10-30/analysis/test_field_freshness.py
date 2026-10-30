import unittest
from field_freshness import check
def sample(age):return dict(unix_ns=1_000_000_000_000,field_instant_timestamp_us=1_000_000_000-age*1e6)
class FieldFreshnessTests(unittest.TestCase):
    def test_current_and_exact_bound(self):
        self.assertTrue(check([sample(0),sample(.0000305),sample(2)])['passed_metadata_bound'])
    def test_stale_is_rejected(self):
        result=check([sample(0),sample(2.000001)])
        self.assertFalse(result['passed_metadata_bound']);self.assertEqual(result['older_than_2s_count_measured'],1)
    def test_future_or_nonfinite_rejected(self):
        for age in [-.002,float('nan'),float('inf')]:
            with self.subTest(age=age):self.assertFalse(check([sample(age)])['passed_metadata_bound'])
    def test_missing_metadata_fails_closed(self):
        with self.assertRaises(KeyError):check([dict(unix_ns=1_000_000_000_000)])
if __name__=='__main__':unittest.main()

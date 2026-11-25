"""No-network tests for deterministic and capped Nasdaq gap sampling."""
import unittest
from nasdaq_price_gap_probe import representative_gap_sample, SAMPLE_SIZE

class GapProbeTests(unittest.TestCase):
    def test_sample_size(self):
        values={f"ABC{i:04}" for i in range(209)}
        a=representative_gap_sample(values)
        self.assertEqual(len(a),SAMPLE_SIZE)
        self.assertEqual(len(set(a)),SAMPLE_SIZE)
        self.assertTrue(set(a).issubset(values))

    def test_deterministic_order(self):
        x=representative_gap_sample({"ABC","DEF","GHI","MNO"},3)
        y=representative_gap_sample({"GHI","ABC","MNO","DEF"},3)
        self.assertEqual(x,y)

    def test_cap_and_empty(self):
        self.assertEqual(representative_gap_sample(set()),[])
        self.assertEqual(len(representative_gap_sample({"X"},25)),1)
        self.assertEqual(representative_gap_sample({"X"},0),[])

if __name__=="__main__":
    unittest.main()

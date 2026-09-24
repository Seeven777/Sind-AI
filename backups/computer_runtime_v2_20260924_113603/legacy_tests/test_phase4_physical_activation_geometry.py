import unittest
from runtime.phase4.whatsapp_uia import WhatsAppUIA


class GeometryTests(unittest.TestCase):
    def test_safe_point_is_inside_live_rect(self):
        p = WhatsAppUIA._safe_row_point((1215,337,1479,410), 0)
        self.assertGreater(p[0], 1215)
        self.assertLess(p[0], 1479)
        self.assertGreater(p[1], 337)
        self.assertLess(p[1], 410)

    def test_second_point_differs_but_stays_inside(self):
        a = WhatsAppUIA._safe_row_point((1215,337,1479,410), 0)
        b = WhatsAppUIA._safe_row_point((1215,337,1479,410), 1)
        self.assertNotEqual(a, b)
        for x,y in (a,b):
            self.assertTrue(1215 < x < 1479)
            self.assertTrue(337 < y < 410)


if __name__ == "__main__":
    unittest.main()

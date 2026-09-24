import unittest
from runtime.phase4.whatsapp_uia import contact_accessible_name_matches, contact_row_matches

class SearchResultIdentityTests(unittest.TestCase):
    def test_exact(self): self.assertTrue(contact_accessible_name_matches("Me (você)","Me (você)"))
    def test_time_suffix(self): self.assertTrue(contact_accessible_name_matches("Me (você) 07:11 preview","Me (você)"))
    def test_date_suffix(self): self.assertTrue(contact_accessible_name_matches("Grupo Exemplo 03/09/2026 preview","Grupo Exemplo"))
    def test_day_suffix(self): self.assertTrue(contact_accessible_name_matches("Maria Silva Ontem Oi","Maria Silva"))
    def test_longer_contact_rejected(self): self.assertFalse(contact_accessible_name_matches("Maria Silva 07:11 Oi","Maria"))
    def test_substring_rejected(self): self.assertFalse(contact_accessible_name_matches("Equipe Me (você) 07:11","Me (você)"))
    def test_geometry(self):
        row={"name":"Me (você) 07:11 preview","visible":True,"enabled":True,"bounds":[1215,337,1479,414]}
        self.assertTrue(contact_row_matches(row,"Me (você)",[1283,208,1407,229]))

if __name__=='__main__': unittest.main()

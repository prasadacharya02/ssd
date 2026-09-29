import unittest
from pathlib import Path

from catalog import family_from_filename, list_families
from attacker_server import ransomware_engines as engines


class CatalogTests(unittest.TestCase):
    def test_attacker_catalog_matches_shared_ids(self):
        ids = {item["id"] for item in list_families()}
        self.assertEqual(ids, set(engines.FAMILIES))
        self.assertEqual(family_from_filename("photo.jpg.WNCRY"), "WannaCry")
        self.assertEqual(family_from_filename("@Please_Read_Me@.txt"), "WannaCry")


class ContractAccessTests(unittest.TestCase):
    def test_log_threat_is_owner_restricted(self):
        source = Path("blockchain/contracts/ThreatLogger.sol").read_text(encoding="utf-8")
        self.assertIn("modifier onlyOwner", source)
        self.assertIn("public onlyOwner returns", source)
        self.assertIn("function transferOwnership", source)


if __name__ == "__main__":
    unittest.main()

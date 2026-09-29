import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryAssetTests(unittest.TestCase):
    def test_checked_in_json_assets_are_valid(self):
        json_files = sorted(
            path for path in ROOT.rglob("*.json")
            if ".git" not in path.parts
            and "user_files" not in path.parts
            # Front-end dependency trees legitimately ship JSON5-ish
            # tsconfig files that json.load rejects. They are not repo assets.
            and "node_modules" not in path.parts
        )
        self.assertTrue(json_files)
        for path in json_files:
            with self.subTest(path=path.relative_to(ROOT)):
                with path.open(encoding="utf-8") as handle:
                    json.load(handle)

    def test_contract_abi_contains_required_functions(self):
        abi_path = ROOT / "blockchain" / "contract_abi.json"
        abi = json.loads(abi_path.read_text(encoding="utf-8"))
        functions = {
            entry.get("name")
            for entry in abi
            if entry.get("type") == "function"
        }
        self.assertTrue({"logThreat", "getEvent", "getEventCount"} <= functions)

    def test_example_environment_file_is_present(self):
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("ENTROPY_WATCH_FOLDERS", example)
        self.assertIn("ENTROPY_BLOCKCHAIN_FALLBACK", example)
        self.assertNotIn("0x16782FEEA599fcA6536Ae03D9FA88019bc3e4Bc2", example)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest


class AcceptanceScriptTests(unittest.TestCase):
    def test_ripgrep_secret_scan_does_not_use_encoding_flag_for_regex(self):
        text = Path('cloud-reference/tests/acceptance.sh').read_text()
        self.assertNotIn('rg -I -n -E ', text)
        self.assertIn('rg -I -n ', text)


if __name__ == '__main__':
    unittest.main()

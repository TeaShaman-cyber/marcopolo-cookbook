import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, 'cloud-reference/lib')
from sources import executable_sources, load_reviewed_sources


class SourcesTests(unittest.TestCase):
    def test_only_reviewed_sources_are_executable(self):
        sources = [
            {'name':'a','state':'DISCOVERED'},
            {'name':'b','state':'REVIEWED_REFERENCE_SOURCE'},
        ]
        self.assertEqual([s['name'] for s in executable_sources(sources)], ['b'])

    def test_loader_rejects_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'sources.json'
            p.write_text('{"sources":[{"name":"x"}]}')
            with self.assertRaises(ValueError):
                load_reviewed_sources(p)


if __name__ == '__main__':
    unittest.main()

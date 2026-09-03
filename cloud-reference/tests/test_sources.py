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


class SourceStateTests(unittest.TestCase):
    def test_nonexecutable_negative_states_are_valid_but_not_routable(self):
        from sources import validate_source_state
        for state in ['EXECUTION_AUTH_REQUIRED', 'CONTROL_PLANE_BLOCKED']:
            self.assertTrue(validate_source_state(state))
        sources=[{'name':'auth','state':'EXECUTION_AUTH_REQUIRED'},{'name':'blocked','state':'CONTROL_PLANE_BLOCKED'},{'name':'reviewed','state':'REVIEWED_REFERENCE_SOURCE'}]
        self.assertEqual([s['name'] for s in executable_sources(sources)], ['reviewed'])

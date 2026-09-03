import sys
import unittest

sys.path.insert(0, 'cloud-reference/lib')
from mcp import build_reference_query, choose_route


class MCPTests(unittest.TestCase):
    def test_waf_reference_rejects_bypass_intent(self):
        with self.assertRaises(ValueError):
            build_reference_query('cloudflare', 'how to bypass waf filtering', mode='waf')

    def test_waf_reference_accepts_false_positive_diagnostics(self):
        query=build_reference_query('cloudflare', 'documented causes of false-positive 403 filtering', mode='waf')
        self.assertIn('false-positive', query)
        self.assertIn('defensive', query.lower())

    def test_provider_routes_are_explicit(self):
        self.assertEqual(choose_route('cloudflare')[0], 'cloudflare-docs')
        self.assertEqual(choose_route('aws')[0], 'aws-knowledge')
        self.assertEqual(choose_route('microsoft')[0], 'microsoft-learn')
        with self.assertRaises(ValueError):
            choose_route('unknown-cloud')


if __name__ == '__main__':
    unittest.main()

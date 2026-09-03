import sys
import unittest

sys.path.insert(0, 'cloud-reference/lib')
from hosting import detect_provider_candidate, validate_hostname


class HostingTests(unittest.TestCase):
    def test_rejects_url_and_shell_text(self):
        for value in ['https://mcp.marcopolo.dev', 'mcp.marcopolo.dev;id', 'mcp.marcopolo.dev/path', 'mcp marcopolo.dev']:
            with self.assertRaises(ValueError, msg=value):
                validate_hostname(value)

    def test_accepts_public_hostname_shape(self):
        self.assertEqual(validate_hostname('mcp.marcopolo.dev'), 'mcp.marcopolo.dev')

    def test_provider_candidates_are_conservative(self):
        self.assertEqual(detect_provider_candidate('cname', 'something.vercel-dns.com'), 'vercel')
        self.assertEqual(detect_provider_candidate('header', 'cf-ray'), 'cloudflare')
        self.assertIsNone(detect_provider_candidate('header', 'server'))


if __name__ == '__main__':
    unittest.main()

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

class ProviderEvidenceTests(unittest.TestCase):
    def test_aws_range_matching_is_network_authority_only(self):
        from hosting import match_aws_ranges
        ranges={'prefixes':[{'ip_prefix':'44.224.0.0/11','region':'us-west-2','service':'EC2','network_border_group':'us-west-2'}]}
        matches=match_aws_ranges(['44.226.16.168'], ranges)
        self.assertEqual(matches[0]['provider_candidate'], 'aws')
        self.assertEqual(matches[0]['region'], 'us-west-2')
        self.assertEqual(matches[0]['service'], 'EC2')


    def test_bounded_json_rejects_oversized_payload(self):
        from hosting import parse_bounded_json
        with self.assertRaises(ValueError):
            parse_bounded_json(b'{"x":1}', max_bytes=3)

    def test_bounded_json_accepts_complete_payload(self):
        from hosting import parse_bounded_json
        self.assertEqual(parse_bounded_json(b'{"x":1}', max_bytes=32), {"x":1})

    def test_amazon_tls_issuer_is_independent_provider_marker(self):
        from hosting import tls_provider_candidate
        tls={'issuer': [[['countryName','US']], [['organizationName','Amazon']], [['commonName','Amazon RSA 2048 M04']]]}
        self.assertEqual(tls_provider_candidate(tls), 'aws')


class LayeredReceiptTests(unittest.TestCase):
    def test_build_receipt_emits_serving_and_application_layers(self):
        from unittest.mock import patch
        from hosting import build_hosting_receipt
        dns=[{'type':'address','value':'44.226.16.168'}]
        ranges={'createDate':'2026-09-03','prefixes':[{'ip_prefix':'44.224.0.0/11','region':'us-west-2','service':'EC2','network_border_group':'us-west-2'}]}
        tls={'issuer': [[['organizationName','Amazon']]], 'subject': [], 'subjectAltName': []}
        http={'status':401,'final_url':'https://mcp.marcopolo.dev/','headers':{'server':'uvicorn'},'body_sha256':'sha256:'+'0'*64,'body_excerpt':''}
        with patch('hosting.collect_dns', return_value=dns), patch('hosting.fetch_aws_ranges', return_value=(ranges, 'sha256:'+'1'*64)), patch('hosting.collect_tls', return_value=tls), patch('hosting.collect_http', return_value=http):
            receipt=build_hosting_receipt('mcp.marcopolo.dev', observation_time='2026-09-03T00:00:00Z')
        self.assertEqual(receipt['layers']['serving']['provider'], 'aws')
        self.assertEqual(receipt['layers']['serving']['classification'], 'VERIFIED_PROVIDER')
        self.assertEqual(receipt['layers']['application']['provider'], 'uvicorn')

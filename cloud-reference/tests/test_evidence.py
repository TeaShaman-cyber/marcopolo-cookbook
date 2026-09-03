import sys
import unittest

sys.path.insert(0, 'cloud-reference/lib')
from evidence import add_observation, bounded_sha256, classify_provider, new_receipt


class EvidenceTests(unittest.TestCase):
    def test_single_signal_cannot_be_likely(self):
        receipt = new_receipt('mcp.marcopolo.dev', 'hosting-identify', '2026-09-03T00:00:00Z')
        add_observation(receipt, 'http_header', 'target', {'provider_candidate': 'vercel'})
        classification, confidence = classify_provider(receipt)
        self.assertEqual(classification, 'INSUFFICIENT_EVIDENCE')
        self.assertLess(confidence, 0.5)

    def test_two_independent_matching_signals_can_be_likely(self):
        receipt = new_receipt('mcp.marcopolo.dev', 'hosting-identify', '2026-09-03T00:00:00Z')
        add_observation(receipt, 'dns', 'target', {'provider_candidate': 'vercel'})
        add_observation(receipt, 'http_header', 'target', {'provider_candidate': 'vercel'})
        classification, confidence = classify_provider(receipt)
        self.assertEqual(classification, 'LIKELY_PROVIDER')
        self.assertGreaterEqual(confidence, 0.5)

    def test_authoritative_signal_plus_two_classes_can_verify(self):
        receipt = new_receipt('mcp.marcopolo.dev', 'hosting-identify', '2026-09-03T00:00:00Z')
        add_observation(receipt, 'dns', 'target', {'provider_candidate': 'vercel'})
        add_observation(receipt, 'provider_header', 'target', {'provider_candidate': 'vercel'}, authority='provider_owned')
        classification, confidence = classify_provider(receipt)
        self.assertEqual(classification, 'VERIFIED_PROVIDER')
        self.assertGreaterEqual(confidence, 0.8)

    def test_bounded_hash_format(self):
        self.assertRegex(bounded_sha256(b'abc'), r'^sha256:[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()


class LayeredAttributionTests(unittest.TestCase):
    def test_layered_attribution_keeps_serving_and_dns_providers_separate(self):
        from evidence import add_layer_evidence, classify_layers
        receipt = new_receipt('mcp.marcopolo.dev', 'hosting-identify', '2026-09-03T00:00:00Z')
        add_layer_evidence(receipt, 'serving', 'network_provider_range', 'aws-ip-ranges', 'aws', authority='provider_owned')
        add_layer_evidence(receipt, 'serving', 'tls_provider_marker', 'target', 'aws')
        add_layer_evidence(receipt, 'dns', 'rdap_nameserver', 'wwhois', 'cloudflare', authority='registry_owned')
        layers = classify_layers(receipt)
        self.assertEqual(layers['serving']['provider'], 'aws')
        self.assertEqual(layers['serving']['classification'], 'VERIFIED_PROVIDER')
        self.assertEqual(layers['dns']['provider'], 'cloudflare')
        self.assertEqual(receipt['classification'], 'MULTI_PROVIDER_OR_PROXY')

    def test_application_layer_does_not_claim_hosting_provider(self):
        from evidence import add_layer_evidence, classify_layers
        receipt = new_receipt('mcp.marcopolo.dev', 'hosting-identify', '2026-09-03T00:00:00Z')
        add_layer_evidence(receipt, 'application', 'http_server', 'target', 'uvicorn')
        layers = classify_layers(receipt)
        self.assertEqual(layers['application']['classification'], 'OBSERVED_COMPONENT')
        self.assertEqual(receipt['classification'], 'INSUFFICIENT_EVIDENCE')

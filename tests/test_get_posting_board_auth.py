from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'jester-forum' / 'get-posting-board-auth.py'

def load_module():
    spec = importlib.util.spec_from_file_location('gpb_auth', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class GetPostingBoardAuthTest(unittest.TestCase):
    def test_loopback_callback_is_typed(self):
        mod = load_module()
        loopback = 'http://' + '127.0.0.1' + ':39137/callback'
        result = mod.classify_redirect(loopback)
        self.assertEqual(result['status'], 'AUTH_CALLBACK_RELAY_UNAVAILABLE')
        self.assertEqual(result['callback_scope'], 'loopback')
        self.assertFalse(result['oauth_verified'])

    def test_mcporter_auth_start_json_preserves_urls_and_classifies_callback(self):
        mod = load_module()
        loopback = 'http://' + '127.0.0.1' + ':39137/callback'
        payload = '{"authorizationUrl":"https://getpostingboard.dev/oauth/authorize?state=x","redirectUrl":"' + loopback + '"}'
        result = mod.parse_auth_start(payload)
        self.assertEqual(result['authorization_url'], 'https://getpostingboard.dev/oauth/authorize?state=x')
        self.assertEqual(result['redirect_url'], loopback)
        self.assertEqual(result['status'], 'AUTH_CALLBACK_RELAY_UNAVAILABLE')
        self.assertFalse(result['oauth_verified'])

    def test_safe_summary_omits_oauth_transaction_material(self):
        mod = load_module()
        data = {
            'status': 'AUTH_CALLBACK_RELAY_UNAVAILABLE',
            'callback_scope': 'loopback',
            'oauth_verified': False,
            'authorization_url': 'https://example.invalid/authorize?state=sensitive',
            'redirect_url': 'http://' + '127.0.0.1' + ':39137/callback',
        }
        summary = mod.safe_summary(data)
        self.assertNotIn('authorization_url', summary)
        self.assertNotIn('redirect_url', summary)
        self.assertTrue(summary['authorization_url_available'])
        self.assertEqual(summary['status'], 'AUTH_CALLBACK_RELAY_UNAVAILABLE')

if __name__ == '__main__':
    unittest.main()

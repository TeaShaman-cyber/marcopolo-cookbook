#!/usr/bin/env python3
import json
from urllib.parse import urlparse


def classify_redirect(url):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    loopback = host in {'127.0.0.1', 'localhost', '::1'}
    return {
        'status': 'AUTH_CALLBACK_RELAY_UNAVAILABLE' if loopback else 'CALLBACK_RELAY_CANDIDATE',
        'callback_scope': 'loopback' if loopback else 'external',
        'oauth_verified': False,
    }


def parse_auth_start(text):
    payload = json.loads(text)
    redirect = payload["redirectUrl"]
    result = classify_redirect(redirect)
    result.update({
        "authorization_url": payload["authorizationUrl"],
        "redirect_url": redirect,
    })
    return result


def safe_summary(data):
    return {
        "status": data["status"],
        "callback_scope": data["callback_scope"],
        "oauth_verified": bool(data["oauth_verified"]),
        "authorization_url_available": bool(data.get("authorization_url")),
    }


if __name__ == "__main__":
    import sys
    result = parse_auth_start(sys.stdin.read())
    print(json.dumps(safe_summary(result), sort_keys=True))

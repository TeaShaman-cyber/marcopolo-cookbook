import hashlib
from datetime import datetime, timezone

VALID_PROBE_KINDS = {
    'hosting-identify',
    'cloud-docs',
    'waf-reference',
    'mcp-registry-check',
    'payload-shape-canary',
}


def _now_rfc3339():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def bounded_sha256(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError('data must be bytes')
    return 'sha256:' + hashlib.sha256(bytes(data)).hexdigest()


def new_receipt(target, probe_kind, observation_time=None):
    if not isinstance(target, str) or not target:
        raise ValueError('target is required')
    if probe_kind not in VALID_PROBE_KINDS:
        raise ValueError('invalid probe_kind')
    return {
        'schema_version': 1,
        'target': target,
        'observation_time': observation_time or _now_rfc3339(),
        'probe_kind': probe_kind,
        'observations': [],
        'reference_sources': [],
        'provider_candidates': [],
        'classification': 'INSUFFICIENT_EVIDENCE',
        'confidence': 0.0,
        'raw_hashes': [],
        'failure': None,
    }


def add_observation(receipt, evidence_class, source, value, authority='observed'):
    if not evidence_class or not source:
        raise ValueError('evidence_class and source are required')
    obs = {
        'evidence_class': str(evidence_class),
        'source': str(source),
        'value': value,
        'authority': str(authority),
    }
    receipt['observations'].append(obs)
    return obs


def _candidate_from(obs):
    value = obs.get('value')
    if isinstance(value, dict):
        candidate = value.get('provider_candidate')
        if isinstance(candidate, str) and candidate:
            return candidate.lower()
    return None


def classify_provider(receipt):
    grouped = {}
    authoritative = set()
    for obs in receipt.get('observations', []):
        candidate = _candidate_from(obs)
        if not candidate:
            continue
        grouped.setdefault(candidate, set()).add(obs.get('evidence_class'))
        if obs.get('authority') == 'provider_owned':
            authoritative.add(candidate)

    if not grouped:
        result = ('INSUFFICIENT_EVIDENCE', 0.0)
    else:
        ranked = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        top_candidate, top_classes = ranked[0]
        top_count = len(top_classes)
        ties = [name for name, classes in ranked if len(classes) == top_count]
        if len(ties) > 1 and top_count >= 2:
            result = ('MULTI_PROVIDER_OR_PROXY', 0.5)
        elif top_count >= 2 and top_candidate in authoritative:
            result = ('VERIFIED_PROVIDER', min(1.0, 0.8 + 0.05 * (top_count - 2)))
        elif top_count >= 2:
            result = ('LIKELY_PROVIDER', min(0.79, 0.5 + 0.1 * (top_count - 2)))
        else:
            result = ('INSUFFICIENT_EVIDENCE', 0.25)

    receipt['classification'], receipt['confidence'] = result
    receipt['provider_candidates'] = [
        {'provider': name, 'evidence_classes': sorted(c for c in classes if c)}
        for name, classes in sorted(grouped.items())
    ]
    return result


LAYER_NAMES = {'serving', 'dns', 'registrar', 'application'}

def add_layer_evidence(receipt, layer, evidence_class, source, provider, authority='observed', value=None):
    if layer not in LAYER_NAMES:
        raise ValueError('invalid layer')
    payload = {'provider_candidate': str(provider).lower(), 'layer': layer}
    if value is not None:
        payload['detail'] = value
    obs = add_observation(receipt, evidence_class, source, payload, authority=authority)
    obs['layer'] = layer
    return obs

def classify_layers(receipt):
    grouped = {}
    authoritative = {}
    for obs in receipt.get('observations', []):
        value = obs.get('value')
        layer = obs.get('layer')
        if not layer and isinstance(value, dict):
            layer = value.get('layer')
        if layer not in LAYER_NAMES:
            continue
        candidate = _candidate_from(obs)
        if not candidate:
            continue
        grouped.setdefault(layer, {}).setdefault(candidate, set()).add(obs.get('evidence_class'))
        if obs.get('authority') == 'provider_owned':
            authoritative.setdefault(layer, set()).add(candidate)
    layers = {}
    for layer, candidates in grouped.items():
        candidate, classes = sorted(candidates.items(), key=lambda item: (-len(item[1]), item[0]))[0]
        count = len(classes)
        if layer == 'application':
            classification, confidence = 'OBSERVED_COMPONENT', 0.6
        elif count >= 2 and candidate in authoritative.get(layer, set()):
            classification, confidence = 'VERIFIED_PROVIDER', min(1.0, 0.8 + 0.05 * (count - 2))
        elif count >= 2:
            classification, confidence = 'LIKELY_PROVIDER', min(0.79, 0.5 + 0.1 * (count - 2))
        else:
            classification, confidence = 'INSUFFICIENT_EVIDENCE', 0.25
        layers[layer] = {'provider': candidate, 'classification': classification, 'confidence': confidence, 'evidence_classes': sorted(c for c in classes if c)}
    infra = {entry['provider'] for name, entry in layers.items() if name in {'serving','dns','registrar'} and entry.get('provider')}
    if len(infra) > 1:
        receipt['classification'], receipt['confidence'] = 'MULTI_PROVIDER_OR_PROXY', 0.75
    elif 'serving' in layers:
        receipt['classification'], receipt['confidence'] = layers['serving']['classification'], layers['serving']['confidence']
    elif layers:
        receipt['classification'], receipt['confidence'] = 'INSUFFICIENT_EVIDENCE', 0.25
    else:
        receipt['classification'], receipt['confidence'] = 'INSUFFICIENT_EVIDENCE', 0.0
    receipt['layers'] = layers
    return layers

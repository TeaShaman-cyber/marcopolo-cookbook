import json
from pathlib import Path

VALID_STATES = {
    'DISCOVERED',
    'LIVE_METADATA_VERIFIED',
    'ANONYMOUS_EXECUTION_VERIFIED',
    'REVIEWED_REFERENCE_SOURCE',
}
REQUIRED = {'name','endpoint','domain','state','last_verified','evidence_note'}


def load_reviewed_sources(path):
    data=json.loads(Path(path).read_text())
    sources=data.get('sources')
    if not isinstance(sources,list):
        raise ValueError('sources must be a list')
    for source in sources:
        missing=REQUIRED-set(source)
        if missing:
            raise ValueError('missing fields: '+','.join(sorted(missing)))
        if source['state'] not in VALID_STATES:
            raise ValueError('invalid state')
        if not str(source['endpoint']).startswith('https://'):
            raise ValueError('endpoint must be https')
    return sources


def executable_sources(sources):
    return [s for s in sources if s.get('state') == 'REVIEWED_REFERENCE_SOURCE']

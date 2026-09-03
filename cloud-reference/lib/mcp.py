import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from evidence import bounded_sha256, new_receipt
from sources import executable_sources, load_reviewed_sources

BLOCKED_WAF_TERMS = re.compile(r'\b(bypass|evade|evasion|circumvent|disable|defeat)\b', re.I)
ROUTES = {
    'cloudflare': ('cloudflare-docs', 'search_cloudflare_documentation', 'query'),
    'aws': ('aws-knowledge', 'aws___search_documentation', 'search_phrase'),
    'microsoft': ('microsoft-learn', 'microsoft_docs_search', 'query'),
}


def choose_route(provider):
    key=str(provider).lower()
    if key not in ROUTES:
        raise ValueError('unsupported provider')
    return ROUTES[key]


def build_reference_query(provider, observation, mode='docs'):
    if not isinstance(observation, str) or not observation.strip():
        raise ValueError('observation is required')
    if mode == 'waf':
        if BLOCKED_WAF_TERMS.search(observation):
            raise ValueError('bypass/evasion intent is not allowed')
        return f'Defensive diagnostic documentation for {provider}: {observation}. Focus on documented false positives, status codes, logging, and supported troubleshooting.'
    if mode != 'docs':
        raise ValueError('unsupported mode')
    return f'Official documentation for {provider}: {observation}'


def repo_root():
    return Path(__file__).resolve().parents[2]


def source_registry_path():
    return repo_root() / 'cloud-reference' / 'queries' / 'reviewed-sources.json'


def mcporter_path():
    return repo_root() / 'mcporter' / 'bin' / 'mcporter'


def _temporary_config(sources):
    cfg={'mcpServers':{}}
    for source in executable_sources(sources):
        cfg['mcpServers'][source['name']]={'baseUrl':source['endpoint'],'description':f"Reviewed cloud-reference source for {source['domain']}"}
    handle=tempfile.NamedTemporaryFile('w',prefix='cloudref-mcporter-',suffix='.json',delete=False)
    try:
        json.dump(cfg,handle,sort_keys=True)
        handle.flush()
        return Path(handle.name)
    finally:
        handle.close()


def run_mcporter(args, timeout=15):
    sources=load_reviewed_sources(source_registry_path())
    cfg=_temporary_config(sources)
    try:
        proc=subprocess.run(
            [str(mcporter_path()), '--config', str(cfg), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            'returncode': proc.returncode,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
            'stdout_sha256': bounded_sha256(proc.stdout.encode()),
            'stderr_sha256': bounded_sha256(proc.stderr.encode()),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            'returncode': 124,
            'stdout': exc.stdout or '',
            'stderr': exc.stderr or '',
            'failure': 'REFERENCE_SOURCE_ERROR',
            'reason': 'timeout',
        }
    finally:
        try: os.unlink(cfg)
        except OSError: pass


def check_source(source_name, timeout=15):
    sources=load_reviewed_sources(source_registry_path())
    allowed={s['name'] for s in executable_sources(sources)}
    if source_name not in allowed:
        raise ValueError('source is not reviewed')
    result=run_mcporter(['list', source_name, '--json'], timeout=timeout)
    receipt=new_receipt(source_name,'mcp-registry-check')
    receipt['reference_sources']=[source_name]
    receipt['raw_hashes']=[h for h in (result.get('stdout_sha256'),result.get('stderr_sha256')) if h]
    if result['returncode'] != 0:
        receipt['failure']={'type': result.get('failure','REFERENCE_SOURCE_ERROR'),'message':result.get('stderr','')[:300]}
    else:
        try:
            data=json.loads(result['stdout'])
            receipt['observations']=[{'evidence_class':'mcp_metadata','source':source_name,'value':{'status':data.get('status'),'tools':[t.get('name') for t in data.get('tools',[])]},'authority':'observed'}]
        except json.JSONDecodeError:
            receipt['failure']={'type':'REFERENCE_PROTOCOL_DRIFT','message':'mcporter list returned non-JSON'}
    return receipt


def query_reference(provider, observation, mode='docs', timeout=20):
    server, tool, key=choose_route(provider)
    query=build_reference_query(provider, observation, mode=mode)
    result=run_mcporter(['call', f'{server}.{tool}', f'{key}:{query}'], timeout=timeout)
    receipt=new_receipt(provider, 'waf-reference' if mode=='waf' else 'cloud-docs')
    receipt['reference_sources']=[server]
    receipt['raw_hashes']=[h for h in (result.get('stdout_sha256'),result.get('stderr_sha256')) if h]
    if result['returncode'] != 0:
        err=(result.get('stderr') or result.get('stdout') or '')[:500]
        upper=err.upper()
        if '401' in upper or 'AUTH' in upper:
            ftype='REFERENCE_AUTH_REQUIRED'
        elif result.get('failure'):
            ftype=result['failure']
        else:
            ftype='REFERENCE_SOURCE_ERROR'
        receipt['failure']={'type':ftype,'message':err}
        return receipt
    receipt['observations']=[{
        'evidence_class':'reference_response',
        'source':server,
        'value':{'tool':tool,'response_excerpt':result['stdout'][:1200]},
        'authority':'provider_owned' if provider in {'aws','cloudflare','microsoft'} else 'observed',
    }]
    return receipt

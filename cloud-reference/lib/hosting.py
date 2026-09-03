import json
import ipaddress
import re
import socket
import ssl
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from evidence import add_layer_evidence, add_observation, bounded_sha256, classify_layers, classify_provider, new_receipt

HOST_RE = re.compile(r'^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$')
SAFE_HEADERS = {'server','via','x-vercel-id','cf-ray','cf-cache-status','x-powered-by','x-request-id','fly-request-id'}


def validate_hostname(value):
    if not isinstance(value, str) or not HOST_RE.fullmatch(value):
        raise ValueError('invalid hostname')
    return value.lower()


def detect_provider_candidate(kind, value):
    text = str(value).lower()
    if kind == 'cname':
        if 'vercel-dns.com' in text or 'vercel.app' in text:
            return 'vercel'
        if 'cloudflare' in text:
            return 'cloudflare'
        if 'amazonaws.com' in text or 'cloudfront.net' in text:
            return 'aws'
        if 'fly.dev' in text:
            return 'fly.io'
    if kind == 'header':
        if text in {'x-vercel-id'}:
            return 'vercel'
        if text in {'cf-ray','cf-cache-status'}:
            return 'cloudflare'
        if text in {'fly-request-id'}:
            return 'fly.io'
    return None



def tls_provider_candidate(tls):
    issuer = json.dumps(tls.get('issuer', []), sort_keys=True).lower()
    if 'amazon' in issuer:
        return 'aws'
    return None


def match_aws_ranges(ips, ranges):
    matches=[]
    prefixes=ranges.get('prefixes', [])
    for raw_ip in ips:
        ip=ipaddress.ip_address(raw_ip)
        for item in prefixes:
            try:
                network=ipaddress.ip_network(item['ip_prefix'])
            except (KeyError, ValueError):
                continue
            if ip in network:
                matches.append({
                    'ip': raw_ip,
                    'ip_prefix': item['ip_prefix'],
                    'region': item.get('region'),
                    'network_border_group': item.get('network_border_group'),
                    'service': item.get('service'),
                    'provider_candidate': 'aws',
                })
    return matches



def parse_bounded_json(body, max_bytes=8_000_000):
    if len(body) > max_bytes:
        raise ValueError('payload exceeds bounded JSON limit')
    return json.loads(body)

def fetch_aws_ranges(timeout=5):
    url='https://ip-ranges.amazonaws.com/ip-ranges.json'
    max_bytes=8_000_000
    with urllib.request.urlopen(url, timeout=timeout) as response:
        declared=response.headers.get('Content-Length')
        if declared and int(declared) > max_bytes:
            raise ValueError('AWS ranges payload exceeds bounded limit')
        body=response.read(max_bytes + 1)
    return parse_bounded_json(body, max_bytes=max_bytes), bounded_sha256(body)

def collect_dns(hostname):
    out=[]
    infos=socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    ips=sorted({item[4][0] for item in infos})
    for ip in ips:
        out.append({'type':'address','value':ip})
    try:
        proc=subprocess.run(['dig','+short','CNAME',hostname],capture_output=True,text=True,timeout=5,check=False)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                cname=line.strip().rstrip('.')
                if cname:
                    rec={'type':'cname','value':cname}
                    cand=detect_provider_candidate('cname', cname)
                    if cand: rec['provider_candidate']=cand
                    out.append(rec)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return out


def collect_tls(hostname, port=443, timeout=5):
    ctx=ssl.create_default_context()
    with socket.create_connection((hostname,port),timeout=timeout) as raw:
        with ctx.wrap_socket(raw,server_hostname=hostname) as s:
            cert=s.getpeercert()
    return {
        'issuer': cert.get('issuer', []),
        'subject': cert.get('subject', []),
        'subjectAltName': cert.get('subjectAltName', []),
        'notBefore': cert.get('notBefore'),
        'notAfter': cert.get('notAfter'),
        'version': cert.get('version'),
    }


def collect_http(hostname, timeout=5, body_limit=4096):
    req=urllib.request.Request(f'https://{hostname}/',headers={'User-Agent':'marcopolo-cloud-reference/0.1','Accept':'*/*'})
    try:
        resp=urllib.request.urlopen(req,timeout=timeout)
        body=resp.read(body_limit)
        status=getattr(resp,'status',200)
        headers=resp.headers
        final_url=resp.geturl()
    except urllib.error.HTTPError as e:
        body=e.read(body_limit)
        status=e.code
        headers=e.headers
        final_url=e.geturl()
    selected={}
    for k,v in headers.items():
        lk=k.lower()
        if lk in SAFE_HEADERS:
            selected[lk]=v
    return {
        'status': status,
        'final_url': final_url,
        'headers': selected,
        'body_sha256': bounded_sha256(body),
        'body_excerpt': body[:160].decode('utf-8','replace').replace('\n',' ')[:160],
    }


def build_hosting_receipt(hostname, timeout=5, observation_time=None):
    hostname=validate_hostname(hostname)
    receipt=new_receipt(hostname,'hosting-identify',observation_time)
    try:
        dns=collect_dns(hostname)
        add_observation(receipt,'dns','target',dns)
        ips=[item['value'] for item in dns if item.get('type') == 'address']
        for item in dns:
            if item.get('provider_candidate'):
                add_observation(receipt,'dns_provider_marker','target',{'provider_candidate':item['provider_candidate'],'record':item['value']})
        try:
            aws_ranges, aws_hash = fetch_aws_ranges(timeout=timeout)
            receipt['raw_hashes'].append(aws_hash)
            matches=match_aws_ranges(ips, aws_ranges)
            if matches:
                add_observation(receipt,'network_provider_range','aws-ip-ranges',{'provider_candidate':'aws','matches':matches,'createDate':aws_ranges.get('createDate')},authority='provider_owned')
                add_layer_evidence(receipt,'serving','network_provider_range','aws-ip-ranges','aws',authority='provider_owned')
        except Exception as range_exc:
            add_observation(receipt,'network_provider_range','aws-ip-ranges',{'error':str(range_exc)},authority='observed')
    except Exception as e:
        receipt['failure']={'type':'TARGET_DNS_ERROR','message':str(e)}
        return receipt
    try:
        tls=collect_tls(hostname,timeout=timeout)
        add_observation(receipt,'tls','target',tls)
        tls_candidate=tls_provider_candidate(tls)
        if tls_candidate:
            add_observation(receipt,'tls_provider_marker','target',{'provider_candidate':tls_candidate,'issuer':tls.get('issuer')},authority='observed')
            add_layer_evidence(receipt,'serving','tls_provider_marker','target',tls_candidate)
    except Exception as e:
        add_observation(receipt,'tls','target',{'error':str(e)})
    try:
        http=collect_http(hostname,timeout=timeout)
        add_observation(receipt,'http','target',http)
        receipt['raw_hashes'].append(http['body_sha256'])
        server_component=http.get('headers',{}).get('server')
        if server_component:
            add_layer_evidence(receipt,'application','http_server','target',server_component)
        for header in http['headers']:
            cand=detect_provider_candidate('header',header)
            if cand:
                authority='provider_owned' if header in {'x-vercel-id','cf-ray','fly-request-id'} else 'observed'
                add_observation(receipt,'provider_header','target',{'provider_candidate':cand,'header':header},authority=authority)
    except Exception as e:
        receipt['failure']={'type':'TARGET_HTTP_ERROR','message':str(e)}
    classify_provider(receipt)
    classify_layers(receipt)
    return receipt

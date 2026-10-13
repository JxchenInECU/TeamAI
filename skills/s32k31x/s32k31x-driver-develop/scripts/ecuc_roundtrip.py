"""Compare two tool-exported ECUC baselines without dropping unknown XML structures."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def local(tag):
    return tag.rsplit('}', 1)[-1]


def tree(path):
    data = path.read_bytes()
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError(f'Unsupported DTD/entity in {path}')
    root = ET.fromstring(data)
    if local(root.tag) != 'AUTOSAR':
        raise ValueError(f'Expected tool-exported AUTOSAR ECUC: {path}')
    modules = root.findall('.//{*}ECUC-MODULE-CONFIGURATION-VALUES')
    if not modules:
        raise ValueError(f'No ECUC module/config_set found: {path}')
    for module in modules:
        if module.findtext('{*}SHORT-NAME') is None:
            raise ValueError(f'Unnamed ECUC module: {path}')
        if module.find('{*}CONTAINERS/{*}ECUC-CONTAINER-VALUE') is None:
            raise ValueError(f'Missing config_set container: {path}')
    for ref in root.findall('.//{*}DEFINITION-REF') + root.findall('.//{*}VALUE-REF'):
        value = (ref.text or '').strip()
        if value and not value.startswith('/'):
            raise ValueError(f'Invalid absolute ECUC reference: {path}')
    return root, hashlib.sha256(data).hexdigest()


def records(root):
    result = {}

    def walk(node, path):
        value = (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(),
                 (node.tail or '').strip())
        result[path] = value
        counts = Counter()
        for child in node:
            counts[child.tag] += 1
            name = child.findtext('{*}SHORT-NAME')
            label = f'{{{name}}}' if name else f'[{counts[child.tag]}]'
            key = f'{path}/{child.tag}{label}'
            if key in result:
                key += f'[{counts[child.tag]}]'
            walk(child, key)

    walk(root, '/' + root.tag)
    return result


def compare(before, after):
    left = {p.name: p for p in Path(before).glob('*.ecvd')}
    right = {p.name: p for p in Path(after).glob('*.ecvd')}
    if not left or not right:
        raise ValueError('Both directories must contain tool-exported *.ecvd files')
    issues = []
    for name in sorted(left.keys() ^ right.keys()):
        issues.append({'file': name, 'issue': 'missing_from_one_export'})
    hashes = {}
    for name in sorted(left.keys() & right.keys()):
        a, ah = tree(left[name])
        b, bh = tree(right[name])
        hashes[name] = {'before': ah, 'after': bh}
        ar, br = records(a), records(b)
        for path in sorted(ar.keys() | br.keys()):
            if ar.get(path) != br.get(path):
                issues.append({'file': name, 'path': path,
                               'before': ar.get(path), 'after': br.get(path)})
    return {'status': 'pass' if not issues else 'roundtrip_mismatch',
            'file_count': len(left), 'hashes': hashes,
            'issue_count': len(issues), 'issues': issues[:200],
            'truncated': len(issues) > 200,
            'note': 'Strict XML semantics including list/choice wrappers, module/config_set names and references; whitespace-only formatting ignored'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.before, args.after)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'pass' else 1
    except (OSError, ValueError, ET.ParseError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())

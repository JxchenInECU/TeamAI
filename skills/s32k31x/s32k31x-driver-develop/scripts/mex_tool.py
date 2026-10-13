"""Read, structurally compare, and stage exact UTF-8 MEX patches. Stdlib only."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

SUPPORTED = {'S32K310', 'S32K311', 'S32K312', 'S32K314'}


def local(tag):
    return tag.rsplit('}', 1)[-1]


def parse(data):
    # Never accept entity declarations or a DTD from project inputs.
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('DTD/entity declarations are unsupported')
    root = ET.fromstring(data)
    if local(root.tag) != 'configuration':
        raise ValueError('Expected a MEX configuration root')
    return root


def common(root):
    node = root.find('{*}common')
    result = {k: node.findtext('{*}' + k) if node is not None else None
              for k in ('processor', 'package', 'mcu_data')}
    cores = node.find('{*}cores') if node is not None else None
    result['cores'] = dict(cores.attrib) if cores is not None else None
    return result


def records(root):
    result = {}

    def walk(node, path):
        result[path] = {'tag': node.tag, 'attributes': dict(node.attrib),
                        'text': (node.text or '').strip(),
                        'tail': (node.tail or '').strip()}
        count = Counter()
        for child in node:
            count[child.tag] += 1
            walk(child, f'{path}/{child.tag}[{count[child.tag]}]')
    walk(root, '/' + root.tag + '[1]')
    return result


def inspect(path, query=None):
    data = Path(path).read_bytes()
    root = parse(data)
    info = common(root)
    info.update(path=str(Path(path).resolve()), sha256=hashlib.sha256(data).hexdigest(),
                root_attributes=root.attrib, namespace=root.tag.split('}')[0].lstrip('{')
                if '}' in root.tag else '', in_scope=info['processor'] in SUPPORTED)
    info['tools'] = []
    for tool in root.findall('{*}tools/*'):
        groups = []
        for group in tool.findall('.//{*}functional_group'):
            groups.append({'group': group.attrib,
                           'instances': [i.attrib for i in group.findall('{*}instances/{*}instance')]})
        info['tools'].append({'element': local(tool.tag), **tool.attrib,
                              'generated_files': [f.attrib for f in tool.findall('{*}generated_project_files/{*}file')],
                              'functional_groups': groups,
                              'clock_configurations': [c.attrib for c in tool.findall('{*}clock_configurations/{*}clock_configuration')],
                              'pin_functions': [f.attrib for f in tool.findall('{*}functions_list/{*}function')]})
    info['validation'] = 'XML parsed only; no schema, Config Tools, build or hardware validation'
    info['dependency_note'] = 'dependencies are constraint declarations, not evaluated errors'
    if query:
        info['matches'] = [{'path': k, **v} for k, v in records(root).items()
                           if query.casefold() in (k + json.dumps(v, ensure_ascii=False)).casefold()]
    return info


def diff(before, after):
    a = records(parse(Path(before).read_bytes()))
    b = records(parse(Path(after).read_bytes()))
    changes = [{'path': k, 'before': a.get(k), 'after': b.get(k)}
               for k in sorted(a.keys() | b.keys()) if a.get(k) != b.get(k)]
    return {'change_count': len(changes), 'changes': changes,
            'note': 'Positional XML comparison; reordering may produce multiple changes'}


def patched_bytes(data, plan):
    original = parse(data)
    identity = common(original)
    if identity['processor'] not in SUPPORTED:
        raise ValueError('Patch supports only S32K310/311/312/314; inspect/diff can read reference samples')
    if not isinstance(plan, dict):
        raise ValueError('Patch plan must be a JSON object')
    digest = hashlib.sha256(data).hexdigest()
    if plan.get('sha256') != digest:
        raise ValueError('Source SHA-256 mismatch; reread current file before patching')
    # Decode validation only; perform byte replacements to preserve BOM and CRLF.
    data.decode('utf-8-sig')
    edits = plan.get('replacements')
    if not isinstance(edits, list) or not edits:
        raise ValueError('Expected a nonempty replacements list')
    spans = []
    for edit in edits:
        if not isinstance(edit, dict) or not isinstance(edit.get('old'), str) or not isinstance(edit.get('new'), str):
            raise ValueError('old/new must be strings')
        old, new = edit['old'].encode('utf-8'), edit['new'].encode('utf-8')
        if not old or old == new or data.count(old) != 1:
            raise ValueError('Each old fragment must match once and differ from new')
        start = data.index(old)
        spans.append((start, start + len(old), new))
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Replacement spans overlap')
    result = data
    for start, end, new in reversed(spans):
        result = result[:start] + new + result[end:]
    changed = parse(result)
    def newline_kinds(raw):
        return set(re.findall(rb'\r\n|(?<!\r)\n|\r(?!\n)', raw))
    before_kinds = newline_kinds(data)
    after_kinds = newline_kinds(result)
    if after_kinds != before_kinds:
        raise ValueError('Patch changes newline style; preserve the source line endings')
    if (records(changed.find('{*}common')) != records(original.find('{*}common'))
            or changed.tag != original.tag or changed.get('version') != original.get('version')):
        raise ValueError('Patch cannot change MCU, package, core, SDK or MEX format identity')
    return result


def publish_new(path, data):
    """Publish a complete candidate without ever replacing an existing file."""
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as stream:
            temp_name = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp_name, path)
    finally:
        if temp_name is not None:
            os.unlink(temp_name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('inspect')
    p.add_argument('mex', type=Path)
    p.add_argument('--query')
    p = sub.add_parser('diff')
    p.add_argument('before', type=Path)
    p.add_argument('after', type=Path)
    p = sub.add_parser('patch')
    p.add_argument('mex', type=Path)
    p.add_argument('plan', type=Path)
    p.add_argument('--output', type=Path, help='New staging file; omitted means dry run')
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            result = inspect(args.mex, args.query)
        elif args.command == 'diff':
            result = diff(args.before, args.after)
        else:
            data = args.mex.read_bytes()
            new = patched_bytes(data, json.loads(args.plan.read_text(encoding='utf-8-sig')))
            if args.output:
                if args.output.suffix.lower() != '.mex':
                    raise ValueError('Output must have .mex extension')
                if hashlib.sha256(args.mex.read_bytes()).digest() != hashlib.sha256(data).digest():
                    raise ValueError('Source changed during patch; retry from a new baseline')
                publish_new(args.output, new)
            result = {'mode': 'staged' if args.output else 'dry-run',
                      'output': str(args.output.resolve()) if args.output else None,
                      'source_unchanged': True, 'sha256': hashlib.sha256(new).hexdigest(),
                      'validation': 'XML only; must reload, validate and generate in S32DS'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ET.ParseError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())

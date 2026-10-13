"""Run a documented S32DS command and retain raw logs plus a conservative result."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

TOOL_ERROR = re.compile(r'\[TOOL\].*?resource "([^"]+)".*?following error:', re.I)
GENERIC_ERROR = re.compile(r'\b(error|failed|exception|severe)\b|错误|失败', re.I)
BUILD_ERROR = re.compile(r'(^|\s)(error:|fatal error:)|\bundefined reference\b|构建失败', re.I)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode_log(path):
    with Path(path).open('rb') as stream:
        sample = stream.read(65536)
    options = [(sample.decode(codec, errors='replace').count('\ufffd'), codec) for codec in ('utf-8', 'cp936')]
    codec = min(options)[1]
    return codec


def classify(log_paths, codecs, modules, kind, exit_code, missing):
    target_errors, other_errors, build_errors = [], [], []
    for path, codec in zip(log_paths, codecs):
        with path.open('r', encoding=codec, errors='replace') as stream:
            for line in stream:
                matched = TOOL_ERROR.search(line)
                if matched:
                    (target_errors if matched.group(1).casefold() in modules else other_errors).append(line[:500])
                elif kind == 'build' and BUILD_ERROR.search(line):
                    build_errors.append(line[:500])
                elif GENERIC_ERROR.search(line) and not line.lstrip().startswith(('Warning:', '!ENTRY')):
                    other_errors.append(line[:500])
    if target_errors:
        status = 'config_error'
    elif kind == 'build' and (build_errors or exit_code != 0):
        status = 'build_error'
    elif exit_code != 0 or missing:
        status = 'incomplete'
    elif other_errors:
        status = 'needs_review'
    else:
        status = 'pass'
    return {'status': status, 'target_errors': target_errors[:30],
            'other_errors': other_errors[:30], 'build_errors': build_errors[:30],
            'diagnostics_truncated': any(len(x) > 30 for x in (target_errors, other_errors, build_errors))}


def run(args):
    command = args.command[1:] if args.command and args.command[0] == '--' else args.command
    if not command:
        raise ValueError('A documented S32DS command is required after --')
    if any(re.search(r'ignore.*version|disable.*version', item, re.I) for item in command):
        raise ValueError('Version checking must remain enabled')
    if args.kind == 'config' and not args.module:
        raise ValueError('At least one target module is required for configuration validation')
    previous = {str(p.resolve()): (p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else None
                for p in args.expected}
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    folder = args.evidence / run_id
    folder.mkdir(parents=True, exist_ok=False)
    inputs = {}
    if args.input:
        (folder / 'inputs').mkdir()
    for index, path in enumerate(args.input):
        if not path.is_file():
            raise ValueError(f'Input file does not exist: {path}')
        snapshot = folder / 'inputs' / f'{index:03d}-{path.name}'
        with snapshot.open('xb') as target, path.open('rb') as source:
            shutil.copyfileobj(source, target)
        inputs[str(path.resolve())] = {'sha256': sha(snapshot), 'snapshot': str(snapshot.relative_to(folder))}
    started = datetime.now(timezone.utc).isoformat()
    with (folder / 'stdout.bin').open('xb') as out, (folder / 'stderr.bin').open('xb') as err:
        try:
            exit_code = subprocess.run(command, stdout=out, stderr=err, check=False,
                                       timeout=args.timeout).returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            exit_code, timed_out = None, True
        except OSError as exc:
            exit_code, timed_out = None, False
            err.write(str(exc).encode('utf-8', errors='replace'))
    outputs = {str(p.resolve()): {'exists': p.is_file(),
                                  'sha256': sha(p) if p.is_file() else None}
               for p in args.expected}
    missing = [p for p, entry in outputs.items() if not entry['exists']]
    stale = [str(p.resolve()) for p in args.expected if p.is_file() and
             previous[str(p.resolve())] == (p.stat().st_mtime_ns, p.stat().st_size)]
    log_paths = [folder / 'stdout.bin', folder / 'stderr.bin']
    out_codec, err_codec = (decode_log(p) for p in log_paths)
    summary = classify(log_paths, (out_codec, err_codec),
                       {m.casefold() for m in args.module}, args.kind, exit_code, missing + stale)
    if timed_out:
        summary['status'] = 'timeout'
    summary.update(run_id=run_id, kind=args.kind, command=command, version=args.version_label,
                   started=started, finished=datetime.now(timezone.utc).isoformat(),
                   exit_code=exit_code, process_finished=exit_code is not None and not timed_out,
                   inputs=inputs, outputs=outputs, missing_outputs=missing, stale_outputs=stale,
                   log_encoding={'stdout': out_codec, 'stderr': err_codec},
                   raw_logs={'stdout': 'stdout.bin', 'stderr': 'stderr.bin'})
    (folder / 'manifest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return folder, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--kind', choices=('config', 'build'), required=True)
    parser.add_argument('--module', action='append', default=[])
    parser.add_argument('--input', type=Path, action='append', default=[])
    parser.add_argument('--expected', type=Path, action='append', required=True)
    parser.add_argument('--version-label', required=True)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        folder, result = run(args)
        print(json.dumps({'evidence': str(folder), 'status': result['status'],
                          'exit_code': result['exit_code'],
                          'missing_outputs': result['missing_outputs']}, ensure_ascii=False))
        return 0 if result['status'] == 'pass' else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())

"""Read-only inventory of an S32DS install and an optional user project."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from mex_tool import SUPPORTED, common, parse


def inventory(install, project=None):
    if not install.is_dir():
        raise ValueError(f'Install directory missing: {install}')
    eclipse = install / 'eclipse'
    plugins = eclipse / 'plugins'
    report = {'install': str(install.resolve()),
              'launchers': [str(p) for n in ('s32ds.exe', 's32dsc.exe', 'eclipsec.exe')
                            if (p := eclipse / n).is_file()],
              'plugins': sorted(p.name for p in plugins.glob('*') if any(
                  term in p.name for term in ('swtools.doc.uct_', 'swtools.clocks_',
                                              'swtools.pins_', 'swtools.periphs_',
                                              's32ds.doc.platform.reference_'))),
              'sdk_manifests': [], 'errors': [],
              'note': 'Filesystem inventory only; does not prove package/license/UI readiness'}
    for manifest in (install / 'S32DS' / 'software').glob('*/sdk_manifest.xml'):
        try:
            root = ET.parse(manifest).getroot()
            devices = [dict(d.attrib, packages=[p.attrib for p in d.findall('{*}package')])
                       for d in root.findall('.//{*}device') if d.get('name') in SUPPORTED or d.get('id') in SUPPORTED]
            if not devices and 'S32K3' not in str(manifest):
                continue
            counts = Counter()
            scoped = []
            total = 0
            for mex in manifest.parent.rglob('*.mex'):
                total += 1
                try:
                    proc = common(parse(mex.read_bytes()))['processor']
                    counts[proc or 'unknown'] += 1
                    if proc in SUPPORTED:
                        scoped.append(str(mex))
                except (OSError, ValueError, ET.ParseError) as exc:
                    report['errors'].append({'path': str(mex), 'error': str(exc)})
            report['sdk_manifests'].append({'path': str(manifest), 'root_attributes': root.attrib,
                'ksdk': [n.attrib for n in root.findall('{*}ksdk')], 's32k31x_devices': devices,
                'mex_count': total, 'mex_processors': dict(counts), 's32k31x_mex': scoped})
        except (OSError, ET.ParseError) as exc:
            report['errors'].append({'path': str(manifest), 'error': str(exc)})
    if project:
        if not project.is_dir():
            raise ValueError(f'Project directory missing: {project}')
        report['project'] = {'root': str(project.resolve()),
                             'mex': [str(p.relative_to(project)) for p in project.rglob('*.mex')],
                             'metadata': [str(p.relative_to(project)) for p in project.rglob('*')
                                          if p.is_file() and p.name in ('.project', '.cproject', 'sdk_manifest.xml')]}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', type=Path, default=Path(r'C:\NXP\S32DS.3.6.6'))
    parser.add_argument('--project', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inventory(args.install, args.project), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())

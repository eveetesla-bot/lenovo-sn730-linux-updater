#!/usr/bin/env python3
"""Download/extract a pinned Lenovo package without executing vendor tools.

No disk device access or firmware flashing. Firmware remains local and must not
be committed or redistributed. Requires innoextract from the distribution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request
from sn730_update import require, validate_payload

URL = 'https://download.lenovo.com/pccbbs/mobiles/fwnva70.exe'
INSTALLER_SHA256 = 'c030171d1bb5e65b8f9b9bcd0234ba0d805f2635f6e96a5951b78064347f9a90'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while data := f.read(4*1024**2):
            h.update(data)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('work'))
    args = p.parse_args()
    extractor = shutil.which('innoextract')
    require(extractor is not None, 'Install innoextract from your distribution first')
    require(not args.output.exists(), 'Output already exists; inspect it instead of overwriting')
    args.output.mkdir(mode=0o700, parents=True)
    installer = args.output/'fwnva70.exe'
    with urllib.request.urlopen(URL, timeout=60) as source, installer.open('xb') as target:
        shutil.copyfileobj(source, target, 4*1024**2)
    require(sha256(installer) == INSTALLER_SHA256,
            'Installer SHA256 differs from the tested package; stop, do not change the hash to bypass this check')
    extracted = args.output/'extracted'
    subprocess.run([extractor, '--extract', '--output-dir', str(extracted), str(installer)], check=True)
    payloads = list(extracted.rglob('11170101.fluf'))
    profiles = list(extracted.rglob('fwwinsd.pro'))
    require(len(payloads) == len(profiles) == 1, 'Unexpected vendor package contents')
    validate_payload(payloads[0], profiles[0])
    print(json.dumps({'source': URL, 'firmware': str(payloads[0]), 'profile': str(profiles[0]),
                      'firmware_modified': False, 'vendor_program_executed': False,
                      'flash_performed': False}, indent=2))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Conservative, experimental SN730 update helper. Read-only by default.

Shared by Gérard Huret, alias gg31, to help others. Not affiliated with Lenovo or Western Digital.
Never reboots, resets a live controller, changes partitions or forces an image.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import subprocess
import sys

MODEL = 'WDC PC SN730 SDBQNTY-256G-1001'
OLD = '11110101'
NEW = '11170101'
PAYLOAD_SHA256 = '2dc6487beb9829a30af8c2737513139d211245e07670d2b5993f4a96d0e2b499'
PROFILE_SHA256 = '85909f5c7f1198ef9d3bc93732448f381a27f58f1fcac9b9deefdd25a62cc4fb'
PAYLOAD_SIZE = 2588672


class SafetyError(Exception):
    """A required safety condition failed; do not continue or force a retry."""


def require(condition, message):
    # Safety checks must remain active under python -O. Do not replace by assert.
    if not condition:
        raise SafetyError(message)


def as_int(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            pass
    raise SafetyError('Unexpected integer in controller output')


def slot_revision(slots, number):
    value = slots.get(f'Firmware Rev Slot {number}', '')
    require(isinstance(value, str), 'Unexpected firmware slot revision format')
    if not value.strip() or value.strip() == '0':
        return ''
    match = re.fullmatch(r'\d+ \(([^)]*)\)', value.strip())
    if match:
        return match.group(1).strip()
    require(bool(re.fullmatch(r'[A-Z0-9]{8}', value.strip())), 'Unknown firmware slot encoding')
    return value.strip()


def normalize_slots(raw):
    require(isinstance(raw, dict) and len(raw) == 1, 'Unexpected fw-log JSON schema')
    slots = next(iter(raw.values()))
    require(isinstance(slots, dict), 'Unexpected fw-log JSON object')
    require('Active Firmware Slot (afi)' in slots, 'Missing firmware slot information')
    as_int(slots['Active Firmware Slot (afi)'])
    return slots


def validate_identity(controller, expected_serial):
    require(bool(expected_serial.strip()), 'An explicit expected serial is required')
    require(controller.get('mn', '').strip() == MODEL, 'Unsupported model; no write permitted')
    require(controller.get('sn', '').strip() == expected_serial.strip(), 'Device serial mismatch')
    require(controller.get('fr', '').strip() in {OLD, NEW}, 'Unsupported firmware revision')
    require(as_int(controller.get('oacs')) & 4, 'Firmware download/commit is unsupported')
    require(((as_int(controller.get('frmw')) >> 1) & 7) == 2, 'Expected exactly two firmware slots')
    require(as_int(controller.get('fwug')) == 1, 'Unsupported firmware update granularity')


def validate_health(smart):
    require(as_int(smart.get('critical_warning')) == 0, 'SMART critical warning: stop')
    require(as_int(smart.get('media_errors')) == 0, 'SMART media errors: stop')


def validate_slots(slots, action):
    afi = as_int(slots['Active Firmware Slot (afi)'])
    active, pending = afi & 7, (afi >> 4) & 7
    first, second = slot_revision(slots, 1), slot_revision(slots, 2)
    require(first == OLD, 'Slot 1 is not the expected original firmware; preserve it')
    if action in {'check', 'stage'}:
        require(active == 1 and pending == 0, 'Unexpected active/pending slot')
        require(second == '', 'Slot 2 is occupied; do not overwrite or repeat staging')
    elif action == 'activate':
        require(active == 1 and pending == 0, 'Activation already pending or unexpected slot')
        require(second == NEW, 'Expected firmware is not stored in slot 2')
    elif action == 'verify':
        require(active == 2 and pending == 0 and second == NEW,
                'New firmware is not active; reboot/activation is not verified')
    else:
        raise SafetyError('Unknown action')


def validate_payload(payload, profile):
    require(payload.is_file() and not payload.is_symlink(), 'A regular, non-symlink firmware file is required')
    require(profile.is_file() and not profile.is_symlink(), 'A regular, non-symlink vendor profile is required')
    data, mapping = payload.read_bytes(), profile.read_bytes()
    require(len(data) == PAYLOAD_SIZE and len(data) % 4096 == 0, 'Firmware size/alignment mismatch')
    require(hashlib.sha256(data).hexdigest() == PAYLOAD_SHA256, 'Firmware SHA256 mismatch')
    require(hashlib.sha256(mapping).hexdigest() == PROFILE_SHA256, 'Vendor profile SHA256 mismatch')
    require(data.startswith(b'FLUF Format 002') and b'FlashVer: 11170101' in data[:4096],
            'Unexpected firmware header')
    rows = csv.reader(mapping.decode('utf-8-sig', errors='replace').splitlines())
    require(any(row[:4] == [MODEL, OLD, NEW, '11170101.fluf'] for row in rows),
            'Exact official model/version transition not found')


def validate_consent(args):
    require(args.acknowledge_backup, 'A tested, recoverable backup must be acknowledged')
    require(args.acknowledge_stable_power, 'Stable mains power must be acknowledged')
    require(args.acknowledge_experimental_method, 'The experimental Linux method must be acknowledged')


def validate_power(base=Path('/sys/class/power_supply')):
    for battery in base.glob('*'):
        kind, status = battery/'type', battery/'status'
        if kind.exists() and kind.read_text().strip() == 'Battery':
            require(status.exists() and status.read_text().strip() in {'Full', 'Charging', 'Not charging'},
                    'Battery is discharging or its status is unknown')


class Nvme:
    def __init__(self, device, executable):
        self.device, self.executable = device, executable

    def call(self, verb, *options):
        result = subprocess.run([self.executable, verb, self.device, *options],
                                capture_output=True, text=True, check=False)
        require(result.returncode == 0, f'nvme {verb} failed; stop, do not force/retry blindly')
        return result.stdout

    def read(self, verb):
        try:
            return json.loads(self.call(verb, '-o', 'json'))
        except json.JSONDecodeError as exc:
            raise SafetyError('Malformed nvme JSON output') from exc

    def slots(self):
        return normalize_slots(self.read('fw-log'))


def snapshot(nvme, expected_serial, action):
    identity, smart, slots = nvme.read('id-ctrl'), nvme.read('smart-log'), nvme.slots()
    validate_identity(identity, expected_serial)
    validate_health(smart)
    require(identity['fr'].strip() == (NEW if action == 'verify' else OLD),
            'Firmware revision does not match the requested phase')
    validate_slots(slots, action)
    return {'controller': identity, 'smart': smart, 'slots': slots}


def execute_stage(nvme, firmware, record):
    # Keep slot 1 intact. A controller refusal stops this sequence immediately.
    record('download_started')
    nvme.call('fw-download', '--fw='+str(firmware.resolve()), '--xfer=4096')
    record('download_completed')
    nvme.call('fw-commit', '--slot=2', '--action=0')
    slots = nvme.slots()
    validate_slots(slots, 'activate')
    record('stored_inactive_not_activated', slots=slots)


def execute_activation(nvme, record):
    # No live reset, no immediate activation and no automatic reboot.
    record('activation_request_started')
    nvme.call('fw-commit', '--slot=2', '--action=2')
    slots = nvme.slots()
    afi = as_int(slots['Active Firmware Slot (afi)'])
    require((afi & 7) == 1 and ((afi >> 4) & 7) == 2, 'Unexpected activation state; stop and inspect')
    require(slot_revision(slots, 1) == OLD and slot_revision(slots, 2) == NEW, 'Unexpected stored revision')
    record('activation_pending_manual_clean_reboot', slots=slots)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device', required=True, help='Controller character device, e.g. /dev/nvme0 (not a namespace)')
    p.add_argument('--expected-serial', required=True, help='Your own SSD serial, checked locally; never hardcoded')
    p.add_argument('--firmware', type=Path)
    p.add_argument('--profile', type=Path)
    p.add_argument('--action', choices=['check', 'stage', 'activate', 'verify'], default='check')
    p.add_argument('--apply', action='store_true', help='Allow the explicitly selected write phase')
    p.add_argument('--acknowledge-backup', action='store_true')
    p.add_argument('--acknowledge-stable-power', action='store_true')
    p.add_argument('--acknowledge-experimental-method', action='store_true')
    p.add_argument('--log-dir', type=Path, default=Path('logs'))
    args = p.parse_args(argv)
    require(platform.system() == 'Linux', 'Linux is required')
    require(os.geteuid() == 0, 'Run with sudo for local NVMe access')
    device = Path(args.device).resolve(strict=True)
    require(bool(re.fullmatch(r'/dev/nvme\d+', str(device))), 'Select an NVMe controller, not a partition/namespace')
    require(stat.S_ISCHR(device.stat().st_mode), 'Controller must be a character device')
    sys_serial = Path('/sys/class/nvme')/device.name/'serial'
    require(sys_serial.read_text().strip() == args.expected_serial.strip(), 'Sysfs serial mismatch')
    binary = shutil.which('nvme')
    require(binary is not None, 'Install nvme-cli from your distribution')
    require(not args.apply or args.action in {'stage', 'activate'}, '--apply is only valid for stage/activate')
    if args.action != 'verify':
        require(args.firmware is not None and args.profile is not None, '--firmware and --profile are required')
        validate_payload(args.firmware, args.profile)
    nvme = Nvme(str(device), binary)
    before = snapshot(nvme, args.expected_serial, args.action)
    validate_power()
    if not args.apply:
        print(json.dumps({'read_only': True, 'action_checked': args.action, 'model': MODEL,
                          'firmware': before['controller']['fr'].strip(), 'serial_matched': True,
                          'write_performed': False, 'reboot_performed': False}, indent=2))
        return 0
    validate_consent(args)
    import fcntl
    lock_flags = os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW
    lock_fd = os.open('/run/lock/sn730-updater-'+device.name+'.lock', lock_flags, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not args.log_dir.is_symlink(), 'Log directory must not be a symlink')
        args.log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(args.log_dir.stat().st_uid == 0 and args.log_dir.stat().st_mode & 0o077 == 0,
                'Use a private root-owned log directory (mode 0700)')
        log = args.log_dir / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+args.action)
        log.mkdir(mode=0o700)
        # These LOCAL logs include the runtime device serial. Never publish them.
        (log/'before.json').write_text(json.dumps(before, indent=2))
        state = {'action': args.action, 'model': MODEL, 'force': False, 'reboot_performed': False}

        def record(phase, **kw):
            state.update(kw, phase=phase, updated_utc=datetime.now(timezone.utc).isoformat())
            temp = log/'status.tmp'
            temp.write_text(json.dumps(state, indent=2))
            temp.replace(log/'status.json')

        try:
            # Recheck identity/state and image immediately before any write.
            snapshot(nvme, args.expected_serial, args.action)
            validate_payload(args.firmware, args.profile)
            validate_power()
            subprocess.run(['sync'], check=True)
            if args.action == 'stage':
                execute_stage(nvme, args.firmware, record)
            else:
                execute_activation(nvme, record)
            subprocess.run(['sync'], check=True)
        except Exception:
            record('error_stop_and_inspect_no_automatic_retry')
            raise
        print(json.dumps(state, indent=2))
        print('LOCAL logs:', log, '(private; do not upload without redaction)')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (SafetyError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print('STOP:', exc, file=sys.stderr)
        raise SystemExit(1)

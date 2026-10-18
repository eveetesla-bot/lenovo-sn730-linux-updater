import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sn730_update as u


def slots(afi=1, second=''):
    return {'Active Firmware Slot (afi)': afi,
            'Firmware Rev Slot 1': u.OLD, 'Firmware Rev Slot 2': second}


class SafetyTests(unittest.TestCase):
    def test_integer_rejects_ambiguous_types(self):
        for value in (None, True, [], 'unknown'):
            with self.subTest(value=value), self.assertRaises(u.SafetyError):
                u.as_int(value)

    def test_slot_encoding(self):
        self.assertEqual(u.slot_revision({'Firmware Rev Slot 1': '123 (11110101)'}, 1), u.OLD)
        self.assertEqual(u.slot_revision({}, 2), '')
        with self.assertRaises(u.SafetyError):
            u.normalize_slots({})

    def test_phase_states(self):
        for action, state in [('check', slots()), ('stage', slots()),
                              ('activate', slots(1, u.NEW)), ('verify', slots(2, u.NEW))]:
            u.validate_slots(state, action)

    def test_refuses_occupied_slot_and_pending_activation(self):
        for state, action in [(slots(1, u.NEW), 'stage'), (slots(33, u.NEW), 'activate'),
                              (slots(1, u.NEW), 'verify'), (slots(2, u.NEW), 'stage')]:
            with self.subTest(action=action), self.assertRaises(u.SafetyError):
                u.validate_slots(state, action)

    def test_health(self):
        u.validate_health({'critical_warning': 0, 'media_errors': 0})
        for field in ('critical_warning', 'media_errors'):
            data = {'critical_warning': 0, 'media_errors': 0, field: 1}
            with self.assertRaises(u.SafetyError):
                u.validate_health(data)

    def test_all_consents_required(self):
        fields = ['acknowledge_backup', 'acknowledge_stable_power', 'acknowledge_experimental_method']
        for missing in fields:
            with self.assertRaises(u.SafetyError):
                u.validate_consent(SimpleNamespace(**{k: k != missing for k in fields}))

    def test_stage_order_and_preserved_slot(self):
        nvme = Mock()
        nvme.slots.return_value = slots(1, u.NEW)
        u.execute_stage(nvme, Path('synthetic.fluf'), Mock())
        self.assertEqual([c.args[0] for c in nvme.call.call_args_list], ['fw-download', 'fw-commit'])
        self.assertEqual(nvme.call.call_args_list[-1].args, ('fw-commit', '--slot=2', '--action=0'))

    def test_download_failure_never_commits(self):
        nvme = Mock()
        nvme.call.side_effect = u.SafetyError('simulated refusal')
        with self.assertRaises(u.SafetyError):
            u.execute_stage(nvme, Path('synthetic.fluf'), Mock())
        self.assertEqual(nvme.call.call_count, 1)

    def test_activation_only_schedules(self):
        nvme = Mock()
        nvme.slots.return_value = slots(33, u.NEW)
        u.execute_activation(nvme, Mock())
        nvme.call.assert_called_once_with('fw-commit', '--slot=2', '--action=2')

    def test_missing_payload_refused(self):
        with self.assertRaises(u.SafetyError):
            u.validate_payload(Path('not-present.fluf'), Path('not-present.pro'))


if __name__ == '__main__':
    unittest.main()

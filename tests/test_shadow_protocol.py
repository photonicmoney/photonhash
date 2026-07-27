import copy
import unittest

from tools.ph_shadow_protocol import (
    PROTOCOL, ProtocolError, parse_json, validate, work_id,
)


class ShadowProtocolTests(unittest.TestCase):
    def work(self):
        message = {
            "protocol": PROTOCOL,
            "type": "work",
            "network": "laser-public-shadow",
            "work_id": "",
            "parent_hash": "11" * 32,
            "height_hint": 42,
            "header_hex": "a0b1c2",
            "shadow_target_le": "ff" * 32,
            "issued_at_ms": 1785123456789,
        }
        message["work_id"] = work_id(message)
        return message

    def test_work_is_canonical(self):
        message = self.work()
        self.assertEqual(validate(message), message)
        self.assertEqual(
            message["work_id"],
            "f717ba59a47bbde3c569c411fbab8788"
            "85fc04d9167ea9c10aaa129441b70202",
        )

    def test_mutation_breaks_work_id(self):
        message = self.work()
        message["height_hint"] += 1
        with self.assertRaisesRegex(ProtocolError, "work_id"):
            validate(message)

    def test_extra_fields_rejected(self):
        message = self.work()
        message["consensus_override"] = True
        with self.assertRaisesRegex(ProtocolError, "canonical"):
            validate(message)

    def test_solution_boundaries(self):
        work = self.work()
        solution = {
            "protocol": PROTOCOL,
            "type": "solution",
            "work_id": work["work_id"],
            "nonce": (1 << 64) - 1,
            "digest": "00" * 32,
            "miner_id": "test-miner",
            "received_at_ms": 1785123456790,
        }
        self.assertEqual(validate(solution), solution)
        bad = copy.deepcopy(solution)
        bad["nonce"] += 1
        with self.assertRaises(ProtocolError):
            validate(bad)

    def test_uppercase_and_oversize_headers_rejected(self):
        message = self.work()
        message["parent_hash"] = "AA" * 32
        with self.assertRaises(ProtocolError):
            work_id(message)
        message = self.work()
        message["header_hex"] = "00" * 4097
        with self.assertRaisesRegex(ProtocolError, "4096"):
            work_id(message)

    def test_duplicate_and_oversize_messages_rejected(self):
        with self.assertRaisesRegex(ProtocolError, "duplicate"):
            parse_json('{"protocol":"a","protocol":"b"}')
        with self.assertRaisesRegex(ProtocolError, "16384"):
            parse_json(" " * 16385)

    def test_miner_identifier_is_bounded_ascii(self):
        work = self.work()
        solution = {
            "protocol": PROTOCOL,
            "type": "solution",
            "work_id": work["work_id"],
            "nonce": 0,
            "digest": "00" * 32,
            "miner_id": "x" * 129,
            "received_at_ms": 1,
        }
        with self.assertRaisesRegex(ProtocolError, "128"):
            validate(solution)


if __name__ == "__main__":
    unittest.main()

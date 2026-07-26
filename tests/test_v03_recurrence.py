import hashlib
import importlib.util
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ph_v03_recurrence_analysis",
    ROOT / "tools" / "ph_v03_recurrence_analysis.py",
)
RECURRENCE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RECURRENCE)


class RecurrenceVectorTests(unittest.TestCase):
    def test_two_round_fused_cuda_vector(self):
        n = 1024
        label = b"PhotonHash/v0.3/R1-fused/n=1024"
        parent = hashlib.shake_256(label).digest(32)
        matrix, _ = RECURRENCE.derive_matrix(parent, n)
        indices = np.arange(n, dtype=np.uint32)
        values = indices * np.uint32(0x9E3779B9) + np.uint32(0x243F6A88)
        values ^= values >> np.uint32(16)
        state = (((values >> np.uint32(28)) & np.uint32(15))
                 .astype(np.int8) - 8).reshape(n, 1)
        shift, offset = RECURRENCE.quantization_parameters(n)
        matrix32 = matrix.astype(np.int32)
        for _ in range(2):
            state, _ = RECURRENCE.transition(
                matrix32, state, shift, offset
            )
        digest = hashlib.shake_256(
            state[:, 0].tobytes(order="C")
        ).hexdigest(32)
        self.assertEqual(
            digest,
            "b32177c65a4cc26a9753316285ddb1e8"
            "c8fca5b484789d9a4320c2a639e600a4",
        )

    def test_known_v02_matrix_checksum(self):
        _, packed = RECURRENCE.derive_matrix(
            RECURRENCE.KNOWN_PARENT, 1024
        )
        checksum = hashlib.shake_256(packed).hexdigest(32)
        self.assertEqual(checksum, RECURRENCE.KNOWN_CHECKSUM)


if __name__ == "__main__":
    unittest.main()

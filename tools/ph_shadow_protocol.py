#!/usr/bin/env python3
"""Canonical non-consensus PhotonHash shadownet message validation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PROTOCOL = "photonhash-shadow/1"
WORK_TAG = b"LASER/PhotonHash/shadownet/work"
MAX_HEADER_BYTES = 4096
MAX_MESSAGE_BYTES = 16384


class ProtocolError(ValueError):
    pass


def _hex(value: Any, length: int, name: str) -> bytes:
    if not isinstance(value, str) or len(value) != length * 2:
        raise ProtocolError(f"{name} must be {length}-byte lowercase hex")
    if value.lower() != value:
        raise ProtocolError(f"{name} must use lowercase hex")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as error:
        raise ProtocolError(f"{name} is not hex") from error
    return decoded


def _uint(value: Any, bits: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProtocolError(f"{name} must be an integer")
    if value < 0 or value >= 1 << bits:
        raise ProtocolError(f"{name} is outside uint{bits}")
    return value


def work_id(message: dict[str, Any]) -> str:
    network = message.get("network")
    if not isinstance(network, str) or not network or len(network) > 64:
        raise ProtocolError("network must be 1..64 characters")
    try:
        network_bytes = network.encode("ascii")
    except UnicodeEncodeError as error:
        raise ProtocolError("network must be ASCII") from error
    parent = _hex(message.get("parent_hash"), 32, "parent_hash")
    target = _hex(message.get("shadow_target_le"), 32, "shadow_target_le")
    height = _uint(message.get("height_hint"), 64, "height_hint")
    header = _hex_bytes(message.get("header_hex"), "header_hex")
    if len(header) > MAX_HEADER_BYTES:
        raise ProtocolError("header exceeds 4096 bytes")
    body = (
        WORK_TAG
        + len(network_bytes).to_bytes(4, "little")
        + network_bytes
        + parent
        + height.to_bytes(8, "little")
        + len(header).to_bytes(4, "little")
        + header
        + target
    )
    return hashlib.shake_256(body).digest(32).hex()


def _hex_bytes(value: Any, name: str) -> bytes:
    if not isinstance(value, str) or len(value) % 2 or value.lower() != value:
        raise ProtocolError(f"{name} must be lowercase even-length hex")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ProtocolError(f"{name} is not hex") from error


def validate(message: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise ProtocolError("message must be an object")
    if message.get("protocol") != PROTOCOL:
        raise ProtocolError(f"protocol must be {PROTOCOL}")
    kind = message.get("type")
    if kind == "work":
        required = {
            "protocol", "type", "network", "work_id", "parent_hash",
            "height_hint", "header_hex", "shadow_target_le", "issued_at_ms",
        }
        if set(message) != required:
            raise ProtocolError("work message fields are not canonical")
        _uint(message["issued_at_ms"], 64, "issued_at_ms")
        expected = work_id(message)
        if message["work_id"] != expected:
            raise ProtocolError("work_id does not match canonical work")
    elif kind == "solution":
        required = {
            "protocol", "type", "work_id", "nonce", "digest", "miner_id",
            "received_at_ms",
        }
        if set(message) != required:
            raise ProtocolError("solution message fields are not canonical")
        _hex(message["work_id"], 32, "work_id")
        _uint(message["nonce"], 64, "nonce")
        _hex(message["digest"], 32, "digest")
        _uint(message["received_at_ms"], 64, "received_at_ms")
        miner_id = message["miner_id"]
        if (not isinstance(miner_id, str) or not miner_id
                or len(miner_id) > 128 or not miner_id.isascii()
                or not miner_id.isprintable()):
            raise ProtocolError(
                "miner_id must be 1..128 printable ASCII characters")
    else:
        raise ProtocolError("type must be work or solution")
    return message


def parse_json(text: str) -> dict[str, Any]:
    if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message exceeds 16384 bytes")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProtocolError(f"duplicate field {key}")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=unique_object)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"invalid JSON: {error.msg}") from error
    return validate(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", type=Path)
    args = parser.parse_args()
    try:
        parse_json(args.message.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ProtocolError) as error:
        print(f"INVALID: {error}")
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

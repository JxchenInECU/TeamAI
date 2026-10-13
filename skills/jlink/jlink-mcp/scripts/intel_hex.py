#!/usr/bin/env python3
"""Inspect Intel HEX records and compare their data bytes with one or more readbacks."""

import argparse
import hashlib
import json
from pathlib import Path


def parse_hex(path: Path) -> tuple[dict[int, int], int | None]:
    data: dict[int, int] = {}
    base = 0
    entry = None
    eof = False
    for line_no, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if eof:
            raise ValueError(f"line {line_no}: record after EOF")
        if not line.startswith(":"):
            raise ValueError(f"line {line_no}: missing ':'")
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as exc:
            raise ValueError(f"line {line_no}: invalid hex") from exc
        if len(record) < 5 or len(record) != record[0] + 5:
            raise ValueError(f"line {line_no}: invalid record length")
        if sum(record) & 0xFF:
            raise ValueError(f"line {line_no}: checksum mismatch")
        count = record[0]
        offset = int.from_bytes(record[1:3], "big")
        kind = record[3]
        payload = record[4:-1]
        if kind == 0:
            if base + offset + count > 0x100000000:
                raise ValueError(f"line {line_no}: address exceeds 32 bits")
            for index, value in enumerate(payload):
                address = base + offset + index
                if address in data and data[address] != value:
                    raise ValueError(f"line {line_no}: conflicting byte at 0x{address:08X}")
                data[address] = value
        elif kind == 1:
            if count or offset:
                raise ValueError(f"line {line_no}: invalid EOF record")
            eof = True
        elif kind in (2, 4):
            if count != 2 or offset:
                raise ValueError(f"line {line_no}: invalid address extension")
            shift = 4 if kind == 2 else 16
            base = int.from_bytes(payload, "big") << shift
        elif kind == 3:
            if count != 4 or offset:
                raise ValueError(f"line {line_no}: invalid start segment record")
            entry = (int.from_bytes(payload[:2], "big") << 4) + int.from_bytes(payload[2:], "big")
        elif kind == 5:
            if count != 4 or offset:
                raise ValueError(f"line {line_no}: invalid start linear record")
            entry = int.from_bytes(payload, "big")
        else:
            raise ValueError(f"line {line_no}: unsupported record type {kind}")
    if not eof:
        raise ValueError("missing EOF record")
    if not data:
        raise ValueError("no data records")
    return data, entry


def ranges(addresses: list[int]) -> list[tuple[int, int]]:
    result = []
    start = last = addresses[0]
    for address in addresses[1:]:
        if address != last + 1:
            result.append((start, last + 1))
            start = address
        last = address
    result.append((start, last + 1))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "verify"))
    parser.add_argument("hex_file", type=Path)
    parser.add_argument(
        "--segment", nargs=2, action="append", metavar=("BASE", "READBACK"),
        help="A readback binary and its target base address; repeat for disjoint ranges",
    )
    args = parser.parse_args()
    try:
        image, entry = parse_hex(args.hex_file)
        addresses = sorted(image)
        spans = ranges(addresses)
        summary = {
            "file": str(args.hex_file.resolve()),
            "sha256": hashlib.sha256(args.hex_file.read_bytes()).hexdigest(),
            "data_bytes": len(image),
            "start": f"0x{addresses[0]:08X}",
            "end_exclusive": f"0x{addresses[-1] + 1:08X}",
            "entry_point": None if entry is None else f"0x{entry:08X}",
            "range_count": len(spans),
            "ranges": [[f"0x{a:08X}", f"0x{b:08X}"] for a, b in spans[:64]],
            "ranges_truncated": len(spans) > 64,
        }
        if args.mode == "verify":
            if not args.segment:
                parser.error("verify requires at least one --segment BASE READBACK")
            segments = []
            for base_text, path_text in args.segment:
                base = int(base_text, 0)
                blob = Path(path_text).read_bytes()
                if not blob or base < 0 or base + len(blob) > 0x100000000:
                    raise ValueError(f"invalid readback segment: {base_text} {path_text}")
                segments.append((base, blob))
            mismatches = []
            uncovered = []
            for address in addresses:
                observed = [blob[address - base] for base, blob in segments if base <= address < base + len(blob)]
                if not observed:
                    uncovered.append(address)
                elif any(value != image[address] for value in observed):
                    mismatches.append((address, image[address], observed))
            summary["verified_bytes"] = len(addresses) - len(uncovered) - len(mismatches)
            summary["mismatch_count"] = len(mismatches)
            summary["uncovered_count"] = len(uncovered)
            summary["mismatches"] = [
                {"address": f"0x{a:08X}", "expected": f"0x{want:02X}",
                 "actual": [f"0x{x:02X}" for x in got]}
                for a, want, got in mismatches[:16]
            ]
            summary["uncovered"] = [f"0x{a:08X}" for a in uncovered[:16]]
            summary["ok"] = not mismatches and not uncovered
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary.get("ok", True) else 1
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

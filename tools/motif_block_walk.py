#!/usr/bin/env python3
"""Walk W*H candidate words in blocks of W and locate the six-field motif in each block.

Builds on #951 (candidate grammar, motif), #1031 and #1035 (fixed-pitch motif
lattice). Standard library only (Python 3.8+). Prints numbers only: no paths,
no image data.

Payload: the declared strip sequence read by strip_start_audit.independent_strips
(separated strips joined in table order without gap bytes; tied, overlapping or
mismatched strip tables, other unsupported containers and files over 128 MiB
give status=unknown with a reason, and the run continues).

Candidate grammar (#951, not established): a literal marker of leading zero
bits and a 1, then words from start_bit, the bit after that 1. A word is q < 12
zeros, a 1 and 5 suffix bits; 12 zeros start an escape of 24 bits. Word ends are
bounded by the payload end (capped_prefix_counts.word_end).

Block b is words b*W .. b*W+W-1 counted from start_bit, for b = 0 .. H-1. A
block is a fixed count of candidate words, not a physical row. Per block the
tool records its length in bits and its motif column: the first word start c
(0 <= c < min(--max-col, W)) in the block at which the 48 bits match the six
8-bit fields (?:100[01]{5}){6} of #950/#1031. Only word starts are checked and
only the first match in a block is recorded. "none" = no match at those word
starts; "outside" = fewer than 48 payload bits remain at a word start reached
before any match.

Reference length: 6W+12 bits, extending the fixed 31332-bit pitch of #1031 (at
W = 5220) to any W. It is a comparison value, not a measured length. Blocks 0
and 1 are reported apart. body_blocks counts the complete blocks from block 2;
the histograms, runs and first_block_off_reference cover those blocks only
(fewer than H - 2 when status is incomplete). first_block_off_reference is null
when every one of them is 6W+12 bits long, and also when body_blocks is 0.

Status: ok (all W*H words complete), no_marker (empty or all-zero payload),
incomplete (a word did not fit before W*H words; complete blocks reported),
unknown (container not supported, with the reason).

--per-block adds, after each file's summary line, one JSON list per complete
block: [block, start bit, bits, motif column, motif bit or null]. Bit positions
count from the first payload bit.

Usage:
    python -I -B tools/motif_block_walk.py [--max-col N] [--min-run N] [--per-block]
        FILE [FILE ...]
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capped_prefix_counts import word_end  # noqa: E402
from motif_interior_probe import MOTIF, OCTETS  # noqa: E402
from strip_start_audit import independent_strips  # noqa: E402

MAX_BYTES = 128 * 1024 * 1024


def motif_column(bits, pos, max_col):
    """(first word column of the motif from pos, its bit position), or
    ("none", None) / ("outside", None). max_col never exceeds the block width."""
    for c in range(max_col):
        if pos + 48 > len(bits):
            return "outside", None
        if MOTIF.match(bits, pos):
            return c, pos
        pos = word_end(bits, pos)
        if pos is None:
            return "outside", None
    return "none", None


def runs(columns, first, min_run):
    """Maximal runs [first block, last block, column] of length >= min_run, and
    the number of blocks in shorter runs."""
    out, short, i = [], 0, 0
    while i < len(columns):
        j = i
        while j + 1 < len(columns) and columns[j + 1] == columns[i]:
            j += 1
        if j - i + 1 >= min_run:
            out.append([first + i, first + j, columns[i]])
        else:
            short += j - i + 1
        i = j + 1
    return out, short


def hist(values):
    h = {}
    for v in values:
        h[str(v)] = h.get(str(v), 0) + 1
    return h


def walk(payload, width, height, max_col=24, min_run=50, blocks=None):
    """Summary dict; with a list for blocks, also append one record per
    complete block: [block, start bit, bits, motif column, motif bit]."""
    out = {"W": width, "H": height, "max_col": max_col, "min_run": min_run}
    bits = "".join(OCTETS[b] for b in payload)
    first = bits.find("1")
    if first < 0:
        out.update(status="no_marker", payload_bits=len(bits))
        return out
    pos = first + 1
    ref = 6 * width + 12
    out.update(start_bit=pos, payload_bits=len(bits), reference_bits=ref)
    lengths, columns = [], []
    for b in range(height):
        start = pos
        col, at = motif_column(bits, start, min(max_col, width))
        for _ in range(width):
            pos = word_end(bits, pos)
            if pos is None:
                break
        if pos is None:
            out.update(status="incomplete", blocks_complete=b)
            break
        lengths.append(pos - start)
        columns.append(col)
        if blocks is not None:
            blocks.append([b, start, pos - start, col, at])
    else:
        out.update(status="ok", blocks_complete=height, tail_bits=len(bits) - pos,
                   tail_ones=bits.count("1", pos))
    out["block01_bits"] = lengths[:2]
    out["block01_motif_columns"] = columns[:2]
    body_len, body_col = lengths[2:], columns[2:]
    off = [i for i, n in enumerate(body_len) if n != ref]
    out["body_blocks"] = len(body_len)
    out["blocks_at_reference"] = len(body_len) - len(off)
    out["first_block_off_reference"] = off[0] + 2 if off else None
    out["excess_bits_hist"] = hist(n - ref for n in body_len)
    out["motif_column_hist"] = hist(body_col)
    out["column_runs"], out["short_run_blocks"] = runs(body_col, 2, min_run)
    return out


def measure(data, max_col=24, min_run=50, blocks=None):
    digest = hashlib.sha256(data).hexdigest()
    try:
        geometry, payload = independent_strips(data)
    except (ValueError, TypeError, IndexError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        return {"sha256": digest, "status": "unknown", "reason": reason}
    r = walk(payload, geometry["width"], geometry["height"], max_col, min_run, blocks)
    r["sha256"] = digest
    r["strips"] = geometry["strip_count"]
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--max-col", type=int, default=24,
                    help="motif searched at word columns 0..N-1 of each block (default 24)")
    ap.add_argument("--min-run", type=int, default=50,
                    help="print column runs of at least N blocks (default 50)")
    ap.add_argument("--per-block", action="store_true",
                    help="after each summary, one JSON list per complete block: "
                         "[block, start bit, bits, motif column, motif bit or null]")
    a = ap.parse_args(argv)
    if a.max_col < 1 or a.min_run < 1:
        ap.error("--max-col and --min-run must be at least 1")
    failed = False
    for n, path in enumerate(a.files, 1):
        blocks = [] if a.per_block else None
        try:
            with open(path, "rb") as f:
                data = f.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                r = {"input": n, "status": "unknown", "reason": "file_over_128_MiB"}
            else:
                r = measure(data, a.max_col, a.min_run, blocks)
        except OSError as exc:
            r = {"input": n, "status": "unknown", "reason": type(exc).__name__}
        failed |= r["status"] == "unknown"
        print(json.dumps(r, sort_keys=True), flush=True)
        for rec in blocks or ():
            print(json.dumps(rec), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

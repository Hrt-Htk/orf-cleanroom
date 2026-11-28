#!/usr/bin/env python3
"""Generated payloads and containers for motif_block_walk."""
import io
import os
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motif_block_walk as mbw  # noqa: E402


def word(q=0, suffix=31):
    return "0" * q + "1" + format(suffix, "05b")


def escape(raw=0):
    return "0" * 12 + format(raw, "012b")


# Six words whose 46 bits plus the first 2 bits of any following "1xxxxx" word
# form six fields 100xxxxx: one q=0 word, then five q=2 words, suffixes 0.
MOTIF_WORDS = [word(0, 0)] + [word(2, 0)] * 5


def block(width, col=None, extra=None):
    """width words: col filler words, the motif (6 words), filler, and a final
    q=2 word so that a motif block is 6W+12 bits. extra replaces filler word 1
    after the motif. col=None gives a block without the motif."""
    words = []
    if col is not None:
        words = [word()] * col + MOTIF_WORDS
    rest = width - len(words) - 1
    filler = [word()] * rest
    if extra is not None:
        filler[1] = extra
    return "".join(words + filler + [word(2)])


def payload(bits):
    bits += "0" * (-len(bits) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def stream(blocks, tail="11111111"):
    return payload("0001" + "".join(blocks) + tail)


def u32(v):
    return struct.pack("<I", v)


def ifd(entries):
    out = struct.pack("<H", len(entries))
    for tag, typ, count, field in sorted(entries):
        out += struct.pack("<HHI", tag, typ, count) + field
    return out + u32(0)


def container(strips, width, height, gap=b"\xff"):
    n = 4
    data_at = 8 + 2 + 12 * n + 4
    offsets_at, counts_at = data_at, data_at + 4 * len(strips)
    pos = counts_at + 4 * len(strips)
    offsets, body = [], b""
    for i, s in enumerate(strips):
        if i:
            body += gap
        offsets.append(pos + len(body))
        body += s
    one = len(strips) == 1
    entries = [(0x100, 4, 1, u32(width)), (0x101, 4, 1, u32(height)),
               (0x111, 4, len(strips), u32(offsets[0] if one else offsets_at)),
               (0x117, 4, len(strips), u32(len(strips[0]) if one else counts_at))]
    arrays = b"".join(u32(o) for o in offsets) + b"".join(u32(len(s)) for s in strips)
    return b"II*\x00" + u32(8) + ifd(entries) + arrays + body


W = 20


class WalkTests(unittest.TestCase):
    def test_reference_length_and_word_column(self):
        r = mbw.walk(stream([block(W, 2)] * 6), W, 6)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["reference_bits"], 6 * W + 12)
        self.assertEqual(r["block01_bits"], [6 * W + 12] * 2)
        self.assertEqual(r["blocks_at_reference"], 4)
        self.assertEqual(r["first_block_off_reference"], "none")
        self.assertEqual(r["motif_column_hist"], {"2": 4})

    def test_column_is_a_word_index_not_a_bit_offset(self):
        # One q=6 word (12 bits) before the motif: bit offset 12, word column 1.
        b = word(6) + "".join(MOTIF_WORDS) + "".join([word()] * (W - 8)) + word(2)
        r = mbw.walk(stream([b] * 3), W, 3)
        self.assertEqual(r["motif_column_hist"], {"1": 1})

    def test_excess_and_first_block_off_reference(self):
        blocks = [block(W, 2)] * 4 + [block(W, 2, extra=word(3))] + [block(W, 2)]
        r = mbw.walk(stream(blocks), W, 6)
        self.assertEqual(r["excess_bits_hist"], {"0": 3, "3": 1})
        self.assertEqual(r["first_block_off_reference"], 4)

    def test_escape_adds_18_bits(self):
        blocks = [block(W, 2)] * 3 + [block(W, 2, extra=escape(4095))]
        r = mbw.walk(stream(blocks), W, 4)
        self.assertEqual(r["excess_bits_hist"], {"0": 1, "18": 1})

    def test_band_of_shifted_columns_and_min_run_edge(self):
        blocks = [block(W, 0)] * 2 + [block(W, 2)] * 3 + [block(W, 4)] * 2
        r = mbw.walk(stream(blocks), W, 7, min_run=3)
        self.assertEqual(r["column_runs"], [[2, 4, 2]])   # run of exactly min_run kept
        self.assertEqual(r["short_run_blocks"], 2)          # run of min_run - 1 not kept
        self.assertEqual(r["block01_motif_columns"], [0, 0])

    def test_none_outside_and_max_col_edge(self):
        r = mbw.walk(stream([block(W, 3)] * 2 + [block(W, 3), block(W)], tail=""), W, 4,
                     max_col=4)
        self.assertEqual(r["motif_column_hist"], {"3": 1, "none": 1})
        r = mbw.walk(stream([block(W, 4)] * 3), W, 3, max_col=4)
        self.assertEqual(r["motif_column_hist"], {"none": 1})
        short = mbw.walk(payload("1" + word() * 4), 4, 1)
        self.assertEqual(short["block01_motif_columns"], ["outside"])

    def test_tail_bits_and_ones(self):
        r = mbw.walk(stream([block(W, 2)] * 3, tail="1110"), W, 3)
        self.assertEqual((r["tail_ones"], r["tail_bits"]), (3, 4 + (-(4 + 3 * (6 * W + 12) + 4) % 8)))

    def test_truncated_last_word_is_incomplete(self):
        bits = "0001" + block(W, 2) * 2 + word()[:3]
        r = mbw.walk(payload(bits), W, 3)
        self.assertEqual((r["status"], r["blocks_complete"]), ("incomplete", 2))

    def test_empty_and_all_zero(self):
        self.assertEqual(mbw.walk(b"", W, 2)["status"], "no_marker")
        self.assertEqual(mbw.walk(b"\0" * 64, W, 2)["status"], "no_marker")


class ContainerTests(unittest.TestCase):
    def test_separated_strips_match_joined_payload(self):
        p = stream([block(W, 2)] * 4)
        joined = mbw.measure(container([p], W, 4))
        split = mbw.measure(container([p[:7], p[7:]], W, 4))
        self.assertEqual(split["strips"], 2)
        for key in ("status", "excess_bits_hist", "motif_column_hist", "tail_bits"):
            self.assertEqual(split[key], joined[key])

    def test_overlapping_strips_are_unknown(self):
        p = stream([block(W, 2)] * 4)
        data = bytearray(container([p[:7], p[7:]], W, 4))
        offsets_at = 8 + 2 + 12 * 4 + 4
        first = struct.unpack_from("<I", data, offsets_at)[0]
        struct.pack_into("<I", data, offsets_at + 4, first + 1)
        r = mbw.measure(bytes(data))
        self.assertEqual((r["status"], r["reason"]), ("unknown", "overlapping_strips"))

    def test_per_block_records(self):
        recs = []
        r = mbw.walk(stream([block(W, 2)] * 3), W, 3, blocks=recs)
        ref = 6 * W + 12
        self.assertEqual(r["status"], "ok")
        self.assertEqual(recs, [[i, 4 + i * ref, ref, 2, 4 + i * ref + 12] for i in range(3)])
        recs = []
        mbw.walk(stream([block(W, 2), block(W)], tail="1" * 200), W, 2, blocks=recs)
        self.assertEqual(recs[1][3:], ["none", None])

    def test_search_stays_inside_the_block(self):
        # max_col 24 > W = 20: a motif at column 0 of the next block is not this block's.
        r = mbw.walk(stream([block(W, 2)] * 2 + [block(W), block(W, 0)]), W, 4, max_col=24)
        self.assertEqual(r["motif_column_hist"], {"none": 1, "0": 1})

    def test_entry_point_per_block(self):
        with tempfile.TemporaryDirectory() as d:
            good = os.path.join(d, "a")
            with open(good, "wb") as f:
                f.write(container([stream([block(W, 2)] * 4)], W, 4))
            out = io.StringIO()
            with redirect_stdout(out):
                code = mbw.main(["--per-block", good])
        lines = out.getvalue().splitlines()
        self.assertEqual((code, len(lines)), (0, 5))
        self.assertTrue(lines[1].startswith("[0, 4, "))

    def test_entry_point_on_generated_files(self):
        with tempfile.TemporaryDirectory() as d:
            good, bad = os.path.join(d, "a"), os.path.join(d, "b")
            with open(good, "wb") as f:
                f.write(container([stream([block(W, 2)] * 4)], W, 4))
            with open(bad, "wb") as f:
                f.write(b"not a tiff")
            out = io.StringIO()
            with redirect_stdout(out):
                code = mbw.main([good, bad])
            lines = out.getvalue().splitlines()
        self.assertEqual(code, 1)
        self.assertIn('"status": "ok"', lines[0])
        self.assertIn('"status": "unknown"', lines[1])
        self.assertNotIn(d, out.getvalue())


if __name__ == "__main__":
    unittest.main()

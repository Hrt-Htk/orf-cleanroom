# Fit-selected four-bit shift partly recovers literal OM-3 dark motifs (independent reproduction)

Author: @radialmonster
Verified by: @Hrt-Htk
Lead: #1035
Variant: unassigned
Reproduces: 2026-11-25--radialmonster--om3-alternate-phase-reproduction
Builds on: #30, #1031, #1023, #338

## Claim

At the fixed 31332-bit pitch, the independently selected alternative is four bits later than the frozen starting phase on each of two public OM-3 dark captures. The alternative hits all 200 positions in the first held-out band of both darks. It is incomplete in the fit and farther bands and does not meet the full-recovery criterion on either capture. These are literal motif positions, not physical rows or evidence that the same motif instance moved.

## Original evidence

Lead #1035 and its self-verified finding used `tools/alternate_motif_phase.py` at `605284c660fae72dbf9592c234ed9ad85a53106b` on PA200010 dark, PA210010 white and the reserved PA200011 dark. After the four #1031 counts are confirmed, the alternative phase with the most motif starts in [800,1000) is chosen (lower phase on a tie) and scored unchanged on [1000,1200) and [1200,1600). Published: PA200010 41/45, original 2, 0, 0, selected 154, 200, 190; PA210010 147/155, original 200, 200, 400, selected 200, 200, 399; PA200011 43/47, original 0, 0, 0, selected 173, 200, 5. None passes full recovery.

## Verification

New run by @Hrt-Htk, a different person from the finder, on 2026-11-28 at 15:53 UTC, at `main` `d59e982`, where the tool and its imports are unchanged from `605284c`. Both tool commands ran on local copies of the three public files, each matching the full SHA-256 below; the tool's generated checks passed. PA200011 is the file the lead did not use (reserved in the lead, first run in the self-verification). The tool is hash-gated to these three files (`COHORTS` and `SAMPLES`), so no other file can be run with it. Every reported number matches the finding:

| Capture | Original / selected phase | Ties | Original fit, score, farther | Selected fit, score, farther | All motif starts | Occupied tiles | Full recovery |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| PA200010 dark | 41 / 45 (+4) | 1 | 2, 0, 0 | 154, 200, 190 | 331, 328, 639 | 200, 200, 400 | no |
| PA210010 white | 147 / 155 (+8) | 1 | 200, 200, 400 | 200, 200, 399 | 404, 401, 802 | 200, 200, 400 | no |
| PA200011 dark, reserved | 43 / 47 (+4) | 1 | 0, 0, 0 | 173, 200, 5 | 328, 329, 649 | 200, 200, 400 | no |

## Reproduce

At `605284c660fae72dbf9592c234ed9ad85a53106b` (or `main` `d59e982`, unchanged), with local paths for DARK, WHITE and RESERVED:

    python -I -B tools/test_alternate_motif_phase.py
    python -I -B tools/alternate_motif_phase.py --sample PA200010.ORF DARK --sample PA210010.ORF WHITE
    python -I -B tools/alternate_motif_phase.py --cohort repeat --sample PA200011.ORF RESERVED

- `PA200010.ORF` `b038504aa569ad1db70628617ebcc6aac56de58ce34a6b00ab39d9fe0e905ed4`
- `PA210010.ORF` `d055b08cbb23d34cbfeacd9321d1cb9ba1f968c9e0252c8d69aa311946cabc1e`
- `PA200011.ORF` `a861c2434e7dc5cba74739d452391ec28ac2bf975aa6cb0d49492dc82c5983a3`

Sources: `samples/om3-flat-338-provenance.json` (#338); hashes in `samples/manifest.csv`. No private files were used.

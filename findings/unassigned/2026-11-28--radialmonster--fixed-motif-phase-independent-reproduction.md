# Fixed OM-3 motif phase persists on white but ends early on two dark captures (independent reproduction)

Author: @radialmonster
Verified by: @Hrt-Htk
Lead: #1031
Variant: unassigned
Reproduces: 2026-11-25--radialmonster--fixed-motif-phase-reproduction
Builds on: #30, #1023, #1027, #338

## Claim

At the previously fixed 31332-bit pitch, the literal six-field motif is present at every nominal index 2–3911 on white PA210010, but none after index 801 on dark PA200010 at its own fixed phase. Reserved dark PA200011 also loses the motif at its fixed phase and has no matches after index 541. The measurements are bit-position predicates, not physical row identifications.

## Original evidence

Lead #1031 and its self-verified finding used `tools/fixed_motif_phase_continuity.py` at `97ed9f5bf8659c8eae1c745b9407e003200cb768` on the public CC0 OM-3 captures PA210010 (white, phase 147), PA200010 (dark, phase 41) and the reserved PA200011 (dark, phase 43). Each nominal start is bit `40 + phase + j * 31332` in the declared strip; six consecutive eight-bit fields `100xxxxx` are checked there. Published windows [0,400), [400,800), [800,1200), [1200,3912): white 398, 400, 400, 2712 (run 2–3911); PA200010 398, 400, 2, 0 (run 2–801); PA200011 242, 142, 0, 0 (run 158–541).

## Verification

New run by @Hrt-Htk, a different person from the finder, on 2026-11-28 at 15:53 UTC, at `main` `d59e982`, where the tool and its imports are unchanged from `97ed9f5`. Both tool commands ran on local copies of the three public files, each matching the full SHA-256 below; the tool's four generated checks passed. PA200011 is the file the lead did not use (reserved in the lead, first run in the self-verification). The tool is hash-gated to these three files (`COHORTS` and `SAMPLES`), so no other file can be run with it. Every reported number matches the finding:

| Capture | [0,400) | [400,800) | [800,1200) | [1200,3912) | Nominal matches | Present run | Absent ranges | Beyond nominal: complete / matched, EOF minus first expected start |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| PA210010 white | 398 | 400 | 400 | 2712 | 3910 | [2, 3912) | [0,2) | 0 / 0, −3 |
| PA200010 dark | 398 | 400 | 2 | 0 | 800 | [2, 802) | [0,2), [802,3912) | 1 / 0, +103 |
| PA200011 dark, reserved | 242 | 142 | 0 | 0 | 384 | [158, 542) | [0,158), [542,3912) | 1 / 0, +93 |

Declared strip bits: 122570968, 122570968 and 122570960.

## Reproduce

At `97ed9f5bf8659c8eae1c745b9407e003200cb768` (or `main` `d59e982`, unchanged), with local paths for WHITE, DARK and RESERVED:

    python -I -B tools/test_fixed_motif_phase_continuity.py
    python -I -B tools/fixed_motif_phase_continuity.py --sample PA210010.ORF WHITE --sample PA200010.ORF DARK
    python -I -B tools/fixed_motif_phase_continuity.py --cohort repeat --sample PA200011.ORF RESERVED

- `PA210010.ORF` `d055b08cbb23d34cbfeacd9321d1cb9ba1f968c9e0252c8d69aa311946cabc1e`
- `PA200010.ORF` `b038504aa569ad1db70628617ebcc6aac56de58ce34a6b00ab39d9fe0e905ed4`
- `PA200011.ORF` `a861c2434e7dc5cba74739d452391ec28ac2bf975aa6cb0d49492dc82c5983a3`

Sources: `samples/om3-flat-338-provenance.json` (#338); hashes in `samples/manifest.csv`. No private files were used.

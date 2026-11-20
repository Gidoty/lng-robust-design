# Feed register status (supersedes the lead list of 2026-11-19)

All seven anchors A2 to A8 (Fields A to G) now come from the primary source, Ebrunu and Akpoturi (2025), Int. J. Adv. Eng. Manag.
7(10), 104-111, Tables 4 to 10. See `lng_robust/data/sources/SOURCES.md`.

- A1 (Soku) and A9 (Sonibare and Akeredolu 2004) are dropped from the register.
- Field D (A5, 42.74 mol% N2) is excluded from the main envelope (decision D11 option b) and kept as a sensitivity case.
- Field E has a sensitivity row (A6S) with the secondary-copy C1 and C2: `lng_robust/data/feeds_sensitivity_fieldE.csv`.
- H2S is printed (0.00 or <0.01 for Fields A to C) but is not simulated.
- C6, C7, C7+, C8 and C9 are lumped as n-hexane (column C6). The treated-feed spec limits C5+ to 0.1 mol%, so the lump is
  largely removed by the specification split.

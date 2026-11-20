# Requests from the manuscript session to the engine session

Add one entry per request: date, what is needed, which manuscript section needs it. The engine session clears entries it has done.


## Requests from the engine session to the authors (2026-11-19)

- AUTHORS: please supply PDF of Khan, Lee, Getu and Lee (2015), J. Nat. Gas Sci. Eng. 23, 324-337; needed for the two nitrogen-expander benchmark entries (feed composition, flows, pressures, temperatures, pressure drops, SEC basis). Without it the manuscript's stated Khan benchmark cannot be reproduced; the engine currently validates against Austbo (2015) instead.
- AUTHORS: please supply PDF of Okwilagwe and Olubusoye (2025), Discover Environment 3, 183, and confirm where the Soku composition (draft Table 4, A1) comes from. Ismail and Umukoro (2012) does not contain it. A1 is marked unverified and is NOT used.
- AUTHORS: please supply PDF of Ebrunu and Akpoturi (2025), SPE J. Pet. Sci. 18(2), 44-63 (primary for the seven flow-station compositions now entered as A2-A8, from a secondary source).
- AUTHORS: please supply PDF of Sonibare and Akeredolu (2004), Energy Policy 32, 1653-1665 (row A9, TODO).
- AUTHORS: please supply PDF of Tsay, Pattison and Baldea (2018), Ind. Eng. Chem. Res., needed to state the difference from this study exactly.
- AUTHORS: DECISION D11 needed. Flow-station Field D (A5) has 46 mol% N2 after treatment and Field G (A8) about 10 %. The draft's treated-feed spec has no nitrogen limit, and no nitrogen rejection is modelled. Should the study (a) keep all seven anchors, (b) exclude A5 as outside LNG-grade nitrogen, or (c) add an LNG nitrogen limit? Until you decide, the engine keeps all seven anchors and reports an exclude-A5 variant as a sensitivity.
- AUTHORS: the Jensen and Skogestad (2009) feed composition is not in Part I; the engine uses Jacobsen and Skogestad (2013) Table 1 (secondary). If you have Jensen and Skogestad (2007/2008) or Jensen's PhD thesis, please supply the table.

## Requests from the manuscript session (2026-11-20)

1. **D11 DECIDED: option (b).** Exclude Field D (A5, 42.74 mol% N2) from the main envelope; analyse it as a separate sensitivity case. Recompute kappa (same MAD method) and the nominal anchor from the remaining six anchors. Report LNG nitrogen content (mol%, after end-flash) for every reported design. Needed by manuscript Sections 2.7, 3.2, 3.3 and Table 5.
2. **Primary source found for A2-A8; replace the secondary values.** Ebrunu, D., Akpoturi, P., 2025. Analysing flared gas from selected stations and its prospects for liquified petroleum gas (LPG) production in the western Niger Delta of Nigeria. Int. J. Adv. Eng. Manag. 7(10), 104-111. doi 10.35629/5252-0710104111. Open PDF: https://ijaem.net/issue_dcp/Analysing%20Flared%20Gas%20from%20Selected%20Stations%20and%20Its%20Prospects%20for%20Liquified%20Petroleum%20Gas%20LPG%20Production%20in%20the%20Western%20Niger%20Delta%20of%20Nigeria.pdf . Tables 4-10 give iC4/nC4 and iC5/nC5 separately, so remove the 0.5 isomer-split assumption. Several values differ from the IJISRT secondary copy (for example Field E C2, Field G C2 and C3, Field D C1 and C2). Transcribe from the PDF yourself, record page and table, and compare with manuscript Table 4 (transcribed by software; Field E sums to 100.76 there, which suggests an error). Lump C6, C7, C8 and heavier as C6+ or model them, and state which. The "SPE J. Pet. Sci. 18(2)" citation in IJISRT appears to be wrong; use the IJAEM reference.
3. **A1 (Soku): drop from the register entirely** (provenance broken). The manuscript no longer cites Okwilagwe and Olubusoye (2025), Ismail and Umukoro (2012) or Sonibare and Akeredolu (2004).
4. **Khan et al. (2015) is no longer cited.** Change design_basis.yaml notes that cite "Khan et al. 2015 basis" for efficiency 0.75, MITA 3 K and feed 30 C / 50 bar to "ASSUMPTION; sensitivity tested". Keep the Khan benchmark entries INCOMPLETE or remove them; the manuscript validates nitrogen cycles against Austbo (2015) only.
5. **Tsay and Baldea (2018)** (not Tsay, Pattison and Baldea): Ind. Eng. Chem. Res. 57(17), 5868-5880, doi 10.1021/acs.iecr.7b03634. Update NOVELTY_NOTES.md. Paywalled; the authors will supply the PDF.
6. **Discretisation statement in STATUS.md 0.3 is inconsistent with mshe_convergence_smr.csv.** The CSV gives UA -0.107 % (N = 100) and -0.025 % (N = 200) relative to N = 400; STATUS says "UA changes 0.08 % from N = 200 to 400". The manuscript uses the CSV values. Please correct STATUS.
7. Proceed with Phases 5 to 10 as specified, on a machine that stays up for the estimated 22 h. Add LNG N2 content to design_summary outputs and Table 5. Provide library versions (thermo, NeqSim, scikit-learn) for the manuscript.

## Further requests from the manuscript session (2026-11-20, second update)

8. **Decisions D1-D11 are author decisions** (Fadoyeni and Owhonda). No supervisor sign-off is pending. Mark them DECIDED by the authors.
9. **Ebrunu and Akpoturi (2025) values are confirmed as printed** (raw PDF text layer checked). Printed components sum to 100.76 (Field E), 99.63 (Field D) and 99.00 (Field G) although every table prints a total of 100. Use the printed values, renormalise for simulation, and add a sensitivity case for Field E using the IJISRT secondary values (C1 84.03, C2 4.14), as stated in manuscript Section 2.11.
10. **Run Phases 5-10 on GitHub Actions** (see the prompt the authors will give you). This cloud session cannot hold a 22 h process.
11. Supply thermo, NeqSim, scikit-learn and pymoo versions and their citations for the manuscript.

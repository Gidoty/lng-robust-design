# Source log (documents opened by the engine session, 2026-11-19 and 2026-11-20)

Every value entered in `benchmarks.yaml`, `feeds.csv` and `sources/*.csv` comes from a document listed here as OPENED.
PDFs are not committed (copyright); the transcriptions are. Page numbers are printed page numbers, with PDF page in brackets.

## OPENED

| Document | Where | What was taken |
|---|---|---|
| Jensen and Skogestad (2009), Single-cycle mixed-fluid LNG process, Part I: Optimal design | skoge.folk.ntnu.no/publications/2009/jensen_lng-prico1_qatar/o10.pdf | Table 2 (p. 4) Case 1: feed 52.2 kg/s, LNG 44.6 kg/s, refrigerant 478 kg/s, Tout -144 C, superheat 10 C, dTmin 1.96 C, eta 82.8 %, Ws 77.5 MW, Ph 22 bar, Pl 4.0 bar, refrigerant composition. SRK stated (p. 2). Feed composition, feed T and P, cooler outlet T, flash pressure, pressure drops are NOT in Part I |
| Jensen and Skogestad (2009), Part II: Operation | skoge.folk.ntnu.no/publications/2009/jensen_lng-prico2_qatar/o11.pdf | Fig. 1 and p. 2: feed 30 C and 40 bar, 35 bar after the exchanger, refrigerant 30 C after the sea-water cooler. Stated for Case 8 of Part I, used for Case 1 by inference |
| Jacobsen and Skogestad (2013), active constraints, PRICO | skoge.folk.ntnu.no/publications/2013/jacobsen-active-constraints-lng/old-submitted/Constraints_LNG_revised.pdf | Table 1: feed composition (CH4 0.897, C2H6 0.055, C3H8 0.018, C4H10 0.001, N2 0.029), pressure drops (NG 5 bar, hot MR 4, cold MR 1, condenser 0.1, suction 0.3), condensation 30 C. Secondary for the Jensen benchmark |
| Perez (2009), NTNU MSc thesis on PRICO in HYSYS | skoge.folk.ntnu.no/diplom/diplom09/perez/perez_luber_lng_ms-thesis09.pdf | pp. 15-17: LNG expanded to atmospheric pressure, same pressure drops, composition 89.8/5.5/1.8/0.1/2.8 (differs slightly from Jacobsen), note that Jensen's composition does not sum to one. Secondary |
| Austbo (2015), PhD thesis NTNU, Use of Optimization in Evaluation and Design of Liquefaction Processes for Natural Gas | skoge.folk.ntnu.no/publications/thesis/more/Austboe_NTNU_2015/phd-thesis-austboe-revised.pdf | Table 5.1 (p. 111 [143]) feed; Table 5.4 (p. 124 [156]) single expander PR and SRK results; Table 5.9 (p. 142 [174]) dual expander; Fig. 5.16 (p. 137 [169]) flowsheet; Table 5.8 (kW units) |
| **Ebrunu and Akpoturi (2025), Int. J. Adv. Eng. Manag. 7(10), 104-111, doi 10.35629/5252-0710104111** (PRIMARY for feeds A2 to A8) | ijaem.net open PDF, opened 2026-11-20 | Tables 4 to 10 (PDF p. 5, printed p. 108): seven flow-station compositions with iC4, nC4, iC5, nC5, C6, C7, C7+, C8, C9 printed separately. Cross-checked against Table 12 (propane, iso-butane, n-butane) for every field. Printed components sum to 100.01, 100.01, 100.00, 99.63, 100.76, 99.98, 99.00 although each table prints 100 |
| Ucheckukwu, Oji, Peter, Banigo (2026), IJISRT 11(6), modular CNG plant, western Niger Delta | ijisrt.com/assets/upload/files/IJISRT26JUN1466.pdf | Table 1 "Gas Data" (PDF pp. 3175-3176): secondary copy of the same seven compositions. Used only for the Field E sensitivity (C1 84.03, C2 4.14). Its citation of Ebrunu and Akpoturi as "SPE J. Pet. Sci. 18(2)" is wrong; the IJAEM reference above is the one used |
| Ismail and Umukoro (2012), Global impact of gas flaring | www.scirp.org/journal/paperinformation?paperid=20231 (HTML full text) | Searched in full: no composition table and no mention of Soku. Not used; the manuscript no longer cites it |

## COULD NOT BE OPENED (requests are in manuscript/REQUESTS_TO_ENGINE.md)

| Document | Reason |
|---|---|
| Khan, Lee, Getu, Lee (2015), J. Nat. Gas Sci. Eng. 23, 324-337 | paywalled. No longer cited by the manuscript; the Khan benchmark entries stay INCOMPLETE and unused |
| Tsay, Pattison, Baldea (2018), Ind. Eng. Chem. Res. | paywalled (ACS host is not on the allowed network list) |
| Nguyen, Rothuizen, Markussen, Elmegaard (2018), Appl. Therm. Eng. 128, 712-724 | DTU Orbit and CORE return HTTP 403 to automated requests |
| Austbo and Gundersen (2015), Energy Procedia 64, 63-72 | publisher blocks automated access; the same content is in Austbo's thesis, which was opened |

## DROPPED FROM THE REGISTER (2026-11-20, manuscript request 3)

A1 (Soku; Okwilagwe and Olubusoye 2025 citing Ismail and Umukoro 2012) and A9 (Sonibare and Akeredolu 2004) are removed from `feeds.csv`. A1's provenance chain could not be confirmed; A9 was never entered. The manuscript no longer cites these three papers. Feed ids A2 to A8 are kept as stable labels (A2 = Field A ... A8 = Field G).

# Data quality report

| Check | Result | Detail |
|---|---|---|
| Unique facility IDs (hospital info) | PASS | 0 duplicate IDs |
| One row per hospital x measure | PASS | 0 duplicate rows |
| Known HRRP measures only | PASS | unexpected: none |
| Readmission rows join to a hospital | WARN | 222 rows without a match |
| ERR = predicted / expected (tol 0.002) | PASS | 0 of 11,720 rows off |
| ERR in plausible range 0.5-2.0 | WARN | 1 rows outside range |
| Suppressed readmission counts | PASS | 56.2% of rows suppressed ('Too Few to Report' / N/A); kept, excluded from O/E stats |
| Single reporting period | PASS | 07/01/2021 to 06/30/2024 |

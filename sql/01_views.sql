-- Analysis views used for Tableau extracts.
-- ERR (excess readmission ratio) = predicted / expected readmission rate; > 1 means
-- more readmissions than expected for a hospital's case mix.

DROP VIEW IF EXISTS v_readmission_detail;
CREATE VIEW v_readmission_detail AS
SELECT
    r.facility_id,
    h.facility_name,
    h.city,
    h.county,
    h.zip,
    r.state,
    h.hospital_type,
    h.hospital_ownership,
    h.hospital_overall_rating,
    r.measure_name,
    r.measure_label,
    r.number_of_discharges,
    r.number_of_readmissions,
    r.predicted_readmission_rate,
    r.expected_readmission_rate,
    r.excess_readmission_ratio,
    -- Expected readmission COUNT, used for observed/expected and funnel limits
    r.expected_readmission_rate / 100.0 * r.number_of_discharges AS expected_readmissions,
    CASE WHEN r.excess_readmission_ratio > 1 THEN 1 ELSE 0 END AS err_above_1,
    r.start_date,
    r.end_date
FROM readmission r
LEFT JOIN hospital h ON h.facility_id = r.facility_id;

DROP VIEW IF EXISTS v_wa_hospital_measures;
CREATE VIEW v_wa_hospital_measures AS
SELECT * FROM v_readmission_detail
WHERE state = 'WA';

DROP VIEW IF EXISTS v_state_measure_summary;
CREATE VIEW v_state_measure_summary AS
SELECT
    state,
    measure_name,
    measure_label,
    COUNT(excess_readmission_ratio)                       AS hospitals_reported,
    ROUND(AVG(excess_readmission_ratio), 4)               AS mean_err,
    ROUND(AVG(err_above_1 * 1.0), 4)                      AS share_err_above_1,
    SUM(number_of_discharges)                             AS total_discharges
FROM v_readmission_detail
WHERE excess_readmission_ratio IS NOT NULL
GROUP BY state, measure_name, measure_label;

-- Which WA hospitals are in HRRP at all? Critical Access Hospitals are excluded
-- from the program, which matters a lot in a state with many rural hospitals.
DROP VIEW IF EXISTS v_wa_hrrp_coverage;
CREATE VIEW v_wa_hrrp_coverage AS
SELECT
    h.facility_id,
    h.facility_name,
    h.city,
    h.county,
    h.zip,
    h.hospital_type,
    h.hospital_ownership,
    h.hospital_overall_rating,
    COUNT(r.excess_readmission_ratio) AS measures_with_err,
    CASE WHEN COUNT(r.measure_name) > 0 THEN 'In HRRP' ELSE 'Not in HRRP' END AS hrrp_status
FROM hospital h
LEFT JOIN readmission r ON r.facility_id = h.facility_id
WHERE h.state = 'WA'
GROUP BY h.facility_id;

-- Query 05: Data Warehouse Reconciliation Audit & DQ Distribution
-- Analyzes detected DQ events and quarantined record severity

SELECT
    RULE_NAME,
    SEVERITY,
    ACTION_TAKEN,
    COUNT(*) AS TOTAL_INCIDENTS,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM DQ_AUDIT_LOG), 2) AS PCT_OF_TOTAL_ISSUES
FROM DQ_AUDIT_LOG
GROUP BY RULE_NAME, SEVERITY, ACTION_TAKEN
ORDER BY TOTAL_INCIDENTS DESC;

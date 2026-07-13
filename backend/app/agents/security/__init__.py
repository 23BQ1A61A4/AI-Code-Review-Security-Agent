"""
Security agent subpackage — Module 3.

    scanner_base.py    - SecurityScanner interface every scanner implements
    static_rules.py     - our own regex-based rule engine (the only scanner
                          that actually runs today)
    external_tools.py   - placeholder scanners for Bandit/Semgrep/SpotBugs/
                          Checkstyle — implement the same interface so they
                          can be dropped into SecurityVulnerabilityAgent's
                          scanner list later with zero API changes
    merge.py            - deduplicates/merges findings from multiple scanners
"""

# Bundled checklist source

The checklist is a deliberately scoped, 27-control subset of the CIS/MS-ISAC NIST Cybersecurity Framework Policy Template Guide (2024). The guide maps NIST CSF 2.0 subcategories to policy documents. Each item in checklist.json keeps the NIST identifier, function, source page, and source URL so an auditor can inspect the reference.

Official source:
https://www.cisecurity.org/-/media/project/cisecurity/cisecurity/data/media/files/uploads/2024/08/cis-ms-isac-nist-cybersecurity-framework-policy-template-guide-2024.pdf

The ISMS, privacy, patch, and risk labels are product demo scopes, not official NIST categories. Severity is a planning weight selected for this prototype, not a rating supplied by NIST or CIS. This is not the complete set of NIST CSF 2.0 subcategories. The guide's printed page numbers are stored in guide_page.

Each control also has a short list of curated partial_signals. If the local model returns missing while one of these phrases appears in a retrieved passage, the rule raises the status to partial and attaches that passage as evidence. This fallback can never mark a control covered. Phrase hits still need human review: they indicate related wording, not proof that the complete requirement is satisfied.

"""Plain-English classification over lobbying subject_matter.

subject_matter is a semicolon-separated list of tags drawn from a real,
mostly-consistent controlled vocabulary (verified 2026-08-05: 713 distinct
tags once split, with a clean concentration at the top -- "Planning and
Development Application, Zoning By-law" alone appears on 2,396 of 14,504
registrations). Splitting on ";" is the only processing needed to get real
"top lobbied issues" -- no hand-curated taxonomy required, unlike the budget
program groupings.

LOBBYING_ISSUE_TO_POLICY_AREA maps only the subset of top tags that
correspond to an actual City *spending area* -- used for the "did this
issue see funding move" cross-reference. Deliberately excludes tags that
are process/regulatory rather than a spending area (Procurement, Signs,
By-law / Regulation, Technology, Licences / Licensing) -- lobbying about a
licensing *process* doesn't map to "how much the City spends on licensing,"
so forcing a mapping there would be misleading, not illuminating.
"""

LOBBYING_ISSUE_TO_POLICY_AREA = {
    "Planning and Development Application, Zoning By-law": "Planning and Development",
    "Planning and Development Application, Site Plan": "Planning and Development",
    "Planning and Development": "Planning and Development",
    "Planning and Development, Combined Application": "Planning and Development",
    "Planning and Development Application": "Planning and Development",
    "Planning and Development Application, Official Plan": "Planning and Development",
    "Planning and Development, Planning Policy / Study": "Planning and Development",
    "Planning and Development Application, Minor Variance": "Planning and Development",
    "Building Permits": "Planning and Development",
    "Economic Development": "Economic Development, Culture and Attractions",
    "Attractions / Tourism": "Economic Development, Culture and Attractions",
    "Environment": "Environment and Climate",
    "Energy": "Environment and Climate",
    "Transit / TTC": "Public Transit",
    "Transportation - Roads / Bridges": "Roads, Engineering and Fleet",
    "Transportation": "Roads, Engineering and Fleet",
    "Affordable Housing": "Housing and Homelessness Support",
    "Water": "Water and Waste",
}


def explode_subject_matter(raw: str) -> list[str]:
    return [t.strip() for t in (raw or "").split(";") if t.strip()]

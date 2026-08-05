"""Plain-English classification layer over the City's raw budget fields.

Three separate curated mappings, each with a different risk profile:

1. PROGRAM_ALIASES / normalize_program_name -- resolves cosmetic renames
   only (word order, pluralization, "Office of X" -> "X"). Verified by
   inspecting the real program name set across all 4 fiscal years (see
   docs/08-decision-log.md's 2026-08-05 entry). Departments that changed by
   more than a cosmetic edit (e.g. "Office of the Controller" -> "Financial
   Operations and Control", "311 Toronto" -> "Customer Experience") are
   deliberately NOT merged here -- this project doesn't assert an
   organizational-history claim it can't verify. Those show up as separate
   appeared/disappeared entries instead, letting a reader judge for
   themselves.

2. PROGRAM_POLICY_AREA -- editorial grouping of the ~60 real program names
   into ~18 plain-English policy areas, for the "where does the money go"
   view. This is a judgment call, same as the grant-program-cut or
   budget-movers decisions elsewhere in this app -- documented, not hidden.

3. CATEGORY_PLAIN_ENGLISH -- one-line plain-English gloss for each of the
   City's own 9 expenditure `category_name` values, which are stable and
   consistent across all 4 years (verified, unlike commitment_item).

4. classify_revenue_bucket -- keyword-rule bucketing for revenue
   commitment_item strings, because the City's own revenue category_name
   dumps almost everything (including the entire property tax levy) into
   one "Other Revenue" catch-all. Revenue commitment_item strings are also
   NOT stable across years (e.g. "Prov Grants/Subs" vs "Provincial Grants &
   Subsidies" -- same real category, different abbreviation per year's raw
   file), so exact-string grouping would undercount every bucket. Keyword
   matching on the lowercased string is more robust to that than an
   exact-match lookup table would be.
"""

import re

# --- 1. Cosmetic-only renames (see module docstring for the confidence bar) ---
PROGRAM_ALIASES = {
    "Toronto Police Services Board": "Toronto Police Service Board",
    "Integrity Commissioner's Office": "Office of the Integrity Commissioner",
    "Fire Services": "Toronto Fire Services",
    "Yonge-Dundas Square": "Sankofa Square",  # City's own 2024 public renaming, not an assumption
    "Parks, Forestry and Recreation": "Parks, Recreation and Forestry",
    "Policy, Planning, Finance and Administration": "Policy, Planning, Finance and Admin",
    "Office of Emergency Management": "Toronto Emergency Management",
}


def normalize_program_name(name: str) -> str:
    """Match key for a program name: collapses '&'/'and' and whitespace
    differences, then resolves the confirmed cosmetic aliases above. Two
    programs with the same normalized name are treated as the same
    department across years; anything not covered here is left distinct.
    """
    n = re.sub(r"\s+", " ", name.strip()).replace(" & ", " and ")
    return PROGRAM_ALIASES.get(n, n)


# --- 2. Policy area groupings ---
# Keyed by normalized program name (post normalize_program_name).
PROGRAM_POLICY_AREA = {
    "Toronto Police Service": "Policing",
    "Toronto Police Service Board": "Policing",

    "Toronto Transit Commission - Conventional": "Public Transit",
    "Toronto Transit Commission - Wheel Trans": "Public Transit",
    "Transit Expansion": "Public Transit",
    "Toronto Parking Authority": "Public Transit",

    "Children's Services": "Childcare and Family Support",

    "Housing Secretariat": "Housing and Homelessness Support",
    "Toronto Shelter and Support Services": "Housing and Homelessness Support",
    "Shelter, Support and Housing Administration": "Housing and Homelessness Support",

    "Toronto Public Health": "Public Health",

    "Seniors Services and Long-Term Care": "Seniors and Long-Term Care",

    "Social Development": "Social Services and Employment",
    "Social Development, Finance and Administration": "Social Services and Employment",
    "Toronto Employment and Social Services": "Social Services and Employment",

    "Toronto Fire Services": "Fire, Paramedic and Emergency Management",
    "Toronto Paramedic Services": "Fire, Paramedic and Emergency Management",
    "Toronto Emergency Management": "Fire, Paramedic and Emergency Management",

    "Parks, Recreation and Forestry": "Parks and Recreation",
    "Arena Boards of Management": "Parks and Recreation",
    "Association of Community Centres": "Parks and Recreation",

    "Toronto Public Library": "Libraries",

    "Transportation Services": "Roads, Engineering and Fleet",
    "Engineering and Construction Services": "Roads, Engineering and Fleet",
    "Fleet Services": "Roads, Engineering and Fleet",

    "Toronto Water": "Water and Waste",
    "Solid Waste Management Services": "Water and Waste",

    "City Planning": "Planning and Development",
    "Toronto Building": "Planning and Development",
    "Development Review": "Planning and Development",
    "CreateTO": "Planning and Development",

    "Economic Development and Culture": "Economic Development, Culture and Attractions",
    "Exhibition Place": "Economic Development, Culture and Attractions",
    "Heritage Toronto": "Economic Development, Culture and Attractions",
    "TO Live": "Economic Development, Culture and Attractions",
    "Sankofa Square": "Economic Development, Culture and Attractions",
    "Toronto Zoo": "Economic Development, Culture and Attractions",

    "Environment and Climate": "Environment and Climate",
    "Toronto Atmospheric Fund": "Environment and Climate",
    "Toronto and Region Conservation Authority": "Environment and Climate",

    "Capital and Corporate Financing": "Debt and Capital Financing",

    "Non-Program Expenditures": "Citywide and Corporate",
    "Non-Program Revenues": "Citywide and Corporate",
    "Non-Program Taxation Tax Levy": "Citywide and Corporate",

    # Everything else -- central administrative, legal, financial, regulatory,
    # and oversight functions -- grouped as one policy area rather than
    # split into many single-program areas too small to chart meaningfully.
    "Auditor General's Office": "City Governance and Corporate Services",
    "City Clerk's Office": "City Governance and Corporate Services",
    "City Council": "City Governance and Corporate Services",
    "City Manager Services": "City Governance and Corporate Services",
    "City Manager's Office": "City Governance and Corporate Services",
    "Corporate Real Estate Management": "City Governance and Corporate Services",
    "Court Services": "City Governance and Corporate Services",
    "Customer Experience": "City Governance and Corporate Services",
    "311 Toronto": "City Governance and Corporate Services",
    "Financial Operations and Control": "City Governance and Corporate Services",
    "Office of the Controller": "City Governance and Corporate Services",
    "Legal Services": "City Governance and Corporate Services",
    "Mayor's Office": "City Governance and Corporate Services",
    "Municipal Licensing and Standards": "City Governance and Corporate Services",
    "Office of the Chief Financial Officer and Treasurer": "City Governance and Corporate Services",
    "Office of the Chief Information Security Officer": "City Governance and Corporate Services",
    "Toronto Cyber Security": "City Governance and Corporate Services",
    "Office of the Integrity Commissioner": "City Governance and Corporate Services",
    "Office of the Lobbyist Registrar": "City Governance and Corporate Services",
    "Office of the Ombudsman": "City Governance and Corporate Services",
    "Policy, Planning, Finance and Admin": "City Governance and Corporate Services",
    "Technology Services": "City Governance and Corporate Services",
}

POLICY_AREA_ORDER = [
    "Policing",
    "Public Transit",
    "Childcare and Family Support",
    "Housing and Homelessness Support",
    "Public Health",
    "Seniors and Long-Term Care",
    "Social Services and Employment",
    "Fire, Paramedic and Emergency Management",
    "Parks and Recreation",
    "Libraries",
    "Roads, Engineering and Fleet",
    "Water and Waste",
    "Planning and Development",
    "Economic Development, Culture and Attractions",
    "Environment and Climate",
    "Debt and Capital Financing",
    "City Governance and Corporate Services",
    "Citywide and Corporate",
]


def policy_area_for_program(program_name: str) -> str:
    key = normalize_program_name(program_name)
    return PROGRAM_POLICY_AREA.get(key, "City Governance and Corporate Services")


# One hue per policy area, evenly spaced around the color wheel by list
# order -- not a hand-picked color per category. The CSS side (.policy-tag
# in base.html) fixes saturation/lightness so contrast stays roughly
# consistent regardless of which hue lands on a given area, in both themes.
POLICY_AREA_HUE = {area: round(i * 360 / len(POLICY_AREA_ORDER)) for i, area in enumerate(POLICY_AREA_ORDER)}


def policy_area_hue(area_name: str) -> int:
    return POLICY_AREA_HUE.get(area_name, 0)


# --- 3. Expenditure category_name -> plain English ---
# All 9 values are confirmed identical and stable across FY2022-2025.
CATEGORY_PLAIN_ENGLISH = {
    "Salaries": ("Salaries", "Base pay for City staff, before benefits."),
    "Benefits": ("Employee benefits", "Health, dental, and pension contributions on top of salary."),
    "Materials & Supplies": ("Materials and supplies", "Everything from office supplies to road salt to medical supplies."),
    "Service And Rent": ("Contracted services and rent", "Outside vendors, contractors, and facility rentals the City pays for."),
    "Equipment": ("Equipment", "Vehicles, machinery, computers, and other hardware."),
    "Inter-Divisional Charges": ("Inter-divisional charges", "Internal billing between City divisions (e.g. IT services billed to another department) -- money moving inside the City, not new spending."),
    "Contribution To Reserves/Reserve Funds": ("Contributions to reserve funds", "Money set aside for future use (capital projects, insurance claims, etc.), not spent this year."),
    "Other Expenditures": ("Other expenditures", "Grants and subsidies to residents or agencies, debt charges, and costs that don't fit the categories above."),
    "Contribution To Capital": ("Contribution to capital", "Money transferred from the operating budget to fund capital construction projects."),
}
CATEGORY_ORDER = [
    "Salaries", "Benefits", "Service And Rent", "Materials & Supplies", "Equipment",
    "Other Expenditures", "Inter-Divisional Charges",
    "Contribution To Reserves/Reserve Funds", "Contribution To Capital",
]


# --- 4. Revenue bucketing (keyword rules, first match wins) ---
# Order matters -- more specific rules first. Applied to commitment_item.lower().
REVENUE_BUCKET_RULES = [
    ("Property Tax", ["tax levy", "supp taxes", "supplementary tax"]),
    ("Other Taxes", ["land transfer", "hotel and lodging", "third party sign tax", "lodging ta"]),
    ("Provincial Transfers", ["prov grant", "prov subs", "provincial grant", "provincial subs", "recoveries from province",
                              "recoveries fr prov", "f/p/m-provincial", "f/p/m-prov contrib"]),
    ("Federal Transfers", ["fed grant", "fed subs", "federal grant", "federal subs", "f/p/m-federal"]),
    ("Water and Waste Fees", ["sale of water", "waste collection", "dump fee", "dumping fee", "industrial waste",
                              "idr-water", "idr - water", "idr-solid waste", "idr - solid waste", "idr-wastewtr",
                              "idr - wastewater", "recycled material"]),
    ("Fines and Penalties", ["fine", "penalty"]),
    ("User Fees, Licences and Permits", ["fee", "charge", "permit", "licence", "license", "admission",
                                          "registration"]),
    ("Transfers From Reserves and Capital", ["reserve", "capital fund", "trans fr capital", "cont from",
                                              "contribution from", "dev chg"]),
    ("Investment and Rental Income", ["investment income", "interest income", "rental", "rents,", "rent of"]),
    ("Inter-Divisional Recoveries", ["idr-", "idr -", "inter-divisional"]),
]


def classify_revenue_bucket(commitment_item: str) -> str:
    s = (commitment_item or "").lower()
    for bucket, keywords in REVENUE_BUCKET_RULES:
        if any(kw in s for kw in keywords):
            return bucket
    return "Other Revenue"


REVENUE_BUCKET_ORDER = [b for b, _ in REVENUE_BUCKET_RULES] + ["Other Revenue"]

REVENUE_BUCKET_DESCRIPTIONS = {
    "Property Tax": "The property tax levy -- the single largest revenue source, set annually by Council.",
    "Other Taxes": "Municipal Land Transfer Tax, the Hotel and Lodging Tax (MAT), and similar City-specific taxes.",
    "Provincial Transfers": "Grants and cost-shared funding from the Government of Ontario.",
    "Federal Transfers": "Grants and cost-shared funding from the Government of Canada.",
    "Water and Waste Fees": "What residents and businesses pay for water and solid waste collection -- billed separately from property tax.",
    "Fines and Penalties": "Parking tickets, bylaw fines, and similar penalties.",
    "User Fees, Licences and Permits": "What the City charges directly for specific services -- recreation programs, permits, licences, parking.",
    "Transfers From Reserves and Capital": "Money drawn from savings set aside in prior years, not new revenue raised this year.",
    "Investment and Rental Income": "Interest earned on City funds and rent from City-owned property.",
    "Inter-Divisional Recoveries": "Internal billing between City divisions -- money moving inside the City, not revenue from outside it.",
    "Other Revenue": "Miscellaneous revenue that doesn't fit the categories above.",
}

# Revenue buckets where the City sets the rate/fee itself (or the tax is City-specific).
# Excludes Provincial/Federal transfers (Queen's Park/Ottawa set those, not Toronto),
# reserve/capital drawdowns (past savings, not new revenue), investment income, and
# inter-divisional recoveries (internal, not revenue from outside the City). Used on
# the homepage to answer "what am I paying more of that's actually within the City's
# control" -- a narrower, more precise question than "what revenue grew."
CITY_CONTROLLED_REVENUE_BUCKETS = {
    "Property Tax", "Other Taxes", "User Fees, Licences and Permits",
    "Water and Waste Fees", "Fines and Penalties",
}

# Olivia Chow was sworn in 2023-07-12 (source below) -- after the FY2023 operating
# budget had already been approved by Council in February 2023, under the outgoing
# mayor. Her first full budget cycle was FY2024. Used on the homepage, which compares
# 2023-2025 at the user's request as a mayoral-term reference point -- this note keeps
# that framing honest: the 2023 baseline itself predates her taking office, and every
# City budget is Council's collective decision, not the mayor's alone.
MAYORAL_TRANSITION_YEAR = 2023
MAYORAL_TRANSITION_NOTE = (
    "Mayor Chow was sworn in July 12, 2023, after the FY2023 budget had already been "
    "approved by Council under the outgoing mayor -- her first full budget cycle was "
    "FY2024. Every City budget is approved by Council as a whole, not by the mayor alone."
)
MAYORAL_TRANSITION_SOURCE = "https://www.toronto.ca/news/mayor-olivia-chow-takes-office-as-mayor-of-toronto/"

# Sourced separately from the raw budget data -- see /methodology. Council-approved
# residential property tax rate increases (CBC News), not derived from FactBudgetLine.
PROPERTY_TAX_RATE_HISTORY = [
    {"year": 2022, "increase_pct": 2.9, "note": "plus a 1.5% City Building Levy ($141 avg. increase)",
     "source_url": "https://www.cbc.ca/news/canada/toronto/toronto-city-council-special-meeting-2022-budget-1.6355293"},
    {"year": 2023, "increase_pct": 5.5, "note": "7% including the City Building Levy",
     "source_url": "https://www.cbc.ca/news/canada/toronto/toronto-property-tax-hike-1.6708309"},
    {"year": 2024, "increase_pct": 9.5, "note": "largest single-year increase in more than 25 years",
     "source_url": "https://www.cbc.ca/news/canada/toronto/toronto-budget-debate-tax-hike-1.7114394"},
    {"year": 2025, "increase_pct": 6.9, "note": "",
     "source_url": "https://www.cbc.ca/news/canada/toronto/toronto-2025-budget-council-meeting-1.7455475"},
]

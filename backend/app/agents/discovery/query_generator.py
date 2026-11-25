"""Search query generator — creates targeted search queries for opportunity discovery."""


# ── Base Search Templates ────────────────────────────
# These templates generate high-precision queries for each opportunity type.

SEARCH_TEMPLATES: dict[str, list[str]] = {
    "PhD": [
        '"{topic}" PhD position {year}',
        '"{topic}" doctoral opening fully funded',
        '"{topic}" PhD scholarship {year}',
        'site:*.edu "{topic}" PhD student opening',
        '"{topic}" doctoral candidate position',
    ],
    "Internship": [
        '"{topic}" research internship {year}',
        '"{topic}" summer research intern',
        '"{topic}" internship AI ML {year}',
        'site:*.com "{topic}" research intern position',
        '"{topic}" student research internship paid',
    ],
    "Fellowship": [
        '"{topic}" research fellowship {year}',
        '"{topic}" fellowship application open',
        '"{topic}" postgraduate fellowship fully funded',
    ],
    "Scholarship": [
        '"{topic}" research scholarship {year}',
        '"{topic}" scholarship masters PhD funding',
        '"{topic}" fully funded scholarship international',
    ],
    "Postdoc": [
        '"{topic}" postdoc position {year}',
        '"{topic}" postdoctoral researcher opening',
        '"{topic}" post-doctoral fellowship',
    ],
    "Summer School": [
        '"{topic}" summer school {year}',
        '"{topic}" summer program research {year}',
        '"{topic}" workshop summer school apply',
    ],
    "AI Residency": [
        '"AI residency" program {year}',
        '"ML residency" research {year}',
        '"research residency" artificial intelligence {year}',
    ],
    "Research Assistant": [
        '"{topic}" research assistant position',
        '"{topic}" RA position university {year}',
        '"{topic}" research associate opening',
    ],
}

# ── Curated Site Searches ────────────────────────────
SITE_SEARCHES = [
    (
        "site:euraxess.ec.europa.eu",
        [
            "PhD position {topic}",
            "postdoc {topic}",
            "fellowship {topic}",
        ],
    ),
    (
        "site:academicpositions.com",
        [
            "PhD {topic}",
            "postdoc {topic}",
        ],
    ),
    (
        "site:findaphd.com",
        [
            "{topic}",
        ],
    ),
    (
        "site:scholarshipdb.net",
        [
            "{topic} fully funded",
        ],
    ),
    (
        "site:github.com/dspinellis/awesome-phd",
        [
            "{topic}",
        ],
    ),
]


def generate_search_queries(
    topics: list[str],
    opportunity_types: list[str] | None = None,
    year: str | None = None,
    max_queries: int = 30,
) -> list[str]:
    """
    Generate targeted search queries from user topics and opportunity types.

    Args:
        topics: Research topics (e.g., ["NLP", "Reinforcement Learning"])
        opportunity_types: Types to search for (e.g., ["PhD", "Internship"])
        year: Target year (defaults to current year)
        max_queries: Maximum number of queries to generate

    Returns:
        List of search query strings, deduplicated and limited.
    """
    from datetime import datetime

    year = year or str(datetime.now().year)
    opportunity_types = opportunity_types or ["PhD", "Internship", "Fellowship"]

    queries: list[str] = []

    # 1. Generate from templates
    for opp_type in opportunity_types:
        templates = SEARCH_TEMPLATES.get(opp_type, [])
        for topic in topics:
            for template in templates:
                query = template.format(topic=topic, year=year)
                queries.append(query)

    # 2. Add site-specific searches
    for site_prefix, site_templates in SITE_SEARCHES:
        for topic in topics[:3]:  # Limit site searches
            for template in site_templates:
                query = f"{site_prefix} {template.format(topic=topic)}"
                queries.append(query)

    # 3. Add broad discovery queries
    for topic in topics:
        queries.append(f'"{topic}" open positions research {year}')
        queries.append(f'"{topic}" call for applications {year}')

    # Deduplicate (preserving order)
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique[:max_queries]


def generate_monitoring_queries(
    topics: list[str],
    last_crawl_hours: int = 24,
) -> list[str]:
    """
    Generate queries to monitor for NEW opportunities (for scheduled re-crawls).

    Uses time-restricted queries to only find recent postings.
    """
    queries = []
    for topic in topics[:5]:
        # Google-style time-restricted queries
        queries.append(f'"{topic}" PhD position new')
        queries.append(f'"{topic}" research internship new opening')
        queries.append(f'"{topic}" fellowship deadline upcoming')

    return queries

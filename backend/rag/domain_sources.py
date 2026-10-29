"""
Maps each agent domain to the knowledge base source files it's allowed to
retrieve from. Addresses the limitation flagged since Milestone 4: all 5
agents previously shared one undifferentiated FAISS index with no
filtering, risking cross-contamination (e.g., a billing query
accidentally retrieving product-warranty content).

premium_troubleshooting.txt is intentionally shared between billing and
technical — it genuinely spans both (the M0 example: "paid yesterday but
Premium still locked" needs both). This is a deliberate overlap, not an
oversight.

If a new domain or document is added later and this mapping isn't
updated, retrieval falls back to searching the whole knowledge base for
that domain (see rag/retrieval.py) rather than silently returning zero
results — a missing mapping degrades gracefully, it doesn't break.
"""

DOMAIN_SOURCES: dict[str, set[str]] = {
    "billing": {"refund_policy.txt", "premium_troubleshooting.txt"},
    "technical": {"technical_troubleshooting.txt", "premium_troubleshooting.txt"},
    "product": {"product_warranty.txt"},
    "complaint": {"complaint_escalation.txt"},
    "faq": {"general_faq.txt"},
}


def get_allowed_sources(domain: str) -> set[str] | None:
    """Returns None (meaning "search everything") if the domain has no
    explicit mapping, rather than an empty set that would silently
    exclude all content."""
    return DOMAIN_SOURCES.get(domain)

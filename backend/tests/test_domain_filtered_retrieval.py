"""
Tests for domain-filtered retrieval — verifies each agent only retrieves
from its own mapped source documents, and that the shared
premium_troubleshooting.txt overlap (billing + technical) works as
intended.
"""
import sys
sys.path.insert(0, ".")

from rag.ingestion import ingest_directory
from rag.retrieval import retrieve
from rag.domain_sources import get_allowed_sources, DOMAIN_SOURCES
from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION


def test_billing_never_retrieves_product_content():
    """Contrived cross-domain query: even if a query happens to score
    higher against product_warranty.txt under the fake embedding, billing's
    domain filter must still exclude it entirely."""
    ep = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", ep, embedding_dim=DIMENSION)
    allowed = get_allowed_sources("billing")

    result = retrieve("warranty specification compatible", ep, store, top_k=5, allowed_sources=allowed)
    sources = {c["source"] for c in result.chunks}
    assert "product_warranty.txt" not in sources
    print("test_billing_never_retrieves_product_content: PASS")


def test_technical_never_retrieves_complaint_content():
    ep = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", ep, embedding_dim=DIMENSION)
    allowed = get_allowed_sources("technical")

    result = retrieve("complaint escalation account manager unhappy", ep, store, top_k=5, allowed_sources=allowed)
    sources = {c["source"] for c in result.chunks}
    assert "complaint_escalation.txt" not in sources
    print("test_technical_never_retrieves_complaint_content: PASS")


def test_premium_doc_reachable_by_both_billing_and_technical():
    """The intentional overlap: premium_troubleshooting.txt genuinely spans
    both domains and must be retrievable by either agent."""
    billing_sources = get_allowed_sources("billing")
    technical_sources = get_allowed_sources("technical")
    assert "premium_troubleshooting.txt" in billing_sources
    assert "premium_troubleshooting.txt" in technical_sources
    print("test_premium_doc_reachable_by_both_billing_and_technical: PASS")


def test_unfiltered_search_still_works_when_allowed_sources_is_none():
    """Backward compatibility: passing no filter still searches everything
    (existing M2/M3 behavior must not break)."""
    ep = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", ep, embedding_dim=DIMENSION)

    result = retrieve("refund payment original method", ep, store, top_k=3, allowed_sources=None)
    assert len(result.chunks) > 0
    print("test_unfiltered_search_still_works_when_allowed_sources_is_none: PASS")


def test_missing_domain_mapping_falls_back_to_unrestricted_search():
    """A domain with no entry in DOMAIN_SOURCES must degrade gracefully
    (search everything), not silently return zero results."""
    result = get_allowed_sources("some_future_domain_not_yet_mapped")
    assert result is None
    print("test_missing_domain_mapping_falls_back_to_unrestricted_search: PASS")


def test_faq_domain_only_reaches_general_faq_doc():
    ep = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", ep, embedding_dim=DIMENSION)
    allowed = get_allowed_sources("faq")

    result = retrieve("refund payment warranty complaint technical", ep, store, top_k=5, allowed_sources=allowed)
    sources = {c["source"] for c in result.chunks}
    assert sources <= {"general_faq.txt"}
    print("test_faq_domain_only_reaches_general_faq_doc: PASS")


def test_all_five_domains_have_a_mapping():
    for domain in ["billing", "technical", "product", "complaint", "faq"]:
        assert domain in DOMAIN_SOURCES, f"{domain} is missing from DOMAIN_SOURCES"
    print("test_all_five_domains_have_a_mapping: PASS")


if __name__ == "__main__":
    test_billing_never_retrieves_product_content()
    test_technical_never_retrieves_complaint_content()
    test_premium_doc_reachable_by_both_billing_and_technical()
    test_unfiltered_search_still_works_when_allowed_sources_is_none()
    test_missing_domain_mapping_falls_back_to_unrestricted_search()
    test_faq_domain_only_reaches_general_faq_doc()
    test_all_five_domains_have_a_mapping()
    print("\nAll domain-filtered retrieval tests passed.")

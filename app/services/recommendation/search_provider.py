from app.services.recommendation.text import contains_term, tokenize
from app.services.recommendation.types import Candidate


class SqlSearchProvider:
    def __init__(self, recommendation_repo):
        self.recommendation_repo = recommendation_repo

    def search_merchants(self, intent):
        merchants = self.recommendation_repo.list_candidate_merchants(
            intent.must.campus
        )

        return [self._merchant_candidate(merchant, intent) for merchant in merchants]

    def search_menus(self, intent, merchant_id: int | None = None):
        menus = self.recommendation_repo.list_candidate_menus(
            intent.must.campus,
            merchant_id,
        )

        return [self._menu_candidate(menu, intent) for menu in menus]

    def _merchant_candidate(self, merchant, intent):
        matched_terms = self._matched_terms(merchant, None, intent.prefer.terms)
        return Candidate(
            merchant=merchant,
            search_score=len(matched_terms) * 12,
            matched_terms=matched_terms,
        )

    def _menu_candidate(self, menu, intent):
        matched_terms = self._matched_terms(menu.merchant, menu, intent.prefer.terms)
        return Candidate(
            merchant=menu.merchant,
            menu=menu,
            search_score=len(matched_terms) * 12,
            matched_terms=matched_terms,
        )

    def _matched_terms(self, merchant, menu, preferred_terms):
        candidate_text = self._candidate_text(merchant, menu)
        candidate_tokens = tokenize(candidate_text)
        matched_terms = []

        for term in preferred_terms:
            normalized = term.lower()

            if normalized in candidate_tokens or contains_term(candidate_text, term):
                matched_terms.append(term)

        return matched_terms

    def _candidate_text(self, merchant, menu):
        pieces = [
            merchant.merchant_name,
            merchant.category,
            " ".join(merchant.tags or []),
        ]

        if menu:
            pieces.append(menu.item_name)
        else:
            pieces.extend(menu_item.item_name for menu_item in merchant.menus)

        return " ".join(pieces)

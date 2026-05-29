import json
import logging
import os
import urllib.error
import urllib.request

from app.services.recommendation.text import delivery_minutes, tokenize
from app.services.recommendation.types import RankedCandidate

logger = logging.getLogger(__name__)


class OpenRouterRerankClient:
    DEFAULT_API_URL = "https://openrouter.ai/api/v1/rerank"
    DEFAULT_MODEL = "cohere/rerank-v3.5"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        api_url: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_RERANK_MODEL", self.DEFAULT_MODEL)
        self.api_url = api_url or os.getenv(
            "OPENROUTER_RERANK_API_URL",
            self.DEFAULT_API_URL,
        )
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("OPENROUTER_RERANK_TIMEOUT_SECONDS", "4")
        )

    def is_enabled(self):
        return bool(self.api_key)

    def rerank(self, query: str, documents: list[str]):
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": len(documents),
        }
        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "Kubereats"),
            },
            method="POST",
        )

        logger.info(
            "OpenRouter rerank request model=%s document_count=%s query=%r",
            self.model,
            len(documents),
            query,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter rerank request failed: {details}") from exc

        data = json.loads(response_body)
        scores = [0.0 for _ in documents]

        for result in data.get("results", []):
            scores[result["index"]] = float(result["relevance_score"])

        logger.info(
            "OpenRouter rerank success model=%s usage=%s scores=%s",
            data.get("model", self.model),
            data.get("usage"),
            scores,
        )
        return scores


class HeuristicRerankerProvider:
    HEURISTIC_WEIGHT = 0.35
    RERANK_WEIGHT = 0.65

    def __init__(self, rerank_client: OpenRouterRerankClient | None = None):
        self.rerank_client = rerank_client or OpenRouterRerankClient()

    def rerank(self, candidates, intent, user_context, limit: int, prompt: str = ""):
        ranked_candidates = [
            self._rank_candidate(candidate, intent, user_context)
            for candidate in candidates
        ]
        ranked_candidates = self._apply_ai_rerank(
            ranked_candidates,
            intent,
            user_context,
            prompt,
        )

        return sorted(
            ranked_candidates,
            key=lambda ranked: ranked.score,
            reverse=True,
        )[:limit]

    def _rank_candidate(self, candidate, intent, user_context):
        merchant = candidate.merchant
        signals = {
            "matchedTerms": candidate.matched_terms,
            "excludedTerms": intent.must.excluded_terms,
            "avoidRecentRelaxed": candidate.avoid_recent_relaxed,
            "recentlyOrdered": merchant.id in user_context.recent_merchant_ids,
        }
        rating_score = float(merchant.rating) * 10
        popularity_score = min(merchant.order_count, 200) * 0.08
        budget_score = self._budget_score(candidate, intent, user_context)
        delivery_score = self._delivery_score(merchant, intent)
        history_score = self._history_score(candidate, intent, user_context)
        novelty_score = self._novelty_score(candidate, intent, user_context)
        capacity_score = self._capacity_score(candidate)

        score = (
            candidate.search_score
            + rating_score
            + popularity_score
            + budget_score
            + delivery_score
            + history_score
            + novelty_score
            + capacity_score
        )

        signals.update(
            {
                "searchScore": round(candidate.search_score, 2),
                "ratingScore": round(rating_score, 2),
                "popularityScore": round(popularity_score, 2),
                "budgetScore": round(budget_score, 2),
                "deliveryScore": round(delivery_score, 2),
                "historyScore": round(history_score, 2),
                "noveltyScore": round(novelty_score, 2),
                "capacityScore": round(capacity_score, 2),
                "heuristicScore": round(score, 2),
            }
        )

        return RankedCandidate(
            candidate=candidate,
            score=round(score, 2),
            signals=signals,
        )

    def _apply_ai_rerank(self, ranked_candidates, intent, user_context, prompt: str):
        if not ranked_candidates:
            return ranked_candidates

        if not self.rerank_client.is_enabled():
            logger.info("AI reranker disabled; using heuristic scores only")
            self._apply_weighted_scores(
                ranked_candidates,
                rerank_scores=None,
                heuristic_weight=1,
                rerank_weight=0,
                source="heuristic_only",
            )
            return ranked_candidates

        query = self._rerank_query(prompt, intent)
        documents = [
            self._candidate_document(ranked.candidate, user_context)
            for ranked in ranked_candidates
        ]

        try:
            rerank_scores = self.rerank_client.rerank(query, documents)
        except Exception:
            logger.exception("OpenRouter rerank failed; using heuristic scores only")
            self._apply_weighted_scores(
                ranked_candidates,
                rerank_scores=None,
                heuristic_weight=1,
                rerank_weight=0,
                source="heuristic_fallback",
            )
            return ranked_candidates

        self._apply_weighted_scores(
            ranked_candidates,
            rerank_scores=rerank_scores,
            heuristic_weight=self.HEURISTIC_WEIGHT,
            rerank_weight=self.RERANK_WEIGHT,
            source="openrouter",
        )
        return ranked_candidates

    def _apply_weighted_scores(
        self,
        ranked_candidates,
        rerank_scores: list[float] | None,
        heuristic_weight: float,
        rerank_weight: float,
        source: str,
    ):
        normalized_rerank_scores = self._normalize_rerank_scores(
            rerank_scores,
            len(ranked_candidates),
        )

        for index, ranked in enumerate(ranked_candidates):
            rerank_score = rerank_scores[index] if rerank_scores else 0
            normalized_rerank_score = normalized_rerank_scores[index]
            weighted_components = self._weighted_components(
                ranked.signals,
                heuristic_weight,
            )
            weighted_heuristic_score = round(ranked.score * heuristic_weight, 2)
            weighted_rerank_score = round(
                normalized_rerank_score * 100 * rerank_weight,
                2,
            )
            final_score = round(weighted_heuristic_score + weighted_rerank_score, 2)
            ranked.score = final_score
            ranked.signals.update(
                {
                    "rerankSource": source,
                    "rerankScore": round(rerank_score, 4),
                    "normalizedRerankScore": round(normalized_rerank_score, 4),
                    "heuristicWeight": heuristic_weight,
                    "rerankWeight": rerank_weight,
                    "weightedScores": weighted_components
                    | {
                        "aiRerankRawScore": round(rerank_score, 4),
                        "aiRerankNormalizedScore": round(
                            normalized_rerank_score,
                            4,
                        ),
                        "heuristicTotal": weighted_heuristic_score,
                        "aiRerank": weighted_rerank_score,
                        "final": final_score,
                    },
                }
            )
            logger.info(
                "Reranker weighted scores source=%s candidate=%s scores=%s",
                source,
                self._candidate_label(ranked.candidate),
                json.dumps(
                    ranked.signals["weightedScores"],
                    ensure_ascii=False,
                ),
            )

    def _normalize_rerank_scores(
        self,
        rerank_scores: list[float] | None,
        candidate_count: int,
    ):
        if not rerank_scores:
            return [0.0 for _ in range(candidate_count)]

        max_score = max(rerank_scores)

        if max_score <= 0:
            return [0.0 for _ in rerank_scores]

        return [score / max_score for score in rerank_scores]

    def _weighted_components(self, signals, heuristic_weight: float):
        keys = [
            "searchScore",
            "ratingScore",
            "popularityScore",
            "budgetScore",
            "deliveryScore",
            "historyScore",
            "noveltyScore",
            "capacityScore",
        ]
        return {
            key: round(float(signals.get(key, 0)) * heuristic_weight, 2)
            for key in keys
        }

    def _rerank_query(self, prompt: str, intent):
        criteria = [
            f"使用者想吃：{prompt or '系統推薦'}",
            f"偏好：{', '.join(intent.prefer.terms) or '無'}",
            f"希望避免：{'最近吃過的店家' if intent.avoid.recent_merchants else '無'}",
            f"排除：{', '.join(intent.must.excluded_terms) or '無'}",
            (
                f"預算限制：{intent.must.max_budget:g} 元以內"
                if intent.must.max_budget is not None
                else "預算限制：無"
            ),
        ]
        return "\n".join(criteria)

    def _candidate_document(self, candidate, user_context):
        merchant = candidate.merchant
        pieces = [
            f"店家：{merchant.merchant_name}",
            f"分類：{merchant.category}",
            f"標籤：{', '.join(merchant.tags or []) or '無'}",
            f"評分：{float(merchant.rating):.1f}",
            f"訂單數：{merchant.order_count}",
            f"配送時間：{merchant.delivery_time}",
            (
                "是否最近吃過：是"
                if merchant.id in user_context.recent_merchant_ids
                else "是否最近吃過：否"
            ),
        ]

        if candidate.menu:
            pieces.extend(
                [
                    f"菜品：{candidate.menu.item_name}",
                    f"價格：{float(candidate.menu.price):g}",
                    f"每日供應量：{candidate.menu.max_daily_quantity}",
                ]
            )
        else:
            menu_names = [menu.item_name for menu in merchant.menus[:8]]
            pieces.extend(
                [
                    f"最低消費：{float(merchant.min_order):g}",
                    f"最大接單量：{merchant.max_order_quantity}",
                    f"菜單摘要：{', '.join(menu_names) or '無'}",
                ]
            )

        return "\n".join(pieces)

    def _candidate_label(self, candidate):
        if candidate.menu:
            return f"{candidate.merchant.merchant_name} / {candidate.menu.item_name}"

        return candidate.merchant.merchant_name

    def _budget_score(self, candidate, intent, user_context):
        price = self._candidate_price(candidate)

        if price is None:
            return 0

        if intent.must.max_budget is not None:
            return 10 if price <= intent.must.max_budget else -20

        if user_context.average_spend is None:
            return 0

        difference = abs(price - user_context.average_spend)
        return max(0, 10 - difference * 0.1)

    def _delivery_score(self, merchant, intent):
        minutes = delivery_minutes(merchant.delivery_time)

        if minutes is None:
            return 0

        if intent.prefer.fast_delivery:
            return max(0, 18 - minutes * 0.35)

        return max(0, 6 - minutes * 0.1)

    def _history_score(self, candidate, intent, user_context):
        merchant = candidate.merchant
        candidate_terms = self._candidate_terms(candidate)
        matched_user_terms = candidate_terms & user_context.favorite_terms
        category_match = merchant.category in user_context.favorite_categories

        if intent.prefer.novelty:
            return (len(matched_user_terms) * 1.5) + (2 if category_match else 0)

        score = len(matched_user_terms) * 3

        if intent.prefer.familiar and merchant.id in user_context.favorite_merchant_ids:
            score += 16
        elif merchant.id in user_context.favorite_merchant_ids:
            score += 6

        if category_match:
            score += 5

        return score

    def _novelty_score(self, candidate, intent, user_context):
        if not intent.prefer.novelty:
            return 0

        if candidate.merchant.id in user_context.recent_merchant_ids:
            return -35 if candidate.avoid_recent_relaxed else -18

        return 14

    def _capacity_score(self, candidate):
        if candidate.menu:
            return min(candidate.menu.max_daily_quantity, 100) * 0.04

        return min(candidate.merchant.max_order_quantity, 100) * 0.03

    def _candidate_price(self, candidate):
        if candidate.menu:
            return float(candidate.menu.price)

        prices = [float(menu.price) for menu in candidate.merchant.menus]
        return min(prices) if prices else float(candidate.merchant.min_order)

    def _candidate_terms(self, candidate):
        merchant = candidate.merchant
        terms = tokenize(merchant.merchant_name) | tokenize(merchant.category)

        for tag in merchant.tags or []:
            terms.update(tokenize(tag))

        if candidate.menu:
            terms.update(tokenize(candidate.menu.item_name))
        else:
            for menu in merchant.menus:
                terms.update(tokenize(menu.item_name))

        return terms

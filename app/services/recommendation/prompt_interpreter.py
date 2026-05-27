import re

from app.schemas.recommendation import (
    RecommendationAvoidConstraints,
    RecommendationIntent,
    RecommendationMustConstraints,
    RecommendationPreferences,
)


class PromptInterpreter:
    FOOD_TERMS = [
        "牛肉",
        "豬肉",
        "雞肉",
        "雞腿",
        "咖哩",
        "便當",
        "燒臘",
        "麵",
        "湯麵",
        "蔬食",
        "低卡",
        "健康",
        "清爽",
        "辣",
        "港式",
        "台式",
        "日式",
    ]
    PREFERENCE_TERMS = [
        "清爽",
        "健康",
        "低卡",
        "蔬食",
        "咖哩",
        "便當",
        "雞腿",
        "燒臘",
        "麵",
        "港式",
        "台式",
        "日式",
        "熱賣",
        "人氣",
    ]
    EXCLUDE_PREFIXES = ("不要", "不吃", "避免", "排除", "不想吃")
    RECENT_AVOID_KEYWORDS = ("最近沒吃過", "換一家", "不要重複", "不想重複", "換口味")
    FAST_DELIVERY_KEYWORDS = ("快送", "快一點", "快點", "快", "配送快")
    POPULAR_KEYWORDS = ("熱門", "人氣", "大家常吃", "最多人", "評分高")
    FAMILIAR_KEYWORDS = ("平常", "常吃", "喜歡的", "我會喜歡", "習慣")

    def interpret(self, prompt: str, campus: str | None = None):
        normalized = prompt.lower()
        excluded_terms = self._excluded_terms(normalized)
        preferred_terms = [
            term
            for term in self.PREFERENCE_TERMS
            if term in prompt and term not in excluded_terms
        ]
        max_budget = self._max_budget(normalized)
        avoid_recent = any(keyword in prompt for keyword in self.RECENT_AVOID_KEYWORDS)
        prefer_fast = any(keyword in prompt for keyword in self.FAST_DELIVERY_KEYWORDS)
        prefer_popular = any(keyword in prompt for keyword in self.POPULAR_KEYWORDS)
        prefer_familiar = any(keyword in prompt for keyword in self.FAMILIAR_KEYWORDS)

        return RecommendationIntent(
            must=RecommendationMustConstraints(
                campus=campus,
                excluded_terms=excluded_terms,
                max_budget=max_budget,
            ),
            avoid=RecommendationAvoidConstraints(recent_merchants=avoid_recent),
            prefer=RecommendationPreferences(
                terms=preferred_terms,
                fast_delivery=prefer_fast,
                popular=prefer_popular,
                familiar=prefer_familiar,
                novelty=avoid_recent,
            ),
        )

    def _excluded_terms(self, prompt: str):
        excluded_terms = []

        for term in self.FOOD_TERMS:
            if any(f"{prefix}{term}" in prompt for prefix in self.EXCLUDE_PREFIXES):
                excluded_terms.append(term)

        return excluded_terms

    def _max_budget(self, prompt: str):
        budget_patterns = [
            r"(\d+)\s*(?:元)?\s*(?:以下|以內|內|之內)",
            r"預算\s*(?:是|在|大概|約)?\s*(\d+)",
            r"不要太貴.*?(\d+)",
        ]

        for pattern in budget_patterns:
            match = re.search(pattern, prompt)

            if match:
                return float(match.group(1))

        return None

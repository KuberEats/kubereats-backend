import json
import logging
import os
import re
import urllib.error
import urllib.request

from app.schemas.recommendation import (
    RecommendationAvoidConstraints,
    RecommendationIntent,
    RecommendationMustConstraints,
    RecommendationPreferences,
)

logger = logging.getLogger(__name__)


class OpenRouterPromptClient:
    DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "google/gemini-3.1-flash-lite"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        api_url: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", self.DEFAULT_MODEL)
        self.api_url = api_url or os.getenv("OPENROUTER_API_URL", self.DEFAULT_API_URL)
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("OPENROUTER_TIMEOUT_SECONDS", "4")
        )

    def is_enabled(self):
        return bool(self.api_key)

    def interpret(self, prompt: str, campus: str | None = None):
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        logger.info(
            "PromptInterpreter OpenRouter request model=%s campus=%s prompt=%r",
            self.model,
            campus,
            prompt,
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You parse Traditional Chinese food recommendation prompts "
                        "for a campus food delivery recommendation system. Return only "
                        "the structured intent. Treat must as hard constraints, avoid "
                        "as relaxable constraints, and prefer as ranking preferences. "
                        "Use short Traditional Chinese food/category terms."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "campus": campus,
                            "allowedCampuses": ["竹科", "南科", "中科", "高科"],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": 300,
            "provider": {
                "require_parameters": True,
            },
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "recommendation_intent",
                    "strict": True,
                    "schema": self._response_schema(),
                },
            },
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

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter request failed: {details}") from exc

        data = json.loads(response_body)
        content = data["choices"][0]["message"]["content"]
        intent_data = json.loads(content) if isinstance(content, str) else content
        intent_data.setdefault("must", {})["campus"] = campus
        intent = RecommendationIntent.model_validate(intent_data)
        logger.info(
            "PromptInterpreter OpenRouter parsed intent=%s",
            self._intent_for_log(intent),
        )
        return intent

    def _intent_for_log(self, intent: RecommendationIntent):
        return json.dumps(
            intent.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
        )

    def _response_schema(self):
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "must": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "campus": {
                            "type": ["string", "null"],
                            "enum": ["竹科", "南科", "中科", "高科", None],
                        },
                        "excluded_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "max_budget": {"type": ["number", "null"]},
                    },
                    "required": ["campus", "excluded_terms", "max_budget"],
                },
                "avoid": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "recent_merchants": {"type": "boolean"},
                        "recent_order_limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                    "required": ["recent_merchants", "recent_order_limit"],
                },
                "prefer": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "terms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "fast_delivery": {"type": "boolean"},
                        "popular": {"type": "boolean"},
                        "familiar": {"type": "boolean"},
                        "novelty": {"type": "boolean"},
                    },
                    "required": [
                        "terms",
                        "fast_delivery",
                        "popular",
                        "familiar",
                        "novelty",
                    ],
                },
            },
            "required": ["must", "avoid", "prefer"],
        }


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

    def __init__(self, ai_client: OpenRouterPromptClient | None = None):
        self.ai_client = ai_client or OpenRouterPromptClient()

    def interpret(self, prompt: str, campus: str | None = None):
        if self.ai_client.is_enabled():
            try:
                intent = self.ai_client.interpret(prompt, campus)
                self._log_success("openrouter", prompt, campus, intent)
                return intent
            except Exception:
                logger.exception("OpenRouter prompt interpretation failed; using fallback")

        intent = self._interpret_with_rules(prompt, campus)
        self._log_success("fallback_rules", prompt, campus, intent)
        return intent

    def _interpret_with_rules(self, prompt: str, campus: str | None = None):
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

    def _log_success(
        self,
        source: str,
        prompt: str,
        campus: str | None,
        intent: RecommendationIntent,
    ):
        logger.info(
            "PromptInterpreter success source=%s campus=%s prompt=%r intent=%s",
            source,
            campus,
            prompt,
            json.dumps(
                intent.model_dump(mode="json", by_alias=True),
                ensure_ascii=False,
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

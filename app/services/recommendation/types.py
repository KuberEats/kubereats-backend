from dataclasses import dataclass, field


@dataclass
class UserContext:
    user_id: int
    tag_terms: set[str] = field(default_factory=set)
    history_terms: set[str] = field(default_factory=set)
    recent_merchant_ids: set[int] = field(default_factory=set)
    recent_merchant_names: set[str] = field(default_factory=set)
    favorite_merchant_ids: set[int] = field(default_factory=set)
    favorite_categories: set[str] = field(default_factory=set)
    favorite_terms: set[str] = field(default_factory=set)
    average_spend: float | None = None


@dataclass
class Candidate:
    merchant: object
    menu: object | None = None
    search_score: float = 0
    matched_terms: list[str] = field(default_factory=list)
    avoid_recent_relaxed: bool = False


@dataclass
class RankedCandidate:
    candidate: Candidate
    score: float
    signals: dict[str, object]

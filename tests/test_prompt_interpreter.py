from app.services.recommendation.prompt_interpreter import PromptInterpreter


class DisabledAiClient:
    def is_enabled(self):
        return False


def test_prompt_interpreter_fallback_extracts_constraints_and_preferences():
    interpreter = PromptInterpreter(ai_client=DisabledAiClient())

    intent = interpreter.interpret(
        "今天想吃清爽一點，不要牛肉，最近沒吃過的，150 以下，快一點",
        campus="竹科",
    )

    assert intent.must.campus == "竹科"
    assert intent.must.excluded_terms == ["牛肉"]
    assert intent.must.max_budget == 150
    assert intent.avoid.recent_merchants is True
    assert intent.prefer.terms == ["清爽"]
    assert intent.prefer.fast_delivery is True
    assert intent.prefer.novelty is True

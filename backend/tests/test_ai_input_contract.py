from pydantic import ValidationError

from app.schemas import AiRecommendIn


def test_ai_recommend_input_limit_is_2000() -> None:
    assert len(AiRecommendIn(message="x" * 2000).message) == 2000
    try:
        AiRecommendIn(message="x" * 2001)
    except ValidationError:
        pass
    else:
        raise AssertionError("AI recommendation input over 2000 characters must be rejected")

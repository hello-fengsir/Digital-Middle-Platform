import json
import os

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.main import create_app


class ValidationProbe(BaseModel):
    customer_text: str = Field(min_length=1)
    quantity: int
    required_name: str


router = APIRouter()


@router.post("/validation-probe")
def validation_probe(payload: ValidationProbe) -> dict[str, bool]:
    return {"ok": bool(payload)}


app = create_app()
app.include_router(router)
client = TestClient(app)


def _assert_sanitized_422(response, secrets: list[str]) -> list[dict]:
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], list) and body["detail"]
    assert all(set(error) <= {"type", "loc", "msg", "ctx"} for error in body["detail"])
    assert all({"type", "loc", "msg"} <= set(error) for error in body["detail"])

    serialized = json.dumps(body, ensure_ascii=False)
    assert '"input"' not in serialized
    assert '"url"' not in serialized
    for secret in secrets:
        assert secret not in serialized
    return body["detail"]


def test_ai_message_2001_characters_is_rejected_without_echo() -> None:
    customer_marker = "客户机密原文"
    customer_text = customer_marker + "密" * (2001 - len(customer_marker))
    assert len(customer_text) == 2001

    errors = _assert_sanitized_422(
        client.post("/api/v1/ai/recommend", json={"message": customer_text}),
        [customer_text, customer_marker],
    )

    assert errors[0]["type"] == "string_too_long"
    assert errors[0]["loc"] == ["body", "message"]
    assert errors[0]["ctx"] == {"max_length": 2000}


def test_body_field_type_error_does_not_echo_customer_value() -> None:
    customer_text = "原始客户数量不可回显-ACME-7788"

    errors = _assert_sanitized_422(
        client.post(
            "/validation-probe",
            json={"customer_text": "正常说明", "quantity": customer_text, "required_name": "已提供"},
        ),
        [customer_text],
    )

    assert errors[0]["loc"] == ["body", "quantity"]
    assert errors[0]["type"] == "int_parsing"


def test_missing_body_fields_keep_understandable_locations_without_echo() -> None:
    customer_text = "保留在未通过校验请求中的客户文本-PRIVATE-991"

    errors = _assert_sanitized_422(
        client.post("/validation-probe", json={"customer_text": customer_text}),
        [customer_text],
    )

    assert {(error["type"], tuple(error["loc"])) for error in errors} == {
        ("missing", ("body", "quantity")),
        ("missing", ("body", "required_name")),
    }


def test_invalid_json_does_not_echo_raw_body_fragment() -> None:
    customer_text = "JSON中的客户秘密-DO-NOT-ECHO"
    raw_body = '{"customer_text":"' + customer_text + '","quantity":'

    errors = _assert_sanitized_422(
        client.post("/validation-probe", content=raw_body, headers={"content-type": "application/json"}),
        [customer_text, raw_body],
    )

    assert errors[0]["type"] == "json_invalid"
    assert errors[0]["loc"][0] == "body"
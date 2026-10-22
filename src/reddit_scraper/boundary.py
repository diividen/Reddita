"""Shared strict external-boundary model base."""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict
from pydantic.config import ExtraValues


def _to_camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


class BoundaryModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        extra="forbid",
        frozen=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        return super().model_validate_json(
            json_data, strict=True, extra=extra, context=context,
            by_alias=True, by_name=False,
        )

    def model_dump_json(self, **kwargs: Any) -> str:
        kwargs["by_alias"] = True
        return super().model_dump_json(**kwargs)

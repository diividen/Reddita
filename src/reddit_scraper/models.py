"""Bounded, deterministic wire records shared by capture source adapters."""

from __future__ import annotations

import hashlib
import json
import math
from enum import Enum
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, StringConstraints, field_validator, model_validator

from .boundary import BoundaryModel


MAX_RECORDS = 10_000
MAX_PAGES = 100
MAX_GAPS = 128
MAX_JSON_BYTES = 1_048_576
MAX_JSON_DEPTH = 64
MAX_JSON_ITEMS = 10_000

Locator = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=8192)]
Identifier = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=512)]
Label = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=64)]
Continuation = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4096)]
ObjectJson = Annotated[str, StringConstraints(strict=True, min_length=2, max_length=MAX_JSON_BYTES)]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]


class SourceBudgets(BoundaryModel):
    timeout_seconds: int = Field(default=60, gt=0, le=3600, strict=True)
    max_requests: int = Field(default=100, gt=0, le=1000, strict=True)
    max_network_bytes: int = Field(default=100_000_000, gt=0, le=100_000_000, strict=True)
    max_storage_bytes: int = Field(default=1_000_000_000, gt=0, le=1_000_000_000, strict=True)


class CaptureSource(str, Enum):
    REDDIT = "reddit"


class CaptureOperation(str, Enum):
    SEARCH = "search"
    SUBREDDIT = "subreddit"
    SUBREDDIT_SEARCH = "subreddit-search"
    THREAD = "thread"
    ABOUT = "about"


SOURCE_OPERATIONS = MappingProxyType({
    CaptureSource.REDDIT: (CaptureOperation.SEARCH, CaptureOperation.SUBREDDIT,
                           CaptureOperation.SUBREDDIT_SEARCH, CaptureOperation.THREAD,
                           CaptureOperation.ABOUT),
})


def _canonical_object_json(value: str) -> str:
    if len(value.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("object JSON exceeds byte limit")

    def unique_object(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("object JSON contains duplicate keys")
            result[key] = item
        return result

    def invalid_constant(value):
        raise ValueError("object JSON contains a nonfinite number")

    try:
        decoded = json.loads(value, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except RecursionError as error:
        raise ValueError("object JSON exceeds depth limit") from error
    if not isinstance(decoded, dict):
        raise ValueError("object JSON must contain an object")
    pending = [(decoded, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > MAX_JSON_DEPTH or count > MAX_JSON_ITEMS:
            raise ValueError("object JSON exceeds depth or item limit")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("object JSON contains a nonfinite number")
        if isinstance(item, (dict, list)):
            children = item.values() if isinstance(item, dict) else item
            pending.extend((child, depth + 1) for child in children)
    canonical = json.dumps(decoded, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    if len(canonical.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("object JSON exceeds byte limit")
    return canonical


class _SourceOperation(BoundaryModel):
    source: CaptureSource
    operation: CaptureOperation

    @model_validator(mode="after")
    def validate_source_operation(self):
        if self.operation not in SOURCE_OPERATIONS[self.source]:
            raise ValueError("operation is not supported by capture source")
        return self


class _ContinuationBoundary(BoundaryModel):
    @field_validator("continuation", check_fields=False)
    @classmethod
    def bound_continuation(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > 4096:
            raise ValueError("continuation exceeds byte limit")
        return value


class CaptureGap(BoundaryModel):
    code: Label
    detail: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=4096)]
    locator: Locator | None = None


class CapturePage(_ContinuationBoundary):
    page_index: int = Field(ge=0, strict=True)
    locator: Locator
    record_ids: tuple[Identifier, ...] = Field(default=(), max_length=MAX_RECORDS)
    continuation: Continuation | None = None

    @field_validator("record_ids")
    @classmethod
    def canonical_record_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("page record IDs must be unique")
        return tuple(sorted(value))


class CaptureRecord(BoundaryModel):
    record_id: Identifier
    record_type: Label
    source_locator: Locator
    source_index: int = Field(ge=0, strict=True)
    data_json: ObjectJson

    _canonical_data = field_validator("data_json")(_canonical_object_json)


class CaptureEnvelope(_SourceOperation, _ContinuationBoundary):
    schema_version: Literal["1"]
    requested_locator: Locator
    final_locator: Locator | None
    captured_at: AwareDatetime
    collection_mode: Literal["static", "rendered", "structured", "supplied"]
    complete: StrictBool
    record_count: int = Field(ge=0, le=MAX_RECORDS, strict=True)
    continuation: Continuation | None
    gaps: tuple[CaptureGap, ...] = Field(max_length=MAX_GAPS)
    source_sha256: Digest | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @field_validator("gaps")
    @classmethod
    def canonical_gaps(cls, value: tuple[CaptureGap, ...]) -> tuple[CaptureGap, ...]:
        if len(set(value)) != len(value):
            raise ValueError("capture gaps must be unique")
        return tuple(sorted(value, key=lambda gap: (gap.code, gap.locator or "", gap.detail)))

    @model_validator(mode="after")
    def validate_completeness(self):
        if self.complete and (self.continuation is not None or self.gaps):
            raise ValueError("complete capture cannot have continuation or gaps")
        return self


class SourceRequest(_SourceOperation, _ContinuationBoundary):
    locator: Locator
    parameters_json: ObjectJson = "{}"
    continuation: Continuation | None = None
    max_records: int = Field(default=100, ge=1, le=MAX_RECORDS, strict=True)
    max_pages: int = Field(default=10, ge=1, le=MAX_PAGES, strict=True)

    _canonical_parameters = field_validator("parameters_json")(_canonical_object_json)


def source_slice_digest(request: SourceRequest) -> str:
    """Identify one effective source slice, including its cursor and allowances."""
    return hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()


class SourceResult(BoundaryModel):
    envelope: CaptureEnvelope
    records: tuple[CaptureRecord, ...] = Field(max_length=MAX_RECORDS)
    pages: tuple[CapturePage, ...] = Field(max_length=MAX_PAGES)

    @model_validator(mode="after")
    def validate_record_closure(self):
        record_ids = [record.record_id for record in self.records]
        indices = [record.source_index for record in self.records]
        page_indices = [page.page_index for page in self.pages]
        if len(set(record_ids)) != len(record_ids) or len(set(indices)) != len(indices):
            raise ValueError("record IDs and source indices must be unique")
        if len(set(page_indices)) != len(page_indices):
            raise ValueError("page indices must be unique")
        if len(self.records) != self.envelope.record_count:
            raise ValueError("envelope record count must match records")
        references = [record_id for page in self.pages for record_id in page.record_ids]
        if sorted(references) != sorted(record_ids):
            raise ValueError("page record IDs must close exactly to records")
        object.__setattr__(self, "records", tuple(sorted(self.records, key=lambda record: record.source_index)))
        object.__setattr__(self, "pages", tuple(sorted(self.pages, key=lambda page: page.page_index)))
        return self

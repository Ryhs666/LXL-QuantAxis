"""Normalized news-event schema checks."""

from src.lxl_quantaxis.data.providers import DataKind, PointInTimeRecord, SchemaViolation


def validate_news_record(record: PointInTimeRecord) -> tuple[SchemaViolation, ...]:
    if record.kind is not DataKind.NEWS:
        return (SchemaViolation("news.kind", "record is not news data"),)
    issues: list[SchemaViolation] = []
    title = record.payload.get("title")
    if not isinstance(title, str) or not title.strip():
        issues.append(SchemaViolation("news.title", "title must be a non-empty string"))
    source_url = record.payload.get("source_url")
    if not isinstance(source_url, str) or not source_url.startswith(("https://", "http://")):
        issues.append(SchemaViolation("news.source_url", "source_url must be HTTP(S)"))
    language = record.payload.get("language")
    if not isinstance(language, str) or not language.strip():
        issues.append(SchemaViolation("news.language", "language must be a non-empty string"))
    return tuple(issues)

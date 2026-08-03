"""Market data provider contracts and legacy mapping."""

from src.lxl_quantaxis.data.providers.market.legacy import map_legacy_market_rows
from src.lxl_quantaxis.data.providers.market.schema import validate_market_record

__all__ = ["map_legacy_market_rows", "validate_market_record"]

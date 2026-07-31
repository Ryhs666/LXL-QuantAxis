"""
BaseProvider — abstract interface for all market data providers.

Every provider must implement:
  - get_history(request) → pd.DataFrame
  - validate() → bool (can this provider serve the request?)
"""

from abc import ABC, abstractmethod
import pandas as pd
from src.data.models import DataRequest, DataSourceError, Market, AssetType


class BaseProvider(ABC):
    """Abstract base for all data providers.

    Subclasses implement get_history() for their market/asset domain.
    """

    name: str = "base"
    supported_markets: tuple = ()
    supported_asset_types: tuple = ()

    def can_serve(self, request: DataRequest) -> bool:
        """Check whether this provider can handle the request."""
        return (
            request.market in self.supported_markets and
            request.asset_type in self.supported_asset_types
        )

    @abstractmethod
    def get_history(self, request: DataRequest) -> pd.DataFrame:
        """Fetch historical OHLCV (or macro) data.

        Args:
            request: DataRequest with symbol, market, dates, etc.

        Returns:
            DataFrame with standardized columns.

        Raises:
            DataSourceError: If data cannot be retrieved.
        """
        ...

    def get_info(self, symbol: str) -> dict:
        """Optional: return metadata about a symbol."""
        return {"symbol": symbol, "name": "", "market": "", "currency": ""}

    def _validate_response(self, df: pd.DataFrame, symbol: str):
        """Validate that a response is non-empty."""
        if df is None or df.empty:
            raise DataSourceError(
                f"[{self.name}] No data returned for {symbol}. "
                f"Check symbol validity and date range."
            )

    def __repr__(self):
        return f"<{self.__class__.__name__} markets={self.supported_markets}>"

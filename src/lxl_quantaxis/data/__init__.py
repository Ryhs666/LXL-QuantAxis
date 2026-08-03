"""Side-effect-free V2 data contracts, catalog, and storage adapters."""

from src.lxl_quantaxis.data.catalog import Dataset, DatasetSnapshot
from src.lxl_quantaxis.data.contracts import StorageKey, StorageMetadata, StoragePort
from src.lxl_quantaxis.data.storage import (
    DataRoot,
    DataRootConfigurationError,
    LegacyCsvAdapter,
    LegacySqliteAdapter,
    LocalStorageAdapter,
)

__all__ = [
    "DataRoot",
    "DataRootConfigurationError",
    "Dataset",
    "DatasetSnapshot",
    "LegacyCsvAdapter",
    "LegacySqliteAdapter",
    "LocalStorageAdapter",
    "StorageKey",
    "StorageMetadata",
    "StoragePort",
]

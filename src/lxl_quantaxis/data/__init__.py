"""Side-effect-free V2 data contracts, catalog, and storage adapters."""

from src.lxl_quantaxis.data.catalog import Dataset, DatasetSnapshot
from src.lxl_quantaxis.data.contracts import StorageKey, StorageMetadata, StoragePort
from src.lxl_quantaxis.data.providers import DataKind, PointInTimeProvider, PointInTimeRecord, RevisionHistory
from src.lxl_quantaxis.data.quality import QualityGate, QualityMode
from src.lxl_quantaxis.data.storage import (
    DataRoot,
    DataRootConfigurationError,
    LegacyCsvAdapter,
    LegacySqliteAdapter,
    LocalStorageAdapter,
)

__all__ = [
    "DataKind",
    "DataRoot",
    "DataRootConfigurationError",
    "Dataset",
    "DatasetSnapshot",
    "LegacyCsvAdapter",
    "LegacySqliteAdapter",
    "LocalStorageAdapter",
    "PointInTimeProvider",
    "PointInTimeRecord",
    "QualityGate",
    "QualityMode",
    "RevisionHistory",
    "StorageKey",
    "StorageMetadata",
    "StoragePort",
]

"""Integration tests for V2 core infrastructure adoption."""

import logging
import pytest
from src.lxl_quantaxis.core.logging import get_logger, configure_root
from src.lxl_quantaxis.core.config.loader import QuantConfig, get_config
from src.lxl_quantaxis.core.exceptions import (
    QuantAxisError, DataError, StrategyError, BacktestError,
    RiskError, AIError, ConfigError, SecurityError, ValidationError,
)


class TestLoggerIntegration:
    def test_get_logger_returns_logger(self):
        log = get_logger("test.module")
        assert isinstance(log, logging.Logger)
        assert log.name == "test.module"

    def test_get_logger_has_handler(self):
        log = get_logger("test.module2")
        assert len(log.handlers) >= 1

    def test_get_logger_respects_level(self):
        log = get_logger("test.debug", level="DEBUG")
        assert log.level == logging.DEBUG

    def test_backtest_logger_exists(self):
        log = get_logger("backtest.engine")
        log.info("integration test message")
        assert True  # no exception = pass

    def test_ai_logger_exists(self):
        log = get_logger("ai.engine")
        log.info("integration test message")
        assert True


class TestConfigIntegration:
    def test_get_config_returns_quant_config(self):
        cfg = get_config()
        assert isinstance(cfg, QuantConfig)
        assert cfg.data_dir != ""
        assert cfg.initial_capital > 0

    def test_config_is_singleton(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_config_from_env(self):
        env = {"QUANT_DATA_DIR": "/tmp/integration_test"}
        cfg = QuantConfig.load(env=env)
        assert "integration_test" in cfg.data_dir


class TestExceptionsIntegration:
    def test_all_exceptions_inherit_base(self):
        for cls in [DataError, StrategyError, BacktestError, RiskError,
                     AIError, ConfigError, SecurityError, ValidationError]:
            assert issubclass(cls, QuantAxisError)

    def test_exceptions_are_raisable(self):
        with pytest.raises(DataError):
            raise DataError("test")
        with pytest.raises(BacktestError):
            raise BacktestError("valuation failed")
        with pytest.raises(RiskError):
            raise RiskError("limit breached")


class TestLoggerInCoreModules:
    def test_engine_imports_logger(self):
        from src.backtest.engine import _log
        assert _log is not None

    def test_ai_engine_imports_logger(self):
        from src.ai.engine import _log
        assert _log is not None

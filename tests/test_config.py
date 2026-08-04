"""Tests for unified configuration system."""

import os
import pytest
from src.lxl_quantaxis.core.config.loader import QuantConfig, DEFAULTS, get_config


class TestQuantConfig:
    def test_load_from_env(self):
        env = {
            "QUANT_DATA_DIR": "/tmp/test_quant_data",
            "QUANT_INITIAL_CAPITAL": "200000",
            "QUANT_COMMISSION_RATE": "0.0005",
            "QUANT_LOG_LEVEL": "DEBUG",
        }
        cfg = QuantConfig.load(env=env)
        assert "test_quant_data" in cfg.data_dir
        assert cfg.initial_capital == 200000
        assert cfg.commission_rate == 0.0005
        assert cfg.log_level == "DEBUG"

    def test_defaults_are_finite(self):
        cfg = QuantConfig.load()
        assert isinstance(cfg.initial_capital, (int, float))
        assert cfg.initial_capital > 0
        assert 0 < cfg.commission_rate < 1
        assert cfg.position_size_pct > 0
        assert cfg.max_drawdown_limit > 0

    def test_cache_dir_derives_from_data_dir(self):
        env = {"QUANT_DATA_DIR": "/tmp/my_data"}
        cfg = QuantConfig.load(env=env)
        assert "my_data" in cfg.cache_dir

    def test_bool_env_parsing(self):
        env = {"QUANT_VERBOSE": "true"}
        cfg = QuantConfig.load(env=env)
        assert cfg.verbose is True

        env2 = {"QUANT_VERBOSE": "0"}
        cfg2 = QuantConfig.load(env=env2)
        assert cfg2.verbose is False

    def test_env_variable_override(self):
        env = {"QUANT_MAX_POSITIONS": "5"}
        cfg = QuantConfig.load(env=env)
        assert cfg.max_positions == 5

    def test_frozen_dataclass(self):
        cfg = QuantConfig.load()
        with pytest.raises(Exception):
            cfg.initial_capital = 9999  # type: ignore

    def test_ensure_dirs_creates(self, tmp_path):
        import shutil
        env = {"QUANT_DATA_DIR": str(tmp_path / "quant_data")}
        cfg = QuantConfig.load(env=env)
        cfg.ensure_dirs()
        assert (tmp_path / "quant_data").exists()
        shutil.rmtree(tmp_path / "quant_data")

    def test_invalid_float_falls_back(self):
        env = {"QUANT_INITIAL_CAPITAL": "not_a_number"}
        with pytest.raises(ValueError):
            QuantConfig.load(env=env)

    def test_deterministic_same_env(self):
        env = {"QUANT_DATA_DIR": "/tmp/a", "QUANT_INITIAL_CAPITAL": "999"}
        c1 = QuantConfig.load(env=env)
        c2 = QuantConfig.load(env=env)
        assert c1.initial_capital == c2.initial_capital
        assert c1.data_dir == c2.data_dir

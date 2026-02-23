"""
Tests for configuration loading and validation
"""
import pytest
from pathlib import Path
from pydantic import ValidationError
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from config import ServiceConfig
from hams.config import HamsConfig


class TestConfigLoading:
    """Test configuration loading from YAML and secrets"""

    def test_config_from_yaml_valid(self, test_config_path, test_secrets_path):
        """Test loading a valid configuration file"""
        config = ServiceConfig.from_yaml_and_secrets_dir(
            yaml_file=test_config_path,
            secrets_path=test_secrets_path
        )

        assert config is not None
        assert config.webservice.url.port == 8080
        assert config.hams.url.port == 8079
        assert config.persistence.db.connection.username == "myuser"

    def test_config_database_dsn_property(self, sample_config):
        """Test that database DSN property is correctly formatted"""
        dsn = sample_config.persistence.db.connection.dsn

        assert "postgresql://" in dsn
        assert "myuser" in dsn
        assert "localhost:5432" in dsn
        assert "service-capture" in dsn


        """Test HAMS URL configuration"""
        assert sample_config.hams.url.host == "localhost"
        assert sample_config.hams.url.port == 8079
        assert sample_config.hams.prefix == "hams"

    def test_config_invalid_yaml_path(self):
        """Test loading from non-existent YAML file"""
        with pytest.raises(Exception):
            ServiceConfig.from_yaml_and_secrets_dir(
                yaml_file=Path("/nonexistent/config.yaml"),
                secrets_path=Path("/tmp")
            )

    def test_config_missing_secrets_dir(self, test_config_path):
        """Test loading with missing secrets directory (should use defaults)"""
        # Should not raise, just log warning
        config = ServiceConfig.from_yaml_and_secrets_dir(
            yaml_file=test_config_path,
            secrets_path=Path("/nonexistent/secrets")
        )
        assert config is not None


class TestConfigValidation:
    """Test Pydantic validation on config models"""

    def test_hams_config_validation(self):
        """Test HAMS config requires valid URL"""
        config = HamsConfig(
            url="http://localhost:8079/",
            prefix="hams",
            checks={"timeout": 5, "fails": 3, "preflights": [], "shutdowns": []},
            shutdownDuration="PT5S"
        )
        assert config.url.port == 8079

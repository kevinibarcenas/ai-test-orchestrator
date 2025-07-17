"""Tests for file manager"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from orchestrator.core.file_manager import FileManager, FileInfo


@pytest.fixture
def file_manager():
    """Create test file manager instance"""
    with patch('orchestrator.core.file_manager.OpenAI'):
        return FileManager()


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample file for testing"""
    file_path = tmp_path / "test.yaml"
    file_path.write_text("test: content")
    return file_path


def test_file_validation(file_manager, sample_file):
    """Test file validation"""
    # Valid file should not raise
    file_manager._validate_file(sample_file)

    # Non-existent file should raise
    with pytest.raises(FileNotFoundError):
        file_manager._validate_file(Path("nonexistent.yaml"))


@pytest.mark.asyncio
async def test_file_hash_calculation(file_manager, sample_file):
    """Test file hash calculation"""
    hash1 = await file_manager._calculate_file_hash(sample_file)
    hash2 = await file_manager._calculate_file_hash(sample_file)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex length


def test_mime_type_detection(file_manager):
    """Test MIME type detection"""
    assert file_manager._get_mime_type(Path("test.yaml")) == "text/yaml"
    assert file_manager._get_mime_type(Path("test.json")) == "application/json"
    assert file_manager._get_mime_type(Path("test.pdf")) == "application/pdf"

"""Refactored file management with dependency injection"""
import hashlib
import json
import mimetypes
from pathlib import Path
import time
from typing import Dict, List, Optional, Union

import aiofiles
from openai import OpenAI
from pydantic import BaseModel, Field

from src.config.dependencies import inject
from src.config.settings import Settings
from src.utils.logger import get_logger


class FileInfo(BaseModel):
    """Information about an uploaded file"""
    file_id: str = Field(..., description="OpenAI file ID")
    filename: str = Field(..., description="Original filename")
    file_path: Path = Field(..., description="Local file path")
    file_hash: str = Field(..., description="SHA256 hash of file content")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    upload_timestamp: float = Field(..., description="Upload timestamp")
    purpose: str = Field(default="user_data",
                         description="OpenAI file purpose")

    class Config:
        json_encoders = {Path: str}


class FileRegistry(BaseModel):
    """Registry of uploaded files with caching"""
    files: Dict[str, FileInfo] = Field(
        default_factory=dict, description="File registry")
    version: str = Field(default="1.0", description="Registry version")

    def add_file(self, file_info: FileInfo) -> None:
        """Add file to registry"""
        self.files[file_info.file_hash] = file_info

    def get_file_by_hash(self, file_hash: str) -> Optional[FileInfo]:
        """Get file info by hash"""
        return self.files.get(file_hash)

    def get_file_by_path(self, file_path: Path) -> Optional[FileInfo]:
        """Get file info by path"""
        for file_info in self.files.values():
            if file_info.file_path == file_path:
                return file_info
        return None

    def remove_file(self, file_hash: str) -> bool:
        """Remove file from registry"""
        return self.files.pop(file_hash, None) is not None

    def cleanup_missing_files(self) -> List[str]:
        """Remove entries for files that no longer exist locally"""
        removed = []
        for file_hash, file_info in list(self.files.items()):
            if not file_info.file_path.exists():
                self.remove_file(file_hash)
                removed.append(file_hash)
        return removed


class FileManager:
    """Manages file uploads and caching for OpenAI API with dependency injection"""

    @inject
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("file_manager")
        self.client = OpenAI(api_key=settings.openai_api_key)

        # Registry file path
        self.registry_path = Path("cache") / "file_registry.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing registry
        self.registry = self._load_registry()

        # Cleanup missing files on startup
        removed = self.registry.cleanup_missing_files()
        if removed:
            self.logger.info(
                f"Cleaned up {len(removed)} missing files from registry")
            self._save_registry()

    def _load_registry(self) -> FileRegistry:
        """Load file registry from disk"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return FileRegistry(**data)
            except Exception as e:
                self.logger.warning(
                    f"Failed to load registry: {e}, creating new one")

        return FileRegistry()

    def _save_registry(self) -> None:
        """Save file registry to disk"""
        try:
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.registry.dict(), f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")

    async def upload_file(self, file_path: Path, purpose: str = "user_data") -> FileInfo:
        """Upload file to OpenAI and cache the result"""
        try:
            # Validate file
            self._validate_file(file_path)

            # Calculate file hash
            file_hash = await self._calculate_file_hash(file_path)

            # Check if file is already uploaded
            cached_file = self.registry.get_file_by_hash(file_hash)
            if cached_file:
                self.logger.info(f"Using cached file: {cached_file.file_id}")
                return cached_file

            # Upload new file
            self.logger.info(f"Uploading file: {file_path.name}")

            with open(file_path, 'rb') as f:
                response = self.client.files.create(
                    file=f,
                    purpose=purpose
                )

            # Create file info
            file_info = FileInfo(
                file_id=response.id,
                filename=file_path.name,
                file_path=file_path,
                file_hash=file_hash,
                file_size=file_path.stat().st_size,
                mime_type=mimetypes.guess_type(str(file_path))[
                    0] or "application/octet-stream",
                upload_timestamp=time.time(),
                purpose=purpose
            )

            # Cache the file info
            self.registry.add_file(file_info)
            self._save_registry()

            self.logger.info(f"✅ File uploaded successfully: {response.id}")
            return file_info

        except Exception as e:
            self.logger.error(f"File upload failed: {e}")
            raise

    async def has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last upload"""
        if not file_path.exists():
            return False

        current_hash = await self._calculate_file_hash(file_path)
        cached_file = self.registry.get_file_by_path(file_path)

        if not cached_file:
            return True  # New file

        return current_hash != cached_file.file_hash

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content"""
        hash_sha256 = hashlib.sha256()

        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    def _validate_file(self, file_path: Path) -> None:
        """Validate file before upload"""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Check file size
        file_size = file_path.stat().st_size
        max_size_bytes = self.settings.max_file_size_mb * 1024 * 1024

        if file_size > max_size_bytes:
            raise ValueError(
                f"File too large: {file_size / (1024*1024):.1f}MB > "
                f"{self.settings.max_file_size_mb}MB"
            )

        # Check file type
        file_suffix = file_path.suffix.lower()
        if file_suffix not in self.settings.supported_file_types:
            raise ValueError(
                f"Unsupported file type: {file_suffix}. "
                f"Supported types: {self.settings.supported_file_types}"
            )

    def cleanup_registry(self) -> Dict[str, int]:
        """Cleanup registry and return statistics"""
        initial_count = len(self.registry.files)
        removed = self.registry.cleanup_missing_files()
        self._save_registry()

        return {
            "initial_files": initial_count,
            "removed_files": len(removed),
            "current_files": len(self.registry.files)
        }

    def get_registry_stats(self) -> Dict[str, Union[int, float]]:
        """Get registry statistics"""
        files = list(self.registry.files.values())

        if not files:
            return {"total_files": 0, "total_size_mb": 0.0}

        total_size = sum(f.file_size for f in files)

        return {
            "total_files": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "avg_size_mb": (total_size / len(files)) / (1024 * 1024),
            "file_types": len(set(f.mime_type for f in files))
        }

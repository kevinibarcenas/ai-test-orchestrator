"""File management for OpenAI API uploads and caching"""
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

import aiofiles
from openai import OpenAI
from pydantic import BaseModel, Field

from config.settings import get_settings
from orchestrator.utils.logger import get_logger


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
        json_encoders = {
            Path: str
        }


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
    """Manages file uploads and caching for OpenAI API"""

    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("file_manager")
        self.client = OpenAI(api_key=self.settings.openai_api_key)

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
                f"Supported: {self.settings.supported_file_types}"
            )

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for file"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"

    async def upload_file(
        self,
        file_path: Union[str, Path],
        purpose: str = "user_data",
        force_reupload: bool = False
    ) -> FileInfo:
        """
        Upload file to OpenAI API with caching

        Args:
            file_path: Path to file to upload
            purpose: OpenAI file purpose
            force_reupload: Force reupload even if cached

        Returns:
            FileInfo object with upload details
        """
        file_path = Path(file_path)
        self.logger.info(f"Processing file: {file_path.name}")

        # Validate file
        self._validate_file(file_path)

        # Calculate file hash
        file_hash = await self._calculate_file_hash(file_path)

        # Check if file already uploaded (unless force reupload)
        if not force_reupload:
            cached_file = self.registry.get_file_by_hash(file_hash)
            if cached_file:
                self.logger.info(f"Using cached file: {cached_file.file_id}")
                return cached_file

        # Upload file to OpenAI
        try:
            self.logger.info(f"Uploading {file_path.name} to OpenAI...")

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
                mime_type=self._get_mime_type(file_path),
                upload_timestamp=response.created_at,
                purpose=purpose
            )

            # Add to registry and save
            self.registry.add_file(file_info)
            self._save_registry()

            self.logger.info(
                f"✅ File uploaded successfully: {response.id} "
                f"({file_info.file_size / 1024:.1f}KB)"
            )

            return file_info

        except Exception as e:
            self.logger.error(f"Failed to upload file {file_path.name}: {e}")
            raise

    async def upload_multiple_files(
        self,
        file_paths: List[Union[str, Path]],
        purpose: str = "user_data"
    ) -> List[FileInfo]:
        """Upload multiple files with progress tracking"""
        file_infos = []

        self.logger.info(f"Uploading {len(file_paths)} files...")

        for i, file_path in enumerate(file_paths, 1):
            self.logger.info(f"Processing file {i}/{len(file_paths)}")
            file_info = await self.upload_file(file_path, purpose)
            file_infos.append(file_info)

        self.logger.info(f"✅ All files uploaded successfully")
        return file_infos

    def get_file_info(self, file_path: Union[str, Path]) -> Optional[FileInfo]:
        """Get file info from registry"""
        file_path = Path(file_path)
        return self.registry.get_file_by_path(file_path)

    async def delete_file(self, file_id: str) -> bool:
        """Delete file from OpenAI and remove from registry"""
        try:
            # Delete from OpenAI
            self.client.files.delete(file_id)

            # Remove from registry
            for file_hash, file_info in list(self.registry.files.items()):
                if file_info.file_id == file_id:
                    self.registry.remove_file(file_hash)
                    self._save_registry()
                    self.logger.info(f"Deleted file: {file_id}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def list_uploaded_files(self) -> List[FileInfo]:
        """List all uploaded files in registry"""
        return list(self.registry.files.values())

    async def detect_file_changes(self, file_path: Union[str, Path]) -> bool:
        """
        Detect if file has changed since last upload

        Returns:
            True if file has changed or is new, False otherwise
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return False

        current_hash = await self._calculate_file_hash(file_path)
        cached_file = self.registry.get_file_by_path(file_path)

        if not cached_file:
            return True  # New file

        return current_hash != cached_file.file_hash

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


# Global file manager instance
_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """Get global file manager instance"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager

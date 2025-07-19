"""File export and artifact management service"""
import json
import csv
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger


class ExportService(ABC):
    """Abstract export service interface"""

    @abstractmethod
    async def export_csv(self, data: List[Dict[str, Any]], output_path: Path, headers: List[str]) -> Path:
        """Export data to CSV file"""
        pass

    @abstractmethod
    async def export_json(self, data: Dict[str, Any], output_path: Path) -> Path:
        """Export data to JSON file"""
        pass


class FileExportService(ExportService):
    """File-based export service implementation"""

    def __init__(self):
        self.logger = get_logger("export_service")

    async def export_csv(self, data: List[Dict[str, Any]], output_path: Path, headers: List[str]) -> Path:
        """Export data to CSV file"""
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)

                # Write headers
                writer.writerow(headers)

                # Write data rows
                for row_data in data:
                    row = []
                    for header in headers:
                        value = row_data.get(header, "")
                        # Handle multiline content
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value, ensure_ascii=False)
                        row.append(str(value))
                    writer.writerow(row)

            self.logger.info(
                f"Exported {len(data)} rows to CSV: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            raise

    async def export_json(self, data: Dict[str, Any], output_path: Path) -> Path:
        """Export data to JSON file"""
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2,
                          ensure_ascii=False, default=str)

            self.logger.info(f"Exported JSON data to: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"JSON export failed: {e}")
            raise

"""CSV processing logic separated from agent implementation"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.config.dependencies import inject
from src.config.settings import Settings
from src.services.export_service import ExportService
from src.utils.logger import get_logger


class CSVProcessor:
    """Handles CSV-specific processing logic"""

    @inject
    def __init__(self, settings: Settings, export_service: ExportService):
        self.settings = settings
        self.export_service = export_service
        self.logger = get_logger("csv_processor")

    async def generate_csv_file(
        self,
        test_cases: List[Dict[str, Any]],
        section_id: str,
        headers: List[str]
    ) -> Path:
        """Generate CSV file from test cases"""
        try:
            # Create output path
            timestamp = self._get_timestamp()
            filename = f"test_cases_{section_id}_{timestamp}.csv"
            output_path = self.settings.output_directory / "csv" / filename

            # Convert test cases to CSV format
            csv_rows = []
            for test_case in test_cases:
                row = self._test_case_to_csv_row(test_case, headers)
                csv_rows.append(dict(zip(headers, row)))

            # Export using export service
            result_path = await self.export_service.export_csv(csv_rows, output_path, headers)

            self.logger.info(f"✅ CSV file generated: {result_path}")
            return result_path

        except Exception as e:
            self.logger.error(f"CSV generation failed: {e}")
            raise

    def get_default_headers(self) -> List[str]:
        """Get default CSV headers for QMetry import"""
        return [
            "Test Case ID",
            "Test Case Name",
            "Test Case Description",
            "Module",
            "Test Type",
            "Priority",
            "Estimated Time (mins)",
            "Preconditions",
            "Test Steps",
            "Expected Results",
            "Test Data",
            "Tags"
        ]

    def _test_case_to_csv_row(self, test_case: Dict[str, Any], headers: List[str]) -> List[str]:
        """Convert test case dictionary to CSV row"""
        # Field mapping for flexible header handling
        field_mapping = {
            "Test Case ID": test_case.get("test_case_id", ""),
            "Test Case Name": test_case.get("test_case_name", ""),
            "Test Case Description": test_case.get("test_case_description", ""),
            "Module": test_case.get("module", "API Tests"),
            "Test Type": test_case.get("test_type", "Functional"),
            "Priority": test_case.get("priority", "Medium"),
            "Estimated Time (mins)": test_case.get("estimated_time", "15"),
            "Preconditions": test_case.get("preconditions", ""),
            "Test Steps": self._format_test_steps(test_case.get("test_steps", "")),
            "Expected Results": test_case.get("expected_results", ""),
            "Test Data": self._format_test_data(test_case.get("test_data", "")),
            "Tags": test_case.get("tags", "")
        }

        # Build row according to header order
        row = []
        for header in headers:
            value = field_mapping.get(header, "")
            row.append(str(value))

        return row

    def _format_test_steps(self, test_steps: Any) -> str:
        """Format test steps for CSV (handle multiline)"""
        if isinstance(test_steps, list):
            # Join list items with numbered steps
            formatted_steps = []
            for i, step in enumerate(test_steps, 1):
                formatted_steps.append(f"{i}. {step}")
            return "\n".join(formatted_steps)

        return str(test_steps).replace('\n', '\n')  # Preserve line breaks

    def _format_test_data(self, test_data: Any) -> str:
        """Format test data for CSV"""
        if isinstance(test_data, dict):
            # Convert dict to readable format
            formatted_data = []
            for key, value in test_data.items():
                formatted_data.append(f"{key}: {value}")
            return "\n".join(formatted_data)
        elif isinstance(test_data, list):
            return "\n".join(str(item) for item in test_data)

        return str(test_data)

    def _get_timestamp(self) -> str:
        """Get timestamp for filename"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def validate_csv_output(self, csv_file_path: Path) -> bool:
        """Validate generated CSV file"""
        try:
            if not csv_file_path.exists():
                self.logger.error(f"CSV file does not exist: {csv_file_path}")
                return False

            # Check file is not empty
            if csv_file_path.stat().st_size == 0:
                self.logger.error("CSV file is empty")
                return False

            # Validate CSV structure
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader, None)

                if not headers:
                    self.logger.error("CSV file has no headers")
                    return False

                # Check required headers are present
                required_headers = [
                    "Test Case ID", "Test Case Name", "Test Steps", "Expected Results"]
                missing_headers = [
                    h for h in required_headers if h not in headers]

                if missing_headers:
                    self.logger.error(
                        f"Missing required headers: {missing_headers}")
                    return False

                # Count rows
                row_count = sum(1 for row in reader)
                if row_count == 0:
                    self.logger.error("CSV file has no test cases")
                    return False

                self.logger.info(
                    f"✅ CSV validation passed: {row_count} test cases")
                return True

        except Exception as e:
            self.logger.error(f"CSV validation failed: {e}")
            return False

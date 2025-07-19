# src/agents/postman/processors.py
"""Postman collection processing logic"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.config.dependencies import inject
from src.config.settings import Settings
from src.services.export_service import ExportService
from src.utils.logger import get_logger


class PostmanProcessor:
    """Handles Postman collection processing and consolidation"""

    @inject
    def __init__(self, settings: Settings, export_service: ExportService):
        self.settings = settings
        self.export_service = export_service
        self.logger = get_logger("postman_processor")

        # Collection consolidation state
        self._consolidated_collection = None
        self._consolidated_environment = None
        self._total_requests = 0
        self._all_folders = []
        self._api_name = "API"  # Will be set from first collection

    async def generate_collection_files(
        self,
        collection_data: Dict[str, Any],
        environments_data: List[Dict[str, Any]],
        section_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Path]:
        """Generate or update consolidated Postman collection"""
        try:
            # Initialize consolidated collection if this is the first section
            if self._consolidated_collection is None:
                self._initialize_consolidated_collection(collection_data)

            # Add this section's items as a folder to the consolidated collection
            self._add_section_to_collection(
                collection_data, section_id, metadata)

            # Update environment with any new variables (use first environment only)
            if environments_data and self._consolidated_environment is None:
                self._consolidated_environment = environments_data[0]
            elif environments_data:
                self._merge_environment_variables(environments_data[0])

            # For now, return empty dict - we'll generate files when finalize is called
            return {}

        except Exception as e:
            self.logger.error(f"Postman section processing failed: {e}")
            raise

    async def finalize_and_export_collection(
        self,
        base_name: str = None,
        generate_docs: bool = True
    ) -> Dict[str, Path]:
        """Finalize and export the consolidated collection with optional documentation"""
        try:
            if self._consolidated_collection is None:
                raise ValueError("No collection data to export")

            # Create meaningful base name from API name
            if base_name is None:
                clean_api_name = self._create_clean_filename(self._api_name)
                timestamp = self._get_timestamp()
                base_name = f"{clean_api_name}_collection_{timestamp}"

            output_paths = {}

            # Update collection metadata
            self._finalize_collection_metadata()

            # Generate main collection file
            collection_path = await self._generate_collection_file(base_name)
            output_paths["collection"] = collection_path

            # Generate single environment file
            if self._consolidated_environment:
                env_path = await self._generate_environment_file(base_name)
                output_paths["environment"] = env_path

            # Conditionally generate consolidated documentation
            if generate_docs:
                docs_path = await self._generate_consolidated_documentation(base_name)
                output_paths["documentation"] = docs_path
                self.logger.info(f"✅ Generated Postman documentation")
            else:
                self.logger.info(
                    "📋 Skipped Postman documentation generation (disabled)")

            self.logger.info(
                f"✅ Generated consolidated Postman collection with {self._total_requests} requests")
            return output_paths

        except Exception as e:
            self.logger.error(f"Collection finalization failed: {e}")
            raise

    def _create_clean_filename(self, name: str) -> str:
        """Create a clean filename from API name"""
        # Extract API name from collection title
        clean = re.sub(r'\s+(API|Collection|Tests?)\s*$',
                       '', name, flags=re.IGNORECASE)
        # Replace spaces and special characters with underscores
        clean = re.sub(r'[^\w\s-]', '', clean)
        clean = re.sub(r'[-\s]+', '_', clean)
        # Convert to lowercase and remove trailing underscores
        clean = clean.lower().strip('_')
        return clean if clean else "api"

    def _initialize_consolidated_collection(self, first_collection: Dict[str, Any]):
        """Initialize the consolidated collection with base structure"""
        # Extract API name from the first collection
        collection_name = first_collection.get("name", "API Collection")
        self._api_name = collection_name.replace(
            " API Collection", "").replace(" Collection", "")

        # Create a professional collection name
        consolidated_name = f"{self._api_name} API Collection"

        self._consolidated_collection = {
            "info": {
                "name": consolidated_name,
                "description": f"Comprehensive {self._api_name} API collection with all endpoints organized by functionality",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "_postman_id": self._generate_uuid(),
                "version": first_collection.get("version", "1.0.0")
            },
            "item": [],  # Will be populated with folders from each section
            "variable": first_collection.get("variable", []),
            "auth": first_collection.get("auth"),
            "event": first_collection.get("event", [])
        }

        self.logger.info(
            f"✅ Initialized consolidated collection: {consolidated_name}")

    def _add_section_to_collection(self, section_collection: Dict[str, Any], section_id: str, metadata: Dict[str, Any]):
        """Add a section as a folder to the consolidated collection"""
        section_items = section_collection.get("item", [])

        if not section_items:
            return

        # Create a meaningful folder name
        section_name = metadata.get("section_name", section_id)
        folder_name = self._create_readable_folder_name(section_name)

        # Create a folder for this section
        section_folder = {
            "name": folder_name,
            "description": metadata.get("section_description", f"API endpoints for {folder_name}"),
            "item": section_items
        }

        # Add folder to consolidated collection
        self._consolidated_collection["item"].append(section_folder)

        # Track metrics
        request_count = self._count_requests_in_items(section_items)
        self._total_requests += request_count
        self._all_folders.append(section_folder["name"])

        self.logger.info(
            f"✅ Added section '{section_folder['name']}' with {request_count} requests")

    def _create_readable_folder_name(self, section_name: str) -> str:
        """Create a readable folder name from section name"""
        # Remove common prefixes
        clean = re.sub(r'^(section_|api_|test_)', '',
                       section_name, flags=re.IGNORECASE)
        # Split on underscores and capitalize words
        words = clean.replace('_', ' ').replace('-', ' ').split()
        # Capitalize each word and join
        readable = ' '.join(word.capitalize() for word in words if word)
        return readable if readable else "API Endpoints"

    def _merge_environment_variables(self, new_env_data: Dict[str, Any]):
        """Merge new environment variables into the consolidated environment"""
        if not self._consolidated_environment:
            return

        existing_keys = {var["key"]
                         for var in self._consolidated_environment.get("values", [])}
        new_values = new_env_data.get("values", [])

        for new_var in new_values:
            if new_var["key"] not in existing_keys:
                self._consolidated_environment["values"].append(new_var)
                self.logger.debug(
                    f"Added environment variable: {new_var['key']}")

    def _finalize_collection_metadata(self):
        """Update collection metadata before export"""
        if not self._consolidated_collection:
            return

        # Update collection description with summary
        description_parts = [
            f"Comprehensive {self._api_name} API collection with all endpoints organized by functionality.",
            f"Total requests: {self._total_requests}",
            f"Organized into {len(self._all_folders)} functional areas: {', '.join(self._all_folders[:3])}{'...' if len(self._all_folders) > 3 else ''}",
            "Uses environment variables for easy deployment across different environments."
        ]

        self._consolidated_collection["info"]["description"] = " ".join(
            description_parts)

    async def _generate_collection_file(self, base_name: str) -> Path:
        """Generate the consolidated collection file"""
        output_path = self.settings.output_directory / \
            "postman" / f"{base_name}.json"

        # Format collection for Postman v2.1 schema
        formatted_collection = self._format_postman_collection(
            self._consolidated_collection)

        # Export as JSON
        result_path = await self.export_service.export_json(
            formatted_collection, output_path
        )

        self.logger.info(
            f"✅ Consolidated collection file generated: {result_path}")
        return result_path

    async def _generate_environment_file(self, base_name: str) -> Path:
        """Generate single environment file"""
        # Create meaningful environment name
        env_base_name = base_name.replace("_collection_", "_environment_")
        output_path = self.settings.output_directory / \
            "postman" / f"{env_base_name}.json"

        # Format environment for Postman
        formatted_env = self._format_postman_environment(
            self._consolidated_environment, base_name)

        # Export environment file
        result_path = await self.export_service.export_json(
            formatted_env, output_path
        )

        self.logger.info(f"✅ Environment file generated: {result_path}")
        return result_path

    async def _generate_consolidated_documentation(self, base_name: str) -> Path:
        """Generate consolidated documentation for the entire collection"""
        # Create meaningful documentation name
        doc_base_name = base_name.replace("_collection_", "_guide_")
        output_path = self.settings.output_directory / \
            "postman" / f"{doc_base_name}.md"

        # Generate comprehensive documentation
        documentation = self._create_consolidated_documentation()

        # Export as markdown
        result_path = await self.export_service.export_text(
            documentation, output_path
        )

        self.logger.info(
            f"✅ Consolidated documentation generated: {result_path}")
        return result_path

    def _create_consolidated_documentation(self) -> str:
        """Create comprehensive documentation for the consolidated collection"""
        collection_name = self._consolidated_collection["info"]["name"]

        doc_sections = [
            f"# {collection_name}",
            "",
            self._consolidated_collection["info"]["description"],
            "",
            "## Overview",
            f"- **Total Requests**: {self._total_requests}",
            f"- **Functional Areas**: {len(self._all_folders)}",
            f"- **Organization**: Requests organized into logical folders by business domain",
            "",
            "## Collection Structure",
            "",
        ]

        # Document folder structure
        for folder_name in self._all_folders:
            doc_sections.append(f"### 📁 {folder_name}")
            doc_sections.append(
                f"Contains API endpoints related to {folder_name.lower()} functionality.")
            doc_sections.append("")

        doc_sections.extend([
            "## Environment Setup",
            "",
            "This collection uses a single environment file that can be customized for different deployment stages.",
            "",
            "### Required Variables",
            "| Variable | Description | Example |",
            "|----------|-------------|---------|",
            "| `base_url` | API base URL | `https://api.example.com` |",
            "| `auth_token` | Authentication token | `Bearer your-token-here` |",
            "| `api_version` | API version | `v1` |",
            "",
            "### Environment Customization",
            "1. **Development**: Update `base_url` to your local API server",
            "2. **Staging**: Update `base_url` to staging environment",
            "3. **Production**: Update `base_url` to production environment",
            "",
            "## Quick Start",
            "",
            "1. **Import Collection**: Import the collection JSON file into Postman",
            "2. **Import Environment**: Import the environment file",
            "3. **Select Environment**: Choose the imported environment in Postman",
            "4. **Configure Variables**: Update environment variables with your actual values",
            "5. **Test Endpoints**: Start with GET requests to verify connectivity",
            "",
            "## Advanced Features",
            "",
            "This collection includes:",
            "- **Pre-request Scripts**: Automatic token refresh and data generation",
            "- **Test Scripts**: Response validation and variable extraction",
            "- **Request Chaining**: Automatic data flow between related requests",
            "- **Error Handling**: Comprehensive error scenario testing",
            "- **Newman Compatibility**: Can be run from command line for CI/CD",
            "",
            "## Automation",
            "",
            "### Collection Runner",
            "Use Postman's Collection Runner to execute all requests sequentially or test specific folders.",
            "",
            "### Newman (CLI)",
            "```bash",
            f"newman run {collection_name.replace(' ', '_')}.json -e environment.json",
            "```",
            "",
            "### CI/CD Integration",
            "Include this collection in your deployment pipeline for automated API testing.",
            "",
            "## Troubleshooting",
            "",
            "- **Authentication Errors**: Verify `auth_token` is valid and not expired",
            "- **Connection Issues**: Check `base_url` and network connectivity",
            "- **Test Failures**: Review request dependencies and execution order",
            "",
            f"Generated by AI Test Orchestrator on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])

        return "\n".join(doc_sections)

    def _count_requests_in_items(self, items: List[Dict]) -> int:
        """Count total requests in items recursively"""
        count = 0
        for item in items:
            if "request" in item:
                count += 1
            elif "item" in item:
                count += self._count_requests_in_items(item["item"])
        return count

    def _format_postman_collection(self, collection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format collection data to Postman v2.1 schema"""
        return collection_data

    def _format_postman_environment(self, env_data: Dict[str, Any], base_name: str) -> Dict[str, Any]:
        """Format environment data to Postman environment schema"""
        # Create meaningful environment name
        env_name = f"{self._api_name} API Environment"

        return {
            "id": self._generate_uuid(),
            "name": env_name,
            "values": env_data.get("values", []),
            "_postman_variable_scope": "environment",
            "_postman_exported_at": datetime.now().isoformat() + "Z",
            "_postman_exported_using": "AI Test Orchestrator"
        }

    async def validate_collection(self, collection_path: Path) -> bool:
        """Validate the generated Postman collection"""
        try:
            if not collection_path.exists():
                self.logger.error(
                    f"Collection file does not exist: {collection_path}")
                return False

            # Load and validate JSON structure
            with open(collection_path, 'r', encoding='utf-8') as f:
                collection = json.load(f)

            # Validate required Postman collection fields
            required_fields = ["info", "item"]
            missing_fields = [
                field for field in required_fields if field not in collection]

            if missing_fields:
                self.logger.error(f"Missing required fields: {missing_fields}")
                return False

            # Validate info section
            info = collection.get("info", {})
            if not info.get("name") or not info.get("schema"):
                self.logger.error("Invalid collection info section")
                return False

            # Validate items
            items = collection.get("item", [])
            if not items:
                self.logger.warning("Collection has no items")
                return False

            # Count requests
            request_count = self._count_requests_in_items(items)
            self.logger.info(
                f"✅ Collection validation passed: {request_count} requests in {len(items)} folders")

            return True

        except Exception as e:
            self.logger.error(f"Collection validation failed: {e}")
            return False

    def _generate_uuid(self) -> str:
        """Generate a UUID for Postman objects"""
        import uuid
        return str(uuid.uuid4())

    def _get_timestamp(self) -> str:
        """Get timestamp for filename"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def reset_state(self):
        """Reset processor state for new collection generation"""
        self._consolidated_collection = None
        self._consolidated_environment = None
        self._total_requests = 0
        self._all_folders = []
        self._api_name = "API"  # Reset to default
        self.logger.info("✅ Reset processor state for new collection")

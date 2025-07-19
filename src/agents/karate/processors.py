# src/agents/karate/processors.py
"""Karate feature file processing logic"""
import json
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.config.dependencies import inject
from src.config.settings import Settings
from src.services.export_service import ExportService
from src.utils.logger import get_logger


class KarateProcessor:
    """Handles Karate feature file processing and generation"""

    @inject
    def __init__(self, settings: Settings, export_service: ExportService):
        self.settings = settings
        self.export_service = export_service
        self.logger = get_logger("karate_processor")

    async def generate_feature_files(
        self,
        feature_data: Dict[str, Any],
        data_files_data: List[Dict[str, Any]],
        section_id: str,
        metadata: Dict[str, Any],
        generate_docs: bool = True
    ) -> Dict[str, Path]:
        """Generate Karate feature file and optionally associated data files and documentation"""
        try:
            self.logger.debug(f"Generating files for section: {section_id}")
            self.logger.debug(f"Feature data type: {type(feature_data)}")
            self.logger.debug(
                f"Data files type: {type(data_files_data)}, count: {len(data_files_data) if isinstance(data_files_data, list) else 'N/A'}")
            self.logger.debug(f"Metadata type: {type(metadata)}")
            self.logger.debug(f"Generate documentation: {generate_docs}")

            # Create clean filename from feature title or section name
            feature_title = feature_data.get("feature_title", section_id)
            clean_name = self._create_clean_filename(feature_title)

            generated_files = {}

            # Generate main feature file
            feature_content = self._build_feature_content(
                feature_data, metadata)
            feature_filename = f"{clean_name}.feature"
            feature_path = self.settings.output_directory / "karate" / feature_filename

            feature_file_path = await self.export_service.export_text(feature_content, feature_path)
            generated_files["feature"] = feature_file_path

            # Generate data files
            for i, data_file in enumerate(data_files_data):
                # Handle both dict and string cases
                if isinstance(data_file, dict):
                    filename = data_file.get(
                        "filename", f"{clean_name}_data_{i+1}.json")
                    content_str = data_file.get("content", "{}")
                elif isinstance(data_file, str):
                    # If data_file is a string, create a simple structure
                    filename = f"{clean_name}_data_{i+1}.json"
                    content_str = data_file
                else:
                    self.logger.warning(
                        f"Unexpected data_file type: {type(data_file)}")
                    continue

                # Parse content string back to object if needed
                try:
                    if content_str.strip():
                        content = json.loads(content_str)
                    else:
                        content = {}
                except json.JSONDecodeError:
                    # If not valid JSON, treat as plain text
                    content = {"data": content_str}

                # Determine file format and export accordingly
                if filename.endswith('.json'):
                    data_path = self.settings.output_directory / "karate" / filename
                    generated_files[f"data_{i+1}"] = await self.export_service.export_json(content, data_path)
                elif filename.endswith('.csv'):
                    # Convert JSON to CSV format if needed
                    if isinstance(content, list) and content:
                        headers = list(content[0].keys())
                        data_path = self.settings.output_directory / "karate" / filename
                        generated_files[f"data_{i+1}"] = await self.export_service.export_csv(content, data_path, headers)
                    else:
                        # Create simple CSV from string content
                        csv_data = [{"data": str(content)}]
                        data_path = self.settings.output_directory / "karate" / filename
                        generated_files[f"data_{i+1}"] = await self.export_service.export_csv(csv_data, data_path, ["data"])
                elif filename.endswith('.yaml') or filename.endswith('.yml'):
                    if isinstance(content, str):
                        yaml_content = content
                    else:
                        yaml_content = yaml.dump(
                            content, default_flow_style=False, allow_unicode=True)
                    data_path = self.settings.output_directory / "karate" / filename
                    generated_files[f"data_{i+1}"] = await self.export_service.export_text(yaml_content, data_path)

            # Conditionally generate documentation file
            if generate_docs:
                doc_content = self._generate_feature_documentation(
                    feature_data, metadata, list(generated_files.keys()))
                doc_filename = f"{clean_name}_README.md"
                doc_path = self.settings.output_directory / "karate" / doc_filename
                generated_files["documentation"] = await self.export_service.export_text(doc_content, doc_path)
                self.logger.info(
                    f"✅ Generated Karate documentation: {doc_filename}")
            else:
                self.logger.info(
                    "📋 Skipped Karate documentation generation (disabled)")

            self.logger.info(
                f"✅ Generated Karate feature files: {len(generated_files)} files")
            self.logger.debug(
                f"Generated files: {list(generated_files.keys())}")
            return generated_files

        except Exception as e:
            self.logger.error(f"Karate feature generation failed: {e}")
            raise

    def _create_clean_filename(self, name: str) -> str:
        """Create a clean filename from feature title or section name"""
        # Remove "API Tests" suffix if present
        clean = re.sub(r'\s+API\s+Tests?$', '', name, flags=re.IGNORECASE)
        # Replace spaces and special characters with underscores
        clean = re.sub(r'[^\w\s-]', '', clean)
        clean = re.sub(r'[-\s]+', '_', clean)
        # Convert to lowercase and remove trailing underscores
        clean = clean.lower().strip('_')
        return clean if clean else "api_tests"

    def _build_feature_content(self, feature_data: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Build the complete Karate feature file content"""
        lines = []

        # Feature header with documentation
        feature_title = feature_data.get("feature_title", "API Tests")
        feature_description = feature_data.get(
            "feature_description", "Comprehensive API testing scenarios")

        lines.extend([
            f"Feature: {feature_title}",
            "",
            f"  {feature_description}",
            "",
            "  # This feature file was generated by AI Test Orchestrator",
            f"  # Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "  # Framework: Karate DSL 1.4.x",
            "  # Documentation: See accompanying README.md for setup and execution guidance",
            ""
        ])

        # Background section if present
        background = feature_data.get("background", [])
        if background:
            lines.extend([
                "  Background:",
                "    # Common setup steps executed before each scenario"
            ])
            for step in background:
                lines.append(f"    {step}")
            lines.append("")

        # Scenarios
        scenarios = feature_data.get("scenarios", [])
        self.logger.debug(
            f"Processing {len(scenarios)} scenarios from LLM output")

        for i, scenario in enumerate(scenarios):
            self.logger.debug(
                f"Processing scenario {i+1}: {scenario.get('name', 'Unnamed')}")
            scenario_lines = self._build_scenario_content(scenario, i + 1)
            lines.extend(scenario_lines)
            lines.append("")  # Empty line between scenarios

        return "\n".join(lines)

    def _build_scenario_content(self, scenario: Dict[str, Any], scenario_num: int) -> List[str]:
        """Build content for a single scenario"""
        lines = []

        scenario_name = scenario.get("name", f"Test Scenario {scenario_num}")
        scenario_description = scenario.get("description", "")
        tags = scenario.get("tags", [])
        steps = scenario.get("steps", [])
        examples = scenario.get("examples", [])

        # Tags - fix double @ issue
        if tags:
            # Remove any existing @ symbols and add single @ prefix
            clean_tags = [tag.replace('@', '') for tag in tags]
            tag_line = "  " + " ".join(f"@{tag}" for tag in clean_tags)
            lines.append(tag_line)

        # Scenario or Scenario Outline
        if examples:
            lines.append(f"  Scenario Outline: {scenario_name}")
        else:
            lines.append(f"  Scenario: {scenario_name}")

        # Description as comment
        if scenario_description:
            lines.extend([
                f"    # {scenario_description}",
                ""
            ])

        # Steps
        for step in steps:
            # All steps are now simple strings
            lines.append(f"    {step}")

        # Examples table for Scenario Outline
        if examples:
            lines.extend([
                "",
                "    Examples:",
                "      # Test data variations for this scenario outline"
            ])

            # Examples are provided as formatted strings - parse and format properly
            if examples and not any("__" in ex for ex in examples):
                # If examples look like table data, format them properly
                for example_line in examples:
                    if example_line.strip() and not example_line.startswith("#"):
                        lines.append(f"      {example_line}")
            else:
                # Create a simple placeholder table
                lines.extend([
                    "      | parameter | value |",
                    "      | --------- | ----- |",
                    "      | testData  | value1 |"
                ])

        return lines

    def _generate_feature_documentation(
        self,
        feature_data: Dict[str, Any],
        metadata: Dict[str, Any],
        generated_files: List[str]
    ) -> str:
        """Generate comprehensive documentation for the feature file"""
        feature_title = feature_data.get("feature_title", "API Tests")

        doc_sections = [
            f"# {feature_title} - Karate Feature Documentation",
            "",
            "This documentation provides comprehensive guidance for executing and understanding the generated Karate feature file.",
            "",
            "## Overview",
            "",
            f"- **Feature**: {feature_title}",
            f"- **Total Scenarios**: {metadata.get('total_scenarios', 0)}",
            f"- **Data-Driven Scenarios**: {metadata.get('data_driven_count', 0)}",
            f"- **Karate Version**: 1.4.x",
            f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Prerequisites",
            "",
            "Before running these tests, ensure you have:",
            "",
            "1. **Java 8 or higher** installed",
            "2. **Karate framework 1.4.x** configured in your project",
            "3. **Maven** or **Gradle** build tool",
            "4. **API environment** accessible and running",
            "",
            "## Project Structure",
            "",
            "```",
            "src/test/java/",
            "├── features/",
            f"│   ├── {feature_data.get('filename', 'api-tests.feature')}",
            "│   └── data/",
        ]

        # Document data files
        data_files = [f for f in generated_files if f.startswith('data_')]
        if data_files:
            doc_sections.extend([
                "│       ├── test-data.json",
                "│       ├── validation-data.csv",
                "│       └── config-data.yaml"
            ])

        doc_sections.extend([
            "└── runners/",
            "    └── TestRunner.java",
            "```",
            "",
            "## Karate Configuration",
            "",
            "### 1. karate-config.js",
            "",
            "Create a `karate-config.js` file in your `src/test/java` directory:",
            "",
            "```javascript",
            "function fn() {",
            "  var config = {",
            "    baseUrl: 'https://api.example.com',",
            "    apiVersion: 'v1',",
            "    timeout: 30000,",
            "    retryInterval: 1000,",
            "    auth: {",
            "      token: karate.properties['auth.token'],",
            "      apiKey: karate.properties['api.key']",
            "    }",
            "  };",
            "",
            "  // Environment-specific configuration",
            "  if (karate.env == 'dev') {",
            "    config.baseUrl = 'https://dev-api.example.com';",
            "  } else if (karate.env == 'staging') {",
            "    config.baseUrl = 'https://staging-api.example.com';",
            "  }",
            "",
            "  return config;",
            "}",
            "```",
            "",
            "### 2. Test Runner",
            "",
            "Create a JUnit test runner:",
            "",
            "```java",
            "package runners;",
            "",
            "import com.intuit.karate.junit5.Karate;",
            "",
            "class TestRunner {",
            "    ",
            "    @Karate.Test",
            "    Karate testFeature() {",
            f"        return Karate.run(\"classpath:features/{feature_data.get('filename', 'api-tests.feature')}\");",
            "    }",
            "}",
            "```",
            "",
            "## Variables and Configuration",
            "",
            "### Global Variables",
            "",
            "The feature uses these configurable variables:",
            ""
        ])

        # Document variables
        variables_used = metadata.get("variables_used", [])
        if variables_used:
            doc_sections.append("| Variable | Description |")
            doc_sections.append("|----------|-------------|")
            for var in variables_used:
                # Now variables_used is a list of strings
                doc_sections.append(f"| `{var}` | Configuration variable |")
        else:
            doc_sections.append("- `baseUrl`: API base URL")
            doc_sections.append("- `auth.token`: Authentication token")
            doc_sections.append("- `api.version`: API version")

        doc_sections.extend([
            "",
            "### Environment Variables",
            "",
            "Set these system properties when running tests:",
            "",
            "```bash",
            "mvn test -Dkarate.env=dev -Dauth.token=your-token -Dapi.key=your-key",
            "```",
            "",
            "## Execution",
            "",
            "### Command Line",
            "",
            "```bash",
            "# Run all scenarios",
            "mvn test",
            "",
            "# Run specific environment",
            "mvn test -Dkarate.env=staging",
            "",
            "# Run with specific tags",
            "mvn test -Dkarate.options=\"--tags @smoke\"",
            "",
            "# Run with custom properties",
            "mvn test -Dauth.token=abc123 -Dapi.key=xyz789",
            "```",
            "",
            "### IDE Execution",
            "",
            "1. Right-click on the feature file",
            "2. Select 'Run' or 'Debug'",
            "3. Configure environment variables in run configuration",
            "",
            "## Test Data",
            "",
        ])

        # Document data files if they exist
        if data_files:
            doc_sections.extend([
                "The feature uses external data files for data-driven testing:",
                "",
            ])
            for i, data_file in enumerate(data_files, 1):
                doc_sections.append(f"### Data File {i}")
                doc_sections.append(
                    f"- **Purpose**: Test variations and edge cases")
                doc_sections.append(f"- **Format**: JSON/CSV/YAML")
                doc_sections.append(
                    f"- **Usage**: Referenced in Scenario Outline examples")
                doc_sections.append("")

        doc_sections.extend([
            "## Scenario Documentation",
            "",
        ])

        # Document each scenario
        scenarios = feature_data.get("scenarios", [])
        for i, scenario in enumerate(scenarios, 1):
            scenario_name = scenario.get("name", f"Scenario {i}")
            scenario_desc = scenario.get(
                "description", "No description available")
            tags = scenario.get("tags", [])

            doc_sections.extend([
                f"### {i}. {scenario_name}",
                "",
                f"**Description**: {scenario_desc}",
                ""
            ])

            if tags:
                clean_tags = [tag.replace('@', '') for tag in tags]
                doc_sections.append(
                    f"**Tags**: {', '.join(f'@{tag}' for tag in clean_tags)}")
                doc_sections.append("")

        doc_sections.extend([
            "## Troubleshooting",
            "",
            "### Common Issues",
            "",
            "1. **Connection Refused**",
            "   - Verify `baseUrl` is correct",
            "   - Ensure API server is running",
            "   - Check network connectivity",
            "",
            "2. **Authentication Errors**",
            "   - Verify `auth.token` is valid and not expired",
            "   - Check API key permissions",
            "   - Ensure correct authentication method",
            "",
            "3. **Schema Validation Failures**",
            "   - API response structure may have changed",
            "   - Check for new required fields",
            "   - Verify data types match expectations",
            "",
            "4. **Timeout Issues**",
            "   - Increase timeout values in karate-config.js",
            "   - Check API performance",
            "   - Consider retry mechanisms",
            "",
            "### Debug Mode",
            "",
            "Enable debug logging:",
            "",
            "```bash",
            "mvn test -Dkarate.options=\"--debug\"",
            "```",
            "",
            "### Reporting",
            "",
            "Karate generates comprehensive HTML reports at:",
            "```",
            "target/karate-reports/",
            "```",
            "",
            "## Best Practices",
            "",
            "1. **Environment Management**: Use karate-config.js for environment-specific settings",
            "2. **Data Management**: Keep test data in separate files for maintainability",
            "3. **Assertion Strategy**: Use appropriate matchers for different validation scenarios",
            "4. **Error Handling**: Implement proper error scenarios and negative testing",
            "5. **Performance**: Monitor response times and set appropriate timeouts",
            "",
            "## Advanced Features Used",
            "",
        ])

        # Document framework features used
        framework_features = metadata.get("framework_features_used", [])
        if framework_features:
            for feature in framework_features:
                doc_sections.append(
                    f"- **{feature}**: Advanced Karate DSL capability")
        else:
            doc_sections.extend([
                "- **Scenario Outline**: Data-driven testing with examples",
                "- **Background**: Common setup steps",
                "- **Variable Substitution**: Dynamic value replacement",
                "- **JSON Path**: Flexible response validation",
                "- **Schema Validation**: Structure verification"
            ])

        doc_sections.extend([
            "",
            "## Support",
            "",
            "For more information:",
            "- [Karate Documentation](https://github.com/karatelabs/karate)",
            "- [Karate DSL Reference](https://github.com/karatelabs/karate#syntax-guide)",
            "- [Best Practices Guide](https://github.com/karatelabs/karate/tree/master/examples)",
            "",
            f"---",
            f"*Generated by AI Test Orchestrator on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])

        return "\n".join(doc_sections)

    async def validate_feature_file(self, feature_file_path: Path) -> bool:
        """Validate the generated Karate feature file"""
        try:
            if not feature_file_path.exists():
                self.logger.error(
                    f"Feature file does not exist: {feature_file_path}")
                return False

            # Read and basic validation
            with open(feature_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Basic Karate syntax validation
            validation_checks = [
                ("Feature:", "Feature declaration"),
                ("Scenario:", "At least one scenario"),
                ("Given", "Setup steps"),
                ("When", "Action steps"),
                ("Then", "Assertion steps")
            ]

            for check, description in validation_checks:
                if check not in content:
                    self.logger.warning(
                        f"Missing {description} in feature file")

            # Count scenarios
            scenario_count = content.count(
                "Scenario:") + content.count("Scenario Outline:")
            if scenario_count == 0:
                self.logger.error("No scenarios found in feature file")
                return False

            self.logger.info(
                f"✅ Feature file validation passed: {scenario_count} scenarios")
            return True

        except Exception as e:
            self.logger.error(f"Feature file validation failed: {e}")
            return False

    def _get_timestamp(self) -> str:
        """Get timestamp for filename"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

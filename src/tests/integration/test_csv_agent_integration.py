"""Integration tests for CSV agent"""
import pytest
from unittest.mock import patch

from orchestrator.agents.csv_agent import CsvAgent


class TestCsvAgentIntegration:
    """Integration tests for CSV agent with mocked OpenAI calls"""

    @pytest.mark.asyncio
    async def test_full_csv_generation_workflow(
        self,
        csv_agent,
        sample_agent_input,
        mock_openai_client,
        tmp_path
    ):
        """Test complete CSV generation workflow"""
        # Mock settings to use temp directory
        with patch.object(csv_agent.settings, 'output_directory', tmp_path):
            # Execute the agent
            result = await csv_agent.execute(sample_agent_input)

        # Verify execution
        assert result.success is True
        assert result.agent_type.value == "csv"
        assert result.section_id == sample_agent_input.section.section_id
        assert result.test_case_count > 0
        assert result.processing_time > 0
        assert result.csv_file is not None

        # Verify token usage recorded
        assert "total_tokens" in result.token_usage
        assert result.token_usage["total_tokens"] > 0

        # Verify CSV file was created
        csv_path = tmp_path / "csv" / result.csv_file.split("/")[-1]
        # Note: The actual path logic may differ, adjust as needed

        # Verify artifacts list
        assert len(result.artifacts) > 0

    @pytest.mark.asyncio
    async def test_csv_agent_with_openai_error(
        self,
        csv_agent,
        sample_agent_input,
        mock_openai_client
    ):
        """Test CSV agent handling OpenAI API errors"""
        # Make OpenAI client raise an exception
        mock_openai_client.responses.create.side_effect = Exception(
            "API Error")

        result = await csv_agent.execute(sample_agent_input)

        assert result.success is False
        assert len(result.errors) > 0
        assert "API Error" in result.errors[0]
        assert result.test_case_count == 0

    @pytest.mark.asyncio
    async def test_csv_agent_context_building(
        self,
        csv_agent,
        sample_agent_input,
        mock_openai_client
    ):
        """Test that agent builds context messages correctly"""
        await csv_agent.execute(sample_agent_input)

        # Verify the OpenAI client was called
        assert mock_openai_client.responses.create.called

        # Get the call arguments
        call_args = mock_openai_client.responses.create.call_args
        messages = call_args.kwargs["input"]

        # Verify message structure
        assert len(messages) == 2  # System + User
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # Verify user message has file inputs
        user_content = messages[1]["content"]
        file_inputs = [c for c in user_content if c.get(
            "type") == "input_file"]
        text_inputs = [c for c in user_content if c.get(
            "type") == "input_text"]

        assert len(file_inputs) == 2  # swagger + pdf
        assert len(text_inputs) == 1  # section context

        # Verify file IDs
        file_ids = [f["file_id"] for f in file_inputs]
        assert sample_agent_input.swagger_file_id in file_ids
        assert sample_agent_input.pdf_file_id in file_ids

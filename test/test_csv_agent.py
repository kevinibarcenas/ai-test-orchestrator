# Test script: test_csv_agent.py
from src.config.dependencies import get_container
from src.agents.csv.agent import CsvAgent
from src.models.agents import AgentInput, Section

container = get_container()
csv_agent = container.get(CsvAgent)

# Create mock input
section = Section(
    section_id="test_001",
    name="Test Section",
    description="Test section for validation"
)

agent_input = AgentInput(section=section)

# Test agent creation
print(f"✅ CSV Agent created: {csv_agent.agent_type}")
print(f"✅ System prompt: {csv_agent.get_system_prompt_name()}")

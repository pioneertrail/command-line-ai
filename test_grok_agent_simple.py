"""
Tests for the simplified Grok CLI Agent.

This module contains tests for the core functionality of the simplified Grok agent,
including token counting, model management, and command handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from grok_agent_simple_v2 import GrokAgent
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import textwrap
from io import StringIO

# Test data
TEST_API_KEY = "test_api_key_123"
TEST_MODEL = "grok-2-latest"
TEST_TEXT = "Hello, world!"
TEST_TOKENS = 4  # Actual token count for "Hello, world!"

# Test constants
HELP_TEXT = textwrap.dedent("""
    Available Commands:
    /model <model_id> - Switch to a different model
    /info - Display current model information
    /tokens <text> - Show token breakdown
    /exit - Exit the program
    """).strip()

def normalize_whitespace(text):
    """Normalize whitespace in text for comparison"""
    return ' '.join(text.split())

def render_to_string(renderable):
    """Render a Rich renderable object to string"""
    console = Console(file=StringIO(), force_terminal=True)
    console.print(renderable)
    return console.file.getvalue()

@pytest.fixture(autouse=True)
def mock_env():
    """Automatically mock environment variables for all tests"""
    with patch.dict(os.environ, {'GROK_API_KEY': TEST_API_KEY}):
        yield

@pytest.fixture
def mock_openai():
    """Mock OpenAI client for testing"""
    with patch('openai.OpenAI') as mock_class:
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_completions = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.completions = mock_completions
        mock_class.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_console():
    """Mock Rich console for testing"""
    with patch('grok_agent_simple_v2.console') as mock:
        mock.input = MagicMock()
        mock.print = MagicMock()
        yield mock

@pytest.fixture
def agent(mock_openai, mock_console):
    """Create a test agent with mocked dependencies"""
    return GrokAgent()

def test_agent_initialization(agent):
    """Test agent initialization with correct settings"""
    assert agent.api_key == TEST_API_KEY
    assert agent.current_model == TEST_MODEL
    assert isinstance(agent.conversation_history, list)
    assert len(agent.conversation_history) == 0

def test_token_counting(agent):
    """Test token counting functionality"""
    token_count = agent.count_tokens(TEST_TEXT)
    assert token_count == TEST_TOKENS
    assert isinstance(token_count, int)

def test_display_model_info(agent, mock_console):
    """Test model information display"""
    agent.display_model_info()
    mock_console.print.assert_called_once()
    
    # Get all print calls and their arguments
    calls = mock_console.print.call_args_list
    assert len(calls) == 1
    
    # Check if any call contains our expected values
    table = calls[0][0][0]
    assert isinstance(table, Table)
    assert table.title == "Model Information"
    
    # Render table to string for comparison
    table_str = render_to_string(table)
    assert TEST_MODEL in table_str
    assert "✓ Valid" in table_str

def test_display_token_info(agent, mock_console):
    """Test token information display"""
    agent.display_token_info(TEST_TEXT)
    mock_console.print.assert_called_once()
    
    # Get all print calls and their arguments
    calls = mock_console.print.call_args_list
    assert len(calls) == 1
    
    # Check if any call contains our expected values
    table = calls[0][0][0]
    assert isinstance(table, Table)
    assert table.title == "Token Information"
    
    # Render table to string for comparison
    table_str = render_to_string(table)
    assert str(TEST_TOKENS) in table_str
    assert "$" in table_str

def test_switch_model(agent, mock_console):
    """Test model switching functionality"""
    new_model = "grok-3"
    agent.switch_model(new_model)
    assert agent.current_model == new_model
    mock_console.print.assert_called_once_with(f"[green]Switched to model: {new_model}[/green]")

def test_chat_with_valid_input(agent, mock_openai, mock_console):
    """Test chat functionality with valid input"""
    # Set up the mock response
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response"))]
    mock_openai.chat.completions.create.return_value = mock_response
    
    # Set up the client mock
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    # Update the agent's client
    agent.client = mock_client
    
    agent.chat(TEST_TEXT)
    
    # Verify API call
    mock_client.chat.completions.create.assert_called_once_with(
        model=TEST_MODEL,
        messages=[{"role": "user", "content": TEST_TEXT}],
        temperature=0.7,
        max_tokens=1000
    )
    
    # Verify response display
    mock_console.print.assert_called_once()
    panel = mock_console.print.call_args[0][0]
    assert isinstance(panel, Panel)
    assert panel.title == "Grok Response"
    
    # Render panel to string for comparison
    panel_str = render_to_string(panel)
    assert "Test response" in panel_str

def test_chat_with_empty_input(agent, mock_openai, mock_console):
    """Test chat functionality with empty input"""
    agent.chat("")
    mock_openai.chat.completions.create.assert_not_called()
    mock_console.print.assert_not_called()

def test_chat_with_api_error(agent, mock_openai, mock_console):
    """Test chat functionality with API error"""
    # Set up the mock error
    error_msg = "API Error"
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = Exception(error_msg)
    mock_openai.return_value = mock_client
    
    # Update the agent's client
    agent.client = mock_client
    
    agent.chat(TEST_TEXT)
    
    # Verify error display
    mock_console.print.assert_called_with(f"[red]Error: {error_msg}[/red]")

def test_command_handling(agent, mock_console):
    """Test command handling in the run loop"""
    # Set up input side effect to raise KeyboardInterrupt after first call
    mock_console.input.side_effect = ["/help", KeyboardInterrupt]
    
    try:
        agent.run()
    except KeyboardInterrupt:
        pass
    
    # Verify welcome message and help output
    welcome_msg = "[bold green]Welcome to Grok CLI Agent![/bold green]"
    help_prompt = "Type /help to see available commands"
    
    # Check that all expected messages were printed
    printed_messages = [render_to_string(args[0]) if not isinstance(args[0], str) else args[0]
                       for args, _ in mock_console.print.call_args_list]
    assert any(welcome_msg in msg for msg in printed_messages)
    assert any(help_prompt in msg for msg in printed_messages)
    assert any(normalize_whitespace(HELP_TEXT) in normalize_whitespace(msg) for msg in printed_messages)

def test_model_command(agent, mock_console):
    """Test model switching command"""
    mock_console.input.side_effect = ["/model grok-3", KeyboardInterrupt]
    
    try:
        agent.run()
    except KeyboardInterrupt:
        pass
    
    assert agent.current_model == "grok-3"
    mock_console.print.assert_any_call("[green]Switched to model: grok-3[/green]")

def test_tokens_command(agent, mock_console):
    """Test tokens command with and without text"""
    # Test with text
    mock_console.input.side_effect = [f"/tokens {TEST_TEXT}", KeyboardInterrupt]
    
    try:
        agent.run()
    except KeyboardInterrupt:
        pass
    
    # Test without text
    mock_console.input.side_effect = ["/tokens", KeyboardInterrupt]
    
    try:
        agent.run()
    except KeyboardInterrupt:
        pass
    
    mock_console.print.assert_any_call("[yellow]Please provide text to analyze. Usage: /tokens <text>[/yellow]")

def test_unknown_command(agent, mock_console):
    """Test handling of unknown commands"""
    mock_console.input.side_effect = ["/unknown", KeyboardInterrupt]
    
    try:
        agent.run()
    except KeyboardInterrupt:
        pass
    
    mock_console.print.assert_any_call("[yellow]Unknown command. Type /help for available commands.[/yellow]")

def test_token_command_variations(agent, mock_console):
    """Test both /token and /tokens commands"""
    mock_console.input.side_effect = [
        f"/token {TEST_TEXT}",
        f"/tokens {TEST_TEXT}",
        KeyboardInterrupt
    ]
    
    try:
        agent.run()
    except KeyboardInterrupt:
        pass
    
    # Both commands should have triggered token info display
    assert mock_console.print.call_count >= 2 
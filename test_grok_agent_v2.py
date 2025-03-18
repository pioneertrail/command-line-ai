"""
Tests for the Grok CLI Agent v2 with system command execution and token tracking.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import os
import sys
from grok_agent_simple_v2 import GrokAgent, ALLOWED_COMMANDS

# Windows-specific command paths
WINDOWS_COMMANDS = {
    'dir': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'cmd.exe'),
    'echo': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'cmd.exe'),
    'type': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'cmd.exe'),
    'ipconfig': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'ipconfig.exe'),
    'ping': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'ping.exe'),
    'tracert': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'tracert.exe'),
    'netstat': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'netstat.exe'),
    'systeminfo': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'systeminfo.exe'),
    'ver': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'cmd.exe'),
    'hostname': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'hostname.exe'),
    'whoami': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'whoami.exe'),
    'date': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'cmd.exe'),
    'time': os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'cmd.exe'),
}

def get_command_path(cmd):
    """Get the full path for a command based on the operating system"""
    if sys.platform == 'win32':
        return WINDOWS_COMMANDS.get(cmd, cmd)
    return cmd

@pytest.fixture
def mock_openai():
    """Mock OpenAI client and responses"""
    with patch('grok_agent_simple_v2.OpenAI') as mock:
        client = Mock()
        mock.return_value = client
        
        # Mock chat completion
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(content="Test response"))]
        completion.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        client.chat.completions.create.return_value = completion
        
        yield client

@pytest.fixture
def agent(mock_openai):
    """Create a GrokAgent instance with mocked dependencies"""
    with patch('grok_agent_simple_v2.load_api_key') as mock_key:
        mock_key.return_value = "test_api_key"
        agent = GrokAgent()
        return agent

def test_token_counting(agent):
    """Test token counting functionality"""
    text = "Hello, world!"
    count = agent.count_tokens(text)
    assert count > 0
    assert isinstance(count, int)

def test_token_info_display(agent, capsys):
    """Test token information display"""
    text = "Test text for token counting"
    agent.display_token_info(text)
    captured = capsys.readouterr()
    assert "Token Count" in captured.out
    assert "Estimated Cost" in captured.out
    assert "Text Length" in captured.out

def test_usage_tracking(agent, mock_openai):
    """Test token usage and cost tracking"""
    # Initial state
    assert agent.total_tokens_used == 0
    assert agent.total_cost == 0.0
    
    # Simulate a chat interaction
    agent.chat("Test message")
    
    # Check updated state
    assert agent.total_tokens_used == 30  # From mock completion
    assert agent.total_cost > 0  # Should be calculated based on tokens

def test_usage_display(agent, capsys):
    """Test usage information display"""
    agent.display_usage()
    captured = capsys.readouterr()
    assert "Total Tokens Used" in captured.out
    assert "Total Cost" in captured.out
    assert "Estimated Remaining" in captured.out

def test_allowed_commands():
    """Test that all allowed commands are valid system commands"""
    for cmd in ALLOWED_COMMANDS:
        cmd_path = get_command_path(cmd)
        try:
            if sys.platform == 'win32' and cmd in ['dir', 'echo', 'ver', 'date', 'time', 'type']:
                # For Windows shell commands, we need to use cmd.exe with /c
                subprocess.run([cmd_path, '/c', cmd], capture_output=True, timeout=1)
            else:
                subprocess.run([cmd_path], capture_output=True, timeout=1)
        except FileNotFoundError:
            pytest.fail(f"Command '{cmd}' not found in system")
        except subprocess.TimeoutExpired:
            # Command exists but timed out, which is fine for testing
            pass

def test_command_execution(agent, capsys):
    """Test system command execution"""
    # Test with allowed command
    if sys.platform == 'win32':
        agent.execute_command("echo test")
    else:
        agent.execute_command("echo 'test'")
    captured = capsys.readouterr()
    assert "Command Output" in captured.out or "test" in captured.out
    
    # Test with disallowed command
    agent.execute_command("rm -rf /")
    captured = capsys.readouterr()
    assert "not allowed for security reasons" in captured.out

def test_command_timeout(agent, capsys):
    """Test command execution timeout"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)
        agent.execute_command("ping google.com")
        captured = capsys.readouterr()
        assert "Command timed out" in captured.out

def test_model_switching(agent):
    """Test model switching functionality"""
    new_model = "grok-2-test"
    agent.switch_model(new_model)
    assert agent.current_model == new_model

def test_model_info_display(agent, capsys):
    """Test model information display"""
    agent.display_model_info()
    captured = capsys.readouterr()
    assert "Current Model" in captured.out
    assert "API Key Status" in captured.out
    assert "Price per 1K tokens" in captured.out

def test_help_display(agent, capsys):
    """Test help information display"""
    agent.display_help()
    captured = capsys.readouterr()
    assert "Available Commands" in captured.out
    assert "Allowed System Commands" in captured.out
    for cmd in ALLOWED_COMMANDS:
        assert cmd in captured.out

def test_empty_command_execution(agent, capsys):
    """Test handling of empty command execution"""
    agent.execute_command("")
    captured = capsys.readouterr()
    assert "Please provide a command to execute" in captured.out

def test_invalid_command_execution(agent, capsys):
    """Test handling of invalid command execution"""
    agent.execute_command("invalid_command")
    captured = capsys.readouterr()
    assert "not allowed for security reasons" in captured.out

def test_command_error_handling(agent, capsys):
    """Test error handling in command execution"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Test error")
        agent.execute_command("echo test")
        captured = capsys.readouterr()
        assert "Error executing command" in captured.out

def test_token_info_empty_input(agent, capsys):
    """Test token info display with empty input"""
    agent.display_token_info("")
    captured = capsys.readouterr()
    assert "Please provide text to analyze" in captured.out

def test_chat_empty_input(agent, mock_openai):
    """Test chat with empty input"""
    agent.chat("")
    mock_openai.chat.completions.create.assert_not_called()

def test_exit_command(agent):
    """Test exit command handling"""
    with patch('builtins.input') as mock_input:
        mock_input.side_effect = ["/exit"]
        agent.run()
        # If we get here without error, the test passes
        assert True 
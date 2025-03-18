"""
Benchmark tests for the Grok CLI Agent.

This module contains benchmarks for measuring the performance of key operations
in the Grok agent, including token counting, API calls, and command processing.
"""

import pytest
import time
from grok_agent_simple_v2 import GrokAgent
import os
from unittest.mock import patch, MagicMock
from rich.console import Console
from io import StringIO

# Test data
TEST_API_KEY = "test_api_key_123"
TEST_MODEL = "grok-2-latest"
TEST_TEXT = "Hello, world!"
LONG_TEXT = "This is a longer text for testing performance. " * 100  # ~2000 characters
VERY_LONG_TEXT = "This is a very long text for testing performance. " * 1000  # ~20000 characters

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

def benchmark_token_counting(agent, text, iterations=1000):
    """Benchmark token counting performance"""
    start_time = time.time()
    for _ in range(iterations):
        agent.count_tokens(text)
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / iterations
    return total_time, avg_time

def benchmark_model_switch(agent, iterations=100):
    """Benchmark model switching performance"""
    start_time = time.time()
    for i in range(iterations):
        agent.switch_model(f"grok-{i}")
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / iterations
    return total_time, avg_time

def benchmark_chat_response(agent, text, iterations=10):
    """Benchmark chat response processing"""
    # Set up mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
    
    # Configure the mock client
    agent.client.chat.completions.create = MagicMock(return_value=mock_response)
    
    start_time = time.time()
    for _ in range(iterations):
        agent.chat(text)
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / iterations
    return total_time, avg_time

def benchmark_command_processing(agent, iterations=100):
    """Benchmark command processing performance"""
    commands = [
        "/model grok-3",
        "/tokens Hello world",
        "/info"
    ]
    
    start_time = time.time()
    for _ in range(iterations):
        for cmd in commands:
            if cmd.startswith("/model"):
                agent.switch_model(cmd.split()[1])
            elif cmd.startswith("/tokens"):
                text = " ".join(cmd.split()[1:])
                agent.display_token_info(text)
            elif cmd == "/info":
                agent.display_model_info()
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / (iterations * len(commands))
    return total_time, avg_time

def print_benchmark_results(title, total_time, avg_time, iterations):
    """Print benchmark results in a formatted way"""
    print(f"\n{title}")
    print("-" * 50)
    print(f"Total time: {total_time:.4f} seconds")
    print(f"Average time per iteration: {avg_time:.6f} seconds")
    print(f"Operations per second: {iterations/total_time:.2f}")
    print("-" * 50)

def test_benchmarks(agent):
    """Run all benchmarks and print results"""
    print("\nRunning Grok Agent Benchmarks")
    print("=" * 50)
    
    # Token counting benchmarks
    print("\nToken Counting Benchmarks:")
    print("-" * 50)
    
    # Short text
    total_time, avg_time = benchmark_token_counting(agent, TEST_TEXT)
    print_benchmark_results("Short text (10 chars)", total_time, avg_time, 1000)
    
    # Medium text
    total_time, avg_time = benchmark_token_counting(agent, LONG_TEXT)
    print_benchmark_results("Medium text (2000 chars)", total_time, avg_time, 1000)
    
    # Long text
    total_time, avg_time = benchmark_token_counting(agent, VERY_LONG_TEXT)
    print_benchmark_results("Long text (20000 chars)", total_time, avg_time, 1000)
    
    # Model switching benchmark
    total_time, avg_time = benchmark_model_switch(agent)
    print_benchmark_results("Model Switching", total_time, avg_time, 100)
    
    # Chat response benchmark
    total_time, avg_time = benchmark_chat_response(agent, TEST_TEXT)
    print_benchmark_results("Chat Response Processing", total_time, avg_time, 10)
    
    # Command processing benchmark
    total_time, avg_time = benchmark_command_processing(agent)
    print_benchmark_results("Command Processing", total_time, avg_time, 400)  # 100 iterations * 4 commands 
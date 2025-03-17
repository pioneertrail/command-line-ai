"""
Test suite for the Grok CLI Agent.

This module contains comprehensive tests for all major functionality of the Grok CLI Agent,
including API interactions, message processing, tool handling, and utility functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime
import os
from colorama import Fore, Style

import grok_agent

# Sample API responses for testing
SAMPLE_API_KEY_INFO = {
    "name": "Test Key",
    "create_time": "2024-01-01T00:00:00Z",
    "modify_time": "2024-01-02T00:00:00Z",
    "acls": ["api-key:endpoint:*", "api-key:model:*"],
    "api_key_blocked": False,
    "api_key_disabled": False,
    "team_blocked": False
}

SAMPLE_LANGUAGE_MODELS = {
    "models": [
        {
            "id": "grok-2-latest",
            "version": "1.0.0",
            "owned_by": "xai",
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "prompt_text_token_price": 20000,
            "completion_text_token_price": 100000,
            "aliases": ["grok-2", "grok-2-latest"]
        }
    ]
}

SAMPLE_MESSAGE_RESPONSE = {
    "content": [
        {
            "type": "text",
            "text": "Hello! How can I assist you today?"
        }
    ],
    "tool_calls": [
        {
            "id": "call_123",
            "function": {
                "name": "get_weather",
                "arguments": "{\"location\": \"London\"}"
            }
        }
    ]
}

SAMPLE_TOKENIZE_RESPONSE = {
    "token_ids": [
        {"token_id": 1, "string_token": "Hello"},
        {"token_id": 2, "string_token": "world"}
    ]
}

@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict('os.environ', {'GROK_API_KEY': 'test-api-key'}):
        yield

@pytest.fixture
def mock_requests():
    """Mock HTTP requests."""
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        yield mock_get, mock_post

class TestGrokAgent:
    """Test suite for the Grok CLI Agent."""

    @pytest.mark.api
    def test_make_api_request_get(self, mock_env, mock_requests):
        """Test making GET requests to the API."""
        mock_get, _ = mock_requests
        mock_get.return_value.json.return_value = SAMPLE_API_KEY_INFO
        
        response = grok_agent.make_api_request("GET", "/api-key")
        
        assert response == SAMPLE_API_KEY_INFO
        mock_get.assert_called_once_with(
            "https://api.x.ai/v1/api-key",
            headers={
                "Authorization": "Bearer test-api-key",
                "Content-Type": "application/json"
            }
        )

    @pytest.mark.api
    def test_make_api_request_post(self, mock_env, mock_requests):
        """Test making POST requests to the API."""
        _, mock_post = mock_requests
        mock_post.return_value.json.return_value = SAMPLE_MESSAGE_RESPONSE
        
        data = {"text": "Hello", "model": "grok-2-latest"}
        response = grok_agent.make_api_request("POST", "/tokenize-text", data)
        
        assert response == SAMPLE_MESSAGE_RESPONSE
        mock_post.assert_called_once_with(
            "https://api.x.ai/v1/tokenize-text",
            headers={
                "Authorization": "Bearer test-api-key",
                "Content-Type": "application/json"
            },
            json=data
        )

    @pytest.mark.api
    def test_get_api_key_info(self, mock_env, mock_requests):
        """Test retrieving API key information."""
        mock_get, _ = mock_requests
        mock_get.return_value.json.return_value = SAMPLE_API_KEY_INFO
        
        response = grok_agent.get_api_key_info()
        
        assert response == SAMPLE_API_KEY_INFO
        assert mock_get.call_count == 1

    @pytest.mark.api
    def test_get_language_models(self, mock_env, mock_requests):
        """Test retrieving available language models."""
        mock_get, _ = mock_requests
        mock_get.return_value.json.return_value = SAMPLE_LANGUAGE_MODELS
        
        response = grok_agent.get_language_models()
        
        assert response == SAMPLE_LANGUAGE_MODELS["models"]
        assert mock_get.call_count == 1

    @pytest.mark.api
    def test_tokenize_text(self, mock_env, mock_requests):
        """Test text tokenization."""
        _, mock_post = mock_requests
        mock_post.return_value.json.return_value = SAMPLE_TOKENIZE_RESPONSE
        
        response = grok_agent.tokenize_text("Hello world!", "grok-2-latest")
        
        assert response == SAMPLE_TOKENIZE_RESPONSE
        assert mock_post.call_count == 1

    @pytest.mark.utils
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        timestamp = "2024-01-01T12:55:18.139305Z"
        formatted = grok_agent.format_timestamp(timestamp)
        assert formatted == "2024-01-01 12:55:18 UTC"

    @pytest.mark.utils
    def test_process_grok_response(self):
        """Test response processing."""
        messages = []
        # Mock the tools_map
        with patch.dict(grok_agent.tools_map, {"get_weather": lambda location: {"temp": 20, "condition": "sunny"}}):
            grok_agent.process_grok_response(messages, SAMPLE_MESSAGE_RESPONSE)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "Hello! How can I assist you today?"
        assert messages[1]["role"] == "tool"
        assert messages[1]["tool_call_id"] == "call_123"
        assert json.loads(messages[1]["content"]) == {"temp": 20, "condition": "sunny"}

    @pytest.mark.utils
    def test_paint_text(self):
        """Test text coloring."""
        colored = grok_agent.paint_text("test", Fore.RED)
        assert colored == f"{Fore.RED}test{Style.RESET_ALL}"

    @pytest.mark.utils
    def test_rainbow_text(self):
        """Test rainbow text generation."""
        text = "hello"
        rainbow = grok_agent.rainbow_text(text)
        assert len(rainbow) > len(text)  # Should include color codes
        assert rainbow.endswith(Style.RESET_ALL)

    @pytest.mark.parametrize("model_id,expected", [
        ("grok-2-latest", "grok-2-latest"),
        ("grok-2", "grok-2"),
    ])
    def test_model_switching(self, model_id, expected):
        """Test model switching functionality."""
        with patch('grok_agent.get_model_details') as mock_details:
            mock_details.return_value = {"id": expected}
            info = grok_agent.get_model_details(model_id)
            assert info["id"] == expected

if __name__ == "__main__":
    pytest.main(["-v", "--emoji", "--sugar", "test_grok_agent.py"]) 
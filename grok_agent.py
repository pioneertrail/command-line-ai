"""
Grok CLI Agent - A colorful command-line interface for the Grok API.

This module provides a user-friendly way to interact with the Grok API, offering features like:
- Interactive chat with colorful responses
- Model management and information display
- API key status and information
- Token usage tracking
- Built-in tool support for weather and web search
- Support for both text and image modalities

Usage:
    python grok_agent.py

Environment Variables:
    GROK_API_KEY: Your Grok API key (required)

Commands:
    /model <model_id> - Switch to a different model
    /info - Display current model information
    /key - Display API key information
    /tokens <text> - Show token breakdown
    /exit - Exit the program

Author: Your Name
License: MIT
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from colorama import init, Fore, Style
import time
import json
import requests
from typing import List, Dict, Any
from datetime import datetime

# Initialize colorama for Windows color support
init()

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("GROK_API_KEY")
BASE_URL = "https://api.x.ai/v1"

# Initialize the Grok client
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

def make_api_request(method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
    """Make a request to the Grok API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if hasattr(e.response, 'json'):
            error_data = e.response.json()
            print(paint_text(f"API request error: {error_data.get('error', str(e))}", Fore.RED))
        else:
            print(paint_text(f"API request error: {str(e)}", Fore.RED))
        return {}

def send_message(messages: List[Dict[str, str]], model_id: str, max_tokens: int = 1000) -> Dict[str, Any]:
    """Send a message using the chat completions endpoint"""
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=messages,
            stream=False,
            temperature=0.7,
            max_tokens=max_tokens
        )
        return completion.model_dump()
    except Exception as e:
        print(paint_text(f"Error sending message: {str(e)}", Fore.RED))
        return {}

def get_api_key_info() -> Dict[str, Any]:
    """Get information about the current API key"""
    return make_api_request("GET", "/api-key")

def get_language_models() -> List[Dict[str, Any]]:
    """Get detailed information about available language models"""
    response = make_api_request("GET", "/language-models")
    return response.get("models", [])

def get_model_details(model_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific model"""
    return make_api_request("GET", f"/language-models/{model_id}")

def tokenize_text(text: str, model_id: str) -> Dict[str, Any]:
    """Tokenize text using the specified model"""
    data = {
        "text": text,
        "model": model_id
    }
    return make_api_request("POST", "/tokenize-text", data)

def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp to human readable format"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp

def get_available_models() -> List[Dict[str, Any]]:
    """Get list of available Grok models"""
    try:
        response = client.models.list()
        return [model.model_dump() for model in response.data]
    except Exception as e:
        print(paint_text(f"Error fetching models: {str(e)}", Fore.RED))
        return []

def get_weather(location: str) -> Dict[str, Any]:
    """Get weather information for a location"""
    try:
        # In a real implementation, this would call a weather API
        return {
            "location": location,
            "temperature": 72,
            "conditions": "sunny",
            "unit": "fahrenheit"
        }
    except Exception as e:
        return {"error": str(e)}

def search_web(query: str) -> Dict[str, Any]:
    """Search the web for information"""
    try:
        # In a real implementation, this would use a web search API
        return {
            "query": query,
            "results": ["Sample result 1", "Sample result 2"]
        }
    except Exception as e:
        return {"error": str(e)}

# Define available tools
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# Map function names to their implementations
tools_map = {
    "get_weather": get_weather,
    "search_web": search_web
}

def paint_text(text: str, color: str) -> str:
    """Add color to text"""
    return f"{color}{text}{Style.RESET_ALL}"

def rainbow_text(text: str) -> str:
    """Create rainbow-colored text"""
    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    result = ""
    for i, char in enumerate(text):
        if char.isspace():
            result += char
        else:
            result += f"{colors[i % len(colors)]}{char}"
    return result + Style.RESET_ALL

def process_grok_response(messages: List[Dict[str, str]], response: Dict[str, Any]) -> None:
    """Process Grok's response and handle any tool calls"""
    if not response:
        return
        
    # Extract message from chat completion response
    choices = response.get("choices", [])
    if not choices:
        return
        
    message = choices[0].get("message", {})
    if not message:
        return
        
    content = message.get("content")
    if content:
        messages.append({
            "role": message.get("role", "assistant"),
            "content": content
        })

    # Handle tool calls if present
    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        for tool_call in tool_calls:
            if isinstance(tool_call, dict) and "function" in tool_call:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])
                
                # Call the appropriate function if it exists in tools_map
                if function_name in tools_map:
                    result = tools_map[function_name](**function_args)
                    
                    # Add the result to messages
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call.get("id", "")
                    })

def display_api_key_info() -> None:
    """Display information about the current API key"""
    try:
        key_info = get_api_key_info()
        if key_info:
            print(paint_text("\nAPI Key Information:", Fore.CYAN))
            print(paint_text(f"Name: {key_info.get('name', 'N/A')}", Fore.GREEN))
            print(paint_text(f"Created: {format_timestamp(key_info.get('create_time', 'N/A'))}", Fore.GREEN))
            print(paint_text(f"Last Modified: {format_timestamp(key_info.get('modify_time', 'N/A'))}", Fore.GREEN))
            print(paint_text("Permissions:", Fore.GREEN))
            for acl in key_info.get('acls', []):
                print(paint_text(f"  • {acl}", Fore.YELLOW))
            
            # Display key status
            status = []
            if key_info.get('api_key_blocked'):
                status.append(paint_text("BLOCKED", Fore.RED))
            if key_info.get('api_key_disabled'):
                status.append(paint_text("DISABLED", Fore.RED))
            if key_info.get('team_blocked'):
                status.append(paint_text("TEAM BLOCKED", Fore.RED))
            if not status:
                status.append(paint_text("ACTIVE", Fore.GREEN))
            print(paint_text(f"Status: {' | '.join(status)}", Fore.CYAN))
    except Exception as e:
        print(paint_text(f"Error displaying API key info: {str(e)}", Fore.RED))

def display_model_info(model_id: str) -> None:
    """Display detailed information about the current model"""
    try:
        model_info = get_model_details(model_id)
        if model_info:
            print(paint_text("\nModel Information:", Fore.CYAN))
            print(paint_text(f"ID: {model_info.get('id')}", Fore.GREEN))
            print(paint_text(f"Version: {model_info.get('version', 'N/A')}", Fore.GREEN))
            print(paint_text(f"Owner: {model_info.get('owned_by')}", Fore.GREEN))
            
            # Display modalities
            input_mods = model_info.get('input_modalities', [])
            output_mods = model_info.get('output_modalities', [])
            print(paint_text("Input Modalities: " + ", ".join(input_mods), Fore.YELLOW))
            print(paint_text("Output Modalities: " + ", ".join(output_mods), Fore.YELLOW))
            
            # Display pricing
            print(paint_text("\nPricing (USD cents per million tokens):", Fore.CYAN))
            print(paint_text(f"  • Prompt Text: {model_info.get('prompt_text_token_price', 'N/A')}", Fore.GREEN))
            print(paint_text(f"  • Completion Text: {model_info.get('completion_text_token_price', 'N/A')}", Fore.GREEN))
            if 'image' in input_mods:
                print(paint_text(f"  • Prompt Image: {model_info.get('prompt_image_token_price', 'N/A')}", Fore.GREEN))
            
            # Display aliases
            aliases = model_info.get('aliases', [])
            if aliases:
                print(paint_text("\nAliases:", Fore.CYAN))
                for alias in aliases:
                    print(paint_text(f"  • {alias}", Fore.YELLOW))
    except Exception as e:
        print(paint_text(f"Error displaying model info: {str(e)}", Fore.RED))

def display_usage_info(usage: Dict[str, Any]) -> None:
    """Display detailed usage information"""
    if not usage:
        return
        
    print(paint_text("\nToken Usage:", Fore.CYAN))
    print(paint_text(f"  • Input Tokens: {usage.get('input_tokens', 0)}", Fore.GREEN))
    print(paint_text(f"  • Output Tokens: {usage.get('output_tokens', 0)}", Fore.GREEN))
    print(paint_text(f"  • Cache Creation: {usage.get('cache_creation_input_tokens', 0)}", Fore.GREEN))
    print(paint_text(f"  • Cache Read: {usage.get('cache_read_input_tokens', 0)}", Fore.GREEN))

def main():
    """
    Main interaction loop for the Grok CLI Agent.
    
    This function:
    1. Initializes the agent and displays welcome message
    2. Shows API key information and available models
    3. Enters an interactive loop for user commands and chat
    4. Processes commands and sends messages to Grok
    5. Displays responses with token usage information
    
    Commands:
        /model <model_id> - Switch to a different model
        /info - Display current model information
        /key - Display API key information
        /tokens <text> - Show token breakdown
        /exit - Exit the program
    
    The function handles errors gracefully and provides colorful feedback
    for all operations.
    """
    print(paint_text("╔════════════════════════════════════╗", Fore.CYAN))
    print(paint_text("║  Welcome to the Grok Command Line!  ║", Fore.GREEN))
    print(paint_text("╚════════════════════════════════════╝", Fore.CYAN))

    # Display API key information
    display_api_key_info()

    # Get and display available models with detailed information
    models = get_language_models()
    if models:
        print(paint_text("\nAvailable Models:", Fore.CYAN))
        for model in models:
            model_id = model.get('id')
            version = model.get('version', 'N/A')
            modalities = ', '.join(model.get('input_modalities', []))
            print(paint_text(f"• {model_id} (v{version}) - Supports: {modalities}", Fore.GREEN))
    
    model_id = "grok-2-latest"  # Default model
    display_model_info(model_id)
    
    print(paint_text("\nCommands:", Fore.MAGENTA))
    print(paint_text("  • /model <model_id> - Switch models", Fore.YELLOW))
    print(paint_text("  • /info - Display current model info", Fore.YELLOW))
    print(paint_text("  • /key - Display API key info", Fore.YELLOW))
    print(paint_text("  • /tokens <text> - Show token breakdown", Fore.YELLOW))
    print(paint_text("  • /exit - Exit the program", Fore.YELLOW))
    
    messages = []
    
    while True:
        user_input = input(paint_text("\n> ", Fore.BLUE))
        
        if user_input.lower() in ['exit', 'quit', '/exit']:
            print(paint_text("\nFarewell! May your code be ever elegant!", Fore.YELLOW))
            break
        
        # Handle commands
        if user_input.startswith('/'):
            cmd_parts = user_input.split(maxsplit=1)
            cmd = cmd_parts[0].lower()
            
            if cmd == '/model' and len(cmd_parts) > 1:
                new_model = cmd_parts[1]
                try:
                    display_model_info(new_model)
                    model_id = new_model
                    print(paint_text(f"\nSwitched to model: {model_id}", Fore.GREEN))
                except Exception as e:
                    print(paint_text(f"\nError switching model: {str(e)}", Fore.RED))
                continue
            elif cmd == '/info':
                display_model_info(model_id)
                continue
            elif cmd == '/key':
                display_api_key_info()
                continue
            elif cmd == '/tokens' and len(cmd_parts) > 1:
                text = cmd_parts[1]
                tokens = tokenize_text(text, model_id)
                if tokens and 'token_ids' in tokens:
                    print(paint_text("\nToken Breakdown:", Fore.CYAN))
                    for token in tokens['token_ids']:
                        print(paint_text(f"  • {token['string_token']} (ID: {token['token_id']})", Fore.GREEN))
                continue

        messages.append({"role": "user", "content": user_input})

        try:
            print(paint_text("\n🤔 Consulting Grok...", Fore.YELLOW))
            
            # Use the chat completions endpoint
            response = send_message(messages, model_id)
            
            if response:
                process_grok_response(messages, response)
                
                # Display usage information
                if 'usage' in response:
                    display_usage_info(response['usage'])
                
                # Display the response
                choices = response.get('choices', [])
                if choices:
                    message = choices[0].get('message', {})
                    content = message.get('content', '')
                    if content:
                        print(f"\n{paint_text('Grok:', Fore.GREEN)} {rainbow_text(content)}\n")
                
                # Display finish reason if available
                finish_reason = choices[0].get('finish_reason') if choices else None
                if finish_reason:
                    print(paint_text(f"Finish reason: {finish_reason}", Fore.CYAN))

        except Exception as e:
            print(paint_text(f"\n❌ Error: {str(e)}", Fore.RED))

if __name__ == "__main__":
    main() 
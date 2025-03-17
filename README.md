# Grok CLI Agent

A colorful command-line interface for interacting with the Grok API. This agent provides a user-friendly way to chat with Grok, manage models, and utilize various API features.

## Features

- 🌈 Colorful interface with rainbow text responses
- 🤖 Interactive chat with Grok AI
- 📊 Real-time token usage tracking
- 🔄 Model switching and information display
- 🔑 API key management and status display
- 🛠️ Built-in tool support (weather, web search)
- 🎨 Support for both text and image modalities

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/grok-cli-agent.git
cd grok-cli-agent
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file with your Grok API key:
```
GROK_API_KEY=your-api-key-here
```

## Usage

Run the agent:
```bash
python grok_agent.py
```

### Available Commands

- `/model <model_id>` - Switch to a different model
- `/info` - Display information about the current model
- `/key` - Display information about your API key
- `/tokens <text>` - Show how a text would be tokenized
- `/exit` - Exit the program

### Chat Example

```
> Tell me a joke

🤔 Consulting Grok...

Grok: Why don't programmers like nature? It has too many bugs!

Token Usage:
  • Input Tokens: 4
  • Output Tokens: 12
  • Cache Creation: 0
  • Cache Read: 0
```

## Development

### Running Tests

```bash
pytest test_grok_agent.py -v
```

### Project Structure

- `grok_agent.py` - Main agent implementation
- `test_grok_agent.py` - Test suite
- `requirements.txt` - Project dependencies
- `.env` - API key configuration
- `pytest.ini` - Test configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - See LICENSE file for details 
# Grok CLI Agent (Simplified)

A streamlined command-line interface for interacting with the Grok API. This simplified version focuses on core functionality while maintaining a user-friendly experience.

## Features

- Interactive chat with the Grok API
- Model management and information display
- Token counting and cost estimation
- Clean, colorful command-line interface

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements_simple.txt
   ```
4. Create a `.env` file in the project root with your Grok API key:
   ```
   GROK_API_KEY=your_api_key_here
   ```

## Usage

Run the agent:
```bash
python grok_agent_simple.py
```

### Available Commands

- `/model <model_id>` - Switch to a different model
- `/info` - Display current model information
- `/tokens <text>` - Show token breakdown
- `/help` - Show available commands
- `/exit` - Exit the program

## Requirements

- Python 3.7+
- Grok API key
- See `requirements_simple.txt` for Python package dependencies

## License

MIT 
# Grok CLI Agent

A powerful command-line interface agent powered by the Grok API, designed to help users execute system commands and perform web searches efficiently.

## Features

- 🤖 Natural language command processing
- 🔒 Secure command execution with safety checks
- 🌐 Web search capabilities using DuckDuckGo
- 💻 System information and monitoring
- 🔑 Admin privilege management
- 📝 Command history and session management
- ⚙️ Configurable settings
- 📊 Token usage tracking and cost monitoring

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/grok-cli-agent.git
cd grok-cli-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements_simple.txt
```

4. Create a `.env` file in the project root and add your Grok API key:
```
GROK_API_KEY=your_api_key_here
```

## Usage

Run the agent:
```bash
python grok_agent_simple_v2.py
```

### Available Commands

#### System Commands
- `ipconfig` - Display network configuration
- `ping` - Test network connectivity
- `tracert` - Trace network routes
- `netstat` - Show network statistics
- `systeminfo` - Display system information
- `ver` - Show Windows version
- `hostname` - Display computer name
- `whoami` - Show current user
- `dir` - List directory contents
- `type` - Display file contents
- `echo` - Output text
- `date` - Show current date
- `time` - Show current time

#### Special Commands
- `/help` - Show help information
- `/exit` - Exit the program
- `/model <model_id>` - Switch models
- `/info` - Show model information
- `/key` - Show API key info
- `/tokens <text>` - Show token breakdown
- `/usage` - Show usage statistics
- `/exec <command>` - Execute a system command
- `/request admin` - Request admin privileges
- `/history` - Show command history
- `/config` - Show configuration
- `/clear history` - Clear command history

## Security Features

- Command validation and safety checks
- Admin privilege management
- Secure API key handling
- Logging and error tracking
- Safe command execution with path validation

## Configuration

The agent can be configured through the following methods:
- Environment variables
- Configuration file
- Command-line arguments

## Dependencies

- openai>=1.0.0
- python-dotenv>=1.0.0
- rich>=13.0.0
- tiktoken>=0.5.0
- requests>=2.31.0
- beautifulsoup4>=4.12.0
- pywin32>=306 (Windows only)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Grok API for providing the underlying AI capabilities
- OpenAI for the API client implementation
- Rich library for beautiful terminal output 
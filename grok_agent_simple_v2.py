"""
Grok CLI Agent - A simplified command-line interface for the Grok API.

This module provides essential functionality to interact with the Grok API:
- Interactive chat with colorful responses
- Model management and information display
- API key status and information
- Token usage tracking
- System command execution (with safety checks)
- Web-based command learning

Usage:
    python grok_agent_simple_v2.py

Environment Variables:
    GROK_API_KEY: Your Grok API key (required)

Commands:
    /model <model_id> - Switch to a different model
    /info - Display current model information
    /key - Display API key information
    /tokens <text> - Show token breakdown
    /usage - Display token usage and cost information
    /exec <command> - Execute a system command (with safety checks)
    /exit - Exit the program
"""

import os
import sys
import subprocess
import re
from typing import Optional, List, Dict, Tuple
import logging
import json
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import tiktoken
from dotenv import load_dotenv
import ctypes
import win32com.shell.shell as shell
import time

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI package not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()

# List of allowed commands (for safety)
ALLOWED_COMMANDS = {
    'ipconfig', 'ping', 'tracert', 'netstat', 'dir', 'type', 'echo',
    'systeminfo', 'ver', 'hostname', 'whoami', 'date', 'time'
}

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

def load_api_key() -> Optional[str]:
    """Load the API key from environment variables"""
    try:
        load_dotenv()
        api_key = os.getenv("GROK_API_KEY")
        if not api_key:
            logger.error("GROK_API_KEY environment variable not set")
            return None
        logger.debug("API key loaded successfully")
        return api_key
    except Exception as e:
        logger.error(f"Error loading API key: {str(e)}")
        return None

class CommandInfo:
    def __init__(self, name: str, description: str, syntax: str, examples: List[str], parameters: List[str] = [], tips: List[str] = []):
        self.name = name
        self.description = description
        self.syntax = syntax
        self.examples = examples
        self.parameters = parameters
        self.tips = tips

class GrokAgent:
    def __init__(self):
        self.api_key = load_api_key()
        if not self.api_key:
            raise ValueError("API key not found. Please set GROK_API_KEY environment variable.")
        
        # Check for admin privileges
        self.is_admin = self.check_admin_privileges()
        if not self.is_admin:
            logger.warning("Agent is not running with admin privileges. Some features may be limited.")
        
        # Configure OpenAI client for Grok API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"  # Correct Grok API endpoint
        )
        self.current_model = "grok-2-latest"  # Updated default model
        self.conversation_history = [
            {
                "role": "system",
                "content": """You are a command-line assistant agent that helps users execute system commands and search the web on their behalf. 
                Your primary responsibilities are:
                1. Understanding user requests in natural language
                2. Converting these requests into appropriate system commands or web searches
                3. Executing commands safely and securely
                4. Processing and formatting command outputs in a user-friendly way
                5. Searching the web when system commands can't provide the needed information
                
                You have access to:
                - System commands (ipconfig, ping, tracert, netstat, systeminfo, ver, hostname, whoami, dir, type, echo)
                - Web search capabilities (using DuckDuckGo API)
                
                Always prioritize:
                - Command Execution: Try to execute a command for ANY user request that could be answered with system information
                - Web Search: Use web search when system commands can't provide the needed information
                - Security: Only execute allowed commands
                - Clarity: Explain what you're doing
                - Helpfulness: Guide users to the right commands
                - Safety: Never execute potentially harmful commands
                
                When users ask questions:
                1. ALWAYS first try to find a command that could answer their question
                2. If no exact command exists, try to combine or modify existing commands
                3. If no command can answer the question, use web search
                4. Only fall back to general chat if no command or web search could help"""
            }
        ]
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.price_per_1k_tokens = 0.0003  # $0.0003 per 1K tokens for Grok-2
        
        # Command learning and caching
        self.command_cache: Dict[str, CommandInfo] = {}
        self.learning_mode = True  # Enable command learning by default
        
        # Enhanced command patterns with web search capabilities
        self.command_patterns = {
            'ipconfig': [
                'what is my ip', 'show my ip', 'display ip', 'network config',
                'show network', 'ip address', 'network address', 'my network',
                'network settings', 'connection info', 'internet settings',
                'wifi info', 'ethernet info', 'network adapter'
            ],
            'systeminfo': [
                'system info', 'computer info', 'pc info', 'hardware info',
                'show system', 'about my computer', 'system details',
                'computer specs', 'hardware specs', 'system configuration',
                'computer details', 'pc details', 'system hardware'
            ],
            'whoami': [
                'who am i', 'current user', 'my username', 'logged in as',
                'show user', 'user name', 'my account', 'current account',
                'user account', 'login info', 'account name'
            ],
            'hostname': [
                'computer name', 'machine name', 'host name', 'pc name',
                'what is my computer called', 'system name', 'computer id',
                'machine id', 'pc identifier', 'computer identifier'
            ],
            'dir': [
                'show files', 'list files', 'show directory', 'list directory',
                'what files are here', 'show folder contents', 'folder contents',
                'directory contents', 'list folder', 'show folder', 'files here',
                'what is in this folder', 'folder files', 'directory files'
            ],
            'ping': [
                'test connection', 'check connection', 'ping test',
                'can i reach', 'network test', 'test network', 'check network',
                'test internet', 'check internet', 'test website',
                'check website', 'test server', 'check server',
                'test if online', 'check if online', 'test connectivity'
            ],
            'tracert': [
                'trace route', 'show route', 'network path',
                'how does traffic get to', 'trace path', 'show path',
                'network trace', 'route trace', 'trace network',
                'show network path', 'trace internet path',
                'how data travels', 'data path', 'connection path'
            ],
            'netstat': [
                'network status', 'show connections', 'active connections',
                'network statistics', 'port usage', 'network ports',
                'active ports', 'connection status', 'network activity',
                'port status', 'connection list', 'network connections',
                'active network', 'port connections'
            ],
            'ver': [
                'windows version', 'os version', 'system version',
                'what version', 'which windows', 'windows info',
                'os info', 'system info', 'version info',
                'windows details', 'os details', 'system details'
            ],
            'date': [
                'what date', 'current date', 'today date',
                'show date', 'what day is it', 'today',
                'current day', 'what day', 'date today',
                'show today', 'what is today', 'today\'s date'
            ],
            'time': [
                'what time', 'current time', 'show time',
                'tell me the time', 'what is the time',
                'current hour', 'what hour', 'time now',
                'show current time', 'what is now', 'current moment'
            ],
            'help': [
                'how do i use', 'what does', 'explain command', 'command help',
                'usage of', 'syntax for', 'examples of', 'how to use',
                'help with', 'explain how', 'show how', 'guide me',
                'tell me about', 'what is', 'how does', 'can you explain'
            ],
            'search': [
                'search for command', 'find command', 'lookup command',
                'what command', 'is there a command', 'command to',
                'how to', 'what can i use', 'which command',
                'find a way to', 'how can i', 'what should i use',
                'looking for command', 'need command', 'want to'
            ],
            'web_search': [
                'search for', 'look up', 'find information about', 'what is',
                'tell me about', 'search online', 'look online', 'find online',
                'web search', 'internet search', 'search the web', 'search internet',
                'find out about', 'learn about', 'get information about',
                'search duckduckgo', 'duckduckgo search', 'search duck duck go',
                'what do you know about', 'tell me more about', 'search for information',
                'find details about', 'get details about', 'search details about'
            ]
        }
        self.command_history = []
        self.max_history = 100  # Maximum number of commands to keep in history
        self.session_file = "grok_session.json"
        self.config_file = "grok_config.json"
        self.config = self.load_config()
        self.load_session()
        self.last_error = None
        self.error_count = 0

    def check_admin_privileges(self) -> bool:
        """Check if the agent has admin privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

    def request_admin_privileges(self) -> bool:
        """Request admin privileges for the agent"""
        try:
            if self.is_admin:
                return True
                
            if sys.platform != 'win32':
                logger.error("Admin privileges are only supported on Windows")
                return False

            # Get the script path and interpreter
            script = os.path.abspath(sys.argv[0])
            interpreter = sys.executable
            
            try:
                # Try to elevate privileges
                result = shell.ShellExecuteEx(
                    lpVerb='runas',
                    lpFile=interpreter,
                    lpParameters=f'"{script}"',
                    nShow=1
                )
                
                # If successful, exit the current non-elevated process
                if result['hInstApp'] > 32:
                    logger.info("Successfully requested admin privileges. Restarting with elevation...")
                    sys.exit(0)  # Exit current process, letting elevated one take over
                    
                logger.error("Failed to get admin privileges")
                return False
                
            except Exception as e:
                logger.error(f"Error during privilege elevation: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error requesting admin privileges: {str(e)}")
            return False

    def web_search(self, query: str) -> List[Dict[str, str]]:
        """
        Perform a web search using DuckDuckGo API
        Returns a list of search results with title, snippet, and URL
        """
        try:
            # Format the query for DuckDuckGo
            formatted_query = query.replace(' ', '+')
            url = f"https://api.duckduckgo.com/?q={formatted_query}&format=json"
            
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # Extract abstract if available
                if data.get('Abstract'):
                    results.append({
                        'title': data['Heading'],
                        'snippet': data['Abstract'],
                        'url': data['AbstractURL'],
                        'source': 'DuckDuckGo'
                    })
                
                # Extract related topics
                for topic in data.get('RelatedTopics', [])[:5]:
                    if 'Text' in topic and 'FirstURL' in topic:
                        results.append({
                            'title': topic['Text'].split(' - ')[0],
                            'snippet': topic['Text'],
                            'url': topic['FirstURL'],
                            'source': 'DuckDuckGo'
                        })
                
                return results
            else:
                logging.error(f"Web search failed with status code: {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"Error during web search: {str(e)}")
            return []

    def learn_command(self, command: str) -> Optional[CommandInfo]:
        """Learn about a command by searching multiple sources"""
        try:
            # Search queries for different aspects
            queries = [
                f"windows {command} command usage examples microsoft docs",
                f"how to use {command} command line tutorial",
                f"{command} command syntax parameters options",
                f"{command} command examples best practices"
            ]
            
            all_results = []
            for query in queries:
                results = self.web_search(query)
                all_results.extend(results)
            
            # Extract command information from search results
            description = ""
            syntax = ""
            examples = []
            parameters = []
            tips = []

            for result in all_results[:5]:  # Check top 5 results
                try:
                    response = requests.get(result['url'], timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for command description
                        desc_elements = soup.find_all(['p', 'div'], class_=['description', 'summary', 'content'])
                        if desc_elements:
                            description = desc_elements[0].get_text().strip()
                        
                        # Look for command syntax
                        syntax_elements = soup.find_all(['pre', 'code'], class_=['syntax', 'command-line', 'example'])
                        if syntax_elements:
                            syntax = syntax_elements[0].get_text().strip()
                        
                        # Look for examples
                        example_elements = soup.find_all(['pre', 'code'], class_=['example', 'sample', 'command'])
                        for elem in example_elements[:3]:
                            examples.append(elem.get_text().strip())
                        
                        # Look for parameters
                        param_elements = soup.find_all(['li', 'p'], class_=['parameter', 'option'])
                        for elem in param_elements:
                            param_text = elem.get_text().strip()
                            if param_text.startswith('/') or param_text.startswith('-'):
                                parameters.append(param_text)
                        
                        # Look for tips
                        tip_elements = soup.find_all(['div', 'p'], class_=['tip', 'note', 'warning'])
                        for elem in tip_elements:
                            tips.append(elem.get_text().strip())
                        
                        if description and syntax:
                            break
                except Exception as e:
                    logger.warning(f"Error fetching command info: {str(e)}")
                    continue

            if description:
                cmd_info = CommandInfo(
                    name=command,
                    description=description,
                    syntax=syntax,
                    examples=examples,
                    parameters=parameters,
                    tips=tips
                )
                # Cache the command info
                self.command_cache[command] = cmd_info
                return cmd_info
            
            return None
        except Exception as e:
            logger.error(f"Error learning command: {str(e)}")
            return None

    def get_command_help(self, command: str) -> str:
        """Get detailed help for a command, learning from the web if needed"""
        # Check cache first
        if command in self.command_cache:
            cmd_info = self.command_cache[command]
        elif self.learning_mode:
            # Try to learn about the command
            cmd_info = self.learn_command(command)
            if not cmd_info:
                return f"Sorry, I couldn't find information about the '{command}' command."
        else:
            return f"No help available for '{command}' command."

        # Format the help information
        help_text = f"""
[bold]Command:[/bold] {cmd_info.name}

[bold]Description:[/bold]
{cmd_info.description}

[bold]Syntax:[/bold]
{cmd_info.syntax}
"""
        if cmd_info.examples:
            help_text += "\n[bold]Examples:[/bold]"
            for i, example in enumerate(cmd_info.examples, 1):
                help_text += f"\n{i}. {example}"

        return help_text

    def process_command_output(self, command: str, output: str) -> str:
        """Process command output into a natural language response with enhanced intelligence"""
        try:
            # Extract relevant information based on command type
            if command == 'ipconfig':
                # Extract IPv4 Address and other network info
                network_info = {}
                current_adapter = None
                for line in output.splitlines():
                    if 'Ethernet adapter' in line or 'Wireless' in line:
                        current_adapter = line.split(':')[0].strip()
                        network_info[current_adapter] = {}
                    elif current_adapter and 'IPv4 Address' in line:
                        network_info[current_adapter]['ip'] = line.split(':')[1].strip()
                    elif current_adapter and 'Physical Address' in line:
                        network_info[current_adapter]['mac'] = line.split(':')[1].strip()
                
                # Format response
                response = "Your network information:\n"
                for adapter, info in network_info.items():
                    response += f"\n{adapter}:\n"
                    if 'ip' in info:
                        response += f"  IP Address: {info['ip']}\n"
                    if 'mac' in info:
                        response += f"  MAC Address: {info['mac']}\n"
                return response

            elif command == 'systeminfo':
                # Extract key system information
                system_info = {}
                for line in output.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        system_info[key.strip()] = value.strip()
                
                # Format response
                response = "Your system information:\n"
                important_fields = ['OS Name', 'OS Version', 'System Type', 'Total Physical Memory', 'Available Physical Memory']
                for field in important_fields:
                    if field in system_info:
                        response += f"\n{field}: {system_info[field]}"
                return response

            elif command == 'netstat':
                # Process network connections
                connections = []
                for line in output.splitlines():
                    if 'TCP' in line or 'UDP' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            protocol = parts[0]
                            local = parts[1]
                            remote = parts[2]
                            state = parts[3] if len(parts) > 3 else 'N/A'
                            connections.append({
                                'protocol': protocol,
                                'local': local,
                                'remote': remote,
                                'state': state
                            })
                
                # Format response
                response = "Active network connections:\n"
                for conn in connections:
                    response += f"\n{conn['protocol']} {conn['local']} -> {conn['remote']} ({conn['state']})"
                return response

            elif command == 'ping':
                # Process ping results
                lines = output.splitlines()
                if len(lines) >= 2:
                    target = lines[0].split()[-1].strip('[]')
                    stats = lines[-2:]
                    response = f"Ping results for {target}:\n"
                    response += "\n".join(stats)
                    return response
                return output

            elif command == 'tracert':
                # Process traceroute results
                lines = output.splitlines()
                if len(lines) >= 2:
                    target = lines[0].split()[-1].strip('[]')
                    hops = [line for line in lines[1:] if line.strip()]
                    response = f"Route to {target}:\n"
                    for hop in hops:
                        response += f"\n{hop}"
                    return response
                return output

            elif command == 'dir':
                # Process directory listing
                files = []
                dirs = []
                for line in output.splitlines():
                    if line.strip():
                        if '<DIR>' in line:
                            dirs.append(line)
                        else:
                            files.append(line)
                
                # Format response
                response = "Directory contents:\n"
                if dirs:
                    response += "\nDirectories:\n" + "\n".join(dirs)
                if files:
                    response += "\n\nFiles:\n" + "\n".join(files)
                return response

            elif command == 'whoami':
                return f"You are logged in as {output.strip()}"

            elif command == 'hostname':
                return f"Your computer's name is {output.strip()}"

            elif command == 'ver':
                return f"You are running {output.strip()}"

            elif command == 'date':
                return f"Current date: {output.strip()}"

            elif command == 'time':
                return f"Current time: {output.strip()}"

            # Default case: return formatted output
            return f"Command output:\n{output}"

        except Exception as e:
            logger.error(f"Error processing command output: {str(e)}")
            return output

    def detect_command_intent(self, user_input: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Enhanced command intent detection with web search support
        Returns: (intent, command, args) or (None, None, None)
        """
        user_input = user_input.lower().strip()
        
        # Check for web search intent first
        if any(pattern in user_input for pattern in self.command_patterns['web_search']):
            # Extract the search query
            search_query = user_input
            for pattern in self.command_patterns['web_search']:
                if pattern in user_input:
                    search_query = user_input.split(pattern)[-1].strip()
                    break
            return 'web_search', None, search_query
        
        # Check for help/search intents
        if any(pattern in user_input for pattern in self.command_patterns['help']):
            # Extract the command name after help patterns
            for cmd in ALLOWED_COMMANDS:
                if cmd in user_input:
                    return 'help', cmd, None
        
        if any(pattern in user_input for pattern in self.command_patterns['search']):
            # Try to extract what kind of command they're looking for
            search_query = user_input
            for pattern in self.command_patterns['search']:
                search_query = search_query.replace(pattern, '').strip()
            return 'search', None, search_query
        
        # Check for command patterns with fuzzy matching
        for cmd, patterns in self.command_patterns.items():
            if cmd not in ['help', 'search', 'web_search']:  # Skip help, search, and web_search patterns
                # Check for exact pattern matches
                for pattern in patterns:
                    if pattern in user_input:
                        # Extract arguments based on command type
                        args = None
                        if cmd == 'ping':
                            # Look for website, server, or domain names
                            if 'can i reach' in user_input:
                                args = user_input.split('can i reach')[-1].strip()
                            elif 'test' in user_input or 'check' in user_input:
                                # Extract the target after 'test' or 'check'
                                parts = user_input.split()
                                for i, part in enumerate(parts):
                                    if part in ['test', 'check'] and i + 1 < len(parts):
                                        args = parts[i + 1].strip()
                                        break
                        elif cmd == 'tracert':
                            # Look for destination after various phrases
                            for phrase in ['how does traffic get to', 'trace path to', 'show path to']:
                                if phrase in user_input:
                                    args = user_input.split(phrase)[-1].strip()
                                    break
                        elif cmd == 'dir':
                            # Look for directory path after various phrases
                            for phrase in ['show files in', 'list files in', 'what is in']:
                                if phrase in user_input:
                                    args = user_input.split(phrase)[-1].strip()
                                    break
                        return 'execute', cmd, args
                
                # Check for semantic similarity
                words = set(user_input.split())
                for pattern in patterns:
                    pattern_words = set(pattern.split())
                    # If more than 50% of the pattern words are in the input
                    if len(pattern_words.intersection(words)) / len(pattern_words) > 0.5:
                        # Extract arguments based on command type
                        args = None
                        if cmd == 'ping':
                            # Look for website, server, or domain names
                            if 'can i reach' in user_input:
                                args = user_input.split('can i reach')[-1].strip()
                            elif 'test' in user_input or 'check' in user_input:
                                parts = user_input.split()
                                for i, part in enumerate(parts):
                                    if part in ['test', 'check'] and i + 1 < len(parts):
                                        args = parts[i + 1].strip()
                                        break
                        elif cmd == 'tracert':
                            for phrase in ['how does traffic get to', 'trace path to', 'show path to']:
                                if phrase in user_input:
                                    args = user_input.split(phrase)[-1].strip()
                                    break
                        elif cmd == 'dir':
                            for phrase in ['show files in', 'list files in', 'what is in']:
                                if phrase in user_input:
                                    args = user_input.split(phrase)[-1].strip()
                                    break
                        return 'execute', cmd, args
        
        # Check for direct command usage
        for cmd in ALLOWED_COMMANDS:
            if user_input.startswith(cmd):
                args = user_input[len(cmd):].strip()
                return 'execute', cmd, args if args else None
        
        return None, None, None

    def retry_with_backoff(self, func, *args, **kwargs):
        """Execute a function with exponential backoff retry"""
        max_attempts = self.config['retry_attempts']
        base_delay = self.config['retry_delay']
        
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.last_error = str(e)
                self.error_count += 1
                
                if attempt == max_attempts - 1:
                    console.print(f"[red]Failed after {max_attempts} attempts. Last error: {self.last_error}[/red]")
                    raise
                    
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                console.print(f"[yellow]Attempt {attempt + 1} failed. Retrying in {delay} seconds...[/yellow]")
                time.sleep(delay)
                
    def initialize_client(self):
        """Initialize the OpenAI client with retry mechanism"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
                
            self.client = self.retry_with_backoff(
                OpenAI,
                api_key=api_key,
                timeout=self.config['api_timeout']
            )
            console.print("[green]Client initialized successfully[/green]")
        except Exception as e:
            console.print(f"[red]Failed to initialize client: {str(e)}[/red]")
            raise
            
    def get_grok_response(self, user_input: str) -> str:
        """Get response from Grok with retry mechanism"""
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Get response with retry
            response = self.retry_with_backoff(
                self.client.chat.completions.create,
                model=self.current_model,
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract and store the response
            grok_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": grok_response})
            
            # Save session if auto-save is enabled
            if self.config['auto_save']:
                self.save_session()
                
            return grok_response
            
        except Exception as e:
            console.print(f"[red]Error getting Grok response: {str(e)}[/red]")
            return f"I apologize, but I encountered an error: {str(e)}"
            
    def execute_command(self, command: str) -> Optional[str]:
        """Execute a system command safely with retry mechanism"""
        try:
            # Add command to history
            self.add_to_history(command)
            
            # Check for config commands
            if command.lower().startswith("config"):
                parts = command.split()
                if len(parts) == 1:
                    self.show_config()
                elif len(parts) == 3 and parts[1] == "set":
                    self.update_config(parts[2], parts[3])
                return
                
            # Check for history commands
            if command.lower() == "history":
                self.show_history()
                return
            elif command.lower() == "clear history":
                self.clear_history()
                return
                
            # Split command into parts
            cmd_parts = command.split()
            if not cmd_parts:
                return "Please provide a command to execute"
                
            # Get the base command (first word)
            base_cmd = cmd_parts[0].lower()
            
            # Check if command is allowed
            if base_cmd not in ALLOWED_COMMANDS:
                return f"Sorry, the command '{base_cmd}' is not allowed for security reasons. Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
                
            # Check if command requires admin privileges
            admin_required_commands = {'netstat', 'systeminfo', 'ipconfig'}
            if base_cmd in admin_required_commands and not self.is_admin:
                if not self.request_admin_privileges():
                    return f"Command '{base_cmd}' requires admin privileges. Please run the agent as administrator."
                    
            # Get the full command path
            cmd_path = get_command_path(base_cmd)
            
            # Prepare command arguments
            if sys.platform == 'win32' and base_cmd in ['dir', 'echo', 'ver', 'date', 'time', 'type']:
                args = [cmd_path, '/c'] + cmd_parts[1:]
            else:
                args = [cmd_path] + cmd_parts[1:]
                
            # Execute the command with retry
            result = self.retry_with_backoff(
                subprocess.run,
                args,
                capture_output=True,
                text=True,
                shell=False,
                timeout=self.config['api_timeout']
            )
            
            # Reset error count on successful execution
            self.error_count = 0
            self.last_error = None
            
            return result.stdout if result.stdout else result.stderr
            
        except subprocess.TimeoutExpired:
            return f"Command timed out after {self.config['api_timeout']} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def chat(self, user_input: str):
        """Process user input and generate a response"""
        try:
            # First, check for command intents
            intent, cmd, args = self.detect_command_intent(user_input)
            
            if intent == 'web_search':
                search_query = args if args else user_input
                console.print(f"[cyan]I'll search the web for information about '{search_query}'...[/cyan]")
                results = self.web_search(search_query)
                
                if results:
                    console.print("\n[bold]Here's what I found:[/bold]")
                    for result in results[:3]:  # Show top 3 results
                        console.print(f"\n[cyan]{result['title']}[/cyan]")
                        console.print(result['snippet'])
                        console.print(f"[dim]Source: {result['source']} - {result['url']}[/dim]")
                else:
                    console.print("[yellow]No relevant information found.[/yellow]")
                return
            
            elif intent == 'help':
                if cmd:
                    help_text = self.get_command_help(cmd)
                    console.print(Panel(help_text, title=f"Help: {cmd}", border_style="blue"))
                else:
                    self.display_help()
                return
            
            elif intent == 'search':
                search_query = args if args else user_input
                results = self.web_search(f"windows command line {search_query}")
                if results:
                    console.print("\n[bold]Found these potentially helpful commands:[/bold]")
                    for result in results[:3]:
                        console.print(f"\n[cyan]{result['title']}[/cyan]")
                        console.print(result['snippet'])
                        console.print(f"[dim]Source: {result['source']} - {result['url']}[/dim]")
                else:
                    console.print("[yellow]No relevant commands found.[/yellow]")
                return
            
            elif intent == 'execute':
                if cmd in ALLOWED_COMMANDS:
                    # Explain what we're going to do
                    console.print(f"[cyan]I'll execute the {cmd} command for you...[/cyan]")
                    output = self.execute_command(command)
                    if output:
                        processed_output = self.process_command_output(cmd, output)
                        console.print(processed_output)
                    return
            
            # If no command intent detected, process as chat
            messages = self.conversation_history + [{"role": "user", "content": user_input}]
            
            try:
                completion = self.client.chat.completions.create(
                    model=self.current_model,
                    messages=messages
                )
                
                if completion.choices:
                    response = completion.choices[0].message.content
                    self.conversation_history.extend([
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": response}
                    ])
                    
                    # Update token usage
                    self.update_usage(completion)
                    
                    # Display the response
                    console.print(Panel(response, border_style="green"))
                else:
                    console.print("[red]No response received from the model.[/red]")
                    
            except Exception as e:
                console.print(f"[red]Error during chat completion: {str(e)}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error processing input: {str(e)}[/red]")

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string"""
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    
    def update_usage(self, completion):
        """Update token usage and cost tracking"""
        if hasattr(completion, 'usage'):
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens
            total_tokens = prompt_tokens + completion_tokens
            
            self.total_tokens_used += total_tokens
            cost = (total_tokens / 1000) * self.price_per_1k_tokens
            self.total_cost += cost

    def display_usage(self):
        """Display current token usage and cost information"""
        table = Table(title="Token Usage Information")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Tokens Used", f"{self.total_tokens_used:,}")
        table.add_row("Cost per 1K tokens", f"${self.price_per_1k_tokens:.4f}")
        table.add_row("Total Cost", f"${self.total_cost:.4f}")
        table.add_row("Estimated Remaining*", f"${5.00 - self.total_cost:.4f}")
        
        console.print(table)
        console.print("\n[dim]* Based on a $5.00 budget[/dim]")
    
    def display_model_info(self):
        """Display information about the current model"""
        table = Table(title="Model Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Current Model", self.current_model)
        table.add_row("API Key Status", "✓ Valid" if self.api_key else "✗ Invalid")
        table.add_row("Price per 1K tokens", f"${self.price_per_1k_tokens:.4f}")
        
        console.print(table)
    
    def display_token_info(self, text: str):
        """Display token information for given text"""
        if not text:
            console.print("[yellow]Please provide text to analyze. Usage: /tokens <text>[/yellow]")
            return
        
        token_count = self.count_tokens(text)
        estimated_cost = (token_count / 1000) * self.price_per_1k_tokens
        
        table = Table(title="Token Information")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Text Length", str(len(text)))
        table.add_row("Token Count", str(token_count))
        table.add_row("Estimated Cost", f"${estimated_cost:.6f}")
        
        console.print(table)
    
    def switch_model(self, model_id: str):
        """Switch to a different model"""
        self.current_model = model_id
        console.print(f"[green]Switched to model: {model_id}[/green]")
    
    def run(self):
        """Run the interactive chat loop"""
        console.print("[bold green]Welcome to the Grok CLI Agent![/bold green]")
        if not self.is_admin:
            console.print("[yellow]Note: Some features may be limited without admin privileges.[/yellow]")
            console.print("[yellow]Use '/request admin' to elevate privileges.[/yellow]")
        console.print("Type [bold]/help[/bold] for available commands or just chat naturally!")
        
        while True:
            try:
                user_input = console.input("\n[bold blue]>[/bold blue] ")
                
                if not user_input.strip():
                    continue
                    
                if user_input.lower() == '/exit':
                    self.display_usage()
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                    
                elif user_input.startswith('/'):
                    command = user_input[1:].strip()
                    
                    if command == 'help':
                        self.display_help()
                    elif command == 'request admin':
                        if self.request_admin_privileges():
                            console.print("[green]Successfully requested admin privileges! The agent will restart.[/green]")
                            return  # Exit the loop to allow restart
                        else:
                            console.print("[red]Failed to request admin privileges.[/red]")
                    elif command.startswith('model '):
                        model_id = command[6:].strip()
                        self.switch_model(model_id)
                    elif command == 'info':
                        self.display_model_info()
                    elif command.startswith('tokens '):
                        text = command[7:].strip()
                        self.display_token_info(text)
                    elif command == 'usage':
                        self.display_usage()
                    elif command.startswith('exec '):
                        cmd = command[5:].strip()
                        if any(cmd.startswith(allowed) for allowed in ALLOWED_COMMANDS):
                            output = self.execute_command(cmd)
                            if output:
                                console.print(output)
                        else:
                            console.print(f"[red]Command not allowed: {cmd}[/red]")
                    else:
                        console.print("[red]Unknown command. Type /help for available commands.[/red]")
                        
                else:
                    self.chat(user_input)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
        
        # Display final usage when exiting
        console.print("\n[bold]Final Usage Summary:[/bold]")
        self.display_usage()

    def display_help(self):
        """Display available commands with categories and descriptions"""
        # Define command categories
        categories = {
            "Network Commands": {
                "ipconfig": "Display network configuration (requires admin)",
                "ping": "Test network connectivity",
                "tracert": "Trace network route",
                "netstat": "Show network connections (requires admin)"
            },
            "System Information": {
                "systeminfo": "Display system information (requires admin)",
                "ver": "Show Windows version",
                "hostname": "Display computer name",
                "whoami": "Show current user"
            },
            "File System": {
                "dir": "List directory contents",
                "type": "Display file contents",
                "echo": "Display text or create files"
            },
            "Time and Date": {
                "date": "Show current date",
                "time": "Show current time"
            },
            "Grok Commands": {
                "model": "Switch to a different model",
                "info": "Display current model information",
                "tokens": "Show token breakdown",
                "usage": "Display token usage and cost information",
                "exec": "Execute a system command (with safety checks)",
                "help": "Show this help message",
                "exit": "Exit the program"
            },
            "Admin Commands": {
                "request admin": "Request administrator privileges",
                "help": "Show this help message",
                "exit": "Exit the program"
            }
        }

        # Create help text with categories
        help_text = "[bold]Available Commands by Category:[/bold]\n"
        
        for category, commands in categories.items():
            help_text += f"\n[bold cyan]{category}:[/bold cyan]"
            for cmd, desc in commands.items():
                help_text += f"\n  /{cmd:<12} - {desc}"
            
            # Add natural language examples for system commands
            if category != "Grok Commands":
                help_text += "\n\n  Natural Language Examples:"
                for cmd in commands:
                    if cmd in self.command_patterns:
                        examples = self.command_patterns[cmd][:2]  # Show first 2 examples
                        help_text += f"\n    • {examples[0]}"
                        if len(examples) > 1:
                            help_text += f"\n    • {examples[1]}"
                help_text += "\n"

        help_text += "\n[bold]Note:[/bold] You can use commands in natural language or with the / prefix."
        console.print(Panel(help_text, title="Command Help", border_style="yellow"))

    def load_session(self):
        """Load previous session data if available"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.conversation_history = data.get('conversation_history', [])
                    self.command_history = data.get('command_history', [])
                    self.current_model = data.get('current_model', "grok-1")
                console.print("[green]Session loaded successfully[/green]")
        except Exception as e:
            console.print(f"[red]Error loading session: {str(e)}[/red]")
            
    def save_session(self):
        """Save current session data"""
        try:
            data = {
                'conversation_history': self.conversation_history[-10:],  # Keep last 10 conversations
                'command_history': self.command_history,
                'current_model': self.current_model
            }
            with open(self.session_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            console.print(f"[red]Error saving session: {str(e)}[/red]")
            
    def add_to_history(self, command):
        """Add command to history"""
        self.command_history.append(command)
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
        self.save_session()
        
    def show_history(self):
        """Display command history"""
        if not self.command_history:
            console.print("[yellow]No command history available[/yellow]")
            return
            
        console.print("\n[bold cyan]Command History:[/bold cyan]")
        for i, cmd in enumerate(self.command_history, 1):
            console.print(f"{i}. {cmd}")
            
    def clear_history(self):
        """Clear command history"""
        self.command_history = []
        self.save_session()
        console.print("[green]Command history cleared[/green]")

    def load_config(self):
        """Load configuration from file or create default"""
        default_config = {
            "max_history": 100,
            "max_conversations": 10,
            "retry_attempts": 3,
            "retry_delay": 1,
            "api_timeout": 30,
            "log_level": "INFO",
            "theme": "default",
            "auto_save": True,
            "safe_mode": True
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all settings exist
                    return {**default_config, **config}
            else:
                # Create default config file
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            console.print(f"[red]Error loading config: {str(e)}[/red]")
            return default_config
            
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            console.print("[green]Configuration saved successfully[/green]")
        except Exception as e:
            console.print(f"[red]Error saving config: {str(e)}[/red]")
            
    def update_config(self, key, value):
        """Update a configuration setting"""
        if key in self.config:
            self.config[key] = value
            self.save_config()
            console.print(f"[green]Configuration updated: {key} = {value}[/green]")
        else:
            console.print(f"[red]Invalid configuration key: {key}[/red]")
            
    def show_config(self):
        """Display current configuration"""
        console.print("\n[bold cyan]Current Configuration:[/bold cyan]")
        for key, value in self.config.items():
            console.print(f"{key}: {value}")

    def show_help(self):
        """Display help information"""
        help_text = """
[bold cyan]Grok CLI Agent Help[/bold cyan]

[bold green]Basic Commands:[/bold green]
• help - Show this help message
• exit - Exit the program
• clear - Clear the screen
• model - Show current model or switch models
• tokens - Show token usage information

[bold green]System Commands:[/bold green]
• dir - List directory contents
• type - Display file contents
• echo - Display text
• ver - Show Windows version
• date - Show current date
• time - Show current time
• hostname - Show computer name
• whoami - Show current user
• systeminfo - Show system information
• ipconfig - Show network configuration
• ping - Test network connectivity
• tracert - Trace network route
• netstat - Show network statistics

[bold green]History Commands:[/bold green]
• history - Show command history
• clear history - Clear command history

[bold green]Configuration Commands:[/bold green]
• config - Show current configuration
• config set <key> <value> - Update configuration setting

[bold green]Security Commands:[/bold green]
• check admin - Check admin privileges
• request admin - Request admin privileges

[bold yellow]Notes:[/bold yellow]
• Some commands require admin privileges
• Command history is automatically saved
• Configuration changes are persistent
• Auto-retry is enabled for failed operations
• Session data is automatically saved

[bold red]Security Warning:[/bold red]
• Only use allowed commands
• Admin privileges are required for some operations
• Safe mode is enabled by default
"""
        console.print(Panel(help_text, title="Command Help", border_style="yellow"))

if __name__ == "__main__":
    try:
        # Configure logging to file
        log_file = 'grok_agent.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        logger.debug("Starting Grok Agent...")
        logger.debug(f"Python version: {sys.version}")
        logger.debug(f"Platform: {sys.platform}")
        logger.debug(f"Working directory: {os.getcwd()}")
        
        # Check for admin status before creating agent
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        logger.debug(f"Running with admin privileges: {is_admin}")
        
        # Initialize agent
        agent = GrokAgent()
        logger.debug("Agent initialized successfully")
        
        # Run the agent
        agent.run()
        
    except ImportError as e:
        error_msg = f"Missing required package: {str(e)}"
        logger.error(error_msg)
        console.print(f"[red]{error_msg}[/red]")
        console.print("[yellow]Try running: pip install -r requirements_simple.txt[/yellow]")
        
    except PermissionError as e:
        error_msg = f"Permission denied: {str(e)}"
        logger.error(error_msg)
        console.print(f"[red]{error_msg}[/red]")
        console.print("[yellow]Try running the agent with administrator privileges.[/yellow]")
        
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[red]{error_msg}[/red]")
        console.print("[yellow]Check grok_agent.log for more details.[/yellow]") 
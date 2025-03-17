"""
Grok CLI Agent - A colorful command-line interface for the Grok API.

This module provides a user-friendly way to interact with the Grok API, offering features like:
- Interactive chat with colorful responses
- Model management and information display
- API key status and information
- Token usage tracking
- Built-in tool support for weather and web search
- Support for both text and image modalities
- Tool discovery and documentation
- Computer management capabilities
- Network traffic monitoring
- System performance metrics
- Advanced system management and optimization
- System health monitoring and diagnostics
- System repair and maintenance tools
- File cleanup and management

Usage:
    python grok_agent.py

Environment Variables:
    GROK_API_KEY: Your Grok API key (required)

Commands:
    /model <model_id> - Switch to a different model
    /info - Display current model information
    /key - Display API key information
    /tokens <text> - Show token breakdown
    /tools - Display available tools and their capabilities
    /system - Show system information and health
    /optimize - Run system optimization
    /repair - Run system repair tools
    /recommendations - Get system improvement recommendations
    /programs - List uninstallable programs and background processes
    /cleanup [days] [paths...] - Clean up unused files
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
import psutil
import platform
import subprocess
import socket
import netifaces
from typing import List, Dict, Any, Optional
from datetime import datetime
from system_management import SystemManager
import cmd
import sys
import logging
import colorama
import argparse
import httpx
import tiktoken
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
import shutil
import glob
import ctypes
from pathlib import Path

# Initialize colorama for Windows color support
init()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()

def load_api_key() -> Optional[str]:
    """Load the API key from environment variables"""
    api_key = os.getenv("GROK_API_KEY")
    if not api_key:
        logger.error("GROK_API_KEY environment variable not set")
        return None
    return api_key

# Define available tools and their capabilities
tools_definition = {
    "system": {
        "description": "System information and health check",
        "capabilities": [
            "CPU usage monitoring",
            "Memory usage tracking",
            "Disk space analysis",
            "Network status",
            "System uptime"
        ]
    },
    "optimize": {
        "description": "System optimization tools",
        "capabilities": [
            "Memory optimization",
            "Disk cleanup",
            "Startup program management",
            "Service optimization",
            "Registry cleanup"
        ]
    },
    "repair": {
        "description": "System repair utilities",
        "capabilities": [
            "File system check",
            "System file verification",
            "DLL registration",
            "Windows Update repair",
            "Network reset"
        ]
    },
    "recommendations": {
        "description": "System improvement recommendations",
        "capabilities": [
            "Performance analysis",
            "Security recommendations",
            "Storage optimization",
            "Update recommendations",
            "Hardware upgrade suggestions"
        ]
    },
    "cleanup": {
        "description": "File cleanup utilities",
        "capabilities": [
            "Temporary file removal",
            "Download folder cleanup",
            "Recycle bin emptying",
            "Windows Update cache cleanup",
            "Browser cache cleanup"
        ]
    }
}

def paint_text(text: str, color: str) -> str:
    """Apply color to text and reset it after"""
    return f"{color}{text}{Style.RESET_ALL}"

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

# Initialize system manager
system_manager = SystemManager()

# Global variables
current_model = "grok-2-latest"  # Default model

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
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'json'):
            error_data = e.response.json()
            error_msg = error_data.get('error', str(e))
        print(paint_text(f"API request error: {error_msg}", Fore.RED))
        return {"error": error_msg}
    except Exception as e:
        error_msg = str(e)
        print(paint_text(f"API request error: {error_msg}", Fore.RED))
        return {"error": error_msg}

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
        logger.debug(f"Raw completion object: {completion}")
        logger.debug(f"Completion type: {type(completion)}")
        logger.debug(f"Completion dir: {dir(completion)}")
        
        # Convert the response to a dictionary
        response_dict = {
            "choices": [{
                "message": {
                    "content": completion.choices[0].message.content,
                    "role": completion.choices[0].message.role
                }
            }],
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }
        }
        logger.debug(f"Converted response: {response_dict}")
        return response_dict
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}", exc_info=True)
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
    if not location:
        return {"error": "Location cannot be empty"}
        
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

def get_system_info() -> Dict[str, Any]:
    """Get system information including CPU, memory, and disk usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "system": platform.system(),
            "platform": platform.platform(),
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
        }
    except Exception as e:
        return {"error": str(e)}

def list_processes(query: str = "") -> Dict[str, Any]:
    """List running processes, optionally filtered by query"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if not query or query.lower() in proc.info['name'].lower():
                    processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {"processes": processes}
    except Exception as e:
        return {"error": str(e)}

def kill_process(pid: int) -> Dict[str, Any]:
    """Kill a process by its PID"""
    try:
        process = psutil.Process(pid)
        process.terminate()
        return {"status": "success", "message": f"Process {pid} terminated"}
    except psutil.NoSuchProcess:
        return {"error": f"Process {pid} not found"}
    except psutil.AccessDenied:
        return {"error": f"Access denied to process {pid}"}
    except Exception as e:
        return {"error": str(e)}

def list_directory(path: str = ".") -> Dict[str, Any]:
    """List contents of a directory"""
    try:
        items = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            try:
                stat = os.stat(full_path)
                items.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(full_path) else "file",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception:
                continue
        return {"items": items}
    except Exception as e:
        return {"error": str(e)}

def execute_command(command: str) -> Dict[str, Any]:
    """Execute a system command and return its output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except Exception as e:
        return {"error": str(e)}

def get_network_info() -> Dict[str, Any]:
    """Get detailed network interface information"""
    try:
        network_info = {
            "interfaces": [],
            "connections": [],
            "io_counters": {}
        }
        
        # Get network interfaces
        for iface in netifaces.interfaces():
            try:
                addrs = netifaces.ifaddresses(iface)
                iface_info = {
                    "name": iface,
                    "addresses": [],
                    "stats": psutil.net_if_stats().get(iface, {})
                }
                
                # Get IP addresses
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        iface_info["addresses"].append({
                            "ip": addr.get("addr"),
                            "netmask": addr.get("netmask"),
                            "broadcast": addr.get("broadcast")
                        })
                
                network_info["interfaces"].append(iface_info)
            except Exception:
                continue
        
        # Get active connections
        for conn in psutil.net_connections(kind='inet'):
            try:
                connection = {
                    "local_ip": conn.laddr.ip if conn.laddr else None,
                    "local_port": conn.laddr.port if conn.laddr else None,
                    "remote_ip": conn.raddr.ip if conn.raddr else None,
                    "remote_port": conn.raddr.port if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid
                }
                network_info["connections"].append(connection)
            except Exception:
                continue
        
        # Get IO counters
        io_counters = psutil.net_io_counters(pernic=True)
        for nic, counters in io_counters.items():
            network_info["io_counters"][nic] = {
                "bytes_sent": counters.bytes_sent,
                "bytes_recv": counters.bytes_recv,
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errors_in": counters.errin,
                "errors_out": counters.errout,
                "drops_in": counters.dropin,
                "drops_out": counters.dropout
            }
        
        return network_info
    except Exception as e:
        return {"error": str(e)}

def get_performance_metrics(interval: int = 1) -> Dict[str, Any]:
    """Get detailed system performance metrics"""
    try:
        # Get initial measurements
        cpu_percent_start = psutil.cpu_percent(interval=None, percpu=True)
        io_counters_start = psutil.disk_io_counters()
        net_io_start = psutil.net_io_counters()
        
        # Wait for interval
        time.sleep(interval)
        
        # Get end measurements
        cpu_percent_end = psutil.cpu_percent(interval=None, percpu=True)
        io_counters_end = psutil.disk_io_counters()
        net_io_end = psutil.net_io_counters()
        
        # Calculate rates
        disk_read_speed = (io_counters_end.read_bytes - io_counters_start.read_bytes) / interval
        disk_write_speed = (io_counters_end.write_bytes - io_counters_start.write_bytes) / interval
        net_send_speed = (net_io_end.bytes_sent - net_io_start.bytes_sent) / interval
        net_recv_speed = (net_io_end.bytes_recv - net_io_start.bytes_recv) / interval
        
        return {
            "cpu": {
                "per_cpu_percent": cpu_percent_end,
                "total_percent": sum(cpu_percent_end) / len(cpu_percent_end),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "stats": {
                    "ctx_switches": psutil.cpu_stats().ctx_switches,
                    "interrupts": psutil.cpu_stats().interrupts,
                    "soft_interrupts": psutil.cpu_stats().soft_interrupts,
                    "syscalls": psutil.cpu_stats().syscalls
                }
            },
            "memory": {
                "virtual": psutil.virtual_memory()._asdict(),
                "swap": psutil.swap_memory()._asdict()
            },
            "disk": {
                "io_counters": {
                    "read_speed": disk_read_speed,
                    "write_speed": disk_write_speed,
                    "read_count": io_counters_end.read_count,
                    "write_count": io_counters_end.write_count,
                    "read_time": io_counters_end.read_time,
                    "write_time": io_counters_end.write_time
                },
                "partitions": [p._asdict() for p in psutil.disk_partitions()],
                "usage": {p.mountpoint: psutil.disk_usage(p.mountpoint)._asdict() 
                         for p in psutil.disk_partitions(all=False)}
            },
            "network": {
                "io_counters": {
                    "bytes_sent_speed": net_send_speed,
                    "bytes_recv_speed": net_recv_speed,
                    "packets_sent": net_io_end.packets_sent,
                    "packets_recv": net_io_end.packets_recv,
                    "errors_in": net_io_end.errin,
                    "errors_out": net_io_end.errout
                }
            }
        }
    except Exception as e:
        return {"error": str(e)}

def monitor_network_traffic(duration: int = 10, interval: float = 1.0) -> Dict[str, Any]:
    """Monitor network traffic for a specified duration"""
    try:
        samples = []
        start_time = time.time()
        last_io = psutil.net_io_counters()
        
        while time.time() - start_time < duration:
            time.sleep(interval)
            current_io = psutil.net_io_counters()
            
            # Calculate rates
            bytes_sent = current_io.bytes_sent - last_io.bytes_sent
            bytes_recv = current_io.bytes_recv - last_io.bytes_recv
            packets_sent = current_io.packets_sent - last_io.packets_sent
            packets_recv = current_io.packets_recv - last_io.packets_recv
            
            samples.append({
                "timestamp": time.time(),
                "bytes_sent_per_sec": bytes_sent / interval,
                "bytes_recv_per_sec": bytes_recv / interval,
                "packets_sent_per_sec": packets_sent / interval,
                "packets_recv_per_sec": packets_recv / interval,
                "errors_in": current_io.errin,
                "errors_out": current_io.errout
            })
            
            last_io = current_io
        
        # Calculate averages
        num_samples = len(samples)
        avg_bytes_sent = sum(s["bytes_sent_per_sec"] for s in samples) / num_samples
        avg_bytes_recv = sum(s["bytes_recv_per_sec"] for s in samples) / num_samples
        avg_packets_sent = sum(s["packets_sent_per_sec"] for s in samples) / num_samples
        avg_packets_recv = sum(s["packets_recv_per_sec"] for s in samples) / num_samples
        
        return {
            "duration": duration,
            "interval": interval,
            "samples": samples,
            "averages": {
                "bytes_sent_per_sec": avg_bytes_sent,
                "bytes_recv_per_sec": avg_bytes_recv,
                "packets_sent_per_sec": avg_packets_sent,
                "packets_recv_per_sec": avg_packets_recv
            }
        }
    except Exception as e:
        return {"error": str(e)}

def get_system_management_info() -> Dict[str, Any]:
    """Get comprehensive system management information"""
    try:
        return {
            "system_info": system_manager.get_detailed_system_info(),
            "health": system_manager.get_system_health()
        }
    except Exception as e:
        return {"error": str(e)}

def optimize_system() -> Dict[str, Any]:
    """Run system optimization tasks"""
    try:
        return system_manager.optimize_system()
    except Exception as e:
        return {"error": str(e)}

def repair_system() -> Dict[str, Any]:
    """Run system repair tasks"""
    try:
        return system_manager.repair_system()
    except Exception as e:
        return {"error": str(e)}

def display_system_info(info: Dict[str, Any]) -> None:
    """Display system information in a formatted way"""
    if "error" in info:
        print(paint_text(f"Error: {info['error']}", Fore.RED))
        return

    print(paint_text("\nSystem Information", Fore.CYAN))
    print("=" * 50)

    # Basic Info
    print(paint_text("\nBasic Information:", Fore.YELLOW))
    basic = info["system_info"]["basic"]
    print(f"System: {basic['system']}")
    print(f"Platform: {basic['platform']}")
    print(f"Machine: {basic['machine']}")
    print(f"Processor: {basic['processor']}")
    print(f"Python Version: {basic['python_version']}")

    # CPU Info
    print(paint_text("\nCPU Information:", Fore.YELLOW))
    cpu = info["system_info"]["cpu"]
    print(f"Name: {cpu['name']}")
    print(f"Cores: {cpu['cores']}")
    print(f"Threads: {cpu['threads']}")
    print(f"Max Speed: {cpu['max_speed']} MHz")

    # Memory Info
    print(paint_text("\nMemory Information:", Fore.YELLOW))
    memory = info["system_info"]["memory"]
    print(f"Total: {memory['total'] / (1024**3):.2f} GB")
    print(f"Speed: {memory['speed']} MHz")
    print(f"Type: {memory['type']}")

    # Disk Info
    print(paint_text("\nDisk Information:", Fore.YELLOW))
    for disk in info["system_info"]["disks"]:
        print(f"\nDevice: {disk['device_id']}")
        print(f"Size: {int(disk['size']) / (1024**3):.2f} GB")
        print(f"Free Space: {int(disk['free_space']) / (1024**3):.2f} GB")
        print(f"File System: {disk['file_system']}")

    # Network Info
    print(paint_text("\nNetwork Information:", Fore.YELLOW))
    for adapter in info["system_info"]["network"]:
        print(f"\nName: {adapter['name']}")
        print(f"Type: {adapter['adapter_type']}")
        print(f"MAC: {adapter['mac_address']}")
        print(f"Speed: {adapter['speed']} Mbps")

    # Health Status
    print(paint_text("\nSystem Health:", Fore.YELLOW))
    health = info["health"]
    
    # CPU Health
    cpu_health = health["cpu_health"]
    print(f"\nCPU Load: {cpu_health['load']}%")
    if cpu_health.get("temperature"):
        print(f"Temperature: {cpu_health['temperature']}°C")
    
    # Memory Health
    mem_health = health["memory_health"]
    print(f"\nMemory Usage: {mem_health['percent']}%")
    print(f"Available: {mem_health['available'] / (1024**3):.2f} GB")
    
    # Disk Health
    print("\nDisk Health:")
    for disk in health["disk_health"]["disks"]:
        print(f"\n{disk['device']}:")
        print(f"Usage: {disk['percent']}%")
        print(f"Free: {disk['free'] / (1024**3):.2f} GB")
    
    # Network Health
    print("\nNetwork Health:")
    for interface in health["network_health"]["interfaces"]:
        print(f"\n{interface['interface']}:")
        print(f"Status: {'Up' if interface['is_up'] else 'Down'}")
        print(f"Speed: {interface['speed']} Mbps")
        print(f"MTU: {interface['mtu']}")

    # System Errors
    if health["system_errors"]["errors"]:
        print(paint_text("\nRecent System Errors:", Fore.RED))
        for error in health["system_errors"]["errors"][:5]:  # Show last 5 errors
            print(f"\nTime: {error['time']}")
            print(f"Source: {error['source']}")
            print(f"Event ID: {error['event_id']}")
            print(f"Description: {error['description']}")

def display_optimization_results(results: Dict[str, Any]) -> None:
    """Display system optimization results"""
    if "error" in results:
        print(paint_text(f"Error: {results['error']}", Fore.RED))
        return

    print(paint_text("\nSystem Optimization Results", Fore.CYAN))
    print("=" * 50)

    for task, result in results.items():
        print(paint_text(f"\n{task.replace('_', ' ').title()}:", Fore.YELLOW))
        if "error" in result:
            print(paint_text(f"Error: {result['error']}", Fore.RED))
        else:
            print(f"Status: {result['status']}")
            if "message" in result:
                print(f"Message: {result['message']}")
            if "files_cleaned" in result:
                print(f"Files Cleaned: {result['files_cleaned']}")
            if "services_optimized" in result:
                print(f"Services Optimized: {result['services_optimized']}")

def display_repair_results(results: Dict[str, Any]) -> None:
    """Display system repair results"""
    if "error" in results:
        print(paint_text(f"Error: {results['error']}", Fore.RED))
        return

    print(paint_text("\nSystem Repair Results", Fore.CYAN))
    print("=" * 50)

    for task, result in results.items():
        print(paint_text(f"\n{task.replace('_', ' ').title()}:", Fore.YELLOW))
        if "error" in result:
            print(paint_text(f"Error: {result['error']}", Fore.RED))
        else:
            print(f"Status: {result['status']}")
            if "message" in result:
                print(f"Message: {result['message']}")
            if "services_repaired" in result:
                print(f"Services Repaired: {result['services_repaired']}")

def display_usage_info(usage: Dict[str, Any]) -> None:
    """Display token usage information"""
    print(paint_text("\nToken Usage:", Fore.CYAN))
    print(paint_text(f"  • Input Tokens: {usage.get('prompt_tokens', 0)}", Fore.GREEN))
    print(paint_text(f"  • Output Tokens: {usage.get('completion_tokens', 0)}", Fore.GREEN))
    print(paint_text(f"  • Total Tokens: {usage.get('total_tokens', 0)}", Fore.GREEN))

def display_available_models() -> None:
    """Display information about available models."""
    try:
        models = get_language_models()
        print(f"\n{Fore.CYAN}Available Models:{Style.RESET_ALL}")
        for model in models:
            print(f"\n{Fore.GREEN}• {model['id']}{Style.RESET_ALL}")
            print(f"  Description: {model.get('description', 'N/A')}")
            print(f"  Input Modalities: {', '.join(model.get('input_modalities', ['text']))}")
            print(f"  Output Modalities: {', '.join(model.get('output_modalities', ['text']))}")
            print(f"  Max Tokens: {model.get('max_tokens', 'N/A')}")
        print()
    except Exception as e:
        print(f"{Fore.RED}Error fetching models: {str(e)}{Style.RESET_ALL}")

def switch_model(model_id: str) -> bool:
    """Switch to a different model"""
    global current_model
    
    # Get available models
    models = get_language_models()
    available_models = [model["id"] for model in models]
    
    if model_id not in available_models:
        print(paint_text(f"Error: Model {model_id} not found", Fore.RED))
        return False
        
    current_model = model_id
    print(paint_text(f"Switched to model: {model_id}", Fore.GREEN))
    return True

def display_tools() -> None:
    """Display available tools and their capabilities"""
    table = Table(title="Available Tools", box=box.ROUNDED)
    table.add_column("Tool", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Capabilities", style="yellow")

    for tool_name, tool_info in tools_definition.items():
        capabilities = "\n".join(f"• {cap}" for cap in tool_info["capabilities"])
        table.add_row(
            tool_name,
            tool_info["description"],
            capabilities
        )

    console.print(table)

def process_grok_response(messages: list, response: dict) -> None:
    """Process and display the Grok API response"""
    try:
        if response and "choices" in response and len(response["choices"]) > 0:
            message = response["choices"][0]["message"]
            if "content" in message:
                print(paint_text("\nGrok: ", Fore.GREEN) + message["content"])
                # Add assistant's response to message history
                messages.append({"role": "assistant", "content": message["content"]})
        
        if "usage" in response:
            usage = response["usage"]
            print(paint_text("\nToken Usage:", Fore.MAGENTA))
            print(paint_text(f"  • Input Tokens: {usage['prompt_tokens']}", Fore.MAGENTA))
            print(paint_text(f"  • Output Tokens: {usage['completion_tokens']}", Fore.MAGENTA))
            print(paint_text(f"  • Total Tokens: {usage['total_tokens']}", Fore.MAGENTA))
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        print(paint_text(f"\nError processing response: {str(e)}", Fore.RED))

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
    """Display detailed information about a model"""
    models = get_language_models()
    model_info = next((model for model in models if model["id"] == model_id), None)
    
    print(paint_text("\nModel Information:", Fore.CYAN))
    if model_info:
        print(paint_text(f"ID: {model_info.get('id')}", Fore.GREEN))
        print(paint_text(f"Version: {model_info.get('version', 'N/A')}", Fore.GREEN))
        print(paint_text(f"Owner: {model_info.get('owned_by', 'N/A')}", Fore.GREEN))
        
        # Display modalities
        print(paint_text(f"Input Modalities: {', '.join(model_info.get('input_modalities', []))}", Fore.YELLOW))
        print(paint_text(f"Output Modalities: {', '.join(model_info.get('output_modalities', []))}", Fore.YELLOW))
        
        # Display pricing information
        print(paint_text("\nPricing (USD cents per million tokens):", Fore.CYAN))
        print(paint_text(f"  • Prompt Text: {model_info.get('prompt_text_token_price', 'N/A')}", Fore.GREEN))
        print(paint_text(f"  • Completion Text: {model_info.get('completion_text_token_price', 'N/A')}", Fore.GREEN))
    else:
        print(paint_text("Model not found", Fore.RED))

def cleanup_files(days: int = 30, paths: List[str] = None) -> Dict[str, Any]:
    """Clean up unused files"""
    try:
        return system_manager.cleanup_unused_files(paths, days)
    except Exception as e:
        return {"error": str(e)}

def display_cleanup_results(results: Dict[str, Any]) -> None:
    """Display cleanup results in a formatted table"""
    if "error" in results:
        console.print(f"[red]Error: {results['error']}[/red]")
        return

    table = Table(title="Cleanup Results", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Details", style="green")

    # Add summary rows
    table.add_row("Files Cleaned", str(len(results.get("cleaned_files", []))))
    table.add_row("Total Space Freed", format_size(results.get("total_size_cleaned", 0)))
    
    # Add detailed lists with truncation
    cleaned_files = results.get("cleaned_files", [])
    protected_files = results.get("protected_files", [])
    skipped_files = results.get("skipped_files", [])
    errors = results.get("errors", [])

    # Truncate long lists
    if len(cleaned_files) > 10:
        cleaned_files = cleaned_files[:10] + [f"... and {len(cleaned_files) - 10} more files"]
    if len(protected_files) > 10:
        protected_files = protected_files[:10] + [f"... and {len(protected_files) - 10} more protected files"]
    if len(skipped_files) > 10:
        skipped_files = skipped_files[:10] + [f"... and {len(skipped_files) - 10} more skipped files"]

    # Add detailed sections
    if cleaned_files:
        table.add_row("Cleaned Files", "\n".join(cleaned_files))
    if protected_files:
        table.add_row("Protected Files (Skipped)", "\n".join(protected_files))
    if skipped_files:
        table.add_row("System Files (Skipped)", "\n".join(skipped_files))
    if errors:
        table.add_row("Errors Encountered", "\n".join(errors))

    console.print(table)

def format_size(size: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def display_recommendations(recommendations: Dict[str, Any]) -> None:
    """Display system improvement recommendations"""
    if "error" in recommendations:
        print(paint_text(f"Error: {recommendations['error']}", Fore.RED))
        return

    print(paint_text("\nSystem Improvement Recommendations", Fore.CYAN))
    print("=" * 50)

    # Color mapping for recommendation levels
    level_colors = {
        "high": Fore.RED,
        "medium": Fore.YELLOW,
        "low": Fore.GREEN
    }

    # Display recommendations by category
    for category, items in recommendations.items():
        if items:  # Only show categories with recommendations
            print(paint_text(f"\n{Fore.YELLOW}{category.title()} Recommendations:{Style.RESET_ALL}", Fore.MAGENTA))
            for item in items:
                level = item.get("level", "medium")
                color = level_colors.get(level, Fore.WHITE)
                
                print(paint_text(f"\n• {item['message']}", color))
                print(paint_text(f"  Action: {item['action']}", Fore.CYAN))
                
                if "details" in item:
                    print(paint_text("  Details:", Fore.CYAN))
                    for detail in item["details"][:5]:  # Show first 5 details
                        print(f"    - {detail['name']} (PID: {detail['pid']}, CPU: {detail['cpu_percent']}%)")

def process_command(command: str) -> None:
    """Process user commands"""
    global current_model
    
    if command.startswith("/model "):
        model_id = command[7:].strip()
        if switch_model(model_id):
            print(paint_text(f"Switched to model: {model_id}", Fore.GREEN))
        else:
            print(paint_text(f"Failed to switch to model: {model_id}", Fore.RED))
    
    elif command == "/info":
        display_model_info(current_model)
    
    elif command == "/key":
        display_api_key_info()
    
    elif command.startswith("/tokens "):
        text = command[8:].strip()
        usage = tokenize_text(text, current_model)
        display_usage_info(usage)
    
    elif command == "/tools":
        display_tools()
    
    elif command == "/system":
        info = get_system_management_info()
        display_system_info(info)
    
    elif command == "/optimize":
        print(paint_text("\nRunning system optimization...", Fore.YELLOW))
        results = optimize_system()
        display_optimization_results(results)
    
    elif command == "/repair":
        print(paint_text("\nRunning system repair...", Fore.YELLOW))
        results = repair_system()
        display_repair_results(results)
    
    elif command == "/recommendations":
        print(paint_text("\nAnalyzing system for recommendations...", Fore.YELLOW))
        recommendations = system_manager.get_system_recommendations()
        display_recommendations(recommendations)
    
    elif command.startswith("/cleanup"):
        args = command[8:].strip().split()
        days = 30  # Default value
        paths = []
        
        if args:
            try:
                days = int(args[0])
                paths = args[1:]
            except ValueError:
                paths = args
        
        if not paths:
            paths = ["."]  # Default to current directory
        
        print(paint_text(f"\nCleaning up files older than {days} days...", Fore.YELLOW))
        results = system_manager.cleanup_unused_files(days=days, paths=paths)
        display_cleanup_results(results)
    
    elif command == "/exit":
        print(paint_text("Goodbye!", Fore.GREEN))
        exit(0)
    
    else:
        print(paint_text("Unknown command. Type /tools to see available commands.", Fore.RED))

def main():
    """Main function to run the Grok CLI agent"""
    try:
        # Initialize colorama for Windows
        colorama.init()
        
        # Display welcome message
        print(paint_text("\n╔════════════════════════════════════╗", Fore.CYAN))
        print(paint_text("║         Welcome to Grok CLI         ║", Fore.CYAN))
        print(paint_text("╚════════════════════════════════════╝\n", Fore.CYAN))
        
        # Load API key
        api_key = load_api_key()
        if not api_key:
            print(paint_text("Error: API key not found. Please set GROK_API_KEY environment variable.", Fore.RED))
            return
        
        # Display API key information
        display_api_key_info()
        
        # Display available models
        display_available_models()
        
        # Display current model info
        display_model_info(current_model)
        
        # Display available commands
        print(paint_text("\nCommands:", Fore.CYAN))
        print(paint_text("  • /model <model_id> - Switch models", Fore.YELLOW))
        print(paint_text("  • /info - Display current model info", Fore.YELLOW))
        print(paint_text("  • /key - Display API key info", Fore.YELLOW))
        print(paint_text("  • /tokens <text> - Show token breakdown", Fore.YELLOW))
        print(paint_text("  • /tools - Display available tools and their capabilities", Fore.YELLOW))
        print(paint_text("  • /system - Show system information and health", Fore.YELLOW))
        print(paint_text("  • /optimize - Run system optimization", Fore.YELLOW))
        print(paint_text("  • /repair - Run system repair", Fore.YELLOW))
        print(paint_text("  • /recommendations - Get system improvement recommendations", Fore.YELLOW))
        print(paint_text("  • /cleanup [days] [paths...] - Clean up unused files", Fore.YELLOW))
        print(paint_text("  • /exit - Exit the program\n", Fore.YELLOW))
        
        # Main interaction loop
        while True:
            try:
                user_input = input(paint_text("\nYou: ", Fore.GREEN))
                
                if user_input.lower() == "/exit":
                    print(paint_text("\nGoodbye! 👋", Fore.CYAN))
                    break
                
                elif user_input.startswith("/model "):
                    model_id = user_input[7:].strip()
                    switch_model(model_id)
                
                elif user_input == "/info":
                    display_model_info(current_model)
                
                elif user_input == "/key":
                    display_api_key_info()
                
                elif user_input.startswith("/tokens "):
                    text = user_input[8:].strip()
                    usage = tokenize_text(text, current_model)
                    display_usage_info(usage)
                
                elif user_input == "/tools":
                    display_tools()
                
                elif user_input == "/system":
                    info = get_system_management_info()
                    display_system_info(info)
                
                elif user_input == "/optimize":
                    print(paint_text("\nRunning system optimization...", Fore.YELLOW))
                    results = optimize_system()
                    display_optimization_results(results)
                
                elif user_input == "/repair":
                    print(paint_text("\nRunning system repair...", Fore.YELLOW))
                    results = repair_system()
                    display_repair_results(results)
                
                elif user_input == "/recommendations":
                    print(paint_text("\nAnalyzing system for recommendations...", Fore.YELLOW))
                    recommendations = system_manager.get_system_recommendations()
                    display_recommendations(recommendations)
                
                elif user_input.startswith("/cleanup"):
                    args = user_input[8:].strip().split()
                    days = 30  # Default value
                    paths = []
                    
                    if args:
                        try:
                            days = int(args[0])
                            paths = args[1:]
                        except ValueError:
                            paths = args
                    
                    if not paths:
                        paths = ["."]  # Default to current directory
                    
                    results = cleanup_files(days=days, paths=paths)
                    display_cleanup_results(results)
                
                else:
                    # Process as a chat message
                    messages = [{"role": "user", "content": user_input}]
                    response = send_message(messages, current_model)
                    process_grok_response(messages, response)
                
            except KeyboardInterrupt:
                print(paint_text("\nOperation cancelled by user.", Fore.YELLOW))
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                print(paint_text(f"\nError: {str(e)}", Fore.RED))
                continue
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(paint_text(f"\nFatal error: {str(e)}", Fore.RED))
        return

if __name__ == "__main__":
    main() 
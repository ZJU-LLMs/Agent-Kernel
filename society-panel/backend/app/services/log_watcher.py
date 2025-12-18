"""
Service for capturing stdout/stderr and streaming to WebSocket clients.
"""

import asyncio
import sys
import re
import io
from datetime import datetime
from typing import Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from threading import Lock


class LogLevel(str, Enum):
    """Enumeration of log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    OUTPUT = "OUTPUT"


class LogCategory(str, Enum):
    """Enumeration of log categories based on module path."""
    AGENT = "agent"
    ACTION = "action"
    ENV = "env"
    KERNEL = "kernel"
    OTHER = "other"


class StdoutCapture(io.TextIOBase):
    """Class for capturing stdout output."""
    
    def __init__(self, original_stdout, callback):
        self.original_stdout = original_stdout
        self.callback = callback
        self._lock = Lock()
    
    def write(self, text):
        if self.original_stdout:
            self.original_stdout.write(text)
        if text and text.strip():
            with self._lock:
                self.callback(text)
        return len(text)
    
    def flush(self):
        if self.original_stdout:
            self.original_stdout.flush()
    
    def fileno(self):
        if self.original_stdout:
            return self.original_stdout.fileno()
        raise io.UnsupportedOperation("fileno")
    
    def isatty(self):
        return False


class LogWatcher:
    """
    Log monitoring service that captures stdout and formats output to WebSocket.
    """

    ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m|\[[\d;]*m')
    
    LOG_PATTERN = re.compile(
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*'
        r'(\w+)\s*\|\s*'
        r'PID:(\d+)\s*\|\s*'
        r'([\w.]+):(\w+):(\d+)\s*-\s*'
        r'(.*)$'
    )
    
    RAY_PREFIX_PATTERN = re.compile(r'\((\w+)\s+pid=(\d+)\)\s*(.*)$')
    
    ACTION_PATTERN = re.compile(r'\{"action":\s*"(\w+)".*\}')
    
    MESSAGE_PATTERN = re.compile(r'(\w+)\s+send message to\s+(\w+)')

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._capturing = False
        self._original_stdout = None
        self._capture = None
        self._event_loop = None
        self._buffer = Queue(maxsize=1000)

    def _categorize_by_module(self, module: str) -> str:
        """Categorize logs based on module path."""
        if not module:
            return LogCategory.OTHER.value
        
        if module.startswith("agentkernel_distributed") or module.startswith("agentkernel_standalone"):
            return LogCategory.KERNEL.value
        
        if module.startswith("plugins."):
            parts = module.split(".")
            if len(parts) >= 2:
                sub = parts[1]
                if sub == "environment":
                    return LogCategory.ENV.value
                elif sub == "agent":
                    return LogCategory.AGENT.value
                elif sub == "action":
                    return LogCategory.ACTION.value
        
        return LogCategory.OTHER.value

    def _parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single output line."""
        line = self.ANSI_ESCAPE.sub('', line)
        line = line.strip()
        if not line:
            return None
        
        if line.startswith("INFO:") and "HTTP" in line:
            return None
        if "DeprecationWarning" in line:
            return None
        if line.startswith("(pid=") and not line.strip("(pid=0123456789) "):
            return None
        if "[repeated" in line:
            return None
        
        now = datetime.now().strftime("%H:%M:%S")
        
        ray_match = self.RAY_PREFIX_PATTERN.match(line)
        if ray_match:
            worker_type, pid, content = ray_match.groups()
            content = content.strip()
            if not content:
                return None
            
            log_match = self.LOG_PATTERN.match(content)
            if log_match:
                timestamp, level, _, module, function, line_num, message = log_match.groups()
                time_part = timestamp.split(' ')[-1]
                category = self._categorize_by_module(module)
                
                return {
                    "tick": time_part,
                    "name": worker_type,
                    "payload": message.strip(),
                    "category": category,
                    "level": level.strip(),
                }
            else:
                action_match = self.ACTION_PATTERN.search(content)
                if action_match:
                    return {
                        "tick": now,
                        "name": worker_type,
                        "payload": content,
                        "category": LogCategory.ACTION.value,
                        "level": LogLevel.INFO.value,
                    }
                
                return {
                    "tick": now,
                    "name": worker_type,
                    "payload": content,
                    "category": LogCategory.OTHER.value,
                    "level": LogLevel.OUTPUT.value,
                }
        
        log_match = self.LOG_PATTERN.match(line)
        if log_match:
            timestamp, level, pid, module, function, line_num, message = log_match.groups()
            time_part = timestamp.split(' ')[-1]
            category = self._categorize_by_module(module)
            
            return {
                "tick": time_part,
                "name": "Main",
                "payload": message.strip(),
                "category": category,
                "level": level.strip(),
            }
        
        return {
            "tick": now,
            "name": "Output",
            "payload": line,
            "category": LogCategory.OTHER.value,
            "level": LogLevel.OUTPUT.value,
        }

    def _get_short_module(self, module: str) -> str:
        """Get abbreviated module name."""
        parts = module.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return module

    def _on_output(self, text: str):
        """Handle captured output."""
        for line in text.split('\n'):
            parsed = self._parse_line(line)
            if parsed:
                try:
                    self._buffer.put_nowait(parsed)
                except:
                    pass

    async def _broadcast_loop(self):
        """Broadcast loop that reads from buffer and sends to WebSocket."""
        while self._capturing:
            try:
                entries = []
                while not self._buffer.empty() and len(entries) < 10:
                    try:
                        entry = self._buffer.get_nowait()
                        entries.append(entry)
                    except:
                        break
                
                for entry in entries:
                    dead_subscribers = set()
                    for queue in self._subscribers:
                        try:
                            await queue.put(entry)
                        except:
                            dead_subscribers.add(queue)
                    self._subscribers -= dead_subscribers
                
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Broadcast error: {e}", file=self._original_stdout or sys.stderr)
                await asyncio.sleep(0.5)

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to log updates."""
        queue = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from log updates."""
        self._subscribers.discard(queue)

    async def start_watching(self):
        """Start capturing stdout."""
        if self._capturing:
            return
        
        self._capturing = True
        self._event_loop = asyncio.get_event_loop()
        
        self._original_stdout = sys.stdout
        
        self._capture = StdoutCapture(self._original_stdout, self._on_output)
        sys.stdout = self._capture
        
        asyncio.create_task(self._broadcast_loop())
        
        print("Log watcher started - capturing stdout")

    async def stop_watching(self):
        """Stop capturing stdout."""
        self._capturing = False
        
        if self._original_stdout:
            sys.stdout = self._original_stdout
            self._original_stdout = None
        
        self._capture = None
        print("Log watcher stopped")


log_watcher = LogWatcher()

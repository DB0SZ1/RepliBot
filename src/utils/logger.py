"""
Logger Utility
Beautiful terminal output with colored logging
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from colorama import init, Fore, Back, Style

# Initialize colorama for Windows
init(autoreset=True)

LOGS_PATH = Path(__file__).parent.parent.parent / "logs"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE
    }
    
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✓',
        'WARNING': '⚠️',
        'ERROR': '✗',
        'CRITICAL': '💀'
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Build message
        msg = f"{color}[{timestamp}] {icon} {record.getMessage()}{Style.RESET_ALL}"
        
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        
        return msg


class Logger:
    """
    Custom logger with terminal colors and file logging.
    """
    
    def __init__(
        self,
        name: str = "x-reply-bot",
        level: int = logging.INFO,
        log_file: bool = True
    ):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            level: Logging level
            log_file: Whether to write to file
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers = []  # Clear existing handlers
        
        # Console handler with colors
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(level)
        console.setFormatter(ColoredFormatter())
        self.logger.addHandler(console)
        
        # File handler
        if log_file:
            LOGS_PATH.mkdir(parents=True, exist_ok=True)
            today = datetime.now().strftime('%Y-%m-%d')
            file_handler = logging.FileHandler(
                LOGS_PATH / f"{today}.log",
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s'
            ))
            self.logger.addHandler(file_handler)
    
    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
    
    def success(self, msg: str):
        """Green success message."""
        print(f"{Fore.GREEN}✓ {msg}{Style.RESET_ALL}")
    
    def action(self, action_type: str, content: str):
        """Log a bot action."""
        icons = {"post": "📝", "reply": "💬", "quote": "🔄", "skip": "⏭️"}
        icon = icons.get(action_type, "•")
        print(f"{Fore.CYAN}{icon} [{action_type.upper()}] {content[:80]}...{Style.RESET_ALL}")
    
    def stats(self, label: str, value, color: str = "blue"):
        """Print a stat line."""
        colors = {
            "blue": Fore.BLUE,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "red": Fore.RED,
            "cyan": Fore.CYAN
        }
        c = colors.get(color, Fore.WHITE)
        print(f"{c}  {label}: {value}{Style.RESET_ALL}")
    
    def header(self, title: str):
        """Print a section header."""
        width = 50
        print(f"\n{Fore.MAGENTA}{'═' * width}")
        print(f"  {title.upper()}")
        print(f"{'═' * width}{Style.RESET_ALL}\n")
    
    def divider(self):
        """Print a divider line."""
        print(f"{Fore.WHITE}{'─' * 50}{Style.RESET_ALL}")
    
    def banner(self):
        """Print the bot banner."""
        banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════╗
║                                                       ║
║   {Fore.WHITE}██╗  ██╗    {Fore.CYAN}██████╗  ███████╗██████╗ ██╗  ██╗   ║
║   {Fore.WHITE}╚██╗██╔╝    {Fore.CYAN}██╔══██╗ ██╔════╝██╔══██╗██║  ██║   ║
║   {Fore.WHITE} ╚███╔╝     {Fore.CYAN}██████╔╝ █████╗  ██████╔╝██║  ██║   ║
║   {Fore.WHITE} ██╔██╗     {Fore.CYAN}██╔══██╗ ██╔══╝  ██╔═══╝ ██║  ██║   ║
║   {Fore.WHITE}██╔╝ ██╗    {Fore.CYAN}██║  ██║ ███████╗██║     ╚█████╔╝   ║
║   {Fore.WHITE}╚═╝  ╚═╝    {Fore.CYAN}╚═╝  ╚═╝ ╚══════╝╚═╝      ╚════╝    ║
║                                                       ║
║   {Fore.YELLOW}Reply Guy Bot v1.0 - Raw, No Filter, Based{Fore.CYAN}          ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)


# Singleton logger instance
_logger: Optional[Logger] = None


def get_logger() -> Logger:
    """Get or create the singleton logger."""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger


# Quick test
if __name__ == "__main__":
    log = get_logger()
    log.banner()
    log.header("Testing Logger")
    log.info("This is an info message")
    log.success("Operation completed!")
    log.warning("This is a warning")
    log.error("This is an error")
    log.action("reply", "Yo that's actually fire, the way you broke that down...")
    log.divider()
    log.stats("Followers", 1234, "green")
    log.stats("Actions Today", "15/17", "yellow")

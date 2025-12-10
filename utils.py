"""
Utility functions for the trading system
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional
import yaml
from colorama import Fore, Style, init

# Initialize colorama for Windows
init(autoreset=True)


# ========================================
# Logging Setup
# ========================================

def setup_logging(config: dict) -> None:
    """
    Setup logging configuration for all components
    
    Args:
        config: Logging configuration dictionary
    """
    log_level = config.get('level', 'INFO')
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(config['files']['main']),
            logging.StreamHandler()
        ]
    )
    
    # Configure component-specific loggers
    components = config.get('components', {})
    for component_name, component_level in components.items():
        logger = logging.getLogger(component_name)
        logger.setLevel(getattr(logging, component_level))
    
    # Error logger
    error_handler = logging.FileHandler(config['files']['errors'])
    error_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(error_handler)
    
    logging.info("Logging system initialized")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


# ========================================
# Configuration Loading
# ========================================

def load_config(config_path: str = 'config.yaml') -> dict:
    """
    Load YAML configuration file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing configuration file: {e}")
        raise


# ========================================
# Time Utilities
# ========================================

def now_ms() -> int:
    """Get current time in milliseconds (Unix timestamp)"""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def ms_to_datetime(timestamp_ms: int) -> datetime:
    """Convert millisecond timestamp to datetime"""
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def format_timestamp(timestamp_ms: int, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format timestamp for display"""
    return ms_to_datetime(timestamp_ms).strftime(fmt)


def get_session_start(timestamp_ms: int, session_start_time: str = "00:00") -> int:
    """
    Get the session start timestamp for a given time
    
    Args:
        timestamp_ms: Current timestamp in ms
        session_start_time: Session start time in HH:MM format
        
    Returns:
        Session start timestamp in ms
    """
    dt = ms_to_datetime(timestamp_ms)
    hour, minute = map(int, session_start_time.split(':'))
    
    session_start = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If current time is before session start, use previous day
    if dt.time() < session_start.time():
        session_start = session_start.replace(day=session_start.day - 1)
    
    return int(session_start.timestamp() * 1000)


# ========================================
# Price Utilities
# ========================================

def round_to_tick(price: float, tick_size: float = 0.1) -> float:
    """
    Round price to tick size
    
    Args:
        price: Price to round
        tick_size: Minimum price increment
        
    Returns:
        Rounded price
    """
    return round(price / tick_size) * tick_size


def calculate_percent_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def is_near(price1: float, price2: float, tolerance_percent: float = 0.1) -> bool:
    """
    Check if two prices are close to each other
    
    Args:
        price1: First price
        price2: Second price
        tolerance_percent: Tolerance as percentage (0.1 = 0.1%)
        
    Returns:
        True if prices are within tolerance
    """
    if price2 == 0:
        return False
    diff_percent = abs((price1 - price2) / price2) * 100
    return diff_percent <= tolerance_percent


# ========================================
# Console Output Formatting
# ========================================

class ColoredFormatter:
    """Colored console output formatter"""
    
    @staticmethod
    def success(msg: str) -> str:
        return f"{Fore.GREEN}{msg}{Style.RESET_ALL}"
    
    @staticmethod
    def error(msg: str) -> str:
        return f"{Fore.RED}{msg}{Style.RESET_ALL}"
    
    @staticmethod
    def warning(msg: str) -> str:
        return f"{Fore.YELLOW}{msg}{Style.RESET_ALL}"
    
    @staticmethod
    def info(msg: str) -> str:
        return f"{Fore.CYAN}{msg}{Style.RESET_ALL}"
    
    @staticmethod
    def highlight(msg: str) -> str:
        return f"{Fore.MAGENTA}{Style.BRIGHT}{msg}{Style.RESET_ALL}"
    
    @staticmethod
    def signal_long(msg: str) -> str:
        return f"{Fore.GREEN}{Style.BRIGHT}🚀 {msg}{Style.RESET_ALL}"
    
    @staticmethod
    def signal_short(msg: str) -> str:
        return f"{Fore.RED}{Style.BRIGHT}🔻 {msg}{Style.RESET_ALL}"
    
    @staticmethod
    def signal_failure(msg: str) -> str:
        return f"{Fore.YELLOW}{Style.BRIGHT}⚠️  {msg}{Style.RESET_ALL}"


def print_banner():
    """Print system startup banner"""
    banner = f"""
{Fore.CYAN}{'='*60}
{'TPO + VWAP + Order Flow Trading System':^60}
{'='*60}{Style.RESET_ALL}
{Fore.GREEN}Status: Initializing...{Style.RESET_ALL}
{Fore.YELLOW}Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}{Style.RESET_ALL}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
"""
    print(banner)


def print_signal_summary(signal_dict: dict):
    """
    Pretty print signal summary
    
    Args:
        signal_dict: Signal data dictionary
    """
    signal_type = signal_dict['signal_type']
    
    # Choose color based on signal type
    if 'LONG' in signal_type:
        color = Fore.GREEN
        icon = '🚀'
    elif 'SHORT' in signal_type:
        color = Fore.RED
        icon = '🔻'
    else:
        color = Fore.YELLOW
        icon = '⚠️'
    
    print(f"\n{color}{'='*60}")
    print(f"{icon}  {signal_type} SIGNAL DETECTED  {icon}")
    print(f"{'='*60}{Style.RESET_ALL}")
    print(f"Symbol:     {signal_dict['symbol']}")
    print(f"Time:       {signal_dict['timestamp']}")
    print(f"Price:      ${signal_dict['price']:,.2f}")
    print(f"Confidence: {signal_dict['confidence']*100:.0f}%")
    
    print(f"\n{Fore.CYAN}Conditions:{Style.RESET_ALL}")
    conditions = signal_dict['conditions']
    print(f"  TPO Event:        {conditions['tpo_event']}")
    print(f"  VWAP Aligned:     {conditions['vwap_aligned']}")
    print(f"  Delta Confirmed:  {conditions['delta_confirmed']}")
    print(f"  CVD Confirmed:    {conditions['cvd_confirmed']}")
    print(f"  OI Confirmed:     {conditions['oi_confirmed']}")
    
    if conditions.get('delta_flip') or conditions.get('cvd_divergence'):
        print(f"  Delta Flip:       {conditions['delta_flip']}")
        print(f"  CVD Divergence:   {conditions['cvd_divergence']}")
    
    print(f"\n{Fore.CYAN}Context:{Style.RESET_ALL}")
    context = signal_dict['context']
    if context['vah'] and context['val']:
        print(f"  VAH: ${context['vah']:,.2f}  |  POC: ${context['poc']:,.2f}  |  VAL: ${context['val']:,.2f}")
    if context['vwap']:
        print(f"  VWAP: ${context['vwap']:,.2f}")
    if context['delta'] is not None:
        print(f"  Delta: {context['delta']:,.0f}  |  CVD: {context['cvd']:,.0f}")
    if context['oi_change']:
        print(f"  OI Change: {context['oi_change']}")
    
    print(f"{color}{'='*60}{Style.RESET_ALL}\n")


# ========================================
# Data Validation
# ========================================

def validate_candle(candle_data: dict) -> bool:
    """Validate candle data structure"""
    required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    return all(field in candle_data for field in required_fields)


def validate_config(config: dict) -> bool:
    """
    Validate configuration structure
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ['exchange', 'tpo', 'vwap', 'orderflow', 'signals', 'alerts']
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
    
    # Validate exchange config
    if 'symbols' not in config['exchange']:
        raise ValueError("Exchange symbols not configured")
    
    if not config['exchange']['symbols']:
        raise ValueError("No symbols configured for monitoring")
    
    return True


# ========================================
# Statistics & Math Utilities
# ========================================

def calculate_std_dev(values: list, mean: float) -> float:
    """
    Calculate standard deviation
    
    Args:
        values: List of values
        mean: Mean of the values
        
    Returns:
        Standard deviation
    """
    if not values:
        return 0.0
    
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


def calculate_slope(values: list) -> float:
    """
    Calculate simple linear slope of values
    
    Args:
        values: List of values (ordered by time)
        
    Returns:
        Slope (positive = uptrend, negative = downtrend)
    """
    if len(values) < 2:
        return 0.0
    
    n = len(values)
    x = list(range(n))
    y = values
    
    # Simple linear regression
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return 0.0
    
    slope = numerator / denominator
    return slope


def weighted_average(values: list, weights: list) -> float:
    """
    Calculate weighted average
    
    Args:
        values: List of values
        weights: List of weights
        
    Returns:
        Weighted average
    """
    if not values or not weights or len(values) != len(weights):
        return 0.0
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    return sum(v * w for v, w in zip(values, weights)) / total_weight


# ========================================
# Environment Variables
# ========================================

def load_api_keys() -> dict:
    """
    Load API keys from environment or .env file
    
    Returns:
        Dictionary with API credentials
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    return {
        'binance_api_key': os.getenv('BINANCE_API_KEY', ''),
        'binance_api_secret': os.getenv('BINANCE_API_SECRET', ''),
        'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
    }

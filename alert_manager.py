"""
报警管理器 Alert Manager

提供多渠道报警功能:
- Console输出
- 文件日志
- Telegram推送
"""

import logging
import json
from typing import Optional, Set
from datetime import datetime
import requests
from pathlib import Path

from models import SignalEvent, Alert, AlertPriority
import utils


class AlertManager:
    """
    Alert Management System
    
    Dispatches alerts via multiple channels with throttling
    """
    
    def __init__(self, config: dict):
        """
        Initialize alert manager
        
        Args:
            config: Alert configuration
        """
        self.logger = utils.get_logger('alert_manager')
        self.config = config
        
        # Channel configuration - 渠道配置
        self.channels = config['channels']
        self.console_config = config.get('console', {})
        self.file_config = config.get('file', {})
        self.telegram_config = config.get('telegram', {})

        
        # Throttling
        self.throttle_enabled = config.get('throttle', {}).get('enabled', True)
        self.duplicate_window = config.get('throttle', {}).get('duplicate_window_seconds', 300)
        self.max_alerts_per_hour = config.get('throttle', {}).get('max_alerts_per_hour', 20)
        
        # Track recent alerts for deduplication
        self.recent_alerts: Set[str] = set()  # Set of alert fingerprints
        self.hourly_alert_count = 0
        self.hour_reset_time: Optional[int] = None
        
        # Setup file logging
        if self.channels.get('file', False):
            self._setup_file_logging()
        
        self.logger.info("AlertManager initialized")
    
    def _setup_file_logging(self):
        """Setup file logging for alerts"""
        log_path = Path(self.file_config.get('path', 'logs/signals.log'))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create dedicated logger for signals
        signal_logger = logging.getLogger('signals')
        signal_logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        )
        signal_logger.addHandler(file_handler)
        
        self.logger.info(f"Signal file logging enabled: {log_path}")
    
    def send_signal_alert(self, signal: SignalEvent):
        """
        Send alert for a trading signal
        
        Args:
            signal: SignalEvent to alert
        """
        if not self.config.get('enabled', True):
            return
        
        # Check throttling
        if not self._check_throttle(signal):
            self.logger.debug("Alert throttled")
            return
        
        # Determine priority
        priority = self._determine_priority(signal)
        
        # Create alert message
        alert_title = f"{signal.signal_type.value} - {signal.symbol}"
        alert_message = self._format_alert_message(signal)
        
        alert = Alert(
            timestamp=signal.timestamp,
            priority=priority,
            title=alert_title,
            message=alert_message,
            signal=signal
        )
        
        # Send to all enabled channels - 发送到所有启用的渠道
        if self.channels.get('console', True):
            self._send_console_alert(alert)
        
        if self.channels.get('file', True):
            self._send_file_alert(alert)
        
        if self.channels.get('telegram', False):
            self._send_telegram_alert(alert)
        
        # Mark signal as alerted
        signal.alerted = True
        signal.alert_timestamp = utils.now_ms()
        
        # Track alert
        self._track_alert(signal)
    
    def _check_throttle(self, signal: SignalEvent) -> bool:
        """
        Check if alert should be throttled
        
        Args:
            signal: Signal to check
            
        Returns:
            True if alert should be sent, False if throttled
        """
        if not self.throttle_enabled:
            return True
        
        current_time = signal.timestamp
        
        # Reset hourly counter if needed
        if self.hour_reset_time is None or (current_time - self.hour_reset_time) > 3600000:
            self.hourly_alert_count = 0
            self.hour_reset_time = current_time
        
        # Check hourly limit
        if self.hourly_alert_count >= self.max_alerts_per_hour:
            self.logger.warning("Hourly alert limit reached")
            return False
        
        # Check for duplicate
        alert_fingerprint = self._get_alert_fingerprint(signal)
        if alert_fingerprint in self.recent_alerts:
            self.logger.debug("Duplicate alert detected")
            return False
        
        return True
    
    def _track_alert(self, signal: SignalEvent):
        """Track alert for deduplication"""
        self.hourly_alert_count += 1
        
        fingerprint = self._get_alert_fingerprint(signal)
        self.recent_alerts.add(fingerprint)
        
        # Clean old fingerprints (older than duplicate window)
        # Simple implementation: clear all every hour
        if len(self.recent_alerts) > 100:
            self.recent_alerts.clear()
    
    def _get_alert_fingerprint(self, signal: SignalEvent) -> str:
        """
        Generate unique fingerprint for alert deduplication
        
        Args:
            signal: Signal event
            
        Returns:
            Fingerprint string
        """
        return f"{signal.symbol}_{signal.signal_type.value}_{int(signal.timestamp / (self.duplicate_window * 1000))}"
    
    def _determine_priority(self, signal: SignalEvent) -> AlertPriority:
        """Determine alert priority based on signal"""
        if signal.confidence >= 0.9:
            return AlertPriority.CRITICAL
        elif signal.confidence >= 0.8:
            return AlertPriority.HIGH
        elif signal.confidence >= 0.7:
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW
    
    def _format_alert_message(self, signal: SignalEvent) -> str:
        """Format detailed alert message"""
        signal_dict = signal.to_dict()
        
        lines = [
            f"Signal: {signal_dict['signal_type']}",
            f"Symbol: {signal_dict['symbol']}",
            f"Price: ${signal_dict['price']:,.2f}",
            f"Time: {signal_dict['timestamp']}",
            f"Confidence: {signal_dict['confidence']*100:.0f}%",
            "",
            "Conditions:",
        ]
        
        cond = signal_dict['conditions']
        if cond['tpo_event']:
            lines.append(f"  - TPO: {cond['tpo_event']}")
        if cond['vwap_aligned']:
            lines.append(f"  - VWAP: Aligned")
        if cond['delta_confirmed']:
            lines.append(f"  - Delta: Confirmed")
        if cond['cvd_confirmed']:
            lines.append(f"  - CVD: Confirmed")
        if cond['oi_confirmed']:
            lines.append(f"  - OI: Increasing")
        if cond['delta_flip']:
            lines.append(f"  - Delta: FLIPPED")
        if cond['cvd_divergence']:
            lines.append(f"  - CVD: DIVERGENCE")
        
        lines.append("")
        lines.append("Context:")
        ctx = signal_dict['context']
        if ctx['vah']:
            lines.append(f"  VAH: ${ctx['vah']:,.2f} | POC: ${ctx['poc']:,.2f} | VAL: ${ctx['val']:,.2f}")
        if ctx['vwap']:
            lines.append(f"  VWAP: ${ctx['vwap']:,.2f}")
        if ctx['delta'] is not None:
            lines.append(f"  Delta: {ctx['delta']:,.0f} | CVD: {ctx['cvd']:,.0f}")
        if ctx['oi_change']:
            lines.append(f"  OI Change: {ctx['oi_change']}")
        
        return "\n".join(lines)
    
    # ========================================
    # Channel Implementations
    # ========================================
    
    def _send_console_alert(self, alert: Alert):
        """Send alert to console"""
        try:
            if self.console_config.get('verbose', True):
                # Detailed output
                utils.print_signal_summary(alert.signal.to_dict())
            else:
                # Simple output
                print(f"[{alert.priority.value}] {alert.title} @ ${alert.signal.price:,.2f}")
        except Exception as e:
            self.logger.error(f"Console alert error: {e}")
    
    def _send_file_alert(self, alert: Alert):
        """Send alert to log file"""
        try:
            signal_logger = logging.getLogger('signals')
            signal_logger.info(alert.message)
        except Exception as e:
            self.logger.error(f"File alert error: {e}")
    
    def _send_telegram_alert(self, alert: Alert):
        """通过Telegram发送报警"""
        try:
            message = f"🚨 *{alert.title}*\n\n{alert.message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self._send_telegram_message(message)
        except Exception as e:
            self.logger.error(f"Telegram报警错误: {e}")
    
    def _send_telegram_message(self, message: str):
        """
        统一的Telegram消息发送方法
        Unified Telegram message sending
        """
        try:
            bot_token = self.telegram_config.get('bot_token')
            chat_id = self.telegram_config.get('chat_id')
            
            if not bot_token or not chat_id:
                return
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code != 200:
                self.logger.warning(f"Telegram发送失败 {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Telegram消息发送错误: {e}")

    
    def send_system_message(self, message: str, level: str = "INFO"):
        """
        发送系统消息 (非信号报警)
        Send system message (non-signal alert)
        
        Args:
            message: Message to send
            level: Log level (INFO, WARNING, ERROR)
        """
        timestamp = utils.now_ms()
        
        # Console输出
        if self.channels.get('console', True):
            if level == "ERROR":
                print(utils.ColoredFormatter.error(f"[SYSTEM] {message}"))
            elif level == "WARNING":
                print(utils.ColoredFormatter.warning(f"[SYSTEM] {message}"))
            else:
                print(utils.ColoredFormatter.info(f"[SYSTEM] {message}"))
        
        # 文件日志
        if self.channels.get('file', True):
            logger = logging.getLogger('signals')
            if level == "ERROR":
                logger.error(f"[SYSTEM] {message}")
            elif level == "WARNING":
                logger.warning(f"[SYSTEM] {message}")
            else:
                logger.info(f"[SYSTEM] {message}")
        
        # Telegram通知
        if self.channels.get('telegram', False):
            emoji = {"ERROR": "❌", "WARNING": "⚠️"}.get(level, "ℹ️")
            telegram_message = f"{emoji} *系统消息*\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self._send_telegram_message(telegram_message)

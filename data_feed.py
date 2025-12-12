"""
数据源模块 - Data Feed Module (修复版)

使用经过验证的WebSocket模式
Using verified WebSocket pattern
"""

import json
import logging
import threading
import time
from typing import Dict, List, Callable, Optional
from collections import deque
import websocket
import requests

from models import Trade, OrderBookSnapshot, OrderBookLevel
import utils


class BinanceDataFeed:
    """
    币安Futures数据源 - Binance Futures Data Feed
    """
    
    def __init__(self, symbol: str, config: dict):
        """初始化数据源"""
        self.logger = utils.get_logger('data_feed')
        self.symbol = symbol.upper()
        self.config = config
        
        # WebSocket
        self.ws = None
        self.ws_thread = None
        
        # 数据缓冲区
        self.trades_buffer: deque = deque(maxlen=1000)
        self.orderbook: Optional[OrderBookSnapshot] = None
        self.current_oi: float = 0.0
        self.previous_oi: float = 0.0
        
        # Delta追踪
        self.current_delta: float = 0.0
        self.cumulative_delta: float = 0.0
        
        # 回调函数
        self.on_trade_callback: Optional[Callable] = None
        self.on_orderbook_callback: Optional[Callable] = None
        self.on_candle_callback: Optional[Callable] = None
        
        # 状态
        self.is_running: bool = False
        
        self.logger.info(f"DataFeed initialized for {self.symbol}")
    
    def start(self):
        """启动WebSocket连接"""
        if self.ws:
            return
        
        # 构建WebSocket URL (Combined streams)
        streams = [
            f"{self.symbol.lower()}@aggTrade",
            f"{self.symbol.lower()}@kline_1m",
            f"{self.symbol.lower()}@ticker"
        ]
        stream_query = "/".join(streams)
        url = f"wss://fstream.binance.com/stream?streams={stream_query}"
        
        self.logger.info(f"连接到: {url}")
        
        # 创建WebSocket
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
            on_open=self._on_ws_open
        )
        
        # 在新线程运行WebSocket
        def run_ws():
            self.ws.run_forever()
        
        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()
        
        # 启动OI定期获取线程（每30秒）
        def update_oi_periodically():
            while self.ws:
                try:
                    oi = self._fetch_open_interest()
                    if oi is not None:
                        self.previous_oi = self.current_oi
                        self.current_oi = oi
                        self.logger.debug(f"OI更新: {oi:.2f} (变化: {self.get_oi_change():.2f}%)")
                except Exception as e:
                    self.logger.debug(f"OI获取失败: {e}")
                time.sleep(30)  # 每30秒更新一次
        
        oi_thread = threading.Thread(target=update_oi_periodically, daemon=True)
        oi_thread.start()
        
        self.logger.info("✓ DataFeed启动成功")
    
    def stop(self):
        """停止数据源"""
        self.is_running = False
        if self.ws:
            self.ws.close()
        self.logger.info("DataFeed已停止")
    
    # WebSocket回调
    def _on_ws_open(self, ws):
        """连接打开"""
        self.logger.info(f"✅ WebSocket已连接 {self.symbol}")
    
    def _on_ws_message(self, ws, message):
        """接收消息"""
        try:
            data = json.loads(message)
            
            if 'data' not in data:
                return
            
            stream = data.get('stream', '')
            msg = data['data']
            
            # 处理不同类型的消息
            if 'aggTrade' in stream:
                self._process_trade(msg)
            elif 'kline' in stream:
                self._process_kline(msg)
            elif 'ticker' in stream:
                self._process_ticker(msg)
                
        except Exception as e:
            self.logger.error(f"消息处理错误: {e}")
    
    def _on_ws_error(self, ws, error):
        """WebSocket错误"""
        self.logger.error(f"WebSocket错误: {error}")
    
    def _on_ws_close(self, ws, close_code, close_msg):
        """连接关闭"""
        self.logger.warning(f"WebSocket关闭: {close_code}")
    
    # 数据处理
    def _process_trade(self, msg):
        """处理交易"""
        try:
            trade = Trade(
                timestamp=msg['T'],
                price=float(msg['p']),
                quantity=float(msg['q']),
                is_buyer_maker=msg['m']
            )
            
            self.trades_buffer.append(trade)
            
            # 更新delta
            if trade.is_buy:
                self.current_delta += trade.quantity
            else:
                self.current_delta -= trade.quantity
            
            # 更新CVD
            self.cumulative_delta += trade.quantity if trade.is_buy else -trade.quantity
            
            # 触发回调
            if self.on_trade_callback:
                self.on_trade_callback(trade, self.current_delta, self.cumulative_delta)
                
        except Exception as e:
            self.logger.error(f"处理交易错误: {e}")
    
    def _process_kline(self, msg):
        """处理K线"""
        try:
            if 'k' not in msg:
                return
            
            kline = msg['k']
            
            # 只处理关闭的K线
            if not kline['x']:
                return
            
            candle_data = {
                'timestamp': kline['t'],
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
            }
            
            # 触发回调
            if self.on_candle_callback:
                self.on_candle_callback(candle_data)
                
        except Exception as e:
            self.logger.error(f"处理K线错误: {e}")
    
    def _process_ticker(self, msg):
        """处理Ticker"""
        try:
            # 检查必要字段是否存在
            if not all(k in msg for k in ['b', 'a', 'B', 'A']):
                # 缺少字段,静默跳过(ticker数据不是核心功能)
                return
            
            bid_price = float(msg['b'])
            ask_price = float(msg['a'])
            bid_qty = float(msg['B'])
            ask_qty = float(msg['A'])
            
            self.orderbook = OrderBookSnapshot(
                timestamp=utils.now_ms(),
                bids=[OrderBookLevel(price=bid_price, quantity=bid_qty)],
                asks=[OrderBookLevel(price=ask_price, quantity=ask_qty)]
            )
            
            # 触发回调
            if self.on_orderbook_callback:
                self.on_orderbook_callback(self.orderbook)
                
        except Exception as e:
            # 降低日志级别,避免刷屏
            self.logger.debug(f"处理Ticker警告: {e}")
    
    # 回调注册
    def on_trade(self, callback: Callable):
        self.on_trade_callback = callback
    
    def on_orderbook(self, callback: Callable):
        self.on_orderbook_callback = callback
    
    def on_candle(self, callback: Callable):
        self.on_candle_callback = callback
    
    # 数据访问
    def get_recent_trades(self, count: int = 100) -> List[Trade]:
        return list(self.trades_buffer)[-count:]
    
    def get_orderbook(self) -> Optional[OrderBookSnapshot]:
        return self.orderbook
    
    def get_delta(self) -> float:
        return self.current_delta
    
    def get_cvd(self) -> float:
        return self.cumulative_delta
    
    def get_oi(self) -> float:
        return self.current_oi
    
    def get_oi_change(self) -> float:
        if self.previous_oi == 0:
            return 0.0
        return ((self.current_oi - self.previous_oi) / self.previous_oi) * 100
    
    def reset_delta(self):
        self.current_delta = 0.0
    
    # 历史数据
    def get_historical_klines(self, interval: str = '1m', limit: int = 100) -> List[dict]:
        """获取历史K线 - 直接调用Binance API"""
        try:
            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                'symbol': self.symbol,
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            candles = []
            for k in klines:
                candles.append({
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                })
            
            self.logger.info(f"获取到 {len(candles)} 根历史K线")
            return candles
            
        except Exception as e:
            self.logger.error(f"获取历史K线失败: {e}")
            return []
    
    def _fetch_open_interest(self) -> Optional[float]:
        """获取持仓量 - 直接调用Binance API"""
        try:
            url = "https://fapi.binance.com/fapi/v1/openInterest"
            params = {'symbol': self.symbol}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data['openInterest'])
        except Exception as e:
            self.logger.debug(f"获取OI失败: {e}")
            return None


# 多币种管理器
class DataFeedManager:
    """管理多个币种的数据源"""
    
    def __init__(self, symbols: List[str], config: dict):
        self.logger = utils.get_logger('data_feed_manager')
        self.symbols = symbols
        self.config = config
        
        self.feeds: Dict[str, BinanceDataFeed] = {}
        for symbol in symbols:
            self.feeds[symbol] = BinanceDataFeed(symbol, config)
        
        self.logger.info(f"DataFeedManager initialized for {len(symbols)} symbols")
    
    def start_all(self):
        """启动所有数据源"""
        self.logger.info("Starting all data feeds")
        for symbol, feed in self.feeds.items():
            feed.start()
            time.sleep(0.5)
    
    def stop_all(self):
        """停止所有数据源"""
        self.logger.info("Stopping all data feeds")
        for symbol, feed in self.feeds.items():
            feed.stop()
    
    def get_feed(self, symbol: str) -> BinanceDataFeed:
        """获取指定币种的数据源"""
        return self.feeds.get(symbol.upper())

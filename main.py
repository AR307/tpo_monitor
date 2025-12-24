"""
主控制器 - Main Controller

协调所有组件:
- Data feed - 数据源
- TPO analyzer - TPO分析器
- VWAP calculator - VWAP计算器
- Order flow analyzer - 订单流分析器
- Signal engine - 信号引擎
- Alert manager - 报警管理器
"""

import time
import signal as sys_signal
import logging
from typing import Dict, Optional
import threading

from models import Candle
from data_feed import DataFeedManager, BinanceDataFeed
from tpo_analyzer import TPOAnalyzer
from vwap_calculator import VWAPCalculator
from orderflow_analyzer import OrderFlowAnalyzer
from signal_engine import SignalEngine
from alert_manager import AlertManager
import utils


class TradingSystem:
    """
    交易系统主控制器
    
    整合所有组件并管理信号检测流程
    """
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        初始化交易系统
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = utils.load_config(config_path)
        utils.validate_config(self.config)
        
        # 设置日志
        utils.setup_logging(self.config['logging'])
        self.logger = utils.get_logger('trading_system')
        
        # 获取要监控的币种
        self.symbols = self.config['exchange']['symbols']
        
        # 初始化数据源管理器
        self.data_feed_manager = DataFeedManager(self.symbols, self.config['exchange'])
        
        # 为每个币种初始化分析器和引擎
        self.tpo_analyzers: Dict[str, TPOAnalyzer] = {}
        self.vwap_calculators: Dict[str, VWAPCalculator] = {}
        self.orderflow_analyzers: Dict[str, OrderFlowAnalyzer] = {}
        self.signal_engines: Dict[str, SignalEngine] = {}
        
        for symbol in self.symbols:
            self.tpo_analyzers[symbol] = TPOAnalyzer(symbol, self.config['tpo'])
            self.vwap_calculators[symbol] = VWAPCalculator(symbol, self.config['vwap'])
            self.orderflow_analyzers[symbol] = OrderFlowAnalyzer(symbol, self.config['orderflow'])
            self.signal_engines[symbol] = SignalEngine(symbol, self.config['signals'])
        
        # 初始化报警管理器
        self.alert_manager = AlertManager(self.config['alerts'])
        
        # 系统状态
        self.is_running = False
        self.warmup_complete = False
        
        # OI更新线程
        self.oi_threads = []
        
        self.logger.info(f"交易系统已初始化,监控 {len(self.symbols)} 个币种")
    
    def start(self):
        """启动交易系统"""
        if self.is_running:
            self.logger.warning("系统已在运行中")
            return
        
        self.logger.info("=" * 60)
        self.logger.info("启动交易系统")
        self.logger.info("=" * 60)
        
        utils.print_banner()
        
        # 发送启动通知
        self.alert_manager.send_system_message(
            f"交易系统启动 - 监控币种: {', '.join(self.symbols)}"
        )
        
        # 设置信号处理器以优雅关闭
        self._setup_signal_handlers()
        
        # 启动数据源
        self.logger.info("启动数据源...")
        for symbol in self.symbols:
            feed = self.data_feed_manager.get_feed(symbol)
            
            # 注册回调函数
            feed.on_candle(lambda candle, s=symbol: self._on_candle(s, candle))
            feed.on_trade(lambda trade, delta, cvd, s=symbol: self._on_trade(s, trade, delta, cvd))
            feed.on_orderbook(lambda ob, s=symbol: self._on_orderbook(s, ob))
            
        self.data_feed_manager.start_all()
        
        # 启动OI轮询线程
        self._start_oi_polling()
        
        # 使用历史数据预热
        self._warmup()
        
        self.is_running = True
        self.logger.info("✓ 交易系统现已上线 LIVE")
        self.alert_manager.send_system_message("系统现已上线 LIVE", "INFO")
        
        # 保持运行
        try:
            self.logger.info("系统运行中... (按 Ctrl+C 停止)")
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("收到键盘中断信号")
        finally:
            self.stop()
    
    def stop(self):
        """停止交易系统"""
        if not self.is_running:
            return
        
        self.logger.info("正在停止交易系统...")
        self.alert_manager.send_system_message("系统正在关闭", "WARNING")
        
        # 停止数据源
        self.data_feed_manager.stop_all()
        
        self.is_running = False
        self.logger.info("交易系统已停止")
    
    def _start_oi_polling(self):
        """启动OI轮询线程"""
        for symbol in self.symbols:
            feed = self.data_feed_manager.get_feed(symbol)
            orderflow = self.orderflow_analyzers[symbol]
            
            def poll_oi(symbol=symbol, feed=feed, orderflow=orderflow):
                """OI轮询函数"""
                update_interval = self.config.get('orderflow', {}).get('oi', {}).get('update_interval', 60)
                
                while self.is_running:
                    try:
                        # 从REST API获取OI
                        oi_data = feed.client.futures_open_interest(symbol=symbol)
                        new_oi = float(oi_data['openInterest'])
                        
                        # 更新OI
                        orderflow.update_oi(new_oi)
                        
                        self.logger.debug(f"{symbol} OI更新: {new_oi:,.0f}")
                        
                    except Exception as e:
                        self.logger.error(f"获取{symbol} OI失败: {e}")
                    
                    time.sleep(update_interval)
            
            # 启动线程
            thread = threading.Thread(target=poll_oi, daemon=True)
            thread.start()
            self.oi_threads.append(thread)
            self.logger.info(f"已启动 {symbol} 的OI轮询线程")
    
    def _warmup(self):
        """使用历史数据预热分析器"""
        self.logger.info("使用历史数据预热中...")
        
        warmup_bars = self.config['data']['warmup_bars']
        
        for symbol in self.symbols:
            feed = self.data_feed_manager.get_feed(symbol)
            
            # 获取历史K线
            historical_klines = feed.get_historical_klines(interval='1m', limit=warmup_bars)
            
            if not historical_klines:
                self.logger.warning(f"{symbol} 没有历史数据")
                continue
            
            # 处理历史K线
            for kline_data in historical_klines:
                candle = Candle(
                    timestamp=kline_data['timestamp'],
                    open=kline_data['open'],
                    high=kline_data['high'],
                    low=kline_data['low'],
                    close=kline_data['close'],
                    volume=kline_data['volume']
                )
                
                # 更新分析器(预热期间不生成信号)
                self.tpo_analyzers[symbol].update(candle)
                self.vwap_calculators[symbol].update(candle)
                self.orderflow_analyzers[symbol].finalize_bar(candle.close)
            
            self.logger.info(f"{symbol} 已预热 {len(historical_klines)} 根K线")
        
        self.warmup_complete = True
        self.logger.info("✓ 预热完成")
    
    def _on_candle(self, symbol: str, candle_data: dict):
        """
        处理新K线(1分钟K线收盘)
        
        这是主要的信号检测触发点
        
        Args:
            symbol: 交易币种
            candle_data: K线数据字典
        """
        try:
            if not self.warmup_complete:
                return
            
            # 创建Candle对象
            candle = Candle(
                timestamp=candle_data['timestamp'],
                open=candle_data['open'],
                high=candle_data['high'],
                low=candle_data['low'],
                close=candle_data['close'],
                volume=candle_data['volume']
            )
            
            self.logger.debug(f"{symbol} K线收盘: {candle.close:.2f}")
            
            # 更新TPO
            tpo_event = self.tpo_analyzers[symbol].update(candle)
            tpo_data = self.tpo_analyzers[symbol].get_current_profile()
            
            # 更新VWAP
            vwap_data = self.vwap_calculators[symbol].update(candle)
            
            # 完成订单流bar
            orderflow = self.orderflow_analyzers[symbol]
            orderflow.finalize_bar(candle.close)
            orderflow_data = orderflow.get_metrics(candle.timestamp)
            
            # 检查信号
            signal = self.signal_engines[symbol].check_signals(
                current_time=candle.timestamp,
                current_price=candle.close,
                tpo_data=tpo_data,
                tpo_event=tpo_event,
                vwap_data=vwap_data,
                orderflow_data=orderflow_data
            )
            
            # DEBUG: 记录信号检测结果
            if signal:
                self.logger.info(f"✅ Signal detected: {signal.signal_type.value} for {symbol} @ ${signal.price:.2f}")
            
            # 如果检测到信号则发送报警
            if signal:
                self.logger.info(f"📤 Sending signal alert...")
                self.alert_manager.send_signal_alert(signal)
                self.logger.info(f"✓ Signal alert sent")
        
        except Exception as e:
            self.logger.error(f"处理{symbol}的K线时出错: {e}", exc_info=True)
    
    def _on_trade(self, symbol: str, trade, delta: float, cvd: float):
        print(f"Passing to OrderFlowAnalyzer: trade={trade}, delta={delta}, cvd={cvd}")
        print(f"_on_trade called: symbol={symbol}, delta={delta}, cvd={cvd}")
        """
        处理交易更新
        
        Args:
            symbol: 交易币种
            trade: Trade对象
            delta: 当前delta
            cvd: 累积成交量delta
        """
        try:
            # 使用订单流分析器更新交易
            # (交易已聚合;我们会在K线收盘时处理)
            # 传递交易到OrderFlow分析器
            if symbol in self.orderflow_analyzers:
                self.orderflow_analyzers[symbol].update_from_trades([trade])
        except Exception as e:
            self.logger.error(f"处理{symbol}的交易时出错: {e}")
    
    def _on_orderbook(self, symbol: str, orderbook):
        """
        处理订单簿更新
        
        Args:
            symbol: 交易币种
            orderbook: OrderBookSnapshot
        """
        try:
            # 更新订单流失衡
            self.orderflow_analyzers[symbol].update_from_orderbook(orderbook)
        except Exception as e:
            self.logger.error(f"处理{symbol}的订单簿时出错: {e}")
    
    def _setup_signal_handlers(self):
        """设置信号处理器以优雅关闭"""
        def signal_handler(sig, frame):
            self.logger.info(f"收到信号 {sig}")
            self.is_running = False
        
        try:
            sys_signal.signal(sys_signal.SIGINT, signal_handler)
            sys_signal.signal(sys_signal.SIGTERM, signal_handler)
        except Exception as e:
            self.logger.warning(f"无法设置信号处理器: {e}")
    
    def get_status(self) -> dict:
        """
        获取系统状态
        
        Returns:
            状态字典
        """
        return {
            'running': self.is_running,
            'warmup_complete': self.warmup_complete,
            'symbols': self.symbols,
            'components': {
                'data_feed': 'running' if self.is_running else 'stopped',
                'tpo_analyzer': len(self.tpo_analyzers),
                'vwap_calculator': len(self.vwap_calculators),
                'orderflow_analyzer': len(self.orderflow_analyzers),
                'signal_engine': len(self.signal_engines),
                'alert_manager': 'active' if self.alert_manager else 'inactive'
            }
        }


# ========================================
# 入口点 - Entry Point
# ========================================

def main():
    """主入口点"""
    try:
        # 创建交易系统
        system = TradingSystem()
        
        # 启动系统
        system.start()
    
    except KeyboardInterrupt:
        logging.info("用户中断")
    except Exception as e:
        logging.error(f"致命错误: {e}", exc_info=True)
    finally:
        logging.info("系统关闭完成")


if __name__ == '__main__':
    # 运行主程序
    main()

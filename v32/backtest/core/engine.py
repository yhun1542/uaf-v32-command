"""
Backtesting Engine using backtrader
"""
import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SimpleStrategy(bt.Strategy):
    """Simple Moving Average Crossover Strategy"""
    
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
    )
    
    def __init__(self):
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        else:
            if self.crossover < 0:
                self.sell()


class BacktestEngine:
    """Backtesting engine wrapper for backtrader"""
    
    def __init__(self):
        self.cerebro = None
        self.results = None
        
    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_class=SimpleStrategy,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        **strategy_params
    ) -> Dict:
        """
        Run backtest with given data and strategy
        
        Args:
            data: OHLCV DataFrame with DatetimeIndex
            strategy_class: Strategy class to use
            initial_cash: Starting capital
            commission: Commission rate
            **strategy_params: Strategy parameters
            
        Returns:
            Performance metrics dictionary
        """
        logger.info(f"Running backtest: {len(data)} bars, initial_cash={initial_cash}")
        
        # Initialize Cerebro
        self.cerebro = bt.Cerebro()
        
        # Add strategy
        self.cerebro.addstrategy(strategy_class, **strategy_params)
        
        # Convert DataFrame to backtrader data feed
        data_feed = bt.feeds.PandasData(dataname=data)
        self.cerebro.adddata(data_feed)
        
        # Set initial cash and commission
        self.cerebro.broker.setcash(initial_cash)
        self.cerebro.broker.setcommission(commission=commission)
        
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Run backtest
        start_value = self.cerebro.broker.getvalue()
        self.results = self.cerebro.run()
        end_value = self.cerebro.broker.getvalue()
        
        # Extract metrics
        strat = self.results[0]
        
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', None)
        drawdown = strat.analyzers.drawdown.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        
        metrics = {
            'start_date': data.index[0].date(),
            'end_date': data.index[-1].date(),
            'initial_value': start_value,
            'final_value': end_value,
            'total_return': (end_value - start_value) / start_value,
            'max_drawdown': drawdown.get('max', {}).get('drawdown', 0.0) / 100.0,
            'sharpe_ratio': sharpe,
            'trade_count': trades.get('total', {}).get('total', 0)
        }
        
        logger.info(f"Backtest completed: Return={metrics['total_return']:.2%}, Sharpe={sharpe}")
        
        return metrics


# Global instance
backtest_engine = BacktestEngine()

"""
Analytics API Routes: TCI, NSDE, Backtesting
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime
import uuid
import logging

from v32.tci.core.causal_engine import causal_engine
from v32.ndde.core.sde_model import NeuralSDE, NSDETrainer, register_model, get_model
from v32.backtest.core.engine import backtest_engine

logger = logging.getLogger(__name__)

router = APIRouter()


# ============= TCI Endpoints =============

@router.post("/tci/analyze")
async def analyze_causal_relationships(
    data: Dict[str, List[float]],
    tau_max: int = 10,
    pc_alpha: float = 0.05
):
    """
    시계열 데이터에서 인과 관계 분석
    
    Request body:
    {
        "data": {
            "var1": [1.0, 2.0, ...],
            "var2": [1.5, 2.5, ...],
            ...
        },
        "tau_max": 10,
        "pc_alpha": 0.05
    }
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        if len(df) < tau_max + 10:
            raise HTTPException(
                status_code=400,
                detail=f"Data length ({len(df)}) too short for tau_max={tau_max}"
            )
        
        # Prepare data
        tg_data = causal_engine.prepare_data(df)
        
        # Run PCMCI+
        result = causal_engine.run_pcmci(tg_data, tau_max=tau_max, pc_alpha=pc_alpha)
        
        # Convert numpy arrays to lists for JSON serialization
        return {
            "status": "success",
            "nodes": result['nodes'],
            "links": result['links'],
            "timestamp": result['timestamp'].isoformat(),
            "num_links": len(result['links'])
        }
        
    except Exception as e:
        logger.error(f"TCI analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tci/get_parents/{target_var}")
async def get_causal_parents(target_var: str, max_lag: int = 5):
    """특정 변수의 인과적 부모 변수 조회"""
    try:
        parents = causal_engine.get_causal_parents(target_var, max_lag)
        return {
            "target": target_var,
            "parents": [{"source": src, "lag": lag} for src, lag in parents]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= NSDE Endpoints =============

@router.post("/nsde/train")
async def train_nsde_model(
    data: List[List[float]],
    input_size: int,
    hidden_size: int = 32,
    epochs: int = 100,
    learning_rate: float = 0.01
):
    """
    Neural SDE 모델 학습
    
    Request body:
    {
        "data": [[1.0, 2.0], [1.1, 2.1], ...],  # [timesteps, features]
        "input_size": 2,
        "hidden_size": 32,
        "epochs": 100,
        "learning_rate": 0.01
    }
    """
    try:
        # Convert to numpy array
        data_array = np.array(data)
        
        if data_array.shape[1] != input_size:
            raise HTTPException(
                status_code=400,
                detail=f"Data feature size ({data_array.shape[1]}) != input_size ({input_size})"
            )
        
        # Create model
        model = NeuralSDE(
            input_size=input_size,
            hidden_size=hidden_size
        )
        
        # Create trainer
        trainer = NSDETrainer(model, learning_rate=learning_rate)
        
        # Train
        final_loss = trainer.train(data_array, epochs=epochs)
        
        # Register model
        model_id = f"nsde_{uuid.uuid4().hex[:8]}"
        register_model(model_id, model, trainer)
        
        return {
            "status": "success",
            "model_id": model_id,
            "final_loss": float(final_loss),
            "epochs": epochs
        }
        
    except Exception as e:
        logger.error(f"NSDE training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nsde/predict/{model_id}")
async def predict_nsde(
    model_id: str,
    initial_state: List[float],
    steps: int = 30,
    num_samples: int = 100
):
    """
    학습된 NSDE 모델로 미래 예측
    
    Request body:
    {
        "initial_state": [1.0, 2.0],
        "steps": 30,
        "num_samples": 100
    }
    """
    try:
        # Get model
        result = get_model(model_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        model, trainer = result
        
        # Predict
        initial_array = np.array(initial_state)
        mean, std = trainer.predict(
            initial_array,
            steps=steps,
            num_samples=num_samples
        )
        
        # Convert to list of predictions
        predictions = []
        for t in range(steps):
            predictions.append({
                "time_step": t + 1,
                "mean": mean[t].tolist(),
                "std": std[t].tolist()
            })
        
        return {
            "status": "success",
            "model_id": model_id,
            "predictions": predictions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"NSDE prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Backtesting Endpoints =============

@router.post("/backtest/run")
async def run_backtest(
    data: Dict[str, List[float]],
    initial_cash: float = 100000.0,
    commission: float = 0.001,
    fast_period: int = 10,
    slow_period: int = 30
):
    """
    백테스팅 실행
    
    Request body:
    {
        "data": {
            "open": [...],
            "high": [...],
            "low": [...],
            "close": [...],
            "volume": [...]
        },
        "initial_cash": 100000.0,
        "commission": 0.001,
        "fast_period": 10,
        "slow_period": 30
    }
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required):
            raise HTTPException(
                status_code=400,
                detail=f"Data must contain columns: {required}"
            )
        
        # Create datetime index (daily data)
        df.index = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
        
        # Run backtest
        metrics = backtest_engine.run_backtest(
            df,
            initial_cash=initial_cash,
            commission=commission,
            fast_period=fast_period,
            slow_period=slow_period
        )
        
        return {
            "status": "success",
            "metrics": {
                "start_date": metrics['start_date'].isoformat(),
                "end_date": metrics['end_date'].isoformat(),
                "initial_value": metrics['initial_value'],
                "final_value": metrics['final_value'],
                "total_return": metrics['total_return'],
                "max_drawdown": metrics['max_drawdown'],
                "sharpe_ratio": metrics['sharpe_ratio'],
                "trade_count": metrics['trade_count']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

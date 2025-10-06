"""
NSDE (Neural Stochastic Differential Equations) Module
PyTorch + torchsde 기반 확률적 미분방정식 모델
"""
import torch
import torch.nn as nn
import torchsde
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DriftNet(nn.Module):
    """Drift function μ(x, t) 근사를 위한 신경망"""
    
    def __init__(self, input_size: int, hidden_size: int = 32, num_layers: int = 2):
        super().__init__()
        
        layers = []
        layers.append(nn.Linear(input_size + 1, hidden_size))  # +1 for time
        layers.append(nn.Tanh())
        
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(hidden_size, hidden_size))
            layers.append(nn.Tanh())
        
        layers.append(nn.Linear(hidden_size, input_size))
        
        self.net = nn.Sequential(*layers)
        
    def forward(self, t: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            t: time tensor [batch_size, 1]
            x: state tensor [batch_size, input_size]
        Returns:
            drift tensor [batch_size, input_size]
        """
        # Concatenate time and state
        tx = torch.cat([t.expand(x.shape[0], 1), x], dim=1)
        return self.net(tx)


class DiffusionNet(nn.Module):
    """Diffusion function σ(x, t) 근사를 위한 신경망"""
    
    def __init__(self, input_size: int, hidden_size: int = 16, num_layers: int = 1):
        super().__init__()
        
        layers = []
        layers.append(nn.Linear(input_size + 1, hidden_size))
        layers.append(nn.Tanh())
        
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(hidden_size, hidden_size))
            layers.append(nn.Tanh())
        
        # Output: diagonal diffusion matrix
        layers.append(nn.Linear(hidden_size, input_size))
        layers.append(nn.Softplus())  # Ensure positive diffusion
        
        self.net = nn.Sequential(*layers)
        
    def forward(self, t: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            t: time tensor [batch_size, 1]
            x: state tensor [batch_size, input_size]
        Returns:
            diffusion tensor [batch_size, input_size]
        """
        tx = torch.cat([t.expand(x.shape[0], 1), x], dim=1)
        return self.net(tx)


class NeuralSDE(nn.Module):
    """
    Neural SDE 모델: dx = μ(x,t)dt + σ(x,t)dW
    
    torchsde 라이브러리와 호환되는 인터페이스 구현
    """
    noise_type = "diagonal"  # 대각 노이즈 (각 차원 독립)
    sde_type = "ito"  # Ito SDE
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 32,
        drift_layers: int = 2,
        diffusion_layers: int = 1
    ):
        super().__init__()
        
        self.input_size = input_size
        
        # Drift and Diffusion networks
        self.drift_net = DriftNet(input_size, hidden_size, drift_layers)
        self.diffusion_net = DiffusionNet(input_size, hidden_size // 2, diffusion_layers)
        
        logger.info(f"Initialized NeuralSDE: input_size={input_size}, hidden_size={hidden_size}")
        
    def f(self, t: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """Drift function (deterministic part)"""
        return self.drift_net(t, y)
    
    def g(self, t: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """Diffusion function (stochastic part)"""
        return self.diffusion_net(t, y)


class NSDETrainer:
    """Neural SDE 학습 및 예측 클래스"""
    
    def __init__(
        self,
        model: NeuralSDE,
        learning_rate: float = 0.01,
        device: str = "cpu"
    ):
        self.model = model.to(device)
        self.device = device
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        self.loss_history = []
        
    def train(
        self,
        data: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        dt: float = 0.1,
        method: str = "euler"
    ) -> float:
        """
        시계열 데이터로 Neural SDE 학습
        
        Args:
            data: 시계열 데이터 [timesteps, features]
            epochs: 학습 에포크 수
            batch_size: 배치 크기
            dt: 시간 간격
            method: SDE 솔버 ('euler', 'milstein', 'srk')
            
        Returns:
            최종 loss
        """
        self.model.train()
        
        # 데이터를 torch tensor로 변환
        data_tensor = torch.FloatTensor(data).to(self.device)
        timesteps = data_tensor.shape[0]
        
        logger.info(f"Training NSDE: {epochs} epochs, batch_size={batch_size}")
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            # 랜덤 시작점에서 배치 생성
            for _ in range(max(1, timesteps // batch_size)):
                # 랜덤 시작 인덱스
                start_idx = np.random.randint(0, max(1, timesteps - batch_size))
                end_idx = min(start_idx + batch_size, timesteps)
                
                batch_data = data_tensor[start_idx:end_idx]
                
                # 초기 상태
                y0 = batch_data[0:1]  # [1, features]
                
                # 시간 벡터
                ts = torch.linspace(0, (end_idx - start_idx) * dt, end_idx - start_idx).to(self.device)
                
                # SDE 솔버로 예측
                try:
                    ys = torchsde.sdeint(self.model, y0, ts, method=method)
                    ys = ys.squeeze(1)  # [timesteps, features]
                    
                    # MSE Loss
                    loss = nn.MSELoss()(ys, batch_data)
                    
                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()
                    
                    epoch_loss += loss.item()
                    num_batches += 1
                    
                except Exception as e:
                    logger.warning(f"SDE integration failed: {e}")
                    continue
            
            avg_loss = epoch_loss / max(1, num_batches)
            self.loss_history.append(avg_loss)
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.6f}")
        
        final_loss = self.loss_history[-1] if self.loss_history else 0.0
        logger.info(f"Training completed. Final loss: {final_loss:.6f}")
        
        return final_loss
    
    def predict(
        self,
        initial_state: np.ndarray,
        steps: int = 30,
        dt: float = 0.1,
        num_samples: int = 100,
        method: str = "euler"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        미래 시계열 예측 (확률적 샘플링)
        
        Args:
            initial_state: 초기 상태 [features]
            steps: 예측 스텝 수
            dt: 시간 간격
            num_samples: 몬테카를로 샘플 수
            method: SDE 솔버
            
        Returns:
            (mean, std): 평균 및 표준편차 [steps, features]
        """
        self.model.eval()
        
        y0 = torch.FloatTensor(initial_state).unsqueeze(0).to(self.device)  # [1, features]
        ts = torch.linspace(0, steps * dt, steps + 1).to(self.device)
        
        predictions = []
        
        with torch.no_grad():
            for _ in range(num_samples):
                try:
                    ys = torchsde.sdeint(self.model, y0, ts, method=method)
                    ys = ys.squeeze(1).cpu().numpy()  # [steps+1, features]
                    predictions.append(ys[1:])  # 초기 상태 제외
                except Exception as e:
                    logger.warning(f"Prediction sample failed: {e}")
                    continue
        
        if not predictions:
            raise RuntimeError("All prediction samples failed")
        
        predictions = np.array(predictions)  # [num_samples, steps, features]
        
        mean = predictions.mean(axis=0)
        std = predictions.std(axis=0)
        
        logger.info(f"Prediction completed: {steps} steps, {num_samples} samples")
        
        return mean, std


# 전역 모델 레지스트리
_model_registry = {}

def register_model(model_id: str, model: NeuralSDE, trainer: NSDETrainer):
    """학습된 모델 등록"""
    _model_registry[model_id] = {
        'model': model,
        'trainer': trainer
    }
    logger.info(f"Model {model_id} registered")

def get_model(model_id: str) -> Optional[Tuple[NeuralSDE, NSDETrainer]]:
    """등록된 모델 가져오기"""
    if model_id in _model_registry:
        entry = _model_registry[model_id]
        return entry['model'], entry['trainer']
    return None

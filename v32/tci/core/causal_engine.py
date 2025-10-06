"""
TCI (Temporal Causal Inference) Module
PCMCI+ 알고리즘 기반 시계열 인과 추론 엔진
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

try:
    from tigramite.data_processing import DataFrame as TigramiteDataFrame
    from tigramite.pcmci import PCMCI
    from tigramite.independence_tests.parcorr import ParCorr
except ImportError as e:
    raise ImportError(f"tigramite import failed: {e}. Run: pip install tigramite")

logger = logging.getLogger(__name__)


class CausalInferenceEngine:
    """
    시계열 데이터에서 인과 관계를 추론하는 엔진
    PCMCI+ (Peter and Clark Momentary Conditional Independence) 알고리즘 사용
    """
    
    def __init__(self, significance_level: float = 0.05):
        """
        Args:
            significance_level: p-value 임계값 (기본: 0.05)
        """
        self.significance_level = significance_level
        self.pcmci = None
        self.results = None
        
    def prepare_data(self, df: pd.DataFrame, var_names: Optional[List[str]] = None) -> TigramiteDataFrame:
        """
        DataFrame을 Tigramite DataFrame 객체로 변환
        
        Args:
            df: 시계열 데이터 (행: 시간, 열: 변수)
            var_names: 변수 이름 리스트 (None이면 컬럼명 사용)
            
        Returns:
            Tigramite DataFrame 객체
        """
        if var_names is None:
            var_names = list(df.columns)
            
        # NaN 처리
        data_array = df[var_names].values
        
        logger.info(f"Preparing data: {data_array.shape[0]} timesteps, {data_array.shape[1]} variables")
        
        return TigramiteDataFrame(data_array, var_names=var_names)
    
    def run_pcmci(
        self,
        data: TigramiteDataFrame,
        tau_max: int = 10,
        pc_alpha: float = 0.05
    ) -> Dict:
        """
        PCMCI+ 알고리즘 실행
        
        Args:
            data: Tigramite Data 객체
            tau_max: 최대 시간 지연 (lag)
            pc_alpha: PC 알고리즘의 유의수준
            
        Returns:
            인과 그래프 결과 딕셔너리
        """
        logger.info(f"Running PCMCI+ with tau_max={tau_max}, pc_alpha={pc_alpha}")
        
        # ParCorr (Partial Correlation) 독립성 테스트 사용
        parcorr = ParCorr(significance='analytic')
        
        # PCMCI 객체 생성
        self.pcmci = PCMCI(
            dataframe=data,
            cond_ind_test=parcorr,
            verbosity=0
        )
        
        # PCMCI+ 실행
        results = self.pcmci.run_pcmciplus(
            tau_max=tau_max,
            pc_alpha=pc_alpha
        )
        
        self.results = results
        
        # 결과 파싱
        causal_graph = self._parse_results(results, data.var_names)
        
        logger.info(f"PCMCI+ completed. Found {len(causal_graph['links'])} causal links")
        
        return causal_graph
    
    def _parse_results(self, results: Dict, var_names: List[str]) -> Dict:
        """
        PCMCI 결과를 표준 형식으로 파싱
        
        Returns:
            {
                'nodes': List[str],
                'links': List[Dict],
                'graph_matrix': np.ndarray,
                'p_matrix': np.ndarray
            }
        """
        graph = results['graph']
        p_matrix = results['p_matrix']
        val_matrix = results['val_matrix']
        
        links = []
        
        # graph 행렬 순회 (i: target, j: source, tau: lag)
        for i in range(graph.shape[0]):  # target variable
            for j in range(graph.shape[1]):  # source variable
                for tau in range(graph.shape[2]):  # time lag
                    # graph[i,j,tau] == "-->" 또는 "<--" 등의 링크가 있는 경우
                    if graph[i, j, tau] == "-->":
                        links.append({
                            'source': var_names[j],
                            'target': var_names[i],
                            'lag': tau,
                            'strength': float(val_matrix[i, j, tau]),
                            'p_value': float(p_matrix[i, j, tau])
                        })
        
        return {
            'nodes': var_names,
            'links': links,
            'graph_matrix': graph,
            'p_matrix': p_matrix,
            'val_matrix': val_matrix,
            'timestamp': datetime.utcnow()
        }
    
    def get_causal_parents(self, target_var: str, max_lag: int = 5) -> List[Tuple[str, int]]:
        """
        특정 변수의 인과적 부모(원인) 변수들을 반환
        
        Args:
            target_var: 타겟 변수명
            max_lag: 최대 시간 지연
            
        Returns:
            [(source_var, lag), ...] 리스트
        """
        if self.results is None:
            raise ValueError("Run PCMCI first")
        
        var_names = self.pcmci.dataframe.var_names
        target_idx = var_names.index(target_var)
        
        graph = self.results['graph']
        parents = []
        
        for j in range(graph.shape[1]):
            for tau in range(min(max_lag + 1, graph.shape[2])):
                if graph[target_idx, j, tau] == "-->":
                    parents.append((var_names[j], tau))
        
        return parents


# 전역 인스턴스
causal_engine = CausalInferenceEngine()

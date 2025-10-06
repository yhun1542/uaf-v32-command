from v32.command.schemas import MasterPlan, TaskStatus

INITIAL_STATE: MasterPlan = {
    "P1_INSIGHT_ENGINE": {
        "name": "P1: The Insight Engine (예측 코어)", "accent": "p1", "phases": {
            "PHASE_1_1": {"name": "1.1 Data Fusion Pipeline", "tasks": [
                {"id": "T1_1_L1_EDGAR", "name": "L1: EDGAR Connector", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_L1_NEWS", "name": "L1: NewsAPI Connector", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_L1_NASA", "name": "L1: NASA Connector", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_L2_PLANET", "name": "L2: Planet Labs (Procurement)", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_1_FUSION_ENGINE", "name": "OASIS-Lumio Fusion Engine", "progress": 0, "status": TaskStatus.PENDING}
            ]},
            "PHASE_1_2": {"name": "1.2 Causal & Predictive Modeling", "tasks": [
                {"id": "T1_2_TCI", "name": "EmarkOS TCI Module", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_2_NDDE_PINN", "name": "NDDE/PINN Models", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T1_2_BACKTESTING", "name": "Backtesting Framework", "progress": 0, "status": TaskStatus.PENDING}
            ]}
        }
    },
    "P2_ALPHA_ONE": {
        "name": "P2: Alpha One (투자 집행 플랫폼)", "accent": "p2", "phases": {
            "PHASE_2_1": {"name": "2.1 C&C Dashboard", "tasks": [
                {"id": "T2_1_VISUALIZATION", "name": "LuminEX Real-time Visualization", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_1_TRADE_UI", "name": "Trade Proposal UI/UX", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_1_PNL_TRACKING", "name": "Real-time PnL Tracking", "progress": 0, "status": TaskStatus.PENDING}
            ]},
            "PHASE_2_2": {"name": "2.2 Trade Execution Engine", "tasks": [
                {"id": "T2_2_BROKER_API", "name": "Global Broker API (IBKR)", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_2_AUTO_AGENT", "name": "Chimera Z+ Trading Agent", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_2_CDT_VETO", "name": "Project Bank CDT (Veto)", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T2_2_CCR_LOGGING", "name": "EmarkOS CCR (Logging)", "progress": 0, "status": TaskStatus.PENDING}
            ]}
        }
    },
    "P3_A2AAS": {
        "name": "P3: A²aaS (자율 개발 플랫폼)", "accent": "p3", "phases": {
            "PHASE_3_1": {"name": "3.1 Platform APIization", "tasks": [
                {"id": "T3_1_TDD_API", "name": "Chimera Z+ TDD Engine API", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T3_1_ORCHESTRATION_API", "name": "UAF v32 Orchestration API", "progress": 0, "status": TaskStatus.PENDING}
            ]},
            "PHASE_3_2": {"name": "3.2 Project Genesis (No-Code)", "tasks": [
                {"id": "T3_2_BUILDER_UI", "name": "No-Code Builder UI/UX", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T3_2_BACKEND_INTEGRATION", "name": "Backend Integration", "progress": 0, "status": TaskStatus.PENDING},
                {"id": "T3_2_MARKETPLACE", "name": "AI Agent Marketplace", "progress": 0, "status": TaskStatus.PENDING}
            ]}
        }
    }
}

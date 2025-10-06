from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Any
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class Task(BaseModel):
    id: str
    name: str
    progress: int = Field(0, ge=0, le=100)
    status: TaskStatus = TaskStatus.PENDING

class Phase(BaseModel):
    name: str
    tasks: List[Task]

class Project(BaseModel):
    name: str
    accent: str
    phases: Dict[str, Phase]

MasterPlan = Dict[str, Project]

class UpdateTaskInput(BaseModel):
    task_id: str
    progress: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[TaskStatus] = None

    @model_validator(mode='before')
    @classmethod
    def check_update_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get('progress') is None and values.get('status') is None:
                raise ValueError("Either progress or status must be provided.")
        return values

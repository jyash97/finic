from pydantic import BaseModel
from enum import Enum
import datetime
import uuid
from typing import List, Optional, Dict, Any
from .models import AppConfig, User, Agent, ExecutionAttempt


class GetAgentRequest(BaseModel):
    agent_id: str


class GetExecutionRequest(BaseModel):
    agent_id: str
    execution_id: str


class DeployAgentRequest(BaseModel):
    agent_id: str
    agent_description: str
    num_retries: int


class DeleteAgentRequest(BaseModel):
    agent_id: str
    num_retries: int


class RunAgentRequest(BaseModel):
    agent_id: str
    input: Dict[str, Any] = {}


class LogExecutionAttemptRequest(BaseModel):
    execution_id: str
    agent_id: str
    results: Dict[str, Any]
    attempt: ExecutionAttempt

import os
import uvicorn
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Depends,
    Body,
    UploadFile,
    Request,
    status,
    Form,
    Query,
    BackgroundTasks,
)
from fastapi.exceptions import RequestValidationError

from fastapi.responses import JSONResponse

from typing import List, Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import requests
from models.api import (
    GetAgentRequest,
    GetExecutionRequest,
    DeployAgentRequest,
    RunAgentRequest,
    LogExecutionAttemptRequest,
)
import uuid
from models.models import AppConfig, Agent, AgentStatus, Execution
from database import Database
import io
import datetime
import pdb
import logging
import sentry_sdk
from agent_runner import AgentRunner
import json
from agent_deployer import AgentDeployer

SENTRY_DSN = os.environ.get("SENTRY_DSN")
sentry_sdk.init(
    dsn=SENTRY_DSN,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    environment=os.environ.get("ENVIRONMENT"),
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to the list of allowed origins if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()
db = Database()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logging.error(f"{request}: {exc_str}")
    content = {"status_code": 10422, "message": exc_str, "data": None}
    return JSONResponse(
        content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    try:
        print(credentials.credentials)
        app_config = db.get_config(credentials.credentials)
    except Exception:
        print(credentials.credentials)
        raise HTTPException(status_code=401, detail="Invalid or missing public key")
    if credentials.scheme != "Bearer" or app_config is None:
        print(credentials.credentials)
        raise HTTPException(status_code=401, detail="Invalid or missing public key")
    return app_config


async def validate_optional_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    try:
        app_config = db.get_config(credentials.credentials)
    except Exception:
        return None
    if credentials.scheme != "Bearer" or app_config is None:
        return None
    return app_config


def deploy_agent_background(agent: Agent):
    deployer = AgentDeployer()
    try:
        deployer.deploy_agent(agent=agent)
        agent.status = AgentStatus.deployed
        db.upsert_agent(agent)
        return agent
    except Exception as e:
        agent.status = AgentStatus.failed
        db.upsert_agent(agent)


@app.post("/deploy-agent")
async def deploy_agent(
    # background_tasks: BackgroundTasks,
    request: DeployAgentRequest = Body(...),
    config: AppConfig = Depends(validate_token),
):
    try:
        agent = db.get_agent(config=config, id=request.agent_id)
        agent.status = AgentStatus.deploying
        db.upsert_agent(agent)
        # background_tasks.add_task(deploy_agent_background, agent)
        deployer = AgentDeployer()
        secret_key = db.get_secret_key_for_user(config.user_id)
        try:
            deployer.deploy_agent(agent=agent, secret_key=secret_key)
            agent.status = AgentStatus.deploying
            db.upsert_agent(agent)
            return agent
        except Exception as e:
            agent.status = AgentStatus.failed
            db.upsert_agent(agent)
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-agent-upload-link")
async def get_agent_upload_link(
    request: DeployAgentRequest = Body(...),
    config: AppConfig = Depends(validate_token),
):
    try:
        deployer = AgentDeployer()
        agent = db.get_agent(config=config, id=request.agent_id)
        if agent is None:
            agent = Agent(
                finic_id=str(uuid.uuid4()),
                app_id=config.app_id,
                id=request.agent_id,
                description=request.agent_description,
                num_retries=request.num_retries,
                status="deploying",
            )
            db.upsert_agent(agent)
        link = deployer.get_agent_upload_link(agent=agent)
        return {"upload_link": link}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run-agent")
async def run_agent(
    request: RunAgentRequest = Body(...),
    config: AppConfig = Depends(validate_token),
):
    try:
        runner = AgentRunner()
        agent = db.get_agent(config=config, id=request.agent_id)
        if agent is None:
            raise HTTPException(
                status_code=404, detail=f"Agent {request.agent_id} not found"
            )
        secret_key = db.get_secret_key_for_user(config.user_id)
        execution = runner.start_agent(
            secret_key=secret_key, agent=agent, input=request.input
        )
        db.upsert_execution(execution)
        return execution
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log-execution-attempt")
async def log_execution_attempt(
    request: LogExecutionAttemptRequest = Body(...),
    config: AppConfig = Depends(validate_token),
):
    try:
        runner = AgentRunner()
        attempt = request.attempt
        agent = db.get_agent(config=config, id=request.agent_id)
        if agent is None:
            raise HTTPException(
                status_code=404, detail=f"Agent {request.agent_id} not found"
            )
        execution = db.get_execution(
            config=config,
            finic_agent_id=agent.finic_id,
            execution_id=request.execution_id,
        )
        updated_execution = runner.update_execution(
            agent=agent, execution=execution, attempt=attempt, results=request.results
        )
        db.upsert_execution(updated_execution)
        return execution
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-agent")
async def get_agent(
    agent_id: str = Query(...),
    config: AppConfig = Depends(validate_token),
):
    try:
        agent = db.get_agent(config=config, id=agent_id)
        return agent
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-agents")
async def list_agents(
    config: AppConfig = Depends(validate_token),
):
    try:
        agents = db.list_agents(config=config)
        return agents
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/delete-agent")
async def delete_agent(
    request: DeployAgentRequest = Body(...),
    config: AppConfig = Depends(validate_token),
):
    try:
        agent = db.get_agent(config=config, id=request.agent_id)
        agent.status = AgentStatus.deploying
        db.upsert_agent(agent)
        deployer = AgentDeployer()
        try:
            deployer.deploy_agent(agent=agent)
            agent.status = AgentStatus.deployed
            db.upsert_agent(agent)
            return agent
        except Exception as e:
            agent.status = AgentStatus.failed
            db.upsert_agent(agent)
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get-execution")
async def get_execution(
    execution_id: str = Query(...),
    agent_id: str = Query(...),
    config: AppConfig = Depends(validate_token),
):
    try:
        agent = db.get_agent(config=config, id=agent_id)
        execution = db.get_execution(
            config=config, finic_agent_id=agent.finic_id, execution_id=execution_id
        )
        return execution
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-executions")
async def list_executions(
    agent_id: Optional[str] = Query(None),
    finic_agent_id: Optional[str] = Query(None),
    config: AppConfig = Depends(validate_token),
):
    try:
        if agent_id is None:
            executions = db.list_executions(config=config)
            return executions
        executions = db.list_executions(
            config=config, finic_agent_id=finic_agent_id, user_defined_agent_id=agent_id
        )
        return executions
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0


def start():
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_excludes="subprocess_env/**",
    )

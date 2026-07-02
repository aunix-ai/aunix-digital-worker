"""Product API: conversational agent creation (compile -> confirm -> activate),
run-now, run history with explainability traces, the activity feed, and CSV
upload. Serve with: uv run uvicorn "aunix.api:create_default_app" --factory"""
import csv as csv_mod
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import delete, select

from aunix.compiler import CompileResult, compile_intent
from aunix.composio.compile_context import build_compile_context
from aunix.composio.normalize import normalize_rows
from aunix.composio.operations import (
    execute_tool,
    get_connect_link,
    get_tool_schema,
    list_toolkit_connections,
    search_tools,
)
from aunix.config import Settings
from aunix.db import make_engine, make_session_factory
from aunix.llm import LlmClient, LlmError, OpenAiLlm
from aunix.actions.service import ActionStateError, execute_action
from aunix.models import Action, Agent, Base, Connection, Finding, Notification, Run, Task
from aunix.runtime import Runtime
from aunix.spec import AgentSpec
from aunix.worker import run_agent_once


class CompileRequest(BaseModel):
    text: str


class CreateAgentRequest(BaseModel):
    owner: str
    spec: AgentSpec


class ApproveRequest(BaseModel):
    params: dict | None = None


class ConnectRequest(BaseModel):
    toolkit: str


class SearchToolsRequest(BaseModel):
    query: str
    toolkits: list[str] | None = None


class ProbeRequest(BaseModel):
    tool_slug: str
    arguments: dict[str, Any] = {}
    row_mapping: dict[str, str] = {}


def _agent_out(agent: Agent) -> dict:
    return {"id": agent.id, "owner": agent.owner, "status": agent.status, "spec": agent.spec}


def _action_out(action: Action, finding: Finding | None = None) -> dict:
    out = {
        "id": action.id, "agent_id": action.agent_id, "run_id": action.run_id,
        "finding_id": action.finding_id, "type": action.type, "params": action.params,
        "status": action.status, "origin": action.origin,
        "policy_decision": action.policy_decision, "decided_by": action.decided_by,
        "result": action.result, "error": action.error,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "expires_at": action.expires_at.isoformat() if action.expires_at else None,
    }
    if finding is not None:
        out["finding"] = {"id": finding.id, "summary": finding.summary,
                          "recommendation": finding.recommendation, "source_ref": finding.source_ref,
                          "severity": finding.severity}
    return out


def _run_out(run: Run) -> dict:
    return {
        "id": run.id, "agent_id": run.agent_id, "trigger": run.trigger,
        "status": run.status, "trace": run.trace, "error": run.error,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def create_app(*, session_factory, llm: LlmClient, runtime: Runtime,
               upload_dir: Path, cors_origins: list[str] | None = None,
               settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Aunix Digital Worker")
    app_settings = settings or Settings()
    app.add_middleware(
        CORSMiddleware, allow_origins=cors_origins or ["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.exception_handler(LlmError)
    def llm_error_handler(request, exc: LlmError):
        return JSONResponse(status_code=502,
                            content={"detail": f"language model unavailable: {exc}"})

    def get_session():
        with session_factory() as session:
            yield session

    def get_agent(agent_id: int, session) -> Agent:
        agent = session.get(Agent, agent_id)
        if agent is None:
            raise HTTPException(404, "agent not found")
        return agent

    @app.post("/agents/compile", response_model=CompileResult)
    def compile_endpoint(body: CompileRequest):
        composio_context = None
        if app_settings.composio_api_key:
            try:
                composio_context = build_compile_context(body.text)
            except Exception as exc:
                composio_context = {"error": str(exc)}
        return compile_intent(llm, body.text, composio_context=composio_context)

    @app.get("/integrations/status")
    def integrations_status():
        if not app_settings.composio_api_key:
            raise HTTPException(503, "Composio is not configured")
        try:
            return {"connections": list_toolkit_connections()}
        except Exception as exc:
            raise HTTPException(502, f"Composio error: {exc}") from exc

    @app.post("/integrations/connect")
    def integrations_connect(body: ConnectRequest):
        if not app_settings.composio_api_key:
            raise HTTPException(503, "Composio is not configured")
        callback_url = f"{app_settings.public_app_url.rstrip('/')}/integrations/callback"
        try:
            return get_connect_link(body.toolkit, callback_url)
        except Exception as exc:
            raise HTTPException(502, f"Composio error: {exc}") from exc

    @app.post("/integrations/search")
    def integrations_search(body: SearchToolsRequest):
        if not app_settings.composio_api_key:
            raise HTTPException(503, "Composio is not configured")
        try:
            return search_tools(body.query, toolkits=body.toolkits)
        except Exception as exc:
            raise HTTPException(502, f"Composio error: {exc}") from exc

    @app.get("/integrations/tools/{tool_slug}")
    def integrations_tool_schema(tool_slug: str):
        if not app_settings.composio_api_key:
            raise HTTPException(503, "Composio is not configured")
        try:
            return get_tool_schema(tool_slug)
        except Exception as exc:
            raise HTTPException(502, f"Composio error: {exc}") from exc

    @app.post("/integrations/probe")
    def integrations_probe(body: ProbeRequest):
        if not app_settings.composio_api_key:
            raise HTTPException(503, "Composio is not configured")
        try:
            raw = execute_tool(body.tool_slug, body.arguments)
            rows = normalize_rows(raw, body.row_mapping or None)
            return {"raw": raw, "rows": rows, "row_count": len(rows)}
        except Exception as exc:
            raise HTTPException(502, f"Composio error: {exc}") from exc

    @app.post("/agents", status_code=201)
    def create_agent(body: CreateAgentRequest, session=Depends(get_session)):
        agent = Agent(owner=body.owner, status="draft",
                      spec=body.spec.model_dump(mode="json"))
        session.add(agent)
        session.commit()
        return _agent_out(agent)

    @app.get("/agents")
    def list_agents(session=Depends(get_session)):
        return [_agent_out(a) for a in session.scalars(select(Agent)).all()]

    @app.get("/agents/{agent_id}")
    def get_agent_endpoint(agent_id: int, session=Depends(get_session)):
        return _agent_out(get_agent(agent_id, session))

    @app.post("/agents/{agent_id}/activate")
    def activate(agent_id: int, session=Depends(get_session)):
        agent = get_agent(agent_id, session)
        agent.status = "active"
        session.commit()
        return _agent_out(agent)

    @app.post("/agents/{agent_id}/pause")
    def pause(agent_id: int, session=Depends(get_session)):
        agent = get_agent(agent_id, session)
        agent.status = "paused"
        session.commit()
        return _agent_out(agent)

    @app.delete("/agents/{agent_id}", status_code=204)
    def delete_agent(agent_id: int, session=Depends(get_session)):
        agent = get_agent(agent_id, session)
        finding_ids = list(
            session.scalars(select(Finding.id).where(Finding.agent_id == agent_id))
        )
        if finding_ids:
            session.execute(
                delete(Notification).where(Notification.finding_id.in_(finding_ids))
            )
            session.execute(delete(Action).where(Action.finding_id.in_(finding_ids)))
            session.execute(delete(Task).where(Task.finding_id.in_(finding_ids)))
        session.execute(delete(Action).where(Action.agent_id == agent_id))
        session.execute(delete(Task).where(Task.agent_id == agent_id))
        session.execute(delete(Finding).where(Finding.agent_id == agent_id))
        session.execute(delete(Run).where(Run.agent_id == agent_id))
        session.delete(agent)
        session.commit()
        return Response(status_code=204)

    @app.post("/agents/{agent_id}/run")
    def run_now(agent_id: int, session=Depends(get_session)):
        agent = get_agent(agent_id, session)
        prior_status = agent.status
        if agent.status != "active":
            agent.status = "active"  # drafts activate; paused agents run once
            session.commit()
        try:
            run = run_agent_once(session_factory, agent_id, runtime, trigger="manual",
                                 now=datetime.now(timezone.utc))
        finally:
            if prior_status == "paused":
                agent.status = "paused"  # pause is sticky across manual runs
                session.commit()
        if run is None:
            raise HTTPException(409, "agent did not run")
        # run was created inside run_agent_once's own session (now closed).
        # SQLAlchemy expires attributes on commit/close, so we must re-fetch
        # using the endpoint's session. The identity key survives detachment.
        from sqlalchemy import inspect as sa_inspect
        run_id = sa_inspect(run).identity[0]
        run = session.get(Run, run_id)
        return _run_out(run)

    @app.get("/agents/{agent_id}/runs")
    def list_runs(agent_id: int, session=Depends(get_session)):
        get_agent(agent_id, session)
        runs = session.scalars(
            select(Run).where(Run.agent_id == agent_id).order_by(Run.id.desc()).limit(50)
        ).all()
        return [_run_out(r) for r in runs]

    @app.get("/runs/{run_id}")
    def get_run(run_id: int, session=Depends(get_session)):
        run = session.get(Run, run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        findings = session.scalars(select(Finding).where(Finding.run_id == run_id)).all()
        out = _run_out(run)
        out["findings"] = [
            {"id": f.id, "dedupe_key": f.dedupe_key, "state": f.state,
             "severity": f.severity, "summary": f.summary,
             "recommendation": f.recommendation, "source_ref": f.source_ref,
             "details": f.details}
            for f in findings
        ]
        out["actions"] = [_action_out(a) for a in
                          session.scalars(select(Action).where(Action.run_id == run_id)).all()]
        return out

    @app.get("/feed")
    def feed(session=Depends(get_session)):
        pairs = session.execute(
            select(Notification, Finding)
            .join(Finding, Notification.finding_id == Finding.id)
            .order_by(Notification.id.desc()).limit(100)
        ).all()
        return [
            {"id": n.id, "channel": n.channel, "status": n.status,
             "created_at": n.created_at.isoformat() if n.created_at else None,
             "finding": {"id": f.id, "agent_id": f.agent_id, "run_id": f.run_id,
                         "severity": f.severity, "state": f.state,
                         "summary": f.summary, "recommendation": f.recommendation,
                         "source_ref": f.source_ref}}
            for n, f in pairs
        ]

    @app.get("/actions")
    def list_actions(status: str | None = None, session=Depends(get_session)):
        q = select(Action).order_by(Action.id.desc()).limit(200)
        if status:
            q = select(Action).where(Action.status == status).order_by(Action.id.desc()).limit(200)
        out = []
        for action in session.scalars(q).all():
            out.append(_action_out(action, session.get(Finding, action.finding_id)))
        return out

    @app.post("/actions/{action_id}/approve")
    def approve_action(action_id: int, body: ApproveRequest | None = None, session=Depends(get_session)):
        action = session.get(Action, action_id)
        if action is None:
            raise HTTPException(404, "action not found")
        if body and body.params is not None:
            action.params = {**action.params, **body.params}  # edited params win
            session.flush()
        try:
            agent = session.get(Agent, action.agent_id)
            execute_action(session, action, runtime.executors(session, owner=agent.owner if agent else None),
                           now=datetime.now(timezone.utc), decided_by="user")
        except ActionStateError as exc:
            raise HTTPException(409, str(exc))
        session.commit()
        return _action_out(action)

    @app.post("/actions/{action_id}/reject")
    def reject_action(action_id: int, session=Depends(get_session)):
        action = session.get(Action, action_id)
        if action is None:
            raise HTTPException(404, "action not found")
        if action.status != "pending":
            raise HTTPException(409, f"action is {action.status}")
        action.status = "rejected"
        action.decided_at = datetime.now(timezone.utc)
        action.decided_by = "user"
        session.commit()
        return _action_out(action)

    @app.post("/uploads/csv", status_code=201)
    def upload_csv(file: UploadFile, session=Depends(get_session)):
        content = file.file.read()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "CSV must be UTF-8 encoded")
        rows = list(csv_mod.DictReader(io.StringIO(text)))
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / "sales_report.csv"  # single-slot MVP: latest upload wins
        path.write_bytes(content)
        session.add(Connection(provider="csv", credentials={"path": str(path)}))
        session.commit()
        return {"path": str(path), "rows": len(rows)}

    return app


def create_default_app() -> FastAPI:
    """uvicorn factory entrypoint: uvicorn "aunix.api:create_default_app" --factory"""
    load_dotenv()  # OPENAI_API_KEY is read by the SDK, not Settings fields
    settings = Settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    return create_app(
        session_factory=make_session_factory(engine),
        llm=OpenAiLlm(model=settings.llm_model),
        runtime=Runtime(settings),
        upload_dir=Path(settings.upload_dir),
        cors_origins=settings.api_cors_origins,
        settings=settings,
    )

"""Product API: conversational agent creation (compile -> confirm -> activate),
run-now, run history with explainability traces, the activity feed, and CSV
upload. Serve with: uv run uvicorn "aunix.api:create_default_app" --factory"""
import csv as csv_mod
import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select

from aunix.compiler import CompileResult, compile_intent
from aunix.config import Settings
from aunix.db import make_engine, make_session_factory
from aunix.llm import AnthropicLlm, LlmClient
from aunix.models import Agent, Base, Connection, Finding, Notification, Run
from aunix.runtime import Runtime
from aunix.spec import AgentSpec
from aunix.worker import run_agent_once


class CompileRequest(BaseModel):
    text: str


class CreateAgentRequest(BaseModel):
    owner: str
    spec: AgentSpec


def _agent_out(agent: Agent) -> dict:
    return {"id": agent.id, "owner": agent.owner, "status": agent.status, "spec": agent.spec}


def _run_out(run: Run) -> dict:
    return {
        "id": run.id, "agent_id": run.agent_id, "trigger": run.trigger,
        "status": run.status, "trace": run.trace, "error": run.error,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def create_app(*, session_factory, llm: LlmClient, runtime: Runtime,
               upload_dir: Path, cors_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="Aunix Digital Worker")
    app.add_middleware(
        CORSMiddleware, allow_origins=cors_origins or ["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"],
    )

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
        return compile_intent(llm, body.text)

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

    @app.post("/agents/{agent_id}/run")
    def run_now(agent_id: int, session=Depends(get_session)):
        agent = get_agent(agent_id, session)
        if agent.status != "active":
            agent.status = "active"  # run-now implies activation for draft agents
            session.commit()
        run = run_agent_once(session_factory, agent_id, runtime, trigger="manual",
                             now=datetime.now(timezone.utc))
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

    @app.post("/uploads/csv", status_code=201)
    def upload_csv(file: UploadFile, session=Depends(get_session)):
        content = file.file.read()
        rows = list(csv_mod.DictReader(io.StringIO(content.decode("utf-8"))))
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / "sales_report.csv"  # single-slot MVP: latest upload wins
        path.write_bytes(content)
        session.add(Connection(provider="csv", credentials={"path": str(path)}))
        session.commit()
        return {"path": str(path), "rows": len(rows)}

    return app


def create_default_app() -> FastAPI:
    """uvicorn factory entrypoint: uvicorn "aunix.api:create_default_app" --factory"""
    settings = Settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    return create_app(
        session_factory=make_session_factory(engine),
        llm=AnthropicLlm(model=settings.llm_model),
        runtime=Runtime(settings),
        upload_dir=Path(settings.upload_dir),
        cors_origins=settings.api_cors_origins,
    )

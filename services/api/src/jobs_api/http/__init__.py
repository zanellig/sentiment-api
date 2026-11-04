"""HTTP transport. Behind the gateway, which authenticates the Tenant (ADR-0020)."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from jobs_api import jobs

app = FastAPI(title="Jobs API")


def current_tenant(x_consumer_username: Annotated[str | None, Header()] = None) -> str:
    """The Tenant the gateway authenticated; without it the request skipped the gateway."""
    if not x_consumer_username:
        raise HTTPException(401, "Missing X-Consumer-Username")
    return x_consumer_username


Tenant = Annotated[str, Depends(current_tenant)]


class TextJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texts: list[str] = Field(min_length=1)
    lang: Literal["es", "en", "it", "pt"]  # one analyze.<lang> queue each (ADR-0007)


@app.post("/jobs", status_code=202)
def create_job(body: TextJob, tenant: Tenant) -> dict:
    return {"job_id": jobs.create_text_job(tenant, body.texts, body.lang), "state": "analyzing"}


@app.get("/jobs/{job_id}")
def get_job(job_id: UUID, tenant: Tenant) -> dict:
    job = jobs.read_job(tenant, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job

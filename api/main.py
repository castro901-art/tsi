import asyncio
import hashlib
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from api import config, store
from api.auth import current_user, router as auth_router
from api.schemas import MatchInput
from api.video import VideoError, probe

ERRORS = {
    "provider_not_configured": "Configure a server-side provider key and model before submitting footage.",
    "provider_terms_not_accepted": "Review provider billing and footage-handling terms, then enable processing explicitly.",
    "account_analysis_limit": "This account has reached its five-analysis development limit.",
    "storage_limit": "This development instance has reached its 20-analysis storage limit.",
}


@asynccontextmanager
async def lifespan(app):
    store.init()
    yield


app = FastAPI(title="TSI API", version=config.PIPELINE_VERSION, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(auth_router)

def job(job_id, owner_id):
    try:
        UUID(job_id)
    except ValueError:
        raise HTTPException(404, "Analysis not found")
    item = store.get(job_id)
    if not item or item["owner_id"] != owner_id:
        raise HTTPException(404, "Analysis not found")
    return item


@app.get("/health")
def health():
    return {"status": "ok", "version": config.PIPELINE_VERSION}


@app.get("/v1/capabilities")
def capabilities(user=Depends(current_user)):
    return {"sources": ["mp4_upload"], "url_ingestion": False, "max_bytes": config.MAX_BYTES, "max_seconds": config.MAX_SECONDS, "movement_tracking": False, "account_authentication": True}


@app.post("/v1/analyses", status_code=201)
def create(metadata: MatchInput, user=Depends(current_user)):
    try:
        config.provider_config()
        job_id = store.create(metadata.model_dump(), user["id"])
    except RuntimeError as exc:
        code = str(exc)
        raise HTTPException(429 if code in ("storage_limit", "account_analysis_limit") else 503, detail={"code": code, "message": ERRORS.get(code, "Configuration unavailable.")})
    return {"id": job_id, "status": "awaiting_upload", "upload_path": f"/v1/analyses/{job_id}/video"}


@app.put("/v1/analyses/{job_id}/video", status_code=202)
async def upload(job_id: str, request: Request, user=Depends(current_user)):
    job(job_id, user["id"])
    if request.headers.get("content-type", "").split(";")[0] != "video/mp4":
        raise HTTPException(415, detail={"code": "unsupported_source", "message": "Send an authorised MP4 file as video/mp4. URLs and multipart uploads are not supported yet."})
    if not store.transition(job_id, "awaiting_upload", "uploading"):
        raise HTTPException(409, "This analysis no longer accepts an upload.")
    path = config.DATA / f"{job_id}.mp4"
    digest = hashlib.sha256()
    size = 0
    success = False
    error_code = "upload_failed"
    try:
        with path.open("xb") as target:
            async for chunk in request.stream():
                size += len(chunk)
                if size > config.MAX_BYTES:
                    raise HTTPException(413, detail={"code": "size_limit", "message": "Maximum upload size is 100 MiB."})
                target.write(chunk)
                digest.update(chunk)
        duration = await asyncio.to_thread(probe, path)
        if not store.transition(job_id, "uploading", "queued", duration=duration, sha256=digest.hexdigest()):
            raise HTTPException(409, "Upload state changed; create a new analysis.")
        success = True
        return {"id": job_id, "status": "queued", "duration_seconds": duration}
    except VideoError as exc:
        error_code = str(exc)
        raise HTTPException(422, detail={"code": str(exc), "message": "Video validation failed. Use an MP4 with a video stream, up to 10 minutes and 3840x2160."})
    except HTTPException as exc:
        if isinstance(exc.detail, dict):
            error_code = exc.detail["code"]
        raise
    finally:
        if not success:
            path.unlink(missing_ok=True)
            store.transition(job_id, "uploading", "failed", error=error_code)


@app.get("/v1/analyses")
def listing(user=Depends(current_user)):
    with store.connection() as db:
        rows = db.execute("SELECT id,status,created,error FROM analyses WHERE owner_id=? ORDER BY created DESC", (user["id"],)).fetchall()
    return [dict(row) for row in rows]


@app.get("/v1/analyses/{job_id}")
def detail(job_id: str, user=Depends(current_user)):
    return job(job_id, user["id"])


@app.get("/v1/analyses/{job_id}/report", response_class=PlainTextResponse)
def report(job_id: str, user=Depends(current_user)):
    item = job(job_id, user["id"])
    if item["status"] != "completed":
        raise HTTPException(409, "Analysis has not completed.")
    result = item["result"]
    lines = [item["metadata"]["title"], "TSI | Trendify Labs", f"Source upload: {job_id}", f"Analysis date (Unix UTC): {result['analysed_at']}", "Verification: model candidates; not human-verified", "", "LIMITATIONS", *result["limitations"], "", "CANDIDATE OBSERVATIONS"]
    for event in result["events"]:
        lines.append(f"[{event['id']}] {event['start_seconds']:.1f}-{event['end_seconds']:.1f}s | {event['event_type']} | {event['observation']}")
    lines += ["", "TACTICAL INTERPRETATIONS (UNVERIFIED)"]
    for claim in result["interpretations"]:
        lines.append(f"{claim['section']}: {claim['text']} [Evidence: {', '.join(claim['evidence_ids'])}]")
    return "\n".join(lines)


@app.api_route("/v1/analyses/{job_id}/video", methods=["GET", "HEAD"])
def playback(job_id: str, user=Depends(current_user)):
    item = job(job_id, user["id"])
    path = config.DATA / f"{job_id}.mp4"
    if item["status"] not in ("queued", "processing", "completed") or not path.is_file():
        raise HTTPException(404, "Video unavailable")
    return FileResponse(path, media_type="video/mp4", headers={
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
    })

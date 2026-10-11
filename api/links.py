"""Authorised platform imports via an operator-approved resolver, never scraping.
The resolver must use permitted access methods and return a direct HTTPS MP4 URL.
No resolver, credentials, payment, or platform access is provisioned by this app.
"""
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import time
from urllib.parse import urlsplit, parse_qs, urlunsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from api import config, store
from api.auth import current_user
from api.schemas import StrictModel, MatchInput
from api.video import probe, VideoError

router = APIRouter()


class LinkInput(StrictModel):
    url: str = Field(min_length=1, max_length=2048)
    metadata: MatchInput


class LinkError(Exception):
    pass


def canonical_source(value):
    try:
        p = urlsplit(value.strip())
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            raise ValueError()
        host = (p.hostname or "").lower()
        if host in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"):
            if host == "youtu.be":
                video_id = p.path.strip("/")
            elif p.path == "/watch":
                video_id = parse_qs(p.query).get("v", [""])[0]
            else:
                match = re.fullmatch(r"/(?:shorts|embed)/([A-Za-z0-9_-]{11})/?", p.path)
                video_id = match[1] if match else ""
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise ValueError()
            return "youtube", f"https://www.youtube.com/watch?v={video_id}"
        if host in ("x.com", "www.x.com", "twitter.com", "www.twitter.com"):
            match = re.fullmatch(r"/([A-Za-z0-9_]{1,15})/status/([0-9]{1,25})(?:/video/[0-9]+)?/?", p.path)
            if not match:
                raise ValueError()
            return "x", f"https://x.com/{match[1]}/status/{match[2]}"
    except (ValueError, TypeError):
        pass
    raise LinkError("Use a public YouTube video or X post URL. Other platforms are not supported.")


def settings():
    endpoint = os.getenv("TSI_LINK_RESOLVER_URL", "")
    hosts = {h.strip().lower() for h in os.getenv("TSI_LINK_MEDIA_HOSTS", "").split(",") if h.strip()}
    return endpoint, hosts


def link_capabilities():
    endpoint, hosts = settings()
    return {"url_ingestion": bool(endpoint and hosts), "link_platforms": ["youtube", "x"],
            "link_access_note": "YouTube/X imports require an operator-configured, permitted-access resolver. No platform downloader or paid service is enabled automatically."}


class PinnedHTTPS(http.client.HTTPSConnection):
    """Pin a validated public IP while preserving hostname verification and SNI."""
    def __init__(self, hostname, address):
        super().__init__(hostname, timeout=10, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        self.sock = socket.create_connection((self.address, 443), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def connection(value, allowed):
    try:
        p = urlsplit(value)
        host = (p.hostname or "").lower()
        if (p.scheme != "https" or host not in allowed or p.username or p.password
                or p.port not in (None, 443) or p.fragment or any(ord(c) < 33 for c in value)):
            raise LinkError("Source host or URL is not permitted.")
        addresses = {row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise LinkError("Private or non-public network destinations are blocked.")
        return PinnedHTTPS(host, sorted(addresses)[0]), urlunsplit(("", "", p.path or "/", p.query, ""))
    except (ValueError, OSError) as exc:
        raise LinkError("Source URL could not be validated.") from exc


def resolve(source):
    endpoint, _ = settings()
    host = urlsplit(endpoint).hostname
    conn, path = connection(endpoint, {host})
    token = os.getenv("TSI_LINK_RESOLVER_TOKEN", "")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        conn.request("POST", path, body=json.dumps({"url": source, "authorised": True}), headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            raise LinkError("Platform access denied or unavailable. Upload the authorised MP4 instead.")
        body, deadline = b"", time.monotonic() + 30
        while True:
            if time.monotonic() > deadline:
                raise LinkError("Resolver timed out.")
            chunk = response.read1(min(4096, 16385 - len(body)))
            if not chunk:
                break
            body += chunk
            if len(body) > 16384:
                raise LinkError("Resolver response is too large.")
        data = json.loads(body)
        if not isinstance(data, dict) or not isinstance(data.get("mp4_url"), str) or len(data["mp4_url"]) > 8192:
            raise LinkError("Resolver did not return an authorised MP4 source.")
        return data["mp4_url"]
    finally:
        conn.close()


def download(url, target):
    _, hosts = settings()
    conn, path = connection(url, hosts)
    digest, size, deadline = hashlib.sha256(), 0, time.monotonic() + 120
    try:
        conn.request("GET", path, headers={"Accept": "video/mp4", "Accept-Encoding": "identity"})
        response = conn.getresponse()
        # Redirects are intentionally rejected; never forward credentials to media hosts.
        if response.status != 200 or response.getheader("Content-Type", "").split(";")[0].strip().lower() != "video/mp4":
            raise LinkError("An accessible direct MP4 is required; redirects and HTML pages are rejected.")
        if response.getheader("Content-Encoding", "identity") != "identity":
            raise LinkError("Compressed downloads are not supported.")
        length = response.getheader("Content-Length")
        if length and (not length.isdigit() or int(length) > config.MAX_BYTES):
            raise LinkError("Linked video exceeds the configured size limit.")
        with target.open("xb") as out:
            while True:
                if time.monotonic() > deadline:
                    raise LinkError("Linked video download timed out.")
                chunk = response.read1(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.MAX_BYTES:
                    raise LinkError("Linked video exceeds the configured size limit.")
                out.write(chunk)
                digest.update(chunk)
        if not size or (length and size != int(length)):
            raise LinkError("Linked video is empty or incomplete.")
        return digest.hexdigest()
    finally:
        conn.close()


@router.post("/v1/analyses/from-link", status_code=202)
def import_link(data: LinkInput, user=Depends(current_user)):
    try:
        platform, source = canonical_source(data.url)
    except LinkError as exc:
        raise HTTPException(422, str(exc))
    if not link_capabilities()["url_ingestion"]:
        raise HTTPException(503, "YouTube/X importing is not configured on this server. Upload an authorised MP4 instead.")
    try:
        config.provider_config()
        job_id = store.create({**data.metadata.model_dump(), "source_url": source, "source_platform": platform}, user["id"])
    except RuntimeError as exc:
        code = str(exc)
        raise HTTPException(429 if code in ("account_analysis_limit", "storage_limit") else 503, {"code": code, "message": "Analysis configuration or account capacity unavailable."})
    store.transition(job_id, "awaiting_upload", "uploading")
    target = config.DATA / f"{job_id}.mp4"
    try:
        sha = download(resolve(source), target)
        duration = probe(target)
        if not store.transition(job_id, "uploading", "queued", duration=duration, sha256=sha):
            raise LinkError("Analysis state changed during import.")
        return {"id": job_id, "status": "queued", "source_platform": platform}
    except (LinkError, VideoError, OSError, ValueError, http.client.HTTPException) as exc:
        target.unlink(missing_ok=True)
        store.transition(job_id, "uploading", "failed", error="link_import_failed")
        # Do not expose signed media URLs, resolver tokens or raw network errors.
        text = str(exc) if isinstance(exc, LinkError) else "Linked video import or validation failed. Upload the authorised MP4 instead."
        raise HTTPException(422, {"code": "link_import_failed", "message": text, "job_id": job_id})

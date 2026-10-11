import time
from uuid import uuid4
from api import config, store
from api.provider import GeminiProvider, ProviderError

LIMITATIONS = [
    "Highlights are incomplete and edited; conclusions apply only to visible sequences.",
    "Events and interpretations are model-generated candidates, not human-verified facts.",
    "Confidence scores are uncalibrated model estimates.",
    "No full-match statistics, verified player identities or movement tracking are available.",
]


def process(job_id, provider):
    item = store.get(job_id)
    try:
        findings = provider.analyse(config.DATA / f"{job_id}.mp4").validate_evidence(item["duration"])
        ids = [str(uuid4()) for _ in findings.events]
        events = []
        for event_id, event in zip(ids, findings.events):
            events.append({**event.model_dump(), "id": event_id, "match_id": job_id, "verification_status": "unverified", "team_id": None, "player_id": None,
                           "source_reference": {"upload_id": job_id, "sha256": item["sha256"], "timestamp_basis": "source_video_seconds", "source_url": item["metadata"].get("source_url"), "source_platform": item["metadata"].get("source_platform")},
                           "model": provider.model, "pipeline_version": config.PIPELINE_VERSION})
        interpretations = [{"section": c.section, "text": c.text, "evidence_ids": [ids[i] for i in c.event_indices], "kind": "model_interpretation", "verification_status": "unverified"} for c in findings.interpretations]
        store.transition(job_id, "processing", "completed", result={"events": events, "interpretations": interpretations, "limitations": LIMITATIONS + findings.limitations, "analysed_at": time.time(), "model": provider.model, "pipeline_version": config.PIPELINE_VERSION})
    except ProviderError as exc:
        store.transition(job_id, "processing", "failed", error=exc.code)
    except ValueError:
        store.transition(job_id, "processing", "failed", error="invalid_provider_evidence")
    except Exception:
        store.transition(job_id, "processing", "failed", error="processing_failed")


def main():
    store.init()
    # Fail before claiming jobs if credentials/consent have not been configured.
    config.provider_config()
    while True:
        store.maintenance()
        job_id = store.claim()
        if job_id:
            try:
                provider = GeminiProvider()
            except Exception:
                store.transition(job_id, "processing", "failed", error="provider_not_configured")
                continue
            process(job_id, provider)
        else:
            time.sleep(2)


if __name__ == "__main__":
    main()

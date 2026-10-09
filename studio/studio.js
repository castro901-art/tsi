// No demo data or client-side analysis. Findings come only from completed API jobs.
const $ = id => document.getElementById(id);
const labels = {
  awaiting_upload: "Awaiting upload — no analysis has run.",
  uploading: "Uploading — the server is receiving or validating footage.",
  queued: "Queued — waiting for a running worker. No results yet.",
  processing: "Processing — provider analysis is running. No results yet.",
  completed: "Completed — review unverified model candidates below.",
  failed: "Failed — no analysis results are available."
};
let session = null, capabilities = null, selected = null, timer = null;
let epoch = 0, busy = false, selectionVersion = 0, statusRequestVersion = 0, renderedResult = null;
const pending = new Set();
const uuid = value => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
function message(id, text = "") { $(id).textContent = text; $(id).hidden = !text; }
function errorText(data, status) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(e => `${e.loc?.slice(1).join(".") || "Input"}: ${e.msg}`).join("; ");
  if (detail?.message) return `${detail.message}${detail.code ? ` [${detail.code}]` : ""}`;
  return `Request failed (HTTP ${status}). No results were substituted.`;
}
async function api(path, options = {}) {
  const requestEpoch = epoch, controller = new AbortController();
  const deadline = setTimeout(() => controller.abort(), options.body instanceof File ? 180000 : 20000);
  pending.add(controller);
  const headers = new Headers(options.headers);
  if (options.method && options.method !== "GET" && session) headers.set("X-TSI-CSRF", session.csrf_token);
  try {
    const response = await fetch(path, {...options, headers, signal: controller.signal, credentials: "same-origin", cache: "no-store"});
    if (requestEpoch !== epoch) throw new Error("Session changed; stale response ignored.");
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      if (response.status === 401 && session) { signOutLocally(); message("notice", "Your session expired. Sign in again to continue."); }
      throw new Error(errorText(data, response.status));
    }
    return data;
  } catch (e) {
    if (e.name === "AbortError") throw new Error("Request cancelled or timed out. Check the saved job status before resubmitting; its server state is unknown.");
    if (e instanceof TypeError) throw new Error("Network unavailable. No results were substituted. Check status when the connection returns.");
    throw e;
  } finally { clearTimeout(deadline); pending.delete(controller); }
}
const jsonOptions = (method, data) => ({method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
function clearReview() {
  clearTimeout(timer); renderedResult = null;
  $("results").hidden = $("events-panel").hidden = $("resume").hidden = true;
  $("events").replaceChildren(); $("interpretations").replaceChildren(); $("limitations").replaceChildren();
  $("report").removeAttribute("href");
  $("video").pause(); $("video").removeAttribute("src"); $("video").load(); $("video").hidden = true;
  $("video-note").textContent = ""; message("job-error");
}
function signOutLocally() {
  epoch++; selectionVersion++; session = capabilities = selected = null;
  for (const c of pending) c.abort();
  clearReview(); $("review").hidden = true; $("workspace").hidden = true; $("auth").hidden = false;
  $("logout").hidden = true; $("username").textContent = "";
  $("analyses").replaceChildren(); $("analysis-form").reset(); $("auth-password").value = "";
  setBusy(false);
}
function setBusy(value) {
  busy = value; $("inputs").disabled = value;
  $("start").disabled = value || !capabilities;
  $("resume-upload").disabled = value || !capabilities;
  $("logout").disabled = value;
  for (const button of $("analyses").querySelectorAll("button")) button.disabled = value;
}
async function loadCapabilities() {
  capabilities = null; setBusy(busy);
  try {
    const data = await api("/v1/capabilities");
    if (!data.sources?.includes("mp4_upload") || !Number.isFinite(data.max_bytes) || !Number.isFinite(data.max_seconds)) throw new Error("MP4 upload capabilities are unavailable.");
    capabilities = data;
    $("limits").textContent = `MP4 only · up to ${data.max_bytes / 1048576} MiB · ${data.max_seconds / 60} minutes · server validates video. Maximum resolution: 3840×2160.`;
  } catch (e) { $("limits").textContent = "Source limits unavailable. Uploads are disabled; use Refresh list to retry."; throw e; }
  finally { setBusy(busy); }
}
async function listAnalyses() {
  const version = epoch, rows = await api("/v1/analyses");
  if (version !== epoch) return;
  $("analyses").replaceChildren();
  $("list-note").textContent = rows.length ? "Saved automatically by the API. Select a job to check its current state." : "No analyses yet. Upload authorised footage to begin.";
  for (const row of rows) {
    if (!uuid(row.id)) continue;
    const li = document.createElement("li"), button = document.createElement("button");
    button.type = "button"; button.disabled = busy; button.dataset.id = row.id;
    button.setAttribute("aria-current", String(row.id === selected));
    button.textContent = `${row.id.slice(0, 8)} · ${row.status} · ${new Date(row.created * 1000).toLocaleString()}`;
    button.addEventListener("click", () => openJob(row.id)); li.append(button); $("analyses").append(li);
  }
}
async function enterWorkspace(data) {
  session = data; $("auth-password").value = "";
  $("auth").hidden = true; $("workspace").hidden = false; $("logout").hidden = false;
  $("username").textContent = data.user.username; message("notice");
  await loadCapabilities(); await listAnalyses();
}
function add(parent, tag, text) { const node = document.createElement(tag); node.textContent = text; parent.append(node); return node; }
function seconds(value) { return `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, "0")}`; }
function seek(event) {
  const video = $("video");
  if (!video.getAttribute("src") || video.hidden) return;
  const go = () => { video.currentTime = event.start_seconds; video.focus(); };
  if (video.readyState >= 1) go(); else video.addEventListener("loadedmetadata", go, {once: true});
}
function evidenceButton(parent, event, text) {
  const button = add(parent, "button", text); button.type = "button"; button.addEventListener("click", () => seek(event));
}
function renderJob(item) {
  if (item.id !== selected) return;
  $("review-title").textContent = item.metadata?.title || "Analysis";
  $("job-id").textContent = `Source upload: ${item.id}`;
  $("status").textContent = labels[item.status] || `Unknown server state: ${item.status}. No results displayed.`;
  $("resume").hidden = item.status !== "awaiting_upload" || busy;
  message("job-error", item.status === "failed" ? `Server error: ${item.error || "unspecified_failure"}. Correct the cause before starting a new analysis. No automatic retry or provider fallback.` : "");
  const playable = ["queued", "processing", "completed"].includes(item.status);
  const video = $("video"), path = `/v1/analyses/${item.id}/video`;
  if (playable && video.getAttribute("src") !== path) { video.src = path; video.hidden = false; }
  if (!playable && video.hasAttribute("src")) { video.pause(); video.removeAttribute("src"); video.load(); video.hidden = true; }
  $("video-note").textContent = playable ? "Protected source footage · pause and scrub with the player controls." : "Playback is available after the API accepts your upload.";
  if (item.status !== "completed") {
    $("results").hidden = $("events-panel").hidden = true; $("report").removeAttribute("href"); renderedResult = null; return;
  }
  const result = item.result;
  if (!result || !Array.isArray(result.events) || !Array.isArray(result.interpretations) || !Array.isArray(result.limitations)) {
    $("results").hidden = $("events-panel").hidden = true;
    $("report").removeAttribute("href"); message("job-error", "Completed job has no valid structured results. No sample results were substituted."); return;
  }
  if (renderedResult === item.id) return;
  renderedResult = item.id; $("events").replaceChildren(); $("interpretations").replaceChildren(); $("limitations").replaceChildren();
  $("results").hidden = $("events-panel").hidden = false;
  if (!result.events.length) add($("events"), "li", "The provider returned no candidate observations. This does not establish that no events occurred.");
  const evidence = new Map(result.events.map(e => [e.id, e]));
  result.events.forEach((event, index) => {
    const li = add($("events"), "li", "");
    evidenceButton(li, event, `Evidence ${index + 1} · ${seconds(event.start_seconds)}–${seconds(event.end_seconds)} · ${event.event_type.replaceAll("_", " ")}`);
    add(li, "p", event.observation);
    add(li, "p", `Unverified · model estimate ${Math.round(event.confidence * 100)}% · Event ${event.id}`).className = "muted";
    add(li, "p", `Upload ${event.source_reference?.upload_id || item.id} · SHA-256 ${event.source_reference?.sha256 || "unavailable"}`).className = "muted";
  });
  for (const limit of result.limitations) add($("limitations"), "li", limit);
  if (!result.interpretations.length) add($("interpretations"), "p", "No supported tactical interpretations were returned.");
  for (const claim of result.interpretations) {
    const section = add($("interpretations"), "section", ""); add(section, "h4", claim.section.replaceAll("_", " "));
    add(section, "p", claim.text);
    for (const id of claim.evidence_ids || []) {
      const event = evidence.get(id);
      if (event) evidenceButton(section, event, `Evidence ${result.events.indexOf(event) + 1} · ${seconds(event.start_seconds)}`);
      else add(section, "p", `Missing evidence reference: ${id}`);
    }
  }
  $("provenance").textContent = `Model: ${result.model} · Pipeline: ${result.pipeline_version} · Analysed: ${new Date(result.analysed_at * 1000).toISOString()} · Model candidates, not human-verified facts.`;
  $("report").href = `/v1/analyses/${item.id}/report`;
}
async function checkJob(id = selected, version = selectionVersion) {
  if (!id || !session) return;
  clearTimeout(timer);
  const requestVersion = ++statusRequestVersion;
  try {
    const item = await api(`/v1/analyses/${id}`);
    if (id !== selected || version !== selectionVersion || requestVersion !== statusRequestVersion) return;
    renderJob(item);
    if (["uploading", "queued", "processing"].includes(item.status)) timer = setTimeout(() => checkJob(id, version), 2000);
  } catch (e) {
    if (id === selected && version === selectionVersion && requestVersion === statusRequestVersion && session) {
      $("results").hidden = $("events-panel").hidden = true; $("report").removeAttribute("href");
      $("status").textContent = "Current server state unavailable. Last known state is not confirmation of progress.";
      message("job-error", `${e.message} Use Check status to reconnect.`);
    }
  }
}
async function openJob(id) {
  if (busy || !uuid(id)) return;
  selected = id; selectionVersion++; clearReview(); $("review").hidden = false;
  $("review-title").textContent = "Loading saved analysis…"; $("job-id").textContent = id;
  $("status").textContent = "Reading current server state…";
  for (const button of $("analyses").querySelectorAll("button")) button.setAttribute("aria-current", String(button.dataset.id === id));
  await checkJob();
}
function chosenFile() {
  const form = $("analysis-form"), file = $("file").files[0];
  if (!capabilities) throw new Error("Load source capabilities before uploading.");
  if (!file || !/\.mp4$/i.test(file.name) || (file.type && file.type !== "video/mp4")) throw new Error("Choose an authorised MP4 file. URLs are not supported.");
  if (!file.size || file.size > capabilities.max_bytes) throw new Error(`Choose a non-empty MP4 up to ${capabilities.max_bytes / 1048576} MiB.`);
  if (!form.elements.authorised.checked || !form.elements.provider_processing_consent.checked) throw new Error("Both authorisation and provider processing consent are required.");
  return file;
}
async function uploadFile(id, file) {
  $("status").textContent = "Sending upload — awaiting server acceptance. This is not analysis progress.";
  await api(`/v1/analyses/${id}/video`, {method: "PUT", headers: {"Content-Type": "video/mp4"}, body: file});
}
$("auth-form").addEventListener("submit", async event => {
  event.preventDefault(); const buttons = [...$("auth-form").querySelectorAll("button")];
  buttons.forEach(b => b.disabled = true); message("notice");
  try { await enterWorkspace(await api(`/v1/auth/${event.submitter?.id === "register" ? "register" : "login"}`, jsonOptions("POST", {username: $("auth-name").value.trim(), password: $("auth-password").value}))); }
  catch (e) { message("notice", e.message); } finally { buttons.forEach(b => b.disabled = false); }
});
$("logout").addEventListener("click", async () => {
  try { await api("/v1/auth/logout", {method: "POST"}); signOutLocally(); message("notice"); }
  catch (e) { message("notice", e.message); }
});
$("refresh").addEventListener("click", async () => {
  try { message("notice"); if (!capabilities) await loadCapabilities(); await listAnalyses(); }
  catch (e) { message("notice", e.message); }
});
$("retry").addEventListener("click", () => checkJob());
$("analysis-form").addEventListener("submit", async event => {
  event.preventDefault(); if (busy) return;
  let file;
  try { file = chosenFile(); } catch (e) { message("notice", e.message); return; }
  const data = new FormData(event.target), metadata = {title: data.get("title").trim(), authorised: true, provider_processing_consent: true};
  if (!metadata.title) { message("notice", "Enter an analysis title."); return; }
  for (const name of ["home_team", "away_team", "competition", "match_date"]) metadata[name] = data.get(name).trim() || null;
  message("notice"); clearTimeout(timer); setBusy(true);
  let created = false;
  try {
    const item = await api("/v1/analyses", jsonOptions("POST", metadata));
    if (!uuid(item.id) || item.upload_path !== `/v1/analyses/${item.id}/video`) throw new Error("Unexpected upload route; no file was sent.");
    selected = item.id; selectionVersion++; created = true; clearReview(); $("review").hidden = false;
    renderJob({...item, metadata}); await uploadFile(item.id, file);
  } catch (e) { message("notice", e.message); }
  finally {
    setBusy(false);
    if (session) { if (created) await checkJob(); try { await listAnalyses(); } catch (e) { message("notice", e.message); } }
  }
});
$("resume-upload").addEventListener("click", async () => {
  if (busy || !selected) return;
  try {
    const file = chosenFile(); message("notice"); setBusy(true); clearTimeout(timer);
    await uploadFile(selected, file);
  } catch (e) { message("notice", e.message); }
  finally { setBusy(false); if (session) await checkJob(); }
});
$("video").addEventListener("error", () => { $("video-note").textContent = "Source playback unavailable or unsupported by this browser. No substitute video is shown."; });
try { await enterWorkspace(await api("/v1/auth/me")); }
catch (e) { if (e.message !== "Sign in to continue") message("notice", e.message); }

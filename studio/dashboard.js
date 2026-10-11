// Presentation enhancements; existing studio.js remains authoritative for sessions,
// MP4 ingestion, recovery, polling, protected playback and evidence rendering.
const $ = id => document.getElementById(id);
let mode = 'file', importing = false, generation = 0;
const statusNames = {awaiting_upload:'Awaiting footage',uploading:'Importing footage',queued:'Queued',processing:'Processing',completed:'Completed',failed:'Failed'};
function notice(text) { $('notice').textContent = text; $('notice').hidden = !text; }
function selectMode(value) {
  if (importing || $('inputs').disabled) return;
  mode = value;
  $('file-fields').hidden = value !== 'file'; $('link-fields').hidden = value !== 'link';
  $('file').required = value === 'file'; $('source-link').required = value === 'link';
  $('source-link').disabled = value !== 'link';
  for (const b of document.querySelectorAll('[data-source-mode]')) b.setAttribute('aria-pressed', String(b.dataset.sourceMode === value));
  $('start').textContent = value === 'file' ? 'Upload & start analysis' : 'Import link & start analysis';
}
for (const b of document.querySelectorAll('[data-source-mode]')) b.addEventListener('click', () => selectMode(b.dataset.sourceMode));
function fileInfo() {
  const file = $('file').files[0];
  $('file-info').textContent = file ? `${file.name} · ${(file.size / 1048576).toFixed(1)} MiB` : 'No file selected.';
}
$('file').addEventListener('change', fileInfo);
$('analysis-form').addEventListener('reset', () => setTimeout(fileInfo));
const zone = $('upload-zone');
zone.addEventListener('dragover', e => { e.preventDefault(); if (!$('inputs').disabled) zone.classList.add('dragging'); });
zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
zone.addEventListener('drop', e => {
  e.preventDefault(); zone.classList.remove('dragging');
  if ($('inputs').disabled) return;
  const file = e.dataTransfer.files[0];
  if (!file) return;
  try { const d = new DataTransfer(); d.items.add(file); $('file').files = d.files; fileInfo(); }
  catch { notice('Use the file chooser to select your authorised MP4.'); }
});
function filterLibrary() {
  const q = $('match-search').value.trim().toLowerCase(); let shown = 0;
  for (const li of $('analyses').children) { li.hidden = !li.textContent.toLowerCase().includes(q); if (!li.hidden) shown++; }
  $('search-empty').hidden = !q || shown > 0;
}
$('match-search').addEventListener('input', filterLibrary);
let libraryVersion = 0;
async function decorateLibrary() {
  if ($('workspace').hidden || !$('analyses').children.length) return;
  const buttons = [...$('analyses').querySelectorAll('button')];
  if (buttons.every(b => b.dataset.decorated)) { filterLibrary(); return; }
  const version = ++libraryVersion, view = generation;
  try {
    const res = await fetch('/v1/analyses', {credentials:'same-origin',cache:'no-store'});
    if (!res.ok) return;
    const rows = await res.json();
    if (version !== libraryVersion || view !== generation || $('workspace').hidden) return;
    const map = new Map(rows.map(r => [r.id,r]));
    for (const b of buttons) {
      if (!b.isConnected) continue;
      const row = map.get(b.dataset.id); if (!row) continue;
      const m = row.metadata || {};
      const title = document.createElement('span'); title.className = 'match-title'; title.textContent = m.title || `Analysis ${row.id.slice(0,8)}`;
      const meta = document.createElement('span'); meta.className = 'match-meta';
      meta.textContent = [m.home_team && m.away_team ? `${m.home_team} vs ${m.away_team}` : '',m.competition,m.match_date || new Date(row.created*1000).toLocaleDateString()].filter(Boolean).join(' · ');
      const status = document.createElement('span'); status.className = 'match-status'; status.dataset.state = row.status; status.textContent = statusNames[row.status] || 'Unknown state';
      b.replaceChildren(title,meta,status); b.dataset.decorated='true';
    }
    filterLibrary();
  } catch { /* Existing studio client displays authoritative request errors. */ }
}
let libraryTimer;
new MutationObserver(() => { clearTimeout(libraryTimer); libraryTimer=setTimeout(decorateLibrary,30); }).observe($('analyses'),{childList:true,subtree:true});
new MutationObserver(() => {
  const b = $('analyses').querySelector('button[aria-current="true"] .match-status');
  if (b) {
    const state = Object.keys(statusNames).find(s => $('status').textContent.toLowerCase().startsWith(s.replaceAll('_',' ')));
    if (state) { b.dataset.state=state; b.textContent=statusNames[state]; }
  }
}).observe($('status'),{childList:true});
$('toggle-evidence').addEventListener('click', () => {
  const content = $('evidence-content'); content.hidden = !content.hidden;
  $('toggle-evidence').textContent = content.hidden ? 'Expand' : 'Collapse';
  $('toggle-evidence').setAttribute('aria-expanded',String(!content.hidden));
});
for (const link of document.querySelectorAll('.nav-item,.mobile-nav a')) link.addEventListener('click', () => {
  for (const item of document.querySelectorAll('.nav-item,.mobile-nav a')) item.classList.toggle('active',item.hash===link.hash);
});
const form = $('analysis-form');
form.addEventListener('submit', async e => {
  if (mode !== 'link') return; // Let the existing MP4 workflow run unchanged.
  e.preventDefault(); e.stopImmediatePropagation();
  if (importing || $('inputs').disabled) return;
  if (!form.reportValidity()) return;
  const data = new FormData(form), metadata = {title:data.get('title').trim(),authorised:data.get('authorised')==='on',provider_processing_consent:data.get('provider_processing_consent')==='on'};
  if (!metadata.title) { notice('Enter an analysis title.'); return; }
  for (const name of ['home_team','away_team','competition','match_date']) metadata[name] = data.get(name).trim() || null;
  const url = $('source-link').value.trim(), view = generation;
  importing=true; $('inputs').disabled=true; $('logout').disabled=true;
  $('start').textContent='Importing authorised footage…'; notice('Importing link. This is footage ingestion, not analysis progress. Do not resubmit.');
  const controller = new AbortController(), timeout=setTimeout(()=>controller.abort(),180000);
  let jobId = null;
  try {
    const auth = await fetch('/v1/auth/me',{credentials:'same-origin',cache:'no-store',signal:controller.signal});
    if (!auth.ok) throw new Error('Your session is unavailable. Sign in again.');
    const session=await auth.json();
    const response = await fetch('/v1/analyses/from-link',{method:'POST',credentials:'same-origin',signal:controller.signal,
      headers:{'Content-Type':'application/json','X-TSI-CSRF':session.csrf_token},body:JSON.stringify({url,metadata})});
    const result=await response.json(); jobId=result.id || result.detail?.job_id;
    if (!response.ok) throw new Error(typeof result.detail==='string' ? result.detail : result.detail?.message || 'Link import failed. Upload the authorised MP4 instead.');
    if (view===generation) notice('Footage accepted and queued. A running worker is required for analysis.');
  } catch (err) {
    if (view===generation) notice(err.name==='AbortError' ? 'Import timed out; server state is unknown. Refresh the library before trying again.' : err.message);
  } finally {
    clearTimeout(timeout); importing=false;
    if (view===generation && !$('workspace').hidden) {
      $('inputs').disabled=false; $('logout').disabled=false; $('start').textContent='Import link & start analysis';
      $('refresh').click();
      if (jobId) {
        const observer=new MutationObserver(()=>{
          const b=[...$('analyses').querySelectorAll('button')].find(b=>b.dataset.id===jobId);
          if(b) {observer.disconnect(); if(view===generation) b.click();}
        }); observer.observe($('analyses'),{childList:true}); setTimeout(()=>observer.disconnect(),5000);
      }
    }
  }
},true);
new MutationObserver(() => {
  generation++; libraryVersion++;
  if (document.body.dataset.view==='auth') {
    $('match-search').value=''; $('source-link').value=''; $('file-info').textContent='No file selected.'; selectMode('file'); return;
  }
  const view=generation;
  fetch('/v1/capabilities',{credentials:'same-origin',cache:'no-store'}).then(r=>r.ok?r.json():null).then(c=>{
    if (!c || view!==generation) return;
    $('link-note').textContent=c.url_ingestion ? 'YouTube and X links · permitted access only · imported MP4s must meet the same source limits.' : 'YouTube/X importing needs an operator-configured permitted-access resolver. Until configured, use an authorised MP4 upload. Links do not grant download permission.';
  }).catch(()=>{});
}).observe(document.body,{attributes:true,attributeFilter:['data-view']});

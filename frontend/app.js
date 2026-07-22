const API = 'http://localhost:8000/api';

// ── State ──────────────────────────────────────────────────────────────────
let resumeData = null;
let allJobs = [];
let activeScoreFilter = 'all';
let selectedWorkMode = 'Any';

// ── DOM refs ───────────────────────────────────────────────────────────────
const uploadZone   = document.getElementById('uploadZone');
const resumeFile   = document.getElementById('resumeFile');
const fileInfo     = document.getElementById('fileInfo');
const fileName     = document.getElementById('fileName');
const removeFile   = document.getElementById('removeFile');
const btnAnalyze   = document.getElementById('btnAnalyze');
const resumeResult = document.getElementById('resumeResult');
const resumeGrid   = document.getElementById('resumeGrid');
const stepFilters  = document.getElementById('step-filters');
const btnHunt      = document.getElementById('btnHunt');
const loadingCard  = document.getElementById('loadingCard');
const loadingTitle = document.getElementById('loadingTitle');
const loadingSub   = document.getElementById('loadingSub');
const resultsSection = document.getElementById('resultsSection');
const jobsGrid     = document.getElementById('jobsGrid');
const resultsCount = document.getElementById('resultsCount');
const resultsKeywords = document.getElementById('resultsKeywords');
const noResults    = document.getElementById('noResults');
const btnSearchAgain = document.getElementById('btnSearchAgain');
const toast        = document.getElementById('toast');

// ── Toast ──────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, type = 'info') {
  clearTimeout(toastTimer);
  toast.textContent = msg;
  toast.className = `toast ${type} show`;
  toastTimer = setTimeout(() => { toast.className = 'toast'; }, 4000);
}

// ── File Upload ────────────────────────────────────────────────────────────
uploadZone.addEventListener('click', () => resumeFile.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragging'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragging'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('dragging');
  const f = e.dataTransfer.files[0];
  if (f) handleFileSelect(f);
});
resumeFile.addEventListener('change', () => {
  if (resumeFile.files[0]) handleFileSelect(resumeFile.files[0]);
});
removeFile.addEventListener('click', e => {
  e.stopPropagation();
  clearFile();
});

function handleFileSelect(file) {
  const allowed = ['.pdf', '.docx', '.doc', '.txt'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast('Please upload a PDF, DOCX, or TXT file.', 'error');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast('File is too large. Maximum size is 10 MB.', 'error');
    return;
  }
  fileName.textContent = file.name;
  fileInfo.style.display = 'block';
  uploadZone.style.display = 'none';
  btnAnalyze.disabled = false;
  btnAnalyze._file = file;
}

function clearFile() {
  fileInfo.style.display = 'none';
  uploadZone.style.display = 'block';
  btnAnalyze.disabled = true;
  btnAnalyze._file = null;
  resumeFile.value = '';
  resumeData = null;
  resumeResult.style.display = 'none';
  stepFilters.style.display = 'none';
}

// ── Analyze Resume ─────────────────────────────────────────────────────────
btnAnalyze.addEventListener('click', async () => {
  const file = btnAnalyze._file;
  if (!file) return;

  btnAnalyze.disabled = true;
  btnAnalyze.innerHTML = '<span class="btn-icon">⏳</span> Analyzing with Gemini AI...';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API}/upload-resume`, { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    resumeData = data.resume_data;
    renderResumeResult(resumeData);
    resumeResult.style.display = 'block';
    stepFilters.style.display = 'block';
    resumeResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    showToast('Resume analyzed successfully! ✨', 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    btnAnalyze.disabled = false;
    btnAnalyze.innerHTML = '<span class="btn-icon">🔍</span> Analyze Resume with AI';
  }
});

function renderResumeResult(data) {
  const skills = (data.skills || []).slice(0, 12);
  const roles  = (data.target_roles || []);
  const highlights = (data.key_highlights || []);

  resumeGrid.innerHTML = `
    <div class="resume-chip-group" style="grid-column: 1/-1">
      <div class="chip-label">👤 Profile Summary</div>
      <div class="chip-value" style="font-size:0.9rem;color:var(--text-muted)">${data.summary || 'No summary available.'}</div>
    </div>
    <div class="resume-chip-group">
      <div class="chip-label">🎯 Target Roles</div>
      <div class="chips-list">${roles.map(r => `<span class="chip">${r}</span>`).join('') || '<span style="color:var(--text-dim);font-size:.85rem">Not detected</span>'}</div>
    </div>
    <div class="resume-chip-group">
      <div class="chip-label">⚡ Top Skills</div>
      <div class="chips-list">${skills.map(s => `<span class="chip">${s}</span>`).join('') || '<span style="color:var(--text-dim);font-size:.85rem">Not detected</span>'}</div>
    </div>
    <div class="resume-chip-group">
      <div class="chip-label">🎓 Education</div>
      <div class="chip-value">${data.education || 'Not specified'}</div>
    </div>
    <div class="resume-chip-group">
      <div class="chip-label">📅 Experience</div>
      <div class="chip-value">${data.years_of_experience || 0} years</div>
    </div>
    ${highlights.length ? `
    <div class="resume-chip-group" style="grid-column:1/-1">
      <div class="chip-label">⭐ Key Highlights</div>
      <ul style="padding-left:1.2rem;margin-top:.4rem;display:flex;flex-direction:column;gap:.3rem">
        ${highlights.map(h => `<li style="font-size:.85rem;color:var(--text-muted)">${h}</li>`).join('')}
      </ul>
    </div>` : ''}
  `;
}

// ── Work Mode Toggle ───────────────────────────────────────────────────────
document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedWorkMode = btn.dataset.mode;
  });
});

// ── Animate Sources ────────────────────────────────────────────────────────
function animateSources() {
  const items = document.querySelectorAll('.source-item');
  let i = 0;
  const interval = setInterval(() => {
    if (i < items.length) {
      items[i].classList.add('active');
      if (i > 0) items[i-1].classList.add('done');
      i++;
    } else {
      clearInterval(interval);
      items.forEach(it => it.classList.add('done'));
    }
  }, 900);
  return interval;
}

// ── Hunt Jobs ─────────────────────────────────────────────────────────────
btnHunt.addEventListener('click', async () => {
  if (!resumeData) { showToast('Please analyze your resume first.', 'error'); return; }

  const customQuery = document.getElementById('customQueryInput')?.value.trim() || '';
  const location = document.getElementById('locationInput').value.trim();
  const rapidApiKey = document.getElementById('rapidApiKey').value.trim();
  const adzunaId   = document.getElementById('adzunaId').value.trim();
  const adzunaKey  = document.getElementById('adzunaKey').value.trim();

  // Show loading
  stepFilters.style.display = 'none';
  resumeResult.style.display = 'none';
  resultsSection.style.display = 'none';
  loadingCard.style.display = 'block';
  loadingTitle.textContent = 'Searching Indeed, LinkedIn, Glassdoor & Remote Boards...';
  loadingSub.textContent = 'Scraping and aggregating live job listings in real-time';
  document.querySelectorAll('.source-item').forEach(el => el.className = 'source-item');
  loadingCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  const srcInterval = animateSources();

  try {
    const payload = {
      resume_data: resumeData,
      custom_query: customQuery,
      location: location,
      work_mode: selectedWorkMode,
      rapidapi_key: rapidApiKey,
      adzuna_app_id: adzunaId,
      adzuna_app_key: adzunaKey,
    };

    loadingTitle.textContent = 'Evaluating & Ranking matches with Groq AI...';
    loadingSub.textContent = 'Calculating candidate fit & skill overlap scores';

    const res = await fetch(`${API}/search-jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    clearInterval(srcInterval);

    if (!res.ok) throw new Error(data.detail || 'Search failed');

    allJobs = data.jobs || [];
    const keywords = (data.keywords_used || []).join(', ');
    resultsKeywords.textContent = keywords ? `Target Query: ${keywords}` : '';

    loadingCard.style.display = 'none';
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    activeScoreFilter = 'all';
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tabAll').classList.add('active');

    renderJobs(allJobs);
    showToast(`Found ${allJobs.length} live job matches! 🎯`, 'success');
  } catch (err) {
    clearInterval(srcInterval);
    loadingCard.style.display = 'none';
    stepFilters.style.display = 'block';
    resumeResult.style.display = 'block';
    showToast(`Error: ${err.message}`, 'error');
  }
});

// ── Render Jobs ────────────────────────────────────────────────────────────
function renderJobs(jobs) {
  let filtered = [...jobs];
  const minScore = activeScoreFilter === 'all' ? 0 : parseInt(activeScoreFilter);
  filtered = filtered.filter(j => (j.match_score || 0) >= minScore);

  const sort = document.getElementById('sortSelect').value;
  if (sort === 'score') filtered.sort((a,b) => (b.match_score||0) - (a.match_score||0));
  else if (sort === 'company') filtered.sort((a,b) => (a.company||'').localeCompare(b.company||''));
  else if (sort === 'recent') filtered.sort((a,b) => new Date(b.posted_at||0) - new Date(a.posted_at||0));

  resultsCount.textContent = `${filtered.length} job${filtered.length !== 1 ? 's' : ''}`;
  noResults.style.display = filtered.length === 0 ? 'block' : 'none';
  jobsGrid.innerHTML = filtered.map((job, idx) => jobCardHTML(job, idx)).join('');

  // Animate score bars
  setTimeout(() => {
    document.querySelectorAll('.score-bar-fill').forEach(bar => {
      bar.style.width = bar.dataset.width + '%';
    });
  }, 100);
}

function jobCardHTML(job, idx) {
  const score = job.match_score || 50;
  const badgeClass = score >= 80 ? 'match-high' : score >= 60 ? 'match-med' : 'match-low';
  const barColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#64748b';
  const modeClass = (job.work_mode||'').toLowerCase();
  const modeIcon = modeClass === 'remote' ? '🏠' : modeClass === 'hybrid' ? '🔄' : '🏢';
  
  const sourceName = job.source || 'Direct';
  const srcBadge = `<span class="job-source-tag source-${sourceName.toLowerCase()}">via ${sourceName}</span>`;
  
  const sal = job.salary ? `<span class="job-salary">💰 ${job.salary}</span>` : '';
  
  const matchingSkills = (job.matching_skills || []).map(s => `<span class="chip skill-chip">✓ ${s}</span>`).join('');
  const tags = (job.tags || []).slice(0,2).map(t => `<span class="meta-tag">${t}</span>`).join('');
  const postedDate = job.posted_at ? `<span class="meta-tag">📅 ${formatDate(job.posted_at)}</span>` : '';
  const desc = stripHTML(job.description || '').slice(0, 220).trim();
  const reason = job.match_reason ? `<div class="job-reason">🤖 ${job.match_reason}</div>` : '';
  const applyUrl = job.url || '#';
  const animDelay = Math.min(idx * 0.04, 0.6);

  return `
  <div class="job-card" style="animation-delay:${animDelay}s">
    <div class="job-card-top">
      <div class="job-title">${escHTML(job.title || 'Untitled Position')}</div>
      <div class="match-badge ${badgeClass}">${score}% match</div>
    </div>
    <div class="job-company-row">
      <span class="job-company">${escHTML(job.company || 'Company not listed')}</span>
      ${srcBadge}
    </div>
    <div class="score-bar-wrap">
      <div class="score-bar-track">
        <div class="score-bar-fill" data-width="${score}" style="width:0%;background:${barColor}"></div>
      </div>
    </div>
    <div class="job-meta">
      <span class="meta-tag ${modeClass}">${modeIcon} ${job.work_mode || 'Unknown'}</span>
      <span class="meta-tag">📍 ${escHTML(job.location || 'Not specified')}</span>
      ${postedDate}
      ${tags}
    </div>
    ${matchingSkills ? `<div class="matching-skills-row"><span class="skills-label">Matching Skills:</span> ${matchingSkills}</div>` : ''}
    ${desc ? `<div class="job-desc">${escHTML(desc)}${job.description && job.description.length > 220 ? '…' : ''}</div>` : ''}
    ${reason}
    <div class="job-card-footer">
      <div style="display:flex;flex-direction:column;gap:3px">${sal}</div>
      <a class="btn-apply" href="${applyUrl}" target="_blank" rel="noopener noreferrer">Apply Now →</a>
    </div>
  </div>`;
}


function escHTML(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function stripHTML(str) {
  return String(str).replace(/<[^>]+>/g, ' ').replace(/\s+/g,' ').trim();
}
function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr.slice(0,10);
    const diff = Math.floor((Date.now() - d) / 86400000);
    if (diff === 0) return 'Today';
    if (diff === 1) return '1 day ago';
    if (diff < 30) return `${diff}d ago`;
    if (diff < 365) return `${Math.floor(diff/30)}mo ago`;
    return `${Math.floor(diff/365)}y ago`;
  } catch { return ''; }
}

// ── Filter Tabs ────────────────────────────────────────────────────────────
document.querySelectorAll('.filter-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    activeScoreFilter = tab.dataset.score;
    renderJobs(allJobs);
  });
});

document.getElementById('sortSelect').addEventListener('change', () => renderJobs(allJobs));

// ── Search Again ───────────────────────────────────────────────────────────
btnSearchAgain.addEventListener('click', () => {
  resultsSection.style.display = 'none';
  resumeResult.style.display = 'block';
  stepFilters.style.display = 'block';
  allJobs = [];
  document.getElementById('step-upload').scrollIntoView({ behavior: 'smooth' });
});

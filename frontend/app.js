/* Crystal Ball — Frontend JS */

const API_BASE = window.CRYSTAL_BALL_API || 'http://localhost:8000/api';

const resultsList = document.getElementById('results-list');
const detailPanel = document.getElementById('detail-panel');
const searchInput = document.getElementById('search');

let currentTab = 'spells';
let debounceTimer = null;

// ── Tab switching ────────────────────────────────────────────────────────

document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelector('.tab.active').classList.remove('active');
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    searchInput.value = '';
    detailPanel.classList.add('hidden');
    loadResults();
  });
});

// ── Search ───────────────────────────────────────────────────────────────

searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadResults, 300);
});

// ── Data loading ─────────────────────────────────────────────────────────

async function apiFetch(path) {
  try {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('API error:', err);
    return null;
  }
}

async function loadResults() {
  const q = searchInput.value.trim();
  let path = `/${currentTab}?limit=200`;
  if (q) path += `&q=${encodeURIComponent(q)}`;

  resultsList.innerHTML = '<div class="loading">Caricamento...</div>';

  const data = await apiFetch(path);
  if (!data || !data.results) {
    resultsList.innerHTML = '<div class="no-results">Errore di connessione all\'API</div>';
    return;
  }

  if (data.results.length === 0) {
    resultsList.innerHTML = '<div class="no-results">Nessun risultato</div>';
    return;
  }

  resultsList.innerHTML = data.results.map((item) => {
    const meta = getMeta(item);
    return `<div class="result-item" data-slug="${item.slug || ''}" data-id="${item.id || ''}">
      <div class="name">${esc(item.name)}</div>
      ${meta ? `<div class="meta">${esc(meta)}</div>` : ''}
    </div>`;
  }).join('');

  resultsList.querySelectorAll('.result-item').forEach((el) => {
    el.addEventListener('click', () => {
      resultsList.querySelectorAll('.selected').forEach((s) => s.classList.remove('selected'));
      el.classList.add('selected');
      loadDetail(el.dataset.slug, el.dataset.id);
    });
  });
}

function getMeta(item) {
  switch (currentTab) {
    case 'spells':
      return [item.school, item.level].filter(Boolean).join(' — ');
    case 'feats':
      return item.type || '';
    case 'classes':
      return item.hit_die ? `Hit Die: ${item.hit_die}` : '';
    case 'races':
      return '';
    case 'equipment':
      return item.category || '';
    default:
      return '';
  }
}

// ── Detail view ──────────────────────────────────────────────────────────

async function loadDetail(slug, id) {
  let path;
  if (currentTab === 'equipment') {
    path = `/${currentTab}/${id}`;
  } else {
    path = `/${currentTab}/${slug}`;
  }

  detailPanel.classList.remove('hidden');
  detailPanel.innerHTML = '<div class="loading">Caricamento...</div>';

  const item = await apiFetch(path);
  if (!item) {
    detailPanel.innerHTML = '<div class="no-results">Errore</div>';
    return;
  }

  detailPanel.innerHTML = renderDetail(item);
}

function renderDetail(item) {
  switch (currentTab) {
    case 'spells':
      return renderSpell(item);
    case 'feats':
      return renderFeat(item);
    case 'classes':
      return renderClass(item);
    case 'races':
      return renderRace(item);
    case 'equipment':
      return renderEquipment(item);
    default:
      return `<h2>${esc(item.name)}</h2>`;
  }
}

function renderSpell(s) {
  const fields = [
    ['Scuola', [s.school, s.subschool ? `(${s.subschool})` : '', s.descriptor ? `[${s.descriptor}]` : ''].filter(Boolean).join(' ')],
    ['Livello', s.level],
    ['Componenti', s.components],
    ['Tempo di lancio', s.casting_time],
    ['Raggio', s.range],
    ['Bersaglio/Area/Effetto', s.target_area_effect],
    ['Durata', s.duration],
    ['Tiro salvezza', s.saving_throw],
    ['Resistenza incantesimi', s.spell_resistance],
  ];

  return `<h2>${esc(s.name)}</h2>` + renderFields(fields) + renderDesc(s.desc_html);
}

function renderFeat(f) {
  const fields = [
    ['Tipo', f.type],
    ['Prerequisiti', f.prerequisites],
    ['Beneficio', f.benefit],
    ['Normale', f.normal],
    ['Speciale', f.special],
  ];

  return `<h2>${esc(f.name)}</h2>` + renderFields(fields);
}

function renderClass(c) {
  const fields = [
    ['Dado vita', c.hit_die],
    ['Allineamento', c.alignment],
  ];

  let html = `<h2>${esc(c.name)}</h2>` + renderFields(fields);

  if (c.table_html) {
    html += `<div class="desc-html">${c.table_html}</div>`;
  }

  html += renderDesc(c.desc_html);
  return html;
}

function renderRace(r) {
  let html = `<h2>${esc(r.name)}</h2>`;

  if (r.traits && r.traits.length) {
    html += '<ul style="margin: 0.75rem 0; padding-left: 1.25rem;">';
    html += r.traits.map((t) => `<li style="margin-bottom: 0.4rem;">${t}</li>`).join('');
    html += '</ul>';
  }

  return html;
}

function renderEquipment(e) {
  let html = `<h2>${esc(e.name)}</h2>`;
  html += `<div class="field"><span class="field-label">Categoria</span><div class="field-value">${esc(e.category || '')}</div></div>`;

  if (e.data) {
    const entries = Object.entries(e.data).filter(([k]) => k !== 'desc_html');
    for (const [key, val] of entries) {
      if (val) {
        html += `<div class="field"><span class="field-label">${esc(key)}</span><div class="field-value">${esc(String(val))}</div></div>`;
      }
    }
  }

  return html;
}

// ── Render helpers ───────────────────────────────────────────────────────

function renderFields(fields) {
  return fields
    .filter(([, v]) => v)
    .map(([label, value]) =>
      `<div class="field"><span class="field-label">${esc(label)}</span><div class="field-value">${esc(String(value))}</div></div>`
    )
    .join('');
}

function renderDesc(html) {
  if (!html) return '';
  return `<div class="desc-html">${html}</div>`;
}

function esc(str) {
  if (!str) return '';
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

// ── Init ─────────────────────────────────────────────────────────────────

loadResults();

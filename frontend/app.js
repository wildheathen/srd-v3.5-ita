/* Crystal Ball — Static JSON frontend */

const DATA_BASE = 'data';

const resultsList = document.getElementById('results-list');
const detailPanel = document.getElementById('detail-panel');
const searchInput = document.getElementById('search');
const filtersDiv = document.getElementById('filters');

let currentTab = 'spells';
let dataCache = {};
let debounceTimer = null;

// ── Data loading (static JSON) ───────────────────────────────────────────

async function loadData(category) {
  if (dataCache[category]) return dataCache[category];

  resultsList.innerHTML = '<div class="loading">Caricamento...</div>';

  try {
    const res = await fetch(`${DATA_BASE}/${category}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    let data = await res.json();

    // Normalize equipment: parse _category for display
    if (category === 'equipment') {
      data = data.map((item) => ({ ...item, category: item._category || '' }));
    }

    dataCache[category] = data;
    return data;
  } catch (err) {
    console.error(`Failed to load ${category}:`, err);
    resultsList.innerHTML = `<div class="no-results">Errore nel caricamento di ${category}.json</div>`;
    return null;
  }
}

// ── Tab switching ────────────────────────────────────────────────────────

document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelector('.tab.active').classList.remove('active');
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    searchInput.value = '';
    detailPanel.classList.add('hidden');
    buildFilters();
    renderResults();
  });
});

// ── Search ───────────────────────────────────────────────────────────────

searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderResults, 150);
});

// ── Filters ──────────────────────────────────────────────────────────────

function buildFilters() {
  filtersDiv.innerHTML = '';

  if (currentTab === 'spells') {
    filtersDiv.innerHTML = `
      <select id="filter-school"><option value="">Tutte le scuole</option></select>
      <select id="filter-level"><option value="">Tutti i livelli</option></select>
      <span id="result-count"></span>
    `;
    populateSchoolFilter();
    populateLevelFilter();
    filtersDiv.querySelectorAll('select').forEach((s) =>
      s.addEventListener('change', renderResults)
    );
  } else if (currentTab === 'feats') {
    filtersDiv.innerHTML = `
      <select id="filter-type"><option value="">Tutti i tipi</option></select>
      <span id="result-count"></span>
    `;
    populateFeatTypeFilter();
    filtersDiv.querySelector('select').addEventListener('change', renderResults);
  } else if (currentTab === 'equipment') {
    filtersDiv.innerHTML = `
      <select id="filter-category"><option value="">Tutte le categorie</option></select>
      <span id="result-count"></span>
    `;
    populateEquipCategoryFilter();
    filtersDiv.querySelector('select').addEventListener('change', renderResults);
  } else {
    filtersDiv.innerHTML = '<span id="result-count"></span>';
  }
}

async function populateSchoolFilter() {
  const data = await loadData('spells');
  if (!data) return;
  const schools = [...new Set(data.map((s) => s.school).filter(Boolean))].sort();
  const sel = document.getElementById('filter-school');
  schools.forEach((s) => {
    sel.innerHTML += `<option value="${esc(s)}">${esc(s)}</option>`;
  });
}

async function populateLevelFilter() {
  const data = await loadData('spells');
  if (!data) return;
  // Extract unique class/level combos like "Sor/Wiz 3"
  const levels = new Set();
  data.forEach((s) => {
    if (!s.level) return;
    s.level.split(',').forEach((part) => {
      const trimmed = part.trim();
      if (trimmed) levels.add(trimmed);
    });
  });
  const sorted = [...levels].sort();
  const sel = document.getElementById('filter-level');
  sorted.forEach((l) => {
    sel.innerHTML += `<option value="${esc(l)}">${esc(l)}</option>`;
  });
}

async function populateFeatTypeFilter() {
  const data = await loadData('feats');
  if (!data) return;
  const types = [...new Set(data.map((f) => f.type).filter(Boolean))].sort();
  const sel = document.getElementById('filter-type');
  types.forEach((t) => {
    sel.innerHTML += `<option value="${esc(t)}">${esc(t)}</option>`;
  });
}

async function populateEquipCategoryFilter() {
  const data = await loadData('equipment');
  if (!data) return;
  const cats = [...new Set(data.map((e) => e._category || e.category).filter(Boolean))].sort();
  const sel = document.getElementById('filter-category');
  cats.forEach((c) => {
    const label = c === 'weapon' ? 'Armi' : c === 'armor' ? 'Armature' : c === 'goods' ? 'Beni e servizi' : c;
    sel.innerHTML += `<option value="${esc(c)}">${esc(label)}</option>`;
  });
}

// ── Filtering + rendering ────────────────────────────────────────────────

async function renderResults() {
  const data = await loadData(currentTab);
  if (!data) return;

  const q = searchInput.value.trim().toLowerCase();
  let filtered = data;

  // Text search
  if (q) {
    filtered = filtered.filter((item) =>
      item.name.toLowerCase().includes(q)
    );
  }

  // Category-specific filters
  if (currentTab === 'spells') {
    const school = document.getElementById('filter-school')?.value;
    const level = document.getElementById('filter-level')?.value;
    if (school) filtered = filtered.filter((s) => s.school === school);
    if (level) filtered = filtered.filter((s) => s.level && s.level.includes(level));
  } else if (currentTab === 'feats') {
    const type = document.getElementById('filter-type')?.value;
    if (type) filtered = filtered.filter((f) => f.type === type);
  } else if (currentTab === 'equipment') {
    const cat = document.getElementById('filter-category')?.value;
    if (cat) filtered = filtered.filter((e) => (e._category || e.category) === cat);
  }

  // Update count
  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = `${filtered.length} risultati`;

  if (filtered.length === 0) {
    resultsList.innerHTML = '<div class="no-results">Nessun risultato</div>';
    return;
  }

  resultsList.innerHTML = filtered.map((item, idx) => {
    const meta = getMeta(item);
    return `<div class="result-item" data-index="${idx}" data-slug="${item.slug || ''}">
      <div class="name">${esc(item.name)}</div>
      ${meta ? `<div class="meta">${esc(meta)}</div>` : ''}
    </div>`;
  }).join('');

  // Store filtered list for detail lookup
  resultsList._filtered = filtered;

  resultsList.querySelectorAll('.result-item').forEach((el) => {
    el.addEventListener('click', () => {
      resultsList.querySelectorAll('.selected').forEach((s) => s.classList.remove('selected'));
      el.classList.add('selected');
      const item = resultsList._filtered[parseInt(el.dataset.index)];
      showDetail(item);
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
    case 'equipment': {
      const cat = item._category || item.category || '';
      return cat === 'weapon' ? 'Arma' : cat === 'armor' ? 'Armatura' : cat === 'goods' ? 'Beni' : cat;
    }
    default:
      return '';
  }
}

// ── Detail view ──────────────────────────────────────────────────────────

function showDetail(item) {
  detailPanel.classList.remove('hidden');
  detailPanel.innerHTML = renderDetail(item);
  // On mobile, scroll to detail
  if (window.innerWidth <= 768) {
    detailPanel.scrollIntoView({ behavior: 'smooth' });
  }
}

function renderDetail(item) {
  switch (currentTab) {
    case 'spells': return renderSpell(item);
    case 'feats': return renderFeat(item);
    case 'classes': return renderClass(item);
    case 'races': return renderRace(item);
    case 'equipment': return renderEquipment(item);
    default: return `<h2>${esc(item.name)}</h2>`;
  }
}

function renderSpell(s) {
  const fields = [
    ['Scuola', [s.school, s.subschool ? `(${s.subschool})` : '', s.descriptor ? `[${s.descriptor}]` : ''].filter(Boolean).join(' ')],
    ['Livello', s.level],
    ['Componenti', s.components],
    ['Tempo di lancio', s.casting_time],
    ['Raggio', s.range],
    ['Bersaglio / Area / Effetto', s.target_area_effect],
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
  return `<h2>${esc(f.name)}</h2>` + renderFields(fields) + renderDesc(f.desc_html);
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
    html += '<div class="desc-html"><ul>';
    html += r.traits.map((t) => `<li>${t}</li>`).join('');
    html += '</ul></div>';
  }
  html += renderDesc(r.desc_html);
  return html;
}

function renderEquipment(e) {
  let html = `<h2>${esc(e.name)}</h2>`;
  const cat = e._category || e.category || '';
  const catLabel = cat === 'weapon' ? 'Arma' : cat === 'armor' ? 'Armatura' : cat === 'goods' ? 'Beni e servizi' : cat;
  html += `<div class="field"><span class="field-label">Categoria</span><div class="field-value">${esc(catLabel)}</div></div>`;

  // Show all table data fields
  const skip = new Set(['name', 'slug', '_category', 'category', 'desc_html']);
  const entries = Object.entries(e).filter(([k]) => !skip.has(k));
  for (const [key, val] of entries) {
    if (val) {
      html += `<div class="field"><span class="field-label">${esc(key)}</span><div class="field-value">${esc(String(val))}</div></div>`;
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

buildFilters();
renderResults();

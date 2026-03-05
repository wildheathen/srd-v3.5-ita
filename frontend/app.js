/* Crystal Ball — Static JSON frontend (i18n-aware) */

const DATA_BASE = 'data';

const resultsList = document.getElementById('results-list');
const detailPanel = document.getElementById('detail-panel');
const searchInput = document.getElementById('search');
const filtersDiv = document.getElementById('filters');

let currentTab = 'spells';
let dataCache = {};
let debounceTimer = null;

// ── Prepared spells (localStorage) ───────────────────────────────────────

const PREPARED_KEY = 'crystalball_prepared';

function loadPrepared() {
  try {
    return JSON.parse(localStorage.getItem(PREPARED_KEY)) || {};
  } catch { return {}; }
}

function savePrepared(prepared) {
  localStorage.setItem(PREPARED_KEY, JSON.stringify(prepared));
}

function addPrepared(spell) {
  const p = loadPrepared();
  if (!p[spell.slug]) {
    p[spell.slug] = { name: spell.name, slug: spell.slug, prepared: 1, used: 0 };
  } else {
    p[spell.slug].prepared++;
  }
  savePrepared(p);
}

function removePrepared(slug) {
  const p = loadPrepared();
  delete p[slug];
  savePrepared(p);
}

function updatePreparedCount(slug, field, delta) {
  const p = loadPrepared();
  if (!p[slug]) return;
  p[slug][field] = Math.max(0, (p[slug][field] || 0) + delta);
  if (field === 'used' && p[slug].used > p[slug].prepared) {
    p[slug].used = p[slug].prepared;
  }
  savePrepared(p);
}

// ── Data loading (static JSON + i18n overlay) ────────────────────────────

async function loadData(category) {
  if (category === 'prepared') return null; // handled separately
  const lang = getCurrentLang();
  const cacheKey = `${category}_${lang}`;

  if (dataCache[cacheKey]) return dataCache[cacheKey];

  resultsList.innerHTML = `<div class="loading">${t('msg.loading')}</div>`;

  try {
    // Load base EN data (always cached under raw key)
    if (!dataCache[category + '_raw']) {
      const res = await fetch(`${DATA_BASE}/${category}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      let data = await res.json();
      if (category === 'equipment') {
        data = data.map((item) => ({ ...item, category: item._category || '' }));
      }
      dataCache[category + '_raw'] = data;
    }

    let data = dataCache[category + '_raw'];

    // Apply language overlay if not English
    const overlay = await loadDataOverlay(category);
    if (overlay) {
      data = applyOverlay(data, overlay);
    }

    dataCache[cacheKey] = data;
    return data;
  } catch (err) {
    console.error(`Failed to load ${category}:`, err);
    resultsList.innerHTML = `<div class="no-results">${t('msg.load_error', { category })}</div>`;
    return null;
  }
}

function clearAllDataCache() {
  dataCache = {};
}

// ── Tab switching ────────────────────────────────────────────────────────

document.querySelectorAll('.tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelector('.tab.active').classList.remove('active');
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    searchInput.value = '';
    detailPanel.classList.add('hidden');
    searchInput.style.display = currentTab === 'prepared' ? 'none' : '';
    buildFilters();
    renderResults();
  });
});

// ── Search ───────────────────────────────────────────────────────────────

searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderResults, 150);
});

// ── Language switcher ────────────────────────────────────────────────────

function initLangSwitcher() {
  const sel = document.getElementById('lang-switcher');
  if (!sel) return;
  sel.value = getCurrentLang();
  sel.addEventListener('change', async () => {
    setLang(sel.value);
    clearAllDataCache();
    await loadI18n(sel.value);
    updateTabLabels();
    searchInput.placeholder = t('search.placeholder');
    buildFilters();
    renderResults();
    // Re-render detail if visible
    detailPanel.classList.add('hidden');
  });
}

function updateTabLabels() {
  const tabMap = {
    spells: 'tab.spells',
    prepared: 'tab.prepared',
    feats: 'tab.feats',
    classes: 'tab.classes',
    races: 'tab.races',
    equipment: 'tab.equipment',
    monsters: 'tab.monsters',
    rules: 'tab.rules',
  };
  document.querySelectorAll('.tab').forEach((btn) => {
    const key = tabMap[btn.dataset.tab];
    if (key) btn.textContent = t(key);
  });
}

// ── Spell level parsing helper ───────────────────────────────────────────

function parseSpellLevels(levelStr) {
  if (!levelStr) return [];
  return levelStr.split(',').map((part) => {
    const trimmed = part.trim();
    const match = trimmed.match(/^(.+?)\s+(\d+)$/);
    if (match) return { cls: match[1], lvl: parseInt(match[2]) };
    return null;
  }).filter(Boolean);
}

// ── Filters ──────────────────────────────────────────────────────────────

function buildFilters() {
  filtersDiv.innerHTML = '';

  if (currentTab === 'spells') {
    filtersDiv.innerHTML = `
      <select id="filter-school"><option value="">${t('filter.all_schools')}</option></select>
      <select id="filter-class"><option value="">${t('filter.all_classes')}</option></select>
      <div class="level-checkboxes" id="filter-levels">
        <span class="level-label">${t('filter.level_label')}</span>
        ${[0,1,2,3,4,5,6,7,8,9].map((n) =>
          `<label class="level-check"><input type="checkbox" value="${n}" checked> ${n}</label>`
        ).join('')}
        <button id="levels-none" class="level-toggle" title="${t('filter.levels_none')}">${t('filter.levels_none')}</button>
        <button id="levels-all" class="level-toggle" title="${t('filter.levels_all')}">${t('filter.levels_all')}</button>
      </div>
      <span id="result-count"></span>
    `;
    populateSpellFilters();
    filtersDiv.querySelector('#filter-school').addEventListener('change', renderResults);
    filtersDiv.querySelector('#filter-class').addEventListener('change', renderResults);
    filtersDiv.querySelectorAll('#filter-levels input').forEach((cb) =>
      cb.addEventListener('change', renderResults)
    );
    filtersDiv.querySelector('#levels-none').addEventListener('click', () => {
      filtersDiv.querySelectorAll('#filter-levels input').forEach((cb) => { cb.checked = false; });
      renderResults();
    });
    filtersDiv.querySelector('#levels-all').addEventListener('click', () => {
      filtersDiv.querySelectorAll('#filter-levels input').forEach((cb) => { cb.checked = true; });
      renderResults();
    });
  } else if (currentTab === 'feats') {
    filtersDiv.innerHTML = `
      <select id="filter-type"><option value="">${t('filter.all_types')}</option></select>
      <span id="result-count"></span>
    `;
    populateFeatTypeFilter();
    filtersDiv.querySelector('select').addEventListener('change', renderResults);
  } else if (currentTab === 'equipment') {
    filtersDiv.innerHTML = `
      <select id="filter-category"><option value="">${t('filter.all_categories')}</option></select>
      <span id="result-count"></span>
    `;
    populateEquipCategoryFilter();
    filtersDiv.querySelector('select').addEventListener('change', renderResults);
  } else if (currentTab === 'monsters') {
    filtersDiv.innerHTML = `
      <select id="filter-cr"><option value="">${t('filter.all_cr')}</option></select>
      <select id="filter-mtype"><option value="">${t('filter.all_types')}</option></select>
      <span id="result-count"></span>
    `;
    populateMonsterFilters();
    filtersDiv.querySelectorAll('select').forEach((s) =>
      s.addEventListener('change', renderResults)
    );
  } else if (currentTab === 'prepared') {
    filtersDiv.innerHTML = `
      <button id="clear-prepared" class="level-toggle" style="color: #e57373;">${t('btn.clear_prepared')}</button>
      <span id="result-count"></span>
    `;
    filtersDiv.querySelector('#clear-prepared').addEventListener('click', () => {
      if (confirm(t('msg.confirm_clear'))) {
        savePrepared({});
        renderResults();
      }
    });
  } else {
    filtersDiv.innerHTML = '<span id="result-count"></span>';
  }
}

async function populateSpellFilters() {
  const data = await loadData('spells');
  if (!data) return;

  // Schools
  const schools = [...new Set(data.map((s) => s.school).filter(Boolean))].sort();
  const schoolSel = document.getElementById('filter-school');
  schools.forEach((s) => {
    schoolSel.innerHTML += `<option value="${esc(s)}">${esc(s)}</option>`;
  });

  // Classes/domains
  const classes = new Set();
  data.forEach((s) => {
    parseSpellLevels(s.level).forEach((l) => classes.add(l.cls));
  });
  const classSel = document.getElementById('filter-class');
  [...classes].sort().forEach((c) => {
    classSel.innerHTML += `<option value="${esc(c)}">${esc(c)}</option>`;
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
    const label = c === 'weapon' ? t('cat.weapons') : c === 'armor' ? t('cat.armors') : c === 'goods' ? t('cat.goods') : c;
    sel.innerHTML += `<option value="${esc(c)}">${esc(label)}</option>`;
  });
}

async function populateMonsterFilters() {
  const data = await loadData('monsters');
  if (!data) return;

  // CRs
  const crs = [...new Set(data.map((m) => m.challenge_rating).filter(Boolean))];
  crs.sort((a, b) => {
    const na = parseFloat(a.replace('–', '-'));
    const nb = parseFloat(b.replace('–', '-'));
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  });
  const crSel = document.getElementById('filter-cr');
  crs.forEach((cr) => {
    crSel.innerHTML += `<option value="${esc(cr)}">CR ${esc(cr)}</option>`;
  });

  // Types
  const types = new Set();
  data.forEach((m) => {
    if (m.type) {
      const base = m.type.replace(/\s*\(.*\)/, '').trim();
      if (base) types.add(base);
    }
  });
  const typeSel = document.getElementById('filter-mtype');
  [...types].sort().forEach((tp) => {
    typeSel.innerHTML += `<option value="${esc(tp)}">${esc(tp)}</option>`;
  });
}

// ── Filtering + rendering ────────────────────────────────────────────────

function getSelectedLevels() {
  const checks = filtersDiv.querySelectorAll('#filter-levels input:checked');
  return new Set([...checks].map((cb) => parseInt(cb.value)));
}

async function renderResults() {
  // Special handling for prepared tab
  if (currentTab === 'prepared') {
    renderPreparedList();
    return;
  }

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
    const cls = document.getElementById('filter-class')?.value;
    const levels = getSelectedLevels();

    if (school) filtered = filtered.filter((s) => s.school === school);

    // Filter by class/domain + levels
    filtered = filtered.filter((s) => {
      const parsed = parseSpellLevels(s.level);
      if (parsed.length === 0) return levels.size === 10; // show unknown-level if all selected
      if (cls) {
        // Must have this class AND level in selected set
        return parsed.some((l) => l.cls === cls && levels.has(l.lvl));
      }
      // Any class at a selected level
      return parsed.some((l) => levels.has(l.lvl));
    });

    // Sort by level (lowest first within the selected class)
    filtered.sort((a, b) => {
      const aLevels = parseSpellLevels(a.level);
      const bLevels = parseSpellLevels(b.level);
      const aMin = Math.min(...aLevels.map((l) => cls ? (l.cls === cls ? l.lvl : 99) : l.lvl));
      const bMin = Math.min(...bLevels.map((l) => cls ? (l.cls === cls ? l.lvl : 99) : l.lvl));
      if (aMin !== bMin) return aMin - bMin;
      return a.name.localeCompare(b.name);
    });
  } else if (currentTab === 'feats') {
    const type = document.getElementById('filter-type')?.value;
    if (type) filtered = filtered.filter((f) => f.type === type);
  } else if (currentTab === 'equipment') {
    const cat = document.getElementById('filter-category')?.value;
    if (cat) filtered = filtered.filter((e) => (e._category || e.category) === cat);
  } else if (currentTab === 'monsters') {
    const cr = document.getElementById('filter-cr')?.value;
    const mtype = document.getElementById('filter-mtype')?.value;
    if (cr) filtered = filtered.filter((m) => m.challenge_rating === cr);
    if (mtype) filtered = filtered.filter((m) => m.type && m.type.replace(/\s*\(.*\)/, '').trim() === mtype);
  }

  // Update count
  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = t('msg.results_count', { count: filtered.length });

  if (filtered.length === 0) {
    resultsList.innerHTML = `<div class="no-results">${t('msg.no_results')}</div>`;
    return;
  }

  const prepared = currentTab === 'spells' ? loadPrepared() : {};

  resultsList.innerHTML = filtered.map((item, idx) => {
    const meta = getMeta(item);
    let prepHtml = '';
    if (currentTab === 'spells') {
      const p = prepared[item.slug];
      if (p) {
        const allUsed = p.used >= p.prepared;
        prepHtml = `<span class="prep-badge ${allUsed ? 'exhausted' : ''}">${p.used}/${p.prepared}</span>`
          + `<button class="prep-btn prep-btn-active" data-idx="${idx}" title="${t('btn.add_prep')}">+</button>`;
      } else {
        prepHtml = `<button class="prep-btn" data-idx="${idx}" title="${t('btn.prepare_spell')}">+</button>`;
      }
    }
    const isPrepared = currentTab === 'spells' && prepared[item.slug];
    return `<div class="result-item ${isPrepared ? 'is-prepared' : ''}" data-index="${idx}" data-slug="${item.slug || ''}">
      <div class="result-row">
        <div class="result-text">
          <div class="name">${esc(item.name)}</div>
          ${meta ? `<div class="meta">${esc(meta)}</div>` : ''}
        </div>
        ${prepHtml}
      </div>
    </div>`;
  }).join('');

  // Store filtered list for detail lookup
  resultsList._filtered = filtered;

  resultsList.querySelectorAll('.result-item').forEach((el) => {
    el.addEventListener('click', (e) => {
      if (e.target.classList.contains('prep-btn')) return;
      resultsList.querySelectorAll('.selected').forEach((s) => s.classList.remove('selected'));
      el.classList.add('selected');
      const item = resultsList._filtered[parseInt(el.dataset.index)];
      showDetail(item);
    });
  });

  // Prepare spell buttons
  resultsList.querySelectorAll('.prep-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const item = resultsList._filtered[parseInt(btn.dataset.idx)];
      addPrepared(item);
      // Re-render to show updated badge
      renderResults();
    });
  });
}

// ── Prepared spells tab ──────────────────────────────────────────────────

async function renderPreparedList() {
  const prepared = loadPrepared();
  const entries = Object.values(prepared);

  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = t('msg.prepared_count', { count: entries.length });

  if (entries.length === 0) {
    resultsList.innerHTML = `<div class="no-results">${t('msg.no_prepared')}</div>`;
    detailPanel.classList.add('hidden');
    return;
  }

  // Sort by name
  entries.sort((a, b) => a.name.localeCompare(b.name));

  resultsList.innerHTML = entries.map((p) => {
    const allUsed = p.used >= p.prepared;
    return `<div class="result-item prepared-item ${allUsed ? 'all-used' : ''}" data-slug="${esc(p.slug)}">
      <div class="prep-name">${esc(p.name)}</div>
      <div class="prep-controls">
        <div class="prep-counter">
          <button class="counter-btn use-minus" data-slug="${esc(p.slug)}" title="${t('btn.undo_use')}">-</button>
          <span class="prep-usage ${allUsed ? 'exhausted' : ''}">${p.used}/${p.prepared}</span>
          <button class="counter-btn use-plus" data-slug="${esc(p.slug)}" title="${t('btn.use')}">+</button>
        </div>
        <div class="prep-adjust">
          <button class="counter-btn prep-minus" data-slug="${esc(p.slug)}" title="${t('btn.less_prepared')}">-</button>
          <span class="prep-label">prep</span>
          <button class="counter-btn prep-plus" data-slug="${esc(p.slug)}" title="${t('btn.more_prepared')}">+</button>
        </div>
        <button class="remove-btn" data-slug="${esc(p.slug)}" title="${t('btn.remove')}">&times;</button>
      </div>
    </div>`;
  }).join('');

  // Event: click on name to show spell detail
  resultsList.querySelectorAll('.prep-name').forEach((el) => {
    el.addEventListener('click', async () => {
      const slug = el.parentElement.dataset.slug;
      const spells = await loadData('spells');
      if (!spells) return;
      const spell = spells.find((s) => s.slug === slug);
      if (spell) showDetail(spell, 'spells');
    });
  });

  // Event: use +/-
  resultsList.querySelectorAll('.use-plus').forEach((btn) => {
    btn.addEventListener('click', () => {
      updatePreparedCount(btn.dataset.slug, 'used', 1);
      renderPreparedList();
    });
  });
  resultsList.querySelectorAll('.use-minus').forEach((btn) => {
    btn.addEventListener('click', () => {
      updatePreparedCount(btn.dataset.slug, 'used', -1);
      renderPreparedList();
    });
  });

  // Event: prepared +/-
  resultsList.querySelectorAll('.prep-plus').forEach((btn) => {
    btn.addEventListener('click', () => {
      updatePreparedCount(btn.dataset.slug, 'prepared', 1);
      renderPreparedList();
    });
  });
  resultsList.querySelectorAll('.prep-minus').forEach((btn) => {
    btn.addEventListener('click', () => {
      const p = loadPrepared();
      if (p[btn.dataset.slug] && p[btn.dataset.slug].prepared <= 1) {
        removePrepared(btn.dataset.slug);
      } else {
        updatePreparedCount(btn.dataset.slug, 'prepared', -1);
      }
      renderPreparedList();
    });
  });

  // Event: remove
  resultsList.querySelectorAll('.remove-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      removePrepared(btn.dataset.slug);
      renderPreparedList();
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
      return item.hit_die ? t('meta.hit_die', { value: item.hit_die }) : '';
    case 'races':
      return '';
    case 'equipment': {
      const cat = item._category || item.category || '';
      return cat === 'weapon' ? t('cat.weapon') : cat === 'armor' ? t('cat.armor') : cat === 'goods' ? t('cat.goods_short') : cat;
    }
    case 'monsters':
      return [item.type, item.challenge_rating ? `CR ${item.challenge_rating}` : ''].filter(Boolean).join(' — ');
    case 'rules':
      return '';
    default:
      return '';
  }
}

// ── Detail view ──────────────────────────────────────────────────────────

function showDetail(item, overrideTab) {
  const tab = overrideTab || currentTab;
  detailPanel.classList.remove('hidden');
  detailPanel.innerHTML = renderDetail(item, tab);
  if (window.innerWidth <= 768) {
    detailPanel.scrollIntoView({ behavior: 'smooth' });
  }
}

function renderDetail(item, tab) {
  switch (tab || currentTab) {
    case 'spells': return renderSpell(item);
    case 'feats': return renderFeat(item);
    case 'classes': return renderClass(item);
    case 'races': return renderRace(item);
    case 'equipment': return renderEquipment(item);
    case 'monsters': return renderMonster(item);
    case 'rules': return renderRules(item);
    default: return `<h2>${esc(item.name)}</h2>`;
  }
}

function renderSpell(s) {
  const fields = [
    [t('detail.spell.school'), [s.school, s.subschool ? `(${s.subschool})` : '', s.descriptor ? `[${s.descriptor}]` : ''].filter(Boolean).join(' ')],
    [t('detail.spell.level'), s.level],
    [t('detail.spell.components'), s.components],
    [t('detail.spell.casting_time'), s.casting_time],
    [t('detail.spell.range'), s.range],
    [t('detail.spell.target'), s.target_area_effect],
    [t('detail.spell.duration'), s.duration],
    [t('detail.spell.saving_throw'), s.saving_throw],
    [t('detail.spell.spell_resistance'), s.spell_resistance],
  ];
  return `<h2>${esc(s.name)}</h2>` + renderFields(fields) + renderDesc(s.desc_html);
}

function renderFeat(f) {
  const fields = [
    [t('detail.feat.type'), f.type],
    [t('detail.feat.prerequisites'), f.prerequisites],
    [t('detail.feat.benefit'), f.benefit],
    [t('detail.feat.normal'), f.normal],
    [t('detail.feat.special'), f.special],
  ];
  return `<h2>${esc(f.name)}</h2>` + renderFields(fields) + renderDesc(f.desc_html);
}

function renderClass(c) {
  const fields = [
    [t('detail.class.hit_die'), c.hit_die],
    [t('detail.class.alignment'), c.alignment],
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
    html += r.traits.map((tr) => `<li>${tr}</li>`).join('');
    html += '</ul></div>';
  }
  html += renderDesc(r.desc_html);
  return html;
}

function renderEquipment(e) {
  let html = `<h2>${esc(e.name)}</h2>`;
  const cat = e._category || e.category || '';
  const catLabel = cat === 'weapon' ? t('cat.weapon') : cat === 'armor' ? t('cat.armor') : cat === 'goods' ? t('cat.goods') : cat;
  html += `<div class="field"><span class="field-label">${t('detail.equip.category')}</span><div class="field-value">${esc(catLabel)}</div></div>`;

  const skip = new Set(['name', 'slug', '_category', 'category', 'desc_html']);
  const entries = Object.entries(e).filter(([k]) => !skip.has(k));
  for (const [key, val] of entries) {
    if (val) {
      html += `<div class="field"><span class="field-label">${esc(key)}</span><div class="field-value">${esc(String(val))}</div></div>`;
    }
  }
  return html;
}

function renderMonster(m) {
  const fields = [
    [t('detail.monster.type'), m.type],
    [t('detail.monster.hit_dice'), m.hit_dice],
    [t('detail.monster.initiative'), m.initiative],
    [t('detail.monster.speed'), m.speed],
    [t('detail.monster.armor_class'), m.armor_class],
    [t('detail.monster.base_attack'), m.base_attack_grapple],
    [t('detail.monster.attack'), m.attack],
    [t('detail.monster.full_attack'), m.full_attack],
    [t('detail.monster.space_reach'), m.space_reach],
    [t('detail.monster.special_attacks'), m.special_attacks],
    [t('detail.monster.special_qualities'), m.special_qualities],
    [t('detail.monster.saves'), m.saves],
    [t('detail.monster.abilities'), m.abilities],
    [t('detail.monster.skills'), m.skills],
    [t('detail.monster.feats'), m.feats],
    [t('detail.monster.environment'), m.environment],
    [t('detail.monster.organization'), m.organization],
    [t('detail.monster.cr'), m.challenge_rating],
    [t('detail.monster.treasure'), m.treasure],
    [t('detail.monster.alignment'), m.alignment],
    [t('detail.monster.advancement'), m.advancement],
    [t('detail.monster.level_adjustment'), m.level_adjustment],
  ];
  return `<h2>${esc(m.name)}</h2>` + renderFields(fields) + renderDesc(m.desc_html);
}

function renderRules(r) {
  return `<h2>${esc(r.name)}</h2>` + renderDesc(r.desc_html);
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

async function initApp() {
  await loadI18n();
  updateTabLabels();
  searchInput.placeholder = t('search.placeholder');
  initLangSwitcher();
  buildFilters();
  renderResults();
}

initApp();

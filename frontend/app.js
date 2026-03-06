/* Crystal Ball — Static JSON frontend (i18n-aware) */

const DATA_BASE = 'data';

const resultsList = document.getElementById('results-list');
const detailPanel = document.getElementById('detail-panel');
const searchInput = document.getElementById('search');
const searchClear = document.getElementById('search-clear');
const filtersDiv = document.getElementById('filters');

let currentTab = 'spells';
let dataCache = {};
let debounceTimer = null;
let sourcesData = null;

// Known spellcasting class abbreviations (EN + IT)
const SPELL_CLASSES = new Set([
  'Brd', 'Clr', 'Drd', 'Pal', 'Rgr', 'Sor/Wiz', 'Sor', 'Wiz',
  'Chr', 'Str/Mag', 'Str', 'Mag',
]);

// School-of-magic color map (EN + IT names)
const SCHOOL_COLORS = {
  'abjuration': '#4fc3f7', 'abiurazione': '#4fc3f7',
  'conjuration': '#81c784', 'evocazione': '#81c784',
  'divination': '#90caf9', 'divinazione': '#90caf9',
  'enchantment': '#f48fb1', 'ammaliamento': '#f48fb1',
  'evocation': '#ff8a65', 'invocazione': '#ff8a65',
  'illusion': '#ce93d8', 'illusione': '#ce93d8',
  'necromancy': '#ef5350', 'necromanzia': '#ef5350',
  'transmutation': '#ffd54f', 'trasmutazione': '#ffd54f',
  'universal': '#b0bec5', 'universale': '#b0bec5',
};

function getSchoolColor(school) {
  return school ? (SCHOOL_COLORS[school.toLowerCase()] || '') : '';
}

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

// ── Learned feats (localStorage) ──────────────────────────────────────────

const LEARNED_KEY = 'crystalball_learned';

function loadLearned() {
  try {
    return JSON.parse(localStorage.getItem(LEARNED_KEY)) || {};
  } catch { return {}; }
}

function saveLearned(learned) {
  localStorage.setItem(LEARNED_KEY, JSON.stringify(learned));
}

function toggleLearned(feat) {
  const l = loadLearned();
  if (l[feat.slug]) {
    delete l[feat.slug];
  } else {
    l[feat.slug] = { name: feat.name, slug: feat.slug };
  }
  saveLearned(l);
}

function removeLearned(slug) {
  const l = loadLearned();
  delete l[slug];
  saveLearned(l);
}

// ── Data loading (static JSON + i18n overlay) ────────────────────────────

async function loadData(category) {
  if (category === 'prepared' || category === 'learned') return null; // handled separately
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
    searchClear.classList.add('hidden');
    detailPanel.classList.add('hidden');
    const hideSearch = currentTab === 'prepared' || currentTab === 'learned' || currentTab === 'translation-status';
    searchInput.parentElement.style.display = hideSearch ? 'none' : '';
    buildFilters();
    renderResults();
  });
});

// ── Search ───────────────────────────────────────────────────────────────

searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderResults, 150);
  searchClear.classList.toggle('hidden', !searchInput.value);
});

searchClear.addEventListener('click', () => {
  searchInput.value = '';
  searchClear.classList.add('hidden');
  searchInput.focus();
  renderResults();
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
    learned: 'tab.learned',
    classes: 'tab.classes',
    races: 'tab.races',
    equipment: 'tab.equipment',
    monsters: 'tab.monsters',
    rules: 'tab.rules',
    'translation-status': 'tab.translation_status',
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
      <select id="filter-domain"><option value="">${t('filter.all_domains')}</option></select>
      <select id="filter-source"><option value="">${t('filter.all_sources')}</option></select>
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
    filtersDiv.querySelector('#filter-class').addEventListener('change', () => {
      if (document.getElementById('filter-class').value) {
        document.getElementById('filter-domain').value = '';
      }
      renderResults();
    });
    filtersDiv.querySelector('#filter-domain').addEventListener('change', () => {
      if (document.getElementById('filter-domain').value) {
        document.getElementById('filter-class').value = '';
      }
      renderResults();
    });
    filtersDiv.querySelector('#filter-source').addEventListener('change', renderResults);
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
  } else if (currentTab === 'learned') {
    filtersDiv.innerHTML = `
      <button id="clear-learned" class="level-toggle" style="color: #e57373;">${t('btn.clear_learned')}</button>
      <span id="result-count"></span>
    `;
    filtersDiv.querySelector('#clear-learned').addEventListener('click', () => {
      if (confirm(t('msg.confirm_clear_learned'))) {
        saveLearned({});
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

  // Split classes and domains
  const classSet = new Set();
  const domainSet = new Set();
  data.forEach((s) => {
    parseSpellLevels(s.level).forEach((l) => {
      if (SPELL_CLASSES.has(l.cls)) {
        classSet.add(l.cls);
      } else {
        domainSet.add(l.cls);
      }
    });
  });

  const classSel = document.getElementById('filter-class');
  [...classSet].sort().forEach((c) => {
    classSel.innerHTML += `<option value="${esc(c)}">${esc(c)}</option>`;
  });

  const domainSel = document.getElementById('filter-domain');
  [...domainSet].sort().forEach((d) => {
    domainSel.innerHTML += `<option value="${esc(d)}">${esc(d)}</option>`;
  });

  // Sources (manuals)
  const sourceSet = new Set(data.map((s) => s.source).filter(Boolean));
  const sourceSel = document.getElementById('filter-source');
  if (sourceSel) {
    const lang = getCurrentLang();
    [...sourceSet].sort().forEach((src) => {
      const info = sourcesData[src];
      const label = info
        ? (lang === 'en' ? info.abbreviation : (info.abbreviation_it || info.abbreviation))
        : src;
      const fullName = info
        ? (lang === 'en' ? info.name_en : (info.name_it || info.name_en))
        : src;
      sourceSel.innerHTML += `<option value="${esc(src)}" title="${esc(fullName)}">${esc(label)} — ${esc(fullName)}</option>`;
    });
  }
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

  // Special handling for learned feats tab
  if (currentTab === 'learned') {
    renderLearnedList();
    return;
  }

  // Special handling for translation status tab
  if (currentTab === 'translation-status') {
    renderTranslationStatus();
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
    const domain = document.getElementById('filter-domain')?.value;
    const filterCls = cls || domain; // use whichever is set (mutually exclusive)
    const levels = getSelectedLevels();

    if (school) filtered = filtered.filter((s) => s.school === school);

    const source = document.getElementById('filter-source')?.value;
    if (source) filtered = filtered.filter((s) => s.source === source);

    // Filter by class/domain + levels
    filtered = filtered.filter((s) => {
      const parsed = parseSpellLevels(s.level);
      if (parsed.length === 0) return levels.size === 10; // show unknown-level if all selected
      if (filterCls) {
        // Must have this class/domain AND level in selected set
        return parsed.some((l) => l.cls === filterCls && levels.has(l.lvl));
      }
      // Any class at a selected level
      return parsed.some((l) => levels.has(l.lvl));
    });

    // Sort by level (lowest first within the selected class/domain)
    filtered.sort((a, b) => {
      const aLevels = parseSpellLevels(a.level);
      const bLevels = parseSpellLevels(b.level);
      const aMin = Math.min(...aLevels.map((l) => filterCls ? (l.cls === filterCls ? l.lvl : 99) : l.lvl));
      const bMin = Math.min(...bLevels.map((l) => filterCls ? (l.cls === filterCls ? l.lvl : 99) : l.lvl));
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

  // Sort non-spell tabs alphabetically by (translated) name
  if (currentTab !== 'spells') {
    filtered.sort((a, b) => a.name.localeCompare(b.name));
  }

  // Update count
  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = t('msg.results_count', { count: filtered.length });

  if (filtered.length === 0) {
    resultsList.innerHTML = `<div class="no-results">${t('msg.no_results')}</div>`;
    return;
  }

  const prepared = currentTab === 'spells' ? loadPrepared() : {};
  const learned = currentTab === 'feats' ? loadLearned() : {};

  resultsList.innerHTML = filtered.map((item, idx) => {
    const meta = getMeta(item);
    let actionHtml = '';
    if (currentTab === 'spells') {
      const p = prepared[item.slug];
      if (p) {
        const allUsed = p.used >= p.prepared;
        actionHtml = `<span class="prep-badge ${allUsed ? 'exhausted' : ''}">${p.used}/${p.prepared}</span>`
          + `<button class="prep-btn prep-btn-active" data-idx="${idx}" title="${t('btn.add_prep')}">+</button>`;
      } else {
        actionHtml = `<button class="prep-btn" data-idx="${idx}" title="${t('btn.prepare_spell')}">+</button>`;
      }
    } else if (currentTab === 'feats') {
      const isLearned = !!learned[item.slug];
      actionHtml = `<button class="learn-btn ${isLearned ? 'learn-btn-active' : ''}" data-idx="${idx}" title="${isLearned ? t('btn.unlearn_feat') : t('btn.learn_feat')}">\u2713</button>`;
    }
    const isPrepared = currentTab === 'spells' && prepared[item.slug];
    const isLearned = currentTab === 'feats' && learned[item.slug];
    const schoolStyle = currentTab === 'spells' && item.school ? ` style="--school-clr: ${getSchoolColor(item.school)}"` : '';
    return `<div class="result-item ${isPrepared ? 'is-prepared' : ''} ${isLearned ? 'is-learned' : ''}" data-index="${idx}" data-slug="${item.slug || ''}"${schoolStyle}>
      <div class="result-row">
        <div class="result-text">
          <div class="name">${esc(item.name)}${renderSourceBadge(item)}${item._name_en ? `<span class="name-en">${esc(item._name_en)}</span>` : ''}</div>
          ${meta ? `<div class="meta">${esc(meta)}</div>` : ''}
        </div>
        ${actionHtml}
      </div>
    </div>`;
  }).join('');

  // Store filtered list for detail lookup
  resultsList._filtered = filtered;

  resultsList.querySelectorAll('.result-item').forEach((el) => {
    el.addEventListener('click', (e) => {
      if (e.target.classList.contains('prep-btn') || e.target.classList.contains('learn-btn')) return;
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
      renderResults();
    });
  });

  // Learn feat buttons
  resultsList.querySelectorAll('.learn-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const item = resultsList._filtered[parseInt(btn.dataset.idx)];
      toggleLearned(item);
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

  // Resolve names, school, level in current language
  const spells = await loadData('spells');
  const spellMap = {};
  if (spells) spells.forEach((s) => { spellMap[s.slug] = s; });
  entries.forEach((p) => {
    const sp = spellMap[p.slug];
    if (sp) {
      p.name = sp.name;
      p._name_en = sp._name_en || '';
      p.school = sp.school || '';
      p.level = sp.level || '';
    }
  });

  // Sort by minimum spell level (ascending), then by name
  entries.sort((a, b) => {
    const aLvls = parseSpellLevels(a.level);
    const bLvls = parseSpellLevels(b.level);
    const aMin = aLvls.length ? Math.min(...aLvls.map(l => l.lvl)) : 99;
    const bMin = bLvls.length ? Math.min(...bLvls.map(l => l.lvl)) : 99;
    return aMin - bMin || a.name.localeCompare(b.name);
  });

  resultsList.innerHTML = entries.map((p) => {
    const allUsed = p.used >= p.prepared;
    const schoolClr = getSchoolColor(p.school);
    const schoolStyle = schoolClr ? ` style="--school-clr: ${schoolClr}"` : '';
    const meta = [p.school, p.level].filter(Boolean).join(' — ');
    return `<div class="result-item prepared-item ${allUsed ? 'all-used' : ''}" data-slug="${esc(p.slug)}"${schoolStyle}>
      <div class="prep-info">
        <div class="prep-name">${esc(p.name)}${p._name_en ? `<span class="name-en">${esc(p._name_en)}</span>` : ''}</div>
        ${meta ? `<div class="meta">${esc(meta)}</div>` : ''}
      </div>
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

// ── Learned feats tab ─────────────────────────────────────────────────────

async function renderLearnedList() {
  const learned = loadLearned();
  const entries = Object.values(learned);

  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = t('msg.learned_count', { count: entries.length });

  if (entries.length === 0) {
    resultsList.innerHTML = `<div class="no-results">${t('msg.no_learned')}</div>`;
    detailPanel.classList.add('hidden');
    return;
  }

  // Resolve names in current language
  const feats = await loadData('feats');
  const nameMap = {};
  const enNameMap = {};
  if (feats) feats.forEach((f) => { nameMap[f.slug] = f.name; enNameMap[f.slug] = f._name_en || ''; });
  entries.forEach((l) => { l.name = nameMap[l.slug] || l.name; l._name_en = enNameMap[l.slug] || ''; });

  // Sort by name
  entries.sort((a, b) => a.name.localeCompare(b.name));

  resultsList.innerHTML = entries.map((l) => {
    return `<div class="result-item learned-item" data-slug="${esc(l.slug)}">
      <div class="learned-name">${esc(l.name)}${l._name_en ? `<span class="name-en">${esc(l._name_en)}</span>` : ''}</div>
      <button class="remove-btn" data-slug="${esc(l.slug)}" title="${t('btn.remove')}">&times;</button>
    </div>`;
  }).join('');

  // Click name to show detail
  resultsList.querySelectorAll('.learned-name').forEach((el) => {
    el.addEventListener('click', async () => {
      const slug = el.parentElement.dataset.slug;
      const feats = await loadData('feats');
      if (!feats) return;
      const feat = feats.find((f) => f.slug === slug);
      if (feat) showDetail(feat, 'feats');
    });
  });

  // Remove buttons
  resultsList.querySelectorAll('.remove-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      removeLearned(btn.dataset.slug);
      renderLearnedList();
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
  detailPanel.innerHTML = `<button class="detail-close" aria-label="Chiudi">&times;</button>` + renderDetail(item, tab);
  detailPanel.querySelector('.detail-close').addEventListener('click', () => {
    detailPanel.classList.add('hidden');
  });
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
    default: return renderDetailTitle(item);
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
  // Add source reference if available
  if (s.manual_name || s.reference) {
    const ref = [s.manual_name, s.reference].filter(Boolean).join(', ');
    fields.push([t('source.label'), ref]);
  }
  let html = renderDetailTitle(s) + renderFields(fields);
  // Show summary if no full description
  if (!s.desc_html && s.summary_it) {
    html += `<div class="desc-html"><p><em>${esc(s.summary_it)}</em></p></div>`;
  } else {
    html += renderDesc(s.desc_html);
  }
  return html;
}

function renderFeat(f) {
  const fields = [
    [t('detail.feat.type'), f.type],
    [t('detail.feat.prerequisites'), f.prerequisites],
    [t('detail.feat.benefit'), f.benefit],
    [t('detail.feat.normal'), f.normal],
    [t('detail.feat.special'), f.special],
  ];
  return renderDetailTitle(f) + renderFields(fields);
}

function renderClass(c) {
  const fields = [
    [t('detail.class.hit_die'), c.hit_die],
    [t('detail.class.alignment'), c.alignment],
  ];
  let html = renderDetailTitle(c) + renderFields(fields);
  if (c.table_html) {
    html += `<div class="desc-html">${c.table_html}</div>`;
  }
  html += renderDesc(c.desc_html);
  return html;
}

function renderRace(r) {
  let html = renderDetailTitle(r);
  if (r.traits && r.traits.length) {
    html += '<div class="desc-html"><ul>';
    html += r.traits.map((tr) => `<li>${tr}</li>`).join('');
    html += '</ul></div>';
  }
  html += renderDesc(r.desc_html);
  return html;
}

function renderEquipment(e) {
  let html = renderDetailTitle(e);
  const cat = e._category || e.category || '';
  const catLabel = cat === 'weapon' ? t('cat.weapon') : cat === 'armor' ? t('cat.armor') : cat === 'goods' ? t('cat.goods') : cat;
  html += `<div class="field"><span class="field-label">${t('detail.equip.category')}</span><div class="field-value">${esc(catLabel)}</div></div>`;

  const skip = new Set(['name', 'slug', '_category', 'category', 'desc_html', 'source']);
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
  return renderDetailTitle(m) + renderFields(fields) + renderDesc(m.desc_html);
}

function renderRules(r) {
  return renderDetailTitle(r) + renderDesc(r.desc_html);
}

// ── Detail title with EN subtitle ────────────────────────────────────────

function renderDetailTitle(item) {
  let html = `<h2>${esc(item.name)}${renderSourceBadge(item)}</h2>`;
  if (item._name_en) {
    html += `<div class="detail-name-en">${esc(item._name_en)}</div>`;
  }
  return html;
}

// ── Source badge ─────────────────────────────────────────────────────────

function renderSourceBadge(item) {
  if (!item.source) return '';
  let label = item.source;
  if (sourcesData && sourcesData[item.source]) {
    const lang = getCurrentLang();
    const src = sourcesData[item.source];
    label = src['abbreviation_' + lang] || src.abbreviation || item.source;
  }
  return `<span class="source-badge">${esc(label)}</span>`;
}

async function loadSources() {
  try {
    const res = await fetch(`${DATA_BASE}/sources.json`);
    if (res.ok) sourcesData = await res.json();
  } catch {}
}

// ── Translation status dashboard ────────────────────────────────────────

async function renderTranslationStatus(selectedLang) {
  detailPanel.classList.add('hidden');
  resultsList.innerHTML = `<div class="loading">${t('msg.loading')}</div>`;

  try {
    // Fetch index to discover available languages
    const indexRes = await fetch(`${DATA_BASE}/translation-status-index.json`);
    let langs = [];
    if (indexRes.ok) {
      const index = await indexRes.json();
      langs = index.languages || [];
    }

    // Determine which language to show
    const lang = selectedLang || (langs.includes(getCurrentLang()) ? getCurrentLang() : langs[0]) || 'it';

    // Fetch per-language status
    const statusUrl = langs.length > 0
      ? `${DATA_BASE}/translation-status-${lang}.json`
      : `${DATA_BASE}/translation-status.json`;
    const res = await fetch(statusUrl);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderStatusDashboard(data, langs, lang);
  } catch (err) {
    resultsList.innerHTML = `<div class="no-results">Translation status data not available.</div>`;
  }
}

function renderStatusDashboard(data, langs, activeLang) {
  const s = data.summary;
  const overallPct = s.overall_percent.toFixed(1);
  const barClass = s.overall_percent >= 100 ? 'complete' : '';

  let html = `<div class="status-dashboard">`;

  // Language selector (if multiple languages available)
  if (langs && langs.length > 1) {
    html += `<div class="status-lang-selector">`;
    langs.forEach((lng) => {
      const label = t(`lang.${lng}`) || lng.toUpperCase();
      const active = lng === activeLang ? ' active' : '';
      html += `<button class="status-lang-btn${active}" data-status-lang="${lng}">${esc(label)}</button>`;
    });
    html += `</div>`;
  } else if (langs && langs.length === 1) {
    const label = t(`lang.${langs[0]}`) || langs[0].toUpperCase();
    html += `<div class="status-lang-label">${esc(label)}</div>`;
  }

  html += `<div class="status-overall">`;
  html += `<h3>${t('status.overall')}</h3>`;
  html += `<div class="status-pct">${overallPct}%</div>`;
  html += `<div class="status-bar-outer"><div class="status-bar-fill ${barClass}" style="width:${overallPct}%"></div></div>`;
  html += `<div style="margin-top:0.3rem;color:var(--text-dim);font-size:0.85rem">${s.translated_fields} / ${s.total_fields} ${t('status.field').toLowerCase()}</div>`;
  html += `</div>`;

  const cats = data.categories;
  for (const [catName, cat] of Object.entries(cats)) {
    const fields = cat.fields;
    const fieldKeys = Object.keys(fields);
    const catTranslated = fieldKeys.reduce((acc, k) => acc + fields[k].translated, 0);
    const catTotal = fieldKeys.reduce((acc, k) => acc + fields[k].total, 0);
    const catPct = catTotal > 0 ? ((catTranslated / catTotal) * 100).toFixed(1) : '0.0';

    html += `<div class="status-category" data-cat="${esc(catName)}">`;
    html += `<div class="status-cat-header" onclick="this.parentElement.classList.toggle('open')">`;
    html += `<span>${esc(catName.toUpperCase())} — ${cat.total} ${t('status.entries')}</span>`;
    html += `<span class="cat-pct">${catPct}%</span>`;
    html += `</div>`;
    html += `<div class="status-cat-body">`;

    for (const [fieldName, f] of Object.entries(fields)) {
      const pct = f.percent.toFixed(1);
      const fillClass = f.percent >= 100 ? 'complete' : '';
      const hasIssues = f.issues && f.issues.length > 0;
      const fieldId = `status-${catName}-${fieldName}`.replace(/[^a-z0-9-]/g, '-');
      html += `<div class="status-field-row${hasIssues ? ' has-issues' : ''}"${hasIssues ? ` onclick="document.getElementById('${fieldId}').classList.toggle('open')"` : ''}>`;
      html += `<span class="field-name">${esc(fieldName)}</span>`;
      html += `<div class="field-bar"><div class="field-bar-fill ${fillClass}" style="width:${pct}%"></div></div>`;
      html += `<span class="field-stats">${f.translated}/${f.total} (${pct}%)</span>`;

      // Quality badges
      const badges = [];
      if (f.identical_to_en > 0) badges.push(`<span class="badge badge-identical">${f.identical_to_en} identici EN</span>`);
      if (f.ocr_issues > 0) badges.push(`<span class="badge badge-ocr">${f.ocr_issues} OCR</span>`);
      if (f.english_residue > 0) badges.push(`<span class="badge badge-english">${f.english_residue} inglese</span>`);
      if (badges.length > 0) html += `<span class="field-badges">${badges.join('')}</span>`;

      html += `</div>`;

      // Expandable issues list
      if (hasIssues) {
        html += `<div class="field-issues-list" id="${fieldId}">`;
        for (const issue of f.issues) {
          const itVal = issue.value || '';
          const enVal = issue.en_value || '';
          const detail = issue.details || issue.words || '';
          const typeLabel = { missing: 'mancante', identical: 'identico EN', ocr: 'OCR', english: 'inglese', length_anomaly: 'lunghezza' }[issue.type] || issue.type;
          html += `<div class="issue-item">`;
          html += `<span class="issue-slug">${esc(issue.slug)}</span>`;
          html += `<span class="issue-type issue-${issue.type}">${typeLabel}</span>`;
          html += `<span class="issue-values">`;
          if (enVal) html += `<span class="issue-en"><b>EN:</b> ${esc(enVal.substring(0, 100))}</span>`;
          if (itVal && itVal !== enVal) html += `<span class="issue-it"><b>IT:</b> ${esc(itVal.substring(0, 100))}</span>`;
          html += `</span>`;
          if (detail) {
            const detailLabel = issue.type === 'english' ? 'residuo' : issue.type === 'ocr' ? 'problema' : '';
            html += `<span class="issue-detail">${detailLabel ? `<b>${detailLabel}:</b> ` : ''}${esc(String(detail).substring(0, 80))}</span>`;
          }
          html += `</div>`;
        }
        html += `</div>`;
      }
    }

    html += `</div></div>`;
  }

  if (data.generated_at) {
    html += `<div class="status-generated">${t('status.generated')}: ${data.generated_at}</div>`;
  }

  html += `</div>`;
  resultsList.innerHTML = html;

  // Auto-open categories with <100%
  resultsList.querySelectorAll('.status-category').forEach((el) => {
    const pctText = el.querySelector('.cat-pct').textContent;
    if (parseFloat(pctText) < 100) el.classList.add('open');
  });

  // Language selector buttons
  resultsList.querySelectorAll('.status-lang-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      renderTranslationStatus(btn.dataset.statusLang);
    });
  });
}

// ── Render helpers ───────────────────────────────────────────────────────

function renderFields(fields) {
  const rows = fields
    .filter(([, v]) => v)
    .map(([label, value]) =>
      `<div class="field"><span class="field-label">${esc(label)}</span><div class="field-value">${escAllowInline(String(value))}</div></div>`
    )
    .join('');
  return rows ? `<div class="fields-grid">${rows}</div>` : '';
}

function renderDesc(html) {
  if (!html) return '';
  return `<div class="desc-html">${html}</div>`;
}

function escAllowInline(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/&lt;(\/?(?:i|em|b|strong))&gt;/g, '<$1>');
}

function esc(str) {
  if (!str) return '';
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

// ── Header toggle ────────────────────────────────────────────────────────

function initHeaderToggle() {
  const header = document.getElementById('app-header');
  const toggle = document.getElementById('header-toggle');
  if (!header || !toggle) return;

  const collapsed = localStorage.getItem('crystalball_header_collapsed') === '1';
  if (collapsed) {
    header.classList.add('collapsed');
    toggle.textContent = '▼';
  }

  toggle.addEventListener('click', () => {
    header.classList.toggle('collapsed');
    const isCollapsed = header.classList.contains('collapsed');
    toggle.textContent = isCollapsed ? '▼' : '▲';
    localStorage.setItem('crystalball_header_collapsed', isCollapsed ? '1' : '0');
    updateContentHeight();
  });
}

function updateContentHeight() {
  const mainEl = document.querySelector('main');
  if (!mainEl) return;
  const top = mainEl.getBoundingClientRect().top;
  const height = window.innerHeight - top - 16; // 16px bottom padding
  document.documentElement.style.setProperty('--content-height', `${Math.max(200, height)}px`);
}

// ── Init ─────────────────────────────────────────────────────────────────

async function initApp() {
  await loadI18n();
  await loadSources();
  updateTabLabels();
  searchInput.placeholder = t('search.placeholder');
  initLangSwitcher();
  initHeaderToggle();
  buildFilters();
  renderResults();
  updateContentHeight();
  window.addEventListener('resize', updateContentHeight);
}

initApp();

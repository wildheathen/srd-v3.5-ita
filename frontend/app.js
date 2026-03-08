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
let sourceBookMap = null;   // reverse map: normalised source_book → abbreviation key

// ── Virtual scroll state ────────────────────────────────────────────────
const VS_ROW_HEIGHT = 64;  // px per result item (padding + margin + content)
const VS_BUFFER = 15;      // extra rows above/below viewport
let vsFilteredData = [];    // current filtered dataset for virtual scroll
let vsDisplayMap = [];      // maps display-row-index → {type:'header',label,level,count} | {type:'item',dataIdx}
let vsDataToDisplay = {};   // reverse map: dataIdx → displayIdx (for scroll-to-item)
let vsCollapsedLevels = new Set(); // collapsed level groups (-1 = no level, 0-9 = spell levels)
let vsSpellFilterCls = '';  // current class/domain filter for spell level calculation
let vsLastRange = null;     // last rendered range {start, end} to avoid redundant renders
let vsRafPending = false;   // debounce rAF for scroll handler

// Known spell domains (EN + IT) — everything NOT in this set is treated as a class
const SPELL_DOMAINS = new Set([
  // Standard D&D 3.5 domains
  'Air', 'Animal', 'Chaos', 'Death', 'Destruction', 'Earth', 'Evil', 'Fire',
  'Good', 'Healing', 'Knowledge', 'Law', 'Luck', 'Magic', 'Plant',
  'Protection', 'Strength', 'Sun', 'Travel', 'Trickery', 'War', 'Water',
  // IT domain names
  'Aria', 'Animale', 'Caos', 'Morte', 'Distruzione', 'Terra', 'Male', 'Fuoco',
  'Bene', 'Guarigione', 'Conoscenza', 'Legge', 'Fortuna', 'Magia', 'Vegetale',
  'Protezione', 'Forza', 'Sole', 'Viaggio', 'Inganno', 'Guerra', 'Acqua',
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
  // Tome of Battle disciplines
  'desert wind': '#ff7043', 'devoted spirit': '#7986cb',
  'diamond mind': '#4dd0e1', 'iron heart': '#90a4ae',
  'setting sun': '#ffb74d', 'shadow hand': '#78909c',
  'stone dragon': '#a1887f', 'tiger claw': '#e57373',
  'white raven': '#e0e0e0',
};

function getSchoolColor(school) {
  if (!school) return '';
  const key = school.toLowerCase();
  // Direct match
  if (SCHOOL_COLORS[key]) return SCHOOL_COLORS[key];
  // Combined schools (e.g. "Abjuration/Evocation") — use first school's color
  if (key.includes('/')) {
    const first = key.split('/')[0].trim();
    if (SCHOOL_COLORS[first]) return SCHOOL_COLORS[first];
  }
  return '';
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
    searchInput.closest('.search-wrapper').style.display = hideSearch ? 'none' : '';
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
    // Remember selected item before switching language
    const prevSlug = detailPanel.classList.contains('hidden') ? null : detailPanel.dataset.activeSlug;
    const prevTab = currentTab;
    setLang(sel.value);
    clearAllDataCache();
    await loadI18n(sel.value);
    updateTabLabels();
    searchInput.placeholder = t('search.placeholder');
    const ftLabel = document.getElementById('fulltext-text');
    if (ftLabel) ftLabel.textContent = t('search.fulltext');
    buildFilters();
    await renderResults();
    // Re-select same item after language switch
    if (prevSlug && prevTab === currentTab) {
      const item = vsFilteredData.find(d => d.slug === prevSlug);
      if (item) {
        showDetail(item);
        // Scroll virtual list to bring the item into view
        const dataIdx = vsFilteredData.indexOf(item);
        const displayIdx = vsDataToDisplay[dataIdx] ?? dataIdx;
        resultsList.scrollTop = displayIdx * VS_ROW_HEIGHT;
        // After scroll triggers re-render, highlight the item
        requestAnimationFrame(() => {
          vsRenderVisible();
          const el = resultsList.querySelector(`[data-data-idx="${dataIdx}"]`);
          if (el) {
            resultsList.querySelectorAll('.selected').forEach(s => s.classList.remove('selected'));
            el.classList.add('selected');
          }
        });
      } else {
        detailPanel.classList.add('hidden');
      }
    } else {
      detailPanel.classList.add('hidden');
    }
  });
}

function updateTabLabels() {
  const tabMap = {
    spells: 'tab.spells',
    prepared: 'tab.prepared',
    feats: 'tab.feats',
    learned: 'tab.learned',
    skills: 'tab.skills',
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
  return levelStr.split(/[,;]/).map((part) => {
    const trimmed = part.trim();
    const match = trimmed.match(/^(.+?)\s+(\d+)$/);
    if (match) return { cls: match[1], lvl: parseInt(match[2]) };
    return null;
  }).filter(Boolean);
}

function getSpellSortLevel(item, filterCls) {
  const levels = parseSpellLevels(item.level);
  if (levels.length === 0) return -1;  // no level → sentinel
  if (filterCls) {
    const match = levels.find(l => l.cls === filterCls);
    return match ? match.lvl : Math.min(...levels.map(l => l.lvl));
  }
  return Math.min(...levels.map(l => l.lvl));
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
      <label class="edition-toggle" id="edition-toggle">
        <input type="checkbox" id="filter-show-30"> ${t('filter.show_3.0')}
      </label>
      <span id="result-count"></span>
    `;
    populateSpellFilters();
    filtersDiv.querySelector('#filter-show-30').addEventListener('change', renderResults);
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
      <label class="edition-toggle"><input type="checkbox" id="filter-show-30"> ${t('filter.show_3.0')}</label>
      <span id="result-count"></span>
    `;
    populateFeatTypeFilter();
    filtersDiv.querySelector('select').addEventListener('change', renderResults);
    filtersDiv.querySelector('#filter-show-30').addEventListener('change', renderResults);
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
      <label class="edition-toggle"><input type="checkbox" id="filter-show-30"> ${t('filter.show_3.0')}</label>
      <span id="result-count"></span>
    `;
    populateMonsterFilters();
    filtersDiv.querySelectorAll('select').forEach((s) =>
      s.addEventListener('change', renderResults)
    );
    filtersDiv.querySelector('#filter-show-30').addEventListener('change', renderResults);
  } else if (currentTab === 'skills') {
    filtersDiv.innerHTML = `
      <select id="filter-skill-category">
        <option value="">${t('filter.skills_and_tricks')}</option>
        <option value="skill">${t('filter.skills_only')}</option>
        <option value="skill_trick">${t('filter.tricks_only')}</option>
      </select>
      <select id="filter-ability"><option value="">${t('filter.all_abilities')}</option></select>
      <label class="level-check" style="margin-left:0.5rem"><input type="checkbox" id="filter-trained"> ${t('filter.trained_only')}</label>
      <label class="edition-toggle"><input type="checkbox" id="filter-show-30"> ${t('filter.show_3.0')}</label>
      <span id="result-count"></span>
    `;
    populateSkillFilters();
    filtersDiv.querySelector('#filter-skill-category').addEventListener('change', renderResults);
    filtersDiv.querySelector('#filter-ability').addEventListener('change', renderResults);
    filtersDiv.querySelector('#filter-trained').addEventListener('change', renderResults);
    filtersDiv.querySelector('#filter-show-30').addEventListener('change', renderResults);
  } else if (currentTab === 'classes') {
    filtersDiv.innerHTML = `
      <select id="filter-class-type">
        <option value="">${t('filter.all_types')}</option>
        <option value="prestige">${t('filter.prestige_only')}</option>
        <option value="base">${t('filter.base_only')}</option>
      </select>
      <label class="edition-toggle"><input type="checkbox" id="filter-show-30"> ${t('filter.show_3.0')}</label>
      <span id="result-count"></span>
    `;
    filtersDiv.querySelector('#filter-class-type').addEventListener('change', renderResults);
    filtersDiv.querySelector('#filter-show-30').addEventListener('change', renderResults);
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
  } else if (currentTab === 'races') {
    filtersDiv.innerHTML = `
      <label class="edition-toggle"><input type="checkbox" id="filter-show-30"> ${t('filter.show_3.0')}</label>
      <span id="result-count"></span>
    `;
    filtersDiv.querySelector('#filter-show-30').addEventListener('change', renderResults);
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

  // Split classes and domains (anything NOT in SPELL_DOMAINS is a class)
  const classSet = new Set();
  const domainSet = new Set();
  data.forEach((s) => {
    parseSpellLevels(s.level).forEach((l) => {
      if (SPELL_DOMAINS.has(l.cls)) {
        domainSet.add(l.cls);
      } else {
        classSet.add(l.cls);
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

async function populateSkillFilters() {
  const data = await loadData('skills');
  if (!data) return;
  const abilities = [...new Set(data.map((s) => s.key_ability).filter(Boolean))].sort();
  const sel = document.getElementById('filter-ability');
  abilities.forEach((a) => {
    sel.innerHTML += `<option value="${esc(a)}">${esc(a)}</option>`;
  });
}

// ── Filtering + rendering ────────────────────────────────────────────────

function getSelectedLevels() {
  const checks = filtersDiv.querySelectorAll('#filter-levels input:checked');
  return new Set([...checks].map((cb) => parseInt(cb.value)));
}

// ── HTML tag stripper for full-text search ───────────────────────────────
function stripHtml(html) {
  if (!html) return '';
  return html.replace(/<[^>]*>/g, ' ').replace(/&[a-z]+;/gi, ' ').replace(/\s+/g, ' ');
}

// ── Search term highlighting ─────────────────────────────────────────────
function highlightText(text, query) {
  if (!query) return esc(text);
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`(${escaped})`, 'gi');
  return esc(text).replace(re, '<mark>$1</mark>');
}

function highlightHtml(html, query) {
  if (!query || !html) return html;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`(${escaped})`, 'gi');
  // Only highlight inside text nodes (outside of HTML tags)
  return html.replace(/>([^<]+)</g, (match, textContent) => {
    return '>' + textContent.replace(re, '<mark>$1</mark>') + '<';
  });
}

function isFullTextSearch() {
  const el = document.getElementById('search-fulltext');
  return el && el.checked;
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
  const fullText = isFullTextSearch();

  // Text search
  if (q) {
    if (fullText) {
      filtered = filtered.filter((item) => {
        if (item.name.toLowerCase().includes(q)) return true;
        if (item._name_en && item._name_en.toLowerCase().includes(q)) return true;
        const plain = stripHtml(item.desc_html);
        if (plain.toLowerCase().includes(q)) return true;
        // Also search benefit/special for feats
        if (item.benefit && stripHtml(item.benefit).toLowerCase().includes(q)) return true;
        return false;
      });
    } else {
      filtered = filtered.filter((item) =>
        item.name.toLowerCase().includes(q) ||
        (item._name_en && item._name_en.toLowerCase().includes(q))
      );
    }
  }

  // Edition filter (shared across tabs that have the toggle)
  const show30El = document.getElementById('filter-show-30');
  if (show30El && !show30El.checked) {
    filtered = filtered.filter((item) => !item.edition || item.edition !== '3.0');
  }

  // Category-specific filters
  let spellFilterCls = '';
  if (currentTab === 'spells') {
    const school = document.getElementById('filter-school')?.value;
    const cls = document.getElementById('filter-class')?.value;
    const domain = document.getElementById('filter-domain')?.value;
    const filterCls = cls || domain; // use whichever is set (mutually exclusive)
    spellFilterCls = filterCls;
    vsSpellFilterCls = filterCls;
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
  } else if (currentTab === 'skills') {
    const cat = document.getElementById('filter-skill-category')?.value;
    const ability = document.getElementById('filter-ability')?.value;
    const trained = document.getElementById('filter-trained')?.checked;
    if (cat) filtered = filtered.filter((s) => s.category === cat);
    if (ability) filtered = filtered.filter((s) => s.key_ability === ability);
    if (trained) filtered = filtered.filter((s) => s.trained_only === true);
  } else if (currentTab === 'classes') {
    const classType = document.getElementById('filter-class-type')?.value;
    if (classType === 'prestige') filtered = filtered.filter((c) => c.is_prestige === 'True' || c.is_prestige === true);
    if (classType === 'base') filtered = filtered.filter((c) => c.is_prestige !== 'True' && c.is_prestige !== true);
  }

  // Sort non-spell tabs alphabetically by (translated) name
  if (currentTab !== 'spells') {
    filtered.sort((a, b) => a.name.localeCompare(b.name));
  }

  // Update count
  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = t('msg.results_count', { count: filtered.length });

  if (filtered.length === 0) {
    vsFilteredData = [];
    vsLastRange = null;
    resultsList.innerHTML = `<div class="no-results">${t('msg.no_results')}</div>`;
    return;
  }

  // Store filtered data for virtual scroll rendering
  vsFilteredData = filtered;
  vsCollapsedLevels.clear();  // reset collapsed state when filters change
  vsLastRange = null;
  resultsList._filtered = filtered;
  resultsList._searchQuery = q;

  // Build display map (interleave level headers for spells tab)
  vsDisplayMap = [];
  vsDataToDisplay = {};
  if (currentTab === 'spells') {
    // First pass: group items by level to get counts
    const levelGroups = [];
    let lastLevel = null;
    for (let i = 0; i < filtered.length; i++) {
      const lvl = getSpellSortLevel(filtered[i], spellFilterCls);
      if (lvl !== lastLevel) {
        levelGroups.push({ level: lvl, startIdx: i, count: 0 });
        lastLevel = lvl;
      }
      levelGroups[levelGroups.length - 1].count++;
    }
    // Second pass: build display map with collapse support
    let dataIdx = 0;
    for (const group of levelGroups) {
      const label = group.level === -1
        ? t('spell.no_level_header')
        : t('spell.level_header', { level: group.level });
      const collapsed = vsCollapsedLevels.has(group.level);
      vsDisplayMap.push({ type: 'header', label, level: group.level, count: group.count, collapsed });
      for (let j = 0; j < group.count; j++) {
        const i = group.startIdx + j;
        if (!collapsed) {
          vsDataToDisplay[i] = vsDisplayMap.length;
          vsDisplayMap.push({ type: 'item', dataIdx: i });
        }
      }
    }
  } else {
    for (let i = 0; i < filtered.length; i++) {
      vsDataToDisplay[i] = i;
      vsDisplayMap.push({ type: 'item', dataIdx: i });
    }
  }

  // Setup virtual scroll container
  const totalHeight = vsDisplayMap.length * VS_ROW_HEIGHT;
  resultsList.innerHTML = `<div class="vs-spacer" style="height:${totalHeight}px;position:relative"></div>`;
  resultsList._vsSpacer = resultsList.querySelector('.vs-spacer');

  // Event delegation: single listener on spacer (never re-bound per render)
  resultsList._vsSpacer.addEventListener('click', vsHandleClick);

  // Remove old scroll listener, add new one
  resultsList.removeEventListener('scroll', vsOnScroll);
  resultsList.addEventListener('scroll', vsOnScroll);

  // Initial render of visible rows
  vsRenderVisible();
}

function vsOnScroll() {
  if (!vsRafPending) {
    vsRafPending = true;
    requestAnimationFrame(() => {
      vsRafPending = false;
      vsRenderVisible();
    });
  }
}

// Rebuild display map after collapse toggle (no re-filter needed)
function vsRebuildDisplayMap() {
  const filtered = vsFilteredData;
  if (!filtered.length) return;

  const q = resultsList._searchQuery || '';

  // Rebuild display map
  vsDisplayMap = [];
  vsDataToDisplay = {};
  let lastLevel = null;
  const levelGroups = [];
  for (let i = 0; i < filtered.length; i++) {
    const lvl = getSpellSortLevel(filtered[i], vsSpellFilterCls);
    if (lvl !== lastLevel) {
      levelGroups.push({ level: lvl, startIdx: i, count: 0 });
      lastLevel = lvl;
    }
    levelGroups[levelGroups.length - 1].count++;
  }
  for (const group of levelGroups) {
    const label = group.level === -1
      ? t('spell.no_level_header')
      : t('spell.level_header', { level: group.level });
    const collapsed = vsCollapsedLevels.has(group.level);
    vsDisplayMap.push({ type: 'header', label, level: group.level, count: group.count, collapsed });
    for (let j = 0; j < group.count; j++) {
      const i = group.startIdx + j;
      if (!collapsed) {
        vsDataToDisplay[i] = vsDisplayMap.length;
        vsDisplayMap.push({ type: 'item', dataIdx: i });
      }
    }
  }

  // Re-setup spacer height and re-render
  const totalHeight = vsDisplayMap.length * VS_ROW_HEIGHT;
  const spacer = resultsList._vsSpacer;
  spacer.style.height = totalHeight + 'px';
  vsLastRange = null;
  vsRenderVisible();
}

function vsCreateRow(displayIdx, prepared, learned, q) {
  const entry = vsDisplayMap[displayIdx];
  const top = displayIdx * VS_ROW_HEIGHT;
  const div = document.createElement('div');
  div.dataset.index = String(displayIdx);

  // Level group header row
  if (entry.type === 'header') {
    div.className = `level-group-header${entry.collapsed ? ' collapsed' : ''}`;
    div.dataset.level = String(entry.level);
    div.setAttribute('style', `position:absolute;top:${top}px;left:0;right:0;height:${VS_ROW_HEIGHT}px;box-sizing:border-box;display:flex;align-items:center`);
    div.innerHTML = `<span class="level-chevron">${entry.collapsed ? '\u25B8' : '\u25BE'}</span>${esc(entry.label)}<span class="level-count">${entry.count}</span>`;
    return div;
  }

  const item = vsFilteredData[entry.dataIdx];
  const meta = getMeta(item);
  let actionHtml = '';
  if (currentTab === 'spells') {
    const p = prepared[item.slug];
    if (p) {
      const allUsed = p.used >= p.prepared;
      actionHtml = `<span class="prep-badge ${allUsed ? 'exhausted' : ''}">${p.used}/${p.prepared}</span>`
        + `<button class="prep-btn prep-btn-active" data-idx="${entry.dataIdx}" title="${t('btn.add_prep')}">+</button>`;
    } else {
      actionHtml = `<button class="prep-btn" data-idx="${entry.dataIdx}" title="${t('btn.prepare_spell')}">+</button>`;
    }
  } else if (currentTab === 'feats') {
    const isLearned = !!learned[item.slug];
    actionHtml = `<button class="learn-btn ${isLearned ? 'learn-btn-active' : ''}" data-idx="${entry.dataIdx}" title="${isLearned ? t('btn.unlearn_feat') : t('btn.learn_feat')}">\u2713</button>`;
  }
  const isPrepared = currentTab === 'spells' && prepared[item.slug];
  const isLearned = currentTab === 'feats' && learned[item.slug];
  const schoolStyle = currentTab === 'spells' && item.school ? ` style="--school-clr: ${getSchoolColor(item.school)}"` : '';
  const nameHtml = q ? highlightText(item.name, q) : esc(item.name);
  const enNameHtml = item._name_en ? `<span class="name-en">${q ? highlightText(item._name_en, q) : esc(item._name_en)}</span>` : '';
  div.className = `result-item ${isPrepared ? 'is-prepared' : ''} ${isLearned ? 'is-learned' : ''}`.trim();
  div.dataset.dataIdx = entry.dataIdx;
  div.dataset.slug = item.slug || '';
  div.setAttribute('style', `position:absolute;top:${top}px;left:0;right:0;height:${VS_ROW_HEIGHT}px;box-sizing:border-box${schoolStyle ? ';--school-clr:' + getSchoolColor(item.school) : ''}`);
  div.innerHTML = `<div class="result-row">
    <div class="result-text">
      <div class="name">${nameHtml}${renderSourceBadge(item)}${enNameHtml}</div>
      ${meta ? `<div class="meta">${esc(meta)}</div>` : ''}
    </div>
    ${actionHtml}
  </div>`;
  return div;
}

function vsRenderVisible() {
  if (!vsDisplayMap.length) return;

  const scrollTop = resultsList.scrollTop;
  const viewportHeight = resultsList.clientHeight;

  let start = Math.floor(scrollTop / VS_ROW_HEIGHT) - VS_BUFFER;
  let end = Math.ceil((scrollTop + viewportHeight) / VS_ROW_HEIGHT) + VS_BUFFER;
  start = Math.max(0, start);
  end = Math.min(vsDisplayMap.length, end);

  // Skip if range hasn't changed
  if (vsLastRange && vsLastRange.start === start && vsLastRange.end === end) return;

  const oldStart = vsLastRange ? vsLastRange.start : -1;
  const oldEnd = vsLastRange ? vsLastRange.end : -1;
  vsLastRange = { start, end };

  const spacer = resultsList._vsSpacer;

  // Full rebuild on first render or large jumps (>50% of items changed)
  const overlap = Math.max(0, Math.min(oldEnd, end) - Math.max(oldStart, start));
  const oldCount = oldEnd - oldStart;
  const fullRebuild = oldStart < 0 || overlap < oldCount * 0.5;

  const prepared = currentTab === 'spells' ? loadPrepared() : {};
  const learned = currentTab === 'feats' ? loadLearned() : {};
  const q = resultsList._searchQuery || '';

  if (fullRebuild) {
    const frag = document.createDocumentFragment();
    for (let idx = start; idx < end; idx++) {
      frag.appendChild(vsCreateRow(idx, prepared, learned, q));
    }
    spacer.textContent = '';
    spacer.appendChild(frag);
    return;
  }

  // Incremental update: remove out-of-range nodes, add new ones
  const existing = spacer.children;
  // Remove nodes outside new range (iterate backwards to avoid index shifts)
  for (let i = existing.length - 1; i >= 0; i--) {
    const nodeIdx = parseInt(existing[i].dataset.index);
    if (nodeIdx < start || nodeIdx >= end) {
      existing[i].remove();
    }
  }

  // Build set of currently rendered indices
  const rendered = new Set();
  for (const child of spacer.children) {
    rendered.add(parseInt(child.dataset.index));
  }

  // Add missing rows
  const frag = document.createDocumentFragment();
  for (let idx = start; idx < end; idx++) {
    if (!rendered.has(idx)) {
      frag.appendChild(vsCreateRow(idx, prepared, learned, q));
    }
  }
  if (frag.childNodes.length) {
    spacer.appendChild(frag);
  }
}

// ── Event delegation for virtual scroll items ──
function vsHandleClick(e) {
  // Level group header click → toggle collapse
  const header = e.target.closest('.level-group-header');
  if (header && header.dataset.level !== undefined) {
    const level = parseInt(header.dataset.level);
    if (vsCollapsedLevels.has(level)) {
      vsCollapsedLevels.delete(level);
    } else {
      vsCollapsedLevels.add(level);
    }
    vsRebuildDisplayMap();
    return;
  }

  const prepBtn = e.target.closest('.prep-btn');
  if (prepBtn) {
    e.stopPropagation();
    const item = vsFilteredData[parseInt(prepBtn.dataset.idx)];
    if (item) { addPrepared(item); renderResults(); }
    return;
  }
  const learnBtn = e.target.closest('.learn-btn');
  if (learnBtn) {
    e.stopPropagation();
    const item = vsFilteredData[parseInt(learnBtn.dataset.idx)];
    if (item) { toggleLearned(item); renderResults(); }
    return;
  }
  const row = e.target.closest('.result-item');
  if (row) {
    resultsList.querySelectorAll('.selected').forEach((s) => s.classList.remove('selected'));
    row.classList.add('selected');
    const item = vsFilteredData[parseInt(row.dataset.dataIdx)];
    if (item) showDetail(item);
  }
}

// ── Prepared spells tab ──────────────────────────────────────────────────

async function renderPreparedList() {
  const prepared = loadPrepared();
  let entries = Object.values(prepared);

  // Resolve names, school, level in current language
  const spells = await loadData('spells');
  const spellMap = {};
  if (spells) spells.forEach((s) => { spellMap[s.slug] = s; });
  // Remove stale entries that no longer match any spell (renamed slugs, etc.)
  let cleaned = false;
  const keys = Object.keys(prepared);
  for (let i = keys.length - 1; i >= 0; i--) {
    const key = keys[i];
    const slug = prepared[key].slug || key;
    if (!spellMap[slug] || !prepared[key].prepared) {
      delete prepared[key];
      cleaned = true;
    }
  }
  if (cleaned) {
    savePrepared(prepared);
    entries = Object.values(prepared);
  }

  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = t('msg.prepared_count', { count: entries.length });

  if (entries.length === 0) {
    resultsList.innerHTML = `<div class="no-results">${t('msg.no_prepared')}</div>`;
    detailPanel.classList.add('hidden');
    return;
  }

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

  // Event: click on prep-info area to show spell detail
  resultsList.querySelectorAll('.prep-info').forEach((el) => {
    el.addEventListener('click', async () => {
      const slug = el.closest('[data-slug]').dataset.slug;
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
    case 'skills':
      if (item.category === 'skill_trick') return 'Skill Trick';
      return [item.key_ability, item.trained_only ? '(trained)' : ''].filter(Boolean).join(' ');
    case 'classes': {
      const parts = [];
      if (item.is_prestige === 'True' || item.is_prestige === true) parts.push(t('detail.class.prestige'));
      if (item.hit_die) parts.push(item.hit_die);
      return parts.join(' — ');
    }
    case 'races':
      return item.size || '';
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
  detailPanel.dataset.activeSlug = item.slug || '';
  detailPanel.innerHTML = `<button class="detail-close" aria-label="Chiudi">&times;</button>` + renderDetail(item, tab);
  detailPanel.querySelector('.detail-close').addEventListener('click', () => {
    detailPanel.classList.add('hidden');
  });
  if (window.innerWidth <= 768) {
    // On mobile, use setTimeout to ensure layout is complete before scrolling
    setTimeout(() => {
      const y = detailPanel.getBoundingClientRect().top + window.pageYOffset - 10;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }, 50);
  }
}

function renderDetail(item, tab) {
  switch (tab || currentTab) {
    case 'spells': return renderSpell(item);
    case 'feats': return renderFeat(item);
    case 'skills': return renderSkill(item);
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
  let html = renderDetailTitle(s) + renderFields(fields);
  // Show summary if no full description
  if (!s.desc_html && s.summary_it) {
    html += `<div class="desc-html"><p><em>${esc(s.summary_it)}</em></p></div>`;
  } else {
    html += renderDesc(s.desc_html);
  }
  html += renderSourceFooter(s);
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
  if (f.required_for && f.required_for.length) {
    fields.push([t('detail.feat.required_for'), f.required_for.join(', ')]);
  }
  let html = renderDetailTitle(f) + renderFields(fields);
  // Only show desc_html if structured fields are absent (avoids duplication)
  if (!f.benefit && f.desc_html) html += renderDesc(f.desc_html);
  html += renderSourceFooter(f);
  return html;
}

function renderSkill(s) {
  if (s.category === 'skill_trick') {
    let html = renderDetailTitle(s) + renderDesc(s.desc_html);
    html += renderSourceFooter(s);
    return html;
  }
  // Regular skill
  const fields = [
    [t('detail.skill.key_ability'), s.key_ability],
    [t('detail.skill.trained_only'), s.trained_only ? 'Yes' : 'No'],
    [t('detail.skill.armor_check_penalty'), s.armor_check_penalty ? 'Yes' : 'No'],
  ];
  let html = renderDetailTitle(s) + renderFields(fields);
  // Skill sections
  const sections = [
    ['check', t('detail.skill.check')],
    ['action', t('detail.skill.action')],
    ['try_again', t('detail.skill.try_again')],
    ['special', t('detail.skill.special')],
    ['synergy', t('detail.skill.synergy')],
    ['restriction', t('detail.skill.restriction')],
    ['untrained', t('detail.skill.untrained')],
  ];
  for (const [key, label] of sections) {
    if (s[key]) {
      html += `<div class="desc-html"><h4>${esc(label)}</h4>${s[key]}</div>`;
    }
  }
  if (s.desc_html) html += renderDesc(s.desc_html);
  html += renderSourceFooter(s);
  return html;
}

function renderClass(c) {
  const fields = [
    [t('detail.class.hit_die'), c.hit_die],
    [t('detail.class.alignment'), c.alignment],
  ];
  if (c.is_prestige === 'True' || c.is_prestige === true) {
    fields.unshift([t('filter.all_types'), t('detail.class.prestige')]);
  }
  if (c.skill_points) fields.push([t('detail.class.skill_points'), c.skill_points]);
  if (c.class_skills) {
    const skills = Array.isArray(c.class_skills) ? c.class_skills.join(', ') : c.class_skills;
    fields.push([t('detail.class.class_skills'), skills]);
  }
  let html = renderDetailTitle(c) + renderFields(fields);
  if (c.table_html) {
    html += `<div class="desc-html">${c.table_html}</div>`;
  }
  html += renderDesc(c.desc_html);
  html += renderSourceFooter(c);
  return html;
}

function renderRace(r) {
  const fields = [];
  if (r.size) fields.push([t('detail.race.size'), r.size]);
  if (r.speed) fields.push([t('detail.race.speed'), r.speed]);
  if (r.ability_adjustments) fields.push([t('detail.race.ability_adj'), r.ability_adjustments]);
  if (r.level_adjustment) fields.push([t('detail.race.level_adj'), r.level_adjustment]);
  let html = renderDetailTitle(r) + renderFields(fields);
  if (r.traits && r.traits.length) {
    html += '<div class="desc-html"><ul>';
    html += r.traits.map((tr) => `<li>${tr}</li>`).join('');
    html += '</ul></div>';
  }
  html += renderDesc(r.desc_html);
  html += renderSourceFooter(r);
  return html;
}

function renderEquipment(e) {
  let html = renderDetailTitle(e);
  const cat = e._category || e.category || '';
  const catLabel = cat === 'weapon' ? t('cat.weapon') : cat === 'armor' ? t('cat.armor') : cat === 'goods' ? t('cat.goods') : cat;
  html += `<div class="field"><span class="field-label">${t('detail.equip.category')}</span><div class="field-value">${esc(catLabel)}</div></div>`;

  const skip = new Set(['name', 'slug', '_category', 'category', 'desc_html', 'source']);
  const entries = Object.entries(e).filter(([k]) => !skip.has(k) && !k.startsWith('_'));
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
  let html = renderDetailTitle(m) + renderFields(fields) + renderDesc(m.desc_html);
  html += renderSourceFooter(m);
  return html;
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

function resolveSourceAbbr(item) {
  // Returns { key, label } for the source book abbreviation
  if (!item.source) return null;
  // Direct lookup by source key (e.g. "SRD", "PHB")
  if (item.source !== 'dndtools' && sourcesData && sourcesData[item.source]) {
    const lang = getCurrentLang();
    const src = sourcesData[item.source];
    return { key: item.source, label: src['abbreviation_' + lang] || src.abbreviation || item.source };
  }
  // Reverse lookup via source_book name for dndtools items
  if (item.source_book && sourceBookMap) {
    const norm = item.source_book.toLowerCase();
    let key = sourceBookMap[norm];
    // Try stripping common suffixes: " v.3.5", " v3.5", " 3.0", subtitle after ":"
    if (!key) {
      const stripped = norm.replace(/\s+v\.?3\.[05]$/,'').replace(/:\s.*$/,'').trim();
      key = sourceBookMap[stripped];
    }
    if (key && sourcesData[key]) {
      const lang = getCurrentLang();
      const src = sourcesData[key];
      return { key, label: src['abbreviation_' + lang] || src.abbreviation || key };
    }
    // Fallback: generate initials from source_book
    const initials = item.source_book.split(/[\s-]+/)
      .map(w => w[0]).filter(c => c && c === c.toUpperCase()).join('');
    return { key: initials, label: initials };
  }
  return { key: item.source, label: item.source };
}

function renderSourceBadge(item) {
  const info = resolveSourceAbbr(item);
  if (!info) return '';
  let html = `<span class="source-badge">${esc(info.label)}</span>`;
  if (item.edition) {
    const editions = item.edition.split(',').map(e => e.trim());
    for (const ed of editions) {
      html += `<span class="edition-badge edition-${ed === '3.0' ? '30' : '35'}">${esc(ed)}</span>`;
    }
  }
  return html;
}

function renderSourceFooter(item) {
  // Collect per-language references
  // EN ref: _base_manual_name (preserved by overlay) or source_book or manual_name (when no overlay)
  const lang = getCurrentLang();
  const refs = [];

  // _base_manual_name semantics (set by applyOverlay):
  //   undefined → overlay did NOT provide manual_name → item.manual_name is from base data (EN)
  //   "" (empty) → overlay DID provide manual_name, base had none → item.manual_name is IT
  //   "Book Name" → overlay REPLACED manual_name → _base_ is EN, item.manual_name is IT
  const hasOverlayManual = '_base_manual_name' in item;
  const hasOverlayRef = '_base_reference' in item;

  // EN reference: prefer preserved base value, fallback to source_book, then manual_name if no overlay
  const enBook = (hasOverlayManual ? item._base_manual_name : '') || item.source_book || (!hasOverlayManual ? item.manual_name : '') || '';
  const enPage = (hasOverlayRef ? item._base_reference : '') || (item.source_page ? `p. ${item.source_page}` : '') || (!hasOverlayRef ? item.reference : '') || '';
  if (enBook) refs.push({ lang: 'EN', book: enBook, page: enPage });

  // IT reference: only when overlay provided manual_name (_base_ key exists)
  if (lang !== 'en' && hasOverlayManual) {
    const itBook = item.manual_name || '';
    const itPage = hasOverlayRef ? (item.reference || '') : '';
    if (itBook) refs.push({ lang: 'IT', book: itBook, page: itPage });
  }

  // If no overlay was applied (no _base), translate book name via sources.json
  if (refs.length === 1 && refs[0].lang === 'EN' && lang !== 'en') {
    let itName = '';
    // First try reverse lookup by source_book name (most specific, e.g. "Monster Manual v.3.5" → MM)
    if (enBook && sourceBookMap) {
      const norm = enBook.toLowerCase();
      let key = sourceBookMap[norm];
      if (!key) {
        const stripped = norm.replace(/\s+v\.?3\.[05]$/,'').replace(/:\s.*$/,'').trim();
        key = sourceBookMap[stripped];
      }
      if (key && sourcesData && sourcesData[key]) {
        itName = sourcesData[key].name_it || '';
      }
    }
    // Fallback to source abbreviation key (e.g. "SRD" → sources["SRD"].name_it)
    if (!itName) {
      const info = resolveSourceAbbr(item);
      if (info && sourcesData && sourcesData[info.key]) {
        itName = sourcesData[info.key].name_it || '';
      }
    }
    if (itName && itName !== enBook) {
      refs.push({ lang: 'IT', book: itName, page: '' });
    }
  }

  if (refs.length === 0) return '';

  let html = '<div class="source-footer">';
  for (const ref of refs) {
    const parts = [ref.book];
    if (ref.page) parts.push(ref.page);
    html += `<div class="source-footer-line"><span class="source-footer-lang">${ref.lang}</span> ${esc(parts.join(', '))}</div>`;
  }
  if (item.source_site) {
    html += `<div class="source-footer-site">(${esc(item.source_site)})</div>`;
  }
  html += '</div>';
  return html;
}

async function loadSources() {
  try {
    const res = await fetch(`${DATA_BASE}/sources.json`);
    if (res.ok) {
      sourcesData = await res.json();
      // Build reverse map: normalised source_book name → abbreviation key
      sourceBookMap = {};
      for (const [key, val] of Object.entries(sourcesData)) {
        const n = (val.name_en || '').toLowerCase();
        if (n) sourceBookMap[n] = key;
      }
    }
  } catch {}
}

// ── Translation status dashboard ────────────────────────────────────────

async function renderTranslationStatus(selectedLang) {
  detailPanel.classList.add('hidden');
  resultsList.innerHTML = `<div class="loading">${t('msg.loading')}</div>`;

  try {
    // Fetch index to discover available languages (cache-bust)
    const cb = `v=${Date.now()}`;
    const indexRes = await fetch(`${DATA_BASE}/translation-status-index.json?${cb}`);
    let langs = [];
    if (indexRes.ok) {
      const index = await indexRes.json();
      langs = index.languages || [];
    }

    // Determine which language to show
    const lang = selectedLang || (langs.includes(getCurrentLang()) ? getCurrentLang() : langs[0]) || 'it';

    // Fetch per-language status (cache-bust)
    const statusUrl = langs.length > 0
      ? `${DATA_BASE}/translation-status-${lang}.json?${cb}`
      : `${DATA_BASE}/translation-status.json?${cb}`;
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

    // ── Per-source breakdown ──
    if (cat.by_source) {
      const srcEntries = Object.entries(cat.by_source).sort((a, b) => b[1].total - a[1].total);
      html += `<div class="status-by-source">`;
      const bySourceLabel = (() => { const v = t('status.by_source'); return v && !v.includes('.') ? v : 'Per manuale'; })();
      html += `<h4 class="source-breakdown-title" onclick="this.nextElementSibling.classList.toggle('open')">${bySourceLabel} <span class="toggle-arrow">▸</span></h4>`;
      html += `<div class="source-breakdown-body">`;
      for (const [srcName, srcData] of srcEntries) {
        const sPct = srcData.percent;
        const sFillClass = sPct >= 100 ? 'complete' : '';
        const srcId = `src-${catName}-${srcName}`.replace(/[^a-z0-9-]/gi, '-');
        const hasEntries = srcData.entries && srcData.entries.length > 0;
        const nDesc = hasEntries ? srcData.entries.filter(e => e.desc).length : 0;
        const nNoDesc = hasEntries ? srcData.entries.length - nDesc : 0;
        html += `<div class="source-row${hasEntries ? ' clickable' : ''}"${hasEntries ? ` onclick="document.getElementById('${srcId}').classList.toggle('open')"` : ''}>`;
        html += `<span class="source-name">${esc(srcName)}</span>`;
        html += `<span class="source-count">${srcData.total}</span>`;
        html += `<div class="field-bar"><div class="field-bar-fill ${sFillClass}" style="width:${sPct}%"></div></div>`;
        html += `<span class="field-stats">${srcData.translated_fields}/${srcData.total_fields} (${sPct}%)`;
        if (hasEntries) html += ` <span class="source-desc-badge" title="desc_html">📖 ${nDesc}/${srcData.total}</span>`;
        html += `</span>`;
        html += `</div>`;
        // Expandable spell list
        if (hasEntries) {
          html += `<div class="source-spell-list" id="${srcId}">`;
          for (const entry of srcData.entries) {
            const name = entry.it || entry.en;
            const descClass = entry.desc ? 'has-desc' : 'no-desc';
            html += `<div class="source-spell-entry ${descClass}">`;
            html += `<span class="desc-dot" title="${entry.desc ? 'desc_html ✓' : 'desc_html ✗'}"></span>`;
            html += `<span class="spell-entry-name">${esc(name)}</span>`;
            if (entry.it && entry.en) html += `<span class="spell-entry-en">${esc(entry.en)}</span>`;
            html += `</div>`;
          }
          html += `</div>`;
        }
      }
      html += `</div></div>`;
    }

    // ── CSV export button ──
    html += `<div class="status-export">`;
    html += `<button class="export-csv-btn" data-cat="${esc(catName)}" title="Esporta CSV mancanti">`;
    html += `📥 CSV`;
    html += `</button>`;
    html += `</div>`;

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

  // CSV export buttons
  resultsList.querySelectorAll('.export-csv-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      exportStatusCSV(btn.dataset.cat, data);
    });
  });
}

// ── CSV export for translation status ──────────────────────────────────

async function exportStatusCSV(catName, statusData) {
  const FIELDS_MAP = {
    spells: ['name','school','subschool','descriptor','level','components',
             'casting_time','range','target_area_effect','duration',
             'saving_throw','spell_resistance','short_description','desc_html'],
    feats: ['name','type','prerequisites','benefit','normal','special','desc_html'],
    monsters: ['name','type','alignment','environment','organization','desc_html'],
    classes: ['name','alignment','table_html','desc_html'],
    races: ['name','traits','desc_html'],
    equipment: ['name'],
    rules: ['name','desc_html'],
  };

  try {
    const cb = `v=${Date.now()}`;
    const [enRes, itRes] = await Promise.all([
      fetch(`${DATA_BASE}/${catName}.json?${cb}`),
      fetch(`${DATA_BASE}/i18n/it/${catName}.json?${cb}`),
    ]);
    if (!enRes.ok) throw new Error(`Cannot load ${catName}.json`);
    const enData = await enRes.json();
    const itData = itRes.ok ? await itRes.json() : [];

    const itMap = {};
    for (const e of itData) { if (e.slug) itMap[e.slug] = e; }

    const fields = FIELDS_MAP[catName] || ['name','desc_html'];
    const header = ['slug','name_en','name_it','source', ...fields.map(f => f + '_status')];
    const rows = [header.join(',')];

    for (const en of enData) {
      const slug = en.slug || '';
      const it = itMap[slug] || {};
      const nameEn = (en.name || '').replace(/"/g, '""');
      const nameIt = (it.name || '').replace(/"/g, '""');
      const source = (en.source || '').replace(/"/g, '""');

      const statuses = fields.map(f => {
        const enVal = en[f] || '';
        const itVal = it[f] || '';
        if (!enVal && !itVal) return 'manca';
        if (!itVal && enVal) return 'manca';
        if (itVal && enVal && itVal === enVal) return 'uguale_EN';
        if (itVal) return 'ok';
        return 'manca';
      });

      rows.push([
        `"${slug}"`,`"${nameEn}"`,`"${nameIt}"`,`"${source}"`,
        ...statuses
      ].join(','));
    }

    const csv = rows.join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `translation-missing-${catName}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('CSV export error:', err);
    alert('Errore export CSV: ' + err.message);
  }
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
  const q = (isFullTextSearch() && searchInput) ? searchInput.value.trim() : '';
  const highlighted = q ? highlightHtml(html, q) : html;
  return `<div class="desc-html">${highlighted}</div>`;
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

// ── Full-text search toggle ──────────────────────────────────────────────

function initFullTextToggle() {
  const cb = document.getElementById('search-fulltext');
  const label = document.getElementById('fulltext-text');
  if (!cb) return;
  // Restore preference
  cb.checked = localStorage.getItem('crystalball_fulltext') === '1';
  if (label) label.textContent = t('search.fulltext');
  cb.addEventListener('change', () => {
    localStorage.setItem('crystalball_fulltext', cb.checked ? '1' : '0');
    if (searchInput.value.trim()) renderResults();
  });
}

// ── Init ─────────────────────────────────────────────────────────────────

async function initApp() {
  await loadI18n();
  await loadSources();
  updateTabLabels();
  searchInput.placeholder = t('search.placeholder');
  initLangSwitcher();
  initHeaderToggle();
  initFullTextToggle();
  buildFilters();
  renderResults();
  updateContentHeight();
  window.addEventListener('resize', updateContentHeight);
}

initApp();

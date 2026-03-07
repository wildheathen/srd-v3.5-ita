/* Crystal Ball — i18n module */

const I18N_LANG_KEY = 'crystalball_lang';
const DEFAULT_LANG = 'it';
const SUPPORTED_LANGS = ['it', 'en'];

let currentLang = DEFAULT_LANG;
let uiStrings = {};
let dataOverlayCache = {};

function getSavedLang() {
  try {
    const saved = localStorage.getItem(I18N_LANG_KEY);
    if (saved && SUPPORTED_LANGS.includes(saved)) return saved;
  } catch {}
  return DEFAULT_LANG;
}

function getCurrentLang() { return currentLang; }

async function loadI18n(lang) {
  lang = lang || getSavedLang();
  currentLang = lang;
  try {
    localStorage.setItem(I18N_LANG_KEY, lang);
  } catch {}
  try {
    const res = await fetch(`frontend/i18n/${lang}.json`);
    if (res.ok) uiStrings = await res.json();
  } catch (err) {
    console.warn(`i18n: failed to load ${lang}.json`, err);
  }
}

function t(key, replacements) {
  let str = uiStrings[key] || key;
  if (replacements) {
    for (const [k, v] of Object.entries(replacements)) {
      str = str.replace('${' + k + '}', v);
    }
  }
  return str;
}

async function loadDataOverlay(category) {
  if (currentLang === 'en') return null; // English is the base data language
  const cacheKey = `${currentLang}/${category}`;
  if (dataOverlayCache[cacheKey] !== undefined) return dataOverlayCache[cacheKey];
  try {
    const res = await fetch(`data/i18n/${currentLang}/${category}.json`);
    if (!res.ok) { dataOverlayCache[cacheKey] = null; return null; }
    const overlay = await res.json();
    // Index by slug for fast lookup
    const map = {};
    overlay.forEach((item) => { if (item.slug) map[item.slug] = item; });
    dataOverlayCache[cacheKey] = map;
    return map;
  } catch {
    dataOverlayCache[cacheKey] = null;
    return null;
  }
}

// Fields whose original EN value must be preserved when overlay replaces them
const _PRESERVE_BASE_FIELDS = ['manual_name', 'reference'];

function applyOverlay(data, overlayMap) {
  if (!overlayMap) return data;
  return data.map((item) => {
    const trans = overlayMap[item.slug];
    if (!trans) return item;
    // Preserve original EN values that will be overwritten by overlay
    const merged = { ...item };
    for (const f of _PRESERVE_BASE_FIELDS) {
      if (trans[f] && item[f]) {
        merged['_base_' + f] = item[f];       // EN original
      }
    }
    Object.assign(merged, trans);
    merged.slug = item.slug;
    // Preserve original EN name for cross-reference display
    if (trans.name && trans.name !== item.name) {
      merged._name_en = item.name;
    }
    return merged;
  });
}

function clearDataOverlayCache() {
  dataOverlayCache = {};
}

function setLang(lang) {
  if (!SUPPORTED_LANGS.includes(lang)) return;
  currentLang = lang;
  try { localStorage.setItem(I18N_LANG_KEY, lang); } catch {}
  clearDataOverlayCache();
}

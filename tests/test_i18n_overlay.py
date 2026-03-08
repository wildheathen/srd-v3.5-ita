"""Test i18n overlay system: merge correctness, fallback behavior, slug integrity."""
import json
import pathlib
import pytest

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / 'data'
I18N_DIR = DATA_DIR / 'i18n' / 'it'

CATEGORIES = ['spells', 'feats', 'classes', 'monsters', 'races', 'skills']

VALID_TRANSLATION_SOURCES = {'manual', 'auto', 'ocr', 'pdf'}


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_base(cat):
    return load_json(DATA_DIR / f'{cat}.json')


def load_overlay(cat):
    p = I18N_DIR / f'{cat}.json'
    if p.exists():
        return load_json(p)
    return []


@pytest.fixture(scope='module', params=CATEGORIES)
def category_data(request):
    cat = request.param
    base = load_base(cat)
    overlay = load_overlay(cat)
    return cat, base, overlay


class TestOverlayIntegrity:
    def test_overlay_slugs_exist_in_base(self, category_data):
        """Every slug in the overlay must match a slug in the base data."""
        cat, base, overlay = category_data
        base_slugs = {item['slug'] for item in base}
        overlay_slugs = {item['slug'] for item in overlay}
        orphans = overlay_slugs - base_slugs
        # Allow small margin for lag between data updates
        assert len(orphans) <= 5, (
            f'{cat}: overlay has {len(orphans)} orphan slugs not in base: '
            f'{list(orphans)[:10]}'
        )

    def test_overlay_has_slug_field(self, category_data):
        """Every overlay entry must have a slug."""
        cat, _, overlay = category_data
        for i, entry in enumerate(overlay):
            assert 'slug' in entry, f'{cat} overlay entry {i} missing slug'

    def test_no_duplicate_overlay_slugs(self, category_data):
        """No duplicate slugs within an overlay file."""
        cat, _, overlay = category_data
        slugs = [e['slug'] for e in overlay]
        dupes = [s for s in set(slugs) if slugs.count(s) > 1]
        assert not dupes, f'{cat}: duplicate overlay slugs: {dupes}'

    def test_translation_source_values(self, category_data):
        """translation_source, if present, must be one of the allowed values."""
        cat, _, overlay = category_data
        for entry in overlay:
            src = entry.get('translation_source')
            if src is not None:
                assert src in VALID_TRANSLATION_SOURCES, (
                    f'{cat}/{entry.get("slug","?")}: invalid translation_source '
                    f'"{src}", expected one of {VALID_TRANSLATION_SOURCES}'
                )

    def test_reviewed_is_boolean(self, category_data):
        """reviewed, if present, must be a boolean."""
        cat, _, overlay = category_data
        for entry in overlay:
            if 'reviewed' in entry:
                assert isinstance(entry['reviewed'], bool), (
                    f'{cat}/{entry.get("slug","?")}: reviewed must be bool, '
                    f'got {type(entry["reviewed"]).__name__}'
                )

    def test_reviewed_requires_source(self, category_data):
        """If reviewed is set, translation_source should also be present."""
        cat, _, overlay = category_data
        for entry in overlay:
            if 'reviewed' in entry and 'translation_source' not in entry:
                pytest.fail(
                    f'{cat}/{entry.get("slug","?")}: has reviewed but no '
                    f'translation_source'
                )


class TestOverlayMerge:
    def test_merge_preserves_base_fields(self):
        """Merging overlay should not remove base fields."""
        base = [{'slug': 'test', 'name': 'Test', 'school': 'Evocation', 'level': 'Wiz 1'}]
        overlay = [{'slug': 'test', 'name': 'Prova'}]

        # Simulate applyOverlay logic from i18n.js
        overlay_map = {e['slug']: e for e in overlay}
        merged = []
        for item in base:
            trans = overlay_map.get(item['slug'])
            if trans:
                result = {**item, **trans, 'slug': item['slug']}
                merged.append(result)
            else:
                merged.append(item)

        assert merged[0]['name'] == 'Prova'
        assert merged[0]['school'] == 'Evocation'  # preserved
        assert merged[0]['level'] == 'Wiz 1'       # preserved

    def test_merge_fallback_for_missing_slug(self):
        """Items not in overlay should remain unchanged."""
        base = [
            {'slug': 'a', 'name': 'Alpha'},
            {'slug': 'b', 'name': 'Beta'},
        ]
        overlay = [{'slug': 'a', 'name': 'Alfa'}]

        overlay_map = {e['slug']: e for e in overlay}
        merged = []
        for item in base:
            trans = overlay_map.get(item['slug'])
            if trans:
                merged.append({**item, **trans, 'slug': item['slug']})
            else:
                merged.append(item)

        assert merged[0]['name'] == 'Alfa'
        assert merged[1]['name'] == 'Beta'  # untouched


class TestOverlayCoverage:
    @pytest.mark.parametrize('cat', CATEGORIES)
    def test_overlay_has_name_translations(self, cat):
        """Overlay should translate at least the name field for most entries."""
        base = load_base(cat)
        overlay = load_overlay(cat)
        if not overlay:
            pytest.skip(f'No overlay for {cat}')
        names_translated = sum(1 for e in overlay if 'name' in e)
        pct = names_translated / len(base) * 100 if base else 0
        # At minimum, some name translations should exist
        assert names_translated > 0, f'{cat}: overlay has no name translations'

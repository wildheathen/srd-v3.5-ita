"""Validate JSON data files: required fields, no duplicates, no empty names."""
import json
import pathlib
import pytest

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / 'data'


def load_json(name):
    with open(DATA_DIR / f'{name}.json', encoding='utf-8') as f:
        return json.load(f)


# ── Spell schema ─────────────────────────────────────────────────────────

class TestSpells:
    @pytest.fixture(scope='class')
    def spells(self):
        return load_json('spells')

    def test_has_entries(self, spells):
        assert len(spells) > 1000, f'Expected 1000+ spells, got {len(spells)}'

    def test_required_fields(self, spells):
        required = {'name', 'slug', 'school', 'level'}
        for s in spells:
            missing = required - set(s.keys())
            assert not missing, f'Spell {s.get("name","?")} missing fields: {missing}'

    def test_no_empty_names(self, spells):
        for s in spells:
            assert s['name'].strip(), f'Empty name for slug {s.get("slug","?")}'

    def test_no_duplicate_slugs(self, spells):
        slugs = [s['slug'] for s in spells]
        dupes = [s for s in set(slugs) if slugs.count(s) > 1]
        assert not dupes, f'Duplicate spell slugs: {dupes}'

    def test_school_not_empty(self, spells):
        for s in spells:
            assert s.get('school'), f'Empty school for {s["name"]}'

    def test_short_description_coverage(self, spells):
        has_short = sum(1 for s in spells if s.get('short_description'))
        assert has_short > 3000, f'Expected 3000+ spells with short_description, got {has_short}'

    def test_no_known_typos(self, spells):
        typos = {'Brillant Aura', 'Curse of Licanthropy', 'Energy Votex',
                 'Spell Resistence, Mass', 'Summon Greather Elemental',
                 'Insigna of Blessing'}
        names = {s['name'] for s in spells}
        found = typos & names
        assert not found, f'Known typos still present: {found}'


# ── Feat schema ──────────────────────────────────────────────────────────

class TestFeats:
    @pytest.fixture(scope='class')
    def feats(self):
        return load_json('feats')

    def test_has_entries(self, feats):
        assert len(feats) > 100, f'Expected 100+ feats, got {len(feats)}'

    def test_required_fields(self, feats):
        required = {'name', 'slug'}
        for f in feats:
            missing = required - set(f.keys())
            assert not missing, f'Feat {f.get("name","?")} missing fields: {missing}'

    def test_no_empty_names(self, feats):
        for f in feats:
            assert f['name'].strip(), f'Empty name for slug {f.get("slug","?")}'

    def test_no_duplicate_slugs(self, feats):
        slugs = [f['slug'] for f in feats]
        dupes = [s for s in set(slugs) if slugs.count(s) > 1]
        assert not dupes, f'Duplicate feat slugs: {dupes}'


# ── Class schema ─────────────────────────────────────────────────────────

class TestClasses:
    @pytest.fixture(scope='class')
    def classes(self):
        return load_json('classes')

    def test_has_entries(self, classes):
        assert len(classes) > 500, f'Expected 500+ classes, got {len(classes)}'

    def test_required_fields(self, classes):
        required = {'name', 'slug'}
        for c in classes:
            missing = required - set(c.keys())
            assert not missing, f'Class {c.get("name","?")} missing fields: {missing}'

    def test_no_duplicate_slugs(self, classes):
        slugs = [c['slug'] for c in classes]
        dupes = [s for s in set(slugs) if slugs.count(s) > 1]
        assert not dupes, f'Duplicate class slugs: {dupes}'


# ── Monster schema ───────────────────────────────────────────────────────

class TestMonsters:
    @pytest.fixture(scope='class')
    def monsters(self):
        return load_json('monsters')

    def test_has_entries(self, monsters):
        assert len(monsters) > 1000, f'Expected 1000+ monsters, got {len(monsters)}'

    def test_required_fields(self, monsters):
        required = {'name', 'slug'}
        for m in monsters:
            missing = required - set(m.keys())
            assert not missing, f'Monster {m.get("name","?")} missing: {missing}'

    def test_no_duplicate_slugs(self, monsters):
        slugs = [m['slug'] for m in monsters]
        dupes = [s for s in set(slugs) if slugs.count(s) > 1]
        assert not dupes, f'Duplicate monster slugs: {dupes}'


# ── Equipment schema ─────────────────────────────────────────────────────

class TestEquipment:
    @pytest.fixture(scope='class')
    def equipment(self):
        return load_json('equipment')

    def test_has_entries(self, equipment):
        assert len(equipment) > 100, f'Expected 100+ equipment, got {len(equipment)}'

    def test_required_fields(self, equipment):
        required = {'name', 'slug'}
        for e in equipment:
            missing = required - set(e.keys())
            assert not missing, f'Equipment {e.get("name","?")} missing: {missing}'


# ── Race schema ──────────────────────────────────────────────────────────

class TestRaces:
    @pytest.fixture(scope='class')
    def races(self):
        return load_json('races')

    def test_has_entries(self, races):
        assert len(races) >= 7, f'Expected 7+ races, got {len(races)}'

    def test_required_fields(self, races):
        required = {'name', 'slug'}
        for r in races:
            missing = required - set(r.keys())
            assert not missing, f'Race {r.get("name","?")} missing: {missing}'


# ── Skills schema ────────────────────────────────────────────────────────

class TestSkills:
    @pytest.fixture(scope='class')
    def skills(self):
        return load_json('skills')

    def test_has_entries(self, skills):
        assert len(skills) > 50, f'Expected 50+ skills, got {len(skills)}'

    def test_required_fields(self, skills):
        required = {'name', 'slug'}
        for s in skills:
            missing = required - set(s.keys())
            assert not missing, f'Skill {s.get("name","?")} missing: {missing}'


# ── Sources schema ──────────────────────────────────────────────────────

class TestSources:
    @pytest.fixture(scope='class')
    def sources(self):
        with open(DATA_DIR / 'sources.json', encoding='utf-8') as f:
            return json.load(f)

    def test_has_entries(self, sources):
        assert len(sources) > 100, f'Expected 100+ sources, got {len(sources)}'

    def test_required_fields(self, sources):
        for key, val in sources.items():
            assert val.get('name_en'), f'Source {key} missing name_en'
            assert val.get('abbreviation'), f'Source {key} missing abbreviation'

    def test_no_duplicate_abbreviations(self, sources):
        abbrs = [v['abbreviation'] for v in sources.values()]
        dupes = [a for a in set(abbrs) if abbrs.count(a) > 1]
        assert not dupes, f'Duplicate abbreviations: {dupes}'

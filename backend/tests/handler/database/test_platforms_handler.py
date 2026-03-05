"""
Unit tests for DBPlatformsHandler.

Covers CRUD, lookup by slug, mark_missing, and rom_count calculation.
"""

from handler.database import db_platform_handler, db_rom_handler
from models.platform import Platform
from models.rom import Rom


def _make_platform(name: str, slug: str | None = None) -> Platform:
    s = slug or name.lower().replace(" ", "_")
    return Platform(name=name, slug=s, fs_slug=s)


def _make_rom(platform: Platform, name: str) -> Rom:
    slug = name.lower().replace(" ", "-")
    return Rom(
        platform_id=platform.id,
        name=name,
        slug=slug,
        fs_name=f"{name.replace(' ', '_')}.zip",
        fs_name_no_tags=name.replace(" ", "_"),
        fs_name_no_ext=name.replace(" ", "_"),
        fs_extension="zip",
        fs_path=f"{platform.fs_slug}/roms",
    )


# ---------------------------------------------------------------------------
# Add / Get
# ---------------------------------------------------------------------------


class TestAddAndGetPlatform:
    def test_add_and_get_by_id(self, platform: Platform):
        fetched = db_platform_handler.get_platform(platform.id)
        assert fetched is not None
        assert fetched.id == platform.id
        assert fetched.name == "test_platform"

    def test_get_nonexistent_returns_none(self):
        assert db_platform_handler.get_platform(999999) is None

    def test_add_platform_is_persisted(self):
        new_plat = db_platform_handler.add_platform(
            _make_platform("New Console")
        )
        assert new_plat.id is not None
        fetched = db_platform_handler.get_platform(new_plat.id)
        assert fetched is not None
        assert fetched.name == "New Console"


# ---------------------------------------------------------------------------
# get_platforms
# ---------------------------------------------------------------------------


class TestGetPlatforms:
    def test_returns_all_platforms(self, platform: Platform):
        platforms = db_platform_handler.get_platforms()
        assert any(p.id == platform.id for p in platforms)

    def test_rom_count_is_calculated(self, platform: Platform):
        db_rom_handler.add_rom(_make_rom(platform, "Game One"))
        db_rom_handler.add_rom(_make_rom(platform, "Game Two"))
        platforms = db_platform_handler.get_platforms()
        plat = next(p for p in platforms if p.id == platform.id)
        assert plat.rom_count == 2

    def test_fs_size_bytes_is_calculated(self, platform: Platform):
        platforms = db_platform_handler.get_platforms()
        plat = next(p for p in platforms if p.id == platform.id)
        assert plat.fs_size_bytes >= 0

    def test_returns_sorted_by_name(self):
        db_platform_handler.add_platform(_make_platform("Zebra Console", "zebra"))
        db_platform_handler.add_platform(_make_platform("Alpha Console", "alpha"))
        platforms = db_platform_handler.get_platforms()
        names = [p.name for p in platforms]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# get_platform_ids
# ---------------------------------------------------------------------------


class TestGetPlatformIds:
    def test_returns_ids_list(self, platform: Platform):
        ids = db_platform_handler.get_platform_ids()
        assert platform.id in ids

    def test_returns_list_type(self, platform: Platform):
        result = db_platform_handler.get_platform_ids()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# get_platform_by_fs_slug / get_platform_by_slug
# ---------------------------------------------------------------------------


class TestGetPlatformBySlug:
    def test_get_by_fs_slug(self, platform: Platform):
        fetched = db_platform_handler.get_platform_by_fs_slug(platform.fs_slug)
        assert fetched is not None
        assert fetched.id == platform.id

    def test_get_by_fs_slug_not_found(self):
        assert db_platform_handler.get_platform_by_fs_slug("nonexistent") is None

    def test_get_by_slug(self, platform: Platform):
        fetched = db_platform_handler.get_platform_by_slug(platform.slug)
        assert fetched is not None
        assert fetched.id == platform.id

    def test_get_by_slug_not_found(self):
        assert db_platform_handler.get_platform_by_slug("nonexistent-slug") is None


# ---------------------------------------------------------------------------
# update_platform
# ---------------------------------------------------------------------------


class TestUpdatePlatform:
    def test_update_name(self, platform: Platform):
        db_platform_handler.update_platform(platform.id, {"name": "Renamed Console"})
        fetched = db_platform_handler.get_platform(platform.id)
        assert fetched is not None
        assert fetched.name == "Renamed Console"

    def test_update_custom_name(self, platform: Platform):
        db_platform_handler.update_platform(
            platform.id, {"custom_name": "My Custom Name"}
        )
        fetched = db_platform_handler.get_platform(platform.id)
        assert fetched is not None
        assert fetched.custom_name == "My Custom Name"


# ---------------------------------------------------------------------------
# delete_platform
# ---------------------------------------------------------------------------


class TestDeletePlatform:
    def test_delete_removes_platform(self, platform: Platform):
        plat_id = platform.id
        db_platform_handler.delete_platform(plat_id)
        assert db_platform_handler.get_platform(plat_id) is None

    def test_delete_also_removes_roms(self, platform: Platform):
        rom = db_rom_handler.add_rom(_make_rom(platform, "Orphan ROM"))
        db_platform_handler.delete_platform(platform.id)
        assert db_rom_handler.get_rom(rom.id) is None


# ---------------------------------------------------------------------------
# mark_missing_platforms
# ---------------------------------------------------------------------------


class TestMarkMissingPlatforms:
    def test_marks_platform_not_in_keep_list(self, platform: Platform):
        missing = db_platform_handler.mark_missing_platforms([])
        ids = [p.id for p in missing]
        assert platform.id in ids
        fetched = db_platform_handler.get_platform(platform.id)
        assert fetched is not None
        assert fetched.missing_from_fs is True

    def test_does_not_mark_platform_in_keep_list(self, platform: Platform):
        db_platform_handler.mark_missing_platforms([platform.fs_slug])
        fetched = db_platform_handler.get_platform(platform.id)
        assert fetched is not None
        assert not fetched.missing_from_fs

    def test_also_marks_roms_as_missing(self, platform: Platform):
        rom = db_rom_handler.add_rom(_make_rom(platform, "Will Be Missing"))
        db_platform_handler.mark_missing_platforms([])
        fetched_rom = db_rom_handler.get_rom(rom.id)
        assert fetched_rom is not None
        assert fetched_rom.missing_from_fs is True

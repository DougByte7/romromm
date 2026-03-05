"""
Unit tests for DBRomsHandler.

Covers core CRUD, filtering, and RomUser operations.
"""

from datetime import datetime, timezone

import pytest

from handler.database import db_rom_handler
from models.platform import Platform
from models.rom import Rom, RomUser
from models.user import User


def _make_rom(platform: Platform, *, name: str, fs_name: str | None = None) -> Rom:
    slug = name.lower().replace(" ", "-")
    fs = fs_name or f"{name.replace(' ', '_')}.zip"
    return Rom(
        platform_id=platform.id,
        name=name,
        slug=slug,
        fs_name=fs,
        fs_name_no_tags=name.replace(" ", "_"),
        fs_name_no_ext=name.replace(" ", "_"),
        fs_extension="zip",
        fs_path=f"{platform.fs_slug}/roms",
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestAddAndGetRom:
    def test_add_and_get_rom(self, rom: Rom):
        fetched = db_rom_handler.get_rom(rom.id)
        assert fetched is not None
        assert fetched.id == rom.id
        assert fetched.fs_name == "test_rom.zip"

    def test_get_nonexistent_rom_returns_none(self):
        assert db_rom_handler.get_rom(999999) is None

    def test_get_roms_by_ids_returns_correct_set(
        self, rom: Rom, platform: Platform
    ):
        rom2 = db_rom_handler.add_rom(_make_rom(platform, name="Second ROM"))
        result = db_rom_handler.get_roms_by_ids([rom.id, rom2.id])
        ids = {r.id for r in result}
        assert ids == {rom.id, rom2.id}

    def test_get_roms_by_ids_empty_list_returns_empty(self):
        assert db_rom_handler.get_roms_by_ids([]) == []


class TestUpdateRom:
    def test_update_rom_changes_field(self, rom: Rom):
        db_rom_handler.update_rom(rom.id, {"name": "Updated Name"})
        updated = db_rom_handler.get_rom(rom.id)
        assert updated is not None
        assert updated.name == "Updated Name"

    def test_update_rom_multiple_fields(self, rom: Rom):
        db_rom_handler.update_rom(rom.id, {"name": "New Name", "slug": "new-slug"})
        updated = db_rom_handler.get_rom(rom.id)
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.slug == "new-slug"


class TestDeleteRom:
    def test_delete_rom(self, rom: Rom, platform: Platform):
        db_rom_handler.delete_rom(rom.id)
        roms = db_rom_handler.get_roms_scalar(platform_ids=[platform.id])
        assert all(r.id != rom.id for r in roms)

    def test_delete_rom_does_not_affect_others(self, rom: Rom, platform: Platform):
        rom2 = db_rom_handler.add_rom(_make_rom(platform, name="Keeper ROM"))
        db_rom_handler.delete_rom(rom.id)
        assert db_rom_handler.get_rom(rom2.id) is not None


# ---------------------------------------------------------------------------
# get_roms_scalar filtering
# ---------------------------------------------------------------------------


class TestGetRomsScalarFiltering:
    def test_filter_by_platform_id(self, rom: Rom, platform: Platform):
        roms = db_rom_handler.get_roms_scalar(platform_ids=[platform.id])
        assert len(roms) >= 1
        assert all(r.platform_id == platform.id for r in roms)

    def test_filter_by_nonexistent_platform_returns_empty(self, rom: Rom):
        roms = db_rom_handler.get_roms_scalar(platform_ids=[999999])
        assert roms == []

    def test_filter_by_search_term_matches_name(self, rom: Rom, platform: Platform):
        roms = db_rom_handler.get_roms_scalar(search_term="test_rom")
        ids = {r.id for r in roms}
        assert rom.id in ids

    def test_filter_by_search_term_no_match(self, platform: Platform):
        roms = db_rom_handler.get_roms_scalar(
            search_term="zzz_no_match_xyzzy_99999"
        )
        assert roms == []

    def test_filter_by_search_term_multiple_terms(self, platform: Platform):
        rom_a = db_rom_handler.add_rom(_make_rom(platform, name="Alpha Game"))
        rom_b = db_rom_handler.add_rom(_make_rom(platform, name="Beta Game"))
        _rom_c = db_rom_handler.add_rom(_make_rom(platform, name="Gamma Game"))

        results = db_rom_handler.get_roms_scalar(search_term="Alpha|Beta")
        ids = {r.id for r in results}
        assert rom_a.id in ids
        assert rom_b.id in ids

    def test_filter_matched_true_returns_only_matched(
        self, rom: Rom, platform: Platform
    ):
        # rom fixture has no metadata IDs → unmatched
        unmatched_count = len(
            db_rom_handler.get_roms_scalar(matched=False)
        )
        matched_count = len(
            db_rom_handler.get_roms_scalar(matched=True)
        )
        assert unmatched_count >= 1
        assert matched_count == 0

    def test_filter_missing_false_excludes_missing(
        self, rom: Rom, platform: Platform
    ):
        db_rom_handler.update_rom(rom.id, {"missing_from_fs": True})
        present = db_rom_handler.get_roms_scalar(missing=False)
        assert all(not r.missing_from_fs for r in present)

    def test_filter_missing_true_returns_only_missing(
        self, rom: Rom, platform: Platform
    ):
        db_rom_handler.update_rom(rom.id, {"missing_from_fs": True})
        missing = db_rom_handler.get_roms_scalar(missing=True)
        ids = {r.id for r in missing}
        assert rom.id in ids


# ---------------------------------------------------------------------------
# mark_missing_roms
# ---------------------------------------------------------------------------


class TestMarkMissingRoms:
    def test_marks_roms_not_in_keep_list(self, rom: Rom, platform: Platform):
        missing = db_rom_handler.mark_missing_roms(platform.id, [])
        assert any(r.id == rom.id for r in missing)
        updated = db_rom_handler.get_rom(rom.id)
        assert updated is not None
        assert updated.missing_from_fs is True

    def test_does_not_mark_roms_in_keep_list(self, rom: Rom, platform: Platform):
        missing = db_rom_handler.mark_missing_roms(platform.id, [rom.fs_name])
        assert all(r.id != rom.id for r in missing)
        updated = db_rom_handler.get_rom(rom.id)
        assert updated is not None
        assert not updated.missing_from_fs


# ---------------------------------------------------------------------------
# get_roms_by_fs_name
# ---------------------------------------------------------------------------


class TestGetRomsByFsName:
    def test_returns_correct_mapping(self, rom: Rom, platform: Platform):
        result = db_rom_handler.get_roms_by_fs_name(
            platform.id, [rom.fs_name]
        )
        assert rom.fs_name in result
        assert result[rom.fs_name].id == rom.id

    def test_returns_empty_dict_for_unknown_names(self, platform: Platform):
        result = db_rom_handler.get_roms_by_fs_name(
            platform.id, ["nonexistent.zip"]
        )
        assert result == {}

    def test_ignores_roms_from_other_platforms(
        self, rom: Rom, platform: Platform
    ):
        other_platform = Platform(
            name="other_platform",
            slug="other_platform_slug",
            fs_slug="other_platform_slug",
        )
        from handler.database import db_platform_handler

        other_platform = db_platform_handler.add_platform(other_platform)
        other_rom = db_rom_handler.add_rom(
            _make_rom(other_platform, name="Other ROM", fs_name="other.zip")
        )

        result = db_rom_handler.get_roms_by_fs_name(
            platform.id, [other_rom.fs_name]
        )
        assert result == {}


# ---------------------------------------------------------------------------
# RomUser
# ---------------------------------------------------------------------------


class TestRomUser:
    def test_add_and_get_rom_user(self, rom: Rom, admin_user: User):
        rom_user = db_rom_handler.get_rom_user(rom.id, admin_user.id)
        assert rom_user is not None
        assert rom_user.rom_id == rom.id
        assert rom_user.user_id == admin_user.id

    def test_update_rom_user_last_played(self, rom: Rom, admin_user: User):
        rom_user = db_rom_handler.get_rom_user(rom.id, admin_user.id)
        assert rom_user is not None
        played_at = datetime(2024, 6, 15, tzinfo=timezone.utc)
        db_rom_handler.update_rom_user(rom_user.id, {"last_played": played_at})
        updated = db_rom_handler.get_rom_user(rom.id, admin_user.id)
        assert updated is not None
        assert updated.last_played is not None

    def test_get_rom_user_by_id(self, rom: Rom, admin_user: User):
        rom_user = db_rom_handler.get_rom_user(rom.id, admin_user.id)
        assert rom_user is not None
        fetched = db_rom_handler.get_rom_user_by_id(rom_user.id)
        assert fetched is not None
        assert fetched.id == rom_user.id

    def test_filter_last_played_true(
        self, rom: Rom, platform: Platform, admin_user: User
    ):
        unplayed_rom = db_rom_handler.add_rom(
            _make_rom(platform, name="Unplayed ROM")
        )
        db_rom_handler.add_rom_user(rom_id=unplayed_rom.id, user_id=admin_user.id)

        rom_user = db_rom_handler.get_rom_user(rom.id, admin_user.id)
        assert rom_user is not None
        db_rom_handler.update_rom_user(
            rom_user.id,
            {"last_played": datetime(2024, 1, 1, tzinfo=timezone.utc)},
        )

        played = db_rom_handler.get_roms_scalar(
            user_id=admin_user.id, last_played=True
        )
        unplayed = db_rom_handler.get_roms_scalar(
            user_id=admin_user.id, last_played=False
        )

        played_ids = {r.id for r in played}
        unplayed_ids = {r.id for r in unplayed}

        assert rom.id in played_ids
        assert unplayed_rom.id in unplayed_ids
        assert rom.id not in unplayed_ids
        assert unplayed_rom.id not in played_ids

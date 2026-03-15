"""Tests for encrypted credential seed/export scripts."""

import json
import uuid
from contextlib import asynccontextmanager

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from regulahub.db.models import Base, RegulaHubUser, System, SystemProfile, SystemType
from regulahub.db.repositories.credential import CredentialRepository

# Fixed IDs for test seed data
REG_TYPE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SISREG_ID = uuid.uuid4()
VF_PROFILE_ID = uuid.uuid4()
SOL_PROFILE_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


@pytest.fixture
def fernet_key():
    return Fernet.generate_key().decode()


@pytest.fixture
def fernet(fernet_key):
    return Fernet(fernet_key.encode())


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Seed system type + user + regulation system + profiles
        session.add(SystemType(id=REG_TYPE_ID, code="regulation", name="Regulation"))
        session.add(RegulaHubUser(id=USER_ID, name="Test User", email="test@example.com", login="testuser"))
        session.add(
            System(id=SISREG_ID, system_type_id=REG_TYPE_ID, code="SISREG", name="SisReg", table_prefix="sisreg")
        )
        session.add(
            SystemProfile(
                id=VF_PROFILE_ID,
                scope_id=REG_TYPE_ID,
                system_id=SISREG_ID,
                profile_name="VIDEOFONISTA",
                description="State-wide view",
            )
        )
        session.add(
            SystemProfile(
                id=SOL_PROFILE_ID,
                scope_id=REG_TYPE_ID,
                system_id=SISREG_ID,
                profile_name="SOLICITANTE",
                description="Unit-scoped view",
            )
        )
        await session.flush()
        yield session

    await engine.dispose()


@pytest.fixture
def repo(db_session):
    return CredentialRepository(db_session)


def _make_seed_file(tmp_path, fernet, credentials):
    """Create a seed JSON file with encrypted credentials."""
    entries = []
    for cred in credentials:
        entries.append(
            {
                "encrypted_username": fernet.encrypt(cred["username"].encode()).decode(),
                "encrypted_password": fernet.encrypt(cred["password"].encode()).decode(),
                "profile_type": cred.get("profile_type", "videofonista"),
                "system": cred.get("system", "SISREG"),
                "state": cred.get("state", "AM"),
                "state_name": cred.get("state_name", "Amazonas"),
                "unit_name": cred.get("unit_name", ""),
                "unit_cnes": cred.get("unit_cnes", ""),
            }
        )

    seed_data = {"version": 1, "encrypted_with": "fernet", "credentials": entries}
    seed_file = tmp_path / "credentials.enc.json"
    seed_file.write_text(json.dumps(seed_data))
    return seed_file


def _patch_settings(monkeypatch, fernet_key, seed_path):
    """Patch encryption key and seed path for tests."""
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", fernet_key)
    monkeypatch.setenv("SEED_CREDENTIALS_PATH", str(seed_path))

    from regulahub.config import get_credential_encryption_settings, get_seed_settings
    from regulahub.utils.encryption import _get_fernet

    get_credential_encryption_settings.cache_clear()
    get_seed_settings.cache_clear()
    _get_fernet.cache_clear()


async def _run_seed(monkeypatch, db_session):
    """Run the seed function with mocked DB session factory.

    Mimics the real call pattern: get_session_factory() -> factory -> factory() -> async CM -> session
    """
    from regulahub.scripts import seed_credentials as seed_mod

    @asynccontextmanager
    async def _fake_cm():
        yield db_session

    class _FakeSessionMaker:
        def __call__(self):
            return _fake_cm()

    monkeypatch.setattr(seed_mod, "get_session_factory", lambda: _FakeSessionMaker())

    await seed_mod.seed()


async def test_seed_from_file_creates_credentials(tmp_path, fernet_key, fernet, monkeypatch, db_session, repo):
    creds = [
        {"username": "user1", "password": "pass1", "profile_type": "VIDEOFONISTA", "state": "AM"},
        {
            "username": "user2",
            "password": "pass2",
            "profile_type": "SOLICITANTE",
            "state": "SP",
            "state_name": "São Paulo",
            "unit_name": "UBS TEST",
            "unit_cnes": "1234567",
        },
    ]
    seed_file = _make_seed_file(tmp_path, fernet, creds)
    _patch_settings(monkeypatch, fernet_key, seed_file)

    await _run_seed(monkeypatch, db_session)

    all_creds = await repo.get_active_by_system("SISREG")
    assert len(all_creds) == 2


async def test_seed_from_file_is_idempotent(tmp_path, fernet_key, fernet, monkeypatch, db_session, repo):
    creds = [{"username": "user1", "password": "pass1", "profile_type": "VIDEOFONISTA"}]
    seed_file = _make_seed_file(tmp_path, fernet, creds)
    _patch_settings(monkeypatch, fernet_key, seed_file)

    await _run_seed(monkeypatch, db_session)
    await _run_seed(monkeypatch, db_session)

    all_creds = await repo.get_active_by_system("SISREG")
    assert len(all_creds) == 1


async def test_seed_skips_missing_file(tmp_path, fernet_key, monkeypatch, db_session, repo):
    missing_path = tmp_path / "nonexistent.json"
    _patch_settings(monkeypatch, fernet_key, missing_path)

    await _run_seed(monkeypatch, db_session)

    all_creds = await repo.get_active_by_system("SISREG")
    assert len(all_creds) == 0


async def test_seed_skips_unknown_version(tmp_path, fernet_key, fernet, monkeypatch, db_session, repo):
    seed_file = tmp_path / "credentials.enc.json"
    seed_file.write_text(json.dumps({"version": 99, "credentials": []}))
    _patch_settings(monkeypatch, fernet_key, seed_file)

    await _run_seed(monkeypatch, db_session)

    all_creds = await repo.get_active_by_system("SISREG")
    assert len(all_creds) == 0


async def test_seed_decrypts_username_correctly(tmp_path, fernet_key, fernet, monkeypatch, db_session, repo):
    creds = [{"username": "12345678901JOHN", "password": "secret", "profile_type": "VIDEOFONISTA"}]
    seed_file = _make_seed_file(tmp_path, fernet, creds)
    _patch_settings(monkeypatch, fernet_key, seed_file)

    await _run_seed(monkeypatch, db_session)

    found = await repo.get_by_username_profile_system("12345678901JOHN", "videofonista", "SISREG")
    assert found is not None
    assert found.username == "12345678901JOHN"


async def test_seed_password_stored_as_is(tmp_path, fernet_key, fernet, monkeypatch, db_session, repo):
    encrypted_pw = fernet.encrypt(b"secret123").decode()
    seed_file = tmp_path / "credentials.enc.json"
    seed_data = {
        "version": 1,
        "encrypted_with": "fernet",
        "credentials": [
            {
                "encrypted_username": fernet.encrypt(b"testuser").decode(),
                "encrypted_password": encrypted_pw,
                "profile_type": "VIDEOFONISTA",
                "system": "SISREG",
                "state": "AM",
                "state_name": "Amazonas",
                "unit_name": "",
                "unit_cnes": "",
            }
        ],
    }
    seed_file.write_text(json.dumps(seed_data))
    _patch_settings(monkeypatch, fernet_key, seed_file)

    await _run_seed(monkeypatch, db_session)

    found = await repo.get_by_username_profile_system("testuser", "videofonista", "SISREG")
    assert found is not None
    assert found.encrypted_password == encrypted_pw


async def test_roundtrip_export_then_seed(tmp_path, fernet_key, fernet, monkeypatch, db_session, repo):
    """Export from DB -> seed into fresh DB -> verify match."""
    _patch_settings(monkeypatch, fernet_key, tmp_path / "unused.json")

    from regulahub.utils.encryption import encrypt_password

    # Create initial credentials in DB
    await repo.create(
        {
            "user_id": USER_ID,
            "profile_id": VF_PROFILE_ID,
            "username": "rtuser1",
            "encrypted_password": encrypt_password("pass1"),
            "state": "AM",
            "state_name": "Amazonas",
        }
    )
    await repo.create(
        {
            "user_id": USER_ID,
            "profile_id": SOL_PROFILE_ID,
            "username": "rtuser2",
            "encrypted_password": encrypt_password("pass2"),
            "state": "SP",
            "state_name": "São Paulo",
            "unit_name": "UBS TEST",
            "unit_cnes": "9999999",
        }
    )
    await db_session.flush()

    # Export — resolve profile names from system_profiles for the seed file
    all_creds = await repo.get_active_by_system("SISREG")
    entries = []
    for cred in all_creds:
        # Look up profile name for export
        from sqlalchemy import select

        profile = await db_session.execute(select(SystemProfile).where(SystemProfile.id == cred.profile_id))
        sp = profile.scalar_one()
        entries.append(
            {
                "encrypted_username": encrypt_password(cred.username),
                "encrypted_password": cred.encrypted_password,
                "profile_type": sp.profile_name,
                "system": "SISREG",
                "state": cred.state or "",
                "state_name": cred.state_name or "",
                "unit_name": cred.unit_name or "",
                "unit_cnes": cred.unit_cnes or "",
            }
        )
    seed_data = {"version": 1, "encrypted_with": "fernet", "credentials": entries}
    seed_file = tmp_path / "exported.enc.json"
    seed_file.write_text(json.dumps(seed_data))

    # Seed into a fresh DB
    engine2 = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine2.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory2 = async_sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False)
    async with factory2() as session2:
        # Seed system type + user + system + profiles in fresh DB
        session2.add(SystemType(id=REG_TYPE_ID, code="regulation", name="Regulation"))
        session2.add(RegulaHubUser(id=USER_ID, name="Test User", email="test@example.com", login="testuser"))
        session2.add(
            System(id=SISREG_ID, system_type_id=REG_TYPE_ID, code="SISREG", name="SisReg", table_prefix="sisreg")
        )
        session2.add(
            SystemProfile(
                id=VF_PROFILE_ID,
                scope_id=REG_TYPE_ID,
                system_id=SISREG_ID,
                profile_name="VIDEOFONISTA",
                description="State-wide view",
            )
        )
        session2.add(
            SystemProfile(
                id=SOL_PROFILE_ID,
                scope_id=REG_TYPE_ID,
                system_id=SISREG_ID,
                profile_name="SOLICITANTE",
                description="Unit-scoped view",
            )
        )
        await session2.flush()

        _patch_settings(monkeypatch, fernet_key, seed_file)

        from regulahub.scripts import seed_credentials as seed_mod

        @asynccontextmanager
        async def _fake_cm2():
            yield session2

        class _Maker2:
            def __call__(self):
                return _fake_cm2()

        monkeypatch.setattr(seed_mod, "get_session_factory", lambda: _Maker2())

        await seed_mod.seed()

        repo2 = CredentialRepository(session2)
        seeded = await repo2.get_active_by_system("SISREG")
        assert len(seeded) == 2

        usernames = {c.username for c in seeded}
        assert "rtuser1" in usernames
        assert "rtuser2" in usernames

        # Verify passwords decrypt correctly
        from regulahub.utils.encryption import decrypt_password

        for c in seeded:
            pw = decrypt_password(c.encrypted_password)
            assert pw in ("pass1", "pass2")

    await engine2.dispose()

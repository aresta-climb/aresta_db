# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Unit tests for the XDG Desktop Portal Secret keyring backend.
Written in English for upstream readiness (jaraco/keyring).
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import keyring.errors

from editor.plataforma.linux.portal_keyring import PortalKeyring


@pytest.fixture
def mock_master_key():
    """Provides a deterministic 32-byte master key for testing."""
    return b"01234567890123456789012345678901"


@pytest.fixture
def temp_keyring_file(tmp_path):
    """Provides a temporary path for the encrypted keyring store."""
    return tmp_path / "test_keyring.enc"


@pytest.fixture
def portal_keyring(temp_keyring_file, mock_master_key):
    """Initializes PortalKeyring with mock storage path and mock key retriever."""
    backend = PortalKeyring(storage_path=temp_keyring_file)
    backend._cached_master_key = mock_master_key
    return backend


def test_priority_available():
    """Validates that priority returns 5.0 when the portal service is functional."""
    with patch.object(PortalKeyring, "is_available", return_value=True):
        assert PortalKeyring.priority == 5.0


def test_priority_unavailable():
    """Validates that priority returns 0.0 when the portal is not responsive or not installed."""
    with patch.object(PortalKeyring, "is_available", return_value=False):
        assert PortalKeyring.priority == 0.0


def test_init_raises_without_xdg_data_home_when_no_storage_path():
    """Ensures instantiation fails if neither storage_path nor XDG_DATA_HOME is provided."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="XDG_DATA_HOME environment variable is required"):
            PortalKeyring()


def test_init_with_xdg_data_home(tmp_path):
    """Ensures default storage_path uses XDG_DATA_HOME without falling back to shared directory."""
    with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}):
        backend = PortalKeyring()
        assert backend._storage_path == tmp_path / "keyring.enc"


def test_is_available_without_xdg_data_home_returns_false():
    """Validates is_available returns False immediately when outside sandbox (no XDG_DATA_HOME)."""
    with patch.dict(os.environ, {}, clear=True):
        assert PortalKeyring.is_available() is False


def test_is_available_success(tmp_path):
    """Validates is_available returns True when XDG_DATA_HOME is set and portal ping succeeds."""
    mock_connection = MagicMock()
    with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}):
        with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", return_value=mock_connection):
            with patch.object(PortalKeyring, "_ping_portal", return_value=True):
                backend = PortalKeyring(storage_path=tmp_path / "k.enc")
                assert backend.is_available() is True


def test_is_available_failure(tmp_path):
    """Validates is_available returns False when connection or portal ping fails."""
    with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}):
        with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", side_effect=Exception("D-Bus down")):
            backend = PortalKeyring(storage_path=tmp_path / "k.enc")
            assert backend.is_available() is False


def test_is_available_ping_false(tmp_path):
    """Validates is_available returns False and logs warning when ping_portal returns False."""
    mock_conn = MagicMock()
    with patch.dict(os.environ, {"XDG_DATA_HOME": str(tmp_path)}):
        with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", return_value=mock_conn):
            with patch.object(PortalKeyring, "_ping_portal", return_value=False):
                backend = PortalKeyring(storage_path=tmp_path / "k.enc")
                assert backend.is_available() is False


def test_retrieve_master_key_from_dbus(tmp_path, mock_master_key):
    """Tests the D-Bus RetrieveSecret interaction with pipe descriptor passing."""
    backend = PortalKeyring(storage_path=tmp_path / "k.enc")

    # Simulate pipe: writing master key to pipe
    r, w = os.pipe()
    os.write(w, mock_master_key)
    os.close(w)

    mock_connection = MagicMock()

    with patch("os.pipe", return_value=(r, 999)):
        with patch("os.close"):
            with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", return_value=mock_connection):
                with patch.object(backend, "_call_retrieve_secret", return_value=None):
                    key = backend.get_master_key()
                    assert key == mock_master_key
                    assert len(key) == 32
                    assert backend._cached_master_key == mock_master_key


def test_retrieve_master_key_uses_cache(mock_master_key):
    """Ensures cached master key is returned without contacting D-Bus repeatedly."""
    backend = PortalKeyring(storage_path=Path("/fake/k.enc"))
    backend._cached_master_key = mock_master_key

    with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection") as mock_conn:
        key = backend.get_master_key()
        assert key == mock_master_key
        mock_conn.assert_not_called()


def test_set_and_get_password(portal_keyring, temp_keyring_file):
    """Validates storing, persisting, and retrieving a password."""
    assert portal_keyring.get_password("service_a", "user_1") is None

    portal_keyring.set_password("service_a", "user_1", "super_secret_token_123")
    assert portal_keyring.get_password("service_a", "user_1") == "super_secret_token_123"

    # Verify a second credential can be stored in the same file
    portal_keyring.set_password("service_b", "user_2", "another_password_456")
    assert portal_keyring.get_password("service_a", "user_1") == "super_secret_token_123"
    assert portal_keyring.get_password("service_b", "user_2") == "another_password_456"


def test_storage_file_is_encrypted(portal_keyring, temp_keyring_file, mock_master_key):
    """Confirms that the data written to disk is ciphertext and cannot be read as plaintext JSON."""
    portal_keyring.set_password("service_a", "user_1", "plaintext_secret_value")

    raw_bytes = temp_keyring_file.read_bytes()
    assert b"plaintext_secret_value" not in raw_bytes
    assert b"service_a" not in raw_bytes

    # Decrypt manually using AES-GCM to verify format: nonce (12 bytes) + ciphertext + tag (16 bytes)
    nonce = raw_bytes[:12]
    ciphertext_and_tag = raw_bytes[12:]
    aesgcm = AESGCM(mock_master_key)
    decrypted_json = aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=None)
    data = json.loads(decrypted_json.decode("utf-8"))

    assert data["service_a:user_1"] == "plaintext_secret_value"


def test_get_password_nonexistent_returns_none(portal_keyring):
    """Validates that query for a non-existent credential returns None."""
    assert portal_keyring.get_password("unknown_service", "unknown_user") is None


def test_delete_password(portal_keyring):
    """Tests removing an existing password."""
    portal_keyring.set_password("service_a", "user_1", "to_delete")
    assert portal_keyring.get_password("service_a", "user_1") == "to_delete"

    portal_keyring.delete_password("service_a", "user_1")
    assert portal_keyring.get_password("service_a", "user_1") is None


def test_delete_password_nonexistent_raises(portal_keyring):
    """Ensures deleting a non-existent password raises PasswordDeleteError."""
    with pytest.raises(keyring.errors.PasswordDeleteError):
        portal_keyring.delete_password("nonexistent_service", "nonexistent_user")


def test_corrupt_storage_file_returns_none(portal_keyring, temp_keyring_file):
    """Ensures corrupt or unreadable ciphertext handles gracefully without crash."""
    temp_keyring_file.write_bytes(b"corrupt_invalid_payload")
    assert portal_keyring.get_password("service_a", "user_1") is None


def test_priority_exception():
    """Validates that priority returns 0.0 when is_available raises an exception."""
    with patch.object(PortalKeyring, "is_available", side_effect=RuntimeError("unexpected failure")):
        assert PortalKeyring.priority == 0.0


def test_ping_portal():
    """Validates _ping_portal sends Ping to D-Bus peer and checks reply header."""
    from jeepney.low_level import MessageType

    mock_conn = MagicMock()
    mock_reply = MagicMock()
    mock_reply.header.message_type = MessageType.method_return
    mock_conn.send_and_get_reply.return_value = mock_reply
    assert PortalKeyring._ping_portal(mock_conn) is True

    # Supports int value if mocked or if int is returned
    mock_reply.header.message_type = 2
    assert PortalKeyring._ping_portal(mock_conn) is True

    mock_reply.header.message_type = MessageType.error
    assert PortalKeyring._ping_portal(mock_conn) is False

    mock_reply.header.message_type = 3
    assert PortalKeyring._ping_portal(mock_conn) is False


def test_call_retrieve_secret():
    """Validates _call_retrieve_secret builds and dispatches the D-Bus method call."""
    mock_conn = MagicMock()
    backend = PortalKeyring(storage_path=Path("/fake/k.enc"))
    backend._call_retrieve_secret(mock_conn, 123)
    mock_conn.send_and_get_reply.assert_called_once()


def test_retrieve_master_key_non_32_bytes(tmp_path):
    """Validates non-32-byte secret is hashed via SHA-256 to produce a 32-byte master key."""
    backend = PortalKeyring(storage_path=tmp_path / "k.enc")
    r, w = os.pipe()
    os.write(w, b"short_secret")
    os.close(w)

    mock_conn = MagicMock()
    with patch("os.pipe", return_value=(r, 999)):
        with patch("os.close"):
            with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", return_value=mock_conn):
                with patch.object(backend, "_call_retrieve_secret"):
                    key = backend.get_master_key()
                    assert len(key) == 32
                    import hashlib
                    assert key == hashlib.sha256(b"short_secret").digest()


def test_retrieve_master_key_empty_raises(tmp_path):
    """Validates empty secret from portal raises KeyringError."""
    backend = PortalKeyring(storage_path=tmp_path / "k.enc")
    r, w = os.pipe()
    os.close(w)

    mock_conn = MagicMock()
    with patch("os.pipe", return_value=(r, 999)):
        with patch("os.close"):
            with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", return_value=mock_conn):
                with patch.object(backend, "_call_retrieve_secret"):
                    with pytest.raises(keyring.errors.KeyringError):
                        backend.get_master_key()


def test_retrieve_master_key_oserror_suppressed(tmp_path, mock_master_key):
    """Validates OSError during os.close or fdopen is handled."""
    backend = PortalKeyring(storage_path=tmp_path / "k.enc")
    r, w = os.pipe()
    os.write(w, mock_master_key)
    os.close(w)

    mock_conn = MagicMock()
    with patch("os.pipe", return_value=(r, 999)):
        with patch("os.close", side_effect=OSError("close failed")):
            with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", return_value=mock_conn):
                with patch.object(backend, "_call_retrieve_secret"):
                    key = backend.get_master_key()
                    assert key == mock_master_key

    # Test fdopen OSError with fresh backend
    backend2 = PortalKeyring(storage_path=tmp_path / "k2.enc")
    with patch("os.pipe", return_value=(r, 999)):
        with patch("os.close"):
            with patch("os.fdopen", side_effect=OSError("read failed")):
                with patch("editor.plataforma.linux.portal_keyring.open_dbus_connection", return_value=mock_conn):
                    with patch.object(backend2, "_call_retrieve_secret"):
                        with pytest.raises(keyring.errors.KeyringError):
                            backend2.get_master_key()


def test_corrupt_storage_file_decrypt_exception(portal_keyring, temp_keyring_file):
    """Ensures ciphertext with valid length but corrupt payload is handled safely."""
    # Write 40 bytes of invalid data (> 28 bytes)
    temp_keyring_file.write_bytes(b"A" * 40)
    assert portal_keyring.get_password("service_a", "user_1") is None


def test_get_credential(portal_keyring):
    """Validates get_credential returns SimpleCredential with username and password."""
    assert portal_keyring.get_credential("service_a", None) is None
    assert portal_keyring.get_credential("service_a", "") is None

    portal_keyring.set_password("service_a", "user_1", "my_pass")
    cred = portal_keyring.get_credential("service_a", "user_1")
    assert cred is not None
    assert cred.username == "user_1"
    assert cred.password == "my_pass"

    cred_empty = portal_keyring.get_credential("unknown", "unknown")
    assert cred_empty is None

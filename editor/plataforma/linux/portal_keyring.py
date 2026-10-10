# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
XDG Desktop Portal Secret Keyring Backend.

Provides a secure, sandboxed keyring backend using the FreeDesktop
org.freedesktop.portal.Secret D-Bus interface and local AES-256-GCM encryption.
Eliminates the requirement for unconfined host Secret Service access in Flatpak.

Written in English for upstream readiness (compatible with jaraco/keyring).
"""

import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional, cast

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jeepney import DBusAddress, new_method_call
from jeepney.io.blocking import open_dbus_connection
import keyring.backend
from keyring.compat import properties
from keyring.credentials import SimpleCredential
import keyring.errors

log = logging.getLogger(__name__)

PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT_PATH = "/org/freedesktop/portal/desktop"
PORTAL_INTERFACE = "org.freedesktop.portal.Secret"


class PortalKeyring(keyring.backend.KeyringBackend):
    """
    Keyring backend that integrates with the XDG Desktop Portal Secret service.
    
    The portal returns an application-specific master encryption key.
    Credentials are encrypted using AES-256-GCM and stored in the application's
    local data directory.
    """

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        if storage_path is not None:
            self._storage_path = storage_path
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if not xdg_data:
                raise RuntimeError(
                    "XDG_DATA_HOME environment variable is required for PortalKeyring "
                    "when storage_path is not explicitly provided"
                )
            self._storage_path = Path(xdg_data) / "keyring.enc"

        self._cached_master_key: Optional[bytes] = None

    @properties.classproperty
    def priority(cls) -> float:
        """Priority of this backend. Returns 5.0 when available, 0.0 otherwise."""
        try:
            if cls.is_available():
                return 5.0
        except Exception as exc:
            log.debug("PortalKeyring availability check failed: %s", exc)
        return 0.0

    @classmethod
    def is_available(cls) -> bool:
        """Checks if the portal secret service is accessible on the session bus and XDG_DATA_HOME is set."""
        if not os.environ.get("XDG_DATA_HOME"):
            return False

        try:
            with open_dbus_connection(bus="SESSION", enable_fds=True) as conn:
                return cls._ping_portal(conn)
        except Exception:
            return False

    @classmethod
    def _ping_portal(cls, connection: Any) -> bool:
        """Pings the desktop portal interface via D-Bus Peer ping."""
        peer_addr = DBusAddress(PORTAL_OBJECT_PATH, bus_name=PORTAL_BUS_NAME, interface="org.freedesktop.DBus.Peer")
        msg = new_method_call(peer_addr, "Ping")
        reply = connection.send_and_get_reply(msg)
        return bool(reply.header.message_type == 2)  # Method return

    def _call_retrieve_secret(self, connection: Any, write_fd: int) -> None:
        """Invokes RetrieveSecret on the portal interface with the pipe write descriptor."""
        portal_addr = DBusAddress(PORTAL_OBJECT_PATH, bus_name=PORTAL_BUS_NAME, interface=PORTAL_INTERFACE)
        msg = new_method_call(portal_addr, "RetrieveSecret", "ha{sv}", (write_fd, {}))
        connection.send_and_get_reply(msg)

    def get_master_key(self) -> bytes:
        """Retrieves and caches the 32-byte master key from the portal."""
        if self._cached_master_key is not None:
            return self._cached_master_key

        read_fd, write_fd = os.pipe()
        try:
            with open_dbus_connection(bus="SESSION", enable_fds=True) as conn:
                self._call_retrieve_secret(conn, write_fd)
        finally:
            try:
                os.close(write_fd)
            except OSError:
                pass

        try:
            with os.fdopen(read_fd, "rb") as pipe_in:
                raw_secret = pipe_in.read()
        except OSError:
            raw_secret = b""

        if not raw_secret:
            raise keyring.errors.KeyringError("Failed to retrieve secret from XDG Portal")

        if len(raw_secret) == 32:
            master_key = raw_secret
        else:
            master_key = hashlib.sha256(raw_secret).digest()

        self._cached_master_key = master_key
        return master_key

    def _load_storage(self) -> Dict[str, str]:
        """Reads and decrypts the credentials mapping from disk."""
        if not self._storage_path.exists():
            return {}

        try:
            data = self._storage_path.read_bytes()
            if len(data) < 28:  # 12 bytes nonce + 16 bytes auth tag minimum
                return {}

            nonce = data[:12]
            ciphertext = data[12:]
            key = self.get_master_key()
            aesgcm = AESGCM(key)
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
            return cast(Dict[str, str], json.loads(decrypted_bytes.decode("utf-8")))
        except Exception as exc:
            log.warning("Could not decrypt keyring store: %s", exc)
            return {}

    def _save_storage(self, mapping: Dict[str, str]) -> None:
        """Encrypts and atomically writes the credentials mapping to disk."""
        key = self.get_master_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        payload = json.dumps(mapping).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, payload, associated_data=None)

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        temp_dir = self._storage_path.parent
        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False) as tf:
            tf.write(nonce + ciphertext)
            temp_path = Path(tf.name)

        os.replace(temp_path, self._storage_path)

    def get_password(self, service: str, username: str) -> Optional[str]:
        """Gets password for the username on service."""
        storage = self._load_storage()
        return storage.get(f"{service}:{username}")

    def set_password(self, service: str, username: str, password: str) -> None:
        """Sets password for the username on service."""
        storage = self._load_storage()
        storage[f"{service}:{username}"] = password
        self._save_storage(storage)

    def delete_password(self, service: str, username: str) -> None:
        """Deletes password for the username on service."""
        storage = self._load_storage()
        key = f"{service}:{username}"
        if key not in storage:
            raise keyring.errors.PasswordDeleteError("No such password!")
        del storage[key]
        self._save_storage(storage)

    def get_credential(self, service: str, username: Optional[str]) -> Optional[SimpleCredential]:
        """Gets credential for a service and username."""
        if not username:
            return None
        password = self.get_password(service, username)
        if password is None:
            return None
        return SimpleCredential(username, password)


# Alias following standard keyring backend naming
Keyring = PortalKeyring

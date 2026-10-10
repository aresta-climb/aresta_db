## Purpose

Provides an isolated, sandboxed Python keyring backend using the XDG Desktop Portal Secret interface (`org.freedesktop.portal.Secret`) and local AES-256-GCM encryption, eliminating the need for unconfined host keyring D-Bus access.

## Requirements

### Requirement: Portal Keyring Backend Implementation
The system SHALL provide a `keyring.backend.KeyringBackend` implementation named `PortalKeyring` that interacts with the `org.freedesktop.portal.Secret` D-Bus service using `jeepney` and stores credentials encrypted with AES-256-GCM in application-isolated storage.

#### Scenario: Secret retrieval via portal D-Bus
- **WHEN** `PortalKeyring` initializes and requests the application master secret
- **THEN** it creates a Unix pipe and passes the write file descriptor to `RetrieveSecret` via D-Bus
- **AND** reads the master secret bytes from the pipe
- **AND** caches the master secret in memory for the process lifetime

#### Scenario: Storing and retrieving credentials in encrypted file
- **WHEN** `set_password` is called with service, username, and password
- **THEN** `PortalKeyring` updates the credentials mapping and writes it encrypted with AES-256-GCM using the portal master key to `$XDG_DATA_HOME/keyring.enc`
- **AND** `get_password` decrypts the file and returns the stored password

#### Scenario: Deleting credentials
- **WHEN** `delete_password` is called for an existing service and username
- **THEN** `PortalKeyring` removes the entry, re-encrypts the storage file, and persists the update

### Requirement: Priority and Fallback Handling
The `PortalKeyring` backend SHALL declare priority 5.0 when the portal is available and functional, and priority 0 when the portal is unavailable or fails to respond.

#### Scenario: Portal available in sandbox
- **WHEN** the application runs inside Flatpak or in a desktop session with active `org.freedesktop.portal.Secret`
- **THEN** `PortalKeyring` reports priority 5.0 and is selected as the primary backend by `keyring`

#### Scenario: Portal unavailable outside sandbox
- **WHEN** the portal D-Bus interface is not present or not responsive
- **THEN** `PortalKeyring` reports priority 0 or raises RuntimeError during availability check
- **AND** `keyring` falls back to secondary backends (such as `SecretService`, `KWallet` or memory fallback)

# Spec Delta

## MODIFIED Requirements

### Requirement: Portal Keyring Backend Implementation
The system SHALL provide a `keyring.backend.KeyringBackend` implementation named `PortalKeyring` that interacts with the `org.freedesktop.portal.Secret` D-Bus service using `jeepney` and stores credentials encrypted with AES-256-GCM in application-isolated storage, handling timeouts and portal errors gracefully.

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

#### Scenario: Portal response error or cancellation
- **WHEN** `RetrieveSecret` returns a non-zero response code or cancellation (e.g. locked system keyring)
- **THEN** `PortalKeyring` raises `KeyringError` immediately without blocking the application thread

#### Scenario: Non-blocking pipe read with timeout
- **WHEN** the portal accepts the call but fails to write secret bytes to the pipe
- **THEN** `PortalKeyring` checks for data readiness using non-blocking polling and raises `KeyringError` upon timeout without hanging

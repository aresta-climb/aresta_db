## ADDED Requirements

### Requirement: Targeted Cache Invalidation
The system SHALL invalidate the Cloudflare cache strictly for the root manifest files: `indice.binarypb` and `arquivos_serving.binarypb`.

#### Scenario: Assets are modified
- **WHEN** the `update_serving.py` script finishes uploading files to Cloudflare R2
- **THEN** it issues a `/purge_cache` HTTP request to the Cloudflare API containing ONLY the URLs for `indice.binarypb` and `arquivos_serving.binarypb`.

### Requirement: Cache Busting Delegation
The system SHALL NOT attempt to purge individual asset URLs (like `compilado.binarypb` or images) from the CDN, delegating cache busting entirely to the client application.

#### Scenario: Client accesses updated assets
- **WHEN** the mobile app needs to download a new asset
- **THEN** it reads the updated hash from `indice.binarypb` (or `arquivos_serving.binarypb`) and appends it as a query string (e.g., `?sha256sum=HASH`) to automatically bypass the CDN cache.

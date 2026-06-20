## ADDED Requirements

### Requirement: Manifesto Compilation
The system SHALL compute the sha256 checksum of every file residing in the `generated/` directory after a successful build and store it in `arquivos_serving.binarypb`.

#### Scenario: Database build is successful
- **WHEN** the `deploy_generated.py` script finishes compiling all croquis
- **THEN** it generates `arquivos_serving.binarypb` containing the relative path and checksum for all generated assets.

### Requirement: Full Deploy Fallback
The system SHALL execute a full download of git blobs and perform a bulk upload to Cloudflare R2 when the remote manifest is missing.

#### Scenario: Remote manifest is absent
- **WHEN** the deployment script attempts to fetch `vX/arquivos_serving.binarypb` from R2 and fails
- **THEN** it executes `git checkout HEAD -- generated/` to fetch all blobs, and uploads every file within `generated/` to the R2 bucket.

### Requirement: Delta Deploy Optimization
The system SHALL parse the remote and local manifests to detect differences and execute partial blobless checkouts and partial uploads to R2.

#### Scenario: Files are added or modified
- **WHEN** the deployment script detects new or changed checksums in the local manifest compared to the remote manifest
- **THEN** it checks out exclusively those specific files from git and uploads them to the R2 bucket.

#### Scenario: Files are deleted
- **WHEN** the deployment script detects files present in the remote manifest that are absent in the local manifest
- **THEN** it executes a delete operation against the Cloudflare R2 API for those specific paths.

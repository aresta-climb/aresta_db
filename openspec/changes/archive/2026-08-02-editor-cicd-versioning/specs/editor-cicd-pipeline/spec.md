## ADDED Requirements

### Requirement: Editor release automation
The system SHALL compile and publish the editor executable upon manual trigger, tagging the release with the provided version.

#### Scenario: User triggers the workflow
- **WHEN** a repository maintainer dispatches the release workflow with a specific semantic version
- **THEN** the system generates a Windows executable, creates a GitHub Release attached to the new git tag, and uploads the `.exe` artifact

### Requirement: Dev cycle progression
The system SHALL automatically bump the repository back to a development state after a successful release.

#### Scenario: Post-release bumping
- **WHEN** the release artifact has been uploaded and tagged successfully
- **THEN** the system calculates the next minor version, appends `-dev`, modifies the version file, and commits this back to the main branch

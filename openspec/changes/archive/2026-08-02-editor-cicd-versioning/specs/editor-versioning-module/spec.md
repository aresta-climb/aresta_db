## ADDED Requirements

### Requirement: Passive version tracking
The system SHALL maintain its compiled version string in an accessible Python module within the editor's source tree.

#### Scenario: Editor initializes
- **WHEN** the editor executable runs
- **THEN** it can passively read `version.py` (or equivalent module) to know its own embedded semantic version

### Requirement: Workflow version injection
The system SHALL allow external systems (like CI/CD pipelines) to overwrite the version constant prior to the packaging step.

#### Scenario: Pipeline execution
- **WHEN** the CI pipeline runs a sed/echo operation to replace the version constant
- **THEN** the resulting `version.py` successfully represents the requested target version for compilation

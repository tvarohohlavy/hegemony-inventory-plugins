<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Travnik <jakub.travnik@gmail.com>
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-inventory-plugins

Standalone release repo for Hegemony inventory plugin packages:

- `hegemony-inventory-sdk`
- `hegemony-inventory-netbox`
- `hegemony-inventory-infrahub`
- `hegemony-inventory-git`

The SDK and all provider wheels are released together from unified semver tags such as
`v0.1.0`. Provider wheels depend on the exact SDK version from the same release.

Public source is licensed under `AGPL-3.0-or-later`; commercial licenses may be
available separately. See [Licensing](LICENSING.md).

Contributions require the Hegemony Contributor License Agreement. See
[Contributing](CONTRIBUTING.md).

## Install From A Release

Install the SDK wheel and whichever provider wheels the container should enable:

```bash
uv pip install --system \
  https://github.com/tvarohohlavy/hegemony-inventory-plugins/releases/download/v0.1.0/hegemony_inventory_sdk-0.1.0-py3-none-any.whl \
  https://github.com/tvarohohlavy/hegemony-inventory-plugins/releases/download/v0.1.0/hegemony_inventory_netbox-0.1.0-py3-none-any.whl \
  https://github.com/tvarohohlavy/hegemony-inventory-plugins/releases/download/v0.1.0/hegemony_inventory_infrahub-0.1.0-py3-none-any.whl \
  https://github.com/tvarohohlavy/hegemony-inventory-plugins/releases/download/v0.1.0/hegemony_inventory_git-0.1.0-py3-none-any.whl
```

## Development

```bash
uv sync --all-packages
uv run pre-commit install --install-hooks
```

If you have [Task](https://taskfile.dev/) installed, the common workflow is:

```bash
task setup
task lint
task test
task build
task smoke
```

The hook set mirrors Hegemony where applicable for this package-only repo:
general file hygiene, pyproject validation, typos, Zizmor, workflow schema checks,
REUSE, Ruff, typecheck, tests, Gitleaks, and commitlint. UI, Docker, OpenAPI, and
task-runner hooks stay in Hegemony because those surfaces are not present here.

Run the same checks locally:

```bash
task ci
```

Run every configured pre-commit hook manually:

```bash
task precommit
```

Before tagging a release, update every package version and provider SDK pin:

```bash
task version:set -- 0.1.0
task lock
```

Tags must match package metadata. A `v0.1.0` tag publishes four wheels plus
`SHA256SUMS` to the matching GitHub Release.

Releases are intended to be immutable: the release workflow fails if a GitHub
Release for the tag already exists and never replaces published assets. If a
release artifact is wrong, cut a new patch tag instead of mutating the existing
release. The release workflow also creates GitHub artifact attestations for the
wheel files and checksum file.

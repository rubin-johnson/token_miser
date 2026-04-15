# Kanon + Loadout + token-miser Integration

## The Pipeline

```
kanon distributes  ->  loadout applies  ->  token-miser measures
(versioned packages)   (local config)       (A/B comparison)
```

### 1. Kanon distributes loadout packages

A manifest repository defines versioned loadout packages as kanon packages:

```xml
<!-- repo-specs/loadout-manifest.xml -->
<manifest>
  <remote name="origin" fetch="${GITBASE}" />
  <project name="token-miser-package"
           path=".packages/token-miser"
           remote="origin"
           revision="refs/tags/0.1.0" />
  <project name="thorough-package"
           path=".packages/thorough"
           remote="origin"
           revision="refs/tags/0.1.0" />
  <project name="tdd-strict-package"
           path=".packages/tdd-strict"
           remote="origin"
           revision="refs/tags/0.1.0" />
</manifest>
```

After `kanon install`, packages appear in `.packages/`:

```
.packages/
  token-miser/     -> ../.kanon-data/sources/loadouts/.packages/token-miser
  thorough/        -> ../.kanon-data/sources/loadouts/.packages/thorough
  tdd-strict/      -> ../.kanon-data/sources/loadouts/.packages/tdd-strict
```

### 2. Loadout applies a package

```bash
# Apply a kanon-synced package
loadout apply .packages/token-miser --yes

# Or apply a local package during development
loadout apply loadouts/token-miser --yes

# Swap to a different configuration
loadout apply .packages/thorough --yes

# Restore to pre-loadout state
loadout restore --yes
```

### 3. Token-miser measures the difference

```bash
# Compare vanilla vs a kanon-distributed package
token-miser run \
  --task tasks/quick-001.yaml \
  --baseline vanilla \
  --package .packages/token-miser

# Or compare two kanon-distributed packages against each other
token-miser run \
  --task tasks/quick-001.yaml \
  --baseline .packages/token-miser \
  --package .packages/thorough

# View results
token-miser compare --task quick-001
token-miser analyze --task quick-001
```

## Local development (without kanon)

During development, loadout packages live directly in `loadouts/`:

```bash
# Run experiment using local packages
token-miser run \
  --task tasks/quick-001.yaml \
  --baseline vanilla \
  --package loadouts/tdd-strict
```

## .kanon configuration

The `.kanon` file in this repo configures kanon to sync loadout packages from a manifest repository. After `kanon install`, the packages are available in `.packages/` and can be used as token-miser packages.

See `.kanon` for the source configuration.

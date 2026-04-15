# Kanon + Loadout + token-miser Integration

## The Pipeline

```
kanon distributes  ->  loadout applies  ->  token-miser measures
(versioned bundles)    (local config)       (A/B comparison)
```

### 1. Kanon distributes loadout bundles

A manifest repository defines versioned loadout bundles as kanon packages:

```xml
<!-- repo-specs/loadout-manifest.xml -->
<manifest>
  <remote name="origin" fetch="${GITBASE}" />
  <project name="token-miser-bundle"
           path=".packages/token-miser"
           remote="origin"
           revision="refs/tags/0.1.0" />
  <project name="thorough-bundle"
           path=".packages/thorough"
           remote="origin"
           revision="refs/tags/0.1.0" />
  <project name="tdd-strict-bundle"
           path=".packages/tdd-strict"
           remote="origin"
           revision="refs/tags/0.1.0" />
</manifest>
```

After `kanon install`, bundles appear in `.packages/`:

```
.packages/
  token-miser/     -> ../.kanon-data/sources/loadouts/.packages/token-miser
  thorough/        -> ../.kanon-data/sources/loadouts/.packages/thorough
  tdd-strict/      -> ../.kanon-data/sources/loadouts/.packages/tdd-strict
```

### 2. Loadout applies a bundle

```bash
# Apply a kanon-synced bundle
loadout apply .packages/token-miser --yes

# Or apply a local bundle during development
loadout apply loadouts/token-miser --yes

# Swap to a different configuration
loadout apply .packages/thorough --yes

# Restore to pre-loadout state
loadout restore --yes
```

### 3. Token-miser measures the difference

```bash
# Compare vanilla vs a kanon-distributed bundle
token-miser run \
  --task tasks/quick-001.yaml \
  --control vanilla \
  --treatment .packages/token-miser

# Or compare two kanon-distributed bundles against each other
token-miser run \
  --task tasks/quick-001.yaml \
  --control .packages/token-miser \
  --treatment .packages/thorough

# View results
token-miser compare --task quick-001
token-miser analyze --task quick-001
```

## Local development (without kanon)

During development, loadout bundles live directly in `loadouts/`:

```bash
# Run experiment using local bundles
token-miser run \
  --task tasks/quick-001.yaml \
  --control vanilla \
  --treatment loadouts/tdd-strict
```

## .kanon configuration

The `.kanon` file in this repo configures kanon to sync loadout bundles from a manifest repository. After `kanon install`, the bundles are available in `.packages/` and can be used as token-miser arms.

See `.kanon` for the source configuration.

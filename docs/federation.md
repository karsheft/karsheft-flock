# Mirror Federation

Flock supports a federated mirror architecture where multiple mirrors collaborate to serve packages with redundancy, geographic distribution, and delegated trust.

---

## Federation Model

A Flock mirror federation consists of:

- **Primary mirror**: The authoritative source of truth. Generates the package index, signs it, and pushes updates to replicas.
- **Replica mirrors**: Read-only copies of the primary. Serve packages to clients for performance and availability.
- **Trust anchors**: GPG keys whose fingerprints are distributed to clients. Clients verify that packages are signed by a trusted anchor, regardless of which mirror served them.

```
                    ┌─────────────────────┐
                    │   Primary Mirror    │
                    │  (Authoritative)    │
                    │  Signs Packages.gz  │
                    └──────────┬──────────┘
                               │ sync
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │Replica  │     │Replica  │     │Replica  │
        │US-East  │     │EU-West  │     │AP-South │
        └─────────┘     └─────────┘     └─────────┘
               │               │               │
               └───────────────┼───────────────┘
                               ▼
                          Flock Clients
```

---

## Setting Up a Primary Mirror

The primary mirror is the only mirror that writes the package index. It must:

1. Host a valid Debian-format repository (see [mirror-protocol.md](./mirror-protocol.md)).
2. Sign the `Packages` index with a GPG key.
3. Publish the signing key fingerprint for client use.

### Signing the Package Index

```bash
# Generate a signing key (if not already done)
gpg --batch --gen-key << 'EOF'
%no-protection
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: Flock Mirror Signing Key
Name-Email: mirror@example.com
Expire-Date: 1y
EOF

# Get the fingerprint
FINGERPRINT=$(gpg --list-keys --with-colons mirror@example.com | grep '^fpr' | head -1 | cut -d: -f10)
echo "Fingerprint: $FINGERPRINT"

# Sign the Packages file
gpg --armor --detach-sign \
  --local-user "$FINGERPRINT" \
  docs/dists/stable/main/binary-amd64/Packages
```

### Publishing the Key

Distribute the public key via your repository:

```bash
gpg --export --armor "$FINGERPRINT" > docs/mirror-signing-key.asc
```

Clients import it:

```bash
gpg --import mirror-signing-key.asc
```

---

## Setting Up a Replica Mirror

Replica mirrors sync from the primary and serve packages read-only.

### GitHub Actions Sync Workflow

```yaml
name: Sync from Primary Mirror
on:
  schedule:
    - cron: "30 * * * *"  # Every hour at :30
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout replica repo
        uses: actions/checkout@v4

      - name: Install rsync
        run: sudo apt-get install -y rsync

      - name: Sync from primary
        run: |
          rsync -avz --delete \
            rsync://primary.example.com/debian/ \
            docs/

      - name: Verify primary signature
        run: |
          gpg --import docs/mirror-signing-key.asc
          gpg --verify \
            docs/dists/stable/main/binary-amd64/Packages.sig \
            docs/dists/stable/main/binary-amd64/Packages

      - name: Commit changes
        run: |
          git config user.name "Mirror Bot"
          git config user.email "bot@example.com"
          git add docs/
          git diff --staged --quiet || \
            git commit -m "chore: sync mirror from primary $(date -u +%Y-%m-%dT%H:%MZ)"
          git push
```

---

## Trust Chains Between Mirrors

Flock uses a hierarchical trust chain:

```
Root CA Key (offline, hardware-secured)
    │
    └── Mirror Signing Key (online, rotated annually)
            │
            └── Package Index Signature (per sync)
                    │
                    └── Per-Package SHA256 in Packages.gz
                                │
                                └── .deb file on disk
```

### Trust Delegation

A primary mirror may delegate signing authority to replicas for specific package namespaces. This is expressed in a `federation.toml` file at the mirror root:

```toml
[federation]
primary = "https://primary.example.com/debian"
signing_key_fingerprint = "A2166B8DE8BDC3367D1901C11EE2FF37CA8DA16B"

[[replica]]
url = "https://us-east.example.com/debian"
region = "us-east"
signing_key_fingerprint = "B3277C9EF9CED4478E2012D22FF3006DB9CB25C9"
namespaces = ["pool/main/a-m/"]

[[replica]]
url = "https://eu-west.example.com/debian"
region = "eu-west"
signing_key_fingerprint = "C4388DAFF0DFE558902123E33AB4117EC8ADC36D"
namespaces = ["pool/main/n-z/"]
```

Clients can verify the entire chain:

```bash
# Verify replica is trusted by primary
flock verify-federation \
  --primary https://primary.example.com/debian \
  --replica https://eu-west.example.com/debian
```

---

## Mirror Failover

Flock supports mirror fallback at resolution time. If the primary mirror is unreachable, Flock tries replicas in order:

```bash
flock resolve --pkg curl \
  --mirror https://primary.example.com/debian \
  --mirror-fallback https://us-east.example.com/debian \
  --mirror-fallback https://eu-west.example.com/debian
```

Failover order:
1. Primary mirror (always tried first)
2. Fallback mirrors in the order specified
3. Error if all mirrors fail

The `flock.lock` records which mirror ultimately served each package, enabling auditing.

---

## Consistency Guarantees

In a federated setup, Flock enforces these consistency properties:

| Property | Guarantee |
|----------|-----------|
| **Index freshness** | Replicas must not serve an index older than 24 hours (configurable) |
| **Hash consistency** | SHA256 hashes in `flock.lock` are verified against the package, not the mirror |
| **Signature chain** | In `full` mode, every package must trace back to a trusted root key |
| **Lockfile immutability** | `flock.lock` is never modified at install time, regardless of mirror |

---

## Monitoring

Monitor federation health with periodic probe jobs:

```yaml
name: Mirror Health Check
on:
  schedule:
    - cron: "*/15 * * * *"  # Every 15 minutes

jobs:
  probe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install karsheft-flock
      - name: Probe primary
        run: flock resolve --pkg curl --mirror https://primary.example.com/debian
      - name: Probe replicas
        run: |
          flock resolve --pkg curl --mirror https://us-east.example.com/debian
          flock resolve --pkg curl --mirror https://eu-west.example.com/debian
```

Failed probes should trigger alerts via your monitoring system (PagerDuty, Opsgenie, etc.).

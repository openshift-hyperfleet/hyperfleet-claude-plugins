# HyperFleet Release Plugin

Release tooling for HyperFleet. Helps cut releases consistently from the release manifest and the actual git history.

## Skills

### `/release-notes` — deterministic release-notes generator

Generates a release-notes draft for a HyperFleet release. A deterministic engine **grounds** it in the real git history — which tickets/CVEs shipped, their categories, components, and image digests. The skill then **enriches** each entry with its JIRA ticket summary, **drafts** the Overview and Highlights, and trims internal noise. It's grounded so it never invents content — every line traces to a real ticket or CVE.

Trigger it by asking, e.g.:

- "draft the release notes for 0.3"
- "generate a changelog for the 0.3 release"

**What it does**

- **Manifest-driven** — per-component target versions from `RELEASE_MANIFEST.yaml`, with each component's baseline auto-resolved (previous-release manifest, else its previous GA tag). Independent per-component versioning is supported.
- **Categorizes** by commit type — `feat` → Features, `fix` → Bug Fixes, `perf` → Performance, any **CVE** → Security (grouped by CVE id across all affected components + tickets).
- **Drops** Renovate/dependency bumps and internal types (chore/test/docs/ci/refactor).
- **Dedups** — one entry per JIRA ticket across repos, union of affected components.
- **Real digests + release date** — pulls each image's SHA256 and build-date from Quay; the build-date sets the release date.
- **Flags non-conforming commits** so changes that won't appear in the notes (wrong format / no JIRA key) get a follow-up.

On top of that grounded data, the skill **enriches** each entry with its real JIRA ticket summary (replacing the raw commit subject), **drafts** the Overview and Highlights, **seeds** Known Issues from open component bugs, and **trims** internal noise — all grounded, so nothing is invented.

The release date is taken from the image build-date. What's left for a human is light curation — tune the Overview, write or verify the Upgrade Notes, and triage which Known Issues candidates are real for the release.

**Prerequisites**

- The component repos (`hyperfleet-api`, `hyperfleet-sentinel`, `hyperfleet-adapter`) checked out under a common directory with up-to-date tags (`git fetch --tags`).
- `git`, and `skopeo` for image digests (or run with `NO_DIGEST=1`).

## Commit message convention

The generator relies on the HyperFleet commit convention `HYPERFLEET-### - type: description`. The more consistently commits follow it (with a JIRA key and a conventional type), the more complete the generated notes.

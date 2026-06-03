#!/usr/bin/env python3
"""
Deterministic release-notes generator (Phase 1, no LLM).

Reads RELEASE_MANIFEST.yaml -> per-component target versions. Resolves each
component's baseline (previous-release manifest if given, else its previous GA
tag) -> per-component tag range -> parses commits -> categorizes
(feat/fix/perf; CVE -> Security) -> dedups (by ticket; CVE by CVE-id) ->
pulls image digests from Quay -> renders the RELEASE-NOTES draft on stdout.

The draft is a starting point for human curation: the Overview, Known Issues,
Upgrade Notes and dates are left as placeholders. Non-conforming commits are
listed on stderr for review.

Env:
  MANIFEST       current manifest (default: <repos-root>/hyperfleet-release/RELEASE_MANIFEST.yaml)
  PREV_MANIFEST  optional previous-release manifest (else: previous GA git tag)
  REPOS_ROOT     dir holding the component repos (default: discovered by walking
                 up from the current directory until a dir containing
                 hyperfleet-api is found)
  NO_DIGEST=1    skip Quay digest lookups (offline / no skopeo)

Requires: git, and skopeo for digests (unless NO_DIGEST=1). Component repos must
be checked out under REPOS_ROOT with up-to-date tags.
"""
import re, subprocess, os, sys, json
from collections import OrderedDict


def find_root():
    """Resolve the directory holding the component repos (REPOS_ROOT, else walk up to find hyperfleet-api)."""
    env = os.environ.get("REPOS_ROOT")
    if env:
        return os.path.abspath(env)
    d = os.getcwd()
    while True:
        if os.path.isdir(os.path.join(d, "hyperfleet-api")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            sys.exit("ERROR: could not locate the component repos — no 'hyperfleet-api' "
                     "directory found in the current directory or any parent. Set REPOS_ROOT "
                     "to the directory that holds hyperfleet-api / -sentinel / -adapter, or run "
                     "from within that tree.")
        d = parent


ROOT = find_root()
MANIFEST = os.environ.get("MANIFEST") or os.path.join(ROOT, "hyperfleet-release", "RELEASE_MANIFEST.yaml")
PREV_MANIFEST = os.environ.get("PREV_MANIFEST", "")
REGISTRY = "quay.io/redhat-services-prod/hyperfleet-tenant/hyperfleet"
JIRA = "https://redhat.atlassian.net/browse/"
DISPLAY = {"hyperfleet-api": "API", "hyperfleet-sentinel": "Sentinel", "hyperfleet-adapter": "Adapter"}
COMP_ORDER = ["API", "Sentinel", "Adapter"]

# key (any project, not CVE), optional "- <known type>", then a ":" or "-" separator, then desc.
# Handles:  KEY - type: desc   |   KEY: desc   |   KEY - type - desc
SUBJ = re.compile(
    r'^(?!CVE-)(?P<key>[A-Za-z]{2,}-\d+)\s*'
    r'(?:-\s*(?P<type>feat|fix|perf|chore|tests?|docs?|refactor|ci|build|security)\b\s*)?'
    r'[-:]\s*(?P<desc>.*)$', re.I)
CVE = re.compile(r'CVE-\d{4}-\d+', re.I)
BOT = re.compile(r'^(Update |Migrate config|Initial commit|Merge |Red Hat Konflux)', re.I)
TYPO = {"HYPERLFEET": "HYPERFLEET", "HYPEFLEET": "HYPERFLEET"}
CAT = {"feat": "Features", "fix": "Bug Fixes", "perf": "Performance"}
CAT_RANK = {"Features": 0, "Bug Fixes": 1, "Performance": 2}  # precedence when one ticket spans types
SEMVER = re.compile(r'^v(\d+)\.(\d+)\.(\d+)$')


def sh(*args, check=True):
    """Run a command and return its stdout; exit on non-zero unless check=False."""
    r = subprocess.run(args, text=True, capture_output=True)
    if check and r.returncode != 0:
        sys.exit(f"ERROR: command failed (exit {r.returncode}): {' '.join(args)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def parse_manifest(path):
    """Minimal parser: `release: "X.Y"` and a `components:` map of repo -> version."""
    rel, comps = None, OrderedDict()
    if not path or not os.path.exists(path):
        return rel, comps
    in_comps = False
    for line in open(path):
        m = re.match(r'\s*release:\s*"?([^"\n]+)"?', line)
        if m and not in_comps:
            rel = m.group(1).strip(); continue
        if re.match(r'\s*components:\s*$', line):
            in_comps = True; continue
        if in_comps:
            m = re.match(r'\s+([\w-]+):\s*"?([^"\n#]+)"?', line)
            if m:
                comps[m.group(1)] = m.group(2).strip()
            elif line.strip() and not line.startswith((" ", "\t")):
                in_comps = False
    return rel, comps


def target_semver(v):
    """Parse a version like 'v0.3.0-rc1' / '0.3.0' into a (major, minor, patch) tuple."""
    m = re.match(r'v?(\d+)\.(\d+)\.(\d+)', v)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def prev_ga_tag(repo, target_v):
    """Return the highest GA tag (vX.Y.Z) in repo that is older than target_v, or None."""
    p = os.path.join(ROOT, repo)
    sh("git", "-C", p, "fetch", "origin", "--tags", "-q", check=False)  # best-effort tag refresh
    tv = target_semver(target_v)
    gas = []
    for t in sh("git", "-C", p, "tag", "--list", "v*").splitlines():
        m = SEMVER.match(t.strip())
        if m:
            sv = tuple(int(x) for x in m.groups())
            if sv < tv:
                gas.append((sv, t.strip()))
    return max(gas)[1] if gas else None


def commits(repo, base, target):
    """Return the non-merge commit subjects in repo over the base..target tag range."""
    p = os.path.join(ROOT, repo)
    rng = f"{base}..{target}" if base else target
    out = subprocess.run(["git", "-C", p, "log", rng, "--no-merges", "--format=%s"],
                         text=True, capture_output=True)
    if out.returncode != 0:
        sys.exit(f"ERROR: git log {rng} failed in {repo} (exit {out.returncode}) — "
                 f"would have silently dropped this component's changes.\n"
                 f"{out.stderr.strip() or out.stdout.strip()}\n"
                 f"Check that both tags exist: git -C {p} fetch origin --tags")
    return [l for l in out.stdout.splitlines() if l.strip()]


def inspect(repo, version):
    """Return {'digest': ..., 'created': 'YYYY-MM-DD' or None} for the released image."""
    if os.environ.get("NO_DIGEST"):
        return {"digest": "TBD", "created": None}
    tag = version.lstrip("v")
    ref = f"docker://{REGISTRY}/{repo}:{tag}"
    out = subprocess.run(["skopeo", "inspect", ref], text=True, capture_output=True)
    if out.returncode != 0:
        sys.exit(f"ERROR: skopeo inspect failed (exit {out.returncode}) for {ref}\n"
                 f"{out.stderr.strip()}\nIf the images aren't released yet, re-run with NO_DIGEST=1.")
    try:
        info = json.loads(out.stdout)
    except Exception as e:
        sys.exit(f"ERROR: could not parse skopeo output for {ref}: {e}\n{out.stdout[:200]}")
    digest = info.get("Digest")
    if not digest:
        sys.exit(f"ERROR: no Digest in skopeo output for {ref}")
    created = info.get("Created") or (info.get("Labels") or {}).get("org.opencontainers.image.created") or ""
    return {"digest": digest, "created": created[:10] or None}


def normkey(k):
    """Normalize a JIRA key: uppercase and fix known project typos (e.g. HYPERLFEET -> HYPERFLEET)."""
    pre, num = k.upper().split("-", 1)
    return f"{TYPO.get(pre, pre)}-{num}"


def keynum(k):
    """Return the numeric part of a JIRA key (HYPERFLEET-1099 -> 1099) for sorting."""
    return int(k.split("-")[1])


# ---- resolve versions + ranges ----
release, targets = parse_manifest(MANIFEST)
if not release:
    sys.exit(f"ERROR: missing 'release' in manifest {MANIFEST}")
if not targets:
    sys.exit(f"ERROR: no components in manifest {MANIFEST}")
# Component names become filesystem paths (os.path.join(ROOT, repo)) and git -C
# targets; versions become skopeo image tags and git refs. All are passed as argv
# (never via a shell), but validate them at the source anyway: keep names in the
# hyperfleet-* namespace so a path stays under ROOT, and keep versions to semver
# so a typo fails clearly here instead of as an opaque skopeo/git error.
for repo, tv in targets.items():
    if not re.fullmatch(r"hyperfleet-[a-z0-9-]+", repo):
        sys.exit(f"ERROR: invalid component name in manifest: {repo!r} "
                 "(expected 'hyperfleet-<name>')")
    if not re.fullmatch(r"v?\d+\.\d+\.\d+(-[A-Za-z0-9.-]+)?", tv):
        sys.exit(f"ERROR: invalid version for {repo} in manifest: {tv!r} "
                 "(expected semver like 'v0.3.0' or '0.3.0-rc1')")
_, prev_targets = parse_manifest(PREV_MANIFEST) if PREV_MANIFEST else (None, {})

ranges = OrderedDict()
for repo, tv in targets.items():
    base = ("v" + prev_targets[repo].lstrip("v")) if repo in prev_targets else prev_ga_tag(repo, tv)
    ranges[repo] = (base, tv if tv.startswith("v") else "v" + tv)

# ---- collect + categorize ----
tickets, cves = OrderedDict(), OrderedDict()
dropped, nonconforming = 0, []
for repo, (base, target) in ranges.items():
    comp = DISPLAY.get(repo, repo)
    for subj in commits(repo, base, target):
        cve = CVE.search(subj); m = SUBJ.match(subj)
        if not m:
            if cve:
                cid = cve.group(0).upper()
                cves.setdefault(cid, {"desc": subj.strip(), "components": set(), "tickets": set()})["components"].add(comp)
            elif BOT.match(subj):
                dropped += 1
            else:
                nonconforming.append((comp, subj))
            continue
        key, typ, desc = normkey(m.group("key")), (m.group("type") or "").lower(), m.group("desc").strip()
        if cve:
            cid = cve.group(0).upper()
            e = cves.setdefault(cid, {"desc": desc, "components": set(), "tickets": set()})
            e["components"].add(comp); e["tickets"].add(key); continue
        if typ in CAT:
            e = tickets.setdefault(key, {"desc": desc, "category": CAT[typ], "components": set()})
            e["components"].add(comp)
            # One ticket can span commits of different types across repos; choose the
            # category by precedence (Features > Bug Fixes > Performance) so it's stable
            # regardless of commit/repo iteration order rather than first-write-wins.
            if CAT_RANK[CAT[typ]] < CAT_RANK[e["category"]]:
                e["category"], e["desc"] = CAT[typ], desc
        else:
            dropped += 1


def ordered_comps(s):
    """Component names in canonical order (COMP_ORDER first), then any extra hyperfleet-* names sorted."""
    return [c for c in COMP_ORDER if c in s] + sorted(x for x in s if x not in COMP_ORDER)


def comps(s):
    """Render a set of component names in canonical order as a comma-separated string."""
    return ", ".join(ordered_comps(s))


prev_max = max((target_semver(b) for b, _ in ranges.values() if b), default=(0, 0, 0))
rel_mm = tuple(int(x) for x in (release or "0.0").split(".")[:2])
rtype = "minor" if rel_mm != prev_max[:2] else "patch (z-stream)"

inspects = {repo: inspect(repo, target) for repo, (base, target) in ranges.items()}
digests = {repo: inspects[repo]["digest"] for repo in inspects}
_dates = [inspects[repo]["created"] for repo in inspects if inspects[repo]["created"]]
release_date = max(_dates) if _dates else "TBD"   # latest image build date across components

# --json: emit the grounded structured data for an LLM curation layer to enrich.
if "--json" in sys.argv or os.environ.get("JSON"):
    data = {
        "release": release, "type": rtype, "date": release_date,
        "ranges": {r: {"base": b, "target": t} for r, (b, t) in ranges.items()},
        "components": {r: {"version": t, "image": f"{REGISTRY}/{r}:{t.lstrip('v')}", "digest": digests[r]}
                       for r, (b, t) in ranges.items()},
        "security": [{"cve": cid, "desc": e["desc"], "tickets": sorted(e["tickets"], key=keynum),
                      "components": ordered_comps(e["components"])}
                     for cid, e in sorted(cves.items())],
        "tickets": [{"key": k, "desc": v["desc"], "category": v["category"],
                     "components": ordered_comps(v["components"])}
                    for k, v in sorted(tickets.items(), key=lambda kv: keynum(kv[0]))],
        "nonconforming": [{"component": c, "subject": s} for c, s in nonconforming],
    }
    print(json.dumps(data, indent=2))
    sys.exit(0)

o = ["---", f'release: "{release}"', f"date: {release_date}", f"type: {rtype}", "components:"]
for repo, (base, target) in ranges.items():
    o.append(f"  {repo}: {{ version: {target}, image: {REGISTRY}/{repo}:{target.lstrip('v')}, digest: {digests[repo]} }}")
o += ["---", f"# HyperFleet Release {release} — Release Notes", "",
      f"**Version:** {release}  ", f"**Release Date:** {release_date}  ", f"**Type:** {rtype}  ", "",
      "> **IMPORTANT**: This MVP release is for exploration and evaluation only. "
      "Do not use in production environments.", "",
      "## Overview", "", "_(summary prose — human-curated)_", "",
      "## Component Versions", "",
      "| Component | Version | Container Image | SHA256 Digest |",
      "|-----------|---------|-----------------|---------------|"]
for repo, (base, target) in ranges.items():
    o.append(f"| **HyperFleet {DISPLAY.get(repo, repo)}** | {target} | "
             f"`{REGISTRY}/{repo}:{target.lstrip('v')}` | `{digests[repo]}` |")
o.append("")

if cves:
    o += ["## Security", ""]
    for cid, e in sorted(cves.items()):
        refs = ", ".join(f"[{k}]({JIRA}{k})" for k in sorted(e["tickets"], key=keynum)) or "—"
        o.append(f"- **{cid}**: {e['desc']} ({comps(e['components'])}) — {refs}")
    o.append("")
for section in ["Features", "Bug Fixes", "Performance"]:
    items = [(k, v) for k, v in tickets.items() if v["category"] == section]
    if not items:
        continue
    o += [f"## {section}", ""]
    for k, v in sorted(items, key=lambda kv: keynum(kv[0])):
        o.append(f"- {v['desc']} ({comps(v['components'])}) [{k}]({JIRA}{k})")
    o.append("")
o += ["## Known Issues", "", "_(human)_", "", "## Upgrade Notes", "", "_(human)_", "",
      "## Support", "", "- **Issues**: JIRA HYPERFLEET project or component repositories",
      "- **Community**: #forum-hyperfleet", ""]

print("\n".join(o))
print("\n--- diagnostics ---", file=sys.stderr)
for repo, (base, target) in ranges.items():
    print(f"  {repo}: {base or '(root)'}..{target}", file=sys.stderr)
print(f"tickets: {len(tickets)} | CVEs: {len(cves)} | dropped: {dropped} | "
      f"non-conforming: {len(nonconforming)}", file=sys.stderr)
for comp, s in nonconforming[:15]:
    print(f"  [{comp}] {s}", file=sys.stderr)

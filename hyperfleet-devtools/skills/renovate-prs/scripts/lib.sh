#!/usr/bin/env bash
# Shared helpers for collect-data.sh.
#
# Kept free of network calls and of $CLAUDE_* variables so the test suite can
# source this file directly.

# Bot accounts that open dependency update PRs in the HyperFleet repositories.
#
#   MintMaker (Konflux)  app/red-hat-konflux-kflux-prd-rh02
#   Renovate (hosted)    app/renovate
#
# MintMaker only scans repositories that have a Konflux Component, so the
# repositories without one are onboarded to the hosted Renovate app instead.
# The two are mutually exclusive per repository; see the architecture ADR.
# shellcheck disable=SC2034  # consumed by collect-data.sh
MINTMAKER_AUTHOR_PREFIX="app/red-hat-konflux"
RENOVATE_AUTHOR_PREFIX="app/renovate"
BOT_AUTHOR_REGEX='^app/(red-hat-konflux|renovate)'

# The shared preset holds the review policy, the schedule and the timezone.
PRESET_NAME="github>openshift-hyperfleet/renovate-config"
# shellcheck disable=SC2034  # consumed by collect-data.sh
PRESET_REPO="openshift-hyperfleet/renovate-config"
PRESET_FILE="default.json"

# True when the login belongs to a dependency bot, so the collector ignores
# human-authored dependency work.
is_bot_author() {
  local login="$1"
  [[ "$login" =~ $BOT_AUTHOR_REGEX ]]
}

# Which automation platform opened the PR, derived from the bot identity.
platform_for_author() {
  local login="$1"
  if [[ "$login" == "$RENOVATE_AUTHOR_PREFIX"* ]]; then
    echo "renovate"
  else
    echo "mintmaker"
  fi
}

# Best-effort bump type for display and for the unlabeled fallback. The review
# policy labels stay authoritative whenever they are present.
classify_bump() {
  local branch="$1" title="$2"

  # Order matters. Security wins over every other class because a vulnerability
  # fix needs a human to confirm the advisory before it merges, whatever the
  # version transition looks like.
  if [[ "$branch" == *"-vulnerability"* ]] || echo "$title" | grep -qi '\[security\]'; then
    echo "security"
  elif echo "$title" | grep -qi "konflux references major"; then
    # The preset groups major Tekton reference bumps as "Konflux references
    # major"; it must not fall into the auto-lgtm references class.
    echo "major"
  elif [[ "$branch" == *"references/"* ]] || echo "$title" | grep -qi "konflux references"; then
    echo "references"
  elif [[ "$branch" == *"major-"* ]] || echo "$title" | grep -qiE 'to v[0-9]+$'; then
    echo "major"
  elif [[ "$branch" == *"-digest"* ]] || echo "$title" | grep -qi "digest"; then
    echo "digest"
  elif [[ "$branch" == *"docker-image"* ]] || echo "$title" | grep -qiE "docker (image|tag)"; then
    echo "docker"
  elif [[ "$branch" == *"minorpatch"* ]] \
    || [[ "$branch" == *"minor-patch"* ]] \
    || [[ "$branch" == *"non-major"* ]] \
    || [[ "$branch" == *"monorepo"* ]] \
    || echo "$title" | grep -qiE "minor/patch|non-major|monorepo"; then
    echo "minor/patch"
  else
    # Renovate names grouped branches after the target series (for example
    # renovate/golang.org-x-oauth2-0.x) and the new major version cannot be
    # derived from that name. The policy labels, not this value, decide the
    # action for those PRs.
    echo "unknown"
  fi
}

# The shared preset labels every bot PR it opens:
#
#   lgtm + approved          auto-approved update, merge once CI is green
#   manual-review-required   a human must review it first
#   ok-to-test               Prow is allowed to run CI on the PR
#
# The labels are authoritative: a classification guess must never turn a
# manual-review-required PR into an auto-lgtm one.
review_policy() {
  local labels="$1"
  if [[ ",$labels," == *",manual-review-required,"* ]]; then
    echo "manual"
  elif [[ ",$labels," == *",lgtm,"* ]]; then
    echo "auto-approved"
  else
    echo "unlabeled"
  fi
}

# Read the schedule of a Renovate config, which may be a string or an array.
json_schedule() {
  local config="$1"
  [ -n "$config" ] || return 0
  jq -r 'if (.schedule // null) == null then ""
         elif (.schedule | type) == "array" then (.schedule | join(", "))
         else (.schedule | tostring) end' <<<"$config" 2>/dev/null || true
}

# True when the config inherits the shared HyperFleet preset.
extends_preset() {
  local config="$1"
  [ -n "$config" ] || return 1
  jq -r --arg preset "$PRESET_NAME" \
    '[(.extends // [])] | flatten | any(. == $preset)' <<<"$config" 2>/dev/null | grep -qx true
}

# Resolve the effective schedule for a repository: its own renovate.json first,
# then the shared preset when the repository only extends it. Prints
# "<schedule>\t<timezone>".
schedule_of() {
  local config="$1" preset="$2" schedule="" timezone=""

  if [ -n "$config" ]; then
    schedule=$(json_schedule "$config")
    timezone=$(jq -r '.timezone // ""' <<<"$config" 2>/dev/null || true)
  fi

  if extends_preset "$config"; then
    if [ -n "$preset" ]; then
      if [ -z "$schedule" ]; then
        schedule=$(json_schedule "$preset")
      fi
      # The preset is inherited wholesale, so its timezone applies even when
      # the repository overrides the schedule.
      if [ -z "$timezone" ]; then
        timezone=$(jq -r '.timezone // ""' <<<"$preset" 2>/dev/null || true)
      fi
    elif [ -z "$schedule" ]; then
      # Without the preset there is no way to know the window. Report the cause
      # instead of a generic "unknown" so the report can explain the gap.
      schedule="preset-unreadable"
    fi
  fi

  [ -n "$schedule" ] || schedule="unknown"
  [ -n "$timezone" ] || timezone="unknown"
  printf '%s\t%s\n' "$schedule" "$timezone"
}

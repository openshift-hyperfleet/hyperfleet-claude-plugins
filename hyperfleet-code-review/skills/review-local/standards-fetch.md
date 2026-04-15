# Standards fetch

Fetch all HyperFleet standards and component docs in a single Bash call. Run this
when the `gh` CLI is available and authenticated (see Dynamic context).

```bash
# Detect portable base64 decode flag (GNU uses --decode/-d, BSD/macOS uses -D)
if echo "" | base64 --decode 2>/dev/null; then
  B64D="base64 --decode"
else
  B64D="base64 -D"
fi

STANDARDS_FILES=()
while IFS= read -r line; do
  STANDARDS_FILES+=("$line")
done < <(gh api repos/openshift-hyperfleet/architecture/contents/hyperfleet/standards \
  -q '.[].name | select(endswith(".md"))' 2>/dev/null)

if [ ${#STANDARDS_FILES[@]} -eq 0 ]; then
  echo "===== FETCH FAILURES ====="
  echo "Failed to list standards directory via gh api"
fi

FAILED_STANDARDS=""
for FILE in "${STANDARDS_FILES[@]}"; do
  if [[ ! "$FILE" =~ ^[a-zA-Z0-9._-]+\.md$ ]]; then
    printf '===== SKIPPED (invalid filename): %s =====\n' "$FILE" && continue
  fi
  printf '===== %s =====\n' "$FILE"
  CONTENT=$(gh api "repos/openshift-hyperfleet/architecture/contents/hyperfleet/standards/$FILE" \
    -q '.content' 2>/dev/null); GH_EXIT=$?
  if [ $GH_EXIT -ne 0 ] || [ -z "$CONTENT" ]; then
    FAILED_STANDARDS="$FAILED_STANDARDS $FILE"
  else
    echo "$CONTENT" | $B64D
  fi
  echo ""
done

if [ -n "$FAILED_STANDARDS" ]; then
  echo "===== FETCH FAILURES ====="
  echo "Failed to fetch:$FAILED_STANDARDS"
fi

RAW_DIR="$(basename "$(pwd)")"
if [[ ! "$RAW_DIR" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  printf '===== SKIPPED component docs (invalid directory name): %s =====\n' "$RAW_DIR"
  COMPONENT_FILES=()
else
  COMPONENT="${RAW_DIR#hyperfleet-}"
  COMPONENT_FILES=()
  while IFS= read -r line; do
    COMPONENT_FILES+=("$line")
  done < <(gh api "repos/openshift-hyperfleet/architecture/contents/hyperfleet/components/$COMPONENT" \
    -q '.[].name | select(endswith(".md"))' 2>/dev/null)
fi

if [ ${#COMPONENT_FILES[@]} -gt 0 ]; then
  FAILED_COMPONENTS=""
  for FILE in "${COMPONENT_FILES[@]}"; do
    if [[ ! "$FILE" =~ ^[a-zA-Z0-9._-]+\.md$ ]]; then
      printf '===== SKIPPED (invalid filename): %s =====\n' "$FILE" && continue
    fi
    printf '===== component/%s/%s =====\n' "$COMPONENT" "$FILE"
    CONTENT=$(gh api "repos/openshift-hyperfleet/architecture/contents/hyperfleet/components/$COMPONENT/$FILE" \
      -q '.content' 2>/dev/null); GH_EXIT=$?
    if [ $GH_EXIT -ne 0 ] || [ -z "$CONTENT" ]; then
      FAILED_COMPONENTS="$FAILED_COMPONENTS $FILE"
    else
      echo "$CONTENT" | $B64D
    fi
    echo ""
  done
  if [ -n "$FAILED_COMPONENTS" ]; then
    echo "===== FETCH FAILURES ====="
    echo "Failed to fetch component docs:$FAILED_COMPONENTS"
  fi
fi
```

If the fetch fails, note it in the setup summary and continue without standards.
If gh auth status was "NOT authenticated", include a hint: "Run `gh auth login` to enable standards fetching."

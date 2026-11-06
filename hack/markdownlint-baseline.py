"""Filter official markdownlint-cli2 JSON findings against reviewed legacy debt."""

import hashlib
import json
from pathlib import Path
import sys


def compare(findings, baseline):
    current, failures = {}, []
    accepted = 0
    for finding in findings:
        file = finding["fileName"]
        source = Path(file).read_text(encoding="utf-8").split("\n")[finding["lineNumber"] - 1]
        payload = [source, finding["errorDetail"], finding["errorContext"]]
        digest = hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode()).hexdigest()
        key = finding["ruleNames"][0] + ":" + digest
        counts = current.setdefault(file, {})
        counts[key] = counts.get(key, 0) + 1
        if counts[key] <= baseline["files"].get(file, {}).get(key, 0):
            accepted += 1
        else:
            failures.append(f"{file}:{finding['lineNumber']} "
                            f"{finding['ruleNames'][0]} {finding['ruleDescription']}")
    return current, failures, accepted


def main():
    results, status, *options = sys.argv[1:]
    findings = json.loads(Path(results).read_text())
    # Missing/malformed output and inconsistent statuses are operational failures.
    if not isinstance(findings, list) or int(status) != int(bool(findings)):
        raise ValueError("Invalid markdownlint-cli2 output or exit status")
    path = Path(".markdownlint-baseline.json")
    write = options == ["--write-baseline"]
    baseline = {"version": 1, "files": {}} if write else json.loads(path.read_text())
    if baseline.get("version") != 1 or not isinstance(baseline.get("files"), dict):
        raise ValueError("Invalid Markdown baseline")
    for counts in baseline["files"].values():
        if not isinstance(counts, dict) or any(
                type(count) is not int or count < 1 for count in counts.values()):
            raise ValueError("Invalid Markdown baseline counts")
    current, failures, accepted = compare(findings, baseline)
    if write:
        path.write_text(json.dumps({"version": 1, "files": current}, indent=2) + "\n")
        print("Wrote Markdown baseline; review its diff before committing.")
        return 0
    print(f"Markdown baseline: {accepted} existing violations, {len(failures)} new violations.")
    for failure in failures:
        print(failure, file=sys.stderr)
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())

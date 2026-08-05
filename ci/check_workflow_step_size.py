#!/usr/bin/env python3
"""Fail if a workflow step's script/run value approaches GitHub's size ceiling.

GitHub caps an individual step input at ~21 000 characters. Over it, the whole
workflow becomes unparseable: every run for the push fails in 0s, the run is
named after the file path instead of the workflow, and there is no annotation
saying why. Nothing in CI can catch that — an invalid workflow never runs — so
the check has to happen before the commit.

We hit it for real: a 33-line comment added to the deploy job's ssh `script:`
pushed it from 20 484 to 22 024 characters and broke main until the revert.

Run: python ci/check_workflow_step_size.py [files...]
"""

import sys

import yaml

# GitHub's ceiling is ~21000; warn earlier so a normal edit has somewhere to go.
HARD_LIMIT = 21000
WARN_AT = 20000


def step_values(workflow):
    """Yield (job, step name, input name, value) for every long-form step input."""
    for job_name, job in (workflow.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            name = step.get("name") or step.get("uses") or "<unnamed>"
            candidates = dict(step.get("with") or {})
            candidates["run"] = step.get("run")
            for key, value in candidates.items():
                if isinstance(value, str):
                    yield job_name, name, key, value


def check(path):
    """Return (errors, warnings) for one workflow file."""
    with open(path, encoding="utf-8") as handle:
        workflow = yaml.safe_load(handle)
    errors, warnings = [], []
    if not isinstance(workflow, dict):
        return errors, warnings
    for job_name, step_name, key, value in step_values(workflow):
        size = len(value)
        where = f"{path}: {job_name} / {step_name} / {key} = {size} chars"
        if size > HARD_LIMIT:
            errors.append(f"{where} (over GitHub's {HARD_LIMIT} ceiling)")
        elif size > WARN_AT:
            warnings.append(f"{where} (only {HARD_LIMIT - size} left)")
    return errors, warnings


def main(paths):
    errors, warnings = [], []
    for path in paths:
        file_errors, file_warnings = check(path)
        errors += file_errors
        warnings += file_warnings
    for line in warnings:
        print(f"warning: {line}")
    for line in errors:
        print(f"error: {line}")
    if errors:
        print("\nTrim the step before committing — over the limit GitHub rejects")
        print("the whole workflow and every run fails instantly with no reason given.")
        return 1
    return 0


def demo():
    """Self-check: the limits are enforced in the right direction."""
    ok = {"jobs": {"j": {"steps": [{"name": "s", "with": {"script": "x" * 100}}]}}}
    over = {"jobs": {"j": {"steps": [{"name": "s", "with": {"script": "x" * 21001}}]}}}
    near = {"jobs": {"j": {"steps": [{"name": "s", "run": "x" * 20500}]}}}
    import tempfile

    def run(doc):
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
            yaml.safe_dump(doc, fh)
            return check(fh.name)

    assert run(ok) == ([], []), "a small step must pass cleanly"
    errs, warns = run(over)
    assert errs and not warns, f"an oversized step must error, got {errs} {warns}"
    errs, warns = run(near)
    assert warns and not errs, f"a near-limit step must warn only, got {errs} {warns}"
    print("self-check OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--self-check"]:
        demo()
        sys.exit(0)
    sys.exit(main(args or [".github/workflows/ci.yml"]))

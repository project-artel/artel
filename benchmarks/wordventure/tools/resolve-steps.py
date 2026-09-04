#!/usr/bin/env python3
"""Turn the `tc` numbers in the step templates into the database ids `artel` handed back.

The step templates under `scenarios/` carry `tc` — the number the design document gave a
test case (9101, 9139, ...). That is not a database id. `artel case create` assigns the real
ids, and it reports them positionally: the i-th entry of `results` is the i-th entry of
`cases.json`. This script joins those two lists and rewrites the templates.

Usage:
    artel case create --project <id> --file cases.json --json > build/created-cases.json
    python3 tools/resolve-steps.py --cases cases.json \\
        --created build/created-cases.json --out build

It writes `build/case-ids.json` (the `tc` -> database id map, for the record) and one
`build/<name>.steps.json` per template. Those output files are what `artel scenario create
--steps` reads; the templates themselves are deliberately not valid CLI input, because
`tc` is not a field the CLI accepts and feeding a template directly fails loudly instead
of creating case-less steps.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

STEP_FIELDS = ("action", "case_id", "hint", "input")


def load_json(path: pathlib.Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SystemExit(f"could not read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not valid JSON: {error}") from error


def build_case_id_map(cases: list, created: dict) -> dict[str, int]:
    """Join `cases.json` and the `case create --json` batch payload by array position."""
    results = created.get("results")
    if not isinstance(results, list):
        raise SystemExit(
            "the --created file has no `results` array. It must be the stdout of "
            "`artel case create --json` given a JSON array of cases."
        )
    if len(results) != len(cases):
        raise SystemExit(
            f"--created reports {len(results)} results but --cases holds {len(cases)} cases. "
            "The two must be the same list in the same order."
        )

    by_index = {}
    for result in results:
        index = result.get("index")
        if not isinstance(index, int):
            raise SystemExit(f"a result entry has no integer `index`: {result!r}")
        by_index[index] = result

    case_ids: dict[str, int] = {}
    for index, case in enumerate(cases):
        tc = case.get("tc")
        if not isinstance(tc, int):
            raise SystemExit(f"cases.json[{index}] has no integer `tc`.")
        result = by_index.get(index)
        if result is None:
            raise SystemExit(f"--created has no result at index {index} (TC {tc}).")
        if result.get("created") is None:
            reason = (result.get("error") or {}).get("message", "no reason reported")
            raise SystemExit(f"TC {tc} (index {index}) was not created: {reason}")
        case_ids[str(tc)] = int(result["created"]["id"])
    return case_ids


def resolve(steps: list, case_ids: dict[str, int], where: str) -> list[dict]:
    resolved = []
    for position, step in enumerate(steps, start=1):
        unknown = set(step) - {"action", "tc", "hint", "input"}
        if unknown:
            raise SystemExit(f"{where} step {position} has unknown fields: {sorted(unknown)}")
        tc = step.get("tc")
        if tc is None:
            case_id = None
        else:
            case_id = case_ids.get(str(tc))
            if case_id is None:
                raise SystemExit(
                    f"{where} step {position} points at TC {tc}, which is not in cases.json."
                )
        resolved.append(
            {
                "action": step["action"],
                "case_id": case_id,
                "hint": step.get("hint"),
                "input": step.get("input"),
            }
        )
    return resolved


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=pathlib.Path, default=here / "cases.json")
    parser.add_argument("--created", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, default=here / "build")
    parser.add_argument("--scenarios", type=pathlib.Path, default=here / "scenarios")
    args = parser.parse_args()

    cases = load_json(args.cases)
    if not isinstance(cases, list):
        raise SystemExit(f"{args.cases} must hold a JSON array of test cases.")
    created = load_json(args.created)
    if not isinstance(created, dict):
        raise SystemExit(f"{args.created} must hold the `case create --json` object.")

    case_ids = build_case_id_map(cases, created)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "case-ids.json").write_text(
        json.dumps(case_ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    templates = sorted(args.scenarios.glob("*.steps.json"))
    if not templates:
        raise SystemExit(f"no *.steps.json templates under {args.scenarios}")
    for template in templates:
        steps = load_json(template)
        if not isinstance(steps, list):
            raise SystemExit(f"{template} must hold a JSON array of steps.")
        resolved = resolve(steps, case_ids, template.name)
        target = args.out / template.name
        target.write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{target} — {len(resolved)} steps")

    print(f"{args.out / 'case-ids.json'} — {len(case_ids)} test cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())

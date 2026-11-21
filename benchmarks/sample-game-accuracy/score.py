import argparse
import json
from collections import defaultdict
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def percentage(numerator, denominator):
    return f"{numerator / denominator:.1%}" if denominator else None


def score(game, verdict_file):
    cases = read(game / "cases.json")
    key = read(game / "answer-key.json")
    truth = {row["tc"]: row["expected_passed"] for row in key}
    case_ids = {row["tc"] for row in cases}
    if len(cases) != 20 or len(case_ids) != 20 or len(key) != 20 or truth.keys() != case_ids:
        raise ValueError(f"{game.name}: expected 20 unique, matching TC IDs")
    if sum(value is True for value in truth.values()) != 10 or sum(
        value is False for value in truth.values()
    ) != 10:
        raise ValueError(f"{game.name}: expected ten true and ten false labels")

    cases_by_id = {row["tc"]: row for row in cases}
    pairs = defaultdict(list)
    for row in key:
        pairs[row["pair"]].append(row)
    for name, pair in pairs.items():
        if len(pair) != 2 or pair[0]["expected_passed"] == pair[1]["expected_passed"]:
            raise ValueError(f"{game.name}: {name} needs one true and one false case")
        first, second = [cases_by_id[row["tc"]] for row in pair]
        if any(first[field] != second[field] for field in ("scene", "precondition", "step")):
            raise ValueError(f"{game.name}: {name} uses different setup or actions")
        for row in pair:
            matches = cases_by_id[row["tc"]]["expectedValue"] == row["observation"]
            if matches != row["expected_passed"]:
                raise ValueError(f"{game.name}: TC {row['tc']} disagrees with the key")

    verdicts = {}
    for row in read(verdict_file) if verdict_file.exists() else []:
        tc = row["tc"]
        if tc not in truth or tc in verdicts:
            raise ValueError(f"{game.name}: unknown or duplicate TC {tc}")
        verdict = row["verdict"]
        if verdict not in {"PASS", "FAIL", "BLOCKED", "ERROR"}:
            raise ValueError(f"{game.name}: unsupported verdict {verdict!r}")
        verdicts[tc] = verdict

    counts = dict(TP=0, TN=0, FP=0, FN=0, BLOCKED=0, ERROR=0, MISSING=0)
    for tc, expected in truth.items():
        verdict = verdicts.get(tc, "MISSING")
        if verdict == "PASS":
            counts["TP" if expected else "FP"] += 1
        elif verdict == "FAIL":
            counts["FN" if expected else "TN"] += 1
        else:
            counts[verdict] += 1

    negative = counts["FP"] + counts["TN"]
    positive = counts["FN"] + counts["TP"]
    complete = negative + positive == len(truth)
    return {
        **counts,
        "coverage": percentage(negative + positive, len(truth)),
        "complete": complete,
        "false_positive_rate": percentage(counts["FP"], negative) if complete else None,
        "false_negative_rate": percentage(counts["FN"], positive) if complete else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("verdict_dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    report = {
        key.parent.name: score(key.parent, args.verdict_dir / f"{key.parent.name}.json")
        for key in sorted(root.glob("*/answer-key.json"))
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

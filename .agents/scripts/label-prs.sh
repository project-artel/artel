#!/usr/bin/env bash
#
# Backfill assignee and label on every GitHub PR across the ARTEL repositories.
#
#   assignee : the PR author
#   label    : derived from the conventional-commit prefix in the PR title
#
#     feat      -> enhancement      chore              -> chore
#     fix       -> bug              refactor / refacor -> refactor
#     docs      -> documentation    infra              -> infra
#
# PRs whose titles predate the convention (`[ARTEL-nnn] ...`, README edits) are
# listed in the OVERRIDES table below and judged individually.
#
# Usage:
#   ./label-prs.sh            # dry run: print the edits that would be made
#   ./label-prs.sh apply      # perform the edits
#
# Requires the `gh` CLI, authenticated against github.com.

set -euo pipefail

ORG=project-artel
REPOS=(artel-agent-server artel-home artel-orchestration-server artel-sdk admin-page)
APPLY="${1:-}"

# Labels this script assigns, beyond the GitHub defaults.
declare -A EXTRA_LABELS=(
  [chore]="fbca04|Maintenance, tooling, or dependency work"
  [refactor]="c2e0c6|Code restructuring without behavior change"
  [infra]="1d76db|Build, CI/CD, or deployment infrastructure"
)

# Titles that carry no conventional-commit prefix, keyed by "<repo>#<number>".
declare -A OVERRIDES=(
  [artel-agent-server#23]=bug
  [artel-orchestration-server#43]=bug
  [artel-sdk#31]=bug
  [artel-agent-server#2]=documentation
  [artel-home#2]=documentation
  [artel-orchestration-server#2]=documentation
  [artel-sdk#2]=documentation
  [artel-sdk#10]=documentation
  [artel-sdk#8]=documentation
  [artel-sdk#7]=documentation
)

label_for() {
  local key="$1" title="$2"
  if [[ -n "${OVERRIDES[$key]:-}" ]]; then
    echo "${OVERRIDES[$key]}"
    return
  fi
  case "${title,,}" in
    docs*)              echo documentation;;
    fix*)               echo bug;;
    chore*)             echo chore;;
    refactor*|refacor*) echo refactor;;
    infra*)             echo infra;;
    *)                  echo enhancement;;
  esac
}

ensure_labels() {
  local repo="$1" name spec
  for name in "${!EXTRA_LABELS[@]}"; do
    spec="${EXTRA_LABELS[$name]}"
    gh label create "$name" -R "$ORG/$repo" \
      --color "${spec%%|*}" --description "${spec#*|}" --force >/dev/null
  done
}

edits=0 failures=0

for repo in "${REPOS[@]}"; do
  [[ "$APPLY" == "apply" ]] && ensure_labels "$repo"

  while IFS=$'\t' read -r num author assignees labels title; do
    [[ -z "$num" ]] && continue
    want=$(label_for "$repo#$num" "$title")

    args=()
    [[ -z "$assignees" ]] && args+=(--add-assignee "$author")
    if [[ -z "$labels" ]]; then
      args+=(--add-label "$want")
    elif [[ "$labels" != "$want" ]]; then
      args+=(--remove-label "$labels" --add-label "$want")
    fi
    [[ ${#args[@]} -eq 0 ]] && continue

    edits=$((edits + 1))
    if [[ "$APPLY" == "apply" ]]; then
      if out=$(gh pr edit "$num" -R "$ORG/$repo" "${args[@]}" 2>&1); then
        echo "OK   $repo#$num ${args[*]}"
      else
        failures=$((failures + 1))
        echo "FAIL $repo#$num ${args[*]} :: ${out//$'\n'/ }"
      fi
    else
      echo "DRY  $repo#$num ${args[*]} :: $title"
    fi
  done < <(gh pr list -R "$ORG/$repo" --state all --limit 500 \
             --json number,title,author,assignees,labels \
             -q '.[] | [.number, .author.login, ([.assignees[].login]|join(",")), ([.labels[].name]|join(",")), .title] | @tsv')
done

echo "---"
if [[ "$APPLY" == "apply" ]]; then
  echo "$edits edit(s) attempted, $failures failure(s)"
else
  echo "$edits edit(s) pending; re-run with 'apply' to perform them"
fi

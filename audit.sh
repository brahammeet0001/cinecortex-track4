#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
check () { local label="$1"; shift; if "$@" >/dev/null 2>&1; then echo "DONE     $label"; else echo "MISSING  $label"; fi; }
echo "--- current branch: $(git branch --show-current) ---"
git status -s | head -5
echo
check "A1  converter (schema.py)"              grep -q to_official code/submission/schema.py
check "A2  class list loads (16/98/301)"       python3 -c "import sys; sys.path.insert(0,'code'); from submission.schema import load_classes; a,b,c=load_classes(); assert len(a)==16 and len(b)==98 and len(c)==301"
check "A3  baseline makes 4s windows"          grep -q MIN_LEN code/perception/baseline.py
check "A4  main.py writes official schema"     grep -q to_official code/main.py
check "A5  highlight compiler reads segments"  grep -q segment code/submission/compile_highlights.py
check "A6  local checker is official"          grep -q team_id code/submission/check_output.py
check "A7  test-manifest helper"               test -f code/submission/make_test_manifest.py
check "A8  check_all.sh runs official validator" grep -q validate_official check_all.sh
check "A9  tests present"                      test -f tests/test_segments.py -a -f tests/test_pipeline.py
check "A10 numpy pinned in requirements.txt"   grep -q '^numpy==' requirements.txt
check "A11 official validator in repo"         test -f code/evaluation/validate_official.py
check "A12 README updated"                     grep -q 'official PRISM' README.md
check "B1  real team ID set (not TEAM_ID)"     bash -c '[ -f team_id.txt ] && [ "$(cat team_id.txt)" != "TEAM_ID" ]'
check "B2  no hardcoded video IDs in code"     bash -c '! grep -rnE "test_00|EPIC|P[0-9]{2}_[0-9]+" code run.sh run_batch.sh'
check "B3  fake test outputs removed from git" bash -c '! git ls-files outputs | grep -q test_'
check "B4  Docker image builds and exists"     docker image inspect cinecortex
check "B5  branch pushed to GitHub"            bash -c 'git ls-remote --exit-code --heads origin "$(git branch --show-current)"'
check "B6  merged into main"                   bash -c 'git merge-base --is-ancestor HEAD origin/main'
check "C1  Brahmbir's predict.py present"      test -f code/perception/predict.py
echo
echo "videos in data/videos: $(ls data/videos/*.mp4 2>/dev/null | wc -l | tr -d ' ')"

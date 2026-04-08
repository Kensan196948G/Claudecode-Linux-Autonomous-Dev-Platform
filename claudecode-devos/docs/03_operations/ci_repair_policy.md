# CI Repair Policy

1. Keep each repair to the smallest relevant change.
2. Do not perform unrelated optimization or broad refactors.
3. Narrow likely causes to at most three before editing.
4. Stop autonomous repair when `repair_attempt_limit` is reached.
5. Run focused local checks before pushing when possible.
6. Keep automatic merge disabled until CI and branch policy are confirmed.

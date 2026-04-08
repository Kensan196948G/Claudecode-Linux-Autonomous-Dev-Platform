# Scoring Model

## ROI Score
価値 + 再利用性 - 維持コストを残工数で割る。

## Value Score
estimated_value, strategic_fit, expected_reuse, personal_interest を統合する。

## Stability Score
ci_stability と blocker_risk の逆数で評価する。

## Urgency Score
release_due の近さで評価する。

## Notes
個人開発では personal_interest をゼロにしない。

# Docs Index

ClaudeCode DevOS のルートドキュメント体系です。

## 01_概要（Overview）
- [01_全体像（SystemOverview）](01_概要（Overview）/01_全体像（SystemOverview）.md)
- [02_用語集（Glossary）](01_概要（Overview）/02_用語集（Glossary）.md)
- [03_構成図（ArchitectureDiagram）](01_概要（Overview）/03_構成図（ArchitectureDiagram）.md)

## 02_導入（Installation）
- [01_事前条件（Prerequisites）](02_導入（Installation）/01_事前条件（Prerequisites）.md)
- [02_インストール手順（InstallProcedure）](02_導入（Installation）/02_インストール手順（InstallProcedure）.md)
- [03_初回起動確認（FirstRunCheck）](02_導入（Installation）/03_初回起動確認（FirstRunCheck）.md)

## 03_設定（Configuration）
- [01_環境変数（EnvironmentVariables）](03_設定（Configuration）/01_環境変数（EnvironmentVariables）.md)
- [02_状態管理（StateManagement）](03_設定（Configuration）/02_状態管理（StateManagement）.md)
- [03_プロジェクト台帳（ProjectRegistry）](03_設定（Configuration）/03_プロジェクト台帳（ProjectRegistry）.md)

## 04_運用（Operations）
- [01_日次運用（DailyOperations）](04_運用（Operations）/01_日次運用（DailyOperations）.md)
- [02_週次運用（WeeklyOperations）](04_運用（Operations）/02_週次運用（WeeklyOperations）.md)
- [03_停止と再開（SuspendResume）](04_運用（Operations）/03_停止と再開（SuspendResume）.md)

## 05_監視（Monitoring）
- [01_メトリクス（Metrics）](05_監視（Monitoring）/01_メトリクス（Metrics）.md)
- [02_ダッシュボード監視（DashboardMonitoring）](05_監視（Monitoring）/02_ダッシュボード監視（DashboardMonitoring）.md)
- [03_ログ監視（LogMonitoring）](05_監視（Monitoring）/03_ログ監視（LogMonitoring）.md)

## 06_自動復旧（AutoHealing）
- [01_復旧方針（RecoveryPolicy）](06_自動復旧（AutoHealing）/01_復旧方針（RecoveryPolicy）.md)
- [02_メモリガード（MemoryGuard）](06_自動復旧（AutoHealing）/02_メモリガード（MemoryGuard）.md)
- [03_復旧後確認（PostRecoveryCheck）](06_自動復旧（AutoHealing）/03_復旧後確認（PostRecoveryCheck）.md)

## 07_GitHub連携（GitHubIntegration）
- [01_Issue連携（IssueIntegration）](07_GitHub連携（GitHubIntegration）/01_Issue連携（IssueIntegration）.md)
- [02_PR連携（PullRequestIntegration）](07_GitHub連携（GitHubIntegration）/02_PR連携（PullRequestIntegration）.md)
- [03_ProjectsとActions（ProjectsAndActions）](07_GitHub連携（GitHubIntegration）/03_ProjectsとActions（ProjectsAndActions）.md)

## 08_CI修復（CIRepair）
- [01_失敗検知（FailureDetection）](08_CI修復（CIRepair）/01_失敗検知（FailureDetection）.md)
- [02_修復プロンプト（RepairPrompt）](08_CI修復（CIRepair）/02_修復プロンプト（RepairPrompt）.md)
- [03_修復制限（RepairLimits）](08_CI修復（CIRepair）/03_修復制限（RepairLimits）.md)

## 09_ダッシュボード（Dashboard）
- [01_画面構成（ScreenLayout）](09_ダッシュボード（Dashboard）/01_画面構成（ScreenLayout）.md)
- [02_操作UI（ControlUI）](09_ダッシュボード（Dashboard）/02_操作UI（ControlUI）.md)
- [03_API（DashboardAPI）](09_ダッシュボード（Dashboard）/03_API（DashboardAPI）.md)

## 10_WorkTree（WorkTree）
- [01_分離方針（IsolationPolicy）](10_WorkTree（WorkTree）/01_分離方針（IsolationPolicy）.md)
- [02_開発WorkTree（DevelopmentWorkTree）](10_WorkTree（WorkTree）/02_開発WorkTree（DevelopmentWorkTree）.md)
- [03_修復WorkTree（RepairWorkTree）](10_WorkTree（WorkTree）/03_修復WorkTree（RepairWorkTree）.md)

## 11_クラスタ（Cluster）
- [01_クラスタ構成（ClusterArchitecture）](11_クラスタ（Cluster）/01_クラスタ構成（ClusterArchitecture）.md)
- [02_ジョブ配布（JobDispatch）](11_クラスタ（Cluster）/02_ジョブ配布（JobDispatch）.md)
- [03_冗長化（Failover）](11_クラスタ（Cluster）/03_冗長化（Failover）.md)

## 12_戦略（Strategy）
- [01_スコアリング（Scoring）](12_戦略（Strategy）/01_スコアリング（Scoring）.md)
- [02_選別方針（SelectionPolicy）](12_戦略（Strategy）/02_選別方針（SelectionPolicy）.md)
- [03_戦略モード（StrategyModes）](12_戦略（Strategy）/03_戦略モード（StrategyModes）.md)

## 13_セキュリティ（Security）
- [01_Secrets管理（SecretsManagement）](13_セキュリティ（Security）/01_Secrets管理（SecretsManagement）.md)
- [02_権限（Permissions）](13_セキュリティ（Security）/02_権限（Permissions）.md)
- [03_危険操作（DangerousOperations）](13_セキュリティ（Security）/03_危険操作（DangerousOperations）.md)

## 14_テスト（Testing）
- [01_検証コマンド（ValidationCommands）](14_テスト（Testing）/01_検証コマンド（ValidationCommands）.md)
- [02_CI方針（CIPolicy）](14_テスト（Testing）/02_CI方針（CIPolicy）.md)
- [03_受け入れ基準（AcceptanceCriteria）](14_テスト（Testing）/03_受け入れ基準（AcceptanceCriteria）.md)

## 15_障害対応（IncidentResponse）
- [01_フリーズ対応（FreezeResponse）](15_障害対応（IncidentResponse）/01_フリーズ対応（FreezeResponse）.md)
- [02_CI無限失敗（CIRetryIncident）](15_障害対応（IncidentResponse）/02_CI無限失敗（CIRetryIncident）.md)
- [03_GitHub連携失敗（GitHubFailure）](15_障害対応（IncidentResponse）/03_GitHub連携失敗（GitHubFailure）.md)

## 16_レポート（Reporting）
- [01_日次レポート（DailyReport）](16_レポート（Reporting）/01_日次レポート（DailyReport）.md)
- [02_自動生成（ReportGeneration）](16_レポート（Reporting）/02_自動生成（ReportGeneration）.md)
- [03_保存方針（Retention）](16_レポート（Reporting）/03_保存方針（Retention）.md)

## 17_自己進化（Evolution）
- [01_進化ループ（EvolutionLoop）](17_自己進化（Evolution）/01_進化ループ（EvolutionLoop）.md)
- [02_メトリクス学習（MetricsLearning）](17_自己進化（Evolution）/02_メトリクス学習（MetricsLearning）.md)
- [03_安全制約（EvolutionSafety）](17_自己進化（Evolution）/03_安全制約（EvolutionSafety）.md)

## 18_ロードマップ（Roadmap）
- [01_短期計画（ShortTermRoadmap）](18_ロードマップ（Roadmap）/01_短期計画（ShortTermRoadmap）.md)
- [02_中期計画（MidTermRoadmap）](18_ロードマップ（Roadmap）/02_中期計画（MidTermRoadmap）.md)
- [03_長期計画（LongTermRoadmap）](18_ロードマップ（Roadmap）/03_長期計画（LongTermRoadmap）.md)

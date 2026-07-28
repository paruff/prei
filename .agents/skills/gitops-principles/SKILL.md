# GitOps Principles Skill — prei

## When to load
- Before editing anything under `.github/workflows/`
- Before touching deployment config, the GitOps manifest repo, or `docker-compose.yml`
- When reasoning about rollback, canary, or progressive-delivery behavior

## Principles

1. **Git is the source of truth.** Config, workflows, deployment state — all in git. Never modify running infrastructure directly.
2. **Immutable artifacts.** The Docker image is the deployable unit. Test the artifact, not the source. Never rebuild for deployment.
3. **PR gates are deploy gates.** Every merge to `main` is a deploy candidate. Broken `main` blocks all PRs — fix main CI before merging anything else.
4. **Declarative pipelines.** Workflows describe DESIRED STATE: what artifacts, what gates, what triggers. Not imperative scripts.
5. **Artifact verification.** Every PR that touches workflows or deployment config must be verified against the live container via `post-deployment.yml`.
6. **Rollback is `git revert`.** Rollback to a previous commit on the GitOps manifest repo. The rollback job in `post-deployment.yml` is a safety net, not the primary mechanism.
7. **Observability built-in.** Every workflow step logs `job-start` / `job-finish` timestamps. Build times, test results, deploy status are traceable.
8. **Progressive delivery.** Canary → staging → production (see `docs/DEPLOYMENT_STRATEGY.md`). Never ship to 100% in one step.
9. **Naming is infrastructure.** PR titles follow Conventional Commits. Commit messages describe intent. Tags trigger deployments.
10. **Branch discipline.** All work happens on feature branches off `main` (trunk-based development, short-lived). Never commit directly to `main`. Branch naming: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`. Every branch opens a PR through CI gates before merge.

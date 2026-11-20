# Release workflow — "push to github"

Runbook for when the user explicitly says something like "push to github" /
"release this" / "push origin main". Not run automatically, not implied by
finishing an unrelated task — see `CLAUDE.md`'s "Guardrails" section.

This is linked to the `UU-BUEM` organization and pushed to the repo
`https://github.com/UU-BUEM/occupancy`

## Steps

0. **Sync with GitHub first — before choosing a version or writing the
   CHANGELOG.** `git fetch origin --tags`, then
   `git log --oneline HEAD..origin/main`. If that lists anything, merge it
   (`git merge origin/main`) before going further, and check two things
   in what came in: (a) whether its `CHANGELOG.md` already reserves the
   next version number (PRs sometimes add a `## [X.Y.Z]` heading without
   tagging it), and (b) whether that version's tag already exists
   (`git ls-remote --tags origin`). Pick a number that is free on the
   remote, not just locally.

   **Why (2026-11-20, v6.1.1 incident):** local `main` was missing PR #16
   (`CITATION.cff`, which had already written a `[6.1.1]` changelog
   entry). The `main` push was rejected as non-fast-forward, but the tag
   push succeeded anyway, so `release.yml` published a GitHub Release —
   and Zenodo minted a DOI — for `v6.1.1` pointing at a commit not on
   `main` and missing `CITATION.cff`. A published Zenodo record cannot be
   deleted by the user, so the fix had to be a follow-up `v6.1.2`, with
   the stray `v6.1.1` left in place permanently.

1. **Survey the diff since the last release.**
   - `git status`, `git diff`, `git log <last-tag>..HEAD --oneline` (last
     tag: `git describe --tags --abbrev=0`).
   - Decide whether `CHANGELOG.md`'s `[Unreleased]` section already covers
     everything, or needs updating — this repo follows [Keep a
     Changelog](https://keepachangelog.com/en/1.1.0/) +
     [SemVer](https://semver.org/); see existing entries for the
     Added/Changed/Fixed/Deprecated style.
   - Decide whether `README.md`/`CONTRIBUTING.md`, `.claude/*.md`, or the
     local `CLAUDE.md` need updating for anything durable the diff
     introduced (new gotcha, new convention, a resolved open-item) — same
     judgment as any other session, not a mechanical step. `CLAUDE.md` is
     gitignored (local only, since 2026-11-20): public extension points
     and scope live in `CONTRIBUTING.md`, so update that for anything
     contributors need.

2. **Determine the version bump.** This repo uses `setuptools_scm`
   (`pyproject.toml`: `version_file = "src/occupancy/_version.py"`) — the
   git tag *is* the version, no version string to hand-edit elsewhere.
   Existing tags follow `vMAJOR.MINOR.PATCH` (see `git tag --list`). Pick
   the bump per CHANGELOG's SemVer convention (breaking → MAJOR,
   backward-compatible addition → MINOR, fix-only → PATCH) based on the
   actual diff — don't default to PATCH without checking.

3. **Move `[Unreleased]` → the new version heading** in `CHANGELOG.md`
   (`## [X.Y.Z] - YYYY-MM-DD`, today's date), leaving a fresh empty
   `[Unreleased]` above it. Commit doc changes (CHANGELOG + any README/
   CONTRIBUTING/`.claude/` updates from step 1) as their own commit before tagging.

4. **Run the local CI mirror** (exact steps from
   `.github/workflows/ci.yml`, in the `occupancy_env` conda env — this
   repo has no plain `python`/`conda` on PATH by default in this
   environment; use the full interpreter path, e.g.
   `C:\Users\sahoo002\.conda\envs\occupancy_env\python.exe`, or resolve
   `conda.bat` under the anaconda install first):

   ```text
   ruff check src/ tests/
   mypy src
   pytest -q --cov=occupancy --cov-report=xml
   python -m occupancy --help
   ```

   Fix or clearly report any failure before proceeding — don't tag/push on
   a red local CI mirror. `python validate.py` (repo-root script, not part
   of CI itself) is a useful extra sanity check covering the same ground
   plus package-structure checks — see `CLAUDE.md` dev commands.

5. **Show the user a summary before pushing**: the version chosen and why,
   the CHANGELOG diff, and the local CI mirror result. This is the last
   checkpoint before an action that touches the shared remote — confirm
   before continuing unless the user has said to run this workflow fully
   autonomously.

6. **Push `main`, confirm it landed, *then* tag and push the tag** —
   strictly in that order, as separate commands:

   ```text
   git fetch origin
   git merge-base --is-ancestor origin/main HEAD   # must succeed (fast-forward)
   git push origin main                            # check: "<old>..<new>  main -> main"
   git tag vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```

   **Never push the tag if the `main` push was rejected or its outcome is
   unclear**, and never chain them (`--follow-tags`, `&&` across both
   pushes, or two pushes in one command whose output gets truncated). A
   tag push is the irreversible step: it triggers `release.yml`, which
   publishes a GitHub Release, which fires the Zenodo webhook and mints a
   permanent DOI for whatever commit the tag points at. A rejected `main`
   push costs nothing to retry; a wrong tag does not.

   **Known gotcha (first hit 2026-08-10, `v3.1.0` push): plain `git push`
   can hang indefinitely with no error output**, even after `gh auth
   setup-git` has correctly rescoped `credential.https://github.com.helper`
   away from the system-wide `credential.helper=manager` (Git Credential
   Manager) — confirmed via `git config --list --show-origin`, the override
   was in place and correct, yet the hang still happened, twice, on two
   separate plain `git push origin <ref>` invocations (2-minute and 1-minute
   timeouts both exhausted). Read-only remote operations
   (`git ls-remote`, `git fetch`) and `gh auth status`/`gh auth token` all
   returned fast and correctly in the same session — this is specific to
   `push` (a write/auth-elevation operation), most likely GCM attempting an
   interactive (browser/credential-prompt) flow that has nothing to
   complete in this headless/background tool-execution context.
   `GIT_TERMINAL_PROMPT=0` does **not** prevent this (that only suppresses
   git's own prompts, not an external credential helper's UI).

   **Workaround that worked**: bypass the credential helper entirely by
   attaching an explicit `Authorization` header built from `gh`'s own
   cached token, run from PowerShell (not the Bash tool — it was also
   unreliable for git/gh commands in the same session, separately timing
   out/erroring; PowerShell was reliable throughout):

   ```powershell
   $token = gh auth token
   $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$token"))
   git -c http.extraHeader="Authorization: Basic $b64" push origin main
   git -c http.extraHeader="Authorization: Basic $b64" push origin vX.Y.Z
   ```

   Note: piping this through `2>&1` in PowerShell will wrap git's normal
   stderr progress lines (e.g. `To https://github.com/...`) in a
   `NativeCommandError` even on success (PowerShell 5.1 native-command
   stderr quirk — see this environment's own PowerShell tool notes); check
   the actual ref-update line (`<old>..<new>  main -> main` / `* [new tag]
   vX.Y.Z -> vX.Y.Z`) rather than trusting the error categorization alone.
   If this reproduces again, worth going straight to the token-header
   approach instead of re-attempting/re-diagnosing plain `git push` first.

   The same header also works from the Bash tool (confirmed 2026-11-20):

   ```bash
   B64=$(printf 'x-access-token:%s' "$(gh auth token)" | base64 -w0)
   git -c http.extraHeader="Authorization: Basic $B64" push origin main
   ```

7. **Monitor CI on GitHub** (`gh run list --branch main --limit 1`, then
   `gh run watch <run-id>`, or `gh run watch` on the latest run) until it
   completes. Report the result (pass/fail, and which step if it failed) —
   don't just fire-and-forget the push. Watch **both** runs: `CI` on
   `main`, and `Release` on the tag
   (`gh run list --workflow release.yml --branch vX.Y.Z`), then confirm
   the release exists with its wheel + sdist (`gh release view vX.Y.Z`).
   Zenodo archives the release automatically via the repo webhook; there
   is nothing to run for it, but remember it cannot be undone.

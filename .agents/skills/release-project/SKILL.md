---
name: release-project
description: >
  Release a zha-toolkit change end to end: open a pull request, wait for CI
  to pass, squash-merge it, tag and publish a GitHub release (vX.Y.Z) with
  the HACS (Home Assistant Community Store) zip asset built by release.yml,
  verify the artifact, and close the linked issue. Repo-specific: relies on
  this project's release-drafter config, release.yml workflow, and hacs.json
  zip_release setting — do not apply to repos without that automation. Use
  when a fix or feature is ready to ship on main.
license: MIT
allowed-tools: Read Write Edit Bash Grep Glob
metadata:
  author: mdeweerd
  version: "1.0"
  domain: devops
  complexity: intermediate
  language: multi
  tags: release, github, hacs, ci-cd, home-assistant
---

# Release the Project

Ship a change to users through the project's GitHub flow: pull request, CI
gate, squash merge, versioned GitHub release with the HACS zip asset,
artifact verification, and issue closure. The flow matches this repo's
automation: `release-drafter` drafts release notes on pushes to `main`, and
`release.yml` stamps the manifest version and attaches `zha-toolkit.zip`
when a release is published.

HACS (Home Assistant Community Store) is the distribution channel for this
custom component: `hacs.json` declares `zip_release: true` with filename
`zha-toolkit.zip`, so users install the component from that zip asset. The
release is not complete until the zip is attached and its manifest version
matches the tag.

## When to Use

- A fix or feature branch is ready and needs to reach users on `main`
- CI is failing and the fix must go through PR review before shipping
- A GitHub issue should be closed by a released change ("this push solves issue #N")
- You need to publish a new `vX.Y.Z` release with the HACS zip asset

## Inputs

- **Required**: The change to release — a commit on a branch or already on `main`
- **Required when re-branching an on-main fix**: `<fix-sha>` (the fix commit already on `main`) and its parent `<fix-sha>^` as the PR base, so the PR diff shows the change
- **Optional**: Issue number the change fixes (adds `Fixes #N` to the PR body; the issue is closed at the end)
- **Optional**: Version bump type (default: `patch`, per `release-drafter` config; only use `minor`/`major` when the PR carries a `minor`/`major` label)
- **Optional**: PR title (default: conventional-commit style, e.g. `fix: drop aiofiles upper cap`)

**Placeholders**: `<owner>/<repo>` = this repository; `<slug>` = short branch-name fragment (e.g. `aiofiles-requirement-cap`); `<number>` = PR number; `<issue>` = issue number; `<X.Y.Z>` = version resolved in Step 1.

## Procedure

### Step 1: Determine the next version

The release-drafter config (`.github/release-drafter.yml`) resolves the next
version from the latest tag, defaulting to a patch bump. Sort by version,
not creation date, so `v1.2.10` beats `v1.2.9`.

```bash
git fetch --tags origin
latest_tag=$(git tag --sort=-version:refname | head -1)   # e.g. v1.2.4
# Compute the next version yourself by applying the bump to the tag above.
# Default bump is patch, so v1.2.4 -> v1.2.5.
```

**Expected:** A next-version string (e.g. `v1.2.5`) one bump above the newest tag.

**On failure:** If `git tag` returns nothing, this is the first release — use `v1.0.0`. If `git fetch --tags` fails, check the remote name (`git remote -v`) and network access.

**Note — stale draft detection (not an error path):** A tag can exist while
its release was never fully published (only a draft or pre-release). The
release-drafter then keeps folding new commits into a draft whose tag already
points at an older commit — publishing that draft ships the wrong code. Check
before deciding:

```bash
# > 0 means the latest tag has a full (non-draft, non-pre-release) release
gh api repos/<owner>/<repo>/releases \
  --jq '[.[] | select(.tag_name=="<latest_tag>") | select((.draft | not) and (.prerelease | not))] | length'

# the drafter's single draft and the version it resolved
gh api repos/<owner>/<repo>/releases \
  --jq '[.[] | select(.draft) | {tag_name, name}]'
```

If the full-release count is 0, still bump from that tag, but do not publish
the old draft — create the new version tag instead (see Common Pitfalls). The
draft's `name` should match the computed next version; if it names an older
version, that is the stale-draft situation.

### Step 2: Prepare the change branch

Two variants:

- **Change already on `main` (direct push):** branch from the fix commit's
  parent — not from `main` HEAD, where cherry-picking the fix yields an
  already-applied commit and the PR diff shows nothing — then cherry-pick
  the fix onto it:

  ```bash
  base_sha=$(git rev-parse <fix-sha>^)   # parent of an on-main fix
  git checkout -b fix/<slug> "$base_sha"
  git cherry-pick <fix-sha>
  git push -u origin fix/<slug>
  ```

- **Change on its own feature branch:** push the branch as-is:

  ```bash
  git push -u origin fix/<slug>
  ```

Name the branch `fix/...` so the autolabeler applies the `bug` label
(release-drafter files it under "Bug Fixes").

**Expected:** Remote branch exists; `git log --oneline -2` shows the fix on top.

**On failure:** If the cherry-pick conflicts, the base moved — branch from current `main` instead: `git checkout -b fix/<slug> main && git cherry-pick <fix-sha>`.

### Step 3: Open the pull request

```bash
gh pr create --base main --head fix/<slug> --label bug \
  --title 'fix: <short summary>' \
  --body "Fixes #<issue>: <one-line description of the change>"
```

Reference the issue with `Fixes #<issue>` so GitHub links them (the issue
auto-closes on merge only if the keyword is in the body at merge time).

**Expected:** `gh pr create` prints the PR URL (e.g. `.../pull/356`).

**On failure:** If `gh pr create` reports missing scopes, check `gh auth status`.

**Issue number learned after PR creation:** The issue is often identified
mid-flow (e.g. "this push solves issue #N"). Add `Fixes #N` to the PR body
before merging — the auto-close keyword only takes effect if it is in the body
at merge time:

```bash
gh pr edit <number> --body "Fixes #<issue>: <one-line description of the change>"
gh pr view <number> --json body   # verify the edit landed
```

`gh pr edit` can fail on token scope (`read:org` is required by its GraphQL
query). Fall back to the REST API:

```bash
printf '%s' '{"body": "Fixes #<issue>: <one-line description of the change>"}' > /tmp/payload.json
curl -s -X PATCH -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  --data-binary @/tmp/payload.json \
  "https://api.github.com/repos/<owner>/<repo>/pulls/<number>"
```

### Step 4: Wait for CI and verify it passes

The PR triggers these checks (names as shown by `gh pr checks`):
`pre-commit` (x2), `validate`/hassfest (x2), `HACS Action` (x2), and
`Update release draft`. `hassfest` validates the Home Assistant component
manifest; the HACS action validates `hacs.json` compliance.
(`codeql-analysis` only runs for PRs against the `dev` branch, so its absence
here is expected — do not wait for it or treat it as a missing gate.)

```bash
gh pr checks <number> --watch               # exits when every run reaches a final state
# mergeable: MERGEABLE, mergeStateStatus: CLEAN
gh pr view <number> --json mergeable,mergeStateStatus
```

**Expected:** The expected check set is complete AND every run passed. For a
PR to `main`, `pre-commit`, `validate`/hassfest, `HACS Action`, and
`Update release draft` must each have at least one run with conclusion
`success`. "Every listed run passed" is not sufficient — a workflow that
never fired is a failure too. The PR is `MERGEABLE` with
`mergeStateStatus: CLEAN`.

**On failure:** Three distinct cases:

- A run reports failure: read the failing job log (`gh run view <run-id> --log-failed`), fix the cause on the branch (pushing updates the PR), and re-poll. Do not merge with red CI.
- An expected check is missing entirely (e.g. `Update release draft` never ran): re-trigger CI with an empty commit (`git commit --allow-empty -m "chore: retrigger checks" && git push`) and re-poll.
- Runs stay pending forever (workflow never triggered): same empty-commit re-trigger.

### Step 5: Merge the pull request

This repo merges PRs as squash commits (merged PR titles carry a `(#<number>)` suffix).

```bash
gh pr merge <number> --squash --delete-branch
git checkout main && git pull --ff-only origin main
squash_sha=$(git rev-parse main)      # tag this exact commit in Step 7
```

**Expected:** PR state `MERGED`; local `main` fast-forwards to the squash
commit. Recognize it: `git log --oneline -1` shows the PR title with its
`(#<number>)` suffix. Save that SHA — Step 7 tags it explicitly.

**On failure:** Two cases:

- Branch protection rejects the merge (e.g. requires a review): merge with `gh pr merge <number> --squash --admin` when you are the repo owner, or request a review first.
- `git pull --ff-only` fails: `git fetch origin` first. If `origin/main` now has the squash commit and local `main` only has unpushed commits, either rebase them (`git pull --rebase`) or discard them (`git reset --hard origin/main` — destructive; only for disposable local work). If `origin/main` does not have the squash commit yet, the merge event has not propagated — wait and retry.

### Step 6: Compose the release notes

Base the notes on the release-drafter draft, which accumulates merged PRs
since the last full release. Save the result as `notes.md` (consumed by
Step 7).

```bash
gh api repos/<owner>/<repo>/releases \
  --jq '.[] | select(.draft) | .body'
```

The push to `main` in Step 5 has already triggered the release-drafter, which
folds the merged PR into the draft under the matching category heading (copy
the exact heading from `.github/release-drafter.yml`, e.g. `## 🐛 Bug Fixes`).
Wait for that workflow run on `main` to finish, then verify the merged PR
appears in the fetched body; only add entries that are missing — otherwise
the entry is duplicated.

```bash
gh run list --branch main --workflow="Release Drafter" --limit 1   # until completed
```

**Expected:** A markdown file `notes.md` covering all changes since the last
published release. Verifiable: `grep -c '#<number>' notes.md` is >= 1 with the
PR under the matching category heading, and no PR merged before the last
published release appears.

**On failure:** If no draft exists, generate notes from merged PRs — bounded
to the window since the last published (non-draft) release, otherwise
already-released PRs leak into the notes. Note: `gh api` returns the raw REST
payload, so fields are snake_case (`published_at`, not `publishedAt`):

```bash
since=$(gh api repos/<owner>/<repo>/releases \
  --jq '[.[] | select((.draft | not) and (.published_at != null))] | sort_by(.published_at) | last | .published_at' | cut -dT -f1)
gh pr list --state merged --base main --limit 50 --search "merged:>=$since" \
  --json number,title,url
```

Careful: "last published release" is not simply "latest tag" — a tag can
exist with only a draft/pre-release (see Step 1).

### Step 7: Tag and publish the release

`release.yml` runs on `release: [published]`: it stamps the manifest version
from the tag name and uploads `zha-toolkit.zip` built from
`custom_components/zha_toolkit`.

```bash
git ls-remote --tags origin "v<X.Y.Z>"        # must print nothing: tag must not exist yet
git tag "v<X.Y.Z>" "$squash_sha"              # the merged commit saved in Step 5 — pin the SHA, not the moving `main` ref
git push origin "v<X.Y.Z>"
# pre-check: does a release (draft) already target this tag?
gh api repos/<owner>/<repo>/releases \
  --jq '.[] | select(.tag_name=="v<X.Y.Z>") | {id, draft, prerelease}'
gh release create "v<X.Y.Z>" --title "v<X.Y.Z> 🧰" --notes-file notes.md
```

The title follows the drafter's `name-template` in
`.github/release-drafter.yml` (currently `v$RESOLVED_VERSION 🧰`) — copy the
exact suffix from that file; do not guess it, or the published title won't
match the drafter's next draft.

**Expected:** `gh release create` prints the release URL;
`gh release view "v<X.Y.Z>" --json isDraft,publishedAt` shows `isDraft: false`
and a non-null `publishedAt` (the release is published and becomes "Latest").

**On failure:** Three cases:

- `gh release create` fails with `already_exists`: a release — usually the release-drafter's draft — already targets this tag. Publish that release instead of creating a duplicate:

  ```bash
  jq -n --rawfile body notes.md '{draft: false, name: "v<X.Y.Z> 🧰", body: $body}' > /tmp/payload.json
  curl -s -X PATCH -H "Authorization: token $GH_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    --data-binary @/tmp/payload.json \
    "https://api.github.com/repos/<owner>/<repo>/releases/<id>"   # id from the pre-check
  ```

  or delete the draft (`gh release delete "v<X.Y.Z>" --yes`) and re-run `gh release create`.
- The tag already exists: the version was already tagged — pick the next patch version and repeat. If the tag push is rejected, fetch first (`git fetch --tags`) and check for a remote tag with the same name.
- `git tag` fails with "already exists" (stale local tag from an earlier attempt): `git tag -d "v<X.Y.Z>"` and re-tag the squash SHA.

### Step 8: Verify the release artifact

Wait for the `release.yml` workflow run bound to THIS release (event
`release`, head SHA = the tagged squash commit) and confirm the zip asset
exists and ships the change. Do not read a single snapshot: right after
publishing, the newest run may still be the previous release's
already-successful run.

```bash
gh run list --workflow=release.yml --limit 5 \
  --json event,status,conclusion,headSha \
  --jq '.[] | select(.event=="release" and .headSha=="<squash_sha>")'
# poll until that run shows status=completed, conclusion=success
gh release view "v<X.Y.Z>" --json assets             # must list zha-toolkit.zip
gh release download "v<X.Y.Z>" --pattern zha-toolkit.zip --dir /tmp/rel
python3 -c "import zipfile,json; z=zipfile.ZipFile('/tmp/rel/zha-toolkit.zip'); \
  m=json.loads(z.read('manifest.json')); print(m['version'], m['requirements'])"
```

Note: the zip stores paths relative to the component dir, so the manifest is
at the zip root (`manifest.json`), and `version` equals the full tag name
including the `v` prefix (the stamp script writes the tag verbatim — expecting
`1.2.4` when the tag is `v1.2.4` would false-alarm).

**Expected:** The workflow run bound to this release is `completed/success`;
asset `zha-toolkit.zip` is present; the manifest inside shows `version` equal
to the full tag name and the intended `requirements`.

**On failure:** Two cases:

- Asset missing or workflow failed: re-run the failed run in its original release context — `gh run rerun <run-id>` — then inspect the `upload-release-action` step log. Do NOT use `gh workflow run release.yml`: a manual dispatch has no release event context, so the version-stamp step would read the branch name instead of the tag.
- Manifest content is wrong (tag points at the wrong commit): the release is already published and HACS clients may have pulled it. Deleting a published release and its tag (`git push origin :refs/tags/v<X.Y.Z>` and `gh release delete "v<X.Y.Z>" --yes`), retagging and republishing rewrites what users may have cached — prefer fixing forward (publish the next patch version with the corrected tag) unless the release is minutes old and confirmed unpulled. If you do delete, retag the correct commit and republish.

### Step 9: Close the linked issue

```bash
gh issue comment <issue> --body "Fixed by #<number> and released in v<X.Y.Z> ..."
gh issue close <issue> --reason completed
```

**Expected:** Issue shows the comment and state `closed`.

**On failure:** If the issue was already closed by the `Fixes #` keyword on merge, the comment still lands; skip the close. If `gh issue close` fails on scopes, close via REST: `curl -X PATCH -H "Authorization: token $GH_TOKEN" -d '{"state":"closed"}' "https://api.github.com/repos/<owner>/<repo>/issues/<issue>"`.

## Validation

- [ ] PR merged as a squash commit and local `main` is up to date with `origin/main`
- [ ] All expected PR check runs reported success before merging
- [ ] Tag `v<X.Y.Z>` exists and points at the merged squash commit: `git ls-remote --tags origin "v<X.Y.Z>"` returns `$squash_sha` (recorded in Step 5)
- [ ] Release is published (not draft): `gh release view "v<X.Y.Z>" --json isDraft,publishedAt` shows `isDraft: false` and a non-null `publishedAt`
- [ ] The `release.yml` run bound to the tag (event `release`, head SHA = `$squash_sha`) completed with success and `zha-toolkit.zip` is attached
- [ ] Zip manifest shows `version` = full tag name (with `v` prefix) and the intended `requirements`
- [ ] Release notes cover all changes since the last published release, with the merged PR under the matching category
- [ ] Linked issue is closed with a comment referencing the PR and release
- [ ] The remaining release-drafter draft targets the NEXT version, not the one just published: `gh api repos/<owner>/<repo>/releases --jq '[.[] | select(.draft) | .tag_name]'`

## Common Pitfalls

- **Publishing a stale draft release**: If a tag exists but its release was never fully published (draft/pre-release only), the release-drafter keeps folding new commits into that draft, whose tag already points at an older commit. Publishing it attaches the release to the OLD tag commit — the zip won't contain recent fixes. Always create the next version tag on the merged commit instead. After publishing, confirm the drafter's remaining draft targets the next version, and delete any draft whose tag already exists (`gh release delete <tag> --yes`).
- **Re-running the skill after a partial run**: A previous attempt may have died mid-flow (branch pushed but no PR, PR open but unmerged, tag pushed but no release). Blindly re-doing a step then fails (`gh pr create` on an existing head branch, pushing an existing tag, `gh release create` on an existing tag). Check what already exists first (`gh pr list --head fix/<slug>`, `git ls-remote --tags origin "v<X.Y.Z>"`, `gh release view "v<X.Y.Z>"`) and resume from the first missing step.
- **Direct pushes to `main` bypass CI**: Pushing a fix straight to `main` skips the PR gate. When a PR flow is required afterwards, branch from the fix's parent and cherry-pick so the PR diff shows the change.
- **`gh` token scope gaps**: Some `gh` commands use GraphQL queries that need scopes the token lacks (`read:org`), e.g. `gh pr edit`. Fall back to the REST API via `curl` with `$GH_TOKEN`.
- **Forgetting the issue link**: Without `Fixes #N` in the PR body (before merge), GitHub won't auto-close the issue; close it manually in Step 9.
- **Tag/commit mismatch**: `release.yml` builds the zip from the tag. Tag the recorded squash SHA, not a ref — tagging a stale local `main` ships stale code. Verify the zip manifest in Step 8.

## Related Skills

- `create-pull-request` - open and manage PRs with gh (used in Step 3)
- `review-pull-request` - review a PR end to end before merging (used in Steps 4-5)
- `evolve-skill` - refine this skill after a release run reveals gaps

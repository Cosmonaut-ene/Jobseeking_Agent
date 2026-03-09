# Contributing Guide

## Branch workflow

`main` is the stable branch. All development happens on feature branches.

```
main
 └── feat/scout-agent-improvements
 └── fix/resume-ats-score
 └── chore/upgrade-deps
```

### Branch naming

| Prefix | When to use |
|--------|-------------|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `chore/` | Config, deps, tooling |
| `refactor/` | Code cleanup, no behaviour change |

Keep names short and lowercase with hyphens: `feat/job-notes`, not `feature/AddJobNotesField`.

## Day-to-day workflow

```bash
# 1. Start from an up-to-date main
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feat/my-feature

# 3. Develop & commit often
git add <files>
git commit -m "feat: short description"

# 4. Push and open PR
git push -u origin feat/my-feature
# Then open a PR on GitHub → main
```

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add user_notes field to Job model
fix: handle missing cover letter gracefully
chore: bump sqlmodel to 0.0.21
```

## PR rules

- Target branch: `main`
- Fill in the PR template
- Self-review before requesting review
- Squash trivial fixup commits before merging (`git rebase -i`)
- Delete the branch after merge

## Local setup

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

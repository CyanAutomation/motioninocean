# Repository skills

These skills are short, task-specific playbooks for contributors and operators. Choose one by the work you need to do, then verify its guidance against the linked source files when those files change.

## Find a skill

| Task | Skill |
| --- | --- |
| Start a code or documentation change | [`contributor-workflow`](./contributor-workflow/SKILL.md) |
| Reproduce local quality gates | [`ci-quality-gates`](./ci-quality-gates/SKILL.md) |
| Diagnose a failed Actions job | [`ci-triage`](./ci-triage/SKILL.md) |
| Validate JavaScript or TypeScript changes | [`frontend-testing-linting`](./frontend-testing-linting/SKILL.md) |
| Review a web interface change | [`ui-review`](./ui-review/SKILL.md) |
| Apply the project’s interface design principles | [`front-end-design`](./front-end-design/SKILL.md) |
| Change or diagnose the mock camera flag | [`feature-flag-management`](./feature-flag-management/SKILL.md) |
| Review dependency update pull requests | [`dependabot-dependency-management`](./dependabot-dependency-management/SKILL.md) |
| Validate a deployment | [`deployment-validation-health-checks`](./deployment-validation-health-checks/SKILL.md) |
| Diagnose Raspberry Pi camera startup or streaming | [`pi-camera-troubleshooting`](./pi-camera-troubleshooting/SKILL.md) |
| Build or validate documentation | [`documentation-build-validation`](./documentation-build-validation/SKILL.md) |
| Create or update a Mermaid diagram | [`mermaid-creator`](./mermaid-creator/SKILL.md) |
| Prepare a manual GitHub release | [`release-operator`](./release-operator/SKILL.md) |
| Verify the published container images | [`release-publish`](./release-publish/SKILL.md) |

## Contributor flow

```mermaid
flowchart TD
    A[Choose task] --> B{Task type}
    B -->|Code or docs| C[contributor-workflow]
    C --> D[ci-quality-gates]
    B -->|CI failure| E[ci-triage]
    B -->|Frontend code| F[frontend-testing-linting]
    B -->|Interface review| G[ui-review]
    B -->|Deployment| H[deployment-validation-health-checks]
    H --> I[pi-camera-troubleshooting]
    B -->|Manual GitHub release| J[release-operator]
    J --> K[release-publish: verify container images]
    B -->|Documentation| L[documentation-build-validation]
    L -->|If a diagram changes| M[mermaid-creator]
```

## Skill authoring and maintenance

Use [`_template/SKILL.md`](./_template/SKILL.md) for new skills. Each `SKILL.md` must include the required frontmatter and sections in the template. Keep instructions concise, use exact current paths and commands, and link to repository sources that define the behavior.

There is no separate owner registry; the motion-in-ocean team owns these skills. When a source-of-truth file changes, review the affected skill in the same change and update `last-reviewed` after verifying its instructions. The documentation checks require compatible paths to exist, keep skill names aligned with their directories and this index, and flag reviews older than 100 days.

The regression checks in [`tests/test_skills_documentation.py`](../../tests/test_skills_documentation.py) verify required skill structure, local links, compatible paths, index entries, review dates, referenced Make/npm commands, and Mermaid extraction and validation. Release checks also ensure the skills describe the manual GitHub Release process. Run them with:

```bash
python -m pytest tests/test_skills_documentation.py -q
```

## Repository sources

- [`AGENTS.md`](../../AGENTS.md) — Repository architecture and contributor instructions for coding agents.
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md) — Human contribution process.
- [`.github/workflows/`](../workflows/) — CI, security scanning, release, and scheduled automation definitions.
- [`docs/CHANGELOG.md`](../../docs/CHANGELOG.md) — Version history and release notes.
- [`docs/guides/RELEASE.md`](../../docs/guides/RELEASE.md) — Release procedure and recovery guidance.

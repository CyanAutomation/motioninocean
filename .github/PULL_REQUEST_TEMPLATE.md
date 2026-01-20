<!--
Thanks for contributing to motion-in-ocean! 🌊📷

Before opening the PR, please ensure:
- The change is focused and easy to review
- You have tested it (Pi + camera where applicable)
- Docs are updated if behaviour/config changes
-->

## Summary
<!-- What does this PR change? Why is it needed? -->

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactor / cleanup
- [ ] CI / build / packaging
- [ ] Other (please describe):

## Related issues
<!-- Link issues: "Fixes #123" or "Closes #123" -->
- Fixes #

## How has this been tested?
<!-- Provide steps, logs, environment details (Pi model + OS) -->
- [ ] Tested on Raspberry Pi hardware with CSI camera
- [ ] Tested in `MOCK_CAMERA=true` mode
- [ ] Smoke-tested endpoints:
  - [ ] `GET /health`
  - [ ] `GET /ready`

### Test environment
- Raspberry Pi model:
- OS version (Bookworm?):
- Camera module:
- Docker version:
- Compose version:

### Test notes
<!-- Paste commands run, brief results -->
```bash
# e.g.
docker compose up -d --build
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
docker logs motion-in-ocean --tail 200
```
Screenshots (if applicable)
<!-- Add screenshots for UI changes or stream output -->
Documentation updates
 No docs changes needed
 README updated
 .env.example updated
 Other docs updated:
Checklist
 My code follows the project style
 I have kept the changes small and focused
 I added comments where Raspberry Pi quirks exist
 I updated docs where relevant
 I’ve checked the change does not weaken security defaults (e.g. binding to 0.0.0.0 without warning)
Notes for reviewers
<!-- Anything that will help reviewing / future maintainers -->

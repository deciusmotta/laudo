Render-ready Flask project for generating 'laudos' (technical reports)
------------------------------------------------------------------

Behavior:
- Counter is persisted in a GitHub file (laudos.json) at the repository specified by GITHUB_REPO and GITHUB_FILE environment variables.
- The app reads laudos.json from GitHub on demand and updates it via the GitHub Contents API when a new laudo is generated.
- Laudos are generated dynamically and returned to the browser (no disk writes), matching your request to open them in the browser for viewing.
- Deploy on Render: set environment variables GITHUB_TOKEN, GITHUB_REPO (e.g. deciusmotta/laudo), GITHUB_FILE (e.g. laudos.json).

Environment variables to set on Render:
- GITHUB_TOKEN : Personal Access Token with repo contents write access for the target repo.
- GITHUB_REPO  : owner/repo (e.g. deciusmotta/laudo)
- GITHUB_FILE  : path to JSON file in repo (e.g. laudos.json)

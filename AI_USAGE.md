# AI Usage Disclosure

- Tool/model: Gemini
- Purpose: Troubleshooting NGINX upstream failover behavior, generating backup/restore scripts, and structuring Part 4 architectural documentation.
- Files or decisions affected:
  - `nginx/nginx.conf`: Configured `proxy_next_upstream` and `max_fails=1` for backend failure handling.
  - `backup.sh` & `restore.sh`: Created PostgreSQL database snapshot and restore scripts.
  - `.github/workflows/ci.yml`: Configured GitHub Actions workflow and Trivy vulnerability scan step.
  - `README.md`, `decisions.md`, `troubleshooting.md`, `security_review.md`: Structured technical responses and operational documentation.
- What you changed or rejected: Adapted default suggested configurations to align strictly with the assessment's specific network topologies, port constraints, and custom script requirements (`validate.py` and `failure_test.py`).
- How you independently verified it: Executed local verification scripts (`python3 validate.py`, `python3 failure_test.py`), verified database persistence via `./backup.sh` and `./restore.sh`, and confirmed automated pass status in the GitHub Actions CI pipeline run.
- Related commit: `feat(ci): add github actions pipeline, backup scripts, and validation tests`

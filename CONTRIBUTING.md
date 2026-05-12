# Contributing

Thanks for your interest in improving the LLM Security Scanner.

## Ways to Contribute

- **New OWASP checks** — the four current checks (LLM01, LLM04, LLM06, LLM08) leave room for LLM02, LLM03, LLM05, LLM07, LLM09, LLM10
- **Probe improvements** — sharper adversarial prompts, better scoring heuristics
- **Bug reports** — open an issue with reproduction steps and your endpoint type

## Local Setup

```bash
git clone https://github.com/DorKaminsky/llm-security-scanner
cd llm-security-scanner
cp .env.example .env
docker-compose up
```

Run tests before opening a PR:

```bash
pip install -r requirements-test.txt
pytest tests/ -v
```

## Pull Request Guidelines

- One logical change per PR
- All existing tests must pass
- New checker logic should include matching tests under `tests/`
- Keep adversarial probes in `services/checkers/<name>/probes.py` — separate from scoring logic

## Ethical Note

This tool is for testing **your own** LLM-powered applications. Contributions must not introduce probes designed to attack endpoints without authorization.

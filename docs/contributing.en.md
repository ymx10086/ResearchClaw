# Contributing

Thank you for your interest in contributing to ResearchClaw!

## Development Setup

### Backend (Python)

```bash
# Clone the repository
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"
```

### Console (Frontend)

```bash
cd console
npm install
npm run dev
```

### Website (Frontend)

```bash
cd website
npm install
npm run dev
```

## Contribution Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m "feat: add my feature"`
4. Push branch: `git push origin feature/my-feature`
5. Create a Pull Request

## Code Standards

- Python code follows PEP 8
- TypeScript code uses ESLint + Prettier
- Commit messages follow Conventional Commits

## Skill Contributions

To develop custom Skills:

1. See [Skills documentation](./skills.md) for skill structure
2. Create a new skill in the `skills/` directory
3. Write `skill.json` and handler logic
4. Test thoroughly
5. Submit a PR or publish to a standalone repository

## Bug Reports

- Use GitHub Issues to report bugs
- Provide reproduction steps and environment info
- Include relevant log output

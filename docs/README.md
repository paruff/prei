# Real Estate Investor Documentation

This directory contains the project documentation structured according to the [Diátaxis framework](https://diataxis.fr/).

## Documentation Structure

### Tutorials (`tutorials/`)
**Learning-oriented** — Hands-on lessons for beginners

- `getting-started.md` — Complete setup and first analysis walkthrough

Tutorials are designed to help newcomers learn by doing. They provide step-by-step instructions to accomplish a meaningful task.

### How-to Guides (`how-to-guides/`)
**Problem-oriented** — Practical solutions for specific tasks

- `add-property.md` — Add a new investment property
- `import-data.md` — Import bulk data from CSV files
- `running-tests.md` — Execute test suite

How-to guides assume some familiarity with the system and focus on solving specific problems or accomplishing particular goals.

### Reference (`reference/`)
**Information-oriented** — Technical descriptions and specifications

- `financial-kpis.md` — Detailed financial calculation reference
- Model documentation (planned)
- API documentation (planned)
- Configuration reference (planned)

Reference documentation provides authoritative technical information about the application's components, APIs, and configuration options.

### Explanation (`explanation/`)
**Understanding-oriented** — Background and design rationale

- `architecture.md` — System design and component organization
- Technology choices (planned)
- Design decisions (planned)

Explanation documentation clarifies concepts, discusses alternatives, and explains why the system works the way it does.

## Building the Documentation

### Local Development

1. Install documentation dependencies:
   ```bash
   pip install -r docs-requirements.txt
   ```

2. Serve documentation locally with live reload:
   ```bash
   mkdocs serve
   ```

3. Open your browser to `http://127.0.0.1:8000`

### Building for Production

Build static site:
```bash
mkdocs build
```

The generated site will be in the `site/` directory.

### Publishing to GitHub Pages

Documentation is automatically built and deployed to GitHub Pages via GitHub Actions when changes are pushed to the `main` branch.

Workflow: `.github/workflows/docs.yml`

Published site: `https://paruff.github.io/prei/`

## Adding New Documentation

### Creating a New Page

1. Create a Markdown file in the appropriate section:
   - `tutorials/` for learning-oriented content
   - `how-to-guides/` for task-oriented content
   - `reference/` for information-oriented content
   - `explanation/` for understanding-oriented content

2. Add the page to `mkdocs.yml` navigation:
   ```yaml
   nav:
     - How-to Guides:
         - how-to-guides/index.md
         - New Guide: how-to-guides/new-guide.md
   ```

3. Test locally with `mkdocs serve`

### Documentation Guidelines

- **Use Markdown** — All documentation is written in Markdown
- **Follow Diátaxis** — Ensure content is in the correct category
- **Be concise** — Get to the point quickly
- **Use examples** — Show, don't just tell
- **Test code samples** — Ensure all code examples work
- **Link internally** — Connect related documentation
- **Update navigation** — Add new pages to `mkdocs.yml`

### MkDocs Material Features

This documentation uses [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/), which provides:

- **Search** — Full-text search
- **Code highlighting** — Syntax highlighting with copy button
- **Admonitions** — Note, warning, tip callouts
- **Tabs** — Tabbed content for alternatives
- **Navigation** — Organized multi-level navigation
- **Dark mode** — Light/dark theme toggle

Example admonition:
```markdown
!!! note
    This is a note admonition.

!!! warning
    This is a warning admonition.
```

Example code block with highlighting:
````markdown
```python
def calculate_noi(income: Decimal, expenses: Decimal) -> Decimal:
    return income - expenses
```
````

## Configuration

Documentation configuration is in `mkdocs.yml` at the repository root.

Key configuration sections:

- **Site metadata** — Name, URL, description
- **Theme** — Material theme with customizations
- **Navigation** — Page organization
- **Plugins** — Search and git revision date
- **Markdown extensions** — Additional Markdown features

## Contributing

When contributing documentation:

1. Follow the Diátaxis framework
2. Write in clear, simple language
3. Include code examples and screenshots where helpful
4. Test all commands and code samples
5. Preview changes locally before submitting
6. Update the navigation in `mkdocs.yml`

## Additional Resources

- [Diátaxis Framework](https://diataxis.fr/) — Documentation system philosophy
- [MkDocs](https://www.mkdocs.org/) — Static site generator
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) — Theme documentation
- [Markdown Guide](https://www.markdownguide.org/) — Markdown syntax reference

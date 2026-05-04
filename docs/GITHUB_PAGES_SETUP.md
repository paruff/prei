# Enabling GitHub Pages

To publish the documentation to GitHub Pages, follow these steps:

## 1. Navigate to Repository Settings

1. Go to the repository on GitHub: `https://github.com/paruff/prei`
2. Click on **Settings** (you must have admin access)

## 2. Configure GitHub Pages

1. In the left sidebar, scroll down to **Pages** under the "Code and automation" section
2. Under **Source**, select:
   - Source: **GitHub Actions**
3. Save the configuration

## 3. Verify Workflow Permissions

1. In the left sidebar, click **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Ensure **Read and write permissions** is selected
4. Check **Allow GitHub Actions to create and approve pull requests**
5. Click **Save**

## 4. Trigger Documentation Build

The documentation workflow (`.github/workflows/docs.yml`) will run automatically when:
- Changes are pushed to `main` branch that affect documentation files
- You manually trigger it via **Actions** → **Documentation** → **Run workflow**

## 5. Verify Deployment

1. Go to **Actions** tab and check the **Documentation** workflow
2. Wait for the workflow to complete (green checkmark)
3. Visit `https://paruff.github.io/prei/` to see the published documentation

## Alternative: Manual Deployment

If automatic deployment isn't working, you can deploy manually:

```bash
# Install documentation dependencies
pip install -r docs-requirements.txt

# Build and deploy to gh-pages branch
mkdocs gh-deploy
```

This will:
1. Build the documentation
2. Push the built site to the `gh-pages` branch
3. GitHub Pages will serve from that branch

## Troubleshooting

### Workflow Failing

Check the workflow logs:
1. Go to **Actions** tab
2. Click on the failed **Documentation** workflow run
3. Review the error messages

Common issues:
- Missing dependencies → Check `docs-requirements.txt`
- Build errors → Run `mkdocs build` locally to reproduce
- Permission errors → Verify workflow permissions (step 3 above)

### Site Not Updating

If the site builds successfully but doesn't update:
1. Clear your browser cache
2. Wait a few minutes for CDN propagation
3. Check that you're viewing the correct URL: `https://paruff.github.io/prei/`

### 404 Error

If you get a 404 error:
1. Verify GitHub Pages is enabled in repository settings
2. Check that the source is set to **GitHub Actions**
3. Ensure the `deploy` job completed successfully in the workflow

## Documentation Workflow

The workflow (`.github/workflows/docs.yml`) consists of two jobs:

1. **build** — Builds the documentation and uploads as artifact
   - Runs on all pushes and PRs that affect docs
   - Validates that documentation builds successfully

2. **deploy** — Deploys to GitHub Pages
   - Only runs on pushes to `main` branch
   - Requires successful build job

## Custom Domain (Optional)

To use a custom domain:

1. Add a `CNAME` file to the `docs/` directory with your domain name:
   ```
   docs.yourdomain.com
   ```

2. Configure DNS with your domain provider:
   - Add a CNAME record pointing to `paruff.github.io`

3. In GitHub Pages settings, enter your custom domain and enforce HTTPS

## Security

The workflow uses:
- `GITHUB_TOKEN` for authentication (automatically provided)
- `permissions` to limit token scope
- `id-token: write` for deployment to Pages

No additional secrets are required.

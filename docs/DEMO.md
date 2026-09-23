# Live demo

The dashboard is a static site. The checked-in `site/` directory is the complete
deployable artifact; it does not need a server-side runtime or model/API
credentials.

## Recommended first demo: internal GitLab Pages

GitLab Pages supports private and internal projects, with access controlled by
the GitLab project. To publish this project:

1. Import or mirror the repository into the internal GitLab group.
2. Keep the project visibility `Internal` or `Private` and ensure a CI runner is
   enabled.
3. Push the default branch. `.gitlab-ci.yml` copies `site/` to the Pages
   artifact and deploys it from the default branch.
4. Open **Deploy > Pages** in GitLab and share the authenticated Pages URL with
   the demo audience.

The local equivalent is:

```bash
python3 -m http.server 8000 --directory site
```

Then open `http://localhost:8000/`.

Before a demo deployment, run the offline checks from the repository root:

```bash
python3 -m modelagency.cli validate
python3 -m unittest discover -s tests -q
node -e "import('./tests/test_dashboard_budget.mjs').then(tests => console.log(tests.runBudgetTests()))"
```

## GitHub alternative

GitHub Pages is available for public repositories on GitHub Free and for
private repositories on GitHub Pro, Team, or Enterprise. A privately published
Pages site with repository-reader access requires GitHub Enterprise Cloud;
making only the repository private on a Free plan is not sufficient.

If the project stays on GitHub, configure Pages from **Settings > Pages** and
confirm the organization plan and intended site visibility. The checked-in
GitHub Actions workflow validates and builds the checked-in snapshots without
fetching upstream data or requiring repository secrets. To opt into deployment,
set the repository variable `ENABLE_PAGES` to `true` after Pages is configured.

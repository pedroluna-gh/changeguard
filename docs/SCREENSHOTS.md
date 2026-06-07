# Screenshots

The images under `docs/screenshots/` are referenced from the README. The files
currently committed are **placeholders** — please replace them with real captures
of the running app so the README shows the actual product.

| File | Where it's used | What to capture |
|---|---|---|
| `app-overview.png` | README hero | The Streamlit app with the Service Catalog and Change Request editors and the **Run Risk Assessment** button. |
| `risk-results.png` | README "Quick demo" | A completed assessment showing the risk score, risk level, and the per-category score breakdown. |
| `github-pr-comment.png` | README GitHub Action section | The ChangeGuard report posted as a pull-request comment with a failed check. |

## How to capture

1. Launch the web app:

   ```bash
   pip install -e ".[app]"
   streamlit run app.py
   ```

2. Click a **Low / High / Critical Risk Example**, then **Run Risk Assessment**.

3. Take a screenshot of:
   - the input editors (for `app-overview.png`), and
   - the results / score breakdown (for `risk-results.png`).

4. For `github-pr-comment.png`, open a pull request in a repo that uses the
   ChangeGuard Action and screenshot the posted report comment.

## Guidelines

- Use a clean browser window (no personal bookmarks/extensions visible).
- Prefer a light background and a width around **1280px** for consistency.
- Keep file sizes reasonable (PNG, ideally < 300 KB each).
- Use only placeholder / non-sensitive data in the inputs.
- Keep the same file names so the README links keep working.

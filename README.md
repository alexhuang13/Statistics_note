# A Guided Tour of Modern Statistics

LaTeX lecture notes by Zixun Huang.

## Online version

After GitHub Pages is enabled with **GitHub Actions** as the source, the latest compiled notes are published at:

- Website: `https://alexhuang13.github.io/Statistics_note/`
- Direct PDF: `https://alexhuang13.github.io/Statistics_note/notes.pdf`

Every push to `main` triggers `.github/workflows/deploy-pages.yml`, which compiles `main.tex` and deploys the updated PDF and reader page.

## Local compilation

```bash
latexmk -pdf main.tex
```

# A Guided Tour of Modern Statistics

LaTeX lecture notes by Zixun Huang.

## Online version

The latest compiled notes are available online:

- **[Read the lecture notes online](https://alexhuang13.github.io/Statistics_note/)**
- **[Open or download the latest PDF](https://alexhuang13.github.io/Statistics_note/notes.pdf)**

Every push to `main` triggers `.github/workflows/deploy-pages.yml`, which:

1. compiles the print-ready PDF;
2. converts the LaTeX source into native HTML with MathJax;
3. builds chapter navigation, full-text search, theorem cards, and responsive pages;
4. deploys the updated reading website and PDF to GitHub Pages.

## Local compilation

Compile the PDF:

```bash
latexmk -pdf main.tex
```

Build the complete HTML reading website locally:

```bash
./scripts/build_html.sh
python3 -m http.server 8765 --directory _site
```

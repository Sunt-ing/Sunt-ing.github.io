# Ting Sun — personal site and bilingual writing

A static GitHub Pages site. The existing homepage remains at `/`; Chinese and English writing live at `/zh/blog/` and `/en/blog/`.

## Editing articles

- Chinese: `content/inkling-2-small/zh.md`
- English: `content/inkling-2-small/en.md`
- Titles, descriptions and optional original publication dates: `content/posts.json`
- Layout: `scripts/build.py`; styling and interactions: `assets/blog.css`, `assets/blog.js`

Install Python 3.10+ and run:

```sh
python -m pip install -r requirements.txt
python scripts/build.py
python -m http.server 8000
```

Open `http://localhost:8000/`. Commit the generated HTML alongside the Markdown sources after edits. GitHub Pages can continue serving the root of the `main` branch; no server, framework runtime, or build workflow is required.

To add an article, add its two Markdown files under `content/<slug>/` and a bilingual entry in `content/posts.json`, then rebuild. Keep entries newest first; the homepage automatically shows the first three. An optional `subject` field adds a subject label to that article only. Set `date` to the verified original publication date, or leave it null to omit a date. The generator creates article pages, language-specific indexes and the sitemap.

The reading layout is inspired by https://normaluhr.github.io/zh/p/score-function-centering/; its implementation is independent. Chinese copy is the published article text supplied by the author for this migration. The English version translates that text.

## Offline preview

Run `python scripts/package_preview.py` after building. The self-contained `bilingual-blog-preview.html` and source ZIP are written beside the checkout. Preview navigation supports the browser Back/Forward buttons, local anchors and external links; external sites open separately.

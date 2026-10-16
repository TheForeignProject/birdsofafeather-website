# Birds of a Feather website

This is the production repository for the Birds of a Feather website at [birdsofafeather.com.sg](https://birdsofafeather.com.sg/). The site is a static Tumult Hype export. A Python standard-library script prepares it for publication; no application build or package installation is needed.

Pushes to `main` automatically deploy the website to GitHub Pages through [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml). The workflow runs the publishing tests, then [`scripts/prepare_site.py`](scripts/prepare_site.py). Only the prepared `_site/` directory is published: the branded `index.html`, unchanged `birds website.hyperesources/`, icons, social image, `robots.txt` and `sitemap.xml`.

For a future designer export, replace `index.html` and the entire `birds website.hyperesources/` directory with the new export, run the local checks below, review the changes, and commit them to `main`. Preserve the generated directory name and structure exactly, including its space: the HTML and Hype scripts refer to those paths. Keep `site/`, `scripts/`, `tests/` and the deployment workflow. A local designer-sync skill may assist with this update; it is maintained outside the published repository.

## Production branding

[`site/seo-head.html`](site/seo-head.html) is the source of truth for the title and site name `Birds of a Feather`, description `Enter the World of Redefined Sichuan Flavours`, canonical URL, Open Graph and Twitter metadata, icons and `WebSite` JSON-LD. The canonical homepage is `https://birdsofafeather.com.sg/`. Preparation replaces conflicting metadata without modifying the original export, page body or Hype resources. Existing unrelated head content and JSON-LD entities are retained. If an export combines a `WebSite` entity with other entities, preparation fails so they can be merged deliberately without data loss.

[`site/icons/`](site/icons/) contains the unchanged official gray and white bird [256×256 source image](https://cdn.prod.website-files.com/60e31e7e6f31a6504b692ea3/60e31e7e6f31a626e9692ebe_bof-webclip.jpg) as `bof-webclip.jpg`, plus a 96×96 PNG, an ICO with 16×16, 32×32 and 48×48 versions, and a 180×180 Apple touch icon. The source SHA-256 is `29a74d8d5c110bbdea5399e1874a81ba56348e17a8f6eecea2c4eec108d8ff68`. The raster icons were downsampled with Pillow's Lanczos filter without redesigning the artwork. Pillow is only needed to regenerate those committed assets; publication uses the standard library. Icon links are relative so they also work at the default GitHub Pages repository path.

[`site/social-image.jpg`](site/social-image.jpg) preserves the official [Sichuan chicken photograph](https://cdn.prod.website-files.com/60e31e7e6f31a6504b692ea3/60e31e7e6f31a62b9e692ec8_bof-food-find-the-chicken-in-the-chillies-2.jpg). The template uses its absolute production URL for social previews. [`site/robots.txt`](site/robots.txt) and [`site/sitemap.xml`](site/sitemap.xml) use the same canonical domain.

## Local verification and preview

Run with Python 3.9 or newer from this repository:

```sh
python -m unittest discover -s tests -v
python scripts/prepare_site.py
python -m http.server 8000 --directory _site
```

Open `http://localhost:8000/` to preview the actual published website, including its title and icons. Viewing the raw export directly still shows the designer's original metadata. Preparation rebuilds only the generated `_site/` directory, removing obsolete files from previous previews. Do not put hand-maintained files there.

## Google Search follow-up

After a successful deployment, check the production homepage, `/favicon.png`, `/favicon.ico`, `/apple-touch-icon.png`, `/social-image.jpg`, `/robots.txt` and `/sitemap.xml` for HTTP 200 responses. Verify the live title is `Birds of a Feather` and validate its `WebSite` JSON-LD with [Schema Markup Validator](https://validator.schema.org/).

The domain owner should inspect `https://birdsofafeather.com.sg/` in [Google Search Console](https://search.google.com/search-console), run **Test live URL**, confirm that the rendered HTML includes the production metadata, and select **Request indexing**. Submit `https://birdsofafeather.com.sg/sitemap.xml` in the property's Sitemaps report. If the property is not verified, first complete the verification method Search Console provides.

Google selects the final search title, site name and favicon, and changes appear after recrawling: [title links](https://developers.google.com/search/docs/appearance/title-link), [site names](https://developers.google.com/search/docs/appearance/site-names), [favicon requirements](https://developers.google.com/search/docs/appearance/favicon-in-search).

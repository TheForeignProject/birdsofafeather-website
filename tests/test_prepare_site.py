"""Exercise the publication boundary with real files and only the stdlib."""

from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_site.py"
RESOURCES = "birds website.hyperesources"
HYPE_SCRIPT = "birdswebsite_hype_generated_script.js"


class HeadTags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PrepareSiteTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "Publishing script has not been implemented")
        spec = importlib.util.spec_from_file_location("prepare_site", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.prepare = module.prepare_site
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.source = Path(self.scratch.name)
        self.output = self.source / "_site"
        self.original = (
            b'<!DOCTYPE html>\r\n<html><head><title>birds website</title>'
            b'<meta name="viewport" content="width=440">'
            b'<style>body { background: #eee; }</style>'
            b'<script>const note = \'<meta name="description" content="keep script">\';</script>'
            b'<script>window.addEventListener("popstate", function () { designerHistory(); });</script>'
            b'<!-- <link rel="icon" href="keep-comment.png"> -->'
            b'</head>\r\n<body><script src="birds%20website.hyperesources/'
            b'birdswebsite_hype_generated_script.js?97637"></script>'
            b'<p>Caf\xc3\xa9</p></body></html>\r\n'
        )
        (self.source / "index.html").write_bytes(self.original)
        resources = self.source / RESOURCES
        (resources / "nested").mkdir(parents=True)
        (resources / HYPE_SCRIPT).write_bytes(b"Hype();\r\n")
        (resources / "nested" / "photo.jpg").write_bytes(bytes(range(256)))
        icons = self.source / "site" / "icons"
        icons.mkdir(parents=True)
        for name in ("favicon.png", "favicon.ico", "apple-touch-icon.png"):
            (icons / name).write_bytes(b"unchanged " + name.encode())
        (self.source / "site" / "seo-head.html").write_text(
            '<title>Birds of a Feather</title>\n'
            '<meta name="description" content="Enter the World of Redefined Sichuan Flavours">\n'
            '<meta property="og:title" content="Birds of a Feather">\n'
            '<meta property="og:site_name" content="Birds of a Feather">\n'
            '<meta property="og:url" content="https://birdsofafeather.com.sg/">\n'
            '<meta property="og:description" content="Enter the World of Redefined Sichuan Flavours">\n'
            '<meta property="og:type" content="website">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            '<meta name="twitter:title" content="Birds of a Feather">\n'
            '<link rel="canonical" href="https://birdsofafeather.com.sg/">\n'
            '<link rel="icon" href="favicon.ico">\n'
            '<link rel="icon" href="favicon.png">\n'
            '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
            '<meta name="apple-mobile-web-app-title" content="Birds of a Feather">\n'
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"WebSite",'
            '"name":"Birds of a Feather","url":"https://birdsofafeather.com.sg/"}</script>\n',
            encoding="utf-8",
        )
        (self.source / "site" / "robots.txt").write_bytes(b"User-agent: *\nAllow: /\nSitemap: https://birdsofafeather.com.sg/sitemap.xml\n")
        (self.source / "site" / "sitemap.xml").write_bytes(b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://birdsofafeather.com.sg/</loc></url></urlset>\n')
        (self.source / "site" / "social-image.jpg").write_bytes(b"official social image")
        self.router = b"/* production router */\r\ninstallRouter();\r\n"
        (self.source / "site" / "hype-hash-router.js").write_bytes(self.router)

    def publish_with_extra_head(self, extra):
        (self.source / "index.html").write_bytes(self.original.replace(b"</head>", extra + b"</head>"))
        self.prepare(self.source)
        return (self.output / "index.html").read_text(encoding="utf-8")

    def test_stages_branding_without_changing_export_body_or_resources(self):
        self.prepare(self.source)
        published_bytes = (self.output / "index.html").read_bytes()
        published = published_bytes.decode("utf-8")
        self.assertEqual(re.findall(r"<title>(.*?)</title>", published), ["Birds of a Feather"])
        self.assertEqual((self.source / "index.html").read_bytes(), self.original)
        self.assertEqual(published_bytes.split(b"</head>", 1)[1], self.original.split(b"</head>", 1)[1])
        self.assertIn('<meta name="viewport" content="width=440">', published)
        self.assertIn("const note = '<meta name=\"description\" content=\"keep script\">';", published)
        self.assertIn('<!-- <link rel="icon" href="keep-comment.png"> -->', published)
        for path in (self.source / RESOURCES).rglob("*"):
            if path.is_file():
                self.assertEqual((self.output / RESOURCES / path.relative_to(self.source / RESOURCES)).read_bytes(), path.read_bytes())
        for name in ("favicon.png", "favicon.ico", "apple-touch-icon.png"):
            self.assertEqual((self.output / name).read_bytes(), (self.source / "site" / "icons" / name).read_bytes())
        for name in ("robots.txt", "sitemap.xml"):
            self.assertEqual((self.output / name).read_bytes(), (self.source / "site" / name).read_bytes())
        self.assertEqual(set(path.name for path in self.output.iterdir()), {"index.html", RESOURCES, "favicon.png", "favicon.ico", "apple-touch-icon.png", "robots.txt", "sitemap.xml", "social-image.jpg", "hype-hash-router.js"})

    def test_router_is_blocking_at_end_of_head_after_designer_history_before_hype(self):
        self.prepare(self.source)
        published = (self.output / "index.html").read_bytes().decode("utf-8")
        scripts = [attrs for tag, attrs in HeadTags(published).tags if tag == "script"]
        routers = [attrs for attrs in scripts if attrs.get("src") == "hype-hash-router.js"]
        self.assertEqual(len(routers), 1)
        self.assertEqual(set(routers[0]), {"src", "data-hype-route-aliases"})
        self.assertEqual(json.loads(routers[0]["data-hype-route-aliases"]), {
            "menu": "mainmenu", "ourstory": "our story", "story": "our story",
        })
        router_position = published.index('<script src="hype-hash-router.js"')
        self.assertLess(published.index('window.addEventListener("popstate"'), router_position)
        self.assertRegex(published[router_position:], r'^<script [^>]+></script>\s*</head>')
        self.assertLess(router_position, published.index(HYPE_SCRIPT))
        self.assertEqual((self.output / "hype-hash-router.js").read_bytes(), self.router)

    def test_missing_router_preserves_entire_previous_output(self):
        self.prepare(self.source)
        (self.output / "preview-marker.txt").write_bytes(b"previous preview")
        previous = {path.relative_to(self.output): path.read_bytes()
                    for path in self.output.rglob("*") if path.is_file()}
        (self.source / "site" / "hype-hash-router.js").unlink()
        with self.assertRaisesRegex(ValueError, "hype-hash-router.js"):
            self.prepare(self.source)
        self.assertEqual({path.relative_to(self.output): path.read_bytes()
                          for path in self.output.rglob("*") if path.is_file()}, previous)

    def test_conflicting_metadata_is_replaced_including_case_and_rel_variants(self):
        old = (
            b'<META NAME="DESCRIPTION" CONTENT="stale description">'
            b'<meta property="description" content="stale property description">'
            b'<meta property="og:title" content="stale title">'
            b'<meta name="OG:IMAGE" content="stale.jpg">'
            b'<meta property="og:locale" content="stale locale">'
            b'<meta property="twitter:card" content="stale card">'
            b'<meta name="twitter:image" content="stale.jpg">'
            b'<meta name="apple-mobile-web-app-title" content="stale app title">'
            b'<LINK REL="CANONICAL" HREF="https://stale.example/">'
            b'<link rel="shortcut ICON" href="stale.ico">'
            b'<link rel="apple-touch-icon-precomposed" href="stale-apple.png">'
            b'<link rel="mask-icon" href="stale-mask.svg">'
            b'<script type="application/ld+json">{"@type":"WebSite","name":"stale website"}</script>'
            b'<script type="application/ld+json">{"@type":"Organization","name":"Preserved organization"}</script>'
            b'<link rel="stylesheet" href="preserved.css">'
        )
        published = self.publish_with_extra_head(old)
        self.assertNotIn("stale", published)
        tags = HeadTags(published).tags
        for attribute, value in (("name", "description"), ("property", "og:title"), ("name", "twitter:card"), ("name", "apple-mobile-web-app-title"), ("rel", "canonical"), ("rel", "apple-touch-icon")):
            self.assertEqual(sum(attrs.get(attribute) == value for tag, attrs in tags), 1, value)
        self.assertIn('"name":"Preserved organization"', published)
        self.assertIn('<link rel="stylesheet" href="preserved.css">', published)
        self.assertEqual(published.count('"@type":"WebSite"'), 1)
        for tag, attrs in tags:
            if tag == "link" and attrs.get("rel") in {"icon", "apple-touch-icon"}:
                self.assertFalse(attrs["href"].startswith("/"))

    def test_single_array_form_website_type_is_replaced(self):
        published = self.publish_with_extra_head(b'<script type="application/ld+json">{"@type":["WebSite"],"name":"stale"}</script>')
        self.assertNotIn("stale", published)
        self.assertEqual(published.count('"@type":"WebSite"'), 1)

    def test_mixed_website_entities_fail_before_replacing_previous_site(self):
        self.prepare(self.source)
        previous = (self.output / "index.html").read_bytes()
        for data in (
            {"@graph": [{"@type": "WebSite"}, {"@type": "Organization"}]},
            [{"@type": ["WebSite"]}, {"@type": "Organization"}],
            {"@type": ["WebSite", "Organization"]},
            {"@type": "WebSite", "@graph": [{"@type": "Organization"}]},
        ):
            with self.subTest(data=data):
                extra = ('<script type="application/ld+json">' + json.dumps(data) + '</script>').encode()
                (self.source / "index.html").write_bytes(self.original.replace(b"</head>", extra + b"</head>"))
                with self.assertRaisesRegex(ValueError, "merge"):
                    self.prepare(self.source)
                self.assertEqual((self.output / "index.html").read_bytes(), previous)

    def test_new_export_rebuild_removes_stale_published_assets(self):
        self.prepare(self.source)
        (self.output / "stale.txt").write_text("old output")
        (self.source / RESOURCES / "nested" / "photo.jpg").unlink()
        (self.source / "index.html").write_bytes(self.original.replace(b"<title>birds website</title>", b"<title>new export</title>"))
        self.prepare(self.source)
        self.assertIn(b"<title>Birds of a Feather</title>", (self.output / "index.html").read_bytes())
        self.assertFalse((self.output / "stale.txt").exists())
        self.assertFalse((self.output / RESOURCES / "nested" / "photo.jpg").exists())
        published = (self.output / "index.html").read_bytes()
        self.assertEqual(published.count(b'src="hype-hash-router.js"'), 1)
        self.assertEqual((self.output / "hype-hash-router.js").read_bytes(), self.router)
        self.assertEqual(published.split(b"</head>", 1)[1], self.original.split(b"</head>", 1)[1])

    def test_id_only_related_entities_require_merge_and_preserve_previous_site(self):
        self.prepare(self.source)
        previous = (self.output / "index.html").read_bytes()
        for data in (
            {"@type": "WebSite", "@graph": [{"@id": "https://example.com/#org", "name": "Organization to preserve"}]},
            {"@type": "WebSite", "@graph": []},
            {"@type": "WebSite", "publisher": {"@id": "https://example.com/#org", "name": "Organization to preserve"}},
        ):
            with self.subTest(data=data):
                extra = ('<script type="application/ld+json">' + json.dumps(data) + '</script>').encode()
                (self.source / "index.html").write_bytes(self.original.replace(b"</head>", extra + b"</head>"))
                with self.assertRaisesRegex(ValueError, "merge"):
                    self.prepare(self.source)
                self.assertEqual((self.output / "index.html").read_bytes(), previous)

    def test_social_image_is_copied_unchanged(self):
        (self.source / "site" / "social-image.jpg").write_bytes(b"official social image")
        self.prepare(self.source)
        self.assertEqual((self.output / "social-image.jpg").read_bytes(), b"official social image")

    def test_missing_social_image_fails_without_replacing_previous_site(self):
        social = self.source / "site" / "social-image.jpg"
        social.write_bytes(b"official social image")
        self.prepare(self.source)
        previous = (self.output / "index.html").read_bytes()
        social.unlink()
        with self.assertRaisesRegex(ValueError, "social-image.jpg"):
            self.prepare(self.source)
        self.assertEqual((self.output / "index.html").read_bytes(), previous)
        self.assertEqual((self.output / "social-image.jpg").read_bytes(), b"official social image")

    def test_missing_required_inputs_fail_without_replacing_previous_site(self):
        self.prepare(self.source)
        previous = (self.output / "index.html").read_bytes()
        for relative in (
            "index.html", RESOURCES + "/" + HYPE_SCRIPT,
            "site/seo-head.html", "site/hype-hash-router.js", "site/icons/favicon.png",
            "site/icons/favicon.ico", "site/icons/apple-touch-icon.png",
            "site/robots.txt", "site/sitemap.xml",
        ):
            with self.subTest(path=relative):
                path = self.source / relative
                contents = path.read_bytes()
                path.unlink()
                with self.assertRaises(ValueError):
                    self.prepare(self.source)
                self.assertEqual((self.output / "index.html").read_bytes(), previous)
                path.write_bytes(contents)

    def test_missing_script_reference_fails_before_publication(self):
        (self.source / "index.html").write_bytes(self.original.replace(HYPE_SCRIPT.encode(), b"wrong.js"))
        with self.assertRaisesRegex(ValueError, "Hype script reference"):
            self.prepare(self.source)
        self.assertFalse(self.output.exists())

    def test_body_crossing_head_fails_without_replacing_previous_site(self):
        self.prepare(self.source)
        previous = (self.output / "index.html").read_bytes()
        malformed = self.original.replace(b"</head>", b"<body>crossed boundary</head>")
        (self.source / "index.html").write_bytes(malformed)
        with self.assertRaisesRegex(ValueError, "head|body"):
            self.prepare(self.source)
        self.assertEqual((self.output / "index.html").read_bytes(), previous)

    def test_invalid_head_title_or_jsonld_fails_before_publication(self):
        for html in (
            b"<html><body>No head</body></html>",
            self.original.replace(b"</head>", b""),
            self.original.replace(b"</head>", b"<title>duplicate</title></head>"),
            self.original.replace(b"<title>birds website</title>", b""),
            self.original.replace(b"</head>", b'<script type="application/ld+json">{broken}</script></head>'),
        ):
            with self.subTest(html=html):
                (self.source / "index.html").write_bytes(html)
                with self.assertRaises(ValueError):
                    self.prepare(self.source)
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

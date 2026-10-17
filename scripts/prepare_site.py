"""Stage the Hype export with production branding, using only the stdlib."""

from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys


RESOURCES = "birds website.hyperesources"
HYPE_SCRIPT = "birdswebsite_hype_generated_script.js"
ICONS = ("favicon.png", "favicon.ico", "apple-touch-icon.png")
STATIC_FILES = ("robots.txt", "sitemap.xml", "social-image.jpg")
ROUTER_SCRIPT = "hype-hash-router.js"
ROUTER_HEAD = (
    '<script src="hype-hash-router.js" '
    'data-hype-route-aliases=\'{"menu":"mainmenu","ourstory":"our story","story":"our story"}\'></script>'
)


class HeadTags(HTMLParser):
    """Locate real tags without rewriting markup or matching script strings."""

    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.lines = [0]
        self.lines.extend(index + 1 for index, character in enumerate(html) if character == "\n")
        self.starts = []
        self.ends = []
        self.scripts = []
        self.open_script = None
        self.feed(html)

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.source_offset()
        end = start + len(self.get_starttag_text())
        attributes = dict(attrs)
        self.starts.append((tag, start, end, attributes))
        if tag == "script":
            self.open_script = (start, end, attributes)

    def handle_endtag(self, tag):
        start = self.source_offset()
        end = self.html.find(">", start) + 1
        self.ends.append((tag, start, end))
        if tag == "script" and self.open_script is not None:
            opening, content, attrs = self.open_script
            self.scripts.append((opening, end, attrs, self.html[content:start]))
            self.open_script = None


def is_website(node):
    types = node.get("@type") if isinstance(node, dict) else None
    return types == "WebSite" or isinstance(types, list) and "WebSite" in types


def contains_website(node):
    if isinstance(node, dict):
        return is_website(node) or any(contains_website(value) for value in node.values())
    return isinstance(node, list) and any(contains_website(value) for value in node)


def contains_entity(node):
    if isinstance(node, dict):
        return "@type" in node or "@id" in node or any(contains_entity(value) for value in node.values())
    return isinstance(node, list) and any(contains_entity(value) for value in node)


def brand_head(html, template):
    """Replace controlled head metadata while retaining all other text verbatim."""
    tags = HeadTags(html)
    heads = [tag for tag in tags.starts if tag[0] == "head"]
    head_ends = [tag for tag in tags.ends if tag[0] == "head"]
    if len(heads) != 1 or len(head_ends) != 1 or heads[0][2] > head_ends[0][1]:
        raise ValueError("Expected exactly one complete <head> in the Hype export")
    begin, end = heads[0][2], head_ends[0][1]
    if any(tag == "body" and start < end for tag, start, finish, attrs in tags.starts):
        raise ValueError("The Hype export body must begin after the closing head tag")
    titles = [tag for tag in tags.starts if tag[0] == "title"]
    title_ends = [tag for tag in tags.ends if tag[0] == "title"]
    if (len(titles) != 1 or len(title_ends) != 1
            or not begin <= titles[0][1] < titles[0][2] <= title_ends[0][1] < title_ends[0][2] <= end):
        raise ValueError("Expected exactly one complete <title> in the Hype export head")
    removed = [(titles[0][1], title_ends[0][2])]
    for tag, start, finish, attrs in tags.starts:
        if not begin <= start < finish <= end:
            continue
        if tag == "meta":
            keys = ((attrs.get(key) or "").strip().lower() for key in ("name", "property"))
            if any(key in {"description", "apple-mobile-web-app-title"}
                   or key.startswith(("og:", "twitter:")) for key in keys):
                removed.append((start, finish))
        elif tag == "link":
            rel = set((attrs.get("rel") or "").lower().split())
            if rel & {"canonical", "icon", "mask-icon", "apple-touch-icon", "apple-touch-icon-precomposed"}:
                removed.append((start, finish))
    for start, finish, attrs, content in tags.scripts:
        if not begin <= start < finish <= end:
            continue
        if (attrs.get("type") or "").split(";", 1)[0].strip().lower() != "application/ld+json":
            continue
        data = json.loads(content)
        if not contains_website(data):
            continue
        simple_website = is_website(data) and data["@type"] in ("WebSite", ["WebSite"]) and "@graph" not in data
        if simple_website and not any(contains_entity(value) for key, value in data.items() if key != "@type"):
            removed.append((start, finish))
        else:
            raise ValueError("Existing WebSite in mixed JSON-LD: merge it into site/seo-head.html before publishing")
    content = html[begin:end]
    for start, finish in sorted(removed, reverse=True):
        content = content[:start - begin] + content[finish - begin:]
    return html[:begin] + content + "\n" + template.rstrip() + "\n" + html[end:]


def prepare_site(source):
    """Publish to source/_site; never edit the input index or Hype resources."""
    source = Path(source).resolve()
    output = source / "_site"
    required = [source / "index.html", source / RESOURCES / HYPE_SCRIPT,
                source / "site" / "seo-head.html", source / "site" / ROUTER_SCRIPT]
    required.extend(source / "site" / "icons" / name for name in ICONS)
    required.extend(source / "site" / name for name in STATIC_FILES)
    for path in required:
        if not path.is_file():
            label = "Hype script" if path.name == HYPE_SCRIPT else "required file"
            raise ValueError(f"Missing {label}: {path}")

    # Byte reads retain the original UTF-8 export's line endings.
    original = (source / "index.html").read_bytes().decode("utf-8")
    template = (source / "site" / "seo-head.html").read_bytes().decode("utf-8")
    published = brand_head(original, template.rstrip() + "\n" + ROUTER_HEAD).encode("utf-8")
    if f"{RESOURCES.replace(' ', '%20')}/{HYPE_SCRIPT}" not in original:
        raise ValueError("Hype script reference is missing from index.html")

    # Validate before cleanup, and never follow a redirected output directory.
    if output.is_symlink() or output.resolve() != output:
        raise ValueError("Refusing to replace a redirected _site directory")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    shutil.copytree(source / RESOURCES, output / RESOURCES)
    (output / "index.html").write_bytes(published)
    for name in ICONS:
        shutil.copyfile(source / "site" / "icons" / name, output / name)
    for name in STATIC_FILES:
        shutil.copyfile(source / "site" / name, output / name)
    shutil.copyfile(source / "site" / ROUTER_SCRIPT, output / ROUTER_SCRIPT)
    return output


if __name__ == "__main__":
    try:
        destination = prepare_site(Path(__file__).resolve().parents[1])
    except (ValueError, OSError) as error:
        print(f"Site preparation failed: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"Prepared production website: {destination}")

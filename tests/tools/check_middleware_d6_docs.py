"""Kiểm tài liệu D6 offline; chạy bằng Python có Playwright, không chạy sản phẩm."""

import argparse
import collections
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids = []
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag in ("a", "link", "script"):
            ref = attrs.get("href") or attrs.get("src")
            if ref:
                self.links.append(ref)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    docs = root / "agent_workspace/tasks/middleware"
    evidence = {"scope": "D6 documentation only; product gates NOT RUN", "checks": {}}
    checked = 0
    for file in (docs / "index.html", docs / "packet-security.html"):
        source = file.read_text()
        page = Page(source)
        assert not [i for i, count in collections.Counter(page.ids).items() if count > 1]
        for link in page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = (file.parent / unquote(parsed.path)).resolve() if parsed.path else file
            assert target.exists(), (file, link)
            if parsed.fragment and target.suffix == ".html":
                assert unquote(parsed.fragment) in Page(target.read_text()).ids, (file, link)
            checked += 1
        for svg in re.findall(r"<svg\b.*?</svg>", source, flags=re.S):
            ET.fromstring(svg)
    evidence["checks"]["local_links_and_svg"] = {"pass": True, "links": checked}

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        context = browser.new_context()
        # File pages use only local resources. Block network to prove offline reading.
        context.route("http://**/*", lambda route: route.abort())
        context.route("https://**/*", lambda route: route.abort())
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        url = (docs / "packet-security.html").as_uri() + "#decision-d6"
        for name, width in (("desktop", 1440), ("mobile", 390)):
            page.set_viewport_size({"width": width, "height": 1000})
            page.goto(url)
            page.locator("#decision-d6").scroll_into_view_if_needed()
            page.screenshot(path=str(args.output / f"{name}-top.png"))
            page.locator("#decision-d6").screenshot(path=str(args.output / f"{name}-card.png"))
            size = page.evaluate("({viewport: innerWidth, document: document.documentElement.scrollWidth})")
            assert size["viewport"] == size["document"], size
            assert page.locator("#decision-d6 .d6-gates tbody tr").count() == 7
            assert page.locator("#decision-d6 svg").count() == 2
            evidence["checks"][name] = {"pass": True, **size}

        page.set_viewport_size({"width": 1440, "height": 1000})
        for diagram in ("d6-cutover", "d6-recovery"):
            for label in ("Phóng to", "Mã nguồn"):
                button = page.locator(f"#{diagram} button").filter(has_text=re.compile("^" + label + "$"))
                button.click()
                assert page.locator("dialog[open]").count() == 1
                if label == "Mã nguồn":
                    assert "<svg" in page.locator("dialog pre").inner_text()
                else:
                    assert page.locator("dialog svg").count() == 1
                ids = page.locator("[id]").evaluate_all("els => els.map(e => e.id)")
                assert len(ids) == len(set(ids))
                page.keyboard.press("Escape")
                assert page.locator("dialog[open]").count() == 0
                assert button.evaluate("e => e === document.activeElement")
        evidence["checks"]["zoom_source_escape_focus"] = {"pass": True, "dialogs": 4}
        page.emulate_media(media="print")
        assert page.locator("#decision-d6 .dg-tools").first.is_hidden()
        page.pdf(path=str(args.output / "report.pdf"), format="A4", print_background=True,
                 margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
        evidence["checks"]["print_rendered"] = {"pass": True, "visual_scope": "D6 pages inspected separately"}

        nojs = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 1000})
        nojs.route("http://**/*", lambda route: route.abort())
        nojs.route("https://**/*", lambda route: route.abort())
        plain = nojs.new_page()
        plain.goto(url)
        assert plain.locator("#d6-cutover svg").is_visible()
        assert plain.locator("#d6-recovery svg").is_visible()
        assert plain.locator("#decision-d6 .d6-gates tbody tr").count() == 7
        evidence["checks"]["offline_nojs"] = {"pass": True}
        assert not errors, errors
        evidence["checks"]["js_errors"] = errors
        browser.close()
    result = args.output / "checks.json"
    result.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(evidence, ensure_ascii=False))


if __name__ == "__main__":
    main()

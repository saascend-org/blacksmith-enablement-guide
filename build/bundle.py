#!/usr/bin/env python3
"""Bundle the six-page enablement guide (../Blacksmith/enablement-guide) into ONE self-contained page:
pages become in-page views switched by the URL hash, CSS/JS are inlined and every screenshot becomes a data URI.
build/encrypt.js then encrypts it, so the encrypted gate is the only place the guide exists on the public site.
Output: build/index.plain.html (git-ignored; never commit it).
"""
import base64, re
from pathlib import Path

B = Path(__file__).resolve().parent
SRC = Path.home() / "Work/SaaScend/Blacksmith/enablement-guide"
PAGES = ["index", "start", "journey", "capabilities", "rollout", "reference"]


def uri(rel):
    p = SRC / "assets" / rel
    mime = {"png": "image/png", "jpg": "image/jpeg"}[p.suffix[1:]]
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def links(s):
    """journey.html#commit -> #commit ; start.html -> #pg-start ; index.html -> #pg-index"""
    s = re.sub(r"\b(?:%s)\.html#" % "|".join(PAGES), "#", s)
    return re.sub(r"\b(%s)\.html\b" % "|".join(PAGES), r"#pg-\1", s)


def images(s):
    return re.sub(r"assets/((?:screens/)?[\w.-]+\.(?:png|jpg))", lambda m: uri(m.group(1)), s)


views, nav, footer, overlays = [], None, None, None
for name in PAGES:
    html = (SRC / f"{name}.html").read_text()
    if nav is None:
        nav = re.search(r'<div id="scrollbar"></div>\s*(<nav class="top">.*?</nav>)', html, re.S).group(1)
        footer = re.search(r"(<footer>.*?</footer>)", html, re.S).group(1)
        overlays = re.search(r'(<div class="lb" id="lb">.*?<div class="toast" id="toast"></div>)', html, re.S).group(1)
    body = re.search(r"</nav>(.*?)<footer>", html, re.S).group(1)
    views.append(f'<section class="pg" id="pg-{name}">{body}</section>')

css = (SRC / "assets/site.css").read_text() + "\n.pg{display:none}.pg.on{display:block}\n"
data = (SRC / "assets/data.js").read_text()
data = data.replace("const S = f => `assets/screens/${f}.png`;", "const S = f => IMG[`screens/${f}.png`];")
site = (SRC / "assets/site.js").read_text().replace("assets/${s.shot.src}", "${IMG[s.shot.src]}")
imgmap = "const IMG = {" + ",".join(f'"screens/{p.name}":"{uri("screens/" + p.name)}"'
                                     for p in sorted((SRC / "assets/screens").glob("*.png"))) + "};"
router = """
// one document, six views: show the view that holds the hash target (a view id or any element inside one)
function route(){
  const h=decodeURIComponent(location.hash.slice(1))||"pg-index";
  const el=document.getElementById(h)||document.getElementById("pg-index");
  const pg=el.classList.contains("pg")?el:el.closest(".pg");
  document.querySelectorAll(".pg").forEach(p=>p.classList.toggle("on",p===pg));
  document.querySelectorAll("nav.top .links a").forEach(a=>a.classList.toggle("on",a.getAttribute("href")==="#"+pg.id));
  if(el===pg)scrollTo(0,0);else setTimeout(()=>el.scrollIntoView({block:"start"}),30);
}
addEventListener("hashchange",route);route();
"""
page = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
<title>Blacksmith on Salesforce · SaaScend</title>
<style>{css}</style>
</head>
<body>
<div id="scrollbar"></div>
{images(links(nav))}
{images(links("".join(views)))}
{images(links(footer))}
{overlays}
<script>{imgmap}</script>
<script>{images(links(data))}</script>
<script>{links(site)}</script>
<script>{router}</script>
</body>
</html>
"""
(B / "index.plain.html").write_text(page)
left = re.findall(r'(?:src|href|data-zoom)="(?!data:|#|https?:)[^"]+"', page)
print(f"bundled {len(PAGES)} views -> build/index.plain.html ({len(page):,} bytes); unresolved local refs: {left[:5] or 'none'}")

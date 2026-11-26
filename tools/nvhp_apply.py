#!/usr/bin/env python3
"""Nieuwe upload van de vergelijkingstool (BijMij-/tool-opmaak) omzetten naar de NVHP-site.

Gebruik (vanuit de repo-map):
    python3 tools/nvhp_apply.py /pad/naar/verzilveren_NN.html

Neemt van de upload: alle data, de JavaScript-functies en de basis-CSS.
Neemt van de huidige index.html (de 'donor'): het site-omhulsel, dus lettertypes,
site-opmaak + NVHP-huisstijl, menu met logo, kop-opmaak, footer en de NVHP-
instellingen in meta (label, titel, site, merk, menu, contact).
Draait daarna tools/seo_build.py. Het script stopt met een melding als een
verwacht stuk in de upload ontbreekt, zodat er nooit half omgezette pagina's
live gaan.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / 'index.html'
SITE = 'https://woningverzilveraar.nl/'
META_VAN_DONOR = ['label', 'titel', 'titelTab', 'site', 'merk', 'menu', 'contact']


def fout(msg):
    sys.exit('Gestopt: ' + msg)


def een(s, oud, nieuw, wat):
    n = s.count(oud)
    if n != 1:
        fout(f'{wat}: {n}x gevonden in de upload (verwacht 1)')
    return s.replace(oud, nieuw)


def data(s):
    m = re.search(r'(<script[^>]*id="data"[^>]*>)(.*?)(</script>)', s, re.S)
    if not m:
        fout('datablok ontbreekt')
    return m, json.loads(m.group(2))


def main():
    if len(sys.argv) != 2:
        fout('geef het pad van de upload mee')
    up = Path(sys.argv[1]).read_text(encoding='utf-8')
    donor = PAGE.read_text(encoding='utf-8')
    s = up

    # ---- head: canonical, og:url, lettertypes ----
    s = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{SITE}">', s, count=1)
    s = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{SITE}">', s, count=1)
    s = re.sub(r'<link rel="preconnect"[^>]*>\n?', '', s)
    s = re.sub(r'<link href="https://fonts.googleapis.com/css2[^>]*>\n?', '', s)
    fonts = ''.join(re.findall(r'<link rel="preconnect"[^>]*>\n|<link href="https://fonts.googleapis.com/css2[^>]*>\n', donor))
    if 'League+Spartan' not in fonts:
        fout('lettertype-links niet gevonden in huidige index.html')
    s = re.sub(r'(<meta name="robots" content="[^"]*">\n)', lambda m: m.group(1) + fonts, s, count=1)

    # ---- CSS: basis van upload + site-laag van donor ----
    dcss = re.search(r'<style>(.*?)</style>', donor, re.S).group(1)
    i = dcss.find('/* ================= Basisstijl ================= */')
    if i < 0:
        fout('site-laag (Basisstijl) niet gevonden in huidige index.html')
    site_laag = re.sub(r'/\*SEO:CSS\*/.*?/\*/SEO:CSS\*/\s*', '', dcss[i:], flags=re.S)
    if 'Basisstijl' in s or 'BijMij huisstijl' in s:
        fout('upload heeft al een site-laag; vergelijk handmatig')
    s = een(s, '</style>', '\n' + site_laag.strip() + '\n</style>', 'einde stijlblok')
    s = s.replace("'Fraunces',Georgia,serif", "'League Spartan',sans-serif").replace("'Fraunces',serif", "'League Spartan',sans-serif")

    # ---- HTML-omhulsel ----
    s = re.sub(r'<nav id="sitenav" hidden></nav>|<div id="sitenav" hidden></div>', '<nav id="sitenav" hidden></nav>', s, count=1)
    if '<header><div class="wrap">' not in s:
        hm = re.search(r'<header>(.*?)</header>', s, re.S)
        if not hm:
            fout('header niet gevonden')
        s = s[:hm.start()] + '<header><div class="wrap">' + hm.group(1) + '</div></header>' + s[hm.end():]
    s = re.sub(r'<div class="balk">', '<div class="balk" style="display:none">', s, count=1)
    s = re.sub(r'<div class="voetnoot">.*?</div></div>\n?', '', s, count=1, flags=re.S)
    dfoot = re.search(r'<footer>.*?</footer>', donor, re.S).group(0)
    s = re.sub(r'<footer>.*?</footer>', lambda _: dfoot, s, count=1, flags=re.S)
    if 'assets/embed.js' not in s:
        fout('insluitscript (assets/embed.js) ontbreekt in de footer van de huidige index.html')

    # ---- JavaScript: menu met logo, contactregel ----
    dnav = re.search(r"^ *var nv=\$\('#sitenav'\).*$", donor, re.M)
    unav = re.search(r"^ *var nv=\$\('#sitenav'\).*$", s, re.M)
    if not dnav or not unav:
        fout('menu-opbouw niet gevonden')
    s = s[:unav.start()] + dnav.group(0) + s[unav.end():]
    s = s.replace("var cv=$('#contactvoet');cv.hidden=false;cv.textContent=D.meta.contact;",
                  "var cv=$('#contactvoet');if(cv){cv.hidden=false;cv.textContent=D.meta.contact;}")

    # ---- meta-instellingen uit donor ----
    _, Dd = data(donor)
    m, Du = data(s)
    for k in META_VAN_DONOR:
        if k in Dd['meta']:
            Du['meta'][k] = Dd['meta'][k]
    s = s[:m.start(2)] + '\n' + json.dumps(Du, ensure_ascii=False, indent=1).replace('</', '<\\/') + '\n' + s[m.end(2):]

    rest = re.findall(r'.{0,40}(?:bijmij|BijMij|Spoorpad|83202072|dennesroes).{0,40}', s)
    PAGE.write_text(s, encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'seo_build.py')], check=True)
    if rest:
        print('Let op, mogelijk nog BijMij-tekst in de data:')
        for r in rest[:10]:
            print('  ', r)
    print(f"Omgezet: peildatum {Du['meta'].get('peildatum')}, versie {Du['meta'].get('versie')}, {len(Du['proposities'])} producten.")


if __name__ == '__main__':
    main()

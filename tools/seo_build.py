#!/usr/bin/env python3
"""SEO/GEO-onderdelen van woningverzilveraar.nl opnieuw opbouwen uit de productdata.

Gebruik (vanuit de repo-map):  python3 tools/seo_build.py

Draai dit na elke nieuwe versie van index.html. Het script is idempotent:
blokken tussen <!--SEO:...--> markers worden vervangen, ontbrekende markers
worden op een vaste plek ingevoegd. Werkt ook als de upload nog in BijMij-
opmaak is niet: zet eerst de NVHP-aanpassingen terug.
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / 'index.html'
SITE = 'https://woningverzilveraar.nl/'
NVHP = 'https://www.hypothecairplanner.nl/'
THEMA = 'https://www.hypothecairplanner.nl/themas/verzilveren-overwaarde-opnemen'
ADVISEUR = 'https://www.hypothecairplanner.nl/zoek-een-hypotheekadviseur-voor-het-beste-advies'
LOGO = SITE + 'assets/nvhp-logo.png'

TITEL = 'Woning verzilveren: verzilverhypotheken vergelijken | NVHP'
H1 = 'Woning verzilveren'
MAANDEN = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus',
           'september', 'oktober', 'november', 'december']

e = lambda s: html.escape(str(s or ''), quote=True)


def iso(peildatum):
    m = re.match(r'(\d{1,2}) (\w+) (\d{4})', peildatum or '')
    if not m or m.group(2).lower() not in MAANDEN:
        sys.exit(f'Peildatum niet herkend: {peildatum!r}')
    return f'{m.group(3)}-{MAANDEN.index(m.group(2).lower()) + 1:02d}-{int(m.group(1)):02d}'


def blok(s, naam, inhoud, anker, voor=True):
    """Vervang het blok tussen SEO-markers, of voeg het in bij anker.
    HTML-blokken gebruiken <!--SEO:naam-->, het CSS-blok /*SEO:CSS*/ (een HTML-commentaar breekt CSS)."""
    if naam == 'CSS':
        a, z = '/*SEO:CSS*/', '/*/SEO:CSS*/'
    else:
        a, z = f'<!--SEO:{naam}-->', f'<!--/SEO:{naam}-->'
    nieuw = f'{a}\n{inhoud}\n{z}'
    pat = re.compile(re.escape(a) + '.*?' + re.escape(z), re.S)
    if pat.search(s):
        return pat.sub(lambda _: nieuw, s, count=1)
    if s.count(anker) != 1:
        sys.exit(f'Anker voor {naam} niet (uniek) gevonden: {anker!r}')
    return s.replace(anker, nieuw + '\n' + anker if voor else anker + '\n' + nieuw)


def main():
    s = PAGE.read_text(encoding='utf-8')
    m = re.search(r'(<script[^>]*id="data"[^>]*>)(.*?)(</script>)', s, re.S)
    D = json.loads(m.group(2))
    meta, P = D['meta'], D['proposities']
    def status(p):
        if p.get('status') == 'gestopt':
            return 'Niet meer verkrijgbaar'
        if p.get('verwacht'):
            return 'Nog niet verkrijgbaar'
        return 'Verkrijgbaar'
    actief = [p for p in P if status(p) == 'Verkrijgbaar']
    gestopt = [p for p in P if p.get('status') == 'gestopt']
    cat = {c['id']: c for c in D.get('categorieen', [])}
    datum = iso(meta['peildatum'])
    naam = lambda p: f"{p['aanbieder']} – {p['product']}"
    aanbieders = sorted({p['aanbieder'] for p in actief}, key=str.lower)

    beschrijving = (f"Overwaarde opnemen zonder te verhuizen? Vergelijk {len(actief)} verzilver- en "
                    f"seniorenhypotheken van {len(aanbieders)} aanbieders op leeftijd, maximum, rente en "
                    f"voorwaarden. NVHP-overzicht, peildatum {meta['peildatum']}.")

    # ---- data: titels en menu ----
    meta['titelTab'] = TITEL
    meta['titel'] = H1
    meta['label'] = 'NVHP · Thema Verzilveren'
    menu = meta.setdefault('menu', [])
    if not any(x.get('u') == ADVISEUR for x in menu):
        menu.append({'t': 'Vind een adviseur', 'u': ADVISEUR})
    s = s[:m.start(2)] + '\n' + json.dumps(D, ensure_ascii=False, indent=1).replace('</', '<\\/') + '\n' + s[m.end(2):]

    # ---- head: title, description, og ----
    s = re.sub(r'<title>.*?</title>', f'<title>{e(TITEL)}</title>', s, count=1, flags=re.S)
    s = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(beschrijving)}">', s, count=1)
    s = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(TITEL)}">', s, count=1)
    s = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(beschrijving)}">', s, count=1)
    s = re.sub(r'<meta name="theme-color" content="[^"]*">', '<meta name="theme-color" content="#234765">', s, count=1)
    s = re.sub(r'<meta name="robots" content="[^"]*">', '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">', s, count=1)

    # ---- statische tekst in header (zichtbaar zonder JavaScript) ----
    for k in ['label', 'titel', 'subtitel', 'peildatum', 'versie']:
        s = re.sub(rf'(<(\w+)[^>]*data-m="{k}"[^>]*>).*?(</\2>)',
                   lambda mm: mm.group(1) + e(meta.get(k, '')) + mm.group(3), s, count=1, flags=re.S)

    # ---- FAQ (zichtbaar) ----
    def lijst(veld):
        return '<ul>' + ''.join(
            f"<li><b>{e(naam(p))}</b>{'' if status(p) == 'Verkrijgbaar' else ' (' + status(p).lower() + ')'}: {e(p.get(veld) or 'niet bekend')}</li>"
            for p in P) + '</ul>'

    faq = [
        ('Wat is woning verzilveren?',
         '<p>Woning verzilveren is geld opnemen uit de overwaarde van je koopwoning zonder te verhuizen. '
         'De overwaarde is de marktwaarde van je woning min je hypotheekschuld. Je leent tegen die overwaarde, '
         'met een hypotheek die speciaal voor senioren is bedoeld. Het geld kun je ineens of per maand opnemen, afhankelijk van de aanbieder.</p>'),
        ('Welke soorten verzilverhypotheken zijn er?',
         '<ul>' + ''.join(f"<li><b>{e(c['naam'])}</b> ({sum(1 for p in actief if p.get('cat') == c['id'])} verkrijgbaar): {e(c['uitleg'])}</li>"
                          for c in cat.values()) + '</ul>'),
        ('Vanaf welke leeftijd kun je je woning verzilveren?',
         '<p>Dat verschilt per aanbieder:</p>' + lijst('minLeeftijd')),
        ('Hoeveel kan ik maximaal opnemen?',
         '<p>Het maximum hangt af van je leeftijd, de marktwaarde van je woning en een eventuele bestaande hypotheek. '
         'Bij sommige aanbieders telt ook je inkomen mee. Het maximum op basis van de marktwaarde per aanbieder:</p>' + lijst('maxLtv')),
        ('Wat gebeurt er als de schuld hoger wordt dan de woningwaarde?',
         '<p>Bij rente bijschrijven groeit de schuld door rente op rente. Of je dan een restschuld kunt overhouden, hangt af van de voorwaarden:</p>' + lijst('restschuld')),
        ('Wat gebeurt er bij overlijden?',
         lijst('overlijden')),
        ('Heb ik advies nodig bij het verzilveren van mijn woning?',
         '<p>Deze vergelijking is informatie en geen advies. Een verzilverhypotheek heeft gevolgen voor je vermogen, je erfgenamen '
         'en je mogelijkheden om later te verhuizen of zorg te betalen. Een Erkend Hypothecair Planner kijkt naar je hele situatie. '
         f'<a href="{ADVISEUR}">Zoek een adviseur bij de NVHP</a>.</p>'),
        ('Wie maakt deze vergelijking?',
         f'<p>Deze vergelijkingstool hoort bij het <a href="{THEMA}">NVHP-thema Verzilveren</a> van de Nederlandse Vereniging van '
         f'Hypothecair Planners. De gegevens komen uit de openbare productinformatie en voorwaarden van de aanbieders (zie Bronnen). '
         f'Peildatum: {e(meta["peildatum"])}. De offerte en de voorwaarden van de aanbieder zijn leidend.</p>'),
    ]
    faq_html = ('<section id="veelgestelde-vragen" class="faq">\n  <h2>Veelgestelde vragen over woning verzilveren</h2>\n'
                + ''.join(f'  <details class="acc faqitem"><summary><h3>{e(q)}</h3></summary><div class="faqtekst">{a}</div></details>\n' for q, a in faq)
                + '</section>')

    # ---- productoverzicht voor zoekmachines zonder JavaScript ----
    rijen = ''.join(
        f"<tr><td>{e(p['aanbieder'])}</td><td>{e(p['product'])}</td><td>{status(p)}</td>"
        f"<td>{e(p.get('minLeeftijd'))}</td><td>{e(p.get('maxLtv'))}</td><td>{e(p.get('maxBedrag'))}</td><td>{e(p.get('rentevast'))}</td><td>{e(p.get('opname'))}</td></tr>"
        for p in P)
    noscript = ('<noscript><section><h2>Overzicht verzilverhypotheken (peildatum ' + e(meta['peildatum']) + ')</h2>'
                '<div class="tabelwrap"><table><thead><tr><th>Aanbieder</th><th>Product</th><th>Status</th><th>Minimumleeftijd</th>'
                '<th>Maximum op basis van marktwaarde</th><th>Maximaal bedrag</th><th>Rentevast</th><th>Geld vrij</th></tr></thead><tbody>'
                + rijen + '</tbody></table></div></section></noscript>')
    s = blok(s, 'FAQ', faq_html + '\n' + noscript, '</main>')

    # ---- adviesblok onder de kop + footerverwijzing + stijl ----
    advies = (f'<aside class="adviesblok" aria-label="Geen advies">\n'
              f'  <p><b>Dit is informatie, geen advies.</b> Of verzilveren bij je past, hangt af van je inkomen, je woning, '
              f'je wensen en je erfgenamen. Laat je adviseren door een Erkend Hypothecair Planner.</p>\n'
              f'  <a class="adviesknop" href="{ADVISEUR}">Zoek een adviseur bij de NVHP</a>\n</aside>')
    s = blok(s, 'ADVIES', advies, '</div></header>')
    s = blok(s, 'VOETADVIES',
             f'<p class="voetadvies">Deze pagina is informatie en geen advies. De offerte en de voorwaarden van de aanbieder zijn leidend. '
             f'<a href="{ADVISEUR}">Zoek een Erkend Hypothecair Planner</a></p>', '<div class="foot-bottom">')
    s = blok(s, 'CSS', '''
.adviesblok{margin-top:22px;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 24px;padding:16px 20px;background:var(--gold-tint);border:1px solid var(--line);border-radius:8px}
.adviesblok p{margin:0;flex:1 1 320px;min-width:0;color:var(--ink);max-width:70ch}
.adviesblok b{color:var(--navy);font-weight:700}
.adviesknop{display:inline-flex;align-items:center;min-height:44px;padding:10px 18px;border-radius:4px;background:var(--accent-text);color:#fff!important;font-weight:600;text-decoration:none;white-space:nowrap}
.adviesknop:hover{background:var(--navy)}
.adviesknop:focus-visible,.faq summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
@media(max-width:480px){.adviesknop{width:100%;justify-content:center;white-space:normal;text-align:center}}
.faq{max-width:900px}
.faq .faqitem{margin-bottom:10px}
.faq summary{cursor:pointer;list-style-position:inside}
.faq summary h3{display:inline;font-size:1.08rem;margin:0}
.faqtekst{padding:6px 4px 2px;max-width:75ch}
.faqtekst ul{margin:6px 0 0;padding-left:20px}.faqtekst li{margin-bottom:4px}
.faqtekst a,.voetadvies a{color:inherit;text-decoration:underline}
.voetadvies{margin:0 0 14px;font-size:.9rem;opacity:.9}
@media print{.adviesblok{border:1px solid #999}.adviesknop{display:none}}
/* iOS/WebKit: keuzelijsten worden zo breed als de langste optie; begrenzen en zijwaarts scrollen voorkomen */
html,body{max-width:100%;overflow-x:clip}
.aflrij>div{column-gap:12px}
select{max-width:100%}
.mxsort,.mxsort select{min-width:0!important;max-width:100%!important}
@media(max-width:760px){.mxsort select{width:100%!important;flex:1 1 0!important;text-overflow:ellipsis}}''', '</style>')

    # ---- JSON-LD ----
    org = {'@type': 'Organization', '@id': NVHP + '#organisatie', 'name': 'NVHP – Nederlandse Vereniging van Hypothecair Planners',
           'alternateName': 'NVHP', 'url': NVHP, 'logo': LOGO}
    graph = [
        org,
        {'@type': 'WebSite', '@id': SITE + '#website', 'url': SITE, 'name': 'Woningverzilveraar', 'inLanguage': 'nl-NL',
         'publisher': {'@id': org['@id']}},
        {'@type': 'WebPage', '@id': SITE + '#pagina', 'url': SITE, 'name': TITEL, 'description': beschrijving,
         'inLanguage': 'nl-NL', 'isPartOf': {'@id': SITE + '#website'}, 'publisher': {'@id': org['@id']},
         'dateModified': datum, 'breadcrumb': {'@id': SITE + '#kruimelpad'}, 'mainEntity': {'@id': SITE + '#aanbod'},
         'about': [{'@type': 'Thing', 'name': 'Verzilverhypotheek'}, {'@type': 'Thing', 'name': 'Overwaarde opnemen'},
                   {'@type': 'Thing', 'name': 'Seniorenhypotheek'}]},
        {'@type': 'BreadcrumbList', '@id': SITE + '#kruimelpad', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'NVHP', 'item': NVHP},
            {'@type': 'ListItem', 'position': 2, 'name': 'Thema Verzilveren', 'item': THEMA},
            {'@type': 'ListItem', 'position': 3, 'name': 'Vergelijkingstool', 'item': SITE}]},
        {'@type': 'ItemList', '@id': SITE + '#aanbod', 'name': f"Verzilverhypotheken in Nederland (peildatum {meta['peildatum']})",
         'numberOfItems': len(actief), 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'item': {k: v for k, v in {
                '@type': 'LoanOrCredit', 'name': p['product'], 'category': cat.get(p.get('cat'), {}).get('naam'),
                'provider': {'@type': 'Organization', 'name': p['aanbieder']}, 'url': p.get('website') or None,
                'areaServed': {'@type': 'Country', 'name': 'Nederland'},
                'description': f"Minimumleeftijd: {p.get('minLeeftijd')}. Maximum: {p.get('maxLtv')}. Maximaal bedrag: {p.get('maxBedrag')}. Rentevast: {p.get('rentevast')}. Geld vrij: {p.get('opname')}."
            }.items() if v}} for i, p in enumerate(actief)]},
        {'@type': 'FAQPage', '@id': SITE + '#faq', 'inLanguage': 'nl-NL', 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer',
             'text': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', a.replace('</li>', '; '))).strip()}} for q, a in faq]},
    ]
    ld = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, indent=1).replace('</', '<\\/')
    head = '\n'.join([
        '<link rel="icon" type="image/png" href="assets/nvhp-logo.png">',
        '<link rel="apple-touch-icon" href="assets/nvhp-logo.png">',
        '<link rel="sitemap" type="application/xml" href="/sitemap.xml">',
        '<meta property="og:locale" content="nl_NL">',
        '<meta property="og:site_name" content="Woningverzilveraar · NVHP">',
        f'<meta property="og:image" content="{LOGO}">',
        '<meta property="og:image:alt" content="NVHP - Nederlandse Vereniging van Hypothecair Planners">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{e(TITEL)}">',
        f'<meta name="twitter:description" content="{e(beschrijving)}">',
        f'<meta name="twitter:image" content="{LOGO}">',
        f'<script type="application/ld+json">\n{ld}\n</script>'])
    s = blok(s, 'HEAD', head, '</head>')
    PAGE.write_text(s, encoding='utf-8')

    # ---- sitemap, robots, llms.txt ----
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{SITE}</loc><lastmod>{datum}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>\n</urlset>\n',
        encoding='utf-8')
    (ROOT / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n\n'
        '# AI-zoekmachines en assistenten expliciet toegestaan\n'
        + ''.join(f'User-agent: {b}\nAllow: /\n\n' for b in
                  ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User',
                   'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended', 'Bingbot'])
        + f'Sitemap: {SITE}sitemap.xml\n', encoding='utf-8')
    llms = [f'# Woningverzilveraar – verzilverhypotheken vergelijken (NVHP)', '',
            f'> Overzicht van alle hypotheken in Nederland waarmee senioren overwaarde uit hun koopwoning kunnen opnemen zonder te verhuizen. '
            f'Onderdeel van het NVHP-thema Verzilveren. Peildatum {meta["peildatum"]}. Informatie, geen advies; de offerte en de voorwaarden van de aanbieder zijn leidend.', '',
            '## Pagina\'s', f'- [Vergelijkingstool]({SITE}): filters, vergelijking naast elkaar en veelgestelde vragen',
            f'- [NVHP-thema Verzilveren]({THEMA})', f'- [Zoek een Erkend Hypothecair Planner]({ADVISEUR})', '',
            '## Soorten']
    llms += [f"- **{c['naam']}**: {c['uitleg']}" for c in cat.values()]
    llms += ['', '## Aanbod']
    for p in P:
        st = '' if status(p) == 'Verkrijgbaar' else ' (' + status(p).lower() + ')'
        llms.append(f"- **{naam(p)}**{st}: minimumleeftijd {p.get('minLeeftijd')}; maximum {p.get('maxLtv')}; "
                    f"maximaal bedrag {p.get('maxBedrag')}; rentevast {p.get('rentevast')}; geld vrij: {p.get('opname')}; "
                    f"restschuld: {p.get('restschuld')}." + (f" {p['website']}" if p.get('website') else ''))
    (ROOT / 'llms.txt').write_text('\n'.join(llms) + '\n', encoding='utf-8')
    print(f'Klaar: {len(actief)} actief, {len(gestopt)} gestopt, peildatum {datum}.')


if __name__ == '__main__':
    main()

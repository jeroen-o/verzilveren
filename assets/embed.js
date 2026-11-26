/* Woningverzilveraar: insluitversie voor de website van een adviseur.
 *
 * Aan:  https://woningverzilveraar.nl/?embed=1   (ook automatisch in een iframe)
 * Uit:  ?embed=0
 *
 * Optionele parameters (alles wordt als tekst getoond, nooit als HTML):
 *   kantoor, adviseur   naam van kantoor en adviseur
 *   logo                logo-URL (alleen https)
 *   kleur               huisstijlkleur, bijv. %23e30613 (#e30613)
 *   web, email, tel     contactgegevens voor de knop "Neem contact op"
 *
 * De pagina meldt haar hoogte aan de bovenliggende pagina met
 *   postMessage({type: "woningverzilveraar:hoogte", hoogte: <px>}, "*")
 * zodat de iframe meegroeit.
 *
 * Dit bestand wordt geladen vanuit de footer van index.html. tools/nvhp_apply.py
 * neemt de footer ongewijzigd over, dus een nieuwe upload laat dit intact.
 */
(function () {
  var q = new URLSearchParams(location.search);
  var ingesloten = false;
  try { ingesloten = window.self !== window.top; } catch (e) { ingesloten = true; }
  var aan = q.get('embed') === '1' || (ingesloten && q.get('embed') !== '0');
  if (!aan) return;

  function tekst(k, max) { return (q.get(k) || '').trim().slice(0, max || 80); }
  var A = {
    kantoor: tekst('kantoor'),
    adviseur: tekst('adviseur'),
    logo: /^https:\/\/[^\s"'<>]+$/i.test(tekst('logo', 500)) ? tekst('logo', 500) : '',
    kleur: /^#?[0-9a-f]{6}$/i.test(tekst('kleur', 7)) ? '#' + tekst('kleur', 7).replace('#', '') : '',
    web: /^https?:\/\/[^\s"'<>]+$/i.test(tekst('web', 300)) ? tekst('web', 300) : '',
    email: /^[^\s@<>"]+@[^\s@<>"]+\.[a-z]{2,}$/i.test(tekst('email', 120)) ? tekst('email', 120) : '',
    tel: tekst('tel', 30).replace(/[^\d+ ()-]/g, '')
  };
  var naam = A.kantoor || A.adviseur;
  var contact = A.web || (A.email ? 'mailto:' + A.email : '') || (A.tel ? 'tel:' + A.tel.replace(/[^\d+]/g, '') : '');

  var root = document.documentElement;
  root.classList.add('wv-embed');

  /* Kleur: als accent; alleen als knopkleur als witte tekst erop goed leesbaar is (contrast >= 4,5). */
  var css = '';
  if (A.kleur) {
    var r = parseInt(A.kleur.substr(1, 2), 16) / 255, g = parseInt(A.kleur.substr(3, 2), 16) / 255, b = parseInt(A.kleur.substr(5, 2), 16) / 255;
    var lin = function (c) { return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    var L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
    css += 'html.wv-embed,html.wv-embed body{--accent:' + A.kleur + '!important;--geel:' + A.kleur + '!important}';
    if (1.05 / (L + 0.05) >= 4.5) css += 'html.wv-embed,html.wv-embed body{--accent-text:' + A.kleur + '!important}';
  }
  css += [
    '.wv-embed body{background:#fff}',
    '.wv-embed #sitenav,.wv-embed .balk,.wv-embed #bbewerk,.wv-embed #bdownload,.wv-embed #bewerkmelding,.wv-embed .alleenbewerk{display:none!important}',
    '.wv-embed header .label{display:none}',
    '.wv-embed header{padding-top:20px!important;padding-bottom:20px!important}',
    '.wv-embed header h1{font-size:clamp(1.6rem,4vw,2.3rem)!important}',
    '.wv-embed footer{background:none!important;color:var(--grijs,#5B6675)!important;padding:0 0 18px!important;border:0!important}',
    '.wv-embed footer .foot-grid,.wv-embed footer .socials{display:none!important}',
    '.wv-embed footer .wrap{padding-top:0!important}',
    '.wv-embed footer .voetadvies,.wv-embed footer .foot-bottom{color:inherit!important;opacity:1!important;font-size:.85rem}',
    '.wv-embed footer a{color:inherit!important}',
    '.wv-aanbieder{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 16px;border-bottom:1px solid var(--lijn,#DDE1E7);background:#fff;font-size:.9rem;color:var(--grijs,#5B6675)}',
    '.wv-aanbieder img{max-height:40px;max-width:180px;width:auto;height:auto;display:block}',
    '.wv-aanbieder b{color:var(--navy,#1D2632)}',
    '.wv-bron{font-size:.85rem;margin:6px 0 0}'
  ].join('\n');
  var st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  /* Afdrukken in een iframe: open de pagina in een nieuw venster (window.print werkt niet overal in een iframe). */
  if (ingesloten) {
    window.print = function () {
      var u = new URL(location.href); u.searchParams.set('embed', '0'); u.hash = 'print';
      window.open(u.toString(), '_blank', 'noopener');
    };
  }

  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt) e.textContent = txt; return e; }

  function contactLink(tekstKnop, cls) {
    var a = el('a', cls, tekstKnop);
    a.href = contact; a.target = '_blank'; a.rel = 'noopener';
    return a;
  }

  /* Links naar "zoek een adviseur bij de NVHP" wijzen in de insluitversie naar de adviseur zelf. */
  function vervangAdviseurLinks(scope) {
    var links = (scope || document).querySelectorAll('a[href*="zoek-een-hypotheekadviseur"]');
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      if (a.dataset.wv) continue;
      a.dataset.wv = '1';
      if (contact) {
        a.href = contact; a.target = '_blank'; a.rel = 'noopener';
        a.textContent = naam ? 'Neem contact op met ' + naam : 'Neem contact op met je adviseur';
      } else {
        a.remove();
      }
    }
  }

  /* Externe links openen in een nieuw tabblad, zodat de bezoeker op de site van de adviseur blijft. */
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var h = a.getAttribute('href') || '';
    if (/^https?:\/\//i.test(h) && a.host !== location.host) { a.target = '_blank'; a.rel = 'noopener'; }
  }, true);

  function bouw() {
    /* Balk bovenaan: aangeboden door */
    if (naam || A.logo) {
      var bar = el('div', 'wv-aanbieder');
      if (A.logo) { var img = el('img'); img.src = A.logo; img.alt = naam || 'Logo'; img.onerror = function () { img.remove(); }; bar.appendChild(img); }
      if (naam) {
        var s = el('span'); s.appendChild(document.createTextNode('Aangeboden door ')); s.appendChild(el('b', '', naam));
        if (A.adviseur && A.kantoor) s.appendChild(document.createTextNode(' · ' + A.adviseur));
        bar.appendChild(s);
      }
      var hd = document.querySelector('header');
      if (hd) hd.parentNode.insertBefore(bar, hd);
    }
    /* Bron blijft altijd zichtbaar */
    var vb = document.querySelector('footer .foot-bottom');
    if (vb && !vb.querySelector('.wv-bron')) {
      var p = el('p', 'wv-bron');
      p.appendChild(document.createTextNode('Bron: '));
      var l = el('a', '', 'Woningverzilveraar.nl'); l.href = 'https://woningverzilveraar.nl/'; l.target = '_blank'; l.rel = 'noopener';
      p.appendChild(l);
      p.appendChild(document.createTextNode(' van de NVHP. Het aanbod wordt centraal bijgehouden.'));
      vb.appendChild(p);
    }
    vervangAdviseurLinks();
    /* Contactknop in het adviesblok als die er nog niet is */
    var blok = document.querySelector('.adviesblok');
    if (blok && contact && !blok.querySelector('.adviesknop')) blok.appendChild(contactLink(naam ? 'Neem contact op met ' + naam : 'Neem contact op', 'adviesknop'));

    new MutationObserver(function (m) { for (var i = 0; i < m.length; i++) if (m[i].addedNodes.length) { vervangAdviseurLinks(); break; } })
      .observe(document.body, { childList: true, subtree: true });

    /* Hoogte doorgeven aan de bovenliggende pagina */
    if (ingesloten && window.parent) {
      var laatst = 0;
      var meld = function () {
        var f = document.querySelector('footer') || document.body;
        var h = Math.ceil(f.getBoundingClientRect().bottom + window.pageYOffset) + 8;
        if (Math.abs(h - laatst) > 2) { laatst = h; window.parent.postMessage({ type: 'woningverzilveraar:hoogte', hoogte: h }, '*'); }
      };
      if (window.ResizeObserver) new ResizeObserver(meld).observe(document.body);
      window.addEventListener('load', meld);
      setInterval(meld, 1500);
      meld();
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bouw); else bouw();
})();

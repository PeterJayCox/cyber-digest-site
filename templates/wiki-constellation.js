/* ============================================================
   Cyber Wiki — Constellation. Generated from draft-c by
   mockups/wiki-variants-2026-09/migrate_to_templates.py
   ============================================================ */
/* ============================================================
   Constellation — reads the built wiki under docs/wiki/.
   Routing is hash-based so back/forward and deep links work.

   SECURITY NOTE (re the innerHTML warnings below): every dynamic value is
   passed through esc() before it reaches innerHTML, and all of it originates
   in this machine's own built wiki pages (data/wiki.js, emitted by
   extract_full.py from the site build) — not from user input or third-party
   fetches. Page body HTML is rendered as-is by design: it is the site's own
   generated markup. Do not feed this bundle from an untrusted source.
   ============================================================ */
const D = window.WIKI_FULL;
const KIND = {incident:'Incident', cve:'Vulnerability', entity:'Entity', concept:'Concept'};
const KINDPL = {incident:'Incidents & campaigns', cve:'Vulnerabilities & CVEs', entity:'Entities & threat actors', concept:'Concepts & frameworks'};
const COL = {incident:'#f97316', cve:'#a78bfa', entity:'#22d3ee', concept:'#34d399'};
const PAGE = 25;

const bySlug = new Map(D.items.map(p => [p.slug, p]));
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dmy = d => d ? d.slice(8,10)+'/'+d.slice(5,7)+'/'+d.slice(0,4) : '—';
const short = d => d ? d.slice(8,10)+'/'+d.slice(5,7) : '—';
const el = id => document.getElementById(id);
let listState = {items:[], shown:PAGE, sort:'rel', title:'', kick:'', sub:''};

/* ---------------- query language ----------------
   free text (AND, all tokens must hit) plus type:, tag:, sector:, au: filters */
function parseQuery(raw){
  const f = {terms:[], type:[], tag:[], sector:[], au:false, raw:raw.trim()};
  raw.trim().toLowerCase().split(/\s+/).filter(Boolean).forEach(tok => {
    let m;
    if ((m = tok.match(/^type:(incident|cve|entity|concept)s?$/))) f.type.push(m[1].replace(/s$/,''));
    else if ((m = tok.match(/^tag:(.+)$/))) f.tag.push(m[1]);
    else if ((m = tok.match(/^sector:(.+)$/))) f.sector.push(m[1]);
    else if (tok === 'au' || tok === 'au:true') f.au = true;
    else f.terms.push(tok);
  });
  return f;
}
function score(p, q){
  if (q.type.length && !q.type.includes(p.k)) return -1;
  if (q.au && !p.au) return -1;
  if (q.tag.length && !q.tag.every(t => p.tags.some(x => x.startsWith(t)))) return -1;
  if (q.sector.length && !q.sector.every(s => p.sectors.some(x => x.startsWith(s)))) return -1;
  const title = p.title.toLowerCase(), sum = p.summary.toLowerCase();
  const tags = p.tags.join(' ').toLowerCase(), secs = p.sectors.join(' ').toLowerCase();
  let s = 0;
  for (const t of q.terms){
    let hit = 0;
    if (title.startsWith(t)) hit += 9; else if (title.includes(t)) hit += 6;
    if (tags.includes(t)) hit += 4;
    if (secs.includes(t)) hit += 3;
    if (sum.includes(t)) hit += 2;
    if (!hit) return -1;
    s += hit;
  }
  // CIDR-free relevance tiebreak: cited pages and richer pages rank up
  return s + Math.min(p.in.length, 6) * 0.5 + (q.terms.length ? 0 : 0);
}
function search(raw){
  const q = parseQuery(raw);
  const empty = !q.terms.length && !q.type.length && !q.tag.length && !q.sector.length && !q.au;
  if (empty) return {q, hits:[]};
  const hits = [];
  for (const p of D.items){ const s = score(p, q); if (s >= 0) hits.push({p, s}); }
  hits.sort((a, b) => b.s - a.s || b.p.created.localeCompare(a.p.created));
  return {q, hits};
}
function sortList(list, how){
  const L = list.slice();
  if (how === 'date')  L.sort((a,b) => (b.created||'').localeCompare(a.created||''));
  if (how === 'title') L.sort((a,b) => a.title.localeCompare(b.title));
  if (how === 'cited') L.sort((a,b) => b.in.length - a.in.length || b.out.length - a.out.length);
  return L;
}

/* ---------------- routing ---------------- */
function go(hash){ location.hash = hash; }
function route(){
  const h = decodeURIComponent(location.hash || '#/');
  const m = h.match(/^#\/p\/(.+)$/);
  const c = h.match(/^#\/c\/(\w+)$/);
  const t = h.match(/^#\/t\/(.+)$/);
  const q = h.match(/^#\/q\/(.*)$/);
  closeResults();
  if (m)            { showPage(m[1]); return; }
  if (c)            { showList({kind:c[1]}); return; }
  if (t)            { showList({tag:t[1]}); return; }
  if (q)            { showList({raw:q[1]}); return; }
  showHome();
}
function view(name){
  for (const v of ['home','list','page']) el('view-'+v).hidden = (v !== name);
  window.scrollTo({top:0, behavior:'instant'});
}

/* ---------------- home ---------------- */
function showHome(){
  view('home');
  el('sort').value = listState.sort;
}

/* ---------------- list ---------------- */
function showList({kind, tag, raw, sector}){
  let items, title, kick, sub;
  if (kind){
    items = D.items.filter(p => p.k === kind);
    title = KINDPL[kind] || kind; kick = '// family'; sub = `${D.counts[kind]} pages filed under this family.`;
  } else if (tag){
    items = D.items.filter(p => p.tags.some(x => x === tag));
    title = `Tagged “${tag}”`; kick = '// subject'; sub = `${items.length} pages carry this tag.`;
  } else if (sector){
    items = D.items.filter(p => p.sectors.some(x => x === sector));
    title = `Sector: ${sector}`; kick = '// sector'; sub = `${items.length} pages record this sector as affected.`;
  } else {
    const r = search(raw || '');
    items = r.hits.map(x => x.p); title = raw ? `“${raw}”` : 'All pages';
    kick = '// search';
    sub = r.hits.length ? `${r.hits.length} of ${D.total} pages match ${describeQuery(r.q)}.`
                        : 'No page matches that. Try a tag like kev, a family like type:cve, or sector:health.';
  }
  if (raw !== undefined) syncQuery(raw || '');
  const sorted = sortList(items, listState.sort);
  listState = {items:sorted, shown:PAGE, sort:listState.sort, title, kick, sub};
  el('listKick').textContent = kick;
  el('listTitle').textContent = title;
  el('listSub').textContent = sub;
  drawList();
  view('list');
}
function describeQuery(q){
  const bits = [];
  if (q.terms.length) bits.push(q.terms.join(' + '));
  if (q.type.length) bits.push('type: ' + q.type.join(', '));
  if (q.tag.length) bits.push('tag: ' + q.tag.join(', '));
  if (q.sector.length) bits.push('sector: ' + q.sector.join(', '));
  if (q.au) bits.push('Australian impact');
  return bits.join(' · ') || 'anything';
}
function drawList(){
  const s = listState, slice = s.items.slice(0, s.shown);
  el('listCount').textContent = `${Math.min(s.shown, s.items.length)} of ${s.items.length} shown`;
  el('listFacets').textContent = `${D.total} pages in the file · ${D.edge_count} internal links`;
  el('listRows').innerHTML = slice.map(p => `
    <div class="row" data-slug="${esc(p.slug)}">
      <div>
        <h3>${esc(p.title)}</h3>
        <p>${esc(p.summary.slice(0, 210))}${p.summary.length > 210 ? '…' : ''}</p>
        <div class="tg">
          <span class="k k-${p.k}">${KIND[p.k]}</span>
          ${p.tags.slice(0,4).map(t => `<span class="chip" data-tag="${esc(t)}">${esc(t)}</span>`).join('')}
          ${p.au ? '<span class="chip" style="color:#a5f3fc;border-color:rgba(0,180,216,.4)">AU</span>' : ''}
        </div>
      </div>
      <div class="rt">
        ${p.severity ? `<span class="sev p-${esc(p.severity)}">${esc(p.severity)}</span><br>` : ''}
        ${dmy(p.created)}<br>
        ${p.in.length} in · ${p.out.length} out
      </div>
    </div>`).join('') || `<div class="empty">Nothing here.</div>`;
  const more = el('more');
  more.hidden = s.shown >= s.items.length;
  more.textContent = `Show ${Math.min(PAGE, s.items.length - s.shown)} more of ${s.items.length}`;
}

/* ---------------- article ---------------- */
function linkList(slugs, limit){
  if (!slugs.length) return '<div class="gnode" style="color:var(--dim)">None recorded.</div>';
  return slugs.slice(0, limit).map(s => {
    const p = bySlug.get(s);
    if (!p) return '';
    return `<div class="gnode"><span class="dotnode" style="background:${COL[p.k]}"></span>
      <span><a href="#/p/${esc(p.slug)}" data-slug="${esc(p.slug)}">${esc(p.title.length > 54 ? p.title.slice(0,54)+'…' : p.title)}</a>
      <small>${KIND[p.k]} · ${short(p.created)}</small></span></div>`;
  }).join('') || '<div class="gnode" style="color:var(--dim)">None recorded.</div>';
}
function showPage(slug){
  const p = bySlug.get(slug);
  if (!p){ el('view-page').innerHTML = `<div class="vhead"><h1>Page not found</h1><p>No wiki page with slug <code>${esc(slug)}</code>.</p></div>`; view('page'); return; }
  const idx = D.items.findIndex(x => x.slug === slug);
  const newer = D.items[idx-1], older = D.items[idx+1];
  const sib = D.items.filter(x => x.k === p.k && x.tags.some(t => p.tags.includes(t))).slice(0, 5);
  el('view-page').innerHTML = `
    <div class="crumb"><button id="back">← Back</button> · <a href="#/c/${p.k}">${KINDPL[p.k]}</a> · filed ${dmy(p.created)}</div>
    <div class="agrid">
      <article class="article">
        <h1>${esc(p.title)}</h1>
        <div class="meta">
          <span class="d">${dmy(p.created)}${p.updated !== p.created ? ' → revised ' + dmy(p.updated) : ''}</span>
          ${p.tags.slice(0,6).map(t => `<a class="chip" href="#/t/${encodeURIComponent(t)}">#${esc(t)}</a>`).join('')}
          ${p.au ? '<span class="chip" style="color:#a5f3fc;border-color:rgba(0,180,216,.4)">Australian impact</span>' : ''}
          ${p.severity ? `<span class="chip p-${esc(p.severity)}">${esc(p.severity)}</span>` : ''}
        </div>
        <div class="body" id="body"><p style="color:var(--dim)">Loading the full entry…</p></div>
        <div id="srcblock"></div>
        <div class="nextprev">
          ${older ? `<a href="#/p/${esc(older.slug)}" data-slug="${esc(older.slug)}"><small>Earlier</small>${esc(older.title.slice(0,70))}…</a>` : '<span></span>'}
          ${newer ? `<a href="#/p/${esc(newer.slug)}" data-slug="${esc(newer.slug)}" style="text-align:right"><small>Later</small>${esc(newer.title.slice(0,70))}…</a>` : '<span></span>'}
        </div>
      </article>
      <aside class="rail">
        <div class="card"><h4>Attributes</h4><div class="attrs">
          <div class="attr"><span>Family</span><span>${KIND[p.k]}</span></div>
          <div class="attr"><span>Created</span><span>${p.created || '—'}</span></div>
          <div class="attr"><span>Updated</span><span>${p.updated || '—'}</span></div>
          <div class="attr"><span>Confidence</span><span>${esc(p.confidence || '—')}</span></div>
          <div class="attr"><span>Severity</span><span>${esc(p.severity || '—')}</span></div>
          <div class="attr"><span>AU impact</span><span>${p.au ? 'yes' : 'no'}</span></div>
          <div class="attr"><span>Sectors</span><span>${esc(p.sectors.join(', ') || '—')}</span></div>
          <div class="attr"><span>Words</span><span>${p.words}</span></div>
        </div></div>
        <div class="card"><h4>Links to <span>${p.out.length}</span></h4>${linkList(p.out, 8)}</div>
        <div class="card"><h4>Cited by <span>${p.in.length}</span></h4>${linkList(p.in, 10)}</div>
        ${sib.length ? `<div class="card"><h4>Shares a subject</h4>${linkList(sib.map(x => x.slug), 5)}</div>` : ''}
      </aside>
    </div>`;
  rewriteLinks(el('body'));
  loadBody(p);
  document.title = p.title + ' · Cyber Wiki';
  view('page');
}

/* config: where the static wiki pages live, relative to the entry page.
   The entry page is /wiki/index.html, so the pages are its siblings. */
const WIKI_BASE = '';  // the index is /wiki/index.html; pages are siblings

/* the article body is fetched, not bundled: pull the static page and lift its
   wiki-body div out. Falls back to a link when fetch is unavailable (file://). */
async function loadBody(p){
  const box = el('body'), src = el('srcblock');
  let html = null;
  try {
    const res = await fetch(WIKI_BASE + p.url, { cache: 'force-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const doc = new DOMParser().parseFromString(await res.text(), 'text/html');
    const wb = doc.querySelector('.wiki-body');
    if (!wb) throw new Error('no wiki-body in page');
    wb.querySelectorAll('script,style').forEach(n => n.remove());
    const fm = wb.querySelector('.frontmatter'); if (fm) fm.remove();
    html = wb.innerHTML;
  } catch (err){
    box.innerHTML = `<div class="empty" style="text-align:left;padding:22px 0">`
      + `<p>Couldn't load the full entry on this page.</p>`
      + `<p>Open it at <a href="${esc(WIKI_BASE + p.url)}">${esc(p.url)}</a>.</p>`
      + `<p style="color:var(--dim);font-size:13px">(${esc(err.message)})</p></div>`;
    return;
  }
  box.innerHTML = html;
  rewriteLinks(box);
  const ext = [...box.querySelectorAll('a[href^="http"]')]
    .map(a => ({ url: a.getAttribute('href'), label: a.textContent.trim() }))
    .filter((s, i, arr) => arr.findIndex(x => x.url === s.url) === i);
  if (ext.length){
    src.innerHTML = `<h2 style="font:650 19px/1.35 Inter;margin:28px 0 12px;padding-top:18px;border-top:1px solid var(--border)">Sources</h2>`
      + `<ul class="srclist">${ext.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label || s.url)}</a></li>`).join('')}</ul>`;
  }
}

/* rewrite wiki-internal hrefs to in-app hash routes so the graph is traversable */
function rewriteLinks(root){
  root.querySelectorAll('a[href]').forEach(a => {
    const href = a.getAttribute('href');
    if (!href) return;
    if (/^https?:/.test(href)){
      if (href.includes('cyber.peterjaycox.com/wiki/')){
        const target = href.split('/').pop().replace(/\.html$/, '');
        if (bySlug.has(target)){ a.setAttribute('href', '#/p/' + target); a.dataset.slug = target; }
      }
      return;
    }
    if (href.startsWith('#')) return;
    if (/\.html$/.test(href)){
      const target = href.split('/').pop().replace(/\.html$/, '');
      if (bySlug.has(target)){
        a.setAttribute('href', '#/p/' + target);
        a.dataset.slug = target;
        return;
      }
    }
    a.setAttribute('href', WIKI_BASE + href.replace(/^(\.\.\/)+/, ''));
  });
}

/* ---------------- search box (two instances: hero + sticky bar) ---------------- */
function resultsHTML(raw, focusIdx){
  const {q, hits} = search(raw);
  if (!raw.trim()) {
    return `<div class="rhead"><span>Try a query</span><span>${D.total} pages loaded</span></div>
      <div class="sugg">${['type:cve','type:entity','tag:kev','tag:ransomware','sector:health','au','zero-day','ClickFix'].map(s => `<span data-query="${esc(s)}">${esc(s)}</span>`).join('')}</div>
      <div class="rhead"><span>Recently filed</span><span>newest first</span></div>` +
      D.items.slice(0, 5).map((p, i) => rowHTML(p, i === focusIdx)).join('');
  }
  return `<div class="rhead"><span>${hits.length ? hits.length + ' match' + (hits.length===1?'':'es') : 'No match'}</span><span>${esc(describeQuery(q))}</span></div>` +
    (hits.slice(0, 8).map((x, i) => rowHTML(x.p, i === focusIdx)).join('')
     || `<div class="sugg">${['type:cve','tag:kev','sector:health','au'].map(s => `<span data-query="${esc(s)}">${esc(s)}</span>`).join('')}</div>`);
}
function rowHTML(p, sel){
  return `<div class="r ${sel ? 'sel' : ''}" data-slug="${esc(p.slug)}">
      <span class="k k-${p.k}">${KIND[p.k]}</span>
      <span class="t">${esc(p.title)}<small>${esc(p.summary.slice(0, 118))}…</small></span>
      <span class="d">${short(p.created)}${p.in.length ? ' · ' + p.in.length + ' in' : ''}</span>
    </div>`;
}
let focusIdx = -1, currentHits = [];
function bindSearch(input, box){
  const open = () => { box.classList.add('on'); render(); };
  function render(){
    box.innerHTML = resultsHTML(input.value, focusIdx);
    currentHits = search(input.value).hits.slice(0, 8).map(x => x.p);
    if (!input.value.trim()) currentHits = D.items.slice(0, 5);
  }
  input.addEventListener('input', () => { focusIdx = -1; open(); });
  input.addEventListener('focus', open);
  input.addEventListener('keydown', e => {
    const n = currentHits.length;
    if (e.key === 'ArrowDown'){ e.preventDefault(); focusIdx = Math.min(n-1, focusIdx+1); render(); }
    else if (e.key === 'ArrowUp'){ e.preventDefault(); focusIdx = Math.max(-1, focusIdx-1); render(); }
    else if (e.key === 'Enter'){
      e.preventDefault();
      if (focusIdx >= 0 && currentHits[focusIdx]) go('#/p/' + currentHits[focusIdx].slug);
      else if (input.value.trim()) go('#/q/' + encodeURIComponent(input.value.trim()));
      else go('#/');
      input.blur(); closeResults();
    } else if (e.key === 'Escape'){ input.blur(); closeResults(); }
  });
  box.addEventListener('click', e => {
    const s = e.target.closest('.r[data-slug]');
    const q = e.target.closest('[data-query]');
    if (s){ go('#/p/' + s.dataset.slug); closeResults(); }
    if (q){ input.value = q.dataset.query; input.focus(); focusIdx = -1; open(); }
  });
  return {render};
}
let searchBinders = [];
function closeResults(){ document.querySelectorAll('.results').forEach(b => b.classList.remove('on')); }
function syncInputs(val){
  document.querySelectorAll('.search-input').forEach(i => { if (i.value !== val) i.value = val; });
}

/* ============================================================
   Constellation — home / landing surface.
   Everything here is computed from WIKI_FULL, which is derived
   from the BUILT wiki pages, so the graph is the real wikilink
   set and not a tag-based approximation.
   ============================================================ */

/* ---------------- family map ---------------- */
const FAM = ['incident', 'cve', 'entity', 'concept'];
const FAMPOS = {incident:[400,120], cve:[648,300], entity:[400,382], concept:[152,300]};

function famEdges(a, b){ return D.fam_edges[a + '>' + b] || 0; }

function drawGraph(){
  const svg = el('graph');
  const maxE = Math.max(...FAM.flatMap(a => FAM.map(b => a === b ? 0 : famEdges(a, b))), 1);
  let s = '';

  // edges first, so nodes draw over them
  for (const a of FAM){
    for (const b of FAM){
      if (a > b) continue;                       // draw each pair once
      const n = famEdges(a, b);
      const rev = a === b ? 0 : famEdges(b, a);
      const total = n + rev;
      if (!total) continue;
      const [x1, y1] = FAMPOS[a], [x2, y2] = FAMPOS[b];
      const w = (1 + 3.2 * (total / maxE)).toFixed(2);
      const op = (0.18 + 0.5 * (total / maxE)).toFixed(2);
      if (a === b){
        // self-reference: a compact loop lifted just above the node
        const ratio = total / maxE;
        const rx = (24 + 14 * ratio).toFixed(1), ry = (18 + 10 * ratio).toFixed(1);
        const [nx, ny] = FAMPOS[a];
        const nr = 22 + Math.sqrt(D.counts[a] || 0) * 1.15;
        s += `<path d="M${nx - 20},${(ny - nr + 6).toFixed(1)} A${rx},${ry} 0 1 1 ${nx + 20},${(ny - nr + 6).toFixed(1)}"`
           + ` fill="none" stroke="${COL[a]}" stroke-width="${w}" opacity="${op}"
             stroke-dasharray="3 4"/>`;
      } else {
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        const dx = x2 - x1, dy = y2 - y1;
        const len = Math.hypot(dx, dy) || 1;
        const ox = -dy / len * 34, oy = dx / len * 34;    // bow the curve outward
        s += `<path d="M${x1},${y1} Q${mx + ox},${my + oy} ${x2},${y2}" fill="none"`
           + ` stroke="${COL[a]}" stroke-width="${w}" opacity="${op}"/>`;
      }
    }
  }

  // hubs per family: the satellites around each node
  const hubsByFam = {};
  for (const h of D.hubs) (hubsByFam[h.k] ||= []).push(h);

  for (const fam of FAM){
    const [x, y] = FAMPOS[fam];
    const n = D.counts[fam] || 0;
    const r = 22 + Math.sqrt(n) * 1.15;
    s += `<g class="famnode" data-kind="${fam}" style="cursor:pointer">`
       + `<circle cx="${x}" cy="${y}" r="${r.toFixed(1)}" fill="${COL[fam]}" opacity=".13"`
       + ` stroke="${COL[fam]}" stroke-width="1.4"/>`
       + `<text x="${x}" y="${y - 2}" text-anchor="middle" fill="#e2e8f0"`
       + ` style="font:600 15px Inter,sans-serif">${n}</text>`
       + `<text x="${x}" y="${y + 14}" text-anchor="middle" fill="#8a9cb6"`
       + ` style="font:500 9.5px 'JetBrains Mono',monospace;letter-spacing:.1em"`
       + `>${KIND[fam].toUpperCase()}</text></g>`;

    // satellites, ringed left-to-right
    const sat = (hubsByFam[fam] || []).slice(0, 4);
    sat.forEach((h, i) => {
      const ang = (-0.85 + i * 0.57) + (fam === 'concept' ? Math.PI : fam === 'cve' ? 0.35 : 0);
      const sx = x + Math.cos(ang) * (r + 52), sy = y + Math.sin(ang) * (r + 44);
      s += `<line x1="${x}" y1="${y}" x2="${sx}" y2="${sy}" stroke="${COL[fam]}"`
         + ` stroke-width="1" opacity=".35"/>`
         + `<g class="sat" data-slug="${h.slug}" style="cursor:pointer">`
         + `<circle cx="${sx}" cy="${sy}" r="${(4 + Math.min(h.in, 12) * 0.55).toFixed(1)}"`
         + ` fill="${COL[fam]}" opacity=".85"/>`
         + `<title>${h.title} — cited by ${h.in}</title></g>`;
      if (h.in >= 10){
        const anchor = sx < x - 10 ? 'end' : sx > x + 10 ? 'start' : 'middle';
        const lx = sx + (anchor === 'end' ? -9 : anchor === 'start' ? 9 : 0);
        s += `<text x="${lx}" y="${sy + 3}" text-anchor="${anchor}" fill="#8a9cb6"`
           + ` style="font:500 9px 'JetBrains Mono',monospace">`
           + `${esc(h.title.length > 22 ? h.title.slice(0, 22) + '…' : h.title)}`
           + `<tspan fill="#64748b"> ${h.in}</tspan></text>`;
      }
    });
  }
  svg.innerHTML = s;
  svg.querySelectorAll('.famnode').forEach(g => g.addEventListener('click', () => go('#/c/' + g.dataset.kind)));
  svg.querySelectorAll('.sat').forEach(g => g.addEventListener('click', e => { e.stopPropagation(); go('#/p/' + g.dataset.slug); }));

  el('mapTag').textContent = `${D.total} pages · ${D.edge_count} internal links`;
  el('mapnote').innerHTML = `<b>Reading this map:</b> circle area is real page count`;
  el('mapnote').innerHTML += ` (${FAM.map(f => D.counts[f] + ' ' + KIND[f].toLowerCase()).join(' · ')}). `
    + `Edge thickness is the number of cross-links between families, counted from the built`
    + ` pages. Dotted loops are a family linking to itself. Satellites are the most-cited pages;`
    + ` the number beside one is how many entries cite it.`;
}

/* ---------------- side panels ---------------- */
function renderFams(){
  el('famTitle').textContent = 'Families';
  el('famCount').textContent = D.total;
  el('famList').innerHTML = FAM.map(f => `
    <div class="hit" data-kind="${f}" style="cursor:pointer">
      <span class="dotnode" style="width:8px;height:8px;border-radius:50%;background:${COL[f]}"></span>
      <a href="#/c/${f}">${KINDPL[f]}</a>
      <span class="m">${D.counts[f]}</span>
    </div>`).join('');
  el('famList').querySelectorAll('[data-kind]').forEach(r =>
    r.addEventListener('click', () => go('#/c/' + r.dataset.kind)));
}

function renderTags(){
  const top = D.tags.slice(0, 20);
  el('tagCount').textContent = `${D.tags.length} subjects`;
  el('tagcloud').innerHTML = top.map(([t, n]) =>
    `<span class="chip" data-tag="${esc(t)}">${esc(t)} <em style="font-style:normal;color:#64748b">${n}</em></span>`).join('');
  el('tagcloud').querySelectorAll('.chip').forEach(c =>
    c.addEventListener('click', () => go('#/t/' + encodeURIComponent(c.dataset.tag))));
}

function renderHubs(){
  const rows = D.hubs.slice(0, 8).map(h => {
    const p = bySlug.get(h.slug);
    return `<div class="hit" data-slug="${esc(h.slug)}" style="cursor:pointer">
        <span class="k k-${h.k}">${KIND[h.k]}</span>
        <a href="#/p/${esc(h.slug)}">${esc(h.title)}</a>
        <span class="lk">${h.in} in</span>
        <span class="m">${h.out} out</span>
      </div>`;
  }).join('');
  el('hubs').innerHTML = `<h4>Most cited<span>${D.edge_count} links</span></h4>` + rows;
  el('hubs').querySelectorAll('[data-slug]').forEach(r =>
    r.addEventListener('click', () => go('#/p/' + r.dataset.slug)));
}

function renderThreads(){
  const max = Math.max(...D.threads.map(t => t.in + t.out), 1);
  el('threads').innerHTML = D.threads.slice(0, 6).map(t => {
    const n = t.in + t.out, pct = Math.round(100 * n / max);
    return `<div class="th" data-slug="${esc(t.slug)}">
      <h5>${esc(t.title)}</h5>
      <div class="mix"><em>${KIND[t.k]}</em><em>${t.in} cited by</em><em>${t.out} links out</em></div>
      <div class="line"><span style="width:${pct}%"></span></div>
      <div class="why">Filed ${esc(t.span)} · ${n} recorded connections in the corpus</div>
    </div>`;
  }).join('') || '<div class="gnode" style="color:var(--dim)">No entity or concept carries links yet.</div>';
  el('threads').querySelectorAll('.th').forEach(t =>
    t.addEventListener('click', () => go('#/p/' + t.dataset.slug)));
}

function renderOrphans(){
  el('orphanTag').textContent = `${D.orphan_count} of ${D.total} pages`;
  const list = D.orphans.slice(0, 12).map(o => `
    <div class="hit" data-slug="${esc(o.slug)}" style="cursor:pointer">
      <span class="k k-${o.k}">${KIND[o.k]}</span>
      <a href="#/p/${esc(o.slug)}">${esc(o.title)}</a>
      <span class="m">${dmy(o.created)}</span>
    </div>`).join('');
  el('orphans').innerHTML = list + (D.orphan_count > D.orphans.length
    ? `<div class="hit"><span class="m" style="margin-left:0">…and ${D.orphan_count - D.orphans.length} more with no links in or out</span></div>` : '');
  el('orphans').querySelectorAll('[data-slug]').forEach(r =>
    r.addEventListener('click', () => go('#/p/' + r.dataset.slug)));
}

/* ---------------- hero ---------------- */
function renderHero(){
  const sev = D.severity || {};
  el('heroKick').textContent = '// the file';
  el('heroLede').textContent =
    `${D.total} pages across four families — ${D.counts.incident} incidents and campaigns, `
    + `${D.counts.cve} vulnerabilities, ${D.counts.entity} entities and threat actors, `
    + `${D.counts.concept} concepts. Every page is also a static entry at /wiki/.`;
  el('heroNote').innerHTML =
    `Built from the same vault that produces the daily digest · latest filing ${dmy(D.updated_max)} · `
    + `<b>${D.edge_count}</b> internal links · <b>${D.orphan_count}</b> pages with none · `
    + `${D.au} recording Australian impact`;
  const stats = [
    ['Pages', D.total], ['Incidents', D.counts.incident], ['Vulnerabilities', D.counts.cve],
    ['Entities', D.counts.entity], ['Concepts', D.counts.concept], ['AU impact', D.au],
    ['Critical', sev.critical || 0], ['Orphans', D.orphan_count]
  ];
  el('statsrow').innerHTML = stats.map(([l, n], i) =>
    `<div class="stat${i === 7 && n > 300 ? ' warn' : ''}"><b>${n}</b>${l}</div>`).join('');
  el('method').textContent =
    `This page reads the built site, not the vault: titles, dates, severity, tags, sectors, each `
    + `page's body and its outbound links are extracted from the generated HTML, so the link graph is `
    + `the real wikilink set rather than a guess. Pages that link to nothing and are linked by nothing `
    + `are counted as orphans rather than hidden. The corpus loads the whole file; a production build `
    + `should ship metadata for search and the graph and fetch each body on demand.`;
}

function renderHome(){
  renderHero(); renderFams(); renderTags(); renderHubs(); renderThreads(); renderOrphans(); drawGraph();
}

/* ============================================================
   Constellation — boot: search wiring, shortcuts, routing.
   ============================================================ */

/* the hero search box. bindSearch() owns rendering the dropdown. */
const heroInput = el('q'), heroBox = el('results');
const hero = bindSearch(heroInput, heroBox);

/* clicking outside the results closes them without clearing the query */
document.addEventListener('click', e => {
  if (!e.target.closest('.cmd')) closeResults();
});

/* "/" focuses the search from anywhere; Escape clears it */
document.addEventListener('keydown', e => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
  if (e.key === '/' && !typing){ e.preventDefault(); heroInput.focus(); heroInput.select(); }
  if (e.key === 'Escape' && document.activeElement === heroInput){
    heroInput.value = ''; hero.render(); closeResults(); heroInput.blur();
  }
});

/* keep the query visible when the user is deep-linked into a results view */
function syncQuery(raw){ if (heroInput.value !== raw) heroInput.value = raw; }

/* ---------------- list & article wiring ----------------
   drawList()/showPage() render markup; these are the listeners that make it
   interactive. Kept here (last script) so the render functions stay pure. */
document.addEventListener('click', e => {
  const more = e.target.closest('#more');
  if (more){ listState.shown += PAGE; drawList(); return; }

  const chip = e.target.closest('#listRows .chip[data-tag]');
  if (chip){ go('#/t/' + encodeURIComponent(chip.dataset.tag)); return; }

  const row = e.target.closest('#listRows .row');
  if (row){ go('#/p/' + row.dataset.slug); return; }

  if (e.target.id === 'back'){
    if (history.length > 1) history.back(); else go('#/');
  }
});

const sortSel = el('sort');
if (sortSel){
  sortSel.addEventListener('change', () => {
    listState.sort = sortSel.value;
    listState.shown = PAGE;
    drawList();
  });
}

/* ---------------- boot ---------------- */
window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', () => {
  // data sanity: if the bundle is missing, say so plainly rather than drawing an empty shell
  if (!window.WIKI_FULL || !window.WIKI_FULL.items){
    document.querySelector('.wrap').innerHTML =
      '<div class="empty">The wiki data bundle (data/wiki.js) did not load. Re-run '
      + 'extract_full.py, then rebuild this page.</div>';
    return;
  }
  renderHome();
  route();
});
/* DOMContentLoaded may already have fired if this script runs last — cover both */
if (document.readyState !== 'loading'){ renderHome(); route(); }

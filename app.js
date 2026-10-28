/* Signets — fil filtrable des signets X de Guy (statique, sans serveur) */
(() => {
  "use strict";
  const PAGE = 30;
  const $ = (s, r = document) => r.querySelector(s);
  const el = {
    q: $("#q"), sort: $("#sort"), feed: $("#feed"), more: $("#more"), empty: $("#empty"), count: $("#count"),
    catBtn: $("#catBtn"), catList: $("#catList"), catBtnLbl: $("#catBtnLbl"), catBtnN: $("#catBtnN"), catBtnDot: $("#catBtnDot"), active: $("#active"), from: $("#from"), to: $("#to"),
    presets: $("#presets"), types: $("#types"), langs: $("#langs"), byInput: $("#byInput"), byList: $("#byList"),
    bySel: $("#bySel"), newBtn: $("#newBtn"), newN: $("#newN"), filters: $("#filters"), scrim: $("#scrim"), badge: $("#filterBadge"), meta: $("#meta")
  };
  const nf = new Intl.NumberFormat("fr-CA");
  const nfc = new Intl.NumberFormat("fr-CA", { notation: "compact", maximumFractionDigits: 1 });
  const df = new Intl.DateTimeFormat("fr-CA", { day: "numeric", month: "short", year: "numeric" });

  let all = [], cats = [], catColor = {}, catActive = -1, authors = [], results = [], shown = 0;
  const st = { nouv: false, q: "", cat: "", from: "", to: "", by: "", type: [], lang: [], sort: "recent", preset: "" };

  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = s => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const parseD = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const hash = s => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return Math.abs(h); };
  const initials = h => (h.replace(/^@/, "").replace(/[^A-Za-z0-9]/g, "").slice(0, 2) || "?").toUpperCase();
  const avatar = h => `<span class="avatar" aria-hidden="true" style="background:hsl(${hash(h) % 360} 55% 38%)">${esc(initials(h))}</span>`;
  const NO_CAT = "Sans catégorie";
  // Couleur stable par nom de catégorie (hash) : aucune liste codée en dur, une nouvelle catégorie reçoit sa propre teinte.
  // Palette de teintes contrastées ; chaque nom choisit sa case par hash (sondage linéaire pour éviter les doublons).
  // Au-delà de la palette, repli sur une teinte calculée par hash.
  const PALETTE = [204, 340, 48, 145, 270, 10, 180, 95, 300, 28, 228, 160, 320, 65];
  const fnv = s => { let h = 2166136261; for (const c of s) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  function assignColors(names) {
    const used = new Set(), out = {};
    [...names].sort((a, b) => a.localeCompare(b, "fr")).forEach(n => {
      let i = fnv(norm(n)) % PALETTE.length, k = 0;
      while (used.has(i) && k < PALETTE.length) { i = (i + 1) % PALETTE.length; k++; }
      if (k < PALETTE.length) { used.add(i); out[n] = `hsl(${PALETTE[i]} 80% 66%)`; }
      else out[n] = `hsl(${fnv(n) % 360} 70% 65%)`;
    });
    return out;
  }
  const countBy = (arr, k) => arr.reduce((m, x) => (m[x[k]] = (m[x[k]] || 0) + 1, m), {});

  /* ---------- État ↔ URL ---------- */
  function readURL() {
    const p = new URLSearchParams(location.search);
    st.q = p.get("q") || ""; st.cat = p.get("cat") || ""; st.from = p.get("du") || ""; st.to = p.get("au") || "";
    st.by = p.get("par") || ""; st.type = (p.get("type") || "").split(",").filter(Boolean);
    st.lang = (p.get("langue") || "").split(",").filter(Boolean); st.sort = p.get("tri") || "recent"; st.preset = p.get("periode") || "";
    st.nouv = p.get("nouveaux") === "1";
  }
  function writeURL() {
    const p = new URLSearchParams();
    if (st.nouv) p.set("nouveaux", "1"); if (st.q) p.set("q", st.q); if (st.cat) p.set("cat", st.cat);
    if (st.preset) p.set("periode", st.preset); else { if (st.from) p.set("du", st.from); if (st.to) p.set("au", st.to); }
    if (st.by) p.set("par", st.by); if (st.type.length) p.set("type", st.type.join(","));
    if (st.lang.length) p.set("langue", st.lang.join(",")); if (st.sort !== "recent") p.set("tri", st.sort);
    const qs = p.toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
  }
  function applyPreset(v) {
    st.preset = v;
    if (!v) return;
    if (/^\d{4}$/.test(v)) { st.from = `${v}-01-01`; st.to = `${v}-12-31`; }
    else { const d = new Date(); d.setDate(d.getDate() - Number(v)); st.from = iso(d); st.to = iso(new Date()); }
  }

  /* ---------- Filtrage ---------- */
  function filtered(skip) {
    const terms = norm(st.q).split(/\s+/).filter(Boolean);
    return all.filter(x =>
      (!st.nouv || x.nouveau) &&
      (skip === "cat" || !st.cat || x.categorie === st.cat) &&
      (!st.from || x.date >= st.from) && (!st.to || x.date <= st.to) &&
      (!st.by || x.handle === st.by) &&
      (skip === "type" || !st.type.length || st.type.includes(x.type)) &&
      (skip === "lang" || !st.lang.length || st.lang.includes(x.langue)) &&
      (!terms.length || terms.every(t => x._s.includes(t))));
  }
  function sortList(l) {
    const f = { recent: (a, b) => b.date.localeCompare(a.date) || b.jaime - a.jaime,
      ancien: (a, b) => a.date.localeCompare(b.date) || b.jaime - a.jaime,
      jaime: (a, b) => b.jaime - a.jaime }[st.sort] || (() => 0);
    return l.sort(f);
  }

  /* ---------- Rendu ---------- */
  function hl(text) {
    const terms = norm(st.q).split(/\s+/).filter(t => t.length > 1);
    const safe = esc(text);
    if (!terms.length) return safe;
    // surlignage insensible aux accents : on travaille sur les positions du texte normalisé
    const n = norm(text); const marks = [];
    terms.forEach(t => { let i = n.indexOf(t); while (i > -1) { marks.push([i, i + t.length]); i = n.indexOf(t, i + t.length); } });
    if (!marks.length || n.length !== text.length) return safe;
    marks.sort((a, b) => a[0] - b[0]);
    let out = "", pos = 0;
    for (const [a, b] of marks) { if (a < pos) continue; out += esc(text.slice(pos, a)) + "<mark>" + esc(text.slice(a, b)) + "</mark>"; pos = b; }
    return out + esc(text.slice(pos));
  }
  function card(x) {
    const c = catColor[x.categorie];
    return `<article class="card" data-lien="${esc(x.lien)}">
      ${avatar(x.handle)}
      <div class="c-body">
        <div class="c-head"><span class="c-name">${hl(x.nom)}</span><span class="c-handle">${hl(x.handle)}</span><span class="c-sep">·</span><time class="c-date" datetime="${x.date}">${df.format(parseD(x.date))}</time>${x.nouveau ? `<span class="new-badge">Nouveau</span>` : ""}</div>
        <button class="chip" data-cat="${esc(x.categorie)}" style="color:${c};border-color:${c}66" title="Filtrer par cette catégorie"><span class="dot" style="width:6px;height:6px;border-radius:50%;background:${c}"></span>${esc(x.categorie)}</button>
        <h3 class="c-subject">${hl(x.sujet)}</h3>
        <p class="c-desc">${hl(x.description)}</p>
        <div class="c-foot">
          <span class="badge t-${esc(x.type)}">${esc(x.type)}</span>
          <span class="badge">${esc(x.langue)}</span>
          <span class="likes" title="${nf.format(x.jaime)} J'aime"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.1 5.2 3 1.6-1.9 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z"/></svg>${nfc.format(x.jaime)}<span class="sr-only"> J'aime</span></span>
          <a class="see" href="${esc(x.lien)}" target="_blank" rel="noopener noreferrer">Voir sur X <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3h7v7h-2V6.4l-9.3 9.3-1.4-1.4L17.6 5H14zM5 5h6v2H7v10h10v-4h2v6H5z"/></svg></a>
        </div>
      </div></article>`;
  }
  function renderMore() {
    const next = results.slice(shown, shown + PAGE);
    el.feed.insertAdjacentHTML("beforeend", next.map(card).join(""));
    shown += next.length;
    el.more.hidden = shown >= results.length;
    el.more.textContent = `Charger plus (${nf.format(results.length - shown)} restants)`;
  }
  /* Liste déroulante des catégories, construite à partir des données */
  function catOptions() {
    const base = filtered("cat"); const cnt = countBy(base, "categorie");
    return [{ v: "", label: "Toutes", n: base.length }, ...cats.map(c => ({ v: c, label: c, n: cnt[c] || 0 }))];
  }
  function renderCats() {
    const opts = catOptions(); const cur = opts.find(o => o.v === st.cat) || opts[0];
    el.catBtnLbl.textContent = cur.label; el.catBtnN.textContent = nf.format(cur.n);
    el.catBtnDot.hidden = !cur.v; el.catBtnDot.style.background = cur.v ? catColor[cur.v] : "";
    el.catList.innerHTML = opts.map((o, i) => `<li role="option" id="cat-${i}" data-cat="${esc(o.v)}" aria-selected="${o.v === st.cat}" class="${o.n ? "" : "zero"}${i === catActive ? " active" : ""}"><span class="dot${o.v ? "" : " dot-all"}" style="${o.v ? `background:${catColor[o.v]}` : ""}"></span><span class="lbl">${esc(o.label)}</span><span class="n">${nf.format(o.n)}</span></li>`).join("");
  }
  function setCatActive(i) {
    const items = [...el.catList.children]; if (!items.length) return;
    catActive = Math.max(0, Math.min(i, items.length - 1));
    items.forEach((li, j) => li.classList.toggle("active", j === catActive));
    el.catList.setAttribute("aria-activedescendant", items[catActive].id);
    items[catActive].scrollIntoView({ block: "nearest" });
  }
  function openCat(open) {
    el.catList.hidden = !open; el.catBtn.setAttribute("aria-expanded", open);
    if (open) { const i = [...el.catList.children].findIndex(li => li.getAttribute("aria-selected") === "true"); el.catList.focus(); setCatActive(i < 0 ? 0 : i); }
    else catActive = -1;
  }
  function pickCat(v, refocus = true) { st.cat = v; openCat(false); update(); if (refocus) el.catBtn.focus(); }
  el.catBtn.addEventListener("click", () => openCat(el.catList.hidden));
  el.catBtn.addEventListener("keydown", e => { if (["ArrowDown", "ArrowUp"].includes(e.key)) { e.preventDefault(); openCat(true); } });
  el.catList.addEventListener("keydown", e => {
    const items = [...el.catList.children];
    if (e.key === "ArrowDown") { e.preventDefault(); setCatActive(catActive + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setCatActive(catActive - 1); }
    else if (e.key === "Home") { e.preventDefault(); setCatActive(0); }
    else if (e.key === "End") { e.preventDefault(); setCatActive(items.length - 1); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (items[catActive]) pickCat(items[catActive].dataset.cat); }
    else if (e.key === "Escape" || e.key === "Tab") { if (e.key === "Escape") e.preventDefault(); openCat(false); if (e.key === "Escape") el.catBtn.focus(); }
    else if (e.key.length === 1) { const k = norm(e.key); const j = items.findIndex((li, n) => n > catActive && norm(li.textContent).startsWith(k)); const f = j > -1 ? j : items.findIndex(li => norm(li.textContent).startsWith(k)); if (f > -1) setCatActive(f); }
  });
  function renderToggles(box, key, field, values) {
    const cnt = countBy(filtered(key), field);
    box.innerHTML = values.map(v => `<button data-${key}="${esc(v)}" aria-pressed="${st[key].includes(v)}">${esc(v)}<span class="n">${nf.format(cnt[v] || 0)}</span></button>`).join("");
  }
  function renderBy() {
    const a = authors.find(x => x.handle === st.by);
    el.bySel.hidden = !a;
    el.bySel.innerHTML = a ? `${avatar(a.handle)}<span class="who"><b>${esc(a.nom)}</b> ${esc(a.handle)}</span><button aria-label="Retirer ce compte" data-clear="by">✕</button>` : "";
  }
  function renderByList() {
    const t = norm(el.byInput.value.trim());
    const list = authors.filter(a => !t || a._s.includes(t)).slice(0, 50);
    el.byList.innerHTML = list.length ? list.map((a, i) => `<li role="option" id="by-${i}" data-by="${esc(a.handle)}" aria-selected="false">${avatar(a.handle)}<span class="who"><b>${esc(a.nom)}</b><span>${esc(a.handle)}</span></span><span class="n">${a.n}</span></li>`).join("")
      : `<li aria-disabled="true">Aucun compte</li>`;
    el.byList.hidden = false; el.byInput.setAttribute("aria-expanded", "true");
  }
  function renderActive() {
    const chips = [];
    const add = (label, key, val) => chips.push(`<span class="af">${esc(label)}<button aria-label="Retirer ${esc(label)}" data-clear="${key}" data-val="${esc(val || "")}">✕</button></span>`);
    if (st.nouv) add("Nouveaux seulement", "nouv");
    if (st.q) add(`« ${st.q} »`, "q");
    if (st.cat) add(st.cat, "cat");
    if (st.from || st.to) add(st.preset && /^\d{4}$/.test(st.preset) ? st.preset : `${st.from ? df.format(parseD(st.from)) : "…"} → ${st.to ? df.format(parseD(st.to)) : "…"}`, "date");
    if (st.by) add(st.by, "by");
    st.type.forEach(v => add(v, "type", v)); st.lang.forEach(v => add(v, "lang", v));
    el.active.innerHTML = chips.length ? chips.join("") + `<button class="af-reset" data-reset>Tout effacer</button>` : "";
    el.badge.hidden = !(st.from || st.to || st.by || st.type.length || st.lang.length);
  }
  function syncInputs() {
    if (document.activeElement !== el.q) el.q.value = st.q;
    el.sort.value = st.sort; el.from.value = st.from; el.to.value = st.to;
    el.presets.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.preset === st.preset));
  }
  function update() {
    if (st.cat && !cats.includes(st.cat)) st.cat = ""; // catégorie disparue (ex. lien ancien) → « Toutes »
    results = sortList(filtered());
    shown = 0; el.feed.innerHTML = ""; renderMore();
    el.count.innerHTML = `<b>${nf.format(results.length)}</b> signet${results.length > 1 ? "s" : ""}${results.length !== all.length ? ` sur ${nf.format(all.length)}` : ""}`;
    el.empty.hidden = results.length > 0;
    const nNew = all.filter(x => x.nouveau).length;
    el.newN.textContent = nf.format(nNew); el.newBtn.setAttribute("aria-pressed", st.nouv);
    el.newBtn.disabled = !nNew && !st.nouv; el.newBtn.classList.toggle("has-new", nNew > 0);
    renderCats(); renderToggles(el.types, "type", "type", ["Post", "Citation", "Réponse"].filter(v => all.some(x => x.type === v)));
    renderToggles(el.langs, "lang", "langue", langs);
    renderBy(); renderActive(); syncInputs(); writeURL();
  }
  let langs = [];

  function reset() { Object.assign(st, { nouv: false, q: "", cat: "", from: "", to: "", by: "", type: [], lang: [], preset: "", sort: "recent" }); el.byInput.value = ""; update(); }
  function toggle(key, v) { const a = st[key]; const i = a.indexOf(v); i > -1 ? a.splice(i, 1) : a.push(v); update(); }
  function openFilters(open) {
    el.filters.classList.toggle("open", open); el.scrim.hidden = !open;
    $("#openFilters").setAttribute("aria-expanded", open);
    document.body.style.overflow = open ? "hidden" : "";
  }

  /* ---------- Événements ---------- */
  let qT;
  el.q.addEventListener("input", () => { clearTimeout(qT); qT = setTimeout(() => { st.q = el.q.value.trim(); update(); }, 150); });
  el.sort.addEventListener("change", () => { st.sort = el.sort.value; update(); });
  el.from.addEventListener("change", () => { st.from = el.from.value; st.preset = ""; update(); });
  el.to.addEventListener("change", () => { st.to = el.to.value; st.preset = ""; update(); });
  el.more.addEventListener("click", renderMore);
  el.byInput.addEventListener("input", renderByList);
  el.byInput.addEventListener("focus", renderByList);
  el.byInput.addEventListener("keydown", e => {
    const items = [...el.byList.querySelectorAll("li[data-by]")]; let i = items.findIndex(li => li.getAttribute("aria-selected") === "true");
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); if (!items.length) return;
      i = e.key === "ArrowDown" ? Math.min(i + 1, items.length - 1) : Math.max(i - 1, 0);
      items.forEach((li, j) => li.setAttribute("aria-selected", j === i)); items[i].scrollIntoView({ block: "nearest" });
      el.byInput.setAttribute("aria-activedescendant", items[i].id);
    } else if (e.key === "Enter" && items.length) { e.preventDefault(); pickBy((items[i] || items[0]).dataset.by); }
    else if (e.key === "Escape") closeByList();
  });
  function closeByList() { el.byList.hidden = true; el.byInput.setAttribute("aria-expanded", "false"); }
  function pickBy(h) { st.by = h; el.byInput.value = ""; closeByList(); update(); }
  document.addEventListener("click", e => {
    const t = e.target.closest("button,li[data-by],li[data-cat]");
    if (!e.target.closest("#combo")) closeByList();
    if (!e.target.closest("#catdd")) openCat(false);
    if (!t) return;
    if (t.matches("li[data-by]")) return pickBy(t.dataset.by);
    if (t.matches("li[data-cat]")) return pickCat(t.dataset.cat);
    if (t.classList.contains("chip")) { st.cat = st.cat === t.dataset.cat ? "" : t.dataset.cat; update(); window.scrollTo({ top: 0 }); return; }
    if (t.dataset.type !== undefined) return toggle("type", t.dataset.type);
    if (t.dataset.lang !== undefined) return toggle("lang", t.dataset.lang);
    if (t.dataset.preset !== undefined) { if (st.preset === t.dataset.preset) { st.preset = ""; st.from = st.to = ""; } else applyPreset(t.dataset.preset); return update(); }
    if (t.hasAttribute("data-reset")) return reset();
    if (t.dataset.clear) {
      const k = t.dataset.clear;
      if (k === "date") { st.from = st.to = ""; st.preset = ""; }
      else if (k === "type" || k === "lang") st[k] = st[k].filter(v => v !== t.dataset.val);
      else if (k === "nouv") st.nouv = false;
      else st[k] = "";
      return update();
    }
    if (t.id === "newBtn") { st.nouv = !st.nouv; return update(); }
    if (t.id === "openFilters") return openFilters(true);
    if (t.id === "closeFilters" || t.id === "applyFilters") return openFilters(false);
  });
  el.scrim.addEventListener("click", () => openFilters(false));
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !el.catList.hidden) { openCat(false); el.catBtn.focus(); return; } if (e.key === "Escape" && el.filters.classList.contains("open")) openFilters(false); });

  /* ---------- Chargement ---------- */
  fetch("data/signets.json", { cache: "no-cache" }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(d => {
    all = d.signets.map(x => ({ ...x, categorie: String(x.categorie || "").trim() || NO_CAT, nouveau: x.nouveau === true, _s: norm(`${x.sujet} ${x.description} ${x.soumisPar}`) }));
    const cc = countBy(all, "categorie");
    cats = Object.keys(cc).sort((a, b) => cc[b] - cc[a] || a.localeCompare(b, "fr"));
    catColor = assignColors(cats);
    const lc = countBy(all, "langue"); langs = Object.keys(lc).sort((a, b) => lc[b] - lc[a]);
    const am = {};
    all.forEach(x => { (am[x.handle] ||= { handle: x.handle, nom: x.nom, n: 0 }).n++; });
    authors = Object.values(am).sort((a, b) => b.n - a.n || a.handle.localeCompare(b.handle)).map(a => ({ ...a, _s: norm(`${a.handle} ${a.nom}`) }));
    const dates = all.map(x => x.date).sort();
    el.meta.textContent = `${nf.format(all.length)} signets · ${authors.length} comptes · posts du ${df.format(parseD(dates[0]))} au ${df.format(parseD(dates.at(-1)))} · données du ${d.genere}` +
      (d.precedente && d.precedente !== d.genere ? ` · ${nf.format(all.filter(x => x.nouveau).length)} nouveau(x) depuis la génération du ${d.precedente}` : " · aucun nouveau depuis la génération précédente");
    readURL(); if (st.preset) applyPreset(st.preset);
    update();
  }).catch(err => { el.count.textContent = `Impossible de charger les signets (${err.message}).`; });
})();

import sys, json, re
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
data = json.load(open("/workspace/prototypes/proto-signets-x/data/signets.json"))["signets"]
ok = True
def check(name, cond, extra=""):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name, extra)
def pick_cat(p, name):
    p.click("#catBtn"); p.wait_for_selector("#catList:not([hidden])")
    p.locator(f'#catList li[data-cat="{name}"]').click(); p.wait_for_timeout(250)
def opt_n(p, name):
    return int(re.sub(r"\D", "", p.locator(f'#catList li[data-cat="{name}"] .n').inner_text()))
def overflow(p):
    return p.evaluate("Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth")
def list_fits(p):
    return p.evaluate("""(() => { const r = document.querySelector('#catList').getBoundingClientRect();
      return r.left >= 0 && r.right <= innerWidth + 0.5 && r.bottom <= innerHeight + 0.5 && r.width >= 240; })()""")
def cnt(p):
    p.wait_for_timeout(250)
    t = p.inner_text("#count"); return int(re.sub(r"\D", "", t.split("signet")[0]))
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    p = b.new_page(viewport={"width":1280,"height":800})
    errs=[]; p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(BASE); p.wait_for_selector(".card")
    check("total 948", cnt(p)==948 and len(data)==948, p.inner_text("#count"))
    check("30 cartes initiales", p.locator(".card").count()==30)
    if SHOTS: p.screenshot(path=f"{SHOTS}/desktop-accueil.png")
    if not SHOTS or "live" not in SHOTS:
        while p.is_visible("#more"): p.click("#more")
        check("toutes les cartes chargées = 948", p.locator(".card").count()==948)
    p.goto(BASE); p.wait_for_selector(".card")
    # catégorie
    cat="Tesla – véhicules, FSD et Optimus"; exp=sum(1 for x in data if x["categorie"]==cat)
    cats_data = sorted(set(x["categorie"] for x in data))
    p.click("#catBtn"); p.wait_for_selector("#catList:not([hidden])")
    opts = p.eval_on_selector_all("#catList li", "l => l.map(x => x.dataset.cat)")
    check("liste = Toutes + catégories du JSON", opts[0]=="" and sorted(opts[1:])==cats_data, f"{len(opts)-1} catégories")
    check("liste « Toutes (948) »", p.inner_text("#catList li >> nth=0").split("\n")[0].strip()=="Toutes" and opt_n(p, "")==948)
    check("compte Tesla dans la liste = 119", opt_n(p, cat)==exp==119)
    check("pastilles de couleur", p.eval_on_selector_all("#catList li .dot", "l => l.slice(1).every(d => d.style.background)"))
    check("liste lisible 1280 (dans l'écran)", list_fits(p))
    p.keyboard.press("Escape")
    pick_cat(p, cat); check("liste déroulante Tesla", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    check("bouton affiche Tesla", cat in p.inner_text("#catBtn") and "119" in p.inner_text("#catBtn"))
    check("URL cat", "cat=" in p.url)
    p.click("#types [data-type='Citation']"); p.click("#catBtn")
    expc=sum(1 for x in data if x["categorie"]==cat and x["type"]=="Citation"); check("comptes suivent les autres filtres", opt_n(p, cat)==expc and opt_n(p, "")==175, f"{opt_n(p, cat)} vs {expc}")
    p.keyboard.press("Escape"); p.click("#types [data-type='Citation']")
    # clavier : focus bouton, flèche bas, Fin, Entrée
    p.click(".af-reset"); p.focus("#catBtn"); p.keyboard.press("ArrowDown"); p.keyboard.press("End"); p.keyboard.press("Enter"); p.wait_for_timeout(250)
    last = opts[-1]; check("clavier (↓, Fin, Entrée)", f"cat=" in p.url and cnt(p)==sum(1 for x in data if x["categorie"]==last), last)
    check("focus revient au bouton", p.evaluate("document.activeElement.id")=="catBtn")
    p.keyboard.press("ArrowDown"); p.keyboard.press("Home"); p.keyboard.press("Enter"); p.wait_for_timeout(250); check("clavier retour à Toutes", cnt(p)==948)
    # clic sur la puce d'une carte → règle la liste
    chipcat = p.locator(".card .chip").first.get_attribute("data-cat"); p.locator(".card .chip").first.click(); p.wait_for_timeout(250)
    check("puce de carte règle la liste", chipcat in p.inner_text("#catBtn") and cnt(p)==sum(1 for x in data if x["categorie"]==chipcat))
    p.click(".af-reset")
    # catégorie inexistante dans l'URL → Toutes
    p.goto(BASE + "?cat=Cat%C3%A9gorie%20disparue&type=Post"); p.wait_for_selector(".card")
    check("cat inconnue dans l'URL → Toutes", p.inner_text("#catBtnLbl")=="Toutes" and "cat=" not in p.url and cnt(p)==745, p.url)
    p.goto(BASE); p.wait_for_selector(".card")
    # année
    p.click("[data-preset='2025']"); exp=sum(1 for x in data if x["date"].startswith("2025")); check("préréglage 2025", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    p.click("[data-preset='2025']")
    p.fill("#from","2026-10-01"); p.dispatch_event("#from","change"); p.fill("#to","2026-10-15"); p.dispatch_event("#to","change")
    exp=sum(1 for x in data if "2026-10-01"<=x["date"]<="2026-10-15"); check("plage de dates", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    p.click("[data-reset] >> nth=0") if False else p.click(".af-reset"); check("reset", cnt(p)==948)
    # soumis par
    p.fill("#byInput","elon"); p.wait_for_selector("#byList li[data-by]")
    p.click("#byList li[data-by='@elonmusk']"); exp=sum(1 for x in data if x["handle"]=="@elonmusk"); check("soumis par @elonmusk", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    p.click(".af-reset")
    # type / langue
    p.click("#types [data-type='Citation']"); exp=sum(1 for x in data if x["type"]=="Citation"); check("type Citation", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    p.click("#langs [data-lang='Français']"); exp=sum(1 for x in data if x["type"]=="Citation" and x["langue"]=="Français"); check("type+langue", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    url=p.url; p.goto(url); p.wait_for_selector("#count b"); check("état restauré depuis l'URL", cnt(p)==exp, url)
    p.click(".af-reset")
    # recherche
    p.fill("#q","starship"); 
    import unicodedata
    n=lambda s:"".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn").lower()
    exp=sum(1 for x in data if "starship" in n(x["sujet"]+" "+x["description"]+" "+x["soumisPar"])); check("recherche starship", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    p.fill("#q","")
    # tri J'aime
    p.select_option("#sort","jaime"); p.wait_for_timeout(200)
    top=p.locator(".card").first.get_attribute("data-lien"); exp=max(data,key=lambda x:x["jaime"])["lien"]; check("tri plus aimés", top==exp)
    p.select_option("#sort","ancien"); p.wait_for_timeout(200)
    check("tri plus anciens", p.locator(".card time").first.get_attribute("datetime")==min(x["date"] for x in data))
    p.select_option("#sort","recent")
    a=p.locator(".card .see").first; check("lien Voir sur X nouvel onglet", a.get_attribute("target")=="_blank" and a.get_attribute("href").startswith("https://x.com/"))
    check("pied de page", "© GTR Technologies Inc. · Tous droits réservés." in p.inner_text(".footer") and "Site réalisé par la GTR-Teams" in p.inner_text(".footer"))
    if SHOTS:
        pick_cat(p, "Espace – Starship, NASA et Artemis"); p.click("#langs [data-lang='Français']"); p.wait_for_timeout(300)
        p.screenshot(path=f"{SHOTS}/desktop-filtre-espace-francais.png"); p.click(".af-reset")
        p.evaluate("window.scrollTo(0,0)"); p.click("#catBtn"); p.wait_for_timeout(200); p.screenshot(path=f"{SHOTS}/desktop-liste-categories.png"); p.keyboard.press("Escape")
        p.evaluate("window.scrollTo(0,document.body.scrollHeight)"); p.click("#more"); p.evaluate("window.scrollTo(0,document.body.scrollHeight)"); p.wait_for_timeout(200)
    # mobile
    m = b.new_page(viewport={"width":390,"height":844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    m.on("pageerror", lambda e: errs.append(str(e)))
    m.goto(BASE); m.wait_for_selector(".card")
    check("mobile 948", cnt(m)==948)
    sw = m.evaluate("document.documentElement.scrollWidth"); check("mobile sans débordement horizontal", sw<=390, sw)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-accueil.png")
    m.click("#openFilters"); m.wait_for_timeout(400); check("tiroir filtres ouvert", m.is_visible("#types"))
    m.click("#types [data-type='Réponse']"); m.click("[data-preset='2026']"); m.wait_for_timeout(300)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-tiroir-filtres.png")
    m.click("#applyFilters"); m.wait_for_timeout(400)
    exp=sum(1 for x in data if x["type"]=="Réponse" and x["date"].startswith("2026")); check("mobile filtres Réponse+2026", cnt(m)==exp, f"{cnt(m)} vs {exp}")
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-filtre-reponses-2026.png")
    m.click(".af-reset"); m.evaluate("window.scrollTo(0,0)")
    m.tap("#catBtn"); m.wait_for_timeout(250)
    check("mobile liste lisible (dans l'écran) et sans débordement", list_fits(m) and overflow(m)<=0)
    h = m.eval_on_selector_all("#catList li", "l => Math.min(...l.map(x => x.getBoundingClientRect().height))"); check("mobile options ≥ 40 px (tactile)", h>=40, h)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-liste-categories.png")
    m.locator('#catList li[data-cat="Humour et sketchs"]').tap(); m.wait_for_timeout(300)
    check("mobile liste Humour 39", cnt(m)==39)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-categorie-humour.png")
    m.evaluate("window.scrollTo(0,document.body.scrollHeight)"); m.wait_for_timeout(200)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-pied-de-page.png")
    # tablette 768
    t = b.new_page(viewport={"width":768,"height":1024}, has_touch=True)
    t.on("pageerror", lambda e: errs.append(str(e)))
    t.goto(BASE); t.wait_for_selector(".card")
    check("tablette 948 + sans débordement", cnt(t)==948 and overflow(t)<=0, overflow(t))
    t.tap("#catBtn"); t.wait_for_timeout(200)
    check("tablette liste ouverte, lisible, sans débordement", list_fits(t) and overflow(t)<=0)
    if SHOTS: t.screenshot(path=f"{SHOTS}/tablette-liste-categories.png")
    t.locator('#catList li[data-cat="Tesla – véhicules, FSD et Optimus"]').tap(); t.wait_for_timeout(250)
    check("tablette tap Tesla 119", cnt(t)==119)
    check("desktop 1280 sans débordement", overflow(p)<=0)
    check("aucune erreur JS", not errs, errs)
    # JSON modifié à la volée (rien d'écrit) : Humour retirée, nouvelle catégorie ajoutée
    import copy
    mod = copy.deepcopy(json.load(open("/workspace/prototypes/proto-signets-x/data/signets.json")))
    for x in mod["signets"]:
        if x["categorie"] == "Humour et sketchs": x["categorie"] = "Catégorie test ajoutée"
    mod["signets"][0]["categorie"] = ""
    d = b.new_page(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True)
    d.on("pageerror", lambda e: errs.append(str(e)))
    d.route("**/data/signets.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(mod)))
    d.goto(BASE + "?cat=Humour%20et%20sketchs"); d.wait_for_selector(".card")
    check("dyn : cat retirée dans l'URL → Toutes", d.inner_text("#catBtnLbl")=="Toutes" and cnt(d)==948 and "cat=" not in d.url)
    d.tap("#catBtn"); d.wait_for_timeout(200)
    opts = d.eval_on_selector_all("#catList li", "l => l.map(x => x.dataset.cat)")
    exp_cats = sorted(set((x["categorie"] or "Sans catégorie") for x in mod["signets"]))
    check("dyn : liste = catégories du JSON modifié", sorted(opts[1:])==exp_cats and "Humour et sketchs" not in opts and "Catégorie test ajoutée" in opts and "Sans catégorie" in opts, f"{len(opts)-1} catégories")
    newc = sum(1 for x in mod["signets"] if x["categorie"]=="Catégorie test ajoutée")
    check("dyn : nouvelle catégorie a une couleur", bool(d.locator('#catList li[data-cat="Catégorie test ajoutée"] .dot').get_attribute("style")))
    d.locator('#catList li[data-cat="Catégorie test ajoutée"]').tap(); d.wait_for_timeout(250)
    check("dyn : filtre nouvelle catégorie", cnt(d)==newc, f"{cnt(d)} vs {newc}")
    check("aucune erreur JS (dyn)", not errs, errs)
    b.close()
print("RESULTAT:", "OK" if ok else "ECHEC")

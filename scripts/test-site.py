import sys, json, re
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
data = json.load(open("/workspace/prototypes/proto-signets-x/data/signets.json"))["signets"]
N = len(data)
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
    check("total 948", cnt(p)==N and len(data)==N, p.inner_text("#count"))
    check("30 cartes initiales", p.locator(".card").count()==30)
    if SHOTS: p.screenshot(path=f"{SHOTS}/desktop-accueil.png")
    if not SHOTS or "live" not in SHOTS:
        while p.is_visible("#more"): p.click("#more")
        check("toutes les cartes chargées = 948", p.locator(".card").count()==N)
    p.goto(BASE); p.wait_for_selector(".card")
    # catégorie
    cat="Tesla et Optimus"; exp=sum(1 for x in data if x["categorie"]==cat)
    cats_data = sorted(set(x["categorie"] for x in data))
    p.click("#catBtn"); p.wait_for_selector("#catList:not([hidden])")
    opts = p.eval_on_selector_all("#catList li", "l => l.map(x => x.dataset.cat)")
    check("liste = Toutes + catégories du JSON", opts[0]=="" and sorted(opts[1:])==cats_data, f"{len(opts)-1} catégories")
    check("liste « Toutes (948) »", p.inner_text("#catList li >> nth=0").split("\n")[0].strip()=="Toutes" and opt_n(p, "")==N)
    check("compte Tesla dans la liste = 119", opt_n(p, cat)==exp==119)
    check("pastilles de couleur", p.eval_on_selector_all("#catList li .dot", "l => l.slice(1).every(d => d.style.background)"))
    check("liste lisible 1280 (dans l'écran)", list_fits(p))
    p.keyboard.press("Escape")
    pick_cat(p, cat); check("liste déroulante Tesla", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    check("bouton affiche Tesla", cat in p.inner_text("#catBtn") and "119" in p.inner_text("#catBtn"))
    check("URL cat", "cat=" in p.url)
    p.click("#types [data-type='Citation']"); p.click("#catBtn")
    expc=sum(1 for x in data if x["categorie"]==cat and x["type"]=="Citation"); check("comptes suivent les autres filtres", opt_n(p, cat)==expc and opt_n(p, "")==sum(1 for x in data if x["type"]=="Citation"), f"{opt_n(p, cat)} vs {expc}")
    p.keyboard.press("Escape"); p.click("#types [data-type='Citation']")
    # clavier : focus bouton, flèche bas, Fin, Entrée
    p.click(".af-reset"); p.focus("#catBtn"); p.keyboard.press("ArrowDown"); p.keyboard.press("End"); p.keyboard.press("Enter"); p.wait_for_timeout(250)
    last = opts[-1]; check("clavier (↓, Fin, Entrée)", f"cat=" in p.url and cnt(p)==sum(1 for x in data if x["categorie"]==last), last)
    check("focus revient au bouton", p.evaluate("document.activeElement.id")=="catBtn")
    p.keyboard.press("ArrowDown"); p.keyboard.press("Home"); p.keyboard.press("Enter"); p.wait_for_timeout(250); check("clavier retour à Toutes", cnt(p)==N)
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
    p.click("[data-reset] >> nth=0") if False else p.click(".af-reset"); check("reset", cnt(p)==N)
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
    check("mobile 948", cnt(m)==N)
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
    m.locator('#catList li[data-cat="Divers et humour"]').tap(); m.wait_for_timeout(300)
    check("mobile liste Divers et humour 179", cnt(m)==179)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-categorie-humour.png")
    m.evaluate("window.scrollTo(0,document.body.scrollHeight)"); m.wait_for_timeout(200)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-pied-de-page.png")
    # tablette 768
    t = b.new_page(viewport={"width":768,"height":1024}, has_touch=True)
    t.on("pageerror", lambda e: errs.append(str(e)))
    t.goto(BASE); t.wait_for_selector(".card")
    check("tablette 948 + sans débordement", cnt(t)==N and overflow(t)<=0, overflow(t))
    t.tap("#catBtn"); t.wait_for_timeout(200)
    check("tablette liste ouverte, lisible, sans débordement", list_fits(t) and overflow(t)<=0)
    if SHOTS: t.screenshot(path=f"{SHOTS}/tablette-liste-categories.png")
    t.locator('#catList li[data-cat="Tesla et Optimus"]').tap(); t.wait_for_timeout(250)
    check("tablette tap Tesla 119", cnt(t)==119)
    check("desktop 1280 sans débordement", overflow(p)<=0)
    check("aucune erreur JS", not errs, errs)
    # JSON modifié à la volée (rien d'écrit) : Humour retirée, nouvelle catégorie ajoutée
    import copy
    mod = copy.deepcopy(json.load(open("/workspace/prototypes/proto-signets-x/data/signets.json")))
    for x in mod["signets"]:
        if x["categorie"] == "Divers et humour": x["categorie"] = "Catégorie test ajoutée"
    mod["signets"][0]["categorie"] = ""
    d = b.new_page(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True)
    d.on("pageerror", lambda e: errs.append(str(e)))
    d.route("**/data/signets.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(mod)))
    d.goto(BASE + "?cat=Divers%20et%20humour"); d.wait_for_selector(".card")
    check("dyn : cat retirée dans l'URL → Toutes", d.inner_text("#catBtnLbl")=="Toutes" and cnt(d)==N and "cat=" not in d.url)
    d.tap("#catBtn"); d.wait_for_timeout(200)
    opts = d.eval_on_selector_all("#catList li", "l => l.map(x => x.dataset.cat)")
    exp_cats = sorted(set((x["categorie"] or "Sans catégorie") for x in mod["signets"]))
    check("dyn : liste = catégories du JSON modifié", sorted(opts[1:])==exp_cats and "Divers et humour" not in opts and "Catégorie test ajoutée" in opts and "Sans catégorie" in opts, f"{len(opts)-1} catégories")
    newc = sum(1 for x in mod["signets"] if x["categorie"]=="Catégorie test ajoutée")
    check("dyn : nouvelle catégorie a une couleur", bool(d.locator('#catList li[data-cat="Catégorie test ajoutée"] .dot').get_attribute("style")))
    d.locator('#catList li[data-cat="Catégorie test ajoutée"]').tap(); d.wait_for_timeout(250)
    check("dyn : filtre nouvelle catégorie", cnt(d)==newc, f"{cnt(d)} vs {newc}")
    check("aucune erreur JS (dyn)", not errs, errs)
    # ---------- Compteur « nouveaux » ----------
    real = json.load(open("/workspace/prototypes/proto-signets-x/data/signets.json"))
    nreal = sum(1 for x in real["signets"] if x.get("nouveau"))
    check("nouveaux : champ nouveaux du JSON = nb de signets marqués", real.get("nouveaux")==nreal and all("nouveau" in x for x in real["signets"]), nreal)
    r = b.new_page(viewport={"width":1280,"height":800}); r.on("pageerror", lambda e: errs.append(str(e)))
    r.goto(BASE); r.wait_for_selector(".card")
    check("nouveaux : compteur de l'en-tête = données réelles", r.inner_text("#newN")==str(nreal) and r.locator(".card .new-badge").count()==sum(1 for x in real["signets"][:30] if x.get("nouveau")), r.inner_text("#newN"))
    if nreal == 0: check("nouveaux : bouton désactivé quand 0", r.is_disabled("#newBtn"))
    r.close()
    mod2 = copy.deepcopy(real); NEWL = [x["lien"] for x in mod2["signets"][2:9:2]] + [mod2["signets"][-1]["lien"]]
    for x in mod2["signets"]: x["nouveau"] = x["lien"] in NEWL
    mod2["nouveaux"] = len(NEWL); mod2["precedente"] = "2026-10-20 10:00"; mod2["genere"] = "2026-10-27 08:00"
    route = lambda r_: r_.fulfill(status=200, content_type="application/json", body=json.dumps(mod2))
    for vw, vh, mob in ((1280, 800, False), (390, 844, True)):
        q = b.new_page(viewport={"width":vw,"height":vh}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
        q.on("pageerror", lambda e: errs.append(str(e))); q.route("**/data/signets.json*", route)
        q.goto(BASE); q.wait_for_selector(".card"); tag = "mobile" if mob else "desktop"
        check(f"nouveaux {tag} : compteur = 5", q.inner_text("#newN")=="5" and not q.is_disabled("#newBtn"))
        check(f"nouveaux {tag} : badges Nouveau dans les 30 premières cartes = 4", q.locator(".card .new-badge").count()==4)
        bb = q.locator("#newBtn").bounding_box(); check(f"nouveaux {tag} : bouton ≥ 40 px et dans l'écran", bb["height"]>=40 and bb["x"]+bb["width"]<=vw and overflow(q)<=0, bb)
        (q.tap if mob else q.click)("#newBtn"); q.wait_for_timeout(250)
        check(f"nouveaux {tag} : filtre Nouveaux seulement = 5", cnt(q)==5 and q.locator(".card").count()==5 and q.locator(".card .new-badge").count()==5 and "nouveaux=1" in q.url)
        check(f"nouveaux {tag} : puce de filtre actif", "Nouveaux seulement" in q.inner_text("#active"))
        if SHOTS: q.screenshot(path=f"{SHOTS}/{tag}-nouveaux.png")
        if not mob:
            q.click("#catBtn"); check("nouveaux : liste des catégories suit le filtre (Toutes = 5)", opt_n(q, "")==5); q.keyboard.press("Escape")
            u = q.url; q.goto(u); q.wait_for_selector(".card"); check("nouveaux : état restauré depuis l'URL", cnt(q)==5 and q.get_attribute("#newBtn","aria-pressed")=="true")
            q.click("#active [data-clear='nouv']"); q.wait_for_timeout(250); check("nouveaux : retirer la puce → 948", cnt(q)==N and "nouveaux" not in q.url)
            q.click("#newBtn"); q.click(".af-reset"); q.wait_for_timeout(250); check("nouveaux : Tout effacer → 948", cnt(q)==N)
            check("nouveaux : méta indique la génération précédente", "5 nouveau(x) depuis la génération du 2026-10-20 10:00" in q.inner_text("#meta"))
        else:
            check("nouveaux mobile : sans débordement filtre actif", overflow(q)<=0)
        q.close()
    # Script : un signet absent de la génération précédente est « nouveau » ; relancer sans changement garde la même base
    import subprocess, tempfile, shutil, os
    tmp = tempfile.mkdtemp(); shutil.copytree("/workspace/prototypes/proto-signets-x/scripts", f"{tmp}/scripts"); os.makedirs(f"{tmp}/data")
    prev = copy.deepcopy(real); prev["signets"] = prev["signets"][3:]; prev["genere"] = "2026-10-20 10:00"
    json.dump(prev, open(f"{tmp}/data/signets.json", "w"))
    xl = "/workspace/x_signets/Signets_X.xlsx"
    for _ in range(2): subprocess.run(["python3", f"{tmp}/scripts/build-data.py", xl], check=True, capture_output=True)
    out = json.load(open(f"{tmp}/data/signets.json"))
    check("script : 3 nouveaux détectés et conservés au 2e build", out["nouveaux"]==3 and [x["nouveau"] for x in out["signets"][:4]]==[True,True,True,False] and out["precedente"]=="2026-10-20 10:00")
    shutil.rmtree(tmp)
    check("aucune erreur JS (nouveaux)", not errs, errs)
    b.close()
print("RESULTAT:", "OK" if ok else "ECHEC")

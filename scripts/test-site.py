import sys, json, re
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
data = json.load(open("/workspace/prototypes/proto-signets-x/data/signets.json"))["signets"]
ok = True
def check(name, cond, extra=""):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name, extra)
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
    p.click(f".nav .cat-btn[data-cat='{cat}']"); check("catégorie Tesla", cnt(p)==exp, f"{cnt(p)} vs {exp}")
    check("URL cat", "cat=" in p.url)
    nav_n = int(re.sub(r"\D","",p.inner_text(f".nav .cat-btn[data-cat='{cat}'] .n"))); check("compte de catégorie", nav_n==exp)
    p.click(".nav .cat-btn[data-cat='']")
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
        p.click(f".nav .cat-btn[data-cat='Espace – Starship, NASA et Artemis']"); p.click("#langs [data-lang='Français']"); p.wait_for_timeout(300)
        p.screenshot(path=f"{SHOTS}/desktop-filtre-espace-francais.png"); p.click(".af-reset")
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
    m.click(".af-reset"); m.click("#catsMobile [data-cat='Humour et sketchs']"); m.wait_for_timeout(300)
    check("mobile puce catégorie", cnt(m)==39)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-categorie-humour.png")
    m.evaluate("window.scrollTo(0,document.body.scrollHeight)"); m.wait_for_timeout(200)
    if SHOTS: m.screenshot(path=f"{SHOTS}/mobile-pied-de-page.png")
    check("aucune erreur JS", not errs, errs)
    b.close()
print("RESULTAT:", "OK" if ok else "ECHEC")

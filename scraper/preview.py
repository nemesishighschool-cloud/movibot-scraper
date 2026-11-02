"""Mini serveur de prévisualisation : voir et tester les lecteurs dans une page.

Aucune dépendance externe (bibliothèque standard). Aucun octet de vidéo ne
passe par ce serveur : le navigateur charge directement le lecteur tiers.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .players import sonde
from .storage import COLONNES

PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>MoviBot — aperçu</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0e1117;color:#e6e6e6;font-family:Arial,sans-serif}
header{padding:18px 20px;background:linear-gradient(135deg,#123152,#0e1117);border-bottom:1px solid #2a3a51}
h1{margin:0 0 5px;font-size:22px}.sous{margin:0;color:#9aa4b2;font-size:13px}
.kpis{display:flex;flex-wrap:wrap;gap:9px;padding:14px 20px}.kpi{flex:1;min-width:120px;background:#151a22;border:1px solid #2a3442;border-radius:9px;padding:11px}
.kpi b{display:block;font-size:20px;color:#58a6ff}.kpi span{font-size:11px;color:#9aa4b2}
#lecteur{padding:0 20px 12px}.cadre{background:#000;border:1px solid #334155;border-radius:11px;overflow:hidden}
.entete{padding:10px 14px;background:#151a22;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.entete b{font-size:15px}.fermer{background:#3a1d1d;color:#ff9b95;border:0;border-radius:7px;padding:6px 11px;cursor:pointer}
.cadre iframe{width:100%;height:min(60vh,480px);border:0;display:block;background:#000}
.diag{margin-top:8px;padding:11px;border-radius:9px;background:#111a26;border:1px solid #2b3a4d;font-size:13px;line-height:1.5}
.diag.pret{border-color:#2d6a3f;background:#10261a}.diag.attente{border-color:#7a5a15;background:#261f10}
.barre{display:flex;gap:8px;flex-wrap:wrap;padding:12px 20px}
input,select{padding:10px 12px;font-size:14px;border-radius:8px;border:1px solid #3a4c66;background:#1b1f27;color:#fff}input{flex:1;min-width:220px}
#compteur{padding:0 20px 9px;font-size:13px;color:#9aa4b2}
#liste{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:11px;padding:0 20px 24px}
.carte{display:flex;gap:11px;background:#151a22;border:1px solid #2a3442;border-radius:11px;padding:11px}
.affiche{flex:none;width:66px;height:98px;border-radius:7px;position:relative;overflow:hidden;background:linear-gradient(150deg,#1f6feb,#7b3fa1);display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:bold}
.affiche img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.corps{min-width:0;flex:1}.titre{font-weight:bold;font-size:14px;margin:0 0 5px}
.badges{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}.b{font-size:10px;padding:2px 6px;border-radius:20px;background:#22304a;color:#a9c7ff}
.b.src{background:#3b2c12;color:#f0c674}.b.ok{background:#173a24;color:#7ee787}.b.no{background:#3a1d1d;color:#ff9b95}.b.at{background:#3a3212;color:#f0d674}
.syn{font-size:11px;color:#9aa4b2;margin:0 0 7px}.actions{display:flex;gap:6px;flex-wrap:wrap}
.actions button,.actions a{padding:7px 10px;font-size:12px;border:0;border-radius:7px;cursor:pointer;text-decoration:none;color:#fff;background:#238636}
.actions a.dl{background:#1f6feb}.actions a.ext{background:#334155}
footer{padding:16px 20px 30px;font-size:12px;color:#7d8896;border-top:1px solid #2a3442;line-height:1.6}
</style></head><body>
<header><h1>MoviBot — aperçu de la base web</h1><p class="sous">Données de votre base · le lecteur est chargé directement par le navigateur</p></header>
<div class="kpis"><div class="kpi"><b id="k1">…</b><span>fiches</span></div><div class="kpi"><b id="k2">…</b><span>avec lecteur</span></div><div class="kpi"><b id="k3">…</b><span>lecteurs prêts</span></div><div class="kpi"><b id="k4">…</b><span>attente 180 s</span></div></div>
<div id="lecteur"></div>
<div class="barre"><input id="q" placeholder="Chercher un titre, un genre, une année…">
<select id="src"><option value="">Toutes les sources</option><option value="frenchstream">FrenchStream</option><option value="franime">FRAnime</option></select>
<select id="f"><option value="">Tous</option><option value="lecteur">Avec lecteur</option><option value="pret">Lecteur prêt</option><option value="film">Films</option><option value="serie">Séries</option><option value="anime">Animes</option></select></div>
<div id="compteur"></div><div id="liste"></div>
<footer>Le cadre affiche le lecteur du site source ; notre serveur ne fait passer aucun octet de vidéo. Le bouton « ⬇ Télécharger » ouvre une page tierce dans un nouvel onglet.</footer>
<script>
const D=__PAYLOAD__;const $=i=>document.getElementById(i);
function rendre(){const q=$('q').value.trim().toLowerCase(),src=$('src').value,f=$('f').value;
const l=D.filter(d=>{const h=(d.title+' '+d.year+' '+(d.genres||[]).join(' ')).toLowerCase();
if(q&&!h.includes(q))return false;if(src&&d.source!==src)return false;
if(f==='lecteur'&&!d.embed_url)return false;if(f==='pret'&&d.etat_lecteur!=='pret')return false;
if(['film','serie','anime'].includes(f)&&d.kind!==f)return false;return true});
$('compteur').textContent=l.length+' résultat(s) sur '+D.length;
$('liste').innerHTML=l.map(d=>{let b=`<span class="b src">${d.source}</span>`;
if(d.kind)b+=`<span class="b">${d.kind}</span>`;if(d.year)b+=`<span class="b">${d.year}</span>`;
if(d.season)b+=`<span class="b">S${d.season}</span>`;if(d.episode_count)b+=`<span class="b">${d.episode_count} ép.</span>`;
if(d.etat_lecteur==='pret')b+=`<span class="b ok">✅ prêt</span>`;
else if(d.etat_lecteur==='attente')b+=`<span class="b at">⏳ 180 s</span>`;
else if(d.notes&&d.notes.includes('connexion'))b+=`<span class="b no">🔒 connexion</span>`;
else b+=`<span class="b">lecteur non exposé</span>`;
const poster=d.poster_url?`<img src="${d.poster_url}" onerror="this.style.display='none'">`:'';
const dl=d.download_url?`<a class="dl" href="${d.download_url}" target="_blank" rel="noopener">⬇ Télécharger</a>`:'';
return `<div class="carte"><div class="affiche">${(d.title||'?').slice(0,2).toUpperCase()}${poster}</div><div class="corps">
<div class="titre">${(d.title||'').replace(/</g,'&lt;')}</div><div class="badges">${b}</div>
<p class="syn">${(d.genres||[]).slice(0,3).join(' · ')}</p>
<div class="actions"><button onclick="voir(${d.id})">▶ Regarder</button>${dl}</div></div></div>`}).join('')}
async function voir(id){const d=D.find(x=>x.id===id);if(!d)return;const z=$('lecteur');
if(!d.embed_url){z.innerHTML=`<div class="cadre"><div class="entete"><b>${d.title} — pas de lecteur</b><button class="fermer" onclick="$('lecteur').innerHTML=''">✕</button></div><div class="diag">Cette fiche n'expose pas de lecteur. Relancez <code>run</code> avec les clics sur les onglets activés.</div></div>`;return}
z.innerHTML=`<div class="cadre"><div class="entete"><b>▶ ${d.title}</b><button class="fermer" onclick="$('lecteur').innerHTML=''">✕</button></div>
<iframe src="${d.embed_url}" allowfullscreen allow="autoplay; encrypted-media; fullscreen"></iframe></div><div class="diag" id="diag">Diagnostic…</div>`;
try{const p=await(await fetch('/api/probe?url='+encodeURIComponent(d.embed_url))).json();
const e=$('diag');e.className='diag '+(p.etat==='pret'?'pret':'attente');
e.textContent=`${p.etat.toUpperCase()} — HTTP ${p.http||'—'}, ${p.flux||0} flux, X-Frame-Options : ${p.x_frame_options||'—'}`}catch(err){}}
async function init(){const s=await(await fetch('/api/stats')).json();
$('k1').textContent=s.fiches;$('k2').textContent=s.avec_lecteur;
$('k3').textContent=s.lecteurs_prets;
$('k4').textContent=await(await fetch('/api/attente')).json().then(x=>x.n);
rendre()}
['q','src','f'].forEach(i=>$(i).addEventListener(i==='q'?'input':'change',rendre));init();
</script></body></html>"""


def demarrer(chemin_db: str, port: int | None = None):
    port = int(port or os.environ.get("SCRAPER_PREVIEW_PORT", "8090"))
    db = os.path.abspath(chemin_db)

    def lignes():
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        out = []
        cols = ["id", "source", "title", "kind", "year", "season", "episode_count",
                "languages", "genres", "poster_url", "embed_url", "download_url",
                "etat_lecteur", "notes"]
        for r in c.execute("SELECT " + ",".join(cols) + " FROM web_media"):
            d = dict(r)
            for k in ("languages", "genres"):
                try:
                    d[k] = json.loads(d[k] or "[]")
                except Exception:
                    d[k] = []
            out.append(d)
        c.close()
        return out

    page = PAGE.replace("__PAYLOAD__",
                        json.dumps(lignes(), ensure_ascii=False).replace("</", "<\\/"))

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def envoie(self, code, corps, ctype="application/json; charset=utf-8"):
            data = corps.encode() if isinstance(corps, str) else corps
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            try:
                if u.path == "/":
                    self.envoie(200, page, "text/html; charset=utf-8")
                elif u.path == "/api/probe":
                    self.envoie(200, json.dumps(sonde(q.get("url", [""])[0])))
                elif u.path in ("/api/stats", "/api/attente"):
                    c = sqlite3.connect(db)
                    if u.path == "/api/stats":
                        self.envoie(200, json.dumps({
                            "fiches": c.execute("SELECT COUNT(*) FROM web_media").fetchone()[0],
                            "avec_lecteur": c.execute("SELECT COUNT(*) FROM web_media WHERE embed_url IS NOT NULL").fetchone()[0],
                            "lecteurs_prets": c.execute("SELECT COUNT(*) FROM web_media WHERE etat_lecteur='pret'").fetchone()[0]}))
                    else:
                        self.envoie(200, json.dumps({"n": c.execute(
                            "SELECT COUNT(*) FROM web_media WHERE etat_lecteur='attente'").fetchone()[0]}))
                    c.close()
                else:
                    self.envoie(404, '{"ok":false}')
            except Exception as e:
                self.envoie(500, json.dumps({"ok": False, "error": str(e)[:120]}))

    print(f"=== Aperçu sur http://0.0.0.0:{port} | base {db} ===", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


import os, base64, json, datetime, requests
from flask import Flask, render_template, request, Response, flash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "replace-me")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_FILE = os.environ.get("GITHUB_FILE", "laudos.json")
GITHUB_API = "https://api.github.com"

HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

def get_remote_json():
    if not GITHUB_REPO:
        return {"last_number": 0}
    owner_repo = GITHUB_REPO.strip()
    raw_url = f"https://raw.githubusercontent.com/{owner_repo}/main/{GITHUB_FILE}"
    try:
        r = requests.get(raw_url, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            return {"last_number": 0}
    except Exception:
        return {"last_number": 0}

def get_file_sha():
    if not GITHUB_REPO:
        return None
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code == 200:
        data = r.json()
        return data.get("sha")
    return None

def update_remote_json(new_json, message="Update laudos.json via web app"):
    if not GITHUB_REPO or not GITHUB_TOKEN:
        return False, "Missing GITHUB_REPO or GITHUB_TOKEN"
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    sha = get_file_sha()
    content_b64 = base64.b64encode(json.dumps(new_json, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": content_b64, "branch": "main"}
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=HEADERS, json=payload, timeout=10)
    if r.status_code in (200, 201):
        return True, r.json()
    else:
        return False, f"GitHub API error {r.status_code}: {r.text}"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        client = request.form.get("client", "").strip()
        sample = request.form.get("sample", "").strip()
        observations = request.form.get("observations", "").strip()
        responsible = request.form.get("responsible", "").strip()

        data = get_remote_json()
        last = int(data.get("last_number", 0))
        new_number = last + 1
        data["last_number"] = new_number

        ok, resp = update_remote_json(data, message=f"Increment laudo number to {new_number}")
        if not ok:
            flash("Aviso: não foi possível atualizar contador no GitHub: " + str(resp), "warning")

        fixed_text = ("Atestamos para os devidos fins que o processo de Higienização de Caixas Plásticas utilizado pela empresa "
                      "Organizações Salomão Martins Ltda, portadora do CNPJ 59.508.117/0001-23, CREA MG 241837, "
                      "Registro IMA Nº 19.336, localizada à Rod. BR-040, 383 – Galpão 01, Bairro Vila Paris, Contagem, Minas Gerais, "
                      "no CEP 32.150-340; é realizado de acordo com as normas e padrões necessários.")

        rendered = render_template("laudo_template.html",
                                   laudo_number=new_number,
                                   client=client,
                                   sample=sample,
                                   observations=observations,
                                   responsible=responsible,
                                   fixed_text=fixed_text,
                                   date=datetime.date.today().isoformat())

        return Response(rendered, mimetype="text/html")

    return render_template("index.html")

@app.route("/status")
def status():
    data = get_remote_json()
    return {"last_number": data.get("last_number", 0)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

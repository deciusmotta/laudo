from flask import Flask, render_template, request, send_file
import os, io, json, base64, datetime, requests
from weasyprint import HTML
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "replace-me")

@app.template_filter('nl2br')
def nl2br(value):
    """Converte quebras de linha em <br>."""
    return value.replace('\n', '<br>') if value else ''

GITHUB_REPO = os.environ.get("GITHUB_REPO", "deciusmotta/laudo")
GITHUB_FILE = os.environ.get("GITHUB_FILE", "laudos.json")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"

def get_remote_json():
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{GITHUB_FILE}"
    try:
        r = requests.get(raw_url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"ultimo_numero": 0}

def update_remote_json(new_json, message="Atualiza contador de laudos"):
    if not GITHUB_TOKEN:
        return False, "Missing token"
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None
    content_b64 = base64.b64encode(json.dumps(new_json, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": content_b64, "branch": "main"}
    if sha:
        payload["sha"] = sha
    r2 = requests.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload, timeout=10)
    return (r2.status_code in (200,201)), r2.text

def get_next_number():
    data = get_remote_json()
    last = int(data.get("ultimo_numero", 0))
    new = last + 1
    update_remote_json({"ultimo_numero": new}, message=f"Incrementa laudo {new}")
    return new

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        form = request.form.to_dict()
        numero = get_next_number()
        hoje = datetime.date.today()
        validade = hoje + datetime.timedelta(days=15)
        dados = {
            "numero_laudo": numero,
            "data_geracao": hoje.strftime("%d/%m/%Y"),
            "data_validade": validade.strftime("%d/%m/%Y"),
            **form
        }
        buffer = io.BytesIO()
        Code128(str(numero), writer=ImageWriter()).write(buffer, {"module_height": 8.0, "font_size": 0, "text_distance": 0})
        dados["barcode"] = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return render_template("laudo_template.html", dados=dados)
    return render_template("index.html")

@app.route("/pdf", methods=["POST"])
def gerar_pdf():
    dados = request.form.to_dict()
    if "data_geracao" not in dados:
        hoje = datetime.date.today()
        validade = hoje + datetime.timedelta(days=15)
        dados["data_geracao"] = hoje.strftime("%d/%m/%Y")
        dados["data_validade"] = validade.strftime("%d/%m/%Y")
    if "barcode" not in dados or not dados.get("barcode"):
        buffer = io.BytesIO()
        Code128(str(dados.get("numero_laudo","")), writer=ImageWriter()).write(buffer, {"module_height": 8.0, "font_size": 0, "text_distance": 0})
        dados["barcode"] = base64.b64encode(buffer.getvalue()).decode("utf-8")
    html = render_template("laudo_template.html", dados=dados)
    pdf = HTML(string=html).write_pdf()
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name=f"Laudo_{dados.get('numero_laudo','0')}.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))

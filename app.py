from flask import Flask, render_template, request, send_file, redirect, url_for
import io, json, requests, datetime, base64
from weasyprint import HTML
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)

# Configurações do GitHub remoto
GITHUB_REPO = "deciusmotta/laudo"
GITHUB_FILE = "laudos.json"
GITHUB_TOKEN = None  # Defina via variável de ambiente no Render

def get_next_laudo():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = json.loads(base64.b64decode(r.json()["content"]).decode())
        numero = content.get("ultimo_numero", 0) + 1
    else:
        numero = 1
    content = {"ultimo_numero": numero}
    encoded = base64.b64encode(json.dumps(content).encode()).decode()
    data = {"message": f"Atualiza laudo {numero}", "content": encoded, "branch": "main"}
    requests.put(url, headers=headers, json=data)
    return numero

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        dados = request.form.to_dict()
        numero_laudo = get_next_laudo()
        hoje = datetime.date.today()
        validade = hoje + datetime.timedelta(days=15)
        dados.update({
            "numero_laudo": numero_laudo,
            "data_geracao": hoje.strftime("%d/%m/%Y"),
            "data_validade": validade.strftime("%d/%m/%Y"),
        })
        buffer = io.BytesIO()
        barcode = Code128(str(numero_laudo), writer=ImageWriter())
        barcode.save(buffer, {"format": "PNG"})
        dados["barcode"] = base64.b64encode(buffer.getvalue()).decode()
        return render_template("laudo_template.html", dados=dados)
    return render_template("index.html")

@app.route("/pdf", methods=["POST"])
def gerar_pdf():
    dados = request.form.to_dict()
    html = render_template("laudo_template.html", dados=dados)
    pdf = HTML(string=html).write_pdf()
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name="laudo.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

from flask import Flask, render_template, request, send_file
import io, json, requests, datetime, base64, os
from weasyprint import HTML
from barcode import Code128
from barcode.writer import ImageWriter
from datetime import datetime, timedelta

app = Flask(__name__)

GITHUB_REPO = "deciusmotta/laudo"
GITHUB_FILE = "laudos.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

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
    if GITHUB_TOKEN:
        data = {"message": f"Atualiza laudo {numero}", "content": encoded, "branch": "main", "sha": r.json().get("sha") if r.status_code==200 else None}
        requests.put(url, headers=headers, json=data)
    return numero

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        dados = request.form.to_dict()  # captura todos os campos do formulário
        numero_laudo = get_next_laudo()

        # Data de emissão e validade
        data_emissao = datetime.now()
        validade = data_emissao + timedelta(days=15)
        data_emissao_str = data_emissao.strftime('%d/%m/%Y')
        validade_str = validade.strftime('%d/%m/%Y')

        # Atualizar dados do laudo
        dados.update({
            "numero_laudo": numero_laudo,
            "data_geracao": data_emissao_str,
            "data_validade": validade_str
        })
        # Código de barras menor
        buffer = io.BytesIO()
        Code128(str(numero_laudo), writer=ImageWriter()).write(buffer, {"module_height": 8.0, "font_size": 0, "text_distance": 0})
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

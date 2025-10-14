from flask import Flask, render_template, request, send_file
import io, json, requests, base64, os
from weasyprint import HTML
from barcode import Code128
from barcode.writer import ImageWriter
from datetime import datetime, timedelta

app = Flask(__name__)

# Configurações GitHub
GITHUB_REPO = "deciusmotta/laudo"
GITHUB_FILE = "laudos.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Arquivo local para gravar os laudos gerados (caminho absoluto)
LAUDOS_FILE = os.path.join(os.path.dirname(__file__), "laudos_gerados.json")

# Função para obter próximo número de laudo via GitHub
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
        data = {
            "message": f"Atualiza laudo {numero}",
            "content": encoded,
            "branch": "main",
            "sha": r.json().get("sha") if r.status_code==200 else None
        }
        requests.put(url, headers=headers, json=data)
    return numero

# Função para salvar laudo em arquivo JSON local
def salvar_laudo(dados):
    laudo_registro = {
        "numero_laudo": str(dados.get("numero_laudo", "")),
        "data_emissao": dados.get("data_geracao", ""),
        "data_validade": dados.get("data_validade", ""),
        "cpf_cnpj_cliente": dados.get("cpf_cnpj_cliente", ""),
        "nome_cliente": dados.get("nome_cliente", ""),
        "quantidade_caixas": dados.get("quantidade_caixas", ""),
        "modelo_caixas": dados.get("modelo_caixas", "")
    }

    try:
        if os.path.exists(LAUDOS_FILE):
            with open(LAUDOS_FILE, "r", encoding="utf-8") as f:
                todos_laudos = json.load(f)
        else:
            todos_laudos = []

        todos_laudos.append(laudo_registro)

        with open(LAUDOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos_laudos, f, ensure_ascii=False, indent=4)

        print(f"Laudo {laudo_registro['numero_laudo']} salvo com sucesso!")

    except Exception as e:
        print(f"Erro ao salvar laudo: {e}")

# Rota principal - formulário e geração do laudo HTML
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        dados = request.form.to_dict()
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

        # Gerar código de barras
        buffer = io.BytesIO()
        Code128(
            str(numero_laudo),
            writer=ImageWriter()
        ).write(buffer, {"module_height": 8.0, "font_size": 0, "text_distance": 0})
        buffer.seek(0)
        dados["barcode"] = base64.b64encode(buffer.getvalue()).decode()

        # Salvar no JSON local
        salvar_laudo(dados)

        return render_template("laudo_template.html", dados=dados)

    return render_template("index.html")

# Rota para gerar PDF
@app.route("/pdf", methods=["POST"])
def gerar_pdf():
    dados = request.form.to_dict()
    html = render_template("laudo_template.html", dados=dados)
    pdf = HTML(string=html).write_pdf()
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name="laudo.pdf")

# Rota para consultar todos os laudos gerados
@app.route("/api/laudos", methods=["GET"])
def listar_laudos():
    if os.path.exists(LAUDOS_FILE):
        with open(LAUDOS_FILE, "r", encoding="utf-8") as f:
            todos_laudos = json.load(f)
    else:
        todos_laudos = []

    return {"laudos": todos_laudos}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

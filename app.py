from flask import Flask, render_template, request, send_file
from zeep import Client
from datetime import datetime
from weasyprint import HTML
import io

app = Flask(__name__)

SOAP_URL = "https://laudoservice.onrender.com/soap?wsdl"

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        data_emissao = request.form["data_emissao"]
        cpf_cnpj = request.form["cpf_cnpj"]
        nome_cliente = request.form["nome_cliente"]
        qtd_caixas = request.form["qtd_caixas"]
        modelo_caixas = request.form["modelo_caixas"]

        client = Client(SOAP_URL)
        data_emissao_dt = datetime.strptime(data_emissao, "%Y-%m-%d").date()
        response = client.service.gerar_laudo(data_emissao_dt)

        html = render_template(
            "laudo.html",
            numero_laudo=response.numero_laudo,
            data_emissao=response.data_emissao,
            data_validade=response.data_validade,
            cpf_cnpj=cpf_cnpj,
            nome_cliente=nome_cliente,
            qtd_caixas=qtd_caixas,
            modelo_caixas=modelo_caixas,
        )

        pdf = io.BytesIO()
        HTML(string=html).write_pdf(pdf)
        pdf.seek(0)
        return send_file(pdf, download_name=f"Laudo_{response.numero_laudo}.pdf", as_attachment=True)

    return render_template("form.html")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

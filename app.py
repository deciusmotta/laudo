from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer, Date, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from io import BytesIO
import logging
import os
from datetime import timedelta

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- Arquivo para armazenar o último número de laudo ---
ULTIMO_LAUDO_FILE = "ultimo_laudo.txt"

def get_next_laudo_number():
    """Gera número sequencial do laudo"""
    if not os.path.exists(ULTIMO_LAUDO_FILE):
        with open(ULTIMO_LAUDO_FILE, "w") as f:
            f.write("0")

    with open(ULTIMO_LAUDO_FILE, "r") as f:
        last = int(f.read().strip() or "0")

    next_num = last + 1

    with open(ULTIMO_LAUDO_FILE, "w") as f:
        f.write(str(next_num))

    return next_num


# --- Modelo de resposta ---
class LaudoResponse(ComplexModel):
    numero_laudo = Unicode
    data_emissao = Date
    data_validade = Date
    cpf_cnpj_cliente = Unicode
    nome_cliente = Unicode
    quantidade_caixas = Integer
    modelo_caixas = Unicode


# --- Serviço SOAP ---
class LaudoService(ServiceBase):
    @rpc(Date, _returns=LaudoResponse)
    def gerar_laudo(ctx, data_emissao):
        """
        Gera um laudo com base na Data de Emissão informada no Request.
        A Data de Validade será automaticamente 15 dias após a emissão.
        """
        numero = get_next_laudo_number()
        numero_formatado = f"017{numero:06d}"

        # Calcula validade
        data_validade = data_emissao + timedelta(days=15)

        # Exemplo de dados fixos
        cpf_cnpj_cliente = "59.508.117/0001-23"
        nome_cliente = "Organizações Salomão Martins Ltda"
        quantidade_caixas = 50
        modelo_caixas = "Modelo X"

        return LaudoResponse(
            numero_laudo=numero_formatado,
            data_emissao=data_emissao,
            data_validade=data_validade,
            cpf_cnpj_cliente=cpf_cnpj_cliente,
            nome_cliente=nome_cliente,
            quantidade_caixas=quantidade_caixas,
            modelo_caixas=modelo_caixas
        )


# --- Configuração SOAP ---
soap_app = Application(
    [LaudoService],
    tns='http://laudoservice.onrender.com/soap',
    name='LaudoService',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(soap_app)


# --- Endpoint SOAP ---
@app.route("/soap", methods=['GET', 'POST'])
def soap_server():
    buf = BytesIO()

    def start_response(status, headers):
        buf.status = status
        buf.headers = headers
        return buf.write

    result = wsgi_app(request.environ, start_response)
    response_data = b"".join(result)
    return Response(response_data, mimetype="text/xml; charset=utf-8")


# --- Endpoint WSDL ---
@app.route("/soap?wsdl", methods=["GET"])
def wsdl():
    wsdl_content = soap_app.get_interface_document('wsdl')
    return Response(wsdl_content, mimetype='text/xml')


# --- Página inicial ---
@app.route("/")
def home():
    return "LaudoService SOAP ativo em /soap e WSDL em /soap?wsdl"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

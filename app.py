# --- PATCH DE COMPATIBILIDADE ---
# Spyne depende do módulo cgi, que foi removido no Python 3.13.
# Este patch cria um módulo cgi falso com a função parse_header.
import sys, types
if 'cgi' not in sys.modules:
    sys.modules['cgi'] = types.ModuleType('cgi')
    sys.modules['cgi'].parse_header = lambda x: ('', {})

# --- IMPORTS NORMAIS ---
from flask import Flask, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer, Date, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from io import BytesIO
from datetime import date, timedelta
import logging, os

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

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


# --- Modelo de retorno ---
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
        """Gera um laudo a partir da data de emissão"""
        numero = get_next_laudo_number()
        numero_formatado = f"017{numero:06d}"
        data_validade = data_emissao + timedelta(days=15)

        return LaudoResponse(
            numero_laudo=numero_formatado,
            data_emissao=data_emissao,
            data_validade=data_validade,
            cpf_cnpj_cliente="59.508.117/0001-23",
            nome_cliente="Organizações Salomão Martins Ltda",
            quantidade_caixas=50,
            modelo_caixas="Modelo X"
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
    return """
    <h2>LaudoService SOAP ativo</h2>
    <p>WSDL disponível em: <a href="/soap?wsdl">/soap?wsdl</a></p>
    <p>Endpoint SOAP: /soap (POST)</p>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

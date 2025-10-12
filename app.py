from flask import Flask, render_template, request, Response, send_file
from lxml import etree
from datetime import date, timedelta
import io
import os
from weasyprint import HTML

app = Flask(__name__)

ULTIMO_LAUDO_FILE = "ultimo_laudo.txt"

# -----------------------
# Funções auxiliares
# -----------------------
def get_next_laudo_number():
    if not os.path.exists(ULTIMO_LAUDO_FILE):
        with open(ULTIMO_LAUDO_FILE, "w") as f:
            f.write("0")
    with open(ULTIMO_LAUDO_FILE, "r") as f:
        last = int(f.read().strip() or "0")
    next_num = last + 1
    with open(ULTIMO_LAUDO_FILE, "w") as f:
        f.write(str(next_num))
    return next_num

def gerar_laudo_soap(data_emissao_str):
    data_emissao = date.fromisoformat(data_emissao_str)
    numero = get_next_laudo_number()
    numero_formatado = f"017{numero:06d}"
    data_validade = data_emissao + timedelta(days=15)

    # Dados fixos
    cpf_cnpj_cliente = "59.508.117/0001-23"
    nome_cliente = "Organizações Salomão Martins Ltda"
    quantidade_caixas = 50
    modelo_caixas = "Modelo X"

    # Monta XML SOAP
    NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
    NS_TNS = "http://laudoservice.onrender.com/soap"

    Envelope = etree.Element("{%s}Envelope" % NS_SOAP, nsmap={"soap": NS_SOAP, "tns": NS_TNS})
    Body = etree.SubElement(Envelope, "{%s}Body" % NS_SOAP)
    ResponseEl = etree.SubElement(Body, "{%s}gerar_laudoResponse" % NS_TNS)

    etree.SubElement(ResponseEl, "{%s}numero_laudo" % NS_TNS).text = numero_formatado
    etree.SubElement(ResponseEl, "{%s}data_emissao" % NS_TNS).text = data_emissao.isoformat()
    etree.SubElement(ResponseEl, "{%s}data_validade" % NS_TNS).text = data_validade.isoformat()
    etree.SubElement(ResponseEl, "{%s}cpf_cnpj_cliente" % NS_TNS).text = cpf_cnpj_cliente
    etree.SubElement(ResponseEl, "{%s}nome_cliente" % NS_TNS).text = nome_cliente
    etree.SubElement(ResponseEl, "{%s}quantidade_caixas" % NS_TNS).text = str(quantidade_caixas)
    etree.SubElement(ResponseEl, "{%s}modelo_caixas" % NS_TNS).text = modelo_caixas

    return etree.tostring(Envelope, xml_declaration=True, encoding="utf-8")

# -----------------------
# Rotas SOAP
# -----------------------
@app.route("/soap", methods=["POST"])
def soap_endpoint():
    xml_data = request.data
    tree = etree.fromstring(xml_data)
    ns = {"soap": "http://schemas.xmlsoap.org/soap/envelope/"}
    body = tree.find("soap:Body", ns)

    data_emissao_el = body.find(".//data_emissao")
    if data_emissao_el is None:
        return Response("Missing data_emissao", status=400)
    data_emissao_str = data_emissao_el.text

    response_xml = gerar_laudo_soap(data_emissao_str)
    return Response(response_xml, mimetype="text/xml; charset=utf-8")

@app.route("/soap?wsdl", methods=["GET"])
def wsdl():
    wsdl_content = f"""<?xml version="1.0"?>
<definitions name="LaudoService"
  targetNamespace="http://laudoservice.onrender.com/soap"
  xmlns:tns="http://laudoservice.onrender.com/soap"
  xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
  xmlns:xsd="http://www.w3.org/2001/XMLSchema"
  xmlns="http://schemas.xmlsoap.org/wsdl/">
  <types>
    <xsd:schema targetNamespace="http://laudoservice.onrender.com/soap">
      <xsd:element name="gerar_laudo">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="data_emissao" type="xsd:date"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="gerar_laudoResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="numero_laudo" type="xsd:string"/>
            <xsd:element name="data_emissao" type="xsd:date"/>
            <xsd:element name="data_validade" type="xsd:date"/>
            <xsd:element name="cpf_cnpj_cliente" type="xsd:string"/>
            <xsd:element name="nome_cliente" type="xsd:string"/>
            <xsd:element name="quantidade_caixas" type="xsd:int"/>
            <xsd:element name="modelo_caixas" type="xsd:string"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
  </types>
  <message name="gerar_laudoRequest">
    <part name="parameters" element="tns:gerar_laudo"/>
  </message>
  <message name="gerar_laudoResponse">
    <part name="parameters" element="tns:gerar_laudoResponse"/>
  </message>
  <portType name="LaudoServicePortType">
    <operation name="gerar_laudo">
      <input message="tns:gerar_laudoRequest"/>
      <output message="tns:gerar_laudoResponse"/>
    </operation>
  </portType>
  <binding name="LaudoServiceBinding" type="tns:LaudoServicePortType">
    <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="gerar_laudo">
      <soap:operation soapAction="gerar_laudo"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
  </binding>
  <service name="LaudoService">
    <port name="LaudoServicePort" binding="tns:LaudoServiceBinding">
      <soap:address location="https://laudoservice.onrender.com/soap"/>
    </port>
  </service>
</definitions>"""
    return Response(wsdl_content, mimetype="text/xml")

# -----------------------
# Frontend Web
# -----------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        data_emissao = request.form["data_emissao"]
        cpf_cnpj = request.form["cpf_cnpj"]
        nome_cliente = request.form["nome_cliente"]
        qtd_caixas = request.form["qtd_caixas"]
        modelo_caixas = request.form["modelo_caixas"]

        # Gera SOAP e extrai informações
        response_xml = gerar_laudo_soap(data_emissao)
        tree = etree.fromstring(response_xml)
        tns = "http://laudoservice.onrender.com/soap"
        numero_laudo = tree.find(f".//{{{tns}}}numero_laudo").text
        data_validade = tree.find(f".//{{{tns}}}data_validade").text

        # Renderiza o laudo em HTML na tela
        return render_template(
            "laudo.html",
            numero_laudo=numero_laudo,
            data_emissao=data_emissao,
            data_validade=data_validade,
            cpf_cnpj=cpf_cnpj,
            nome_cliente=nome_cliente,
            qtd_caixas=qtd_caixas,
            modelo_caixas=modelo_caixas,
        )

    return render_template("form.html")


# -----------------------
# Rota para gerar PDF
# -----------------------
@app.route("/baixar_pdf", methods=["POST"])
def baixar_pdf():
    """Gera um PDF do laudo atual e faz o download."""
    data = request.form

    html_content = render_template(
        "laudo.html",
        numero_laudo=data["numero_laudo"],
        data_emissao=data["data_emissao"],
        data_validade=data["data_validade"],
        cpf_cnpj=data["cpf_cnpj"],
        nome_cliente=data["nome_cliente"],
        qtd_caixas=data["qtd_caixas"],
        modelo_caixas=data["modelo_caixas"],
    )

    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)

    nome_arquivo = f"Laudo_{data['numero_laudo']}.pdf"
    return send_file(pdf_file, download_name=nome_arquivo, as_attachment=True)


# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

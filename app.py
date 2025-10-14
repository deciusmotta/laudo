from flask import Flask, render_template, request, send_file
from datetime import datetime
import io
from weasyprint import HTML
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.form.to_dict()
        numero_laudo = 123  # Simulação
        html = render_template('laudo.html', data=data, numero_laudo=numero_laudo, data_hoje=datetime.now().strftime("%d/%m/%Y"))
        pdf_file = io.BytesIO()
        HTML(string=html).write_pdf(pdf_file)
        pdf_file.seek(0)
        return send_file(pdf_file, as_attachment=True, download_name=f"Laudo_{numero_laudo}.pdf", mimetype='application/pdf')
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)

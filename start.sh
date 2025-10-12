#!/bin/bash
echo "Instalando dependências (sem build de wheel)..."
pip install --no-build-isolation --prefer-binary -r requirements.txt

echo "Iniciando aplicação Flask..."
python app.py

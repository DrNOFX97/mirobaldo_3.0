#!/bin/bash

# Mirobaldo 3.0 - Script de Lançamento
# Autor: F. Nuno
# Descrição: Inicia a aplicação Mirobaldo 3.0

echo "🦁 Iniciando Mirobaldo 3.0 - Chatbot do SC Farense"
echo "=================================================="
echo ""

# Ir para o diretório do projeto
cd "$(dirname "$0")"

# Verificar se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Verificar se as dependências estão instaladas
if ! python -c "import flask" 2>/dev/null; then
    echo "📦 Instalando dependências..."
    pip install -q flask requests beautifulsoup4 lxml python-dotenv
fi

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "📝 Crie um arquivo .env com as configurações necessárias"
    echo "   Copie .env.example se disponível"
fi

# Criar pasta de logs se não existir
mkdir -p logs

echo ""
echo "✅ Configuração completa!"
echo ""
echo "🚀 Iniciando aplicação Flask..."
echo "📍 URL: http://localhost:5000"
echo "⏹️  Para parar: CTRL+C"
echo ""
echo "=================================================="
echo ""

# Iniciar aplicação Flask
cd backend
export FLASK_APP=app.py
export FLASK_ENV=development
python app.py

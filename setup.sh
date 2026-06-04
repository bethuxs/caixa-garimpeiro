#!/bin/bash
# ============================================================================
# Setup Script - Garimpeiro de Imóveis
# ============================================================================
# Script para facilitar a instalação inicial do projeto
# Uso: bash setup.sh
# ============================================================================

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                  Garimpeiro de Imóveis - Setup Inicial                        ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para imprimir com cor
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Verificar Python
echo "Verificando dependências do sistema..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 não encontrado. Instale Python 3.9+ primeiro."
    exit 1
fi
print_status "Python3 encontrado: $(python3 --version)"

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 não encontrado."
    exit 1
fi
print_status "pip3 encontrado"

echo ""

# Criar ambiente virtual
if [ -d "venv" ]; then
    print_warning "Ambiente virtual já existe. Pulando criação..."
else
    echo "Criando ambiente virtual..."
    python3 -m venv venv
    print_status "Ambiente virtual criado"
fi

echo ""

# Ativar ambiente virtual
echo "Ativando ambiente virtual..."
source venv/bin/activate
print_status "Ambiente virtual ativado"

echo ""

# Atualizar pip
echo "Atualizando pip..."
pip install --upgrade pip > /dev/null 2>&1
print_status "pip atualizado"

echo ""

# Instalar dependências
echo "Instalando dependências Python..."
pip install -r requirements.txt > /dev/null 2>&1
print_status "Dependências instaladas"

echo ""

# Instalar Playwright browsers
echo "Instalando Playwright browsers (Chromium)..."
playwright install chromium > /dev/null 2>&1
print_status "Playwright browsers instalados"

echo ""

# Criar arquivo .env se não existir
if [ -f ".env" ]; then
    print_warning "Arquivo .env já existe"
else
    echo "Criando arquivo .env a partir do template..."
    cp .env.example .env
    print_status "Arquivo .env criado"
    print_warning "IMPORTANTE: Edite o arquivo .env com suas credenciais do Telegram!"
fi

echo ""

# Criar arquivo database.db se não existir
if [ -f "database.db" ]; then
    print_warning "Banco de dados já existe"
else
    echo "Criando banco de dados..."
    python3 -c "from scraper import Database; Database('database.db')"
    print_status "Banco de dados inicializado"
fi

echo ""

# Criar arquivo de log
if [ -f "scraper.log" ]; then
    print_warning "Arquivo de log já existe"
else
    touch scraper.log
    print_status "Arquivo de log criado"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                      Setup concluído com sucesso!                             ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Próximos passos:"
echo "1. Edite o arquivo .env com suas credenciais do Telegram:"
echo "   nano .env"
echo ""
echo "2. (Opcional) Customize o arquivo config.yaml conforme necessário"
echo ""
echo "3. Teste a execução:"
echo "   python scraper.py"
echo ""
echo "4. Configure execução periódica (cron, systemd timer, etc.)"
echo ""
echo "Para desativar o ambiente virtual depois, execute: deactivate"
echo ""

#!/bin/bash
# ============================================================================
# DEPLOY SCRIPT - Garimpeiro de Imóveis
# Executar como usuário: caixa@financiero.com.br
# ============================================================================
# Este script faz o deploy completo do projeto no VPS
# Uso: bash deploy.sh
# ============================================================================

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║           Deploy - Garimpeiro de Imóveis no VPS                               ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[→]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# ============================================================================
# 1. Verificar ambiente
# ============================================================================
print_step "Verificando ambiente..."

if ! command -v python3 &> /dev/null; then
    print_error "Python3 não encontrado!"
    exit 1
fi
print_status "Python3: $(python3 --version)"

if ! command -v git &> /dev/null; then
    print_error "Git não encontrado!"
    exit 1
fi
print_status "Git: $(git --version)"

if ! command -v pip3 &> /dev/null; then
    print_error "pip3 não encontrado!"
    exit 1
fi
print_status "pip3: $(pip3 --version)"

echo ""

# ============================================================================
# 2. Criar diretórios
# ============================================================================
print_step "Criando estrutura de diretórios..."

PROJECT_DIR="/home/caixa/projetos/caixa-garimpeiro"
mkdir -p /home/caixa/projetos
print_status "Diretório criado: /home/caixa/projetos"

echo ""

# ============================================================================
# 3. Clonar repositório
# ============================================================================
print_step "Clonando repositório GitHub..."

if [ -d "$PROJECT_DIR" ]; then
    print_warning "Diretório já existe. Atualizando..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    cd /home/caixa/projetos
    git clone git@github.com:bethuxs/caixa-garimpeiro.git
    cd "$PROJECT_DIR"
fi
print_status "Repositório clonado/atualizado"

echo ""

# ============================================================================
# 4. Criar ambiente virtual
# ============================================================================
print_step "Criando ambiente virtual Python..."

if [ -d "venv" ]; then
    print_warning "Ambiente virtual já existe"
else
    python3 -m venv venv
    print_status "Ambiente virtual criado"
fi

source venv/bin/activate
print_status "Ambiente virtual ativado"

echo ""

# ============================================================================
# 5. Instalar dependências
# ============================================================================
print_step "Instalando dependências Python..."

pip install --upgrade pip setuptools wheel > /dev/null 2>&1
print_status "pip, setuptools, wheel atualizados"

pip install -r requirements.txt > /dev/null 2>&1
print_status "Dependências do requirements.txt instaladas"

echo ""

# ============================================================================
# 6. Instalar Playwright
# ============================================================================
print_step "Instalando Playwright e navegadores..."

python -m playwright install chromium > /dev/null 2>&1
print_status "Playwright Chromium instalado"

echo ""

# ============================================================================
# 7. Criar arquivo .env
# ============================================================================
print_step "Configurando arquivo .env..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    print_status "Arquivo .env criado de .env.example"
    print_warning "IMPORTANTE: Edite /home/caixa/projetos/caixa-garimpeiro/.env"
    print_warning "Adicione: TELEGRAM_TOKEN e TELEGRAM_CHAT_ID"
else
    print_warning "Arquivo .env já existe (não sobrescrito)"
fi

echo ""

# ============================================================================
# 8. Testar instalação
# ============================================================================
print_step "Testando instalação..."

python -c "import playwright; print(f'  Playwright: OK')" 2>/dev/null || print_warning "Playwright: falha na importação"
python -c "import yaml; print(f'  PyYAML: OK')" 2>/dev/null || print_warning "PyYAML: falha na importação"
python -c "import requests; print(f'  Requests: OK')" 2>/dev/null || print_warning "Requests: falha na importação"
python -c "import dotenv; print(f'  python-dotenv: OK')" 2>/dev/null || print_warning "python-dotenv: falha na importação"

echo ""

# ============================================================================
# 9. Criar diretórios de logs
# ============================================================================
print_step "Criando diretórios de logs..."

mkdir -p /home/caixa/projetos/caixa-garimpeiro/logs
print_status "Diretório de logs criado"

echo ""

# ============================================================================
# 10. Resumo e próximos passos
# ============================================================================
echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                      Deploy Concluído com Sucesso!                            ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Localização: $PROJECT_DIR"
echo ""
echo "🔧 Próximos Passos:"
echo ""
echo "1. Editar configurações:"
echo "   ${BLUE}nano /home/caixa/projetos/caixa-garimpeiro/.env${NC}"
echo "   Adicione:"
echo "     TELEGRAM_TOKEN=seu_token_aqui"
echo "     TELEGRAM_CHAT_ID=seu_chat_id"
echo ""
echo "2. Editar filtros (opcional):"
echo "   ${BLUE}nano /home/caixa/projetos/caixa-garimpeiro/config.yaml${NC}"
echo ""
echo "3. Testar uma vez:"
echo "   ${BLUE}cd $PROJECT_DIR${NC}"
echo "   ${BLUE}source venv/bin/activate${NC}"
echo "   ${BLUE}python scraper.py${NC}"
echo ""
echo "4. Configurar execução periódica (systemd timer):"
echo "   ${BLUE}sudo nano /etc/systemd/system/caixa-scraper.service${NC}"
echo "   (Ver arquivo cron-and-systemd-examples.txt)"
echo ""
echo "5. Ativar timer:"
echo "   ${BLUE}sudo systemctl daemon-reload${NC}"
echo "   ${BLUE}sudo systemctl enable --now caixa-scraper.timer${NC}"
echo "   ${BLUE}sudo systemctl status caixa-scraper.timer${NC}"
echo ""
echo "📊 Ver logs:"
echo "   ${BLUE}tail -f /home/caixa/projetos/caixa-garimpeiro/scraper.log${NC}"
echo ""
echo "🔗 Repositório: https://github.com/bethuxs/caixa-garimpeiro"
echo ""

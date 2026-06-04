#!/bin/bash
# ============================================================================
# SCRIPT DE DEPLOYMENT AUTOMATIZADO
# Executa: SSH root -> su caixa -> deploy completo
# ============================================================================

# Configurações
VPS_HOST="root@financiero.com.br"
VPS_USER="caixa"

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║     Deployment Automático - Garimpeiro de Imóveis no VPS                       ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Script a executar no VPS
DEPLOY_SCRIPT='
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║           Iniciando Deploy do Garimpeiro de Imóveis                           ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Cores
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[1;33m"
NC="\033[0m"

print_step() {
    echo -e "${BLUE}[→]${NC} $1"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# ============================================================================
# 1. Verificar ambiente
# ============================================================================
print_step "Verificando ambiente..."
python3 --version > /dev/null 2>&1 && print_status "Python3 encontrado" || (echo "Python3 não encontrado"; exit 1)
git --version > /dev/null 2>&1 && print_status "Git encontrado" || (echo "Git não encontrado"; exit 1)
pip3 --version > /dev/null 2>&1 && print_status "pip3 encontrado" || (echo "pip3 não encontrado"; exit 1)
echo ""

# ============================================================================
# 2. Criar diretórios
# ============================================================================
print_step "Criando estrutura de diretórios..."
mkdir -p /home/caixa/projetos
mkdir -p /home/caixa/projetos/logs
print_status "Diretórios criados"
echo ""

# ============================================================================
# 3. Clonar ou atualizar repositório
# ============================================================================
PROJECT_DIR="/home/caixa/projetos/caixa-garimpeiro"

print_step "Processando repositório Git..."
if [ -d "$PROJECT_DIR" ]; then
    print_status "Repositório já existe. Atualizando..."
    cd "$PROJECT_DIR"
    git pull origin main 2>&1 | tail -5
else
    print_status "Clonando repositório..."
    cd /home/caixa/projetos
    git clone git@github.com:bethuxs/caixa-garimpeiro.git
    cd "$PROJECT_DIR"
fi
print_status "Repositório pronto"
echo ""

# ============================================================================
# 4. Criar ambiente virtual
# ============================================================================
print_step "Criando ambiente virtual Python..."
if [ -d "venv" ]; then
    print_status "Ambiente virtual já existe"
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
    print_status "Arquivo .env criado"
    echo -e "${YELLOW}[!] PRÓXIMO PASSO: Edite o arquivo .env com suas credenciais!${NC}"
    echo -e "${YELLOW}    nano /home/caixa/projetos/caixa-garimpeiro/.env${NC}"
else
    print_status "Arquivo .env já existe"
fi
echo ""

# ============================================================================
# 8. Testar instalação
# ============================================================================
print_step "Testando importações..."
python -c "import playwright; print(\"  ✓ Playwright\");" 2>/dev/null || echo "  ✗ Playwright"
python -c "import yaml; print(\"  ✓ PyYAML\");" 2>/dev/null || echo "  ✗ PyYAML"
python -c "import requests; print(\"  ✓ Requests\");" 2>/dev/null || echo "  ✗ Requests"
python -c "import dotenv; print(\"  ✓ python-dotenv\");" 2>/dev/null || echo "  ✗ python-dotenv"
echo ""

# ============================================================================
# 9. Criar diretórios de logs
# ============================================================================
print_step "Criando diretórios de logs..."
mkdir -p /home/caixa/projetos/caixa-garimpeiro/logs
print_status "Diretório de logs criado"
echo ""

# ============================================================================
# 10. Resumo
# ============================================================================
echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                      Deploy Concluído com Sucesso!                            ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Localização: /home/caixa/projetos/caixa-garimpeiro"
echo ""
echo "🔧 Próximos Passos:"
echo ""
echo "1. Editar arquivo .env com credenciais do Telegram:"
echo "   nano /home/caixa/projetos/caixa-garimpeiro/.env"
echo ""
echo "2. Testar uma execução:"
echo "   cd /home/caixa/projetos/caixa-garimpeiro"
echo "   source venv/bin/activate"
echo "   python scraper.py"
echo ""
echo "3. Configurar execução periódica (como root):"
echo "   exit  # Voltar para root"
echo "   sudo nano /etc/systemd/system/caixa-scraper.service"
echo ""
echo "📊 Ver logs:"
echo "   tail -f /home/caixa/projetos/caixa-garimpeiro/scraper.log"
echo ""
'

# Executar script no VPS como root, depois su para caixa
echo "🔐 Conectando ao VPS como root..."
echo ""

ssh "$VPS_HOST" bash -s <<'EOF'
# Executar como root primeiro
echo "=== Executando como ROOT ==="
echo ""

# Verificar se usuário caixa existe
if id caixa &>/dev/null; then
    echo "✓ Usuário 'caixa' já existe"
else
    echo "✓ Criando usuário 'caixa'..."
    useradd -m -s /bin/bash caixa
    usermod -aG sudo caixa
fi

# Mudar para usuário caixa e executar script
echo ""
echo "=== Executando como CAIXA ==="
echo ""

su - caixa << 'CAIXA_SCRIPT'
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║           Iniciando Deploy do Garimpeiro de Imóveis                           ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Cores
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[1;33m"
NC="\033[0m"

print_step() {
    echo -e "${BLUE}[→]${NC} $1"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# 1. Verificar ambiente
print_step "Verificando ambiente..."
python3 --version && print_status "Python3 encontrado" || (echo "Python3 não encontrado"; exit 1)
git --version > /dev/null 2>&1 && print_status "Git encontrado" || (echo "Git não encontrado"; exit 1)
pip3 --version > /dev/null 2>&1 && print_status "pip3 encontrado" || (echo "pip3 não encontrado"; exit 1)
echo ""

# 2. Criar diretórios
print_step "Criando estrutura de diretórios..."
mkdir -p /home/caixa/projetos
mkdir -p /home/caixa/projetos/logs
print_status "Diretórios criados"
echo ""

# 3. Processar repositório
PROJECT_DIR="/home/caixa/projetos/caixa-garimpeiro"
print_step "Processando repositório Git..."

if [ -d "$PROJECT_DIR" ]; then
    print_status "Repositório já existe. Atualizando..."
    cd "$PROJECT_DIR"
    git pull origin main 2>&1 | tail -3
else
    print_status "Clonando repositório..."
    cd /home/caixa/projetos
    git clone https://github.com/bethuxs/caixa-garimpeiro.git
    cd "$PROJECT_DIR"
fi
print_status "Repositório pronto"
echo ""

# 4. Ambiente virtual
print_step "Criando ambiente virtual Python..."
if [ -d "venv" ]; then
    print_status "Ambiente virtual já existe"
else
    python3 -m venv venv
    print_status "Ambiente virtual criado"
fi
source venv/bin/activate
print_status "Ambiente virtual ativado"
echo ""

# 5. Dependências Python
print_step "Instalando dependências Python..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
print_status "pip, setuptools, wheel atualizados"
pip install -r requirements.txt > /dev/null 2>&1
print_status "Dependências instaladas"
echo ""

# 6. Playwright
print_step "Instalando Playwright e navegadores..."
python -m playwright install chromium > /dev/null 2>&1
print_status "Playwright Chromium instalado"
echo ""

# 7. Configurar .env
print_step "Configurando arquivo .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_status "Arquivo .env criado"
else
    print_status "Arquivo .env já existe"
fi
echo ""

# 8. Testar importações
print_step "Testando importações..."
python -c "import playwright; print('  ✓ Playwright');" 2>/dev/null
python -c "import yaml; print('  ✓ PyYAML');" 2>/dev/null
python -c "import requests; print('  ✓ Requests');" 2>/dev/null
python -c "import dotenv; print('  ✓ python-dotenv');" 2>/dev/null
echo ""

# 9. Diretório de logs
print_step "Criando diretórios de logs..."
mkdir -p /home/caixa/projetos/caixa-garimpeiro/logs
print_status "Diretório de logs criado"
echo ""

# 10. Resumo final
echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                      Deploy Concluído com Sucesso!                            ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Localização: /home/caixa/projetos/caixa-garimpeiro"
echo ""
echo "🔧 Próximos Passos:"
echo ""
echo "1. Editar arquivo .env com credenciais do Telegram:"
echo "   ${YELLOW}nano /home/caixa/projetos/caixa-garimpeiro/.env${NC}"
echo ""
echo "2. Teste rápido de conexão Telegram:"
echo "   ${YELLOW}cd /home/caixa/projetos/caixa-garimpeiro${NC}"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo "   ${YELLOW}python debug.py test-telegram${NC}"
echo ""
echo "3. Testar uma execução completa:"
echo "   ${YELLOW}python scraper.py${NC}"
echo ""
echo "4. Configurar execução periódica (volte para root):"
echo "   ${YELLOW}exit${NC}"
echo "   ${YELLOW}sudo nano /etc/systemd/system/caixa-scraper.service${NC}"
echo "   (Ver instruções em DEPLOYMENT.md)"
echo ""
echo "📊 Ver logs:"
echo "   ${YELLOW}tail -f /home/caixa/projetos/caixa-garimpeiro/scraper.log${NC}"
echo ""
echo "📚 Documentação completa: DEPLOYMENT.md"
echo ""

CAIXA_SCRIPT

EOF

echo ""
echo "✅ Deploy finalizado!"
echo ""
echo "Próximos passos:"
echo "1. SSH no VPS: ssh caixa@financiero.com.br"
echo "2. Editar .env: nano /home/caixa/projetos/caixa-garimpeiro/.env"
echo "3. Testar: python /home/caixa/projetos/caixa-garimpeiro/scraper.py"

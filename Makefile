# ============================================================================
# Makefile - Garimpeiro de Imóveis
# ============================================================================
# Facilita comandos comuns do projeto
# Uso: make <target>
# ============================================================================

.PHONY: help setup install run test lint clean logs test-telegram

# Variáveis
PYTHON := python3
VENV := venv
VENV_PYTHON := $(VENV)/bin/python3
VENV_PIP := $(VENV)/bin/pip3

help:
	@echo "╔════════════════════════════════════════════════════════════════════════╗"
	@echo "║                 Garimpeiro de Imóveis - Comandos Disponíveis           ║"
	@echo "╚════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Instalação e Setup:"
	@echo "  make setup              - Setup completo do projeto (cria venv, instala deps)"
	@echo "  make install            - Instala dependências no venv ativo"
	@echo "  make clean              - Remove arquivos gerados e cache"
	@echo ""
	@echo "Execução:"
	@echo "  make run                - Executa o scraper uma vez"
	@echo "  make run-debug          - Executa com modo DEBUG ativado"
	@echo ""
	@echo "Desenvolvimento:"
	@echo "  make lint               - Verifica PEP 8 (pylint/flake8)"
	@echo "  make format             - Formata código com black"
	@echo "  make logs               - Mostra últimas linhas do log"
	@echo "  make logs-follow        - Segue arquivo de log em tempo real (tail -f)"
	@echo ""
	@echo "Testes:"
	@echo "  make test-telegram      - Testa conexão com Telegram Bot"
	@echo "  make test-db            - Testa conexão com banco de dados"
	@echo "  make test-scraper       - Testa scraper (sem Telegram)"
	@echo ""
	@echo "Utilitários:"
	@echo "  make stats              - Mostra estatísticas do banco de dados"
	@echo "  make backup-db          - Faz backup do banco de dados"
	@echo "  make reset-db           - Remove banco de dados (CUIDADO!)"
	@echo ""

setup: venv
	bash setup.sh

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip

install:
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PYTHON) -m playwright install chromium

run:
	$(VENV_PYTHON) scraper.py

run-debug:
	DEBUG=true $(VENV_PYTHON) scraper.py

lint:
	@echo "Verificando estilo de código (PEP 8)..."
	@$(VENV_PYTHON) -m py_compile scraper.py
	@echo "✓ Sintaxe Python válida"

format:
	@echo "Formatando código com black..."
	@command -v black >/dev/null 2>&1 || $(VENV_PIP) install black
	@$(VENV_PYTHON) -m black scraper.py
	@echo "✓ Formatação concluída"

logs:
	@tail -n 50 scraper.log

logs-follow:
	@tail -f scraper.log

test-telegram:
	@echo "Testando conexão com Telegram..."
	@if [ -f .env ]; then \
		. .env; \
		$(VENV_PYTHON) -c "from scraper import TelegramNotifier; TelegramNotifier('$$TELEGRAM_TOKEN', '$$TELEGRAM_CHAT_ID').enviar_teste()"; \
	else \
		echo "❌ Arquivo .env não encontrado"; \
		exit 1; \
	fi

test-db:
	@echo "Testando banco de dados..."
	@$(VENV_PYTHON) -c "from scraper import Database; db = Database(); stats = db.obter_estatisticas(); print(f'Total de imóveis: {stats.get(\"total_imoveis\", 0)}'); print('✓ Banco de dados OK')"

test-scraper:
	@echo "Executando scraper em modo teste (sem Telegram)..."
	@DEBUG=true $(VENV_PYTHON) scraper.py

stats:
	@echo "Estatísticas do Banco de Dados:"
	@$(VENV_PYTHON) -c "\
		from scraper import Database; \
		db = Database(); \
		stats = db.obter_estatisticas(); \
		print(f'Total de imóveis: {stats.get(\"total_imoveis\", 0)}'); \
		print(f'Preço médio: R\$ {stats.get(\"preco_medio\", 0):,.2f}'); \
		print('Imóveis por bairro:'); \
		for bairro, total in sorted(stats.get('por_bairro', {}).items(), key=lambda x: x[1], reverse=True)[:10]: \
		    print(f'  - {bairro}: {total}')"

backup-db:
	@echo "Fazendo backup do banco de dados..."
	@cp database.db database.db.backup.$$(date +%Y%m%d_%H%M%S)
	@echo "✓ Backup criado"

reset-db:
	@echo "⚠️  AVISO: Esta ação vai deletar todo o histórico de imóveis!"
	@read -p "Digite 'sim' para confirmar: " confirm; \
	if [ "$$confirm" = "sim" ]; then \
		rm -f database.db; \
		echo "✓ Banco de dados removido"; \
	else \
		echo "Operação cancelada"; \
	fi

clean:
	@echo "Limpando arquivos gerados..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".pytest_cache" -delete
	@rm -rf .playwright/
	@echo "✓ Limpeza concluída"

# Destino padrão
.DEFAULT_GOAL := help

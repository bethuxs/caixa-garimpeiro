# 🏠 Garimpeiro de Imóveis - Caixa Econômica Federal

Um MVP de script web scraping profissional para monitorar e alertar sobre novas oportunidades de imóveis no portal oficial de vendas da Caixa Econômica Federal, com foco na região leste de Curitiba e Pinhais.

## 📋 Características

- ✅ **Web Scraping Assíncrono** com Playwright em modo headless
- ✅ **Persistência de Dados** em SQLite com histórico de imóveis processados
- ✅ **Alertas em Tempo Real** via Bot do Telegram
- ✅ **Filtros Inteligentes** (bairros, preço máximo)
- ✅ **Configuração Flexível** via YAML e variáveis de ambiente
- ✅ **Logging Profissional** com registro em arquivo e console
- ✅ **Tratamento de Erros** com retry automático e resiliência
- ✅ **Type Hints** e segue PEP 8

## 🛠️ Pré-requisitos

- Python 3.9+
- pip ou poetry
- Navegador Chromium (instalado automaticamente pelo Playwright)
- Token de Bot do Telegram
- Chat ID do Telegram

## 📦 Instalação

### 1. Clone ou crie o projeto

```bash
cd /home/beto/www/caixa
```

### 2. Crie um ambiente virtual (recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou no Windows: venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Instale navegadores do Playwright

```bash
playwright install chromium
```

## 🔧 Configuração

### 1. Configure o arquivo `.env`

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e preenchha com seus dados:

```env
# Obter TOKEN e CHAT_ID do Telegram (ver seção abaixo)
TELEGRAM_TOKEN=seu_token_aqui_do_botfather
TELEGRAM_CHAT_ID=seu_chat_id_pessoal

# Opcional
DEBUG=false
TZ=America/Sao_Paulo
EXECUTION_INTERVAL_HOURS=1
```

### 2. Configure o arquivo `config.yaml`

Customize conforme necessário:

```yaml
busca:
  estado: "PR"  # Estado (pode manter ou mudar)
  cidades:
    - nome: "Curitiba"
      codigo: "410690"
    - nome: "Pinhais"
      codigo: "411915"
  modalidades: [33, 34]  # 33=Venda Online, 34=Venda Direta Online

filtros:
  preco_maximo: 200000.00  # Em reais
  bairros_alvo:
    - "TARUMÃ"
    - "BAIRRO ALTO"
    - "CAPÃO DA IMBUIA"
    - "ALTO TARUMÃ"
```

## 🤖 Configurando Telegram Bot

### Obter Token do Bot

1. Abra Telegram e procure por `@BotFather`
2. Envie `/newbot`
3. Siga as instruções para criar um novo bot
4. Copie o **token** fornecido (formato: `123456789:ABCDefGHIJKLmnoPQRstUVwxyz`)

### Obter Chat ID

#### Opção 1: Via @userinfobot
1. Abra Telegram e procure por `@userinfobot`
2. Envie `/start`
3. Copie o **ID** exibido

#### Opção 2: Via seu bot
1. Converse com seu bot criado
2. Execute em terminal:
```bash
curl "https://api.telegram.org/bot[SEU_TOKEN]/getUpdates"
```
3. Procure por `"chat":{"id":` - esse é seu Chat ID

## 🚀 Uso

### Executar uma vez

```bash
python scraper.py
```

### Executar em intervalos (Cron)

#### Linux/macOS - Executar a cada 1 hora

```bash
# Edite o crontab
crontab -e

# Adicione a linha:
0 * * * * cd /home/beto/www/caixa && /path/to/venv/bin/python scraper.py
```

#### Usando systemd timer (Alternativa moderna)

Crie `/etc/systemd/system/caixa-scraper.service`:

```ini
[Unit]
Description=Garimpeiro de Imóveis Caixa
After=network.target

[Service]
Type=oneshot
User=seu_usuario
WorkingDirectory=/home/beto/www/caixa
ExecStart=/home/beto/www/caixa/venv/bin/python scraper.py
Environment="PATH=/home/beto/www/caixa/venv/bin"
StandardOutput=journal
StandardError=journal
```

Crie `/etc/systemd/system/caixa-scraper.timer`:

```ini
[Unit]
Description=Executar Garimpeiro de Imóveis a cada hora
Requires=caixa-scraper.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
AccuracySec=1s

[Install]
WantedBy=timers.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now caixa-scraper.timer
sudo systemctl status caixa-scraper.timer
```

## 📊 Estrutura de Dados

### Banco de Dados SQLite

O arquivo `database.db` armazena:

**Tabela: `imoveis`**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id_imovel` | TEXT PRIMARY KEY | ID único do imóvel |
| `codigo` | TEXT | Código do imóvel |
| `bairro` | TEXT | Bairro do imóvel |
| `preco` | REAL | Preço em reais |
| `descricao` | TEXT | Descrição do imóvel |
| `link` | TEXT UNIQUE | URL do anúncio |
| `modalidade` | TEXT | Tipo de modalidade (Venda Online/Direta) |
| `cidade` | TEXT | Cidade |
| `data_captura` | TIMESTAMP | Data/hora da captura |
| `data_insercao` | TIMESTAMP | Data/hora da inserção no banco |

## 📝 Logs

Os logs são registrados em:
- **Arquivo**: `scraper.log`
- **Console**: Saída padrão (stdout)

Formato:
```
2026-06-04 14:30:45,123 - caixa_scraper - INFO - Garimpeiro iniciado
```

## 🐛 Debug

Para ativar modo debug:

1. Edite `.env`:
```env
DEBUG=true
```

2. Altere nível de log em `config.yaml`:
```yaml
logging:
  level: "DEBUG"
```

3. Execute:
```bash
python scraper.py
```

## 📚 Estrutura do Código

```
scraper.py
├── Importações e configuração de logging
├── setup_logging()              # Configura logging
├── CaixaConfig                  # Gerencia configurações YAML/.env
├── Imovel                       # Dataclass para imóvel
├── Database                     # SQLite operations
│   ├── imovel_existe()
│   ├── inserir_imovel()
│   ├── limpar_antigos()
│   └── obter_estatisticas()
├── TelegramNotifier             # Notificações via Telegram
│   ├── enviar_alerta_imovel()
│   ├── _enviar_mensagem()
│   └── enviar_teste()
├── CaixaScraper                 # Orquestra scraping
│   ├── iniciar()
│   ├── fechar()
│   ├── navegar_e_buscar()
│   ├── _preencher_formulario()
│   ├── _extrair_imoveis()
│   ├── _extrair_dados_linha()
│   ├── _extrair_preco()
│   ├── _aplicar_filtros()
│   ├── processar_resultados()
│   └── executar()
└── main()                       # Função principal
```

## 🔍 Seletores CSS (Ajustáveis)

Os seletores estão definidos em `CaixaScraper.SELECTORS`:

```python
SELECTORS = {
    "estado": "#cmb_estado",
    "cidade": "#cmb_cidade",
    "modalidade": "#cmb_tipo_modalidade",
    "botao_buscar": "button:has-text('Buscar')",
    "tabela_resultados": "table.resultTable, .resultado, [data-testid='resultTable']",
    "linhas_imovel": "tr[class*='linhaResultado'], .imovel-item",
    # ... mais seletores
}
```

**Se o portal for atualizado e os seletores não funcionarem:**

1. Abra DevTools do navegador (F12)
2. Identifique novos seletores
3. Atualize `CaixaScraper.SELECTORS`

## 🚨 Troubleshooting

### "Timeout ao carregar página"
- Aumentar timeout em `config.yaml`: `timeout: 20000`
- Verificar conexão de internet
- Portal pode estar fora do ar

### "Nenhum resultado encontrado"
- Verificar se os seletores CSS ainda são válidos
- Usar DevTools para inspecionar página
- Aumentar `wait_between_requests` em config.yaml

### "Mensagens não chegam no Telegram"
- Verificar TOKEN e CHAT_ID em `.env`
- Executar: `python -c "from scraper import TelegramNotifier; TelegramNotifier('token', 'id').enviar_teste()"`
- Verificar se Bot não foi banido

### "Erro: SQLite database is locked"
- Garantir que apenas uma instância está rodando
- Verificar se existe outro processo usando o banco
- Reiniciar: `rm -f database.db` (perderá histórico)

## 📈 Próximas Melhorias

- [ ] Suporte a proxy/VPN
- [ ] Notificações com imagens
- [ ] Filtros por área/metragem
- [ ] Histórico gráfico de preços
- [ ] Exportar para CSV/JSON
- [ ] Dashboard web
- [ ] Cache de imagens
- [ ] Multi-threading para múltiplas cidades

## ⚖️ Notas Legais

- Respeite os `robots.txt` do portal
- Não sobrecarregue o servidor com requisições
- Use timeout e delays apropriados
- Verifique a política de termos de serviço da Caixa

## 📄 Licença

MIT License - Use livremente em projetos pessoais ou comerciais

## 👤 Suporte

Para problemas ou sugestões:
1. Verifique os logs em `scraper.log`
2. Consulte a seção Troubleshooting
3. Revise a configuração em `config.yaml` e `.env`

---

**Última atualização**: 04 de Junho de 2026  
**Versão**: 1.0.0 (MVP)

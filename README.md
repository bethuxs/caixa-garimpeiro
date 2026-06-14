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
# Combine TOKEN e CHAT_ID do Telegram em uma única variável (formato: token:chat_id)
TELEGRAM_CREDENTIALS=seu_token_aqui_do_botfather:seu_chat_id_pessoal

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

### Executar uma única vez

```bash
source venv/bin/activate  # Ativar ambiente virtual
python scraper.py
```

**O que acontece:**
1. Lê configurações de `config.yaml` e variáveis de `.env`
2. Conecta ao portal da Caixa
3. Busca imóveis conforme filtros configurados
4. Filtra resultados e envia alertas via Telegram para novos imóveis
5. Registra dados no `database.db`
6. Sai

### Executar continuamente com Cron (Recomendado para VPS)

#### Linux/macOS - Executar a cada 1 hora

```bash
# Abra o editor do crontab
crontab -e

# Adicione esta linha (substitua o caminho do venv):
0 * * * * cd /home/beto/www/caixa && /home/beto/www/caixa/venv/bin/python scraper.py >> scraper.log 2>&1
```

**Outros intervalos úteis:**
```bash
# A cada 30 minutos
*/30 * * * * cd /home/beto/www/caixa && /home/beto/www/caixa/venv/bin/python scraper.py

# A cada 15 minutos
*/15 * * * * cd /home/beto/www/caixa && /home/beto/www/caixa/venv/bin/python scraper.py

# A cada dia às 08:00
0 8 * * * cd /home/beto/www/caixa && /home/beto/www/caixa/venv/bin/python scraper.py

# Segunda a sexta às 09:00 e 17:00
0 9,17 * * 1-5 cd /home/beto/www/caixa && /home/beto/www/caixa/venv/bin/python scraper.py
```

**Para verificar crons ativos:**
```bash
crontab -l
```

**Para remover cron:**
```bash
crontab -r
```

#### Usando systemd timer (Alternativa moderna para VPS)

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

## 📋 Referência de Configuração (config.yaml)

### Seção: `busca` - Parâmetros de Busca no Portal

Define **qual estado, cidades e tipos de imóvel** devem ser procurados.

```yaml
busca:
  estado: "PR"                    # Estado (sigla de 2 letras)
  cidades:
    - nome: "Curitiba"            # Nome da cidade (para logs)
      codigo: "6143"              # Código interno do portal da Caixa
    - nome: "Cascavel"
      codigo: "6068"
    - nome: "Pinhais"
      codigo: "6578"
    - nome: "São José dos Pinhais"
      codigo: "6794"
    - nome: "Foz do Iguaçu"
      codigo: "6220"
  modalidades: [14, 33, 34]       # IDs das modalidades desejadas
```

**Modalidades disponíveis:**
- `14` = Leilão SFI - Edital Único
- `33` = Venda Online (Melhor Oferta)
- `34` = Venda Direta Online
- Consulte o portal para outros códigos

**⚠️ Nota sobre Modalidades:**
- Os números (14, 33, 34) são convertidos automaticamente para nomes legíveis nos resultados
- Exemplo: em `config.yaml` você define `modalidades: [33]`, mas nos resultados e Telegram aparecerá como "Venda Online (Melhor Oferta)"
- Imóveis com preço R$ 0 são automaticamente descartados

**Como obter código de cidade:**
1. Acesse: https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis
2. Abra DevTools (F12) → Aba Network
3. Selecione um estado, depois a cidade
4. Procure pela requisição que contém a cidade e veja seu código

---

### Seção: `filtros` - Filtros de Resultado

Define **quais imóveis são importantes** depois que foram coletados. O scraper coleta TODOS e depois filtra localmente.

```yaml
filtros:
  preco_maximo: 999999999.00      # Preço máximo em reais (sem limite)
  cidades_alvo: []                # Lista de cidades para alertar (vazio = todas)
  bairros_alvo: []                # Lista de bairros para alertar (vazio = todos)
```

**⚠️ Importante:**
- Se `cidades_alvo` está **vazio** → alerta de TODAS as cidades
- Se `bairros_alvo` está **vazio** → alerta de TODOS os bairros
- Se ambos têm valores → filtra por AMBOS (AND lógico)
- Se apenas `cidades_alvo` tem valores → filtra apenas por cidade

**Exemplos:**

```yaml
# Exemplo 1: Apenas Curitiba, qualquer bairro
filtros:
  preco_maximo: 999999999.00
  cidades_alvo:
    - "Curitiba"
  bairros_alvo: []

# Exemplo 2: Curitiba OU Pinhais, qualquer preço
filtros:
  preco_maximo: 999999999.00
  cidades_alvo:
    - "Curitiba"
    - "Pinhais"
  bairros_alvo: []

# Exemplo 3: Apenas Tarumã (qualquer cidade)
filtros:
  preco_maximo: 999999999.00
  cidades_alvo: []
  bairros_alvo:
    - "TARUMÃ"

# Exemplo 4: Curitiba E Tarumã até R$ 200.000
filtros:
  preco_maximo: 200000.00
  cidades_alvo:
    - "Curitiba"
  bairros_alvo:
    - "TARUMÃ"

# Exemplo 5: Sem nenhum filtro (alerta TUDO)
filtros:
  preco_maximo: 999999999.00
  cidades_alvo: []
  bairros_alvo: []
```

---

### Seção: `playwright` - Configuração do Navegador Automatizado

Controla como o Playwright (navegador headless) se comporta durante o scraping.

```yaml
playwright:
  headless: true                          # true = sem janela visível, false = mostra navegador
  timeout: 30000                          # Timeout em ms (30s) para aguardar elementos
  wait_between_requests: 2                # Tempo de espera entre requisições em segundos
  max_retries: 3                          # Número máximo de tentativas ao carregar página
  user_agent: "Mozilla/5.0 (Windows NT..." # User-Agent customizado
```

**Recomendações:**

| Configuração | Valor | Quando usar |
|---|---|---|
| `headless` | `true` | Em produção (VPS, Cron, etc) |
| `headless` | `false` | Debugando localmente |
| `timeout` | `30000` (30s) | Padrão - portal responde rápido |
| `timeout` | `60000` (60s) | Portal lento ou conexão ruim |
| `wait_between_requests` | `2` | Padrão - respeita servidor |
| `wait_between_requests` | `5` | Portal bloqueia requisições rápidas |
| `max_retries` | `3` | Padrão - tenta 3 vezes antes de falhar |

---

### Seção: `logging` - Configuração de Logs

Define **como e onde** registrar informações do scraping.

```yaml
logging:
  level: "INFO"                           # Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  file: "scraper.log"                     # Nome do arquivo de log
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Níveis de Log:**

| Nível | Quando usar | Exemplo |
|---|---|---|
| `DEBUG` | Debugging detalhado | Valores de variáveis, passos internos |
| `INFO` | Operação normal (padrão) | "Iniciando scraper", "50 imóveis encontrados" |
| `WARNING` | Situações inesperadas mas toleradas | Elementos não encontrados |
| `ERROR` | Erros que impactam execução | Falha ao conectar ao Telegram |
| `CRITICAL` | Erros críticos que param execução | Falha ao ler config.yaml |

**Exemplo para debugging:**

```yaml
logging:
  level: "DEBUG"  # Muito verboso, mostra tudo
  file: "scraper.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

### Seção: `database` - Banco de Dados SQLite

Configura armazenamento de dados.

```yaml
database:
  path: "database.db"                     # Caminho do arquivo SQLite
  cleanup_days: 90                        # Deletar registros com mais de 90 dias
```

**O que fazer se o banco ficar muito grande:**
- Diminua `cleanup_days` para deletar dados mais antigos
- Ou apague manualmente: `rm database.db` (reseta o histórico)

---

### Seção: `urls` - URLs do Portal

**Não altere esta seção** a menos que a Caixa mude o endereço do portal.

```yaml
urls:
  base_url: "https://venda-imoveis.caixa.gov.br"
  search_page: "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis"
```

---

## 🎯 Exemplos de Configuração Comum

### Ejemplo 1: Monitorar Curitiba - Apenas Tarumã até R$ 150.000

```yaml
busca:
  estado: "PR"
  cidades:
    - nome: "Curitiba"
      codigo: "6143"
  modalidades: [33, 34]

filtros:
  preco_maximo: 150000.00
  cidades_alvo:
    - "Curitiba"
  bairros_alvo:
    - "TARUMÃ"

playwright:
  headless: true
  timeout: 30000
  wait_between_requests: 2
  max_retries: 3
```

### Ejemplo 2: Monitorar Toda Región - Sem Filtro de Preço

```yaml
busca:
  estado: "PR"
  cidades:
    - nome: "Curitiba"
      codigo: "6143"
    - nome: "Pinhais"
      codigo: "6578"
    - nome: "São José dos Pinhais"
      codigo: "6794"
    - nome: "Cascavel"
      codigo: "6068"
  modalidades: [33, 34]

filtros:
  preco_maximo: 999999999.00
  cidades_alvo: []  # Alerta de TODAS as ciudades
  bairros_alvo: []  # Alerta de TODOS os bairros

logging:
  level: "INFO"
```

### Exemplo 3: Debug - Tudo Detalhado

```yaml
# ... mesmas configs acima ...

logging:
  level: "DEBUG"  # Mostra TUDO que está acontecendo
  file: "scraper_debug.log"

playwright:
  headless: false  # Mostra janela do navegador
  timeout: 60000   # Mais tempo para você acompanhar
  wait_between_requests: 5
```

---

## ⚙️ Usando Variáveis de Ambiente vs. config.yaml

**Configuração do scraper vem de 3 fontes (ordem de prioridade):**

1. **Variáveis de ambiente** (`.env`) - Maior prioridade
2. **config.yaml** - Prioridade média
3. **Defaults no código** - Menor prioridade

**Quando usar cada uma:**

- **`.env`**: Dados sensíveis (token Telegram, credenciais)
- **`config.yaml`**: Parâmetros de busca e filtros que mudam frequentemente
- **Código**: Defaults que raramente mudam

**Exemplo: Override via .env**

Se você quer temporariamente mudar o nível de log sem editar `config.yaml`:

```bash
# Terminal
export DEBUG=true
python scraper.py

# Ou em .env (permanente)
DEBUG=true
```

---

#### Usando systemd timer (Alternativa moderna para VPS)

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

### "Imóveis com preço R$ 0 aparecem"
- Estes são automaticamente **DESCARTADOS** (filtro ativo)
- Verificar logs em `scraper.log` para ver quais foram rejeitados
- Para ver detalhadamente por que um imóvel tem preço 0:
  1. Ativar DEBUG mode em `.env`: `DEBUG=true`
  2. Ou em `config.yaml`: `logging.level: "DEBUG"`
  3. Executar: `python scraper.py`
  4. Ver logs: `grep "Preço extraído como 0.0" scraper.log`

**Possíveis causas:**
- Imóvel ainda não tem preço definido no portal
- Preço estava em formato diferente não reconhecido
- Campo de preço vazio no HTML

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

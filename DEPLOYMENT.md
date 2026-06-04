# 🚀 GUIA DE DEPLOYMENT - Garimpeiro de Imóveis no VPS

## 📋 Checklist Pre-Deploy

Antes de começar, certifique-se que:
- ✅ Você tem acesso SSH ao servidor: `root@financiero.com.br`
- ✅ Usuário `caixa` foi criado (já feito)
- ✅ Python 3, pip3 e git estão instalados (já feito)
- ✅ Você tem Token do Telegram Bot (@BotFather)
- ✅ Você tem Chat ID do Telegram (@userinfobot)

---

## 🎯 Passo 1: Fazer SSH e Preparar

```bash
# Conectar ao servidor como root
ssh root@financiero.com.br

# Verificar que usuário caixa existe
id caixa

# Mudar para usuário caixa
su - caixa

# Verificar que estamos no diretório correto
pwd  # Deve retornar: /home/caixa
```

---

## 🎯 Passo 2: Clonar o Repositório

```bash
# Como usuário caixa
cd /home/caixa/projetos

# Clonar o repositório
git clone git@github.com:bethuxs/caixa-garimpeiro.git

# Entrar no diretório
cd caixa-garimpeiro
```

**Se receber erro de SSH key**, configure assim (como usuário caixa):

```bash
# Gerar SSH key
ssh-keygen -t ed25519 -C "caixa@financiero.com.br"

# Aceitar padrões (pressionar Enter 3 vezes)

# Copiar chave pública para GitHub
cat ~/.ssh/id_ed25519.pub
# Ir em GitHub > Settings > SSH Keys > Add new

# Testar conexão
ssh -T git@github.com
# Deve retornar: "Hi bethuxs! You've successfully authenticated..."
```

---

## 🎯 Passo 3: Criar Ambiente Virtual e Instalar Dependências

```bash
# Estar no diretório do projeto
cd /home/caixa/projetos/caixa-garimpeiro

# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente
source venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt

# Instalar Playwright (demora alguns minutos)
python -m playwright install chromium

# Desativar venv (opcional por enquanto)
deactivate
```

**Tempo estimado:** 5-10 minutos

---

## 🎯 Passo 4: Configurar Telegram

```bash
# Copiar template do .env
cp .env.example .env

# Editar arquivo .env
nano .env
```

**Altere:**
```
TELEGRAM_TOKEN=seu_token_aqui_do_botfather
TELEGRAM_CHAT_ID=seu_chat_id_pessoal
DEBUG=false
```

**Como obter:**

1. **Token:**
   - Abra Telegram
   - Procure por `@BotFather`
   - Envie `/newbot`
   - Siga as instruções
   - Copie o token fornecido

2. **Chat ID:**
   - Procure por `@userinfobot`
   - Envie `/start`
   - Copie o ID mostrado

**Salve (Ctrl+X, Y, Enter)**

---

## 🎯 Passo 5: Configurar Filtros (Opcional)

```bash
# Editar configurações
nano config.yaml
```

Customize conforme necessário:
```yaml
filtros:
  preco_maximo: 200000.00  # Aumentar/diminuir limite
  bairros_alvo:
    - "TARUMÃ"
    - "BAIRRO ALTO"
    - "CAPÃO DA IMBUIA"
    - "ALTO TARUMÃ"
    # Adicionar/remover bairros
```

**Salve (Ctrl+X, Y, Enter)**

---

## 🎯 Passo 6: Testar Execução Uma Vez

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Rodar script
python scraper.py

# Verificar logs
tail scraper.log
```

**Esperado:**
```
[✓] Banco de dados inicializado
[✓] Playwright iniciado
[✓] Navegando para portal...
[✓] Imóveis encontrados: X
[✓] Execução concluída
```

Se receber mensagem no Telegram = **Sucesso!** 🎉

---

## 🎯 Passo 7: Configurar Execução Periódica (Systemd Timer)

### Opção A: Cron (Simples)

```bash
# Editar crontab
crontab -e

# Adicionar linha para executar a cada 1 hora:
0 * * * * cd /home/caixa/projetos/caixa-garimpeiro && /home/caixa/projetos/caixa-garimpeiro/venv/bin/python scraper.py >> /home/caixa/projetos/caixa-garimpeiro/logs/cron.log 2>&1

# Salvar e sair (Ctrl+X, Y, Enter)

# Verificar que foi adicionado
crontab -l
```

### Opção B: Systemd Timer (Recomendado)

**Como root:**

```bash
exit  # Voltar para root

# Criar arquivo de serviço
sudo nano /etc/systemd/system/caixa-scraper.service
```

**Cole:**
```ini
[Unit]
Description=Garimpeiro de Imóveis Caixa
After=network.target

[Service]
Type=oneshot
User=caixa
Group=caixa
WorkingDirectory=/home/caixa/projetos/caixa-garimpeiro
ExecStart=/home/caixa/projetos/caixa-garimpeiro/venv/bin/python /home/caixa/projetos/caixa-garimpeiro/scraper.py
Environment="PATH=/home/caixa/projetos/caixa-garimpeiro/venv/bin"
StandardOutput=journal
StandardError=journal
EnvironmentFile=/home/caixa/projetos/caixa-garimpeiro/.env

[Install]
WantedBy=multi-user.target
```

**Salve (Ctrl+X, Y, Enter)**

**Criar arquivo de timer:**

```bash
sudo nano /etc/systemd/system/caixa-scraper.timer
```

**Cole:**
```ini
[Unit]
Description=Executar Garimpeiro de Imóveis a cada hora
Requires=caixa-scraper.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
AccuracySec=1s
Persistent=true

[Install]
WantedBy=timers.target
```

**Salve (Ctrl+X, Y, Enter)**

**Ativar:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable caixa-scraper.timer
sudo systemctl start caixa-scraper.timer

# Verificar status
sudo systemctl status caixa-scraper.timer

# Ver próximas execuções
sudo systemctl list-timers caixa-scraper.timer

# Ver logs
sudo journalctl -u caixa-scraper.service -f
```

---

## 📊 Monitorando

### Ver Logs em Tempo Real

```bash
# Via arquivo (cron)
tail -f /home/caixa/projetos/caixa-garimpeiro/scraper.log

# Via systemd (timer)
sudo journalctl -u caixa-scraper.service -f

# Ver últimas 50 linhas
tail -50 scraper.log
```

### Ver Próximas Execuções

```bash
sudo systemctl list-timers
```

### Testar Service Manualmente

```bash
sudo systemctl start caixa-scraper.service
```

### Ver Estatísticas do Banco de Dados

```bash
cd /home/caixa/projetos/caixa-garimpeiro
source venv/bin/activate
python debug.py test-db
```

---

## 🔧 Troubleshooting

### "Erro: git@github.com permission denied"

```bash
# Gerar SSH key se não tiver
ssh-keygen -t ed25519

# Adicionar chave pública no GitHub
cat ~/.ssh/id_ed25519.pub
# Copiar e adicionar em: GitHub > Settings > SSH Keys

# Testar
ssh -T git@github.com
```

### "Erro: Playwright chromium not found"

```bash
source venv/bin/activate
python -m playwright install chromium
```

### "Mensagens não chegam no Telegram"

```bash
source venv/bin/activate
python debug.py test-telegram
```

### "Erro: SQLite database is locked"

```bash
# Garantir que apenas uma instância está rodando
ps aux | grep scraper.py

# Se houver múltiplos processos, matar um:
kill <PID>

# Ou resetar banco (perderá histórico):
rm database.db
```

### "Timeout ao carregar página"

```bash
# Editar config.yaml
nano config.yaml

# Aumentar timeout:
playwright:
  timeout: 20000  # De 10000 para 20000
```

---

## 📈 Atualizações Futuras

Quando quiser atualizar o código:

```bash
cd /home/caixa/projetos/caixa-garimpeiro
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📞 Suporte

Para problemas:

1. Verificar logs: `tail -f scraper.log`
2. Testar conexão: `python debug.py test-telegram`
3. Testar BD: `python debug.py test-db`
4. Ver documentação: `README.md`

---

## ✅ Confirmação de Sucesso

Após tudo configurado, você deve:

- ✅ Receber alertas no Telegram quando novo imóvel for encontrado
- ✅ Ver arquivo `database.db` com histórico de imóveis
- ✅ Ver arquivo `scraper.log` com execuções
- ✅ Systemd timer/Cron executando automaticamente
- ✅ Zero erros nos logs

**Deploy Completo!** 🎉

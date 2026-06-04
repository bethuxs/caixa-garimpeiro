#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Garimpeiro de Imóveis - Caixa Econômica Federal
Script de Web Scraping com Playwright e Alertas via Telegram
================================================================================

Módulo principal para monitorar e alertar sobre novas oportunidades de imóveis
no portal oficial de venda de imóveis da Caixa Econômica Federal.

Dependências:
    - playwright >= 1.40.0
    - pyyaml >= 6.0
    - python-dotenv >= 1.0.0
    - requests >= 2.31.0

Uso:
    python scraper.py

Autor: Seu Nome
Data: 2026-06-04
Versão: 1.0.0
================================================================================
"""

import asyncio
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin

import requests
import yaml
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """
    Configura o sistema de logging da aplicação.

    Args:
        config: Dicionário com configurações de logging

    Returns:
        Logger configurado
    """
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO"))
    log_file = log_config.get("file", "scraper.log")
    log_format = log_config.get(
        "format",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger("caixa_scraper")
    logger.setLevel(log_level)

    # Handler para arquivo
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


# ============================================================================
# CLASSES DE DADOS
# ============================================================================

@dataclass
class Imovel:
    """Representa um imóvel encontrado no portal da Caixa."""
    id_imovel: str
    codigo: str
    bairro: str
    preco: float
    descricao: str
    link: str
    modalidade: str
    cidade: str
    data_captura: str

    def __post_init__(self):
        """Valida dados após inicialização."""
        if not self.id_imovel:
            raise ValueError("ID do imóvel não pode estar vazio")
        if self.preco < 0:
            raise ValueError(f"Preço inválido: {self.preco}")


@dataclass
class CaixaConfig:
    """Configuração da aplicação."""
    config_file: str = "config.yaml"
    env_file: str = ".env"
    
    def __post_init__(self):
        """Carrega configurações após inicialização."""
        load_dotenv(self.env_file)
        self._load_yaml()
        self._validate()

    def _load_yaml(self) -> None:
        """Carrega configurações do arquivo YAML."""
        if not Path(self.config_file).exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_file}")
        
        with open(self.config_file, "r", encoding="utf-8") as f:
            self.yaml_config = yaml.safe_load(f)

    def _validate(self) -> None:
        """Valida configurações obrigatórias."""
        if not os.getenv("TELEGRAM_TOKEN"):
            raise ValueError("TELEGRAM_TOKEN não definido nas variáveis de ambiente")
        if not os.getenv("TELEGRAM_CHAT_ID"):
            raise ValueError("TELEGRAM_CHAT_ID não definido nas variáveis de ambiente")

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração."""
        return self.yaml_config.get(key, default)


# ============================================================================
# CLASSE DE BANCO DE DADOS
# ============================================================================

class Database:
    """
    Gerencia operações de banco de dados SQLite.
    
    Responsabilidades:
        - Inicializar e criar tabelas
        - Verificar existência de imóveis processados
        - Inserir novos imóveis
        - Limpar registros antigos
    """

    def __init__(self, db_path: str = "database.db", logger: Optional[logging.Logger] = None):
        """
        Inicializa a conexão com o banco de dados.

        Args:
            db_path: Caminho para o arquivo do banco de dados
            logger: Logger para registrar operações
        """
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        self._init_db()

    def _init_db(self) -> None:
        """Cria as tabelas necessárias se não existirem."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela de imóveis processados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS imoveis (
                    id_imovel TEXT PRIMARY KEY,
                    codigo TEXT NOT NULL,
                    bairro TEXT NOT NULL,
                    preco REAL NOT NULL,
                    descricao TEXT,
                    link TEXT UNIQUE NOT NULL,
                    modalidade TEXT,
                    cidade TEXT,
                    data_captura TIMESTAMP NOT NULL,
                    data_insercao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para otimizar consultas
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_id_imovel ON imoveis(id_imovel)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_bairro ON imoveis(bairro)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_data_insercao ON imoveis(data_insercao)
            """)
            
            conn.commit()
            self.logger.info(f"Banco de dados inicializado: {self.db_path}")

    def imovel_existe(self, id_imovel: str) -> bool:
        """
        Verifica se um imóvel já foi processado.

        Args:
            id_imovel: ID do imóvel

        Returns:
            True se o imóvel foi processado, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM imoveis WHERE id_imovel = ?", (id_imovel,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao verificar imóvel: {e}")
            return False

    def inserir_imovel(self, imovel: Imovel) -> bool:
        """
        Insere um novo imóvel no banco de dados.

        Args:
            imovel: Objeto Imovel a ser inserido

        Returns:
            True se inserido com sucesso, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO imoveis (
                        id_imovel, codigo, bairro, preco, descricao, 
                        link, modalidade, cidade, data_captura
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    imovel.id_imovel,
                    imovel.codigo,
                    imovel.bairro,
                    imovel.preco,
                    imovel.descricao,
                    imovel.link,
                    imovel.modalidade,
                    imovel.cidade,
                    imovel.data_captura
                ))
                conn.commit()
                self.logger.info(f"Imóvel inserido: {imovel.id_imovel}")
                return True
        except sqlite3.IntegrityError as e:
            self.logger.warning(f"Imóvel duplicado: {imovel.id_imovel} - {e}")
            return False
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao inserir imóvel: {e}")
            return False

    def limpar_antigos(self, dias: int = 90) -> int:
        """
        Remove registros de imóveis processados há mais de N dias.

        Args:
            dias: Número de dias para manter histórico

        Returns:
            Número de registros removidos
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                data_limite = datetime.now() - timedelta(days=dias)
                cursor.execute(
                    "DELETE FROM imoveis WHERE data_insercao < ?",
                    (data_limite.isoformat(),)
                )
                conn.commit()
                deletados = cursor.rowcount
                self.logger.info(f"Registros antigos removidos: {deletados}")
                return deletados
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao limpar banco de dados: {e}")
            return 0

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do banco de dados.

        Returns:
            Dicionário com estatísticas
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total de imóveis
                cursor.execute("SELECT COUNT(*) FROM imoveis")
                total = cursor.fetchone()[0]
                
                # Imóveis por bairro
                cursor.execute("""
                    SELECT bairro, COUNT(*) as total 
                    FROM imoveis 
                    GROUP BY bairro 
                    ORDER BY total DESC
                """)
                por_bairro = dict(cursor.fetchall())
                
                # Preço médio
                cursor.execute("SELECT AVG(preco) FROM imoveis")
                preco_medio = cursor.fetchone()[0] or 0
                
                return {
                    "total_imoveis": total,
                    "por_bairro": por_bairro,
                    "preco_medio": preco_medio
                }
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {}


# ============================================================================
# CLASSE DE TELEGRAM
# ============================================================================

class TelegramNotifier:
    """
    Gerencia envio de notificações via Telegram Bot.
    
    Responsabilidades:
        - Enviar mensagens formatadas
        - Tratamento de erros de conexão
        - Retry automático
    """

    def __init__(self, token: str, chat_id: str, logger: Optional[logging.Logger] = None):
        """
        Inicializa o notificador do Telegram.

        Args:
            token: Token do Telegram Bot
            chat_id: ID do chat para receber mensagens
            logger: Logger para registrar operações
        """
        self.token = token
        self.chat_id = chat_id
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        self.session.timeout = 10

    def enviar_alerta_imovel(self, imovel: Imovel) -> bool:
        """
        Envia alerta de novo imóvel via Telegram.

        Args:
            imovel: Objeto Imovel com dados a serem enviados

        Returns:
            True se enviado com sucesso, False caso contrário
        """
        # Formata preço em reais
        preco_formatado = f"R$ {imovel.preco:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        
        # Constrói mensagem HTML
        mensagem = f"""
<b>🏠 NOVO IMÓVEL ENCONTRADO!</b>

<b>ID:</b> <code>{imovel.id_imovel}</code>
<b>Bairro:</b> {imovel.bairro}
<b>Cidade:</b> {imovel.cidade}
<b>Preço:</b> <b>{preco_formatado}</b>
<b>Modalidade:</b> {imovel.modalidade}

<b>Descrição:</b>
{imovel.descricao}

<b>🔗 Link:</b> <a href="{imovel.link}">Acessar Anúncio</a>

<i>Capturado em: {imovel.data_captura}</i>
        """.strip()

        return self._enviar_mensagem(mensagem, parse_mode="HTML")

    def _enviar_mensagem(self, texto: str, parse_mode: str = "HTML", max_retries: int = 3) -> bool:
        """
        Envia uma mensagem via API do Telegram com retry automático.

        Args:
            texto: Texto da mensagem
            parse_mode: Modo de parse (HTML ou Markdown)
            max_retries: Número máximo de tentativas

        Returns:
            True se enviado com sucesso, False caso contrário
        """
        payload = {
            "chat_id": self.chat_id,
            "text": texto,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }

        for tentativa in range(1, max_retries + 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/sendMessage",
                    json=payload
                )
                response.raise_for_status()
                
                if response.json().get("ok"):
                    self.logger.info("Mensagem enviada via Telegram")
                    return True
                else:
                    self.logger.error(f"Erro Telegram: {response.json()}")
                    return False

            except requests.Timeout:
                self.logger.warning(f"Timeout ao enviar mensagem (tentativa {tentativa}/{max_retries})")
                if tentativa < max_retries:
                    asyncio.run(asyncio.sleep(2 ** tentativa))  # Exponential backoff
                continue

            except requests.RequestException as e:
                self.logger.error(f"Erro ao enviar mensagem: {e}")
                return False

        self.logger.error(f"Falha ao enviar mensagem após {max_retries} tentativas")
        return False

    def enviar_teste(self) -> bool:
        """
        Envia uma mensagem de teste para validar configuração.

        Returns:
            True se enviado com sucesso, False caso contrário
        """
        mensagem = """
<b>✅ Teste de Conexão</b>

Garimpeiro de Imóveis - Caixa está funcionando corretamente!

<i>Mensagem de teste enviada em: {}</i>
        """.format(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        
        return self._enviar_mensagem(mensagem, parse_mode="HTML")


# ============================================================================
# CLASSE PRINCIPAL DE SCRAPING
# ============================================================================

class CaixaScraper:
    """
    Orquestra o scraping do portal de imóveis da Caixa.
    
    Responsabilidades:
        - Navegar até a página de busca
        - Preencher formulários
        - Extrair dados de imóveis
        - Aplicar filtros
        - Coordenar com banco de dados e Telegram
    """

    # Seletores CSS do portal (podem mudar com atualizações do site)
    SELECTORS = {
        "estado": "#cmb_estado",
        "cidade": "#cmb_cidade",
        "modalidade": "#cmb_tipo_modalidade",
        "botao_buscar": "button:has-text('Buscar')",
        "tabela_resultados": "table.resultTable, .resultado, [data-testid='resultTable']",
        "linhas_imovel": "tr[class*='linhaResultado'], .imovel-item",
        "link_imovel": "a[href*='imovel']",
        "preco": ".valor, .preco, td:nth-child(3)",
        "bairro": ".bairro, td:nth-child(2)",
    }

    def __init__(self, config: CaixaConfig, db: Database, telegram: TelegramNotifier,
                 logger: logging.Logger):
        """
        Inicializa o scraper.

        Args:
            config: Configurações da aplicação
            db: Instância do gerenciador de banco de dados
            telegram: Instância do notificador Telegram
            logger: Logger para registrar operações
        """
        self.config = config
        self.db = db
        self.telegram = telegram
        self.logger = logger
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def iniciar(self) -> None:
        """Inicia o navegador Playwright."""
        try:
            playwright_config = self.config.get("playwright", {})
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=playwright_config.get("headless", True),
            )
            self.page = await self.browser.new_page(
                user_agent=playwright_config.get("user_agent")
            )
            self.logger.info("Playwright iniciado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao iniciar Playwright: {e}")
            raise

    async def fechar(self) -> None:
        """Fecha o navegador e libera recursos."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("Playwright finalizado")
        except Exception as e:
            self.logger.error(f"Erro ao fechar Playwright: {e}")

    async def navegar_e_buscar(self) -> List[Imovel] | tuple:
        """
        Navega até o portal e executa a busca com filtros.

        Returns:
            Lista de imóveis encontrados
        """
        try:
            url_busca = self.config.get("urls", {}).get(
                "search_page",
                "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp"
            )
            
            self.logger.info(f"Navegando para: {url_busca}")
            await self.page.goto(url_busca, wait_until="networkidle", timeout=30000)
            
            # Aguarda carregamento da página
            await self.page.wait_for_load_state("networkidle")
            
            # Preenche o formulário
            await self._preencher_formulario()
            
            # Aguarda resultados
            await asyncio.sleep(self.config.get("playwright", {}).get("wait_between_requests", 2))
            
            # Extrai imóveis
            imoveis = await self._extrair_imoveis()
            
            self.logger.info(f"Total de imóveis encontrados: {len(imoveis)}")
            return imoveis

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout ao carregar página: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Erro durante navegação: {e}")
            return []

    async def _preencher_formulario(self) -> None:
        """Preenche e submete o formulário de busca."""
        try:
            busca_config = self.config.get("busca", {})
            playwright_config = self.config.get("playwright", {})
            timeout = playwright_config.get("timeout", 10000)

            # Seleciona estado
            estado = busca_config.get("estado", "PR")
            self.logger.info(f"Selecionando estado: {estado}")
            await self.page.select_option(self.SELECTORS["estado"], estado, timeout=timeout)
            
            await asyncio.sleep(1)

            # Seleciona cidades
            cidades = busca_config.get("cidades", [])
            for cidade_info in cidades:
                codigo = cidade_info.get("codigo")
                nome = cidade_info.get("nome")
                if codigo:
                    self.logger.info(f"Selecionando cidade: {nome}")
                    try:
                        await self.page.select_option(
                            self.SELECTORS["cidade"],
                            codigo,
                            timeout=timeout
                        )
                    except Exception as e:
                        self.logger.warning(f"Erro ao selecionar cidade {nome}: {e}")

            await asyncio.sleep(1)

            # Seleciona modalidades
            modalidades = busca_config.get("modalidades", [33, 34])
            for modalidade in modalidades:
                self.logger.info(f"Selecionando modalidade: {modalidade}")
                try:
                    await self.page.select_option(
                        self.SELECTORS["modalidade"],
                        str(modalidade),
                        timeout=timeout
                    )
                except Exception as e:
                    self.logger.warning(f"Erro ao selecionar modalidade {modalidade}: {e}")

            await asyncio.sleep(1)

            # Clica em buscar
            self.logger.info("Clicando em Buscar")
            await self.page.click(self.SELECTORS["botao_buscar"], timeout=timeout)

        except Exception as e:
            self.logger.error(f"Erro ao preencher formulário: {e}")
            raise

    async def _extrair_imoveis(self) -> List[Imovel]:
        """
        Extrai dados dos imóveis da página de resultados.

        Returns:
            Lista de objetos Imovel
        """
        imoveis = []
        try:
            # Aguarda tabela de resultados
            timeout = self.config.get("playwright", {}).get("timeout", 10000)
            await self.page.wait_for_selector(self.SELECTORS["tabela_resultados"], timeout=timeout)
            
            # Extrai conteúdo HTML
            conteudo = await self.page.content()
            
            # Parse simples de linhas (pode ser expandido com BeautifulSoup se necessário)
            # Esta é uma extração básica que precisa ser ajustada conforme o HTML real
            linhas = await self.page.query_selector_all(self.SELECTORS["linhas_imovel"])
            
            self.logger.info(f"Linhas de imóvel encontradas: {len(linhas)}")
            
            for linha in linhas:
                try:
                    imovel = await self._extrair_dados_linha(linha)
                    if imovel:
                        imoveis.append(imovel)
                except Exception as e:
                    self.logger.warning(f"Erro ao extrair dados de linha: {e}")
                    continue
            
            return imoveis

        except PlaywrightTimeoutError:
            self.logger.warning("Timeout esperando tabela de resultados - possivelmente nenhum resultado")
            return []
        except Exception as e:
            self.logger.error(f"Erro ao extrair imóveis: {e}")
            return []

    async def _extrair_dados_linha(self, elemento) -> Optional[Imovel]:
        """
        Extrai dados de um elemento de linha de imóvel.

        Args:
            elemento: Elemento DOM com dados do imóvel

        Returns:
            Objeto Imovel ou None se falhar
        """
        try:
            # Obtém células/campos
            colunas = await elemento.query_selector_all("td, .campo")
            
            if len(colunas) < 4:
                return None

            # Extrai dados (ajustar índices conforme HTML real)
            id_imovel = (await colunas[0].text_content()).strip()
            codigo = (await colunas[0].text_content()).strip()
            bairro = (await colunas[1].text_content()).strip().upper()
            
            # Extrai preço (remove formatação)
            preco_texto = (await colunas[2].text_content()).strip()
            preco = self._extrair_preco(preco_texto)
            
            # Link do imóvel
            link_elem = await elemento.query_selector("a[href*='imovel']")
            link = await link_elem.get_attribute("href") if link_elem else ""
            
            # URL completa se necessário
            if link and not link.startswith("http"):
                base_url = self.config.get("urls", {}).get("base_url", "https://venda-imoveis.caixa.gov.br")
                link = urljoin(base_url, link)
            
            descricao = (await colunas[3].text_content() if len(colunas) > 3 else "").strip()
            
            imovel = Imovel(
                id_imovel=id_imovel,
                codigo=codigo,
                bairro=bairro,
                preco=preco,
                descricao=descricao,
                link=link,
                modalidade="",
                cidade="",
                data_captura=datetime.now().isoformat()
            )
            
            return imovel

        except Exception as e:
            self.logger.debug(f"Erro ao extrair dados de linha: {e}")
            return None

    @staticmethod
    def _extrair_preco(texto: str) -> float:
        """
        Extrai valor numérico de preço de uma string.

        Args:
            texto: String contendo o preço formatado

        Returns:
            Valor do preço em float
        """
        try:
            # Remove tudo exceto números e ponto/vírgula
            numeros = re.sub(r"[^0-9,.\s]", "", texto)
            
            # Se houver múltiplos separadores, assume vírgula como decimal
            if numeros.count(",") > 1:
                numeros = numeros.replace(".", "").replace(",", ".")
            elif numeros.count(".") > 1:
                numeros = numeros.replace(".", "", numeros.count(".") - 1)
            else:
                # Trata vírgula como decimal
                numeros = numeros.replace(".", "").replace(",", ".")
            
            return float(numeros) if numeros else 0.0
        except (ValueError, AttributeError):
            return 0.0

    def _aplicar_filtros(self, imoveis: List[Imovel]) -> List[Imovel]:
        """
        Aplica filtros de negócio aos imóveis.

        Args:
            imoveis: Lista de imóveis para filtrar

        Returns:
            Lista de imóveis filtrados
        """
        filtros = self.config.get("filtros", {})
        preco_maximo = filtros.get("preco_maximo", 200000.0)
        bairros_alvo = {b.upper() for b in filtros.get("bairros_alvo", [])}

        imoveis_filtrados = []

        for imovel in imoveis:
            # Filtro de preço
            if imovel.preco > preco_maximo:
                self.logger.debug(f"Imóvel {imovel.id_imovel} rejeitado: preço R$ {imovel.preco}")
                continue

            # Filtro de bairro
            if imovel.bairro.upper() not in bairros_alvo:
                self.logger.debug(f"Imóvel {imovel.id_imovel} rejeitado: bairro {imovel.bairro}")
                continue

            imoveis_filtrados.append(imovel)

        self.logger.info(f"Imóveis após filtros: {len(imoveis_filtrados)} de {len(imoveis)}")
        return imoveis_filtrados

    async def processar_resultados(self, imoveis: List[Imovel]) -> Tuple[int, int]:
        """
        Processa resultados: filtra, verifica duplicidade e envia alertas.

        Args:
            imoveis: Lista de imóveis brutos da página

        Returns:
            Tupla (novos_imoveis, alertas_enviados)
        """
        # Aplica filtros
        imoveis_filtrados = self._aplicar_filtros(imoveis)
        
        novos_count = 0
        alertas_count = 0

        for imovel in imoveis_filtrados:
            # Verifica se já foi processado
            if self.db.imovel_existe(imovel.id_imovel):
                self.logger.debug(f"Imóvel já processado: {imovel.id_imovel}")
                continue

            # Insere no banco de dados
            if self.db.inserir_imovel(imovel):
                novos_count += 1

                # Envia alerta via Telegram
                if self.telegram.enviar_alerta_imovel(imovel):
                    alertas_count += 1
                else:
                    self.logger.warning(f"Falha ao enviar alerta para imóvel: {imovel.id_imovel}")

        return novos_count, alertas_count

    async def executar(self) -> Dict[str, Any]:
        """
        Executa o ciclo completo de scraping.

        Returns:
            Dicionário com estatísticas da execução
        """
        resultado = {
            "sucesso": False,
            "imoveis_encontrados": 0,
            "imoveis_filtrados": 0,
            "novos_imoveis": 0,
            "alertas_enviados": 0,
            "erro": None,
            "timestamp": datetime.now().isoformat()
        }

        try:
            await self.iniciar()
            
            # Navega e busca
            imoveis = await self.navegar_e_buscar()
            resultado["imoveis_encontrados"] = len(imoveis)
            
            if imoveis:
                # Processa resultados
                novos, alertas = await self.processar_resultados(imoveis)
                resultado["imoveis_filtrados"] = len(self._aplicar_filtros(imoveis))
                resultado["novos_imoveis"] = novos
                resultado["alertas_enviados"] = alertas
            
            # Limpeza de dados antigos
            dias_cleanup = self.config.get("database", {}).get("cleanup_days", 90)
            self.db.limpar_antigos(dias_cleanup)
            
            resultado["sucesso"] = True
            self.logger.info(f"Execução concluída com sucesso: {novos} novo(s) imóvel(ns)")

        except Exception as e:
            resultado["erro"] = str(e)
            self.logger.error(f"Erro durante execução: {e}", exc_info=True)

        finally:
            await self.fechar()

        return resultado


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

async def main() -> None:
    """
    Função principal que orquestra a execução do scraper.
    
    Fluxo:
        1. Carrega configurações
        2. Inicializa banco de dados
        3. Inicializa Telegram
        4. Executa scraper
        5. Exibe resumo
    """
    try:
        # Carrega configurações
        config = CaixaConfig()
        logger = setup_logging(config.get("logging", {}))
        
        logger.info("=" * 80)
        logger.info("Garimpeiro de Imóveis - Caixa Econômica Federal")
        logger.info(f"Inicio da execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        logger.info("=" * 80)

        # Inicializa componentes
        db = Database(
            db_path=config.get("database", {}).get("path", "database.db"),
            logger=logger
        )

        telegram = TelegramNotifier(
            token=os.getenv("TELEGRAM_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            logger=logger
        )

        # Testa conexão com Telegram (opcional)
        if os.getenv("DEBUG", "false").lower() == "true":
            logger.info("Enviando mensagem de teste Telegram...")
            telegram.enviar_teste()

        # Executa scraper
        scraper = CaixaScraper(config, db, telegram, logger)
        resultado = await scraper.executar()

        # Log do resultado
        logger.info("=" * 80)
        logger.info("RESUMO DA EXECUÇÃO:")
        logger.info(f"  Imóveis encontrados: {resultado['imoveis_encontrados']}")
        logger.info(f"  Imóveis filtrados: {resultado['imoveis_filtrados']}")
        logger.info(f"  Novos imóveis: {resultado['novos_imoveis']}")
        logger.info(f"  Alertas enviados: {resultado['alertas_enviados']}")
        
        if resultado.get("erro"):
            logger.error(f"  Erro: {resultado['erro']}")
        
        # Exibe estatísticas do banco
        stats = db.obter_estatisticas()
        if stats:
            logger.info("=" * 80)
            logger.info("ESTATÍSTICAS DO BANCO DE DADOS:")
            logger.info(f"  Total de imóveis: {stats.get('total_imoveis', 0)}")
            logger.info(f"  Preço médio: R$ {stats.get('preco_medio', 0):,.2f}")
            if stats.get("por_bairro"):
                logger.info("  Imóveis por bairro:")
                for bairro, total in sorted(stats["por_bairro"].items(), key=lambda x: x[1], reverse=True)[:5]:
                    logger.info(f"    - {bairro}: {total}")

        logger.info("=" * 80)
        logger.info(f"Fim da execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        logger.info("=" * 80)

    except Exception as e:
        logging.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

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
from typing import Optional, List, Dict, Any, Tuple, Union
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
        # Telegram é opcional - será validado durante startup se configurado
        # if not os.getenv("TELEGRAM_CREDENTIALS"):
        #     raise ValueError("TELEGRAM_CREDENTIALS não definido nas variáveis de ambiente")

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
        """Cria as tabelas necessárias se não existirem e migra se necessário."""
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
                    data_insercao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_actualizacion TIMESTAMP,
                    activo INTEGER DEFAULT 1
                )
            """)
            
            # MIGRACIÓN: Agregar columnas que falten a tabla existente
            cursor.execute("PRAGMA table_info(imoveis)")
            columns = {col[1] for col in cursor.fetchall()}
            
            # Agregar columna 'activo' si no existe
            if 'activo' not in columns:
                self.logger.info("Migrando BD: agregando columna 'activo' a tabla imoveis")
                cursor.execute("ALTER TABLE imoveis ADD COLUMN activo INTEGER DEFAULT 1")
            
            # Agregar columna 'data_actualizacion' si no existe
            if 'data_actualizacion' not in columns:
                self.logger.info("Migrando BD: agregando columna 'data_actualizacion' a tabla imoveis")
                cursor.execute("ALTER TABLE imoveis ADD COLUMN data_actualizacion TIMESTAMP")
            
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
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activo ON imoveis(activo)
            """)
            
            # Tabla de historial de cambios en imóveis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS imoveis_historial (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_imovel TEXT NOT NULL,
                    campo TEXT NOT NULL,
                    valor_anterior TEXT,
                    valor_nuevo TEXT,
                    fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tipo_cambio TEXT,
                    FOREIGN KEY (id_imovel) REFERENCES imoveis(id_imovel)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_historial_imovel ON imoveis_historial(id_imovel)
            """)
            
            conn.commit()
            self.logger.info(f"Banco de datos inicializado: {self.db_path}")

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
        Si ya existe pero estaba inactivo, lo reactiva.

        Args:
            imovel: Objeto Imovel a ser inserido

        Returns:
            True se inserido com sucesso, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Verificar si ya existe
                cursor.execute("SELECT activo FROM imoveis WHERE id_imovel = ?", (imovel.id_imovel,))
                resultado = cursor.fetchone()
                
                if resultado:
                    # Ya existe
                    activo = resultado[0]
                    if not activo:
                        # Estaba inactivo, reactivar y actualizar
                        cursor.execute("""
                            UPDATE imoveis 
                            SET preco = ?, bairro = ?, descricao = ?, 
                                modalidade = ?, data_actualizacion = ?, activo = 1
                            WHERE id_imovel = ?
                        """, (
                            imovel.preco, imovel.bairro, imovel.descricao,
                            imovel.modalidade, datetime.now().isoformat(), imovel.id_imovel
                        ))
                        self.registrar_cambio(imovel.id_imovel, "activo", 0, 1, "REACTIVACION")
                        self.logger.info(f"Imóvel reactivado: {imovel.id_imovel}")
                    return False  # No es nuevo, devolver False
                
                # Es nuevo, insertar
                cursor.execute("""
                    INSERT INTO imoveis (
                        id_imovel, codigo, bairro, preco, descricao, 
                        link, modalidade, cidade, data_captura, activo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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

    def registrar_cambio(self, id_imovel: str, campo: str, valor_anterior: Any, valor_nuevo: Any, tipo_cambio: str = "UPDATE") -> bool:
        """
        Registra un cambio en el historial de un inmueble.

        Args:
            id_imovel: ID del inmueble
            campo: Campo que cambió (ej: "preco", "modalidade")
            valor_anterior: Valor antes del cambio
            valor_nuevo: Valor después del cambio
            tipo_cambio: Tipo de cambio ("UPDATE", "REACTIVACION", etc.)

        Returns:
            True si se registró con suceso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO imoveis_historial (id_imovel, campo, valor_anterior, valor_nuevo, tipo_cambio)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_imovel, campo, str(valor_anterior), str(valor_nuevo), tipo_cambio))
                conn.commit()
                self.logger.info(f"Cambio registrado para {id_imovel}: {campo} ({valor_anterior} → {valor_nuevo})")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error al registrar cambio: {e}")
            return False

    def actualizar_imovel(self, imovel: Imovel) -> Tuple[bool, List[str]]:
        """
        Actualiza un inmueble existente si sus datos cambiaron.

        Args:
            imovel: Objeto Imovel con datos nuevos

        Returns:
            (True si se actualizó, Lista de campos que cambiaron)
        """
        campos_cambios = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener inmueble actual
                cursor.execute("""
                    SELECT preco, modalidade, bairro, descricao, activo 
                    FROM imoveis WHERE id_imovel = ?
                """, (imovel.id_imovel,))
                
                resultado = cursor.fetchone()
                if not resultado:
                    self.logger.warning(f"Inmueble {imovel.id_imovel} no encontrado para actualizar")
                    return False, []
                
                preco_anterior, modalidade_anterior, bairro_anterior, desc_anterior, activo = resultado
                
                # Detectar cambios
                if float(preco_anterior) != imovel.preco:
                    campos_cambios.append(f"preco: {preco_anterior} → {imovel.preco}")
                    self.registrar_cambio(imovel.id_imovel, "preco", preco_anterior, imovel.preco)
                
                if modalidade_anterior != imovel.modalidade:
                    campos_cambios.append(f"modalidade: {modalidade_anterior} → {imovel.modalidade}")
                    self.registrar_cambio(imovel.id_imovel, "modalidade", modalidade_anterior, imovel.modalidade)
                
                if bairro_anterior != imovel.bairro:
                    campos_cambios.append(f"bairro: {bairro_anterior} → {imovel.bairro}")
                    self.registrar_cambio(imovel.id_imovel, "bairro", bairro_anterior, imovel.bairro)
                
                if desc_anterior != imovel.descricao:
                    campos_cambios.append("descricao: ACTUALIZADA")
                    self.registrar_cambio(imovel.id_imovel, "descricao", desc_anterior[:50] if desc_anterior else "", imovel.descricao[:50] if imovel.descricao else "")
                
                # Si estaba inactivo, reactivar
                if not activo:
                    campos_cambios.append("REACTIVADO (estaba inactivo)")
                    self.registrar_cambio(imovel.id_imovel, "activo", 0, 1, "REACTIVACION")
                
                # Si hay cambios, actualizar
                if campos_cambios:
                    cursor.execute("""
                        UPDATE imoveis 
                        SET preco = ?, modalidade = ?, bairro = ?, descricao = ?, 
                            data_actualizacion = ?, activo = 1
                        WHERE id_imovel = ?
                    """, (
                        imovel.preco,
                        imovel.modalidade,
                        imovel.bairro,
                        imovel.descricao,
                        datetime.now().isoformat(),
                        imovel.id_imovel
                    ))
                    
                    conn.commit()
                    self.logger.info(f"Inmueble {imovel.id_imovel} actualizado: {', '.join(campos_cambios)}")
                    return True, campos_cambios
                
                # Sin cambios, solo reactivar si está inactivo
                if not activo:
                    cursor.execute("""
                        UPDATE imoveis SET activo = 1, data_actualizacion = ?
                        WHERE id_imovel = ?
                    """, (datetime.now().isoformat(), imovel.id_imovel))
                    conn.commit()
                    return True, ["REACTIVADO"]
                
                return False, []
                
        except sqlite3.Error as e:
            self.logger.error(f"Error al actualizar inmueble: {e}")
            return False, []

    def soft_delete_inactivos(self, ids_activos: List[str]) -> int:
        """
        Marca como inactivos los inmuebles que NO están en la lista de IDs activos.
        (Soft delete - mantiene el historial)

        Args:
            ids_activos: Lista de IDs de inmuebles encontrados en esta búsqueda

        Returns:
            Número de inmuebles marcados como inactivos
        """
        if not ids_activos:
            self.logger.warning("No hay IDs activos para comparación")
            return 0
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener inmuebles que ANTES estaban activos
                placeholders = ",".join("?" * len(ids_activos))
                cursor.execute(f"""
                    SELECT id_imovel FROM imoveis 
                    WHERE activo = 1 AND id_imovel NOT IN ({placeholders})
                """, ids_activos)
                
                inactivos = [row[0] for row in cursor.fetchall()]
                
                if inactivos:
                    # Marcar como inactivos
                    placeholders_in = ",".join("?" * len(inactivos))
                    cursor.execute(f"""
                        UPDATE imoveis 
                        SET activo = 0, data_actualizacion = ?
                        WHERE id_imovel IN ({placeholders_in})
                    """, [datetime.now().isoformat()] + inactivos)
                    
                    conn.commit()
                    
                    # Registrar cambios
                    for id_im in inactivos:
                        self.registrar_cambio(id_im, "activo", 1, 0, "SOFT_DELETE")
                    
                    self.logger.info(f"✓ {len(inactivos)} inmuebles marcados como INACTIVOS (no encontrados en búsqueda)")
                    for id_im in inactivos[:5]:  # Mostrar primeros 5
                        self.logger.debug(f"  - {id_im}")
                    if len(inactivos) > 5:
                        self.logger.debug(f"  ... y {len(inactivos) - 5} más")
                    
                    return len(inactivos)
                
                return 0
                
        except sqlite3.Error as e:
            self.logger.error(f"Error al marcar inactivos: {e}")
            return 0

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

    # Mapeamento de modalidades (número -> nome legível)
    MODALIDADES_MAP = {
        "14": "Leilão SFI - Edital Único",
        "33": "Venda Online (Melhor Oferta)",
        "34": "Venda Direta Online",
    }

    # Seletores CSS do portal (podem mudar com atualizações do site)
    SELECTORS = {
        "estado": "#cmb_estado",
        "cidade": "#cmb_cidade",
        "modalidade": "#cmb_modalidade",  # CORREGIDO: era #cmb_tipo_modalidade
        "financiamento": "#cmb_financiamento",
        "tp_imovel": "#cmb_tp_imovel",
        "quartos": "#cmb_quartos",
        "garagem": "#cmb_vg_garagem",
        "area_util": "#cmb_area_util",
        "faixa_vlr": "#cmb_faixa_vlr",
        "botao_buscar": "button:has-text('Buscar')",
        # Seletores de resultados - basado en HTML real del portal
        "contenedor_resultados": "#listaimoveispaginacao",
        "linhas_imovel": "li.group-block-item",
        "preco": "a font strong, .price, .valor",
        "bairro": ".dadosimovel-col2 font, .endereco, .localizacao",
        "link_detalle": "a[onclick*='detalhe_imovel']",
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
        """Inicia o navegador Playwright com headers de navegador real e stealth mode."""
        try:
            playwright_config = self.config.get("playwright", {})
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=playwright_config.get("headless", True),
                args=["--disable-blink-features=AutomationControlled"]
            )
            self.page = await self.browser.new_page(
                user_agent=playwright_config.get("user_agent"),
                extra_http_headers={
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Referer": "https://venda-imoveis.caixa.gov.br/",
                    "DNT": "1"
                }
            )
            
            # Hide automation indicators  
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)
            
            self.logger.info("Playwright iniciado com sucesso (stealth mode)")
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

    async def navegar_e_buscar(self) -> Union[List[Imovel], tuple]:
        """
        Navega até o portal e executa a busca em TODAS as cidades configuradas.
        Faz um loop por cidade, extraindo resultados de cada uma.

        Returns:
            Lista de imóveis encontrados em todas as cidades
        """
        imoveis_totales = []
        busca_config = self.config.get("busca", {})
        cidades = busca_config.get("cidades", [])
        
        # Loop por cada cidade
        for idx, cidade_info in enumerate(cidades):
            codigo = cidade_info.get("codigo")
            nome = cidade_info.get("nome")
            
            if not codigo:
                continue
            
            self.logger.info(f"\n=== CIUDAD {idx+1}/{len(cidades)}: {nome} ===\n")
            
            try:
                # Recargar página para cada ciudad
                url_busca = self.config.get("urls", {}).get(
                    "search_page",
                    "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp"
                )
                
                self.logger.info(f"Navegando para: {url_busca}")
                await self.page.goto(url_busca, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
                # Llenar formulario para esta ciudad específica
                await self._preencher_formulario_multistep_ciudad(nome, codigo)
                
                # Aguardar resultados
                await asyncio.sleep(self.config.get("playwright", {}).get("wait_between_requests", 2))
                
                # Extraer inmuebles (pasar ciudad actual)
                imoveis_ciudad = await self._extrair_imoveis(cidade_atual=nome)
                
                self.logger.info(f"✓ Encontrados {len(imoveis_ciudad)} inmuebles en {nome}")
                imoveis_totales.extend(imoveis_ciudad)
                
            except Exception as e:
                self.logger.error(f"Error buscando en {nome}: {e}")
                continue
        
        self.logger.info(f"\n=== TOTAL INMUEBLES EN TODAS CIUDADES: {len(imoveis_totales)} ===\n")
        return imoveis_totales

    async def _preencher_formulario_multistep_ciudad(self, cidade_nome: str, cidade_codigo: str) -> None:
        """Preenche e submete o formulário multi-step de busca para UMA CIDADE específica."""
        try:
            busca_config = self.config.get("busca", {})
            playwright_config = self.config.get("playwright", {})
            timeout = playwright_config.get("timeout", 30000)

            # Aguarda JavaScript inicial
            await asyncio.sleep(3)
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)

            # ========== ESTADO ==========
            estado = busca_config.get("estado", "PR")
            self.logger.info(f"Selecionando estado: {estado}")
            
            await self.page.wait_for_selector(self.SELECTORS["estado"], timeout=timeout)
            await self.page.select_option(self.SELECTORS["estado"], estado)
            await asyncio.sleep(1)
            
            # ========== CIUDAD ESPECÍFICA (Solo una) ==========
            self.logger.info(f"Selecionando ciudad: {cidade_nome} (código: {cidade_codigo})")
            
            try:
                await self.page.select_option(self.SELECTORS["cidade"], str(cidade_codigo))
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.warning(f"Erro ao selecionar cidade {cidade_nome}: {e}")
                return

            # ========== MODALIDADES ==========
            modalidades = busca_config.get("modalidades", [14])
            
            for modalidade in modalidades:
                self.logger.info(f"Selecionando modalidade: {modalidade}")
                
                try:
                    await self.page.select_option(self.SELECTORS["modalidade"], str(modalidade))
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.warning(f"Erro ao selecionar modalidade {modalidade}: {e}")
                    continue

            await asyncio.sleep(1)

            # ========== CLICK PRÓXIMO (Paso 1 -> 2) ==========
            self.logger.info("Navegando al paso 2")
            btn_next0 = await self.page.query_selector("#btn_next0")
            if btn_next0:
                await btn_next0.click()
                await asyncio.sleep(2)
            
            # ========== PASO 2: Sin filtros restrictivos ==========
            self.logger.info("Paso 2: Sin filtros restrictivos (trae TODOS los resultados)")
            
            # NO RELLENAR - Pasar el Paso 2 sin cambios para traer TODOS los resultados
            await asyncio.sleep(1)
            
            # CLICK PRÓXIMO (Paso 2 -> 3)
            await asyncio.sleep(1)
            btn_next1 = await self.page.query_selector("#btn_next1")
            if btn_next1:
                await btn_next1.click()
                await asyncio.sleep(2)
                
                # ========== PASO 3: Rellenar datos del cliente ==========
                self.logger.info("Paso 3: Rellenando datos del cliente")
                
                # Obtener CPF, Teléfono y Email del .env
                cpf = __import__('os').getenv("CAIXA_CPF", "").strip()
                telefone = __import__('os').getenv("CAIXA_TELEFONE", "").strip()
                email = __import__('os').getenv("CAIXA_EMAIL", "").strip()
                
                # Rellenar CPF (formato: 000.000.000-00)
                if cpf:
                    try:
                        cpf_clean = cpf.replace(".", "").replace("-", "")
                        if len(cpf_clean) == 11:
                            cpf_formatted = f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:11]}"
                        else:
                            cpf_formatted = cpf
                        
                        cpf_field = await self.page.query_selector("#txtCPF")
                        if cpf_field:
                            await cpf_field.fill(cpf_formatted)
                            self.logger.info(f"  ✓ CPF rellenado: {cpf_formatted}")
                    except Exception as e:
                        self.logger.warning(f"  Error al rellenar CPF: {e}")
                
                # Rellenar Teléfono
                if telefone:
                    try:
                        tel_field = await self.page.query_selector("#txtTelefone")
                        if tel_field:
                            await tel_field.fill(telefone)
                            self.logger.info(f"  ✓ Teléfono rellenado: {telefone}")
                    except Exception as e:
                        self.logger.warning(f"  Error al rellenar teléfono: {e}")
                
                # Rellenar Email
                if email:
                    try:
                        email_field = await self.page.query_selector("#txtEmail")
                        if email_field:
                            await email_field.fill(email)
                            self.logger.info(f"  ✓ Email rellenado: {email}")
                    except Exception as e:
                        self.logger.warning(f"  Error al rellenar email: {e}")
                
                # Validar datos del formulario
                form_values = await self.page.evaluate(r"""
                    () => ({
                        cpf: document.querySelector('#txtCPF').value,
                        telefone: document.querySelector('#txtTelefone').value,
                        email: document.querySelector('#txtEmail').value,
                        cpf_length: document.querySelector('#txtCPF').value.length,
                        telefone_length_numeric: document.querySelector('#txtTelefone').value.replace(/\D/g, '').length,
                    })
                """)
                
                self.logger.warning(f"⚠️  Form values before click: {form_values}")
                
                # Remover overlay
                await asyncio.sleep(2)
                await self.page.evaluate("() => { const overlay = document.querySelector('.ui-widget-overlay'); if (overlay) overlay.remove(); }")
                
                # CLICK ENVIAR (Paso 3 -> Resultados vía AJAX)
                btn_next2 = await self.page.query_selector("#btn_next2")
                if btn_next2:
                    await btn_next2.click()
                    
                    # Esperar a que se carguen los resultados
                    for attempt in range(20):
                        items = await self.page.query_selector_all("li.group-block-item")
                        if items:
                            self.logger.info(f"✓ Resultados cargados después de {attempt*0.5}s - {len(items)} items encontrados")
                            break
                        await asyncio.sleep(0.5)
                    
                    await asyncio.sleep(1)
        
        except Exception as e:
            self.logger.error(f"Error en _preencher_formulario_multistep_ciudad: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    async def _preencher_formulario_multistep(self) -> None:
        """Función legacy - deprecated. Usar _preencher_formulario_multistep_ciudad()"""
        pass

    async def _preencher_formulario_multistep(self) -> None:
        """Preenche e submete o formulário multi-step de busca da Caixa."""
        try:
            busca_config = self.config.get("busca", {})
            playwright_config = self.config.get("playwright", {})
            timeout = playwright_config.get("timeout", 30000)

            # Aguarda JavaScript inicial
            await asyncio.sleep(3)
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)

            # ========== PASO 1: ESTADO ==========
            estado = busca_config.get("estado", "PR")
            self.logger.info(f"Selecionando estado: {estado}")
            
            await self.page.wait_for_selector(self.SELECTORS["estado"], timeout=timeout)
            await self.page.select_option(self.SELECTORS["estado"], estado)
            await asyncio.sleep(1)
            
            # ========== CIUDADES - LOOP PRINCIPAL ==========
            cidades = busca_config.get("cidades", [])
            for cidade_info in cidades:
                codigo = cidade_info.get("codigo")
                nome = cidade_info.get("nome")
                if not codigo:
                    continue
                
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"CIUDAD: {nome} (código: {codigo})")
                self.logger.info(f"{'='*60}")
                
                try:
                    await self.page.select_option(self.SELECTORS["cidade"], str(codigo))
                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.warning(f"Erro ao selecionar cidade {nome}: {e}")
                    continue

                # ========== MODALIDADES - LOOP ANIDADO ==========
                modalidades = busca_config.get("modalidades", [34])
                
                for mod_index, modalidade in enumerate(modalidades, 1):
                    self.logger.info(f"\n[MODALIDADE {mod_index}/{len(modalidades)}] Processando modalidade: {modalidade}")
                    
                    try:
                        await self.page.select_option(self.SELECTORS["modalidade"], str(modalidade))
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        self.logger.warning(f"Erro ao selecionar modalidade {modalidade}: {e}")
                        continue

                    await asyncio.sleep(1)

                    # ========== CLICK PRÓXIMO (Paso 1 -> 2) ==========
                    self.logger.info("  Navegando al paso 2...")
                    btn_next0 = await self.page.query_selector("#btn_next0")
                    if btn_next0:
                        await btn_next0.click()
                        await asyncio.sleep(2)
                    else:
                        self.logger.warning("  Botón #btn_next0 no encontrado")
                        continue
            
# ========== PASO 2: Sin filtros restrictivos ==========
                    self.logger.info("  Paso 2: Sin filtros restrictivos (trae TODOS los resultados)")
                    await asyncio.sleep(1)
                    
                    # CLICK PRÓXIMO (Paso 2 -> 3)
                    await asyncio.sleep(1)
                    btn_next1 = await self.page.query_selector("#btn_next1")
                    if not btn_next1:
                        self.logger.warning("  Botón #btn_next1 no encontrado")
                        continue
                        
                    await btn_next1.click()
                    await asyncio.sleep(2)
                    
                    # ========== PASO 3: Rellenar dados del cliente ==========
                    self.logger.info("  Paso 3: Rellenando datos del cliente")
                    
                    # Obtener CPF, Teléfono y Email del .env
                    cpf = os.getenv("CAIXA_CPF", "").strip()
                    telefone = os.getenv("CAIXA_TELEFONE", "").strip()
                    email = os.getenv("CAIXA_EMAIL", "").strip()
                    
                    # Rellenar CPF
                    if cpf:
                        try:
                            cpf_clean = cpf.replace(".", "").replace("-", "")
                            if len(cpf_clean) == 11:
                                cpf_formatted = f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:11]}"
                            else:
                                cpf_formatted = cpf
                            
                            cpf_field = await self.page.query_selector("#txtCPF")
                            if cpf_field:
                                await cpf_field.fill(cpf_formatted)
                                self.logger.info(f"    ✓ CPF rellenado")
                        except Exception as e:
                            self.logger.warning(f"    Error rellenar CPF: {e}")
                    
                    # Rellenar Teléfono
                    if telefone:
                        try:
                            tel_field = await self.page.query_selector("#txtTelefone")
                            if tel_field:
                                await tel_field.fill(telefone)
                                self.logger.info(f"    ✓ Teléfono rellenado")
                        except Exception as e:
                            self.logger.warning(f"    Error rellenar teléfono: {e}")
                    
                    # Rellenar Email
                    if email:
                        try:
                            email_field = await self.page.query_selector("#txtEmail")
                            if email_field:
                                await email_field.fill(email)
                                self.logger.info(f"    ✓ Email rellenado")
                        except Exception as e:
                            self.logger.warning(f"    Error rellenar email: {e}")
                    
                    # Remover overlay
                    await asyncio.sleep(1)
                    try:
                        await self.page.evaluate("() => { const o = document.querySelector('.ui-widget-overlay'); if (o) o.remove(); }")
                    except:
                        pass
                    
                    # CLICK ENVIAR (Paso 3 -> Resultados)
                    btn_next2 = await self.page.query_selector("#btn_next2")
                    if btn_next2:
                        await btn_next2.click()
                        
                        # Esperar resultados
                        for attempt in range(20):
                            await asyncio.sleep(0.5)
                            items = await self.page.query_selector_all("li.group-block-item")
                            if items:
                                self.logger.info(f"  ✓ Resultados cargados: {len(items)} items")
                                break
                    
                    await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Erro ao preencher formulário: {e}")
            raise

    async def _extrair_imoveis(self, cidade_atual: str = "") -> List[Imovel]:
        """
        Extrai dados dos imóveis da página de resultados (con soporte para paginação).

        Args:
            cidade_atual: Nombre de la ciudad actual siendo buscada

        Returns:
            Lista de objetos Imovel
        """
        imoveis = []
        try:
            timeout = self.config.get("playwright", {}).get("timeout", 10000)
            
            current_url = self.page.url
            self.logger.info(f"Intentando extrair de: {current_url}")
            
            # Aguardar más tiempo para que la página se cargue completamente
            self.logger.info("Esperando 8 segundos para que los resultados se carguen completamente...")
            await asyncio.sleep(8)
            
            # GUARDAR HTML PARA COMPARACIÓN
            html_content = await self.page.content()
            with open("/tmp/scraper_resultados.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info(f"HTML guardado: {len(html_content)} bytes en /tmp/scraper_resultados.html")
            
            # Verificar que el elemento container existe
            container = await self.page.query_selector("#listaimoveispaginacao")
            if container:
                self.logger.info("✓ Container #listaimoveispaginacao detectado")
            else:
                self.logger.warning("⚠️  Container #listaimoveispaginacao NO detectado")
            
            # DEBUG: Probar cada selector directamente
            self.logger.info("=== DEBUG: PROBANDO SELECTORES ===")
            test_selectors = [
                "li.group-block-item",
                "#listaimoveispaginacao li.group-block-item",
                "#listaimoveispaginacao",
                "li[class*='group-block']",
                ".group-block-item"
            ]
            
            for test_sel in test_selectors:
                try:
                    test_items = await self.page.query_selector_all(test_sel)
                    self.logger.info(f"  Selector '{test_sel}': {len(test_items)} elementos")
                except Exception as e:
                    self.logger.info(f"  Selector '{test_sel}': ERROR - {e}")
            
            self.logger.info("=== FIN DEBUG ===\n")
            
            # MANEJO DE SCROLL INFINITO - Cargar todos los items con scroll
            # Caixa usa lazy-load: necesitamos scroll para cargar más resultados
            max_scrolls = 50  # Máximo de scrolls para evitar loops infinitos
            scroll_count = 0
            ultima_cantidad = 0
            sin_cambios_count = 0
            
            while scroll_count < max_scrolls:
                scroll_count += 1
                
                # Intentar con varios selectores para encontrar resultados
                selectors_to_try = [
                    "li.group-block-item",
                    self.SELECTORS["linhas_imovel"],
                    self.SELECTORS["contenedor_resultados"],
                    ".resultado-busca",
                    ".resultado",
                    "div[class*='resultado']",
                    ".imovel",
                    "div[class*='imovel']"
                ]
                
                linhas = []
                for selector in selectors_to_try:
                    try:
                        linhas = await self.page.query_selector_all(selector)
                        if linhas:
                            self.logger.info(f"✓ Encontrados {len(linhas)} items con selector: '{selector}'")
                            break
                    except:
                        continue
                
                # Si no encontramos items, verificar si es "no resultados"
                if not linhas:
                    page_html = await self.page.content()
                    if "Nenhum Resultado" in page_html or "nenhum resultado" in page_html.lower():
                        self.logger.warning("Página indica: Nenhum resultado encontrado")
                        break
                    
                    # Guardar HTML para análisis
                    with open("resultado_extraccion.html", "w", encoding="utf-8") as f:
                        f.write(page_html)
                    self.logger.debug("HTML guardado en resultado_extraccion.html")
                    break
                
                # Procesar los items NUEVOS (desde ultima_cantidad hasta ahora)
                self.logger.info(f"\nScroll {scroll_count}: Total {len(linhas)} items (últimos procesados: {ultima_cantidad})")
                
                for i in range(ultima_cantidad, len(linhas)):
                    try:
                        linha = linhas[i]
                        imovel = await self._extrair_dados_linha(linha, cidade_atual=cidade_atual)
                        if imovel:
                            imoveis.append(imovel)
                            self.logger.debug(f"Imóvel {i+1} extraído: {imovel.bairro}, R$ {imovel.preco}")
                    except Exception as e:
                        self.logger.debug(f"Erro ao extrair dados de línea {i}: {e}")
                        continue
                
                # Si el número de items no cambió en 3 scrolls consecutivos, probablemente terminamos
                if len(linhas) == ultima_cantidad:
                    sin_cambios_count += 1
                    if sin_cambios_count >= 3:
                        self.logger.info("✓ Sin cambios en 3 scrolls consecutivos - fin del scroll infinito")
                        break
                else:
                    sin_cambios_count = 0
                
                ultima_cantidad = len(linhas)
                
                # SCROLL DOWN para cargar más items
                try:
                    await self.page.evaluate("window.scrollBy(0, window.innerHeight);")
                    wait_time = self.config.get("playwright", {}).get("wait_between_requests", 2)
                    self.logger.info(f"  Scroll realizado, esperando {wait_time}s para cargar más...")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    self.logger.warning(f"Error al hacer scroll: {e}")
                    break
            
            self.logger.info(f"\n✓ Total de imóveles extraídos (todas las páginas): {len(imoveis)}")
            return imoveis

        except Exception as e:
            self.logger.error(f"Error general ao extrair imóveles: {e}", exc_info=True)
            return imoveis

    async def _extrair_dados_linha(self, elemento, cidade_atual: str = "") -> Optional[Imovel]:
        """
        Extrai dados de um elemento li.group-block-item.

        Args:
            elemento: Elemento HTML
            cidade_atual: Nombre de la ciudad actual siendo buscada

        Returns:
            Objeto Imovel o None si falla
        """
        try:
            self.logger.debug(f"_extrair_dados_linha() iniciado para elemento")
            
            # Extraer ID del imóvel del onclick="javascript:detalhe_imovel(ID)"
            id_imovel = ""
            img_elem = await elemento.query_selector(".fotoimovel-col1 img")
            if img_elem:
                onclick = await img_elem.get_attribute("onclick")
                if onclick:
                    # Extraer número de: javascript:detalhe_imovel(1444403577706)
                    match = re.search(r"detalhe_imovel\((\d+)\)", onclick)
                    if match:
                        id_imovel = match.group(1)
            
            # Si no encontramos ID, intentar con el link
            if not id_imovel:
                link_elem = await elemento.query_selector(".dadosimovel-col2 a[onclick*='detalhe']")
                if link_elem:
                    onclick = await link_elem.get_attribute("onclick")
                    if onclick:
                        match = re.search(r"detalhe_imovel\((\d+)\)", onclick)
                        if match:
                            id_imovel = match.group(1)
            
            if not id_imovel:
                self.logger.debug("No se pudo extraer ID del imóvel")
                return None
            
            # Extraer título y precio de la primera línea en la lista
            titulo_completo = ""
            preco_str = ""
            
            # Buscar en "TITULO | R$ PRECO" format
            title_elem = await elemento.query_selector(".dadosimovel-col2 a > span > strong > font")
            if title_elem:
                titulo_completo = await title_elem.text_content()
                titulo_completo = titulo_completo.strip()
            
            # Parsear título y precio
            # Formato: "FOZ DO IGUACU - CONJUNTO RESIDENCIAL VILLAGE SAO FRANCISCO | R$ 310.000,00"
            if titulo_completo:
                if "|" in titulo_completo:
                    partes = titulo_completo.split("|")
                    bairro_cidade = partes[0].strip() if partes else ""
                    preco_str = partes[1].strip() if len(partes) > 1 else ""
                else:
                    bairro_cidade = titulo_completo
            else:
                bairro_cidade = ""
            
            # Extraer precio
            preco = self._extrair_preco(preco_str) if preco_str else 0.0
            
            # Log detallado de precio para debugging
            if preco == 0.0 and preco_str:
                self.logger.debug(f"Precio extraído como 0.0 de texto: '{preco_str}' - ID: {id_imovel}")
            elif preco == 0.0:
                self.logger.debug(f"Precio vacío (sin preco_str) para ID: {id_imovel}")
            
            # Extraer descripción (segunda línea y siguientes)
            desc_lines = []
            # Selector correcto: todos los <font> dentro de .dadosimovel-col2
            desc_fonts = await elemento.query_selector_all(".dadosimovel-col2 font")
            for i, font_elem in enumerate(desc_fonts):
                desc_text = await font_elem.text_content()
                if desc_text.strip():
                    # Primera es el título (ya capturada), skip it
                    if i > 0:
                        desc_lines.append(desc_text.strip())
            
            descricao = " | ".join(desc_lines) if desc_lines else ""
            
            # Extraer bairro/ciudad de la descripción
            # Ejemplo: "Apartamento - 104,22 m2, 2 quarto(s), 1 vaga(s) na garagem - Leilão SFI..."
            bairro = ""
            if "na garagem" in descricao:
                # Extraer tipo de imóvel
                match = re.search(r"^([^-]+)", descricao)
                if match:
                    bairro = match.group(1).strip()
            
            # Link del imóvel - Usar endpoint local que simula detalhe_imovel()
            # Este endpoint genera un formulario con POST a Caixa
            # En producción con web.py corriendo, usar: http://localhost:5000/link-imovel/<id>
            # O si está en VPS: http://caixa.tecnofalls.com.br/link-imovel/<id>
            base_url = self.config.get("urls", {}).get("web_base_url", "http://localhost:5000")
            link = f"{base_url}/link-imovel/{id_imovel}"
            
            # Modalidad y ciudad
            busca_config = self.config.get("busca", {})
            # Mapear números de modalidad a nombres legibles
            modalidades_nums = busca_config.get("modalidades", [])
            modalidades_nombres = [
                self.MODALIDADES_MAP.get(str(m), f"Modalidad {m}") 
                for m in modalidades_nums
            ]
            modalidade = " | ".join(modalidades_nombres)
            cidade = cidade_atual  # Usar la ciudad actual pasada como parámetro
            
            # Crear objeto Imovel
            imovel = Imovel(
                id_imovel=id_imovel,
                codigo=id_imovel,  # Usar ID como código también
                bairro=bairro if bairro else bairro_cidade,
                preco=preco,
                descricao=descricao,
                link=link,
                modalidade=modalidade,
                cidade=cidade,
                data_captura=datetime.now().isoformat()
            )
            
            self.logger.debug(f"Extrato: {imovel.bairro}, R$ {imovel.preco}")
            return imovel

        except Exception as e:
            self.logger.debug(f"Erro ao extrair dados de linha: {e}")
            return None

    @staticmethod
    @staticmethod
    def _extrair_preco(texto: str) -> float:
        """
        Extrai valor numérico de preço de uma string.
        Prioriza "Valor mínimo de venda" sobre "Valor de avaliação".

        Args:
            texto: String contendo o preço formatado

        Returns:
            Valor do preço em float
        """
        if not texto:
            return 0.0
        
        try:
            # Limpieza inicial
            texto_limpio = texto.strip()
            
            # PREFERENCIA 1: Extraer "Valor mínimo de venda" (lo que se paga realmente)
            # Formato: "Valor mínimo de venda: R$ 1.453.076,60"
            match_minimo = re.search(r"Valor\s+mínimo\s+de\s+venda:\s*R\$\s*([\d.]+,\d+)", texto_limpio)
            if match_minimo:
                valor_str = match_minimo.group(1)
                valor = float(valor_str.replace(".", "").replace(",", "."))
                return valor
            
            # PREFERENCIA 2: Extraer "Valor de avaliação" (si no hay mínimo)
            # Formato: "Valor de avaliação: R$ 2.280.000,00"
            match_avaliacao = re.search(r"Valor\s+de\s+avaliação:\s*R\$\s*([\d.]+,\d+)", texto_limpio)
            if match_avaliacao:
                valor_str = match_avaliacao.group(1)
                valor = float(valor_str.replace(".", "").replace(",", "."))
                return valor
            
            # FALLBACK: Método genérico si no encuentra ninguno de los anteriores
            numeros = re.sub(r"[^0-9,.\s]", "", texto_limpio)
            
            # Si houver múltiplos separadores, assume vírgula como decimal
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
        cidades_alvo = {c.upper() for c in filtros.get("cidades_alvo", [])}

        imoveis_filtrados = []

        for imovel in imoveis:
            # Filtro: rechazar preço 0
            if imovel.preco == 0:
                self.logger.debug(f"Imóvel {imovel.id_imovel} rejeitado: preço R$ 0 (sem valor)")
                continue

            # Filtro de preço
            if imovel.preco > preco_maximo:
                self.logger.debug(f"Imóvel {imovel.id_imovel} rejeitado: preço R$ {imovel.preco}")
                continue

            # Filtro de ciudad (si especificado)
            if cidades_alvo and imovel.cidade.upper() not in cidades_alvo:
                self.logger.debug(f"Imóvel {imovel.id_imovel} rejeitado: ciudad {imovel.cidade}")
                continue

            # Filtro de bairro (solo si está especificado)
            if bairros_alvo and imovel.bairro.upper() not in bairros_alvo:
                self.logger.debug(f"Imóvel {imovel.id_imovel} rejeitado: bairro {imovel.bairro}")
                continue

            imoveis_filtrados.append(imovel)

        self.logger.info(f"Imóveis após filtros: {len(imoveis_filtrados)} de {len(imoveis)}")
        return imoveis_filtrados

    async def processar_resultados(self, imoveis: List[Imovel]) -> Tuple[int, int, List[str]]:
        """
        Processa resultados: filtra, verifica duplicidad, actualiza cambios e envia alertas.

        Args:
            imoveis: Lista de imóveis brutos da página

        Returns:
            Tupla (novos_imoveis, alertas_enviados, ids_encontrados)
        """
        # PRIMERO: Guardar/actualizar TODOS los inmuebles
        novos_count = 0
        alertas_count = 0
        ids_encontrados = []
        
        for imovel in imoveis:
            ids_encontrados.append(imovel.id_imovel)
            
            # Verifica si ya fue procesado
            if self.db.imovel_existe(imovel.id_imovel):
                # Ya existe - intentar actualizar
                atualizado, cambios = self.db.actualizar_imovel(imovel)
                if atualizado and cambios:
                    self.logger.info(f"✓ Actualizado: {imovel.id_imovel} - {', '.join(cambios)}")
                continue

            # Es nuevo - GUARDAR en BD sin aplicar filtros (guardar TODOS)
            if self.db.inserir_imovel(imovel):
                novos_count += 1
                self.logger.info(f"✓ Guardado en BD: {imovel.bairro}, R$ {imovel.preco}")
        
        # SEGUNDO: Aplicar filtros solo para mostrar alertas
        imoveis_filtrados = self._aplicar_filtros(imoveis)
        
        # Enviar alertas solo para los que pasan filtros
        if self.telegram:
            for imovel in imoveis_filtrados:
                if self.db.imovel_existe(imovel.id_imovel):  # Solo alertar los que están en BD
                    if self.telegram.enviar_alerta_imovel(imovel):
                        alertas_count += 1

        return novos_count, alertas_count, ids_encontrados

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

        novos = 0
        alertas = 0
        try:
            await self.iniciar()
            
            # Navega e busca
            imoveis = await self.navegar_e_buscar()
            resultado["imoveis_encontrados"] = len(imoveis)
            
            if imoveis:
                # Processa resultados
                novos, alertas, ids_encontrados = await self.processar_resultados(imoveis)
                resultado["imoveis_filtrados"] = len(self._aplicar_filtros(imoveis))
                resultado["novos_imoveis"] = novos
                resultado["alertas_enviados"] = alertas
                
                # SOFT DELETE: Marcar como inactivos los que NO fueron encontrados
                if ids_encontrados:
                    inativados = self.db.soft_delete_inactivos(ids_encontrados)
                    resultado["imoveis_inativados"] = inativados
            
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

        # Parse credenciais do Telegram de variáveis separadas
        token = os.getenv("TELEGRAM_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        telegram = None
        
        if token and chat_id:
            telegram = TelegramNotifier(
                token=token,
                chat_id=chat_id,
                logger=logger
            )
            # Testa conexão com Telegram (opcional)
            if os.getenv("DEBUG", "false").lower() == "true":
                logger.info("Testando conexão com Telegram...")
                try:
                    if telegram.enviar_teste():
                        logger.info("✅ Telegram conectado")
                    else:
                        logger.warning("⚠️  Falha ao enviar teste Telegram (continuando sem alertas)")
                        telegram = None
                except Exception as e:
                    logger.warning(f"⚠️  Telegram desativado: {e}")
                    telegram = None
        else:
            logger.warning("⚠️  TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não configurados - Notificações desativadas")

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

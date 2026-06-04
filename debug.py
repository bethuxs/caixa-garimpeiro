#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Ferramentas de Debug e Testes - Garimpeiro de Imóveis
================================================================================

Script auxiliar para debug, testes e validação de seletores CSS do portal.

Útil quando:
- O portal foi atualizado e os seletores não funcionam mais
- Precisa testar extrações manualmente
- Quer validar configurações antes de rodar o scraper completo

Uso:
    python debug.py test-page          # Carrega página e exibe estrutura
    python debug.py test-telegram      # Testa envio de mensagem
    python debug.py test-db            # Testa banco de dados
    python debug.py extract-selectors  # Identifica novos seletores
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
from scraper import (
    CaixaConfig, Database, TelegramNotifier, CaixaScraper,
    setup_logging, Imovel
)

# Cores para output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(texto):
    """Imprime um cabeçalho destacado."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{texto:^80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")


def print_success(texto):
    """Imprime mensagem de sucesso."""
    print(f"{Colors.GREEN}✓ {texto}{Colors.END}")


def print_error(texto):
    """Imprime mensagem de erro."""
    print(f"{Colors.RED}✗ {texto}{Colors.END}")


def print_warning(texto):
    """Imprime mensagem de aviso."""
    print(f"{Colors.YELLOW}! {texto}{Colors.END}")


def print_info(texto):
    """Imprime mensagem informativa."""
    print(f"{Colors.BLUE}ℹ {texto}{Colors.END}")


async def test_page():
    """Testa carregamento da página e exibe estrutura."""
    print_header("Teste de Carregamento de Página")
    
    try:
        config = CaixaConfig()
        logger = setup_logging(config.get("logging", {}))
        db = Database(logger=logger)
        telegram = TelegramNotifier(
            token="test",
            chat_id="test",
            logger=logger
        )
        
        scraper = CaixaScraper(config, db, telegram, logger)
        await scraper.iniciar()
        
        print_info("Navegando para página de busca...")
        url = config.get("urls", {}).get(
            "search_page",
            "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp"
        )
        
        await scraper.page.goto(url, wait_until="networkidle", timeout=30000)
        print_success(f"Página carregada: {url}")
        
        # Extrai alguns dados da página
        await scraper.page.wait_for_load_state("networkidle")
        
        # Tenta encontrar elementos
        print_info("\nInspecionando elementos da página...")
        
        # Verifica seletores
        seletores_para_testar = [
            ("Estado", "#cmb_estado"),
            ("Cidade", "#cmb_cidade"),
            ("Modalidade", "#cmb_tipo_modalidade"),
            ("Botão Buscar", "button"),
            ("Tabela Resultados", "table"),
        ]
        
        for nome, seletor in seletores_para_testar:
            try:
                elemento = await scraper.page.query_selector(seletor)
                if elemento:
                    print_success(f"{nome} encontrado: {seletor}")
                else:
                    print_warning(f"{nome} não encontrado: {seletor}")
            except Exception as e:
                print_error(f"Erro ao procurar {nome}: {e}")
        
        # Salva screenshot da página
        screenshot_file = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await scraper.page.screenshot(path=screenshot_file)
        print_success(f"Screenshot salvo: {screenshot_file}")
        
        await scraper.fechar()
        
    except Exception as e:
        print_error(f"Erro durante teste: {e}")
        sys.exit(1)


async def test_telegram():
    """Testa conexão com Telegram."""
    print_header("Teste de Conexão Telegram")
    
    try:
        config = CaixaConfig()
        logger = setup_logging(config.get("logging", {}))
        
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not token or not chat_id:
            print_error("TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não configurados")
            sys.exit(1)
        
        print_info(f"Token (primeiros 10): {token[:10]}...")
        print_info(f"Chat ID: {chat_id}")
        
        telegram = TelegramNotifier(token, chat_id, logger=logger)
        
        print_info("\nEnviando mensagem de teste...")
        sucesso = telegram.enviar_teste()
        
        if sucesso:
            print_success("Mensagem enviada com sucesso!")
        else:
            print_error("Falha ao enviar mensagem")
            sys.exit(1)
            
    except Exception as e:
        print_error(f"Erro durante teste: {e}")
        sys.exit(1)


def test_db():
    """Testa banco de dados."""
    print_header("Teste de Banco de Dados")
    
    try:
        config = CaixaConfig()
        logger = setup_logging(config.get("logging", {}))
        db = Database(logger=logger)
        
        print_success(f"Banco de dados inicializado: {db.db_path}")
        
        # Estatísticas
        stats = db.obter_estatisticas()
        print_info(f"\nEstatísticas:")
        print_info(f"  Total de imóveis: {stats.get('total_imoveis', 0)}")
        print_info(f"  Preço médio: R$ {stats.get('preco_medio', 0):,.2f}")
        
        if stats.get('por_bairro'):
            print_info(f"\n  Imóveis por bairro (Top 5):")
            for bairro, total in sorted(
                stats['por_bairro'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]:
                print_info(f"    - {bairro}: {total}")
        
        # Testa inserção
        print_info("\nTestando inserção...")
        imovel_teste = Imovel(
            id_imovel=f"TESTE_{datetime.now().timestamp()}",
            codigo="TEST001",
            bairro="TARUMÃ",
            preco=150000.00,
            descricao="Imóvel de teste",
            link="https://teste.com.br/imovel",
            modalidade="Venda Online",
            cidade="Curitiba",
            data_captura=datetime.now().isoformat()
        )
        
        if db.inserir_imovel(imovel_teste):
            print_success(f"Imóvel de teste inserido: {imovel_teste.id_imovel}")
        
        # Verifica se existe
        if db.imovel_existe(imovel_teste.id_imovel):
            print_success("Verificação de existência funcionando")
        else:
            print_error("Erro na verificação de existência")
        
        print_success("\nTestesdo banco de dados concluídos!")
        
    except Exception as e:
        print_error(f"Erro durante teste: {e}")
        sys.exit(1)


def extract_selectors():
    """Exibe os seletores atualmente configurados."""
    print_header("Seletores CSS Configurados")
    
    print_info("Seletores do CaixaScraper:")
    selectors = CaixaScraper.SELECTORS
    
    for nome, seletor in selectors.items():
        print(f"  {Colors.BOLD}{nome}{Colors.END}: {seletor}")
    
    print_info("\n\nComo encontrar novos seletores:")
    print("""
1. Abra o portal em um navegador:
   https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp

2. Pressione F12 para abrir DevTools

3. Use a ferramenta Inspecionar (Inspect Element)

4. Clique em elementos específicos para ver seus seletores:
   - ID: #id_do_elemento
   - Classe: .classe_do_elemento
   - Atributo: [atributo="valor"]
   - Tag: tag_name

5. Depois de identificar, atualize os seletores no arquivo scraper.py:
   Classe CaixaScraper, propriedade SELECTORS
    """)


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print_header("Ferramentas de Debug - Garimpeiro de Imóveis")
        print("Uso: python debug.py <comando>\n")
        print("Comandos disponíveis:")
        print("  test-page          - Testa carregamento de página")
        print("  test-telegram      - Testa conexão com Telegram")
        print("  test-db            - Testa banco de dados")
        print("  extract-selectors  - Exibe seletores configurados")
        print("")
        sys.exit(0)
    
    comando = sys.argv[1]
    
    if comando == "test-page":
        asyncio.run(test_page())
    elif comando == "test-telegram":
        asyncio.run(test_telegram())
    elif comando == "test-db":
        test_db()
    elif comando == "extract-selectors":
        extract_selectors()
    else:
        print_error(f"Comando desconhecido: {comando}")
        sys.exit(1)


if __name__ == "__main__":
    main()

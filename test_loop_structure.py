#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests estructurales del flujo ciudad-modalidade.

Validan que cada combinación se busca y extrae de forma independiente, y que el
soft delete queda limitado al alcance de la búsqueda completada.
"""

import unittest
from pathlib import Path


SCRAPER_PATH = Path(__file__).parent / "scraper.py"


def read_scraper() -> str:
    return SCRAPER_PATH.read_text(encoding="utf-8")


def function_block(content: str, signature: str, next_signature: str) -> str:
    start = content.find(signature)
    end = content.find(next_signature, start + len(signature))
    if start < 0:
        return ""
    if end < 0:
        return content[start:]
    return content[start:end]


class TestLoopStructure(unittest.TestCase):
    def test_navegar_e_buscar_processa_cada_combinacao(self):
        content = read_scraper()
        block = function_block(
            content,
            "async def navegar_e_buscar",
            "async def _preencher_formulario_multistep",
        )

        self.assertIn("for cidade_info in cidades:", block)
        self.assertIn("for mod_index, modalidade in enumerate(modalidades", block)
        self.assertIn("await self._executar_busca_combinacao(", block)
        self.assertIn("pendientes_timeout.append((cidade_info, modalidade))", block)
        self.assertIn('tentativa="reintento"', block)
        self.assertIn("escopos_completos.append(escopo)", block)

    def test_helper_ejecuta_una_combinacion(self):
        content = read_scraper()
        block = function_block(
            content,
            "async def _executar_busca_combinacao",
            "async def _preencher_formulario_multistep",
        )

        self.assertIn("await self.page.goto(url_busca", block)
        self.assertIn("await self._preencher_formulario_multistep(", block)
        self.assertIn("cidade_info=cidade_info", block)
        self.assertIn("modalidade=modalidade", block)
        self.assertIn("await self._extrair_imoveis(", block)
        self.assertIn("cidade_atual=nome_cidade", block)
        self.assertIn("modalidade_atual=modalidade_nome", block)
        self.assertIn("return imoveis, (nome_cidade, modalidade_nome)", block)
        self.assertIn("FORM_STATUS_TIMEOUT", block)
        self.assertIn("PlaywrightTimeoutError", block)

    def test_formulario_helper_no_tiene_loops_globales(self):
        content = read_scraper()
        block = function_block(
            content,
            "async def _preencher_formulario_multistep",
            "async def _extrair_imoveis",
        )

        self.assertEqual(content.count("async def _preencher_formulario_multistep"), 1)
        self.assertNotIn("for cidade_info in cidades:", block)
        self.assertNotIn("for mod_index, modalidade in enumerate(modalidades", block)
        self.assertIn('select_option(self.SELECTORS["cidade"]', block)
        self.assertIn('select_option(self.SELECTORS["modalidade"]', block)
        self.assertIn("btn_next0", block)
        self.assertIn("btn_next1", block)
        self.assertIn("btn_next2", block)
        self.assertIn("FORM_STATUS_OK", block)
        self.assertIn("FORM_STATUS_TIMEOUT", block)
        self.assertIn("FORM_STATUS_FAILED", block)

    def test_extraccion_usa_html_real_de_caixa(self):
        content = read_scraper()
        block = function_block(
            content,
            "async def _extrair_dados_linha",
            "def _extrair_preco",
        )

        self.assertIn("_parse_titulo_localizacao", content)
        self.assertIn('query_selector_all(".dadosimovel-col2 font")', block)
        self.assertIn("Valor mínimo de venda", block)
        self.assertIn("Valor de avaliação", block)
        self.assertIn("modalidade_atual", block)
        self.assertIn("preco_texto", block)
        self.assertNotIn('modalidade = " | ".join(modalidades_nombres)', block)

    def test_html_debug_so_bajo_debug(self):
        content = read_scraper()
        block = function_block(
            content,
            "async def _extrair_imoveis",
            "async def _extrair_dados_linha",
        )

        self.assertIn("self._debug_enabled()", block)
        self.assertIn("/tmp/scraper_resultados.html", block)
        self.assertNotIn('self.logger.info(f"HTML guardado', block)

    def test_soft_delete_es_por_alcance(self):
        content = read_scraper()

        self.assertIn("def soft_delete_inactivos(", content)
        self.assertIn("cidade: Optional[str] = None", content)
        self.assertIn("modalidade: Optional[str] = None", content)
        self.assertIn("cidade=cidade", content)
        self.assertIn("modalidade=modalidade", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)

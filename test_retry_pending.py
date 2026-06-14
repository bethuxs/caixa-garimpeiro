#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests del reintento final de combinaciones que vencen por timeout."""

import asyncio
import logging
import unittest
from unittest.mock import patch

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from scraper import CaixaScraper, Imovel


class DummyConfig:
    def __init__(self, busca):
        self.busca = busca

    def get(self, key, default=None):
        if key == "urls":
            return {"search_page": "https://example.test/search"}
        if key == "busca":
            return self.busca
        return default


def make_imovel(id_imovel, cidade, modalidade):
    return Imovel(
        id_imovel=id_imovel,
        codigo=id_imovel,
        bairro="CENTRO",
        preco=100000.0,
        descricao="",
        link=f"http://localhost:5000/link-imovel/{id_imovel}",
        modalidade=modalidade,
        cidade=cidade,
        data_captura="2026-06-14T00:00:00",
    )


class FakeFormElement:
    async def click(self):
        return None

    async def fill(self, value):
        return None


class NoResultsPage:
    async def wait_for_load_state(self, *args, **kwargs):
        return None

    async def wait_for_selector(self, *args, **kwargs):
        return FakeFormElement()

    async def select_option(self, *args, **kwargs):
        return None

    async def query_selector(self, selector):
        if selector in {"#btn_next0", "#btn_next1", "#btn_next2"}:
            return FakeFormElement()
        return None

    async def query_selector_all(self, selector):
        return []

    async def content(self):
        return "<div>Nenhum imóvel encontrado para o filtro selecionado.</div>"

    async def evaluate(self, *args, **kwargs):
        return None


async def no_sleep(*args, **kwargs):
    return None


class TestRetryPending(unittest.TestCase):
    def make_scraper(self, busca):
        return CaixaScraper(
            config=DummyConfig(busca),
            db=None,
            telegram=None,
            logger=logging.getLogger("test_retry_pending"),
        )

    def test_timeout_se_reintenta_al_final(self):
        scraper = self.make_scraper({
            "cidades": [
                {"codigo": "6143", "nome": "Curitiba"},
                {"codigo": "6001", "nome": "Maringa"},
            ],
            "modalidades": [34],
        })
        llamadas = []

        async def fake_execute(url_busca, cidade_info, modalidade, tentativa="principal"):
            nome = cidade_info["nome"]
            modalidade_nome = scraper._modalidade_nome(modalidade)
            llamadas.append((tentativa, nome, modalidade))

            if tentativa == "principal" and nome == "Curitiba":
                return [], None, scraper.FORM_STATUS_TIMEOUT

            imovel = make_imovel(f"{nome}-{modalidade}", nome, modalidade_nome)
            return [imovel], (nome, modalidade_nome), scraper.FORM_STATUS_OK

        scraper._executar_busca_combinacao = fake_execute

        imoveis, escopos = asyncio.run(scraper.navegar_e_buscar())

        self.assertEqual(llamadas, [
            ("principal", "Curitiba", 34),
            ("principal", "Maringa", 34),
            ("reintento", "Curitiba", 34),
        ])
        self.assertEqual([imovel.cidade for imovel in imoveis], ["Maringa", "Curitiba"])
        self.assertEqual(escopos, [
            ("Maringa", "Venda Direta Online"),
            ("Curitiba", "Venda Direta Online"),
        ])

    def test_timeout_agotado_no_completa_escopo(self):
        scraper = self.make_scraper({
            "cidades": [{"codigo": "6143", "nome": "Curitiba"}],
            "modalidades": [34],
        })
        llamadas = []

        async def fake_execute(url_busca, cidade_info, modalidade, tentativa="principal"):
            llamadas.append((tentativa, cidade_info["nome"], modalidade))
            return [], None, scraper.FORM_STATUS_TIMEOUT

        scraper._executar_busca_combinacao = fake_execute

        imoveis, escopos = asyncio.run(scraper.navegar_e_buscar())

        self.assertEqual(llamadas, [
            ("principal", "Curitiba", 34),
            ("reintento", "Curitiba", 34),
        ])
        self.assertEqual(imoveis, [])
        self.assertEqual(escopos, [])

    def test_playwright_timeout_se_reporta_como_pendiente(self):
        scraper = self.make_scraper({
            "cidades": [{"codigo": "6143", "nome": "Curitiba"}],
            "modalidades": [34],
        })

        class TimeoutPage:
            async def goto(self, *args, **kwargs):
                raise PlaywrightTimeoutError("navigation timeout")

        scraper.page = TimeoutPage()

        imoveis, escopo, status = asyncio.run(
            scraper._executar_busca_combinacao(
                url_busca="https://example.test/search",
                cidade_info={"codigo": "6143", "nome": "Curitiba"},
                modalidade=34,
            )
        )

        self.assertEqual(imoveis, [])
        self.assertIsNone(escopo)
        self.assertEqual(status, scraper.FORM_STATUS_TIMEOUT)

    def test_mensaje_sin_resultados_no_es_timeout(self):
        scraper = self.make_scraper({
            "estado": "PR",
            "cidades": [{"codigo": "6143", "nome": "Curitiba"}],
            "modalidades": [34],
        })
        scraper.page = NoResultsPage()

        with patch("scraper.async_sleep_random", no_sleep), patch("scraper.asyncio.sleep", no_sleep):
            status = asyncio.run(
                scraper._preencher_formulario_multistep(
                    cidade_info={"codigo": "6143", "nome": "Curitiba"},
                    modalidade=34,
                )
            )

        self.assertEqual(status, scraper.FORM_STATUS_OK)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests unitarios de extracción usando la estructura real del portal Caixa."""

import asyncio
import logging
import unittest

from scraper import CaixaScraper


class DummyConfig:
    def get(self, key, default=None):
        if key == "urls":
            return {"web_base_url": "http://localhost:5000"}
        return default


class FakeNode:
    def __init__(self, text="", attrs=None):
        self.text = text
        self.attrs = attrs or {}

    async def text_content(self):
        return self.text

    async def get_attribute(self, name):
        return self.attrs.get(name)


class FakeListing:
    def __init__(self, id_imovel, titulo, preco_texto, descricao):
        self.id_imovel = id_imovel
        self.titulo = titulo
        self.preco_texto = preco_texto
        self.descricao = descricao

    async def query_selector(self, selector):
        if selector == ".fotoimovel-col1 img":
            return FakeNode(attrs={"onclick": f"javascript:detalhe_imovel({self.id_imovel});"})
        if "dadosimovel-col2" in selector:
            return FakeNode(self.titulo)
        return None

    async def query_selector_all(self, selector):
        if selector == ".dadosimovel-col2 font":
            return [
                FakeNode(self.titulo),
                FakeNode(self.preco_texto),
                FakeNode(self.descricao),
            ]
        return []


class TestScraperExtraction(unittest.TestCase):
    def setUp(self):
        self.scraper = CaixaScraper(
            config=DummyConfig(),
            db=None,
            telegram=None,
            logger=logging.getLogger("test_scraper_extraction"),
        )

    def extract(self, listing, cidade="Curitiba", modalidade="Venda Direta Online"):
        return asyncio.run(
            self.scraper._extrair_dados_linha(
                listing,
                cidade_atual=cidade,
                modalidade_atual=modalidade,
            )
        )

    def test_extrai_valor_minimo_bairro_e_modalidade(self):
        listing = FakeListing(
            id_imovel="1555528553075",
            titulo="CURITIBA - TINGUI",
            preco_texto=(
                "Valor de avaliação: R$ 2.280.000,00\n"
                "Valor mínimo de venda: R$ 1.453.076,60 ( desconto de 36,27%)"
            ),
            descricao=(
                "Casa - 410,32 m2, 3 quarto(s) - Venda Direta Online\n"
                "Número do imóvel: 155552855307-5\n"
                "RUA JOAO BATISTA TRENTIN,N. 796"
            ),
        )

        imovel = self.extract(listing)

        self.assertEqual(imovel.id_imovel, "1555528553075")
        self.assertEqual(imovel.cidade, "Curitiba")
        self.assertEqual(imovel.bairro, "TINGUI")
        self.assertEqual(imovel.modalidade, "Venda Direta Online")
        self.assertAlmostEqual(imovel.preco, 1453076.60)
        self.assertNotIn("Valor mínimo de venda", imovel.descricao)
        self.assertNotIn("CURITIBA - TINGUI", imovel.descricao)

    def test_extrai_valor_avaliacao_como_fallback(self):
        listing = FakeListing(
            id_imovel="10209029",
            titulo="CURITIBA - EDIFÍCIO ZURIQUE",
            preco_texto="Valor de avaliação: R$ 1.370.000,00",
            descricao="Apartamento - Venda Direta Online\nNúmero do imóvel: 000001020902-9",
        )

        imovel = self.extract(listing)

        self.assertEqual(imovel.bairro, "EDIFÍCIO ZURIQUE")
        self.assertAlmostEqual(imovel.preco, 1370000.00)


if __name__ == "__main__":
    unittest.main(verbosity=2)

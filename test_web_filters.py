#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de filtros y ordenación de la API web."""

import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


def create_test_db() -> str:
    fd, db_path = tempfile.mkstemp(prefix="caixa_web_filters_", suffix=".db")
    os.close(fd)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE imoveis (
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
        rows = [
            ("1", "1", "CENTRO", 100000.0, "Venda Direta Online", "Curitiba"),
            ("2", "2", "TINGUI", 900000.0, "Leilão SFI - Edital Único", "Curitiba"),
            ("3", "3", "BATEL", 450000.0, "Venda Direta Online", "Curitiba"),
        ]
        for id_imovel, codigo, bairro, preco, modalidade, cidade in rows:
            conn.execute("""
                INSERT INTO imoveis
                (id_imovel, codigo, bairro, preco, descricao, link, modalidade, cidade, data_captura)
                VALUES (?, ?, ?, ?, '', ?, ?, ?, '2026-06-14T10:00:00')
            """, (
                id_imovel,
                codigo,
                bairro,
                preco,
                f"http://localhost:5000/link-imovel/{id_imovel}",
                modalidade,
                cidade,
            ))
        conn.commit()
    return db_path


def load_web(db_path: str):
    os.environ["DB_PATH"] = db_path
    os.environ["FLASK_DEBUG"] = "false"
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ.pop("CORS_ORIGINS", None)
    os.environ.pop("SYNC_API_TOKEN", None)

    if "web" in sys.modules:
        return importlib.reload(sys.modules["web"])
    return importlib.import_module("web")


class TestWebFilters(unittest.TestCase):
    def setUp(self):
        self.db_path = create_test_db()
        self.web = load_web(self.db_path)
        self.client = self.web.app.test_client()

    def tearDown(self):
        if self.db_path and Path(self.db_path).exists():
            Path(self.db_path).unlink()

    def test_menor_preco_ordena_ascendente(self):
        response = self.client.get("/api/imoveis?ordenar=preco_asc&limit=10")

        self.assertEqual(response.status_code, 200)
        precos = [imovel["preco"] for imovel in response.json["imoveis"]]
        self.assertEqual(precos, [100000.0, 450000.0, 900000.0])

    def test_valor_legado_preco_tambien_ordena_ascendente(self):
        response = self.client.get("/api/imoveis?ordenar=preco&limit=10")

        self.assertEqual(response.status_code, 200)
        precos = [imovel["preco"] for imovel in response.json["imoveis"]]
        self.assertEqual(precos, [100000.0, 450000.0, 900000.0])

    def test_maior_preco_ordena_descendente(self):
        response = self.client.get("/api/imoveis?ordenar=preco_desc&limit=10")

        self.assertEqual(response.status_code, 200)
        precos = [imovel["preco"] for imovel in response.json["imoveis"]]
        self.assertEqual(precos, [900000.0, 450000.0, 100000.0])

    def test_filtra_por_codigo_de_modalidade(self):
        response = self.client.get(
            "/api/imoveis?modalidade=34&ordenar=preco_asc&limit=10"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["total"], 2)
        self.assertEqual(
            [imovel["modalidade"] for imovel in response.json["imoveis"]],
            ["Venda Direta Online", "Venda Direta Online"],
        )
        self.assertEqual(
            [imovel["preco"] for imovel in response.json["imoveis"]],
            [100000.0, 450000.0],
        )

    def test_filtra_por_texto_de_modalidade_por_compatibilidad(self):
        response = self.client.get(
            "/api/imoveis?modalidade=Venda%20Direta%20Online&ordenar=preco_asc&limit=10"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["total"], 2)
        self.assertEqual(
            [imovel["modalidade"] for imovel in response.json["imoveis"]],
            ["Venda Direta Online", "Venda Direta Online"],
        )
        self.assertEqual(
            [imovel["preco"] for imovel in response.json["imoveis"]],
            [100000.0, 450000.0],
        )

    def test_lista_modalidades(self):
        response = self.client.get("/api/modalidades")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["modalidades"], [
            {
                "codigo": "14",
                "modalidade": "Leilão SFI - Edital Único",
                "total": 1,
            },
            {
                "codigo": "34",
                "modalidade": "Venda Direta Online",
                "total": 2,
            },
        ])


if __name__ == "__main__":
    unittest.main(verbosity=2)

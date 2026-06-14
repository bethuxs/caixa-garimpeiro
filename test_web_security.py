#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de seguridad para endpoints Flask."""

import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


def create_test_db() -> str:
    fd, db_path = tempfile.mkstemp(prefix="caixa_web_test_", suffix=".db")
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
        conn.commit()
    return db_path


def load_web(db_path: str, sync_token: str = "", debug: bool = False):
    os.environ["DB_PATH"] = db_path
    os.environ["FLASK_DEBUG"] = "true" if debug else "false"
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ.pop("CORS_ORIGINS", None)
    if sync_token:
        os.environ["SYNC_API_TOKEN"] = sync_token
    else:
        os.environ.pop("SYNC_API_TOKEN", None)

    if "web" in sys.modules:
        return importlib.reload(sys.modules["web"])
    return importlib.import_module("web")


class TestWebSecurity(unittest.TestCase):
    def tearDown(self):
        db_path = getattr(self, "db_path", None)
        if db_path and Path(db_path).exists():
            Path(db_path).unlink()

    def post_payload(self):
        return {
            "imoveis": [
                {
                    "id_imovel": "123",
                    "codigo": "123",
                    "bairro": "TINGUI",
                    "cidade": "Curitiba",
                    "preco": 100000.0,
                    "link": "http://localhost:5000/link-imovel/123",
                    "descricao": "Casa",
                    "modalidade": "Venda Direta Online",
                    "data_captura": "2026-06-14T10:00:00",
                }
            ]
        }

    def test_sync_sem_token_configurado_retorna_503(self):
        self.db_path = create_test_db()
        web = load_web(self.db_path, sync_token="")

        response = web.app.test_client().post("/api/sincronizar", json=self.post_payload())

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json["sucesso"])

    def test_sync_sem_bearer_retorna_401(self):
        self.db_path = create_test_db()
        web = load_web(self.db_path, sync_token="secret-token")

        response = web.app.test_client().post("/api/sincronizar", json=self.post_payload())

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json["sucesso"])

    def test_sync_com_bearer_valido_insere(self):
        self.db_path = create_test_db()
        web = load_web(self.db_path, sync_token="secret-token")

        response = web.app.test_client().post(
            "/api/sincronizar",
            json=self.post_payload(),
            headers={"Authorization": "Bearer secret-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["inseridos"], 1)
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM imoveis").fetchone()[0]
        self.assertEqual(total, 1)

    def test_debug_endpoint_oculto_fuera_de_debug(self):
        self.db_path = create_test_db()
        web = load_web(self.db_path, sync_token="secret-token", debug=False)

        response = web.app.test_client().get("/debug/link-imovel/123")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)

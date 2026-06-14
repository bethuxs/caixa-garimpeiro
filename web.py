#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Interface Web - Garimpeiro de Imóveis
================================================================================

Aplicação Flask para visualizar resultados do scraper via web.

URL: http://caixa.tecnofalls.com.br
Porta: 5000 (localhost) / 80 (produção com nginx)

Dependências:
    - Flask>=2.3.0
    - Flask-CORS>=4.0.0
"""

import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

DATABASE_PATH = os.getenv("DB_PATH", "database.db")
SECRET_KEY = os.getenv("SECRET_KEY", "seu_secret_key_aqui_mude_em_producao")
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = SECRET_KEY
app.config["JSON_SORT_KEYS"] = False
CORS(app)

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def get_db_connection():
    """Retorna conexão com banco de dados."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_currency(value):
    """Formata valor em reais."""
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def format_date(date_string):
    """Formata data para exibição."""
    try:
        dt = datetime.fromisoformat(date_string)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except:
        return date_string


# ============================================================================
# ROTAS DA API
# ============================================================================

@app.route("/")
def index():
    """Página principal."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total de imóveis
        cursor.execute("SELECT COUNT(*) as total FROM imoveis")
        total = cursor.fetchone()["total"]
        
        # Total da última semana
        data_semana = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ?", (data_semana,))
        semana = cursor.fetchone()["total"]
        
        # Preço médio
        cursor.execute("SELECT AVG(preco) as media FROM imoveis")
        media = cursor.fetchone()["media"] or 0
        
        # Bairros únicos
        cursor.execute("SELECT COUNT(DISTINCT bairro) as total FROM imoveis")
        bairros = cursor.fetchone()["total"]
        
        conn.close()
        
        return render_template(
            "index.html",
            total_imoveis=total,
            imoveis_semana=semana,
            preco_medio=media,
            total_bairros=bairros
        )
    except Exception as e:
        return render_template("index.html", error=str(e))


@app.route("/api/imoveis")
def api_imoveis():
    """API para listar imóveis con filtros."""
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        bairro = request.args.get("bairro", "").upper()
        cidade = request.args.get("cidade", "").upper()
        preco_min = request.args.get("preco_min", 0, type=float)
        preco_max = request.args.get("preco_max", 999999999, type=float)
        ordenar = request.args.get("ordenar", "data_insercao", type=str)
        
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query base
        query = "SELECT * FROM imoveis WHERE preco >= ? AND preco <= ?"
        params = [preco_min, preco_max]
        
        # Filtro por ciudad
        if cidade:
            query += " AND cidade LIKE ?"
            params.append(f"%{cidade}%")
        
        # Filtro por bairro
        if bairro:
            query += " AND bairro LIKE ?"
            params.append(f"%{bairro}%")
        
        # Ordenación
        ordem_permitidas = ["data_insercao", "preco", "bairro", "id_imovel", "cidade"]
        if ordenar not in ordem_permitidas:
            ordenar = "data_insercao"
        
        query += f" ORDER BY {ordenar} DESC"
        
        # Contar total
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]
        
        # Buscar datos
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        imoveis = cursor.fetchall()
        
        conn.close()
        
        # Formatar respuesta
        resultado = []
        for imovel in imoveis:
            resultado.append({
                "id_imovel": imovel["id_imovel"],
                "codigo": imovel["codigo"],
                "bairro": imovel["bairro"],
                "cidade": imovel["cidade"],
                "preco": imovel["preco"],
                "preco_formatado": format_currency(imovel["preco"]),
                "descricao": imovel["descricao"],
                "link": imovel["link"],
                "modalidade": imovel["modalidade"],
                "data_captura": format_date(imovel["data_captura"]),
                "data_insercao": format_date(imovel["data_insercao"])
            })
        
        return jsonify({
            "sucesso": True,
            "total": total,
            "pagina": page,
            "limite": limit,
            "imoveis": resultado
        })
        
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/estatisticas")
def api_estatisticas():
    """API com estatísticas gerais."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total de imóveis
        cursor.execute("SELECT COUNT(*) as total FROM imoveis")
        total = cursor.fetchone()["total"]
        
        # Por período
        data_hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        data_semana = (datetime.now() - timedelta(days=7)).isoformat()
        data_mes = (datetime.now() - timedelta(days=30)).isoformat()
        
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ?", (data_hoje,))
        hoje = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ?", (data_semana,))
        semana = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ?", (data_mes,))
        mes = cursor.fetchone()["total"]
        
        # Preços
        cursor.execute("SELECT AVG(preco) as media, MIN(preco) as minimo, MAX(preco) as maximo FROM imoveis")
        precos = cursor.fetchone()
        
        # Bairros
        cursor.execute("""
            SELECT bairro, COUNT(*) as total 
            FROM imoveis 
            GROUP BY bairro 
            ORDER BY total DESC 
            LIMIT 10
        """)
        bairros = [{"bairro": row["bairro"], "total": row["total"]} for row in cursor.fetchall()]
        
        # Cidades
        cursor.execute("""
            SELECT cidade, COUNT(*) as total 
            FROM imoveis 
            GROUP BY cidade 
            ORDER BY total DESC
        """)
        cidades = [{"cidade": row["cidade"], "total": row["total"]} for row in cursor.fetchall()]
        
        # Modalidades
        cursor.execute("""
            SELECT modalidade, COUNT(*) as total 
            FROM imoveis 
            GROUP BY modalidade
        """)
        modalidades = [{"modalidade": row["modalidade"], "total": row["total"]} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "sucesso": True,
            "total": total,
            "por_periodo": {
                "hoje": hoje,
                "semana": semana,
                "mes": mes
            },
            "precos": {
                "media": precos["media"],
                "media_formatado": format_currency(precos["media"]) if precos["media"] else "N/A",
                "minimo": precos["minimo"],
                "minimo_formatado": format_currency(precos["minimo"]) if precos["minimo"] else "N/A",
                "maximo": precos["maximo"],
                "maximo_formatado": format_currency(precos["maximo"]) if precos["maximo"] else "N/A"
            },
            "bairros": bairros,
            "cidades": cidades,
            "modalidades": modalidades
        })
        
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/bairros")
def api_bairros():
    """API para listar bairros únicos."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT bairro FROM imoveis ORDER BY bairro")
        bairros = [row["bairro"] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            "sucesso": True,
            "bairros": bairros,
            "total": len(bairros)
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/cidades")
def api_cidades():
    """API para listar ciudades únicas."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT cidade FROM imoveis ORDER BY cidade")
        cidades = [row["cidade"] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            "sucesso": True,
            "cidades": cidades,
            "total": len(cidades)
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/imovel/<id_imovel>")
def api_imovel_detalhe(id_imovel):
    """API com detalhes de um imóvel específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM imoveis WHERE id_imovel = ?", (id_imovel,))
        imovel = cursor.fetchone()
        conn.close()
        
        if not imovel:
            return jsonify({"sucesso": False, "erro": "Imóvel não encontrado"}), 404
        
        return jsonify({
            "sucesso": True,
            "imovel": {
                "id_imovel": imovel["id_imovel"],
                "codigo": imovel["codigo"],
                "bairro": imovel["bairro"],
                "cidade": imovel["cidade"],
                "preco": imovel["preco"],
                "preco_formatado": format_currency(imovel["preco"]),
                "descricao": imovel["descricao"],
                "link": imovel["link"],
                "modalidade": imovel["modalidade"],
                "data_captura": format_date(imovel["data_captura"]),
                "data_insercao": format_date(imovel["data_insercao"])
            }
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/exportar")
def api_exportar():
    """API para exportar dados em JSON."""
    try:
        filtro = request.args.get("filtro", "todos")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if filtro == "ultima_semana":
            data = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("SELECT * FROM imoveis WHERE data_insercao > ? ORDER BY data_insercao DESC", (data,))
        elif filtro == "ultimo_mes":
            data = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute("SELECT * FROM imoveis WHERE data_insercao > ? ORDER BY data_insercao DESC", (data,))
        else:
            cursor.execute("SELECT * FROM imoveis ORDER BY data_insercao DESC")
        
        imoveis = cursor.fetchall()
        conn.close()
        
        resultado = []
        for imovel in imoveis:
            resultado.append({
                "id_imovel": imovel["id_imovel"],
                "codigo": imovel["codigo"],
                "bairro": imovel["bairro"],
                "cidade": imovel["cidade"],
                "preco": imovel["preco"],
                "descricao": imovel["descricao"],
                "link": imovel["link"],
                "modalidade": imovel["modalidade"],
                "data_captura": imovel["data_captura"],
                "data_insercao": imovel["data_insercao"]
            })
        
        return jsonify({
            "sucesso": True,
            "total": len(resultado),
            "imoveis": resultado
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/sincronizar", methods=["POST"])
def api_sincronizar():
    """
    Endpoint para sincronizar imóveis do scraper local.
    
    Aceita JSON com array de imóveis:
    {
        "imoveis": [
            {
                "id_imovel": "...",
                "codigo": "...",
                "bairro": "...",
                "cidade": "...",
                "preco": 100000.00,
                "descricao": "...",
                "link": "...",
                "modalidade": "...",
                "data_captura": "2026-06-04T10:30:00"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or "imoveis" not in data:
            return jsonify({
                "sucesso": False,
                "erro": "JSON inválido. Envie: {'imoveis': [...]}"
            }), 400
        
        imoveis = data.get("imoveis", [])
        
        if not isinstance(imoveis, list):
            return jsonify({
                "sucesso": False,
                "erro": "Campo 'imoveis' deve ser uma lista"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        inseridos = 0
        duplicados = 0
        erros = []
        
        for imovel in imoveis:
            try:
                # Validação básica
                campos_obrigatorios = ["id_imovel", "codigo", "bairro", "cidade", "preco", "link"]
                if not all(k in imovel for k in campos_obrigatorios):
                    erros.append(f"Imóvel {imovel.get('id_imovel', '?')} falta campos obrigatórios")
                    continue
                
                # Tenta inserir
                cursor.execute("""
                    INSERT INTO imoveis 
                    (id_imovel, codigo, bairro, cidade, preco, descricao, link, modalidade, data_captura)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    imovel["id_imovel"],
                    imovel["codigo"],
                    imovel["bairro"],
                    imovel["cidade"],
                    float(imovel["preco"]),
                    imovel.get("descricao", ""),
                    imovel["link"],
                    imovel.get("modalidade", ""),
                    imovel.get("data_captura", datetime.now().isoformat())
                ))
                inseridos += 1
                
            except sqlite3.IntegrityError as e:
                # Link já existe (UNIQUE constraint)
                duplicados += 1
            except Exception as e:
                erros.append(f"Erro ao inserir {imovel.get('id_imovel', '?')}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "sucesso": True,
            "inseridos": inseridos,
            "duplicados": duplicados,
            "erros": erros,
            "total_processado": len(imoveis),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "sucesso": False,
            "erro": f"Erro ao processar requisição: {str(e)}"
        }), 500


@app.route("/health")
def health():
    """Verificar saúde da aplicação."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM imoveis")
        total = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            "status": "OK",
            "timestamp": datetime.now().isoformat(),
            "banco_dados": DATABASE_PATH,
            "total_imoveis": total
        })
    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "erro": str(e)
        }), 500


# ============================================================================
# TRATAMENTO DE ERROS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Página não encontrada."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    """Erro interno do servidor."""
    return render_template("500.html"), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Verificar se banco de dados existe
    if not Path(DATABASE_PATH).exists():
        print(f"⚠️  Banco de dados não encontrado: {DATABASE_PATH}")
        print("Execute o scraper primeiro para criar o banco de dados.")
    
    # Rodar aplicação
    port = int(os.getenv("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=DEBUG,
        threaded=True
    )

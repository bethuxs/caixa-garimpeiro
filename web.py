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
import json
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
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE activo = 1")
        total = cursor.fetchone()["total"]
        
        # Total da última semana
        data_semana = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ? AND activo = 1", (data_semana,))
        semana = cursor.fetchone()["total"]
        
        # Preço médio
        cursor.execute("SELECT AVG(preco) as media FROM imoveis WHERE activo = 1")
        media = cursor.fetchone()["media"] or 0
        
        # Bairros únicos
        cursor.execute("SELECT COUNT(DISTINCT bairro) as total FROM imoveis WHERE activo = 1")
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
        
        # Query base - SOLO INMUEBLES ACTIVOS
        query = "SELECT * FROM imoveis WHERE activo = 1 AND preco >= ? AND preco <= ?"
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
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE activo = 1")
        total = cursor.fetchone()["total"]
        
        # Por período
        data_hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        data_semana = (datetime.now() - timedelta(days=7)).isoformat()
        data_mes = (datetime.now() - timedelta(days=30)).isoformat()
        
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ? AND activo = 1", (data_hoje,))
        hoje = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ? AND activo = 1", (data_semana,))
        semana = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM imoveis WHERE data_insercao > ? AND activo = 1", (data_mes,))
        mes = cursor.fetchone()["total"]
        
        # Preços
        cursor.execute("SELECT AVG(preco) as media, MIN(preco) as minimo, MAX(preco) as maximo FROM imoveis WHERE activo = 1")
        precos = cursor.fetchone()
        
        # Bairros
        cursor.execute("""
            SELECT bairro, COUNT(*) as total 
            FROM imoveis 
            WHERE activo = 1
            GROUP BY bairro 
            ORDER BY total DESC 
            LIMIT 10
        """)
        bairros = [{"bairro": row["bairro"], "total": row["total"]} for row in cursor.fetchall()]
        
        # Cidades
        cursor.execute("""
            SELECT cidade, COUNT(*) as total 
            FROM imoveis 
            WHERE activo = 1
            GROUP BY cidade 
            ORDER BY total DESC
        """)
        cidades = [{"cidade": row["cidade"], "total": row["total"]} for row in cursor.fetchall()]
        
        # Modalidades
        cursor.execute("""
            SELECT modalidade, COUNT(*) as total 
            FROM imoveis 
            WHERE activo = 1
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
        cursor.execute("SELECT DISTINCT bairro FROM imoveis WHERE activo = 1 ORDER BY bairro")
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
        cursor.execute("SELECT DISTINCT cidade FROM imoveis WHERE activo = 1 ORDER BY cidade")
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
        cursor.execute("SELECT * FROM imoveis WHERE id_imovel = ? AND activo = 1", (id_imovel,))
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


@app.route("/link-imovel/<id_imovel>")
def link_imovel(id_imovel):
    """
    Redirige al detalle del imóvel en Caixa usando POST (detalhe_imovel()).
    
    Este endpoint genera un formulario HTML que auto-submit para simular
    lo que sucede cuando se hace click en un imóvel en el portal Caixa.
    El formulario llena los hidden fields y hace POST a detalhe-imovel.asp.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM imoveis WHERE id_imovel = ? AND activo = 1", (id_imovel,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return render_template("404.html"), 404
        
        # Convertir row a diccionario usando cursor.description
        cols_names = [description[0] for description in cursor.description]
        imovel = dict(zip(cols_names, row))
        
        # Retornar HTML con formulario auto-submit que simula detalhe_imovel()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Carregando detalhes...</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f0f0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; font-size: 24px; margin-bottom: 10px; }}
                p {{ color: #666; margin-bottom: 20px; }}
                .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔄 Carregando detalhes...</h1>
                <p>Redirecionando para a página de detalhes do imóvel {id_imovel}</p>
                <div class="spinner"></div>
                <p style="font-size: 12px; color: #999; margin-top: 30px;">Se não for redirecionado automaticamente, <a href="#" onclick="document.getElementById('frmlista').submit(); return false;">clique aqui</a></p>
            </div>
            
            <form id="frmlista" method="POST" action="https://venda-imoveis.caixa.gov.br/sistema/venda-online/detalhe-imovel.asp" style="display:none;">
                <input type="hidden" id="hdnimovel" name="hdnimovel" value="{imovel.get('id_imovel', id_imovel)}">
                <input type="hidden" id="hdn_estado" name="hdn_estado" value="PR">
                <input type="hidden" id="hdn_cidade" name="hdn_cidade" value="{imovel.get('cidade', '')}">
                <input type="hidden" id="hdn_modalidade" name="hdn_modalidade" value="{imovel.get('modalidade', '')}">
                <input type="hidden" id="hdn_tp_imovel" name="hdn_tp_imovel" value="">
                <input type="hidden" id="hdn_quartos" name="hdn_quartos" value="">
                <input type="hidden" id="hdn_vg_garagem" name="hdn_vg_garagem" value="">
                <input type="hidden" id="hdn_area_util" name="hdn_area_util" value="">
                <input type="hidden" id="hdn_faixa_vlr" name="hdn_faixa_vlr" value="">
                <input type="hidden" id="hdn_vlr_maximo" name="hdn_vlr_maximo" value="{imovel.get('preco', '')}">
                <input type="hidden" id="hdnValorSimulador" name="hdnValorSimulador" value="">
                <input type="hidden" id="hdnAceitaFGTS" name="hdnAceitaFGTS" value="">
                <input type="hidden" id="hdnAceitaFinanciamento" name="hdnAceitaFinanciamento" value="">
                <input type="hidden" id="hdnOrigem" name="hdnOrigem" value="buscaimovel">
                <input type="hidden" id="hdnSalvarDadosCliente" name="hdnSalvarDadosCliente" value="N">
            </form>
            
            <script>
            // Función para hacer submit del formulario
            function submitForm() {{
                var form = document.getElementById('frmlista');
                if (form) {{
                    console.log('Enviando formulario POST a Caixa...');
                    form.submit();
                }} else {{
                    console.error('Formulario no encontrado');
                }}
            }}
            
            // Esperar a que el documento esté completamente cargado
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    setTimeout(submitForm, 300);
                }});
            }} else {{
                // El documento ya está cargado
                setTimeout(submitForm, 300);
            }}
            </script>
        </body>
        </html>
        """
        
        return html, 200, {'Content-Type': 'text/html; charset=UTF-8'}
        
    except Exception as e:
        return render_template("500.html"), 500


@app.route("/debug/link-imovel/<id_imovel>")
def debug_link_imovel(id_imovel):
    """
    Endpoint de debug: Muestra los datos del formulario SIN auto-submit
    para verificar que los valores se están rellenando correctamente.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM imoveis WHERE id_imovel = ? AND activo = 1", (id_imovel,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return render_template("404.html"), 404
        
        # Convertir row a diccionario usando cursor.description
        cols_names = [description[0] for description in cursor.description]
        imovel = dict(zip(cols_names, row))
        
        # DEBUG HTML que MUESTRA el formulario sin auto-submit
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DEBUG: Datos del Formulario</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; }}
                h1 {{ color: #333; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                td {{ border: 1px solid #ddd; padding: 10px; }}
                td:first-child {{ background: #f9f9f9; font-weight: bold; width: 30%; }}
                .imovel-data {{ background: #e3f2fd; padding: 10px; margin: 20px 0; border-radius: 3px; }}
                .form-data {{ background: #fff3e0; padding: 10px; margin: 20px 0; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 DEBUG: Endpoint /link-imovel/{id_imovel}</h1>
                
                <h2>Datos del Inmueble (BD):</h2>
                <div class="imovel-data">
                    <table>
                        <tr><td>ID Inmueble</td><td>{imovel.get('id_imovel', 'N/A')}</td></tr>
                        <tr><td>Ciudad</td><td>{imovel.get('cidade', 'N/A')}</td></tr>
                        <tr><td>Modalidad</td><td>{imovel.get('modalidade', 'N/A')}</td></tr>
                        <tr><td>Precio</td><td>R$ {imovel.get('preco', 'N/A')}</td></tr>
                        <tr><td>Bairro</td><td>{imovel.get('bairro', 'N/A')}</td></tr>
                        <tr><td>Código</td><td>{imovel.get('codigo', 'N/A')}</td></tr>
                        <tr><td>Activo</td><td>{imovel.get('activo', 'N/A')}</td></tr>
                    </table>
                </div>
                
                <h2>Datos del Formulario (que se enviarán a Caixa):</h2>
                <div class="form-data">
                    <table>
                        <tr><td>hdnimovel</td><td>{imovel.get('id_imovel', id_imovel)}</td></tr>
                        <tr><td>hdn_estado</td><td>PR</td></tr>
                        <tr><td>hdn_cidade</td><td>{imovel.get('cidade', '')}</td></tr>
                        <tr><td>hdn_modalidade</td><td>{imovel.get('modalidade', '')}</td></tr>
                        <tr><td>hdn_vlr_maximo</td><td>{imovel.get('preco', '')}</td></tr>
                    </table>
                </div>
                
                <h2>Acciones:</h2>
                <ul>
                    <li><a href="/link-imovel/{id_imovel}">► Enviar formulario a Caixa (auto-submit)</a></li>
                    <li><a href="/">← Volver al inicio</a></li>
                </ul>
                
                <h2>JSON (para debugging):</h2>
                <pre style="background: #f5f5f5; padding: 10px; overflow-x: auto;">
{json.dumps(imovel, indent=2, default=str)}
                </pre>
            </div>
        </body>
        </html>
        """
        
        return html, 200, {'Content-Type': 'text/html; charset=UTF-8'}
        
    except Exception as e:
        return render_template("500.html"), 500


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

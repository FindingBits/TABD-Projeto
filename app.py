from flask import Flask, render_template
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Configurações da Base de Dados
DB_HOST = "localhost"
DB_NAME = "eleicoes_db"      
DB_USER = "teste"        
DB_PASS = "admin123" 
DB_PORT = "5432"

def get_db_connection():
    """Estabelece uma ligação segura com a base de dados PostgreSQL/PostGIS."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Erro ao ligar à Base de Dados: {e}")
        return None

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/selecao')
def selecao():
    # Lista organizada: primeiro as Legislativas, depois as Presidenciais
    eleicoes = [
        # AUTÁRQUICAS
        {"nome": "Autárquicas 2025", "ano": "2025", "tipo": "Autárquica", "icon": "bi-houses"},
        {"nome": "Autárquicas 2021", "ano": "2021", "tipo": "Autárquica", "icon": "bi-houses"},
        {"nome": "Autárquicas 2017", "ano": "2017", "tipo": "Autárquica", "icon": "bi-houses"}
    ]
    return render_template('selecao.html', eleicoes=eleicoes)

# No teu ficheiro Flask (app.py)
@app.route('/api/municipios/<distrito_id>')
def get_municipios(distrito_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query que junta os dados espaciais com os resultados da votação
    query = """
        SELECT 
            id, name, 
            ST_AsGeoJSON(geom)::json AS geometry
        FROM concelhos_caop
        WHERE id_distrito = %s;
    """
    cursor.execute(query, (distrito_id,))
    features = cursor.fetchall()
    
    # Monta o formato padrão GeoJSON para o Leaflet ler
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": f[2],
                "properties": {"id": f[0], "name": f[1]}
            } for f in features
        ]
    }
    return jsonify(geojson)

@app.route('/detalhes/<nome_eleicao>')
def detalhes(nome_eleicao):
    conn = get_db_connection()
    if conn is None:
        return "Erro interno: Não foi possível ligar à base de dados.", 500
    
    try:
        '''cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query_info = "SELECT vencedor, descricao, total_eleitores FROM eleicoes WHERE nome = %s;"
        cursor.execute(query_info, (nome_eleicao,))
        info_eleicao = cursor.fetchone()
        
        query_mandatos = "SELECT partido, mandatos FROM resultados_partidos WHERE nome_eleicao = %s;"
        cursor.execute(query_mandatos, (nome_eleicao,))
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not info_eleicao:
            info_eleicao = {
                "vencedor": "A definir", 
                "descricao": "Sem descrição disponível.", 
                "total_eleitores": "0"
            }
        
        info_formatada = {
            "vencedor": info_eleicao["vencedor"],
            "descricao": info_eleicao["descricao"],
            "mandatos": {r["partido"]: r["mandatos"] for r in resultados}
        }
        
        return render_template('detalhes.html', nome=nome_eleicao, info=info_formatada)'''
        info_formatada = {
            "vencedor": "Quim",
            "descricao": "O Quim Ganhou",
            "mandatos": {
                "Partido do Quim": 5,  # Agora é um dicionário fake!
                "Outro Partido": 2
            }
        }
        return render_template('detalhes.html', nome="Autárquicas 2025", info=info_formatada)
        
    except Exception as e:
        if conn: conn.close()
        return f"Erro ao executar a query: {e}", 500
        


@app.route('/api/mapa/distritos')
def api_distritos():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Query que transforma a geometria para EPSG:4326 (Web) e gera GeoJSON
    query = """
        SELECT 
            dt AS codigo,
            distrito AS nome,
            ST_AsGeoJSON(ST_Transform(geometry, 4326))::json AS geojson
        FROM public.stg_caop_distritos;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Monta a estrutura oficial FeatureCollection do GeoJSON
    geojson_features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": row["geojson"],
                "properties": {"codigo": row["codigo"], "nome": row["nome"], "tipo": "distrito"}
            } for row in rows
        ]
    }
    return jsonify(geojson_features)

@app.route('/api/mapa/municipios/<codigo_distrito>')
def api_municipios(codigo_distrito):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Não foi possível ligar à base de dados"}), 500
        
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Query ajustada às colunas reais: dtmn e municipio
        query = """
            SELECT 
                municipio AS nome,
                ST_AsGeoJSON(ST_Transform(geometry, 4326))::json AS geojson
            FROM public.stg_caop_municipios
            WHERE SUBSTRING(dtmn, 1, 2) = %s;
        """
        cursor.execute(query, (codigo_distrito,))
        rows = cursor.fetchall()
        
        geojson_features = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": row["geojson"],
                    "properties": {"nome": row["nome"], "tipo": "municipio"}
                } for row in rows
            ]
        }
        return jsonify(geojson_features)

    except Exception as e:
        print(f"❌ Erro na Query dos Municípios: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
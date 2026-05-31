from flask import Flask, render_template
import random
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# =========== Configurações da Base de Dados ================
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

# =============================================

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

@app.route('/about')
def about():
    status_db = False
    versao_db = "Desconectado"
    versao_postgis = "Não disponível"
    
    try:
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            
            # Teste 1: Obter versão do PostgreSQL
            cursor.execute("SELECT version();")
            versao_db = cursor.fetchone()[0].split(',')[0] # Simplifica a string da versão
            
            # Teste 2: Obter versão do PostGIS
            cursor.execute("SELECT PostGIS_Full_Version();")
            versao_postgis = cursor.fetchone()[0].split(']')[0] + ']'
            
            status_db = True
            cursor.close()
            conn.close()
    except Exception as e:
        versao_db = f"Erro de ligação: {str(e)}"
        status_db = False

    return render_template(
        'about.html', 
        status_db=status_db, 
        versao_db=versao_db, 
        versao_postgis=versao_postgis
    )

# ================================================================

# ==========================================
# ROTA 1: Visão Geral de Portugal (Página HTML)
# ==========================================
@app.route('/detalhes/<int:ano>')
def detalhes_ano(ano):
    conn = get_db_connection()
    if conn is None:
        return "Erro interno de base de dados.", 500
        
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Procurar métricas agregadas de TODO o país para o ano selecionado
        query_nacional = """
            SELECT 
                COUNT(DISTINCT municipality_code) AS total_municipios,
                SUM(registered_voters) AS inscritos,
                SUM(voters) AS votantes,
                SUM(blank_votes) AS brancos,
                SUM(null_votes) AS nulos
            FROM public.turnout t
            JOIN public.elections e ON t.election_id = e.election_id
            WHERE e.election_year = %s;
        """
        cursor.execute(query_nacional, (ano,))
        stats = cursor.fetchone()
        
        if not stats or stats['total_municipios'] == 0:
            return f"Não existem dados carregados para o ano {ano}.", 404

        # Obter os votos totais nacionais de cada partido para preencher a tabela inicial
        query_votos_nacionais = """
            SELECT acronym, SUM(votes) AS total_votes FROM (
                SELECT p.acronym, pc.votes FROM public.party_candidacies pc
                JOIN public.parties p ON pc.party_id = p.party_id
                JOIN public.elections e ON pc.election_id = e.election_id WHERE e.election_year = %s
                UNION ALL
                SELECT c.acronym, cc.votes FROM public.coalition_candidacies cc
                JOIN public.coalitions c ON cc.coalition_id = c.coalition_id
                JOIN public.elections e ON cc.election_id = e.election_id WHERE e.election_year = %s
                UNION ALL
                SELECT cg.acronym, cgc.votes FROM public.citizen_group_candidacies cgc
                JOIN public.citizen_groups cg ON cgc.citizen_group_id = cg.citizen_group_id
                JOIN public.elections e ON cgc.election_id = e.election_id WHERE e.election_year = %s
            ) total_nacional
            GROUP BY acronym ORDER BY total_votes DESC;
        """
        cursor.execute(query_votos_nacionais, (ano, ano, ano))
        resultados = cursor.fetchall()
        
        vencedor = resultados[0]["acronym"] if resultados else "N/A"
        
        info_formatada = {
            "vencedor": vencedor,
            "descricao": f"Resultados Consolidados Nacionais para a totalidade do território.",
            "inscritos": stats["inscritos"],
            "votantes": stats["votantes"],
            "brancos": stats["brancos"],
            "nulos": stats["nulos"],
            "mandatos": {r["acronym"]: r["total_votes"] for r in resultados} # No HTML mudamos o texto de 'Lugares' para 'Votos'
        }
        
        return render_template('detalhes.html', ano=ano, nome="Portugal", info=info_formatada)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# ROTA 2: API para Nível de Distrito (JSON)
# ==========================================
@app.route('/api/eleicao/<int:ano>/distrito/<string:codigo_distrito>')
def api_dados_distrito(ano, codigo_distrito):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Agrega os dados apenas das freguesias/concelhos pertencentes ao distrito clicado
        query_stats = """
            SELECT SUM(registered_voters) as inscritos, SUM(voters) as votantes,
                   SUM(blank_votes) as brancos, SUM(null_votes) as nulos
            FROM public.turnout t
            JOIN public.elections e ON t.election_id = e.election_id
            WHERE e.election_year = %s AND SUBSTRING(t.municipality_code, 1, 2) = %s;
        """
        cursor.execute(query_stats, (ano, codigo_distrito))
        stats = cursor.fetchone()

        query_votos = """
            SELECT acronym, SUM(votes) AS total_votes FROM (
                SELECT p.acronym, pc.votes FROM public.party_candidacies pc
                JOIN public.parties p ON pc.party_id = p.party_id
                JOIN public.elections e ON pc.election_id = e.election_id WHERE e.election_year = %s AND SUBSTRING(pc.municipality_code, 1, 2) = %s
                UNION ALL
                SELECT c.acronym, cc.votes FROM public.coalition_candidacies cc
                JOIN public.coalitions c ON cc.coalition_id = c.coalition_id
                JOIN public.elections e ON cc.election_id = e.election_id WHERE e.election_year = %s AND SUBSTRING(cc.municipality_code, 1, 2) = %s
            ) total_distrital GROUP BY acronym ORDER BY total_votes DESC;
        """
        cursor.execute(query_votos, (ano, codigo_distrito, ano, codigo_distrito))
        resultados = cursor.fetchall()
        
        return jsonify({
            "vencedor": resultados[0]["acronym"] if resultados else "N/A",
            "inscritos": stats["inscritos"] or 0,
            "votantes": stats["votantes"] or 0,
            "brancos": stats["brancos"] or 0,
            "nulos": stats["nulos"] or 0,
            "votos_forcas": {r["acronym"]: r["total_votes"] for r in resultados}
        })
    finally:
        cursor.close()
        conn.close()

# ==========================================
# ROTA 3: API para Nível de Município (JSON)
# ==========================================
@app.route('/api/eleicao/<int:ano>/municipio/<string:codigo_municipio>')
def api_dados_municipio(ano, codigo_municipio):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query_stats = """
            SELECT t.registered_voters as inscritos, t.voters as votantes,
                   t.blank_votes as brancos, t.null_votes as nulos
            FROM public.turnout t
            JOIN public.elections e ON t.election_id = e.election_id
            WHERE e.election_year = %s AND t.municipality_code = %s;
        """
        cursor.execute(query_stats, (ano, codigo_municipio))
        stats = cursor.fetchone()

        query_votos = """
            SELECT acronym, votes FROM (
                SELECT p.acronym, pc.votes FROM public.party_candidacies pc
                JOIN public.parties p ON pc.party_id = p.party_id
                JOIN public.elections e ON pc.election_id = e.election_id WHERE e.election_year = %s AND pc.municipality_code = %s
                UNION ALL
                SELECT c.acronym, cc.votes FROM public.coalition_candidacies cc
                JOIN public.coalitions c ON cc.coalition_id = c.coalition_id
                JOIN public.elections e ON cc.election_id = e.election_id WHERE e.election_year = %s AND cc.municipality_code = %s
            ) total_municipal ORDER BY votes DESC;
        """
        cursor.execute(query_votos, (ano, codigo_municipio, ano, codigo_municipio))
        resultados = cursor.fetchall()

        return jsonify({
            "inscritos": stats["inscritos"] if stats else 0,
            "votantes": stats["votantes"] if stats else 0,
            "brancos": stats["brancos"] if stats else 0,
            "nulos": stats["nulos"] if stats else 0,
            "votos_forcas": {r["acronym"]: r["votes"] for r in resultados}
        })
    finally:
        cursor.close()
        conn.close()



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
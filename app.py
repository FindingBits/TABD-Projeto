from flask import Flask, render_template, jsonify
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import plotly
import plotly.express as px
import json

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

# ===========================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/selecao')
def selecao():
    eleicoes = [
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
            
            cursor.execute("SELECT version();")
            versao_db = cursor.fetchone()[0].split(',')[0]
            
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
# ROTAS DE DADOS ELEITORAIS (Adaptadas ao teu Novo Schema)
# ================================================================

@app.route('/detalhes/<int:ano>')
def detalhes_ano(ano):
    conn = get_db_connection()
    if conn is None:
        return "Erro interno de base de dados.", 500
        
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query_nacional = """
            SELECT 
                COUNT(DISTINCT municipality_code) AS total_municipios,
                SUM(registered_voters) AS inscritos,
                SUM(voters) AS votantes,
                SUM(blank_votes) AS brancos,
                SUM(null_votes) AS nulos
            FROM public.turnout
            WHERE election_year = %s;
        """
        cursor.execute(query_nacional, (ano,))
        stats = cursor.fetchone()
        
        if not stats or stats['total_municipios'] == 0:
            return f"Não existem dados carregados para o ano {ano}.", 404

        # 1. Nova Query incluindo o campo logo_url
        query_votos_nacionais = """
            SELECT acronym, SUM(votes) AS total_votes, MAX(logo_url) AS logo_url FROM (
                SELECT p.acronym, pc.votes, p.logo_url
                FROM public.party_candidacies pc
                JOIN public.parties p ON pc.party_id = p.party_id
                WHERE pc.election_year = %s
                
                UNION ALL
                
                SELECT cc.acronym, cc.votes, '' AS logo_url 
                FROM public.coalition_candidacies cc
                WHERE cc.election_year = %s
                
                UNION ALL
                
                SELECT cgc.acronym, cgc.votes, '' AS logo_url 
                FROM public.citizen_group_candidacies cgc
                WHERE cgc.election_year = %s
            ) total_nacional
            GROUP BY acronym ORDER BY total_votes DESC;
        """
        cursor.execute(query_votos_nacionais, (ano, ano, ano))
        resultados = cursor.fetchall()
        
        vencedor = resultados[0]["acronym"] if resultados else "N/A"
        
        # 2. IMPORTANTE: Modificar a estrutura que passas para o HTML.
        # Em vez de passar apenas {acronimo: votos}, passamos uma lista de dicionários com todos os dados.
        info_formatada = {
            "vencedor": vencedor,
            "descricao": f"Resultados Consolidados Nacionais para a totalidade do território.",
            "inscritos": stats["inscritos"],
            "votantes": stats["votantes"],
            "brancos": stats["brancos"],
            "nulos": stats["nulos"],
            "lista_resultados": [
                {
                    "acronym": r["acronym"],
                    "votos": r["total_votes"],
                    "logo_url": r["logo_url"] if r["logo_url"] else "/static/assets/default_logo.avif" # Imagem padrão se for coligação
                } for r in resultados
            ]
        }
        
        return render_template('detalhes.html', ano=ano, nome="Portugal", info=info_formatada)
    finally:
        cursor.close()
        conn.close()


@app.route('/api/eleicao/<int:ano>/distrito/<string:codigo_distrito>')
def api_dados_distrito(ano, codigo_distrito):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Erro interno de ligação à base de dados."}), 500
        
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Convertemos o "01" recebido do mapa para um inteiro (1) de forma segura.
        # Se falhar, assume 0 para não rebentar com a query.
        try:
            distrito_id_int = int(codigo_distrito)
        except ValueError:
            distrito_id_int = 0

        # Query de estatísticas atualizada para usar a coluna 'district' (INTEGER)
        query_stats = """
            SELECT SUM(t.registered_voters) as inscritos, SUM(t.voters) as votantes,
                   SUM(t.blank_votes) as brancos, SUM(t.null_votes) as nulos
            FROM public.turnout t
            JOIN public.municipalities m ON t.municipality_code = m.code
            WHERE t.election_year = %s AND m.district = %s;
        """
        cursor.execute(query_stats, (ano, distrito_id_int))
        stats = cursor.fetchone()

        # Query de votos atualizada:
        # 1. Usa a coluna 'district' no JOIN.
        # 2. Vai buscar a 'logo_url' da tabela dos partidos (usando string vazia para coligações/grupos).
        query_votos = """
            SELECT acronym, SUM(votes) AS total_votes, MAX(logo_url) AS logo_url FROM (
                SELECT p.acronym, pc.votes, p.logo_url
                FROM public.party_candidacies pc
                JOIN public.parties p ON pc.party_id = p.party_id
                JOIN public.municipalities m ON pc.municipality_code = m.code
                WHERE pc.election_year = %s AND m.district = %s
                
                UNION ALL
                
                SELECT cc.acronym, cc.votes, '' AS logo_url 
                FROM public.coalition_candidacies cc
                JOIN public.municipalities m ON cc.municipality_code = m.code
                WHERE cc.election_year = %s AND m.district = %s
                
                UNION ALL
                
                SELECT cgc.acronym, cgc.votes, '' AS logo_url 
                FROM public.citizen_group_candidacies cgc
                JOIN public.municipalities m ON cgc.municipality_code = m.code
                WHERE cgc.election_year = %s AND m.district = %s
            ) total_distrital GROUP BY acronym ORDER BY total_votes DESC;
        """
        cursor.execute(query_votos, (ano, distrito_id_int, ano, distrito_id_int, ano, distrito_id_int))
        resultados = cursor.fetchall()
        
        # Estrutura o JSON de resposta incluindo a lista de forças políticas com os seus logos
        return jsonify({
            "vencedor": resultados[0]["acronym"] if resultados else "N/A",
            "inscritos": stats["inscritos"] or 0,
            "votantes": stats["votantes"] or 0,
            "brancos": stats["brancos"] or 0,
            "nulos": stats["nulos"] or 0,
            "votos_forcas": {r["acronym"]: r["total_votes"] for r in resultados},
            "lista_resultados": [
                {
                    "acronym": r["acronym"],
                    "votos": r["total_votes"],
                    "logo_url": r["logo_url"] if r["logo_url"] else "/static/images/default_logo.avif"
                } for r in resultados
            ]
        })
    except Exception as e:
        print(f"❌ Erro na Rota do Distrito: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/eleicao/<int:ano>/municipio/<string:codigo_municipio>')
def api_dados_municipio(ano, codigo_municipio):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Erro de ligação."}), 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query_stats = """
            SELECT t.registered_voters as inscritos, t.voters as votantes,
                   t.blank_votes as brancos, t.null_votes as nulos
            FROM public.turnout t
            WHERE t.election_year = %s AND t.municipality_code = %s;
        """
        cursor.execute(query_stats, (ano, codigo_municipio))
        stats = cursor.fetchone()

        query_votos = """
            SELECT acronym, votes, MAX(logo_url) AS logo_url FROM (
                SELECT p.acronym, pc.votes, p.logo_url 
                FROM public.party_candidacies pc
                JOIN public.parties p ON pc.party_id = p.party_id
                WHERE pc.election_year = %s AND pc.municipality_code = %s
                
                UNION ALL
                
                SELECT cc.acronym, cc.votes, '' AS logo_url 
                FROM public.coalition_candidacies cc
                WHERE cc.election_year = %s AND cc.municipality_code = %s
                
                UNION ALL
                
                SELECT cgc.acronym, cgc.votes, '' AS logo_url 
                FROM public.citizen_group_candidacies cgc
                WHERE cgc.election_year = %s AND cgc.municipality_code = %s
            ) total_municipal GROUP BY acronym, votes ORDER BY votes DESC;
        """
        cursor.execute(query_votos, (ano, codigo_municipio, ano, codigo_municipio, ano, codigo_municipio))
        resultados = cursor.fetchall()

        return jsonify({
            "vencedor": resultados[0]["acronym"] if resultados else "N/A",  # <- ADICIONAR ESTA LINHA
            "inscritos": stats["inscritos"] if stats else 0,
            "votantes": stats["votantes"] if stats else 0,
            "brancos": stats["brancos"] if stats else 0,
            "nulos": stats["nulos"] if stats else 0,
            "votos_forcas": {r["acronym"]: r["votes"] for r in resultados},
            "lista_resultados": [
                {
                    "acronym": r["acronym"],
                    "votos": r["votes"],
                    "logo_url": r["logo_url"] if r["logo_url"] else "/static/images/default_logo.png"
                } for r in resultados
            ]
        })
    finally:
        cursor.close()
        conn.close()

# ================================================================
# ROTAS GEOGRÁFICAS (Adaptadas para ler as tuas tabelas stg_caop_*)
# ================================================================

@app.route('/api/municipios/<string:distrito_id>')
def get_municipios(distrito_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Adaptado: Alinhado com as colunas reais da tua tabela stg_caop_municipios 
    # e usando o VARCHAR (string) do teu distrito para fazer o corte dos 2 primeiros dígitos.
    query = """
        SELECT 
            dtmn, municipio, 
            ST_AsGeoJSON(ST_Transform(geometry, 4326))::json AS geometry
        FROM geo.stg_caop_municipios
        WHERE SUBSTRING(dtmn, 1, 2) = %s;
    """
    cursor.execute(query, (distrito_id,))
    features = cursor.fetchall()
    
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
    
    # Mantido a tabela 'stg_caop_distritos' garantindo que o tipo de dados
    # mapeia corretamente para o teu front-end.
    query = """
        SELECT 
            dt AS codigo,
            distrito AS nome,
            ST_AsGeoJSON(ST_Transform(geometry, 4326))::json AS geojson
        FROM geo.stg_caop_distritos;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
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


@app.route('/api/mapa/municipios/<string:codigo_distrito>')
def api_municipios(codigo_distrito):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Não foi possível ligar à base de dados"}), 500
        
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Corrigido o tipo do parâmetro da rota de <codigo_distrito> para string.
        # Isto garante que o SUBSTRING do PostGIS avalie corretamente o texto de 2 dígitos.
        query = """
            SELECT 
                dtmn AS codigo,
                municipio AS nome,
                ST_AsGeoJSON(ST_Transform(geometry, 4326))::json AS geojson
            FROM geo.stg_caop_municipios
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
                    "properties": {"codigo": row["codigo"], "nome": row["nome"], "tipo": "municipio"}
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

@app.route('/analise')
def pagina_analise():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Gráfico 1: Evolução da Abstenção Média por Distrito 
        query_abstencao = """
            SELECT m.district_name, ROUND(AVG(f.abstention_rate), 2) AS media_abstencao
            FROM dw.fact_turnout_analysis f
            JOIN dw.dim_municipality m ON f.municipality_code = m.municipality_code
            WHERE m.district_name IS NOT NULL
            GROUP BY m.district_name
            ORDER BY media_abstencao DESC;
        """
        cursor.execute(query_abstencao)
        dados_abs = cursor.fetchall()
        
        fig1 = px.bar(dados_abs, x='district_name', y='media_abstencao', 
                      title="Abstenção Média por Distrito (%)",
                      labels={'district_name': 'Distrito', 'media_abstencao': '% Abstenção'})
        grafico_abstencao_json = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)

        # Gráfico 2: Share de Votos Total Nacional por Força Política (Usando o DW)
        query_forcas = """
            SELECT 
                c.candidacy_acronym, 
                SUM(f.votes) AS total_votos
            FROM dw.fact_election_results f
            JOIN dw.dim_candidacy c ON f.candidacy_key = c.candidacy_key
            GROUP BY c.candidacy_acronym
            ORDER BY total_votos DESC
            LIMIT 7;
        """
        cursor.execute(query_forcas)
        dados_votos = cursor.fetchall()
        
        fig2 = px.pie(dados_votos, names='candidacy_acronym', values='total_votos', 
                      title="Distribuição Global de Votos Apurados")
        grafico_votos_json = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)

        # QUERY AVANÇADA EXTRA: Simulação do Método D'Hondt Real 
        query_dhondt = """
            WITH RECURSIVE divisores AS (
                SELECT 1 AS divisor
                UNION ALL
                SELECT divisor + 1 FROM divisores WHERE divisor < 20
            ),
            quocientes AS (
                SELECT 
                    m.municipality_name,
                    c.candidacy_acronym,
                    f.votes / d.divisor AS quociente,
                    ROW_NUMBER() OVER (PARTITION BY m.municipality_name ORDER BY (f.votes / d.divisor) DESC) as rn
                FROM dw.fact_election_results f
                JOIN dw.dim_municipality m ON f.municipality_code = m.municipality_code
                JOIN dw.dim_candidacy c ON f.candidacy_key = c.candidacy_key
                JOIN dw.fact_turnout_analysis t ON f.municipality_code = t.municipality_code AND f.election_year = t.election_year
                CROSS JOIN divisores d
                WHERE m.municipality_name = 'Ourém' AND f.election_year = 2021 -- Exemplo estático para demonstração
            )
            SELECT candidacy_acronym, COUNT(*) as mandatos_calculados_dhondt
            FROM quocientes
            WHERE rn <= 7 -- Número de mandatos total de Ourém em 2021
            GROUP BY candidacy_acronym
            ORDER BY mandatos_calculados_dhondt DESC;
        """
        cursor.execute(query_dhondt)
        resultados_dhondt = cursor.fetchall()

        return render_template('analise.html', 
                               grafico_abstencao=grafico_abstencao_json, 
                               grafico_votos=grafico_votos_json,
                               resultados_dhondt=resultados_dhondt)
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
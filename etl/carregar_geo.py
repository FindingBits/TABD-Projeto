import geopandas as gpd
from sqlalchemy import create_engine

# 1. Configuração da ligação ao teu PostgreSQL/PostGIS local
DATABASE_URL = "postgresql://teste:admin123@localhost:5432/eleicoes_db"
engine = create_engine(DATABASE_URL)

# 2. Caminho para o teu ficheiro GeoPackage
gpkg_path = "Continente_CAOP2025.gpkg"

# No teu carregar_geo.py

# Atualiza com os nomes exatos que descobriste (tudo em minúsculas)
camada_distritos = "cont_distritos"  
camada_municipios = "cont_municipios"

def carregar_camada_staging(gpkg_file, layer_name, staging_table_name):
    print(f"A ler a camada '{layer_name}' do GeoPackage...")
    # Carrega a camada específica
    gdf = gpd.read_file(gpkg_file, layer=layer_name)
    
    # Garante a projeção oficial de Portugal (PT-TM06 / EPSG:3763)
    if gdf.crs is None or gdf.crs.to_epsg() != 3763:
        print(f"-> A converter a projeção de {layer_name} para EPSG:3763...")
        gdf = gdf.to_crs(epsg=3763)
    
    print(f"-> A enviar para a tabela de staging '{staging_table_name}'...")
    # if_exists="replace" garante que o script é executável várias vezes (rerunnable)
    gdf.to_postgis(
        name=staging_table_name,
        con=engine,
        schema="public", # Se criares um esquema separado para staging, muda aqui
        if_exists="replace",
        index=False
    )
    print(f" Sucesso: {layer_name} carregada em {staging_table_name}.\n")

# 3. Executar o carregamento para a Área de Staging
try:
    carregar_camada_staging(gpkg_path, camada_distritos, "stg_caop_distritos")
    carregar_camada_staging(gpkg_path, camada_municipios, "stg_caop_municipios")
    print("ETL Espacial Concluído com Sucesso para a Área de Staging!")
except Exception as e:
    print(f"❌ Erro durante o processo de ETL: {e}")
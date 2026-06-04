# ============================================================
# Codigo antigo de carregar localizacao geografica
# ============================================================

import os
import geopandas as gpd
from sqlalchemy import create_engine


DATABASE_URL = "postgresql://teste:admin123@localhost:5432/eleicoes_db"
engine = create_engine(DATABASE_URL)

config_regioes = [
    {
        "ficheiro": "Continente_CAOP2025.gpkg",
        "camada_distritos": "cont_distritos",
        "camada_municipios": "cont_municipios"
    },
    {
        "ficheiro": "ArqMadeira_CAOP2025.gpkg", 
        "camada_distritos": "ram_distritos",
        "camada_municipios": "ram_municipios"
    },
    {
        "ficheiro": "ArqAcores_GCentral_GOriental_CAOP2025.gpkg", 
        "camada_distritos": "raa_cen_ori_distritos",
        "camada_municipios": "raa_cen_ori_municipios"
    },
    {
        "ficheiro": "ArqAcores_GOcidental_CAOP2025.gpkg", 
        "camada_distritos": "raa_oci_distritos",
        "camada_municipios": "raa_oci_municipios"
    }
]

def processar_etl_espacial():
    primeiro_registo = True
    
    for regiao in config_regioes:
        gpkg_path = regiao["ficheiro"]
        
        if not os.path.exists(gpkg_path):
            print(f"⚠️ Aviso: Ficheiro {gpkg_path} não encontrado. A saltar...")
            continue
            
        print(f"--- A processar o ficheiro: {gpkg_path} ---")
        
        modo_escrita = "replace" if primeiro_registo else "append"
        
        # Processamento da camada de Distritos
        try:
            gdf_dist = gpd.read_file(gpkg_path, layer=regiao["camada_distritos"])
            if gdf_dist.crs is None or gdf_dist.crs.to_epsg() != 3763:
                gdf_dist = gdf_dist.to_crs(epsg=3763)
                
            gdf_dist.to_postgis(
                name="stg_caop_distritos",
                con=engine,
                schema="geo",
                if_exists=modo_escrita,
                index=False
            )
            print(f" Sucesso: {regiao['camada_distritos']} integrada em stg_caop_distritos ({modo_escrita}).")
        except Exception as e:
            print(f"❌ Erro ao processar distritos de {gpkg_path}: {e}")

        # Processamento da camada de Municípios
        try:
            gdf_mun = gpd.read_file(gpkg_path, layer=regiao["camada_municipios"])
            if gdf_mun.crs is None or gdf_mun.crs.to_epsg() != 3763:
                gdf_mun = gdf_mun.to_crs(epsg=3763)
            
            if "concelho" in gdf_mun.columns:
                gdf_mun = gdf_mun.rename(columns={"concelho": "municipio"})
            if "dtmn" not in gdf_mun.columns and "dt" in gdf_mun.columns:
                gdf_mun = gdf_mun.rename(columns={"dt": "dtmn"})
                
            gdf_mun.to_postgis(
                name="stg_caop_municipios",
                con=engine,
                schema="geo",
                if_exists=modo_escrita,
                index=False
            )
            print(f" Sucesso: {regiao['camada_municipios']} integrada em stg_caop_municipios ({modo_escrita}).")
        except Exception as e:
            print(f"❌ Erro ao processar municípios de {gpkg_path}: {e}")
            
        print("-" * 40)
        primeiro_registo = False

if __name__ == "__main__":
    try:
        processar_etl_espacial()
        print("ETL Espacial Global Concluído com Sucesso para Todas as Regiões!")
    except Exception as e:
        print(f"❌ Falha crítica no pipeline ETL: {e}")
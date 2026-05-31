# The Portuguese Voting Crypt

Este projeto é uma plataforma de análise eleitoral desenvolvida com Flask, PostgreSQL e PostGIS. O repositório contém pipelines de ETL para dados geográficos (CAOP) e de votação, além de uma interface web baseada em mapas dinâmicos (Leaflet).

## Pré-requisitos

PostgreSQL 17 instalado e em execução no sistema antes de iniciar.

## Instalação e Configuração do Ambiente

1. Instalar todas as bibliotecas necessárias
```python
pip install flask geopandas sqlalchemy geoalchemy2 psycopg2-binary shapely fiona
```

## Configuração da Base de Dados

1. Acede ao terminal do PostgreSQL:
   `psql -d template1`

2. Executa os seguintes comandos SQL para preparar a base de dados:
   - `CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'admin123';`
   - `CREATE DATABASE eleicoes_db;`
   - `\c eleicoes_db;`
   - `CREATE EXTENSION postgis;`
   - `\q`

3. Restaurar de um backup:
   - `pg_restore -U postgres -d eleicoes_db -v eleicoes_db_backup.dump`

4. Restaurar um schema:
   - `psql -U postgres -d eleicoes_db -f "elections_schema.sql"` - Sendo necessário depois carregar dados do excel com o script `carregar_excel.py`

## Execução dos Pipelines de ETL

1. Executa o script de carregamento dos dados geográficos do GeoPackage para a área de staging:
   `python carregar_geo.py`

## Execução da Aplicação Web

1. Inicia o servidor local do Flask:
   `python app.py`

2. Abre o navegador e acede ao endereço indicado no terminal: http://127.0.0.1:5000.
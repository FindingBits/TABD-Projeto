# The Portuguese Voting Crypt

Este projeto é uma plataforma de análise eleitoral desenvolvida com Flask, PostgreSQL e PostGIS. O repositório contém pipelines de ETL para dados geográficos (CAOP) e de votação, além de uma interface web baseada em mapas dinâmicos (Leaflet).

## Pré-requisitos

Garante que tens o PostgreSQL 17 instalado e em execução no sistema antes de iniciar.

## Instalação e Configuração do Ambiente

1. Instala todas as bibliotecas necessárias via pip:
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

## Execução dos Pipelines de ETL

1. Executa o script de carregamento dos dados geográficos do GeoPackage para a área de staging:
   python carregar_geo.py

## Execução da Aplicação Web

1. Inicia o servidor local do Flask:
   python app.py

2. Abre o navegador e acede ao endereço indicado no terminal (normalmente http://127.0.0.1:5000).
# The Portuguese Voting Crypt

Este projeto é uma plataforma de análise eleitoral desenvolvida com Flask, PostgreSQL e PostGIS. O repositório contém pipelines de ETL para dados geográficos (CAOP) e de votação, além de uma interface web baseada em mapas dinâmicos (Leaflet).

## Pré-requisitos

PostgreSQL 17 instalado e em execução no sistema antes de iniciar.

Juntar conteúdos de tamanho grande (copiar diretamente para a raiz) em: [Download](https://mega.nz/folder/JMgHWQLZ#4Ze89K0mHMEYgErQLsR-sg)

## Instalação e Configuração do Ambiente

1. Instalar todas as bibliotecas necessárias
```python
pip install flask geopandas sqlalchemy geoalchemy2 psycopg2-binary shapely fiona plotly
```

## Configuração da Base de Dados

1. Aceder ao terminal do PostgreSQL:
   `psql -d template1`

2. Executar os seguintes comandos SQL para preparar a base de dados e user:
   - `CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'admin123';`
   - `CREATE DATABASE eleicoes_db;`
   - `\c eleicoes_db;`
   - `CREATE EXTENSION postgis;`
   - `\q`

4. Restaurar o schema:
   - `psql -U postgres -d eleicoes_db -f "schema_data.sql"`

## Execução dos Pipelines de ETL

1. Executar o script de carregamento dos dados geográficos do GeoPackage (dentro da pasta etl):
   `python carregar_geo.py`

## Execução da Aplicação Web

1. Iniciar o servidor local do Flask:
   `python app.py`

2. Abrir o navegador e aceder ao endereço indicado no terminal: http://127.0.0.1:5000

3. Páginas disponíveis (navegável usando barra superior de navegação)
- Dashboard (`index.html`)
- Selection (`selecao.html`)
- Details (for every year, not accessible directly, only by `Selection`) (`detalhes.html`)
- Analise (`analise.html`)
- About (`about.html`)

## Execução da Data Warehouse

1. Carregar o schema.
`psql -h localhost -U postgres -d eleicoes_db -f sql/dw_schema.sql`

2. Aceder ao terminal da db.
`psql -h localhost -p 5432 -U postgres -d eleicoes_db`

3. Colar no terminal conteudos de `popular_dw.sql`.

4. Chamar PROCEDURE.
`CALL dw.popular_data_warehouse();`

5. Testar DW
`SELECT * FROM dw.fact_turnout_analysis LIMIT 5;`

6. Executar qualquer uma das query em `query.sql`.
# ============================================================
# Codigo antigo de ler excel...
# ============================================================

import os
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://teste:admin123@localhost:5432/eleicoes_db"
engine = create_engine(DATABASE_URL)

EXCEL_FILE = "mapa_1_resultados.xlsx" 
ELECTION_YEAR = 2021
ELECTION_DATE = "2021-09-26"
ELECTION_DESC = "Eleições Autárquicas 2021"

xl = pd.ExcelFile(EXCEL_FILE)
print(f"Folhas encontradas no Excel: {xl.sheet_names}")

df_teste = pd.read_excel(EXCEL_FILE)
print(f"Primeiras 20 linhas detetadas pelo Pandas:\n{df_teste.head(20)}")
print(f"Cabeçalhos de colunas detetados: {list(df_teste.columns)}")

import sys; sys.exit("Fim.")
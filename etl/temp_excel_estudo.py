import os
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Database Connection
DATABASE_URL = "postgresql://teste:admin123@localhost:5432/eleicoes_db"
engine = create_engine(DATABASE_URL)

# 2. Configuration for this run
EXCEL_FILE = "mapa_1_resultados.xlsx"  # Change to your actual file name
ELECTION_YEAR = 2021
ELECTION_DATE = "2021-09-26"
ELECTION_DESC = "Eleições Autárquicas 2021"

print("📖 Entrando em modo Diagnóstico do Excel...")

# 1. Ver que folhas existem no ficheiro
xl = pd.ExcelFile(EXCEL_FILE)
print(f"📄 Folhas encontradas no Excel: {xl.sheet_names}")

# 2. Ler a primeira folha para espreitar as colunas
df_teste = pd.read_excel(EXCEL_FILE)
print(f"📋 Primeiras 20 linhas detetadas pelo Pandas:\n{df_teste.head(20)}")
print(f"🏷️ Cabeçalhos de colunas detetados: {list(df_teste.columns)}")

# Parar a execução aqui para poderes ver o resultado no terminal
import sys; sys.exit("🏁 Fim do diagnóstico. Analisa os dados acima!")
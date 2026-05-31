import os
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Database Connection
DATABASE_URL = "postgresql://teste:admin123@localhost:5432/eleicoes_db"
engine = create_engine(DATABASE_URL)

# 2. Configuration
EXCEL_FILE = "mapa_1_resultados.xlsx"  # Garante que o nome bate certo
ELECTION_YEAR = 2021
ELECTION_DATE = "2021-09-26"
ELECTION_DESC = "Eleições Autárquicas 2021 - Câmara Municipal"

def run_elections_etl():
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: Excel file '{EXCEL_FILE}' not found.")
        return

    print("📖 Reading Excel file...")
    # Lemos mantendo o skiprows=2 para alinhar com os dados
    df = pd.read_excel(EXCEL_FILE, skiprows=2)
    
    # Uniformizar nomes das colunas para maiúsculas e remover espaços
    df.columns = [str(c).strip().upper() for c in df.columns]

    print(f"✅ Cabeçalhos base identificados: {list(df.columns)[:8]}")

    # ======================================================================
    # LISTA NEGRA: Barricada absoluta contra títulos macro e metadados
    # ======================================================================
    lista_negra_partidos = [
        'ELEIÇÃO', 'UNNAMED: 1', 'UNNAMED: 2', 'ÓRG', 'INSC', 'VOT', 'BR', 'NUL', 
        'MANDATOS', 'TOTAL_MANDATOS', 'NAN', 
        'PARTIDOS', 'COLIGAÇÕES', 'GCE',           # 🛑 Os 3 grandes impostores do teu print!
        'SIGLAS COLIGAÇÕES', 'SIGLAS GCE'          # Ignorar colunas de controle macro
    ]

    # Captura apenas os partidos puros (Colunas I a AJ, correspondente aos índices 8 a 35)
    # filtrando ativamente qualquer elemento da lista negra ou colunas fantasma do Pandas
    party_columns = [
        c for c in df.columns[8:36] 
        if c not in lista_negra_partidos and "UNNAMED" not in c
    ]

    with engine.begin() as conn:
        print("⚡ Core infrastructure active. Injecting metadata...")

        # STAGE 1: Garantir Eleição
        conn.execute(
            text("""
                INSERT INTO elections (election_year, election_date, description)
                VALUES (:year, :date, :desc)
                ON CONFLICT (election_year) DO UPDATE SET description = EXCLUDED.description;
            """), {"year": ELECTION_YEAR, "date": ELECTION_DATE, "desc": ELECTION_DESC}
        )
        election_id = conn.execute(
            text("SELECT election_id FROM elections WHERE election_year = :year"),
            {"year": ELECTION_YEAR}
        ).scalar()

        # STAGE 2: Sincronizar CAOP
        print("🌍 Syncing districts and municipalities from CAOP staging...")
        conn.execute(text("""
            INSERT INTO districts (code, name)
            SELECT DISTINCT dt, distrito FROM public.stg_caop_distritos ON CONFLICT (code) DO NOTHING;
        """))
        conn.execute(text("""
            INSERT INTO municipalities (code, district_code, name)
            SELECT DISTINCT dtmn, SUBSTRING(dtmn, 1, 2), municipio FROM public.stg_caop_municipios ON CONFLICT (code) DO NOTHING;
        """))

        # STAGE 3: Registar Partidos Puros (I-AJ)
        print("🏷️ Registering pure political parties...")
        for acronym in party_columns:
            conn.execute(
                text("INSERT INTO parties (acronym, name) VALUES (:acronym, :name) ON CONFLICT (acronym) DO NOTHING;"),
                {"acronym": acronym, "name": f"Partido {acronym}"}
            )

        # STAGE 4 & 5: Processamento das Linhas
        print("📊 Injecting metrics and dynamic candidacies...")
        for idx, row in df.iterrows():
            raw_code = row.get('ELEIÇÃO')
            if pd.isna(raw_code):
                continue
                
            raw_code_str = str(raw_code).strip().split('.')[0].zfill(6)
            
            # Filtrar Totais de Distrito
            if raw_code_str.endswith('0000'):
                continue
                
            # Validar Concelhos (6 dígitos terminados em 00)
            if raw_code_str.endswith('00') and len(raw_code_str) == 6:
                mun_code = raw_code_str[:4]
                nome_concelho = str(row.get('UNNAMED: 1')).strip().upper()

                # Ignorar linhas de cabeçalho intermédio sem votos reais
                if pd.isna(row.get('INSC')) or pd.isna(row.get('VOT')):
                    continue

                # Garantir que estamos a ler o órgão de Câmara Municipal (CM)
                if str(row.get('ÓRG')).strip().upper() != 'CM':
                    continue

                print(f"✅ Mapped -> Concelho: {nome_concelho} | Code: {mun_code}")

                # INSERT Turnout
                conn.execute(
                    text("""
                        INSERT INTO turnout (
                            election_id, municipality_code, registered_voters, 
                            voters, blank_votes, null_votes, total_mandates
                        ) VALUES (:election_id, :mun_code, :reg, :vot, :blank, :null, :mand)
                        ON CONFLICT (election_id, municipality_code) DO UPDATE SET
                            registered_voters = EXCLUDED.registered_voters,
                            voters = EXCLUDED.voters,
                            blank_votes = EXCLUDED.blank_votes,
                            null_votes = EXCLUDED.null_votes;
                    """),
                    {
                        "election_id": election_id,
                        "mun_code": mun_code,
                        "reg": int(row.get('INSC', 0)),
                        "vot": int(row.get('VOT', 0)),
                        "blank": int(row.get('BR', 0)),
                        "null": int(row.get('NUL', 0)),
                        "mand": int(row.get('MANDATOS', 7))
                    }
                )

                # ---- PROCESSAR VOTOS: 1. PARTIDOS PUROS (I até AJ) ----
                for entity in party_columns:
                    try:
                        v_raw = row.get(entity, 0)
                        votes = int(float(str(v_raw).strip())) if not pd.isna(v_raw) and str(v_raw).strip() != '' else 0
                    except:
                        votes = 0

                    if votes > 0:
                        party_id = conn.execute(
                            text("SELECT party_id FROM parties WHERE acronym = :acronym"), 
                            {"acronym": entity}
                        ).scalar()
                        
                        if party_id:
                            conn.execute(text("""
                                INSERT INTO party_candidacies (election_id, municipality_code, party_id, votes)
                                VALUES (:e_id, :m_code, :p_id, :votes)
                                ON CONFLICT (election_id, municipality_code, party_id) DO UPDATE SET votes = EXCLUDED.votes;
                            """), {"e_id": election_id, "m_code": mun_code, "p_id": party_id, "votes": votes})

                # ---- PROCESSAR VOTOS: 2. COLIGAÇÕES (Coluna AK) ----
                # Vamos buscar os votos da coluna 'SIGLAS COLIGAÇÕES'
                col_votes_raw = row.get('SIGLAS COLIGAÇÕES', 0)
                try:
                    col_votes = int(float(str(col_votes_raw).strip())) if not pd.isna(col_votes_raw) and str(col_votes_raw).strip() != '' else 0
                except:
                    col_votes = 0

                if col_votes > 0:
                    # Capturamos a sigla real que o pandas guardou na coluna seguinte correspondente
                    # Ao remover skiprows=2, a célula com a sigla (ex: [PPD/PSD.MPT]) fica na coluna UNNAMED: 36
                    sigla_coligacao = str(row.get('UNNAMED: 36', 'COLIG_LOCAL')).replace('[','').replace(']','').strip()
                    
                    if sigla_coligacao and sigla_coligacao != 'NAN':
                        # Registar coligação dinamicamente se não existir
                        conn.execute(text("""
                            INSERT INTO coalitions (acronym, name) 
                            VALUES (:acronym, :name) ON CONFLICT (acronym, name) DO NOTHING;
                        """), {"acronym": sigla_coligacao, "name": f"Coligação {sigla_coligacao}"})
                        
                        coalition_id = conn.execute(
                            text("SELECT coalition_id FROM coalitions WHERE acronym = :acronym LIMIT 1"), 
                            {"acronym": sigla_coligacao}
                        ).scalar()

                        if coalition_id:
                            conn.execute(text("""
                                INSERT INTO coalition_candidacies (election_id, municipality_code, coalition_id, votes)
                                VALUES (:e_id, :m_code, :c_id, :votes)
                                ON CONFLICT (election_id, municipality_code, coalition_id) DO UPDATE SET votes = EXCLUDED.votes;
                            """), {"e_id": election_id, "m_code": mun_code, "c_id": coalition_id, "votes": col_votes})

                # ---- PROCESSAR VOTOS: 3. GRUPOS DE CIDADÃOS - GCE (Coluna AL) ----
                gce_votes_raw = row.get('SIGLAS GCE', 0)
                try:
                    gce_votes = int(float(str(gce_votes_raw).strip())) if not pd.isna(gce_votes_raw) and str(gce_votes_raw).strip() != '' else 0
                except:
                    gce_votes = 0

                if gce_votes > 0:
                    # Capturamos a sigla do Grupo de Cidadãos na coluna UNNAMED: 37
                    sigla_gce = str(row.get('UNNAMED: 37', 'GCE_LOCAL')).replace('[','').replace(']','').strip()
                    
                    if sigla_gce and sigla_gce != 'NAN':
                        # Registar Grupo de Cidadãos
                        conn.execute(text("""
                            INSERT INTO citizen_groups (acronym, name, municipality_code)
                            VALUES (:acronym, :name, :m_code) ON CONFLICT (acronym, municipality_code) DO NOTHING;
                        """), {"acronym": sigla_gce, "name": f"Grupo Cidadãos {sigla_gce}", "m_code": mun_code})
                        
                        cg_id = conn.execute(text("""
                            SELECT citizen_group_id FROM citizen_groups WHERE acronym = :acronym AND municipality_code = :m_code
                        """), {"acronym": sigla_gce, "m_code": mun_code}).scalar()

                        if cg_id:
                            conn.execute(text("""
                                INSERT INTO citizen_group_candidacies (election_id, municipality_code, citizen_group_id, votes)
                                VALUES (:e_id, :m_code, :cg_id, :votes)
                                ON CONFLICT (election_id, municipality_code, citizen_group_id) DO UPDATE SET votes = EXCLUDED.votes;
                            """), {"e_id": election_id, "m_code": mun_code, "cg_id": cg_id, "votes": gce_votes})

    print("🚀 Relational Core Data Loading Completed Successfully with Complex Entities!")

if __name__ == "__main__":
    run_elections_etl()
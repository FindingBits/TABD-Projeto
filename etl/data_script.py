import os
import pandas as pd
import pdf_full_name as pdf_names
import sys

#pip install pdfplumber xlrd Levenshtein

EXCEL_RESULTS = 0
EXCEL_MANDATES = 1
EXCEL_MANDATES_EXPECTED = 2
EXCEL_ELECTED_MEMBERS = 3
EXCEL_COL_CIT_NAMES = 4         #os dados estão desactualizados
COL_PDF = 0
CIT_PDF = 1
DISTANCE = 2


lista_acronimos = [
    'PCP',
    'CDS-PP',
    'PPD/PSD',
    'PS',
    'PPM',
    'PCTP/MRPP',
    'PEV',
    'MPT',
    'B.E.',
    'PTP',
    'PAN',
    'MAS',
    'L',
    'JPP',
    'ADN',
    'NC',
    'A)T',
    'IL',
    'CH',
    'R.I.R.',
    'VP',
    'ND',
    'PLS',
    'AD',
    'APU',
    'ADIM',
    'CDM',
    'FEPU',
    'FRS',
    'PXXI',
    'UDP',
    'PDC',
    'MES',
    'FSP',
    'PUP',
    'PCP',
    'GDUP',
    'OCMLP',
    'P.S.R.',
    'PT',
    'MIRN',
    'UEDS',
    'POUS',
    'PDA',
    'PST',
    'ASDI',
    'FUP',
    'PC',
    'E',
    'PSN',
    'PG',
    'PPR',
    'P.H.',
    'MD',
    'PND',
    'FER',
    'PLD',
    'MEP',
    'PPV/CDC',
    'A',
    'PCP-PEV'
]


excel_data = {
    2021 : {
            "data": ("2021-09-26","Eleições Autárquicas 2021 - Câmara Municipal"),
            "xls_files": ["sources/2021/mapa_1_resultados.xlsx","sources/2021/al2021_mandatos_cm_am.xlsx","sources/2021/mapa_2_perc_mandatos.xlsx","sources/2021/mapa_3_eleitos.xlsx","sources/2021/mapa_anexo.xlsx"],
            "pdf_files": ["sources/2021/ColigacoesPDF.pdf","sources/2021/GruposCidadaos2021.pdf"],
            "output": "data-output/data_2021.sql"
        },
    2025 : {
        "data": ("2025-10-12","Eleições Autárquicas 2025 - Câmara Municipal"),
        "xls_files": ["sources/2025/mapa_1_resultados_retificado.xlsx","sources/2025/2025_al_mandatos_cm_am.xlsx","sources/2025/mapa_2_perc_mandatos_retificado.xlsx","sources/2025/mapa_3_eleitos_retificado.xlsx","sources/2025/mapa_anexo.xlsx"],
        "pdf_files": ["sources/2025/coligacoes2025.pdf","sources/2025/citizens2025.pdf"],
        "output": "data-output/data_2025.sql"
    },
    2017 : {
        "data": ("2017-10-01","Eleições Autárquicas 2017 - Câmara Municipal"),
        "xls_files": ["sources/2017/01-mapa_I_vf_r2.xls","sources/2017/al2017_mandatos_cm_am.xlsx","sources/2017/02-mapa_II_perc_mandatos-vf_r2.xls","sources/2017/03-mapaIII_eleitos-vf_r2.xls","sources/2017/04-mapa_anexo-vf_r2.xls"],
        "pdf_files": ["sources/2017/coligacoes2017.pdf","sources/2017/grupos-de-cidadaos2017.pdf"],
        "output": "data-output/data_2017.sql"
    }
}


weird_acronyms = {'PSD': 'PPD/PSD', 'BE': 'B.E.', 'CDS': 'CDS-PP','CDU':'PCP-PEV','RIR':'R.I.R.'}

dotted_acronyms = {'BE': 'B.E.','RIR':'R.I.R.'}

municaplity_names_typos = {'MEDA':"MÊDA"}

#partidos: https://www.cne.pt/content/partidos-politicos-1

data = {              # format
    "districts"                     : [],   # (code,name,type)  
    "municipalities"                : [],   # (code,district_code,name)
}

dep_data = {              # format
    "turnout"                       : [],   # (election_year,municipality_code,registered_voters,voters,blank_votes,null_votes,total_mandates)
    "citizen_group_candidacies"     : [],   # (election_year, municipality_code ,acronym,name, votes, calculated_mandates, expected_mandates)
    "coalition_candidacies"         : [],   # (election_year, municipality_code ,acronym,name, votes, calculated_mandates, expected_mandates)
    "party_candidacies"             : [],   # (election_year, municipality_code ,acronym, votes, calculated_mandates, expected_mandates)
    "coalition_parties"             : []    # (election_year, municipality_code, coalition_acronym, order_number, party_acronym)
}

insert_args = {
    "elections"                     : "(election_year,election_date,description)",
    "candidates"                    : "(candidate_id,full_name)",
    "parties"                       : "(acronym,name,logo_url,active)",
    "districts"                     : "(id,name,type)",
    "municipalities"                : "(code,district,name)",
    "turnout"                       : "(election_year,municipality_code,registered_voters,voters,blank_votes,null_votes,total_mandates)",
    "citizen_group_candidacies"     : "(election_year, municipality_code ,acronym,name, votes, calculated_mandates, expected_mandates)",
    "coalition_candidacies"         : "(election_year, municipality_code ,acronym,name, votes, calculated_mandates, expected_mandates)",
    "party_candidacies"             : "(election_year, municipality_code ,party_id, votes, calculated_mandates, expected_mandates)",
    "coalition_parties"             : "(election_year, municipality_code, coalition_acronym, order_number, party_id)",
    "citizen_group_elected_members" : "(election_year,municipality_code,acronym,candidate_id,elected_order)",
    "coalition_elected_members"     : "(election_year,municipality_code,acronym,candidate_id,elected_order)",
    "party_elected_members"         : "(election_year,municipality_code,party_id,candidate_id,elected_order)"
}

def get_municipality_code(code):
    if code < 100000:
        municipality_code = "0" + str(code)[:3]  + "00"
    else: 
        municipality_code = str(code)[:4] + "00"

    return municipality_code

def load_excel_results_clean_headers(EXCEL_FILE,year)->pd.DataFrame:
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: Excel file '{EXCEL_FILE}' not found.")
        sys.exit(0)
    
    print("📖 Reading Excel file...")

    if(year==2017):
        df = pd.read_excel(EXCEL_FILE, skiprows=1)
    else:
        df = pd.read_excel(EXCEL_FILE, skiprows=2)
    
    df = df.iloc[:-3] #deitar fora as ultimas 3 linhas que têm lixo
    # Uniformizar nomes das colunas para maiúsculas e remover espaços
    df.columns = [str(c).strip().upper() for c in df.columns]

    first_line = df.iloc[0] #first line
    new_header = []

    for col,val in zip(df.columns, first_line):

        if(pd.isna(val)):
            new_header.append(col)
        else:
            new_header.append(val)

    if(year==2025):
        idx = new_header.index("inscritos")
        new_header[idx] = "INSC"
        new_header[idx+1] = "VOT"
        new_header[idx+2] = "BR"
        new_header[idx+3] = "NUL"

    df.columns = new_header
    
    print(f"✅ Cabeçalhos limpos: {list(df.columns)}")

    df = df.drop(df.index[0]).reset_index(drop=True)
    df = df.drop(columns=[col for col in df.columns if 'UNNAMED' in str(col)])

    new_header = list(df.columns)
    if(year==2025):
        new_header[-1]  = "SIGLAS GCE"
        new_header[-2]  = "SIGLAS COLIGAÇÕES"
    df.columns = new_header
    
    df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.A\)$', '', regex=True) #type:ignore
    df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.A\.\)$', '', regex=True) #type:ignore
    # df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.M\.\)$', '', regex=True) #type:ignore
    # df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.M\)$', '', regex=True) #type:ignore

    
    print(df)
    return df

def load_excel_results_clean_headers_(EXCEL_FILE,year)->pd.DataFrame:
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: Excel file '{EXCEL_FILE}' not found.")
        sys.exit(0)
    
    print("📖 Reading Excel file...")

    df = pd.read_excel(EXCEL_FILE, skiprows=3)

    # Uniformizar nomes das colunas para maiúsculas e remover espaços
    df.columns = [str(c).strip().upper() for c in df.columns]

    first_line = df.iloc[0] #first line
    new_header = []
    print(df)


    for col,val in zip(df.columns, first_line):

        if(pd.isna(val)):
            new_header.append(col)
        else:
            new_header.append(val)

    if(year==2021):
        new_header[60] = "SIGLAS COLIGAÇÕES"
        new_header[61] = "SIGLAS GCE"
    elif (year==2017):
        new_header[52] = "SIGLAS COLIGAÇÕES"
        new_header[53] = "SIGLAS GCE"       
    
    df.columns = new_header
    
    print(f"✅ Cabeçalhos limpos: {list(df.columns)}")

    df = df.drop(df.index[0]).reset_index(drop=True)

    if year==2025:
        new_header = list(df.columns)
        new_header[56] = "SIGLAS COLIGAÇÕES"
        new_header[57] = "SIGLAS GCE"
        df.columns = new_header
        df = df.drop(columns=[col for col in df.columns if 'UNNAMED' in str(col)])
    


    df = df.drop(columns=[col for col in df.columns if '%' in str(col)])
    df = df[df['ÓRG']=="CM"]
    df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.A\)$', '', regex=True) #type:ignore
    df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.A\.\)$', '', regex=True) #type:ignore
    # df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.M\.\)$', '', regex=True) #type:ignore
    # df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.M\)$', '', regex=True) #type:ignore

    if(year==2025):
        df.astype({"CÓD":str})

    print(df)
    return df

#erros: em 2021 os códigos de AVEIRO e BEJA têm erros.
#como acabamos por atribuir os códigos do CAOP deixamos de ter esse problema
def extract_district(df):
    data["districts"] = []
    district_df = df[df['ÓRG'].isna()]
    district_df = district_df.drop(district_df.columns[2:], axis=1)

    k = 1
    for i,line in district_df.iterrows():
        code = line["CÓD"]
        district_name = line["CONC"].title()
        if code < 300000:
            district_name = line["CONC"].title()
            district_type = "District"
            district_id = k
        elif code < 400000:
            district_name = district_name.split(" ")[1]
            district_type = "Autonomous Region"
            district_id = 46
        else:
            district_name = district_name.split(" ")[1]
            district_type = "Autonomous Region"
            district_id = 31
        k+=1

        
        data["districts"].append((district_id,district_name,district_type))


#em 2017 e 2019 tem que se ter os códigos como INT em todos os DFS
#em 2025 tem que se ter todos str
#a informação extraída dos municipios é usada depois no turnover
def extract_municipalities(df):
    data["municipalities"] = []
    mdf = df.drop(df.columns[2:], axis=1)

    for i,line in mdf.iterrows():
        code = int(line["CÓD"])
        municipality_code = str(code)[:4] + "00"
        name = line["CONC"].title()
        if code < 100000:
            district_code = int(str(code)[0])
            municipality_code = "0" + str(code)[:3]  + "00"
        elif code < 300000:
            district_code = str(code)[:2] + "0000"
            district_code = int(str(code)[:2])
        elif code < 400000:
            district_code = 46
        else:
            district_code = 31

        data["municipalities"].append((municipality_code,district_code,name))


#extrai os distritos e municipalities
#se true faz output
#se false não faz
def get_district_municipality_data(willoutput):
    #carrega os dados de 2021 só para irmos buscar os dados
    df = load_excel_results_clean_headers(excel_data[2021]["xls_files"][EXCEL_RESULTS],2021)
    df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.A\)$', '', regex=True)
    df['CONC'] = df['CONC'].str.replace(r'\s*\(R\.A\.A\.\)$', '', regex=True)

    extract_district(df)
    #apartir daqui só nos interessa os dados de CM
    df = df[df['ÓRG']=="CM"]
    extract_municipalities(df)

    if(willoutput):
        with open("data-output/data_output.sql", "w", encoding="utf-8") as f:
            for keys in data:
                f.write(f"INSERT INTO public.{keys} {insert_args[keys]} VALUES\n")
                s = ""
                for elem in data[keys]:
                    s+="("
                    for e in elem:
                        if type(e) == str:
                            s += f"'{e}',"
                        else:
                            s += f"{e},"
                    
                    s = s[:-1]
                    s += "),\n"
                
                s = s[:-2]
                s+=";\n\n"
                f.write(s)


#gera a turnover
#extraí mandatos totais de outro ficheiro
#Existem 3 concelhos que vão dar dor de cabeça:
#Santa Maria da Feira -> Feira 
#FREIXO DE ESPADA À CINTA -> FREIXO DE ESPADA A CINTA
#MÊDA -> MEDA
conc_name_dif = {"FEIRA":"SANTA MARIA DA FEIRA","FREIXO DE ESPADA A CINTA":"FREIXO DE ESPADA À CINTA","MEDA":"MÊDA"}
def extract_mandates(mdf,EXCEL_FILE,year):

    dep_data["turnout"] = []
    skip_rows = 0
    if year==2025:
        skip_rows = 2
    else:
        skip_rows = 1

    mandates = pd.read_excel(EXCEL_FILE, skiprows=skip_rows)
    mandates.columns = [str(c).strip().upper() for c in mandates.columns]
    print(mandates)
    tup = data["municipalities"]


    for (idx,line_mandates),i in zip(mandates.iterrows(),range(0,len(data["municipalities"]))):
        
        concelho_man = line_mandates['CONCELHO'].upper().strip()
        concelho_mun    = tup[i][2].upper().strip()
        
        #o cross check é feito usando o nome do concelho da nossa lista
        # no dataframe para ir buscar os dados
        # este if resolve o problema dos nomes problemáticos
        # não perguntem porque é só em 2025
        if year==2025:
            if concelho_mun in conc_name_dif:
                concelho_mun = conc_name_dif[concelho_mun]

        row_mun =  mdf[mdf['CONC']==concelho_mun]

        dep_data["turnout"].append((year,tup[i][0],int(row_mun["INSC"].values[0]),int(row_mun["VOT"].values[0]),int(row_mun["BR"].values[0]),int(row_mun["NUL"].values[0]),int(line_mandates["CM"])))

    print("\t\tTurnover: Done")




#nas funções abaixo, o # de partidos é variável e requer ajustes de ano para ano
def extract_coalitions(df,year):
    start_index = 0
    start_index_mandates = 0

    if year==2021:
        start_index = 29
        start_index_mandates = 25
    elif year==2025:
        start_index = 27
        start_index_mandates = 23
    elif year==2017:
        start_index = 26
        start_index_mandates = 22

    df = df[df['SIGLAS COLIGAÇÕES'].notna()]
    df = df.drop(df.columns[2:start_index], axis=1)

    if year==2017:
        df = df.drop(df.columns[5:8], axis=1)
    else: 
        df = df.drop(df.columns[5:9], axis=1)
    
    cols = ["[A]","[B]","[C]"]
    df_mandates = load_excel_results_clean_headers_(excel_data[year]["xls_files"][EXCEL_MANDATES_EXPECTED],year) #type:ignore
    df_mandates = df_mandates[df_mandates['SIGLAS COLIGAÇÕES'].notna()]
    headers = list(df_mandates.columns)
    new_headers = headers[:start_index_mandates] + cols + headers[(start_index_mandates+3):]
    df_mandates.columns = new_headers
    df_mandates = df_mandates.drop(df_mandates.columns[2:10], axis=1)
    
    # print(df)
    # print(df_mandates)

    dep_data["coalition_candidacies"],dep_data["coalition_parties"] = pdf_names.get_coalition_names_pdf(excel_data[year]["pdf_files"][COL_PDF],year,df,df_mandates)
    print("\t\tCoalition Candidacies: Done")

def extract_citizens(df,year):
    start_index = 32
    
    start_index = 0
    start_index_mandates = 0
    if year==2021:
        start_index = 32
        start_index_mandates = 28
    elif year==2025:
        start_index = 29
        start_index_mandates = 26
    elif year==2017:
        start_index = 27
        start_index_mandates = 25
    
    df = df[df['SIGLAS GCE'].notna()]
    df = df.drop(df.columns[2:start_index], axis=1)

    cols = ["[D]","[E]", "[F]","[G]"]

    df_mandates = load_excel_results_clean_headers_(excel_data[year]["xls_files"][EXCEL_MANDATES_EXPECTED],year) #type:ignore
    df_mandates = df_mandates[df_mandates['SIGLAS GCE'].notna()]
    headers = list(df_mandates.columns)
    new_headers = headers[:start_index_mandates] + cols + headers[(start_index_mandates+4):]
    df_mandates.columns = new_headers
    df_mandates = df_mandates.drop(df_mandates.columns[2:10], axis=1)
    print(df_mandates)

    dep_data["citizen_group_candidacies"] = pdf_names.get_citizen_names_pdf(excel_data[year]["pdf_files"][CIT_PDF],year,df,df_mandates)
    print("\t\tCitizen Group Candidacies: Done")

def extract_party_candidacies(df:pd.DataFrame,year):
    dep_data['party_candidacies'] = []
    
    start_i = 8
    end_i = 31-start_i
    mandates = 25
    if year==2021:
        start_i = 8
        end_i = 31-start_i
        mandates = 25
    elif year==2025:
        start_i = 8
        end_i = 29-start_i
        mandates = 23
    elif year==2017:
        start_i = 8
        end_i = 28-start_i
        mandates = 22

    df = df.drop(df.columns[2:start_i], axis=1)
    df = df.drop(df.columns[end_i:], axis=1)
    party_cols = list(df.columns[2:])
    
    df_mandates = load_excel_results_clean_headers_(excel_data[year]["xls_files"][EXCEL_MANDATES_EXPECTED],year) #type:ignore
    
    headers = list(df_mandates.columns)
    new_headers = headers[:4] + party_cols + headers[mandates:]
    df_mandates.columns = new_headers

    # print(df_mandates)
    # print(df)

    for (ind,line),(indx,line_m) in zip(df.iterrows(),df_mandates.iterrows()):
        municipality_code = get_municipality_code(int(line['CÓD']))
        for party in party_cols:
            if pd.notna(line[party]):
                    
                if year<2020 and party=="PNR":
                    party_id = lista_acronimos.index("E")
                elif year<2021 and party=="PURP":
                    party_id = lista_acronimos.index("A)T")
                elif year<=2021 and party=="PDR":
                    party_id = lista_acronimos.index('ADN')
                else:
                    party_id = lista_acronimos.index(party)
                
                party_id += 1
                votes = line[party]
                expected_mandates = line_m[party]
                
                dep_data['party_candidacies'].append((year,municipality_code,party_id,votes,0,expected_mandates))
    
    print("\t\tParty Candidacies: Done")

def get_data():
    
    get_district_municipality_data(True)

    #percorrer os anos de eleições que vão ter que etar associados a ficheiros
    for key in excel_data:
        print(f"--------- Elections {key} ---------")

        df = load_excel_results_clean_headers(excel_data[key]["xls_files"][EXCEL_RESULTS],key)
        
        #apartir daqui só nos interessa os dados de CM
        df = df[df['ÓRG']=="CM"]

        if(key==2025):
            df['CÓD'] = df['CÓD'].astype('str')
        else:
            df['CÓD'] = df['CÓD'].astype('int')

        df.astype({'INSC':int,'VOT':int,'BR':int,'NUL':int})
        print(df)

        #turnout
        extract_mandates(df,excel_data[key]["xls_files"][EXCEL_MANDATES],key)
        #coalition candidacies & coalition_parties
        extract_coalitions(df,key)
        #citizen group candidacies
        extract_citizens(df,key)
        #party candidacies
        extract_party_candidacies(df,key)

        #output
        with open(excel_data[key]['output'], "w", encoding="utf-8") as f:
            for keys in dep_data:
                f.write(f"-- ----------------------------------------------------\n")
                f.write(f"-- Data {keys}\n")
                f.write(f"-- ----------------------------------------------------\n")
                
                f.write(f"INSERT INTO public.{keys} {insert_args[keys]} VALUES\n")
                s = ""
                for elem in dep_data[keys]:
                    s+="("
                    for e in elem:
                        if type(e) == str:
                            s += f"'{e}',"
                        else:
                            s += f"{e},"
                    
                    s = s[:-1]
                    s += "),\n"
                
                s = s[:-2]
                s+=";\n\n"
                f.write(s)


def unificar_ficheiros_sql(ficheiro_saida):
    """
    Lê uma lista de caminhos de ficheiros .sql e junta-os num único ficheiro,
    adicionando cabeçalhos de separação para organização.
    """
    print(f"A iniciar a consolidação em: {ficheiro_saida}")
    
    try:
        with open(ficheiro_saida, mode="w", encoding="utf-8") as f_destino:
            # Escreve um cabeçalho global inicial
            f_destino.write("-- ====================================================\n")
            f_destino.write("-- FICHEIRO GLOBAL CONSOLIDADO AUTOMATICAMENTE (ETL)\n")
            f_destino.write("-- ====================================================\n\n")
            
            for key in excel_data:
                caminho = excel_data[key]['output']
                if not os.path.exists(caminho):
                    print(f"⚠️ Aviso: O ficheiro '{caminho}' não foi encontrado. A saltar...")
                    continue
                
                nome_base = key #os.path.basename(caminho)
                print(f"-> A processar: {nome_base}")
                
                # Injeta um separador visual no SQL para identificar de onde veio o código
                f_destino.write(f"-- ----------------------------------------------------\n")
                f_destino.write(f"-- Data Elections {nome_base}\n")
                f_destino.write(f"-- ----------------------------------------------------\n")
                
                # Lê o conteúdo do ficheiro atual e escreve-o diretamente no destino
                with open(caminho, mode="r", encoding="utf-8") as f_origem:
                    f_destino.write(f_origem.read())
                
                # Garante que há quebras de linha entre os ficheiros para evitar colagens de texto erradas
                f_destino.write("\n\n")
                
        print("🟢 Unificação concluída com sucesso!")
        
    except Exception as e:
        print(f"🔴 Erro crítico durante a unificação: {e}")

    # --- Configuração dos Caminhos ---
    # Defina aqui a ordem exata em que as tabelas e funções devem ser criadas
    ficheiros_a_juntar = [
        "etl/schema_base.sql",     # 1. Cria as tabelas, chaves e restrições CHECK
        "etl/dados_iniciais.sql",  # 2. Insere os distritos, partidos estáveis, etc.
        "etl/triggers_dhondt.sql"  # 3. Injeta as funções PL/pgSQL e os Triggers que estabilizámos
    ]

#ficheiro_final = "etl/schema_clean.sql"

if __name__ == "__main__":
    get_data()
    unificar_ficheiros_sql("data-output/all_data.sql")
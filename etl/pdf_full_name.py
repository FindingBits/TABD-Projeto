
import pdfplumber
import Levenshtein as lev
import pandas as pd
DISTANCE = 2

lista_de_orgaos = ["Câmara Municipal","Assembleia de Freguesia","Assembleia Municipal"]

subs = {'VP':'VOLT'}

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
    'A'
]

lista_acronimos_check = [
    'PCP',
    'CDS-PP',
    'PPD/PSD',
    'PS',
    'PPM',
    'PCTP/MRPP',
    'MPT',
    'B.E.',
    'PTP',
    'JPP',
    'ADN',
    'NC',
    'A)T',
    'R.I.R.',
    'VP',
    'PLS',
    'ADIM',
    'CDM',
    'FEPU',
    'FRS',
    'PXXI',
    'UDP',
    'PDC',
    'FSP',
    'PCP',
    'GDUP',
    'OCMLP',
    'P.S.R.',
    'PT',
    'MIRN',
    'UEDS',
    'PDA',
    'PST',
    'ASDI',
    'FUP',
    'PC',
    'PSN',
    'PG',
    'PPR',
    'P.H.',
    'MD',
    'PND',
    'PLD',
    'PPV/CDC',
]

weird_acronyms = {'PSD': 'PPD/PSD', 'BE': 'B.E.', 'CDS': 'CDS-PP','CDU':'PCP-PEV','RIR':'R.I.R.','R.I.R':'R.I.R.'}
sub_conc_2021 = {"MÊDA":"MEDA"}
sub_conc_2017 = {"MÊDA":"MEDA","FREIXO DE ESPADA À CINTA":"FREIXO DE ESPADA A CINTA"}
sub_conc_2025 = {"FEIRA":"SANTA MARIA DA FEIRA","FREIXO DE ESPADA A CINTA":"FREIXO DE ESPADA À CINTA","MEDA":"MÊDA"}

dotted_acronyms = {'BE': 'B.E.','RIR':'R.I.R.'}

cols_col = ["[A]","[B]","[C]"]
cols_cit = ["[D]","[E]", "[F]","[G]"]


split_string = {2021: ">>", 2025: ">",2017:">>"}
sub_conc = {2021: sub_conc_2021,2025: sub_conc_2025,2017: sub_conc_2017}

def get_municipality_code(code):
    if code < 100000:
        municipality_code = "0" + str(code)[:3] + "00"
    else: 
        municipality_code = str(code)[:4] + "00"

    return municipality_code


#pre-process pdf to be 1 continuous file instead of having pages
#some tables go gover the page limit
def get_file_lines(file,year):
    lines = []
    print("A carregar e a unificar o PDF linha a linha...")
    with pdfplumber.open(file) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            
            if texto_pagina:
                # Divide o texto da página atual por quebras de linha
                linhas_da_pagina = texto_pagina.split('\n')
                
                # Adiciona as linhas desta página à nossa lista global
                for linha in linhas_da_pagina:
                    # Opcional: .strip() remove espaços inúteis no início/fim da linha
                    lines.append(linha.strip())
                if(year==2017): #2017 tem # de página
                    lines.pop()
    #precisamos da linha fantasma no fim. CONFIEM
    lines.append([])
    return lines


def coalition_order(acronym):
    in_order = []
    size = 0

    acronym_temp = acronym.replace("PNR","E")
    acronym_temp = acronym_temp.replace("PURP","A)T")
    acronym_temp = acronym_temp.replace("PDR","ADN")
    acronym_temp = acronym_temp.replace("PPV/DC","PPV/CDC")
    lista_acronimos_local = sorted(lista_acronimos, key=len, reverse=True)
    for p in lista_acronimos_local:
        if(len(acronym_temp)>0):
            pos = acronym_temp.find(p)
            if pos != -1:
                size += len(p)
                acronym_temp = acronym_temp.replace(p,'')
                in_order.append((pos,p))
        else:
            break 
        
    if(len(acronym_temp)>0):
        for w in weird_acronyms:
            pos = acronym_temp.find(w)
            if pos!=-1:
                size += len(w)
                acronym_temp = acronym_temp.replace(w,'')
                in_order.append((pos,w))    

    if(size<len(acronym)-(len(in_order)-1)):
        print(f"parties: {in_order} from: {acronym} stopped at {acronym_temp}")

    return sorted(in_order)

def matching(acronym:str,df_line:pd.DataFrame,df_mandates_temp:pd.DataFrame):
    found = False
    votes = 0
    expected_mandates = 0
    for (ind,line),(ind_,line_m) in zip(df_line.iterrows(),df_mandates_temp.iterrows()):
        df_cols = line['SIGLAS COLIGAÇÕES'].split(",")
        for k in range(0,len(df_cols)):
            df_col_ac = df_cols[k].strip('[]').replace(" ","")
            if(lev.distance(df_col_ac,acronym)<DISTANCE):
                votes = line[cols_col[k]]
                expected_mandates = line_m[cols_col[k]]

                found = True
                return (found,votes,expected_mandates)
    
    return(found,votes,expected_mandates)

def try_matchings(acronym:str,df_line:pd.DataFrame,df_mandates_temp:pd.DataFrame):
    #found = False
    replacements = [(".","/"),("/","."),(".","-"),("-","."),("-","/"),("/","-")]

    
    temp_name_ = acronym.replace("VP","VOLT")
    ret_val = matching(temp_name_,df_line,df_mandates_temp)
    if(ret_val[0]):
        return (ret_val[1],ret_val[2])

    for i in range(0,len(replacements)):
        rep = replacements[i]
        temp_name = temp_name_.replace(rep[0],rep[1])
        ret_val = matching(temp_name,df_line,df_mandates_temp)
        if(ret_val[0]):
            return (ret_val[1],ret_val[2])
    print(f"\t\tWARNING COULDN'T FIND {acronym}")    
    return(0,0)



def check_if_acronym(acronym:str):
    for p in lista_acronimos_check:
        #a coallition não vai ser só este partido
        #e vai dar match com
        if(acronym.find(p)!=-1):
            return True
    return False


def get_coalition_names_pdf(pdf_file:str,year:int,df:pd.DataFrame,df_mandates:pd.DataFrame):
    coalition_parties = []
    coalition_candidacies = []
    
    orgao_target = "Câmara Municipal"
    municipio_atual = None
    orgao_atual = None

    lines = get_file_lines(pdf_file,year)

    print("A processar o PDF e a extrair os nomes...")
    split_s = split_string[year]

    i = 0
    while (i<len(lines)):
        linha = lines[i]

        if split_s in linha:
            municipio_atual = lines[i-1].strip().upper()

        #ver se é a linha do orgão, se sim dar set
        if linha in lista_de_orgaos:
            orgao_atual = linha.strip()
        
        #se não é CM, não nos interessa
        if (orgao_atual != orgao_target):
            i+=1
            continue
        
        #se chegamos aqui, estamos no orgão correcto
        #percorrer a tabela até chegar ao concelho
        i+=1                            #entrar nas linhas da tabela de coligações
        while(split_s not in lines[i+1]):

            
            if(i>=len(lines)):      #no ultimo caso não batemos num >>
                break               #sair fora 
            


            linha = lines[i]
            name_col = linha.split(" ")
            acronym_atual = name_col[-1]

            #há nomes de coligações que ocupam 2 linhas...
            #mas a formatação do ficheiro é diferente em 2021 e 2025
            if(year==2025):
                if(acronym_atual[-1]=='-'):
                    acronym_atual += lines[i+2]
                    name_col = lines[i+1]
                    i+=2
            else:
                if(acronym_atual[-1]=='-'):
                    acronym_atual += lines[i+1]
                    i+=1

            if acronym_atual == "PCP-PEV":
                i+=1
                if(i+1>=len(lines)):
                    break
                continue
            
            if (not check_if_acronym(acronym_atual)):
                spelling = 0
                if '.' in acronym_atual:
                    for w in weird_acronyms:
                        if w in acronym_atual:
                            if check_if_acronym(acronym_atual.replace(w,weird_acronyms[w])):
                                spelling = 1
                                break 
                if (year==2025 and municipio_atual=='OEIRAS' and acronym_atual=='PAN'):
                    acronym_atual = 'PS - PAN'
                    spelling=1
                
                if not spelling:
                    i+=1
                    continue

            
            name_col = linha.split(" ")
            name_col = name_col[:-1]
            name_col = ' '.join(name_col)

            #look. it's one case. 
            if(year==2021):
                if(municipio_atual=="Alcácer do Sal".upper()):
                    name_col = "TODOS JUNTOS PARA QUE ALCÁCER GANHE"
                    acronym_atual = "PPD/PSD.CDS-PP.MPT.PPM.A"
            if (year==2025 and acronym_atual=='PS - PAN'):
                name_col = "PS e PAN - EM OEIRAS TODOS CONTAM"

            party_order = coalition_order(acronym_atual)


            
            if(municipio_atual in sub_conc[year]):
                municipio_atual = sub_conc[year][municipio_atual]
            
            municipality_code = df.loc[df['CONC']==municipio_atual,'CÓD'].values[0]
            df_temp = df.loc[df['CÓD']==municipality_code]
            df_mandates_temp = df_mandates.loc[df_mandates['CÓD']==municipality_code]
            code = get_municipality_code(int(municipality_code))
            
            if(df_temp.empty or df_mandates_temp.empty):
                print("ERROR: One of the dataframes is empty for this municipality")

            #inserção na tabela relacional do coalition_parties
            for k in range(0,len(party_order)):
                
                col_party = party_order[k][1]
                if col_party in weird_acronyms:
                    party_id = lista_acronimos.index(weird_acronyms[col_party])
                else:
                    if year<2020 and col_party=="PNR":
                        party_id = lista_acronimos.index("E")
                    elif year<2021 and col_party=="PURP":
                        party_id = lista_acronimos.index("A)T")
                    elif year<2021 and col_party=="PDR":
                        party_id = lista_acronimos.index('ADN')
                    else:
                        party_id = lista_acronimos.index(col_party)
                    
                    #party_id = lista_acronimos.index(col_party)

                if(party_id<0):
                    print(f"PARTY ID MENOR QUE 0 {col_party} not found")
                
                coalition_parties.append((year,code,acronym_atual,k+1,party_id+1))


            votes = 0
            found = False
            expected_mandates = 0

            for (ind,line),(ind_,line_m) in zip(df_temp.iterrows(),df_mandates_temp.iterrows()):
                df_cols = line['SIGLAS COLIGAÇÕES'].split(",")
                if(year==2021):
                    temp_name = acronym_atual.replace("PDR","ADN")
                else: 
                    temp_name = acronym_atual
                
                indx = -1
                    
                for k in range(0,len(df_cols)):
                    df_col_ac = df_cols[k].strip('[]').replace(" ","")
                    
                    if (lev.distance(df_col_ac,temp_name)<DISTANCE):
                        indx = k
                        break
                
                if(indx>=0):
                    #found best case
                    votes = line[cols_col[indx]]
                    expected_mandates = line_m[cols_col[indx]]
                    coalition_candidacies.append((year,code,acronym_atual,name_col,votes,0,expected_mandates))
                    found = True 
                    break 

            if(not found):
                print(f"col: {acronym_atual} name:{name_col} municipio_atual: {municipio_atual}")
                votes,expected_mandates = try_matchings(acronym_atual,df_temp,df_mandates_temp)
                coalition_candidacies.append((year,code,acronym_atual,name_col,votes,0,expected_mandates))


            i+=1

            if(i+1>=len(lines)):
                break

        
        #se saiu do while tenho que fazer unset ao orgão... senão vai dar asneira
        orgao_atual = None
        if split_s in linha:
            municipio_atual = lines[i-1].strip().upper()
        
        i+=1

    return(coalition_candidacies,coalition_parties)


def try_splits(acronym,name_col,linha,df_temp,df_mandates):
    split_line = linha.split(" ")
    for i in range(1,len(split_line)):
        local_name_col = split_line[:i]
        local_name_col = ' '.join(local_name_col)
        acronym_atual = split_line[i:]
        acronym_atual = ' '.join(acronym_atual)

        votes = 0
        expected_mandates = 0
        for (ind,line),(ind_,line_m) in zip(df_temp.iterrows(),df_mandates.iterrows()):
            df_cols = line['SIGLAS GCE'].split(",")
            indx = -1
            for k in range(0,len(df_cols)):
                df_col_ac = df_cols[k].strip('[]').upper()
                if (lev.distance(df_col_ac,acronym_atual.upper())<DISTANCE):
                    indx = k
                    break

            if(indx>=0):
                #found best case
                votes = line[cols_cit[indx]]
                expected_mandates = line_m[cols_cit[indx]]
                acronym = acronym_atual
                name_col = local_name_col
                return True,votes,expected_mandates,acronym,name_col
                #citizen_group_candidacies.append((year,code,acronym_atual,name_col,votes,0,expected_mandates))
    
    print(f"WARNING: Still not found! line: {linha}")
    return False,votes,expected_mandates,acronym,name_col


def get_citizen_names_pdf(pdf_file:str,year:int,df:pd.DataFrame,df_mandates:pd.DataFrame):
    citizen_group_candidacies = []
    
    orgao_target = "Câmara Municipal"
    municipio_atual = None
    orgao_atual = None


    lines = get_file_lines(pdf_file,year)

    print("A processar o PDF e a extrair os nomes...")
    split_s = split_string[year]

    i = 0
    while (i<len(lines)):
        linha = lines[i]

        if split_s in linha:
            municipio_atual = lines[i-1].strip().upper()

        #ver se é a linha do orgão, se sim dar set
        if linha in lista_de_orgaos:
            orgao_atual = linha.strip()
        
        #se não é CM, não nos interessa
        if (orgao_atual != orgao_target):
            i+=1
            continue
        
        #se chegamos aqui, estamos no orgão correcto
        #percorrer a tabela até chegar ao concelho
        i+=1                            #entrar nas linhas da tabela de coligações
        while(split_s not in lines[i+1]):
            
            if(i>=len(lines)):      #no ultimo caso não batemos num >>
                break               #sair fora 
            
            linha = lines[i]
            name_col = linha.split(" ")
            
            if(len(name_col)<2):
                if(year==2017 and name_col[-1]=='2017'):
                    i+=1
                    continue
                else:
                    i+=1
                    break

            
            acronym_atual = name_col[-1]
            name_col = name_col[:-1]
            name_col = ' '.join(name_col)

            #há nomes de coligações que ocupam 2 linhas...
            if(acronym_atual[-1]=='-'):
                acronym_atual += lines[i+1]
                i+=1

            if(municipio_atual in sub_conc[year]):
                municipio_atual = sub_conc[year][municipio_atual]
            
            #não devia ser legal poderem ter ACRONIMOS com espaços
            if(year==2021):
                if(municipio_atual=="MANTEIGAS"):
                    acronym_atual = "Manteigas 2030"
                    name_col = "Manteigas 2030"
                if(municipio_atual=="MATOSINHOS" and acronym_atual=="SIM!"):
                    acronym_atual = "ANTÓNIO PARADA SIM!"
                    name_col = "ANTÓNIO PARADA SIM!"
            
            if(year==2025):
                if(municipio_atual=="CAMPO MAIOR"):
                    acronym_atual = "SIM"
                    name_col = "Grupo de cidadãos eleitores - Somos Independentes - Movimento por Campo Maior"
                    i+=1 #por causa das duas linhas.
                if((municipio_atual=="PONTE DE SOR")):
                    acronym_atual = "DPP"
                    name_col = "Grupo de Cidadãos Eleitores Cidadania Ativa - Do Povo Para o Povo"
                    i+=1 #por causa das duas linhas.
                if(municipio_atual=="MAÇÃO"):
                    acronym_atual = "TJPM"
                    name_col = "MOVIMENTO INDEPENDENTE TODOS JUNTOS POR MAÇÃO"
                    i+=1
            if(year==2017):
                if(municipio_atual=="VILA NOVA DE CERVEIRA"):
                    acronym_atual = "PenCe"
                    name_col = "MOVIMENTO INDEPENDENTE PENSAR CERVEIRA - PenCe"
                    i+=1
                if(municipio_atual=="VIZELA"):
                    acronym_atual = "VS - VHS"
                    name_col = "Vizela Sempre - Vitor Hugo Salgado - Independentes"
                    i+=1

            municipality_code = df.loc[df['CONC']==municipio_atual,'CÓD'].values[0]
            df_temp = df.loc[df['CÓD']==municipality_code]
            df_mandates_temp = df_mandates.loc[df_mandates['CÓD']==municipality_code]
            code = get_municipality_code(int(municipality_code))


            votes = 0
            found = False
            expected_mandates = 0
            for (ind,line),(ind_,line_m) in zip(df_temp.iterrows(),df_mandates_temp.iterrows()):
                df_cols = line['SIGLAS GCE'].split(",")
                indx = -1
                for k in range(0,len(df_cols)):
                    df_col_ac = df_cols[k].strip('[]').upper()
                    if (lev.distance(df_col_ac,acronym_atual.upper())<DISTANCE):
                        indx = k
                        break
                
                if(indx>=0):
                    #found best case
                    votes = line[cols_cit[indx]]
                    expected_mandates = line_m[cols_cit[indx]]
                    citizen_group_candidacies.append((year,code,acronym_atual,name_col,votes,0,expected_mandates))
                    found = True 
                    break 

            if(not found):
                print(f"col: {acronym_atual} name:{name_col} municipio_atual: {municipio_atual}")

                found,votes,expected_mandates,acronym_atual,name_col = try_splits(acronym_atual,name_col,linha,df_temp,df_mandates_temp)
                if(found):
                    citizen_group_candidacies.append((year,code,acronym_atual,name_col,votes,0,expected_mandates))

            i+=1

            if(i+1>=len(lines)):
                break

        
        #se saiu do while tenho que fazer unset ao orgão... senão vai dar asneira
        orgao_atual = None
        if split_s in linha:
            municipio_atual = lines[i-1].strip().upper()
        
        i+=1
    
    return citizen_group_candidacies   

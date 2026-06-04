import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 1. Efetuar o pedido HTTP à página do Tribunal Constitucional
url = "https://www.cne.pt/content/partidos-politicos-1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response.encoding = 'utf-8' # Preserva a acentuação portuguesa original
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # No HTML do TC, as tabelas de partidos encontram-se dentro de tags <table>
    tabelas = soup.find_all('table')
    
    if len(tabelas) < 1:
        print("Erro: Nenhuma tabela encontrada na página.")
        exit()
        
    partidos_finais = []
    
    # Mapeamento para iterar as tabelas (Tabela 1: Inscritos | Tabela 2: Extintos, se disponível)
    for i, tabela in enumerate(tabelas):
        # Define o estado com base na ordem das tabelas da página
        status = "TRUE" if i == 0 else "FALSE"
        
        linhas = tabela.find_all('tr')
        for linha in linhas:
            celulas = linha.find_all('td')
            
            # Valida se a linha atual contém colunas de dados reais (mínimo 3 células)
            if len(celulas) >= 3:
                nome_bruto = celulas[0].get_text(strip=True)
                sigla_bruta = celulas[2].get_text(strip=True)
                
                # Ignora linhas de cabeçalho estrutural
                if "denominação" in nome_bruto.lower() or "sigla" in sigla_bruta.lower():
                    continue
                
                # Captura e tratamento do logótipo do partido (coluna 2, índice 1)
                tag_img = celulas[1].find('img')
                url_imagem = ""
                if tag_img and tag_img.get('src'):
                    url_imagem = urljoin(url, tag_img.get('src'))
                
                if nome_bruto and sigla_bruta:
                    # Limpeza de ruídos textuais e referências a ex-siglas
                    nome_limpo = nome_bruto.split('[ex-')[0].split('(')[0].strip()
                    sigla_limpa = sigla_bruta.split('[ex-')[0].split('(')[0].strip()
                    
                    # Padronização de maiúsculas para nomes muito longos em maiúsculas
                    if nome_limpo.isupper() and len(nome_limpo) > 10:
                        nome_limpo = nome_limpo.title()
                        
                    # Escapar aspas simples para compatibilidade SQL
                    nome_sql = nome_limpo.replace("'", "''")
                    sigla_sql = sigla_limpa.replace("'", "''")
                    
                    partidos_finais.append((sigla_sql, nome_sql, url_imagem, status))

    #acrescentar o CDU que é uma coligação especial permanente, na prática é um partido
    partidos_finais.append(('PCP-PEV', 'CDU - Coligação Democrática Unitária', 'https://upload.wikimedia.org/wikipedia/commons/b/ba/Logo_of_the_Unitary_Democratic_Coalition.svg', 'TRUE'))
    # 2. Geração e Exportação do Ficheiro SQL
    if partidos_finais:
        linhas_insert = []
        for sigla, nome, img_url, status in partidos_finais:
            img_val = f"'{img_url}'" if img_url else "NULL"
            linhas_insert.append(f"('{sigla}', '{nome}', {img_val}, {status})")
            
        # Agrupamento no formato de alta performance Bulk Insert
        sql_output = "INSERT INTO parties (acronym, name, logo_url, status) VALUES \n" + ",\n".join(linhas_insert) + ";"
        

        with open("data-output/todos_partidos_tc.sql", "w", encoding="utf-8") as f:
            f.write(sql_output)
            
        print(f"Sucesso! Extraídos {len(partidos_finais)} partidos no total para 'todos_partidos_tc.sql'.")
    else:
        print("Erro: Não foi possível processar as células da tabela.")

except requests.exceptions.RequestException as e:
    print(f"Erro de comunicação com o site do TC: {e}")

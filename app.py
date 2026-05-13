from flask import Flask, render_template
import random

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/selecao')
def selecao():
    # Lista organizada: primeiro as Legislativas, depois as Presidenciais
    eleicoes = [
        # LEGISLATIVAS
        {"nome": "Legislativas 2024", "ano": "2024", "tipo": "Legislativa", "icon": "bi-bank"},
        {"nome": "Legislativas 2022", "ano": "2022", "tipo": "Legislativa", "icon": "bi-bank"},
        {"nome": "Legislativas 2019", "ano": "2019", "tipo": "Legislativa", "icon": "bi-bank"},
    ]
    return render_template('selecao.html', eleicoes=eleicoes)

@app.route('/detalhes/<nome_eleicao>')
def detalhes(nome_eleicao):
    # Base de dados de teste (simulada)
    dados_detalhados = {
        "Legislativas 2024": {
            "votos_apurados": "99.01%",
            "abstencao": "33.77%",
            "vencedor": "AD (Aliança Democrática)",
            "mandatos": {"AD": 80, "PS": 78, "CH": 50, "IL": 8, "BE": 5},
            "descricao": "As eleições legislativas de 2024 marcaram uma mudança no cenário político português com a subida do partido Chega.",
            "total_eleitores": "10.8M"
        },
        "Presidenciais 2021": {
            "votos_apurados": "100%",
            "abstencao": "60.51%",
            "vencedor": "Marcelo Rebelo de Sousa",
            "mandatos": {"Marcelo": "60.7%", "Gomes": "13.0%", "Ventura": "11.9%"},
            "descricao": "Eleições realizadas em período de pandemia, resultando numa reeleição à primeira volta do atual Presidente.",
            "total_eleitores": "10.8M"
        }
    }

    # Procura os dados ou mostra um dicionário vazio se não encontrar
    info = dados_detalhados.get(nome_eleicao, {
        "votos_apurados": "N/A", "abstencao": "N/A", "vencedor": "Desconhecido",
        "mandatos": {}, "descricao": "Dados não disponíveis para este teste.", "total_eleitores": "N/A"
    })

    return render_template('detalhes.html', nome=nome_eleicao, info=info)

@app.route('/graficos')
def graficos():
    # Gerar dados aleatórios para o gráfico
    labels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
    dados = [random.randint(10, 100) for _ in range(6)]
    return render_template('graficos.html', labels=labels, dados=dados)

if __name__ == '__main__':
    app.run(debug=True)
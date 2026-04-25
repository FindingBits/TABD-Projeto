from flask import Flask, render_template
import random

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/selecao')
def selecao():
    # Simulando alguns itens
    itens = [f"Opção {i}" for i in range(1, 9)]
    return render_template('selecao.html', itens=itens)

@app.route('/graficos')
def graficos():
    # Gerar dados aleatórios para o gráfico
    labels = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
    dados = [random.randint(10, 100) for _ in range(6)]
    return render_template('graficos.html', labels=labels, dados=dados)

if __name__ == '__main__':
    app.run(debug=True)
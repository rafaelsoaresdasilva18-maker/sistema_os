from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory
import sqlite3
import os
import urllib.parse
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'infonet_chave_secreta_pro'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect('banco_os.db')
    cursor = conn.cursor()
    
    # Tabela de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    ''')
    
    # Tabela de Ordens de Servico
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            endereco TEXT NOT NULL,
            tecnico_id INTEGER NOT NULL,
            tipo_servico TEXT NOT NULL,
            observacao_admin TEXT,
            potencia_cto TEXT,
            potencia_cliente TEXT,
            fusoes_detalhes TEXT,
            tipo_fusoes TEXT,
            cor_tubo_fibra TEXT,
            origem_destino_rota TEXT,
            pendencias TEXT,
            status TEXT NOT NULL,
            foto_nome TEXT,
            data_inicio TEXT,
            data_fim TEXT,
            duracao_minutos INTEGER,
            FOREIGN KEY (tecnico_id) REFERENCES usuarios (id)
        )
    ''')

    # Tabela de Logs de Acesso
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_acesso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nome_usuario TEXT NOT NULL,
            login_time TEXT NOT NULL,
            logout_time TEXT,
            duracao_minutos INTEGER,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')

    colunas_adicionais = [
        ("observacao_admin", "TEXT"),
        ("tipo_fusoes", "TEXT"),
        ("cor_tubo_fibra", "TEXT"),
        ("origem_destino_rota", "TEXT")
    ]
    for col, col_type in colunas_adicionais:
        try:
            cursor.execute(f"ALTER TABLE ordens_servico ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Logins Iniciais
    usuarios_iniciais = [
        ('admin', '781478', 'Gestão / CEO', 'admin'),
        ('cleberalves', 'cleberalves', 'Cleber Alves', 'tecnico'),
        ('wiliammelanes', 'wiliammelanes', 'Wiliam Melanes', 'tecnico'),
        ('victorcarlos', '77451311', 'Victor Carlos', 'tecnico')
    ]

    for user, pwd, nome, tipo in usuarios_iniciais:
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (user,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO usuarios (username, senha, nome, tipo) VALUES (?, ?, ?, ?)", (user, pwd, nome, tipo))
        else:
            cursor.execute("UPDATE usuarios SET senha = ? WHERE username = ?", (pwd, user))

    conn.commit()
    conn.close()

def limpar_logs_antigos():
    try:
        conn = sqlite3.connect('banco_os.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM logs_acesso WHERE datetime(login_time) < datetime('now', '-3 days')")
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# HTML TEMPLATES
HTML_LOGIN = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Infonet Telecom - Login</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a202c; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .login-card { background: white; padding: 30px; border-radius: 10px; width: 90%; max-width: 360px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        h2 { text-align: center; color: #2b6cb0; margin-bottom: 5px; margin-top: 0; }
        p.sub { text-align: center; color: #718096; margin-bottom: 20px; font-size: 14px; }
        label { font-weight: bold; color: #4a5568; display: block; margin-top: 10px; }
        input { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #cbd5e0; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; background: #2b6cb0; color: white; padding: 12px; border: none; border-radius: 5px; font-size: 16px; margin-top: 20px; cursor: pointer; font-weight: bold; }
        .erro { color: #e53e3e; font-size: 14px; text-align: center; margin-top: 10px; }
        .footer { margin-top: 20px; text-align: center; color: #a0aec0; font-size: 13px; font-weight: bold; }
        .btn-wsp { display: block; text-align: center; background: #25d366; color: white; text-decoration: none; padding: 10px; border-radius: 5px; margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Infonet Telecom</h2>
        <p class="sub">Sistema de Gestão e Desempenho</p>
        {% if erro %}<div class="erro">{{ erro }}</div>{% endif %}
        <form method="POST">
            <label>Usuário:</label>
            <input type="text" name="username" required placeholder="Digite seu login">
            <label>Senha:</label>
            <input type="password" name="senha" required placeholder="Digite sua senha">
            <button type="submit">Entrar no Sistema</button>
        </form>
        <a href="https://wa.me/5521983981601" target="_blank" class="btn-wsp">💬 Suporte WhatsApp</a>
    </div>
    <div class="footer">Desenvolvido por Rafael Soares SEMI DEUS</div>
</body>
</html>
'''

HTML_ADMIN = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Infonet - Dashboard Gestão</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; background: #f7fafc; margin: 0; padding: 15px; }
        .header { display: flex; justify-content: space-between; align-items: center; background: #2b6cb0; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        .header-actions { display: flex; gap: 10px; align-items: center; }
        .header a { color: #fff; text-decoration: none; padding: 8px 12px; border-radius: 5px; font-weight: bold; }
        .btn-logout { background: #c53030; }
        .btn-wsp { background: #25d366; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; }
        h3 { margin-top: 0; color: #2d3748; }
        label { font-weight: bold; display: block; margin-top: 10px; color: #4a5568; }
        input, select, textarea { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #cbd5e0; border-radius: 5px; box-sizing: border-box; }
        button { background: #38a169; color: white; padding: 12px; border: none; border-radius: 5px; font-size: 16px; margin-top: 15px; cursor: pointer; width: 100%; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: left; font-size: 13px; }
        th { background: #edf2f7; color: #2d3748; }
        .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 12px; }
        .bg-ok { background: #38a169; } .bg-pendente { background: #e53e3e; }
        .table-responsive { overflow-x: auto; }
        .chart-container { position: relative; height:300px; width:100%; }
        .footer { text-align: center; padding: 15px; color: #718096; font-size: 13px; font-weight: bold; }
        .btn-gps { color: #2b6cb0; font-weight: bold; text-decoration: none; display: inline-block; margin-top: 4px; }
        .box-fibra { background: #edf2f7; padding: 6px; border-radius: 4px; margin-top: 5px; font-size: 12px; border-left: 3px solid #3182ce; }
        summary { cursor: pointer; font-weight: bold; color: #2b6cb0; padding: 5px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h2>Infonet Telecom - Painel do CEO</h2>
        <div class="header-actions">
            <a href="https://wa.me/5521983981601" target="_blank" class="btn-wsp">💬 Suporte WhatsApp</a>
            <a href="/logout" class="btn-logout">Sair</a>
        </div>
    </div>

    <div class="card">
        <h3>📊 Gráfico de Desempenho Diário dos Técnicos</h3>
        <div class="chart-container">
            <canvas id="graficoDesempenho"></canvas>
        </div>
    </div>

    <div class="card">
        <h3>Nova Ordem de Serviço</h3>
        <form action="/criar_os" method="POST">
            <label>Cliente / Referência:</label><input type="text" name="cliente" required placeholder="Nome do cliente ou ID da Caixa/CTO">
            <label>Endereço completo / CTO:</label><input type="text" name="endereco" required placeholder="Rua, Número, Bairro - Cidade">
            <label>Atribuir ao Técnico de Rua:</label>
            <select name="tecnico_id" required>
                {% for tec in tecnicos %}
                    <option value="{{ tec[0] }}">{{ tec[3] }} ({{ tec[1] }})</option>
                {% endfor %}
            </select>
            <label>Tipo de Serviço:</label>
            <select name="tipo_servico">
                <option value="Instalação">Instalação</option>
                <option value="Reparo / Manutenção">Reparo / Manutenção</option>
                <option value="Fusão / Emenda de Caixa">Fusão / Emenda de Caixa</option>
                <option value="Rompimento / Manutenção de Fibra">Rompimento / Manutenção de Fibra</option>
                <option value="Troca de Drop">Troca de Drop</option>
            </select>
            
            <label>Observação da Gestão para o Técnico (Opcional):</label>
            <textarea name="observacao_admin" rows="2" placeholder="Ex: Levar fusão, escada grande, fibra de 6 FO, etc."></textarea>

            <button type="submit">Designar O.S.</button>
        </form>
    </div>

    <div class="card">
        <h3>Histórico e Detalhes da Rede de Fibra</h3>
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>ID</th><th>Cliente / Local</th><th>Técnico</th><th>Serviço / Obs</th><th>Sinal CTO/ONU</th><th>Detalhes Fibra & Rota</th><th>Tempo</th><th>Status</th><th>Foto</th>
                    </tr>
                </thead>
                <tbody>
                    {% for os in ordens %}
                    <tr>
                        <td>#{{ os[0] }}</td>
                        <td>
                            <b>{{ os[1] }}</b><br>
                            <small>{{ os[2] }}</small><br>
                            <a href="https://www.google.com/maps/search/?api=1&query={{ os[18] }}" target="_blank" class="btn-gps">📍 Abrir Mapa</a>
                        </td>
                        <td><b>{{ os[17] }}</b></td>
                        <td>
                            <b>{{ os[4] }}</b><br>
                            {% if os[5] %}<small style="color: #dd6b20;"><b>Obs:</b> {{ os[5] }}</small>{% endif %}
                        </td>
                        <td>CTO: {{ os[6] or '-' }}<br>ONU: {{ os[7] or '-' }}</td>
                        <td>
                            {% if os[9] or os[10] or os[11] %}
                            <div class="box-fibra">
                                <b>Tipo:</b> {{ os[9] or 'N/I' }}<br>
                                <b>Tubo/Fibra:</b> {{ os[10] or 'N/I' }}<br>
                                <b>Rota:</b> {{ os[11] or 'N/I' }}
                            </div>
                            {% else %}
                            <small style="color: #a0aec0;">Sem registro de fusão de fibra</small>
                            {% endif %}
                        </td>
                        <td>
                            {% if os[16] %}
                                <b>{{ os[16] }} min</b><br><small>Finalizado: {{ os[15] }}</small>
                            {% else %}
                                <i>Em andamento desde {{ os[14] }}</i>
                            {% endif %}
                        </td>
                        <td><span class="badge {{ 'bg-ok' if os[12] == 'Concluído' else 'bg-pendente' }}">{{ os[12] }}</span></td>
                        <td>{% if os[13] %}<a href="/uploads/{{ os[13] }}" target="_blank">Ver Foto</a>{% else %}Sem foto{% endif %}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <details class="card">
        <summary>📑 Log de Acessos dos Técnicos (3 dias auto-limpante)</summary>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 10px 0;">
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>Técnico</th><th>Horário Entrada</th><th>Horário Saída</th><th>Tempo Conectado</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in logs %}
                    <tr>
                        <td><b>{{ log[2] }}</b></td>
                        <td>{{ log[3] }}</td>
                        <td>{{ log[4] or 'Em sessão...' }}</td>
                        <td>
                            {% if log[5] is not none %}
                                <b>{{ log[5] }} min</b>
                            {% else %}
                                <i style="color: #38a169;">Online agora</i>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" style="text-align:center;">Nenhum registro de acesso recente.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </details>

    <div class="footer">Desenvolvido por Rafael Soares SEMI DEUS</div>

    <script>
        const ctx = document.getElementById('graficoDesempenho').getContext('2d');
        const graficoDesempenho = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: {{ chart_labels | safe }},
                datasets: [
                    {
                        label: 'Serviços Concluídos',
                        data: {{ chart_concluidos | safe }},
                        backgroundColor: '#38a169'
                    },
                    {
                        label: 'Serviços Pendentes',
                        data: {{ chart_pendentes | safe }},
                        backgroundColor: '#e53e3e'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } }
                }
            }
        });
    </script>
</body>
</html>
'''

HTML_TECNICO = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Infonet - Área do Técnico</title>
    <style>
        body { font-family: Arial, sans-serif; background: #edf2f7; margin: 0; padding: 12px; }
        .header { display: flex; justify-content: space-between; align-items: center; background: #2b6cb0; color: white; padding: 12px; border-radius: 8px; margin-bottom: 15px; }
        .header-actions { display: flex; gap: 8px; align-items: center; }
        .header a { color: white; text-decoration: none; font-weight: bold; padding: 6px 10px; border-radius: 5px; font-size: 13px; }
        .btn-logout { background: #e53e3e; }
        .btn-wsp { background: #25d366; }
        .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; }
        .score-box { background: #ebf8ff; border-left: 4px solid #3182ce; padding: 10px; margin-bottom: 15px; border-radius: 4px; }
        .obs-box { background: #fffaf0; border-left: 4px solid #dd6b20; padding: 10px; margin: 10px 0; border-radius: 4px; font-size: 13px; color: #744210; }
        .fibra-box { background: #f7fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; margin-top: 15px; }
        label { font-weight: bold; color: #4a5568; display: block; margin-top: 10px; font-size: 13px; }
        input, select, textarea { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #cbd5e0; border-radius: 5px; box-sizing: border-box; }
        button { background: #38a169; color: white; padding: 12px; border: none; border-radius: 5px; font-size: 16px; margin-top: 15px; cursor: pointer; width: 100%; font-weight: bold; }
        .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 12px; }
        .bg-ok { background: #38a169; } .bg-pendente { background: #dd6b20; }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
        .stat-card { background: #edf2f7; padding: 8px; text-align: center; border-radius: 5px; font-weight: bold; }
        .nav-buttons { display: flex; gap: 8px; margin-top: 10px; }
        .btn-nav-gmaps { flex: 1; background: #4285F4; color: white; text-align: center; padding: 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 13px; }
        .btn-nav-waze { flex: 1; background: #33CCFF; color: #111; text-align: center; padding: 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 13px; }
        .footer { text-align: center; padding: 15px; color: #718096; font-size: 13px; font-weight: bold; }
        summary { cursor: pointer; font-weight: bold; color: #2b6cb0; padding: 5px 0; }
    </style>
</head>
<body>
    <div class="header">
        <div><b>Técnico:</b> {{ session['nome'] }}</div>
        <div class="header-actions">
            <a href="https://wa.me/5521983981601" target="_blank" class="btn-wsp">💬 Suporte</a>
            <a href="/logout" class="btn-logout">Sair</a>
        </div>
    </div>

    <div class="card">
        <div class="stat-grid">
            <div class="stat-card" style="color: #2b6cb0;">✅ Concluídas Hoje: {{ concluidas_hoje }}</div>
            <div class="stat-card" style="color: #c53030;">⏳ Pendentes: {{ total_pendentes }}</div>
        </div>

        <div class="score-box">
            <b>Status do Seu Desempenho Hoje:</b><br>
            <span style="font-size: 16px; color: #2b6cb0;">{{ mensagem_feedback }}</span>
        </div>
    </div>

    <h3>📋 Ordens de Serviço Pendentes</h3>

    {% for os in ordens_pendentes %}
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <b>O.S. #{{ os[0] }} - {{ os[4] }}</b>
            <span class="badge bg-pendente">{{ os[13] }}</span>
        </div>
        <p style="margin: 8px 0; color: #2d3748;"><b>Cliente / Local:</b> {{ os[1] }}</p>
        <p style="margin: 8px 0; color: #718096; font-size: 14px;"><b>Endereço:</b> {{ os[2] }}</p>

        {% if os[5] %}
        <div class="obs-box">
            <b>📌 Observação da Gestão:</b><br>
            {{ os[5] }}
        </div>
        {% endif %}
        
        <div class="nav-buttons">
            <a href="https://www.google.com/maps/dir/?api=1&destination={{ os[18] }}" target="_blank" class="btn-nav-gmaps">📍 Rota Google Maps</a>
            <a href="https://waze.com/ul?q={{ os[18] }}&navigate=yes" target="_blank" class="btn-nav-waze">🚗 Rota Waze</a>
        </div>

        <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0 10px 0;">

        <form action="/atender_os/{{ os[0] }}" method="POST" enctype="multipart/form-data">
            <label>Potência CTO (dBm):</label>
            <input type="text" name="potencia_cto" value="{{ os[6] or '' }}" placeholder="Ex: -18.5 dBm">

            <label>Potência ONU Cliente (dBm):</label>
            <input type="text" name="potencia_cliente" value="{{ os[7] or '' }}" placeholder="Ex: -21.0 dBm">

            <div class="fibra-box">
                <b style="color: #2b6cb0; font-size: 14px;">📡 Registro de Fusão de Caixa / Rompimento:</b>
                
                <label>Tipo da Fusão / Fibra:</label>
                <select name="tipo_fusoes">
                    <option value="" {% if not os[9] %}selected{% endif %}>Selecione o tipo...</option>
                    <option value="Link / Atendimento Direto" {% if os[9]=='Link / Atendimento Direto' %}selected{% endif %}>Link / Atendimento Direto</option>
                    <option value="Fibra de Passagem (Trono)" {% if os[9]=='Fibra de Passagem (Trono)' %}selected{% endif %}>Fibra de Passagem (Trono)</option>
                    <option value="Sangria de Cabo" {% if os[9]=='Sangria de Cabo' %}selected{% endif %}>Sangria de Cabo</option>
                    <option value="Emenda de Rompimento" {% if os[9]=='Emenda de Rompimento' %}selected{% endif %}>Emenda de Rompimento</option>
                </select>

                <label>Cor do Tubo Loose e Fibra Fusionada:</label>
                <input type="text" name="cor_tubo_fibra" value="{{ os[10] or '' }}" placeholder="Ex: Tubo Verde / Fibra Laranja (FO 02)">

                <label>Rota da Fibra (Origem / Destino):</label>
                <input type="text" name="origem_destino_rota" value="{{ os[11] or '' }}" placeholder="Ex: Vem da CTO-04 / Vai para CTO-10 (Bairro Centro)">
            </div>

            <label>Descrição Detalhada do Serviço:</label>
            <textarea name="fusoes_detalhes" rows="2" placeholder="Descreva os procedimentos realizados">{{ os[8] or '' }}</textarea>

            <label>Pendências (se houver):</label>
            <textarea name="pendencias" rows="2" placeholder="Observações de pendência">{{ os[12] or '' }}</textarea>

            <label>Status da O.S.:</label>
            <select name="status">
                <option value="Concluído">Concluído</option>
                <option value="Pendente" selected>Pendente</option>
            </select>

            <label>Foto da Instalação / CTO / Caixa / Medidor:</label>
            <input type="file" name="foto" accept="image/*" capture="environment">

            <button type="submit">Finalizar / Atualizar O.S.</button>
        </form>
    </div>
    {% else %}
    <div class="card"><p style="text-align: center; color: #38a169; font-weight: bold;">🎉 Nenhuma O.S. pendente no momento!</p></div>
    {% endfor %}

    <details class="card">
        <summary>📂 Ver Histórico de O.S. Concluídas ({{ ordens_concluidas|length }})</summary>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 10px 0;">
        {% for os in ordens_concluidas %}
            <div style="background: #f7fafc; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #38a169;">
                <div style="display: flex; justify-content: space-between;">
                    <b>O.S. #{{ os[0] }} - {{ os[1] }}</b>
                    <span class="badge bg-ok">Concluído</span>
                </div>
                <small style="color: #718096; display: block; margin-top: 4px;">{{ os[2] }}</small>
                <small style="color: #2d3748; display: block; margin-top: 4px;">Tempo: <b>{{ os[17] or 0 }} min</b> | CTO: {{ os[6] or '-' }} | ONU: {{ os[7] or '-' }}</small>
                {% if os[10] or os[11] %}
                <small style="color: #3182ce; display: block; margin-top: 2px;"><b>Fibra:</b> {{ os[10] or '' }} | <b>Rota:</b> {{ os[11] or '' }}</small>
                {% endif %}
                {% if os[14] %}<a href="/uploads/{{ os[14] }}" target="_blank" style="font-size: 12px; color: #2b6cb0; font-weight: bold; display: inline-block; margin-top: 4px;">Ver Foto Anexada</a>{% endif %}
            </div>
        {% else %}
            <p style="font-size: 13px; color: #718096;">Nenhuma O.S. concluída ainda.</p>
        {% endfor %}
    </details>

    <div class="footer">Desenvolvido por Rafael Soares SEMI DEUS</div>
</body>
</html>
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        username = request.form['username']
        senha = request.form['senha']
        
        limpar_logs_antigos()
        
        conn = sqlite3.connect('banco_os.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND senha = ?", (username, senha))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['nome'] = user[3]
            session['tipo'] = user[4]
            
            login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO logs_acesso (usuario_id, nome_usuario, login_time)
                VALUES (?, ?, ?)
            ''', (user[0], user[3], login_time))
            
            session['log_id'] = cursor.lastrowid
            conn.commit()
            conn.close()

            return redirect(url_for('index'))
        else:
            conn.close()
            erro = "Usuário ou senha incorretos!"
            
    return render_template_string(HTML_LOGIN, erro=erro)

@app.route('/logout')
def logout():
    if 'log_id' in session:
        conn = sqlite3.connect('banco_os.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT login_time FROM logs_acesso WHERE id = ?", (session['log_id'],))
        res = cursor.fetchone()
        
        if res and res[0]:
            try:
                inicio = datetime.strptime(res[0], '%Y-%m-%d %H:%M:%S')
                fim = datetime.now()
                duracao_minutos = int((fim - inicio).total_seconds() / 60)
                data_fim_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                cursor.execute('''
                    UPDATE logs_acesso 
                    SET logout_time = ?, duracao_minutos = ?
                    WHERE id = ?
                ''', (data_fim_str, duracao_minutos, session['log_id']))
                conn.commit()
            except Exception:
                pass
        conn.close()

    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = sqlite3.connect('banco_os.db')
    cursor = conn.cursor()

    if session['tipo'] == 'admin':
        cursor.execute("SELECT * FROM usuarios WHERE tipo = 'tecnico'")
        tecnicos = cursor.fetchall()

        cursor.execute('''
            SELECT ordens_servico.*, usuarios.nome 
            FROM ordens_servico 
            JOIN usuarios ON ordens_servico.tecnico_id = usuarios.id 
            ORDER BY ordens_servico.id DESC
        ''')
        ordens_raw = cursor.fetchall()

        ordens = []
        for row in ordens_raw:
            os_list = list(row)
            os_list.append(urllib.parse.quote(row[2]))
            ordens.append(os_list)

        cursor.execute("SELECT * FROM logs_acesso ORDER BY id DESC LIMIT 50")
        logs = cursor.fetchall()

        labels = [tec[3] for tec in tecnicos]
        concluidos = []
        pendentes = []

        data_hoje = datetime.now().strftime('%Y-%m-%d')

        for tec in tecnicos:
            cursor.execute('''
                SELECT COUNT(*) FROM ordens_servico 
                WHERE tecnico_id = ? AND status = 'Concluído' AND data_fim LIKE ?
            ''', (tec[0], f"{data_hoje}%"))
            concluidos.append(cursor.fetchone()[0])

            cursor.execute('''
                SELECT COUNT(*) FROM ordens_servico 
                WHERE tecnico_id = ? AND status = 'Pendente'
            ''', (tec[0],))
            pendentes.append(cursor.fetchone()[0])

        conn.close()

        import json
        return render_template_string(
            HTML_ADMIN, 
            tecnicos=tecnicos, 
            ordens=ordens, 
            logs=logs,
            chart_labels=json.dumps(labels),
            chart_concluidos=json.dumps(concluidos),
            chart_pendentes=json.dumps(pendentes)
        )
    else:
        tec_id = session['user_id']
        data_hoje = datetime.now().strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT COUNT(*) FROM ordens_servico 
            WHERE tecnico_id = ? AND status = 'Concluído' AND data_fim LIKE ?
        ''', (tec_id, f"{data_hoje}%"))
        concluidas_hoje = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*) FROM ordens_servico 
            WHERE tecnico_id = ? AND status = 'Pendente'
        ''', (tec_id,))
        total_pendentes = cursor.fetchone()[0]

        if concluidas_hoje >= 6:
            mensagem_feedback = "🔥 Excelente! Meta diária superada com sucesso!"
        elif concluidas_hoje >= 4:
            mensagem_feedback = "👍 Ótimo ritmo! Continue assim."
        else:
            mensagem_feedback = "🚀 Bom trabalho! Mantenha a atenção aos prazos."

        cursor.execute('''
            SELECT * FROM ordens_servico 
            WHERE tecnico_id = ? AND status = 'Pendente' 
            ORDER BY id DESC
        ''', (tec_id,))
        pendentes_raw = cursor.fetchall()

        ordens_pendentes = []
        for row in pendentes_raw:
            os_list = list(row)
            os_list.append(urllib.parse.quote(row[2]))
            ordens_pendentes.append(os_list)

        cursor.execute('''
            SELECT * FROM ordens_servico 
            WHERE tecnico_id = ? AND status = 'Concluído' 
            ORDER BY id DESC LIMIT 10
        ''', (tec_id,))
        ordens_concluidas = cursor.fetchall()

        conn.close()

        return render_template_string(
            HTML_TECNICO, 
            ordens_pendentes=ordens_pendentes,
            ordens_concluidas=ordens_concluidas,
            concluidas_hoje=concluidas_hoje,
            total_pendentes=total_pendentes,
            mensagem_feedback=mensagem_feedback
        )

@app.route('/criar_os', methods=['POST'])
@login_required
def criar_os():
    if session['tipo'] != 'admin':
        return redirect(url_for('index'))

    cliente = request.form['cliente']
    endereco = request.form['endereco']
    tecnico_id = request.form['tecnico_id']
    tipo_servico = request.form['tipo_servico']
    observacao_admin = request.form.get('observacao_admin', '')
    data_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect('banco_os.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ordens_servico (cliente, endereco, tecnico_id, tipo_servico, observacao_admin, status, data_inicio)
        VALUES (?, ?, ?, ?, ?, 'Pendente', ?)
    ''', (cliente, endereco, tecnico_id, tipo_servico, observacao_admin, data_inicio))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/atender_os/<int:os_id>', methods=['POST'])
@login_required
def atender_os(os_id):
    potencia_cto = request.form.get('potencia_cto', '')
    potencia_cliente = request.form.get('potencia_cliente', '')
    fusoes_detalhes = request.form.get('fusoes_detalhes', '')
    tipo_fusoes = request.form.get('tipo_fusoes', '')
    cor_tubo_fibra = request.form.get('cor_tubo_fibra', '')
    origem_destino_rota = request.form.get('origem_destino_rota', '')
    pendencias = request.form.get('pendencias', '')
    status = request.form.get('status', 'Pendente')

    foto_nome = None
    if 'foto' in request.files:
        foto = request.files['foto']
        if foto and foto.filename != '':
            ext = foto.filename.rsplit('.', 1)[-1]
            foto_nome = f"os_{os_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_nome))

    conn = sqlite3.connect('banco_os.db')
    cursor = conn.cursor()

    if status == 'Concluído':
        cursor.execute("SELECT data_inicio FROM ordens_servico WHERE id = ?", (os_id,))
        res = cursor.fetchone()
        duracao = None
        data_fim = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if res and res[0]:
            try:
                dt_inicio = datetime.strptime(res[0], '%Y-%m-%d %H:%M:%S')
                duracao = int((datetime.now() - dt_inicio).total_seconds() / 60)
            except Exception:
                pass

        if foto_nome:
            cursor.execute('''
                UPDATE ordens_servico
                SET potencia_cto=?, potencia_cliente=?, fusoes_detalhes=?, tipo_fusoes=?, cor_tubo_fibra=?, origem_destino_rota=?, pendencias=?, status=?, foto_nome=?, data_fim=?, duracao_minutos=?
                WHERE id=?
            ''', (potencia_cto, potencia_cliente, fusoes_detalhes, tipo_fusoes, cor_tubo_fibra, origem_destino_rota, pendencias, status, foto_nome, data_fim, duracao, os_id))
        else:
            cursor.execute('''
                UPDATE ordens_servico
                SET potencia_cto=?, potencia_cliente=?, fusoes_detalhes=?, tipo_fusoes=?, cor_tubo_fibra=?, origem_destino_rota=?, pendencias=?, status=?, data_fim=?, duracao_minutos=?
                WHERE id=?
            ''', (potencia_cto, potencia_cliente, fusoes_detalhes, tipo_fusoes, cor_tubo_fibra, origem_destino_rota, pendencias, status, data_fim, duracao, os_id))
    else:
        if foto_nome:
            cursor.execute('''
                UPDATE ordens_servico
                SET potencia_cto=?, potencia_cliente=?, fusoes_detalhes=?, tipo_fusoes=?, cor_tubo_fibra=?, origem_destino_rota=?, pendencias=?, status=?, foto_nome=?
                WHERE id=?
            ''', (potencia_cto, potencia_cliente, fusoes_detalhes, tipo_fusoes, cor_tubo_fibra, origem_destino_rota, pendencias, status, foto_nome, os_id))
        else:
            cursor.execute('''
                UPDATE ordens_servico
                SET potencia_cto=?, potencia_cliente=?, fusoes_detalhes=?, tipo_fusoes=?, cor_tubo_fibra=?, origem_destino_rota=?, pendencias=?, status=?
                WHERE id=?
            ''', (potencia_cto, potencia_cliente, fusoes_detalhes, tipo_fusoes, cor_tubo_fibra, origem_destino_rota, pendencias, status, os_id))

    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
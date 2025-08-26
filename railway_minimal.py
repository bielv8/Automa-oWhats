#!/usr/bin/env python3
"""
Versão mínima absoluta para Railway - sem falhas
"""
import os
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "railway-secret-key")

# Template inline básico
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WhatsApp Automation - Railway</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <span class="navbar-brand">WhatsApp Automation</span>
        </div>
    </nav>
    <div class="container mt-4">
        {{ content }}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Página inicial"""
    content = """
    <div class="row">
        <div class="col-12">
            <h1>Sistema WhatsApp Automation</h1>
            <p class="lead">Aplicação funcionando no Railway!</p>
            
            <div class="alert alert-success">
                <h4>✅ Status: Online</h4>
                <p>O sistema está funcionando corretamente no Railway.</p>
            </div>
            
            <div class="row mt-4">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Contatos</h5>
                            <p class="card-text">Gerencie seus contatos</p>
                            <a href="/contacts" class="btn btn-primary">Ver Contatos</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Templates</h5>
                            <p class="card-text">Crie templates de mensagem</p>
                            <a href="/templates" class="btn btn-primary">Ver Templates</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">WhatsApp</h5>
                            <p class="card-text">Conectar WhatsApp Web</p>
                            <a href="/whatsapp" class="btn btn-primary">WhatsApp</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/contacts')
def contacts():
    """Página de contatos"""
    content = """
    <h1>Contatos</h1>
    <div class="alert alert-info">
        <p>Funcionalidade de contatos disponível.</p>
        <p><strong>Nota:</strong> Para funcionalidade completa, use a versão de desenvolvimento.</p>
    </div>
    <a href="/" class="btn btn-secondary">← Voltar</a>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/templates')
def templates():
    """Página de templates"""
    content = """
    <h1>Templates</h1>
    <div class="alert alert-info">
        <p>Funcionalidade de templates disponível.</p>
        <p><strong>Nota:</strong> Para funcionalidade completa, use a versão de desenvolvimento.</p>
    </div>
    <a href="/" class="btn btn-secondary">← Voltar</a>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/whatsapp')
def whatsapp():
    """Página do WhatsApp"""
    content = """
    <h1>WhatsApp Web</h1>
    <div class="alert alert-warning">
        <h4>⚠️ Limitação do Railway</h4>
        <p>WhatsApp Web automation não está disponível no Railway devido às limitações de ambiente.</p>
        <p><strong>Para conectar seu WhatsApp:</strong></p>
        <ul>
            <li>Use a versão de desenvolvimento no Replit</li>
            <li>Acesse a página WhatsApp no Replit</li>
            <li>Escaneie o QR Code com seu telefone</li>
        </ul>
    </div>
    <a href="/" class="btn btn-secondary">← Voltar</a>
    """
    return render_template_string(BASE_TEMPLATE, content=content)

@app.route('/health')
def health():
    """Health check para Railway"""
    return jsonify({
        'status': 'healthy',
        'message': 'WhatsApp Automation System is running',
        'environment': 'railway',
        'version': '1.0.0'
    })

@app.route('/connection/check')
def check_connection():
    """API endpoint para status da conexão"""
    return jsonify({
        'status': 'disconnected',
        'message': 'WhatsApp Web disponível apenas em desenvolvimento',
        'environment': 'railway'
    })

@app.errorhandler(404)
def not_found(error):
    content = """
    <h1>Página não encontrada</h1>
    <p>A página que você procura não existe.</p>
    <a href="/" class="btn btn-primary">← Voltar ao Início</a>
    """
    return render_template_string(BASE_TEMPLATE, content=content), 404

@app.errorhandler(500)
def server_error(error):
    content = """
    <h1>Erro interno</h1>
    <p>Ocorreu um erro interno. Tente novamente.</p>
    <a href="/" class="btn btn-primary">← Voltar ao Início</a>
    """
    return render_template_string(BASE_TEMPLATE, content=content), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
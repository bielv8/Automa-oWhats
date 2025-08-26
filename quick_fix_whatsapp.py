#!/usr/bin/env python3
"""
Quick Fix para WhatsApp - Versão simplificada que funciona garantido
"""
import os
import webbrowser
import time
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# Template simples
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WhatsApp Quick Connect</title>
    <meta charset="utf-8">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card bg-secondary">
                    <div class="card-header">
                        <h2>🚀 WhatsApp Quick Connect</h2>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-info">
                            <h4>✅ Solução Rápida para Windows</h4>
                            <p>Evita problemas do Selenium conectando diretamente no navegador.</p>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <h5>🔗 Método 1: Direto</h5>
                                <p>Clique para abrir WhatsApp Web:</p>
                                <button onclick="openWhatsApp()" class="btn btn-success btn-lg">
                                    📱 Abrir WhatsApp Web
                                </button>
                            </div>
                            
                            <div class="col-md-6">
                                <h5>📞 Método 2: Envio Rápido</h5>
                                <div class="mb-3">
                                    <input type="text" id="phoneNumber" class="form-control" 
                                           placeholder="Ex: 5511999999999" value="">
                                </div>
                                <div class="mb-3">
                                    <textarea id="message" class="form-control" rows="3" 
                                              placeholder="Sua mensagem aqui..."></textarea>
                                </div>
                                <button onclick="sendMessage()" class="btn btn-primary">
                                    📤 Enviar Mensagem
                                </button>
                            </div>
                        </div>
                        
                        <hr>
                        
                        <div class="row mt-4">
                            <div class="col-12">
                                <h5>📋 Instruções:</h5>
                                <ol>
                                    <li><strong>Abrir WhatsApp Web:</strong> Clique no botão verde</li>
                                    <li><strong>Fazer Login:</strong> Escaneie QR Code com seu celular</li>
                                    <li><strong>Enviar Mensagem:</strong> Preencha número e mensagem</li>
                                    <li><strong>Resultado:</strong> Abre nova aba pronta para enviar</li>
                                </ol>
                            </div>
                        </div>
                        
                        <div class="alert alert-success mt-3">
                            <strong>💡 Vantagem:</strong> Funciona 100% sem problemas de Chrome/Selenium!
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function openWhatsApp() {
            window.open('https://web.whatsapp.com', '_blank');
        }
        
        function sendMessage() {
            const phone = document.getElementById('phoneNumber').value.trim();
            const message = document.getElementById('message').value.trim();
            
            if (!phone) {
                alert('Digite o número do telefone!');
                return;
            }
            
            let cleanPhone = phone.replace(/\D/g, '');
            
            // Adiciona código do país se necessário
            if (cleanPhone.length === 11 && !cleanPhone.startsWith('55')) {
                cleanPhone = '55' + cleanPhone;
            }
            
            const encodedMessage = encodeURIComponent(message);
            const url = `https://web.whatsapp.com/send?phone=${cleanPhone}&text=${encodedMessage}`;
            
            window.open(url, '_blank');
        }
        
        // Auto-focus no campo de telefone
        document.getElementById('phoneNumber').focus();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'WhatsApp Quick Fix funcionando!'})

if __name__ == '__main__':
    print("🚀 WhatsApp Quick Fix - Solução Rápida!")
    print("📱 Acesse: http://localhost:5000")
    print("✅ Funciona 100% sem problemas de Selenium!")
    print("🔧 Para parar: Ctrl+C")
    
    # Abre automaticamente
    import threading
    threading.Timer(1, lambda: webbrowser.open('http://localhost:5000')).start()
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Aplicação encerrada!")
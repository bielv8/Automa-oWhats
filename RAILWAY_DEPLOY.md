# Instruções de Deploy no Railway

## Aplicação Corrigida para Railway

O sistema agora tem dois arquivos principais:

### Para desenvolvimento (Replit):
- Use `app.py` (arquivo principal com funcionalidade completa do WhatsApp)
- Inclui Selenium WebDriver para WhatsApp Web
- Suporte total ao Firebase e outras integrações

### Para produção (Railway):
- Use `railway_app.py` (versão simplificada para produção)
- Remove dependências do Selenium (não disponível em ambiente Railway)
- Interface simplificada mas funcional
- Pronto para PostgreSQL do Railway

## Configuração do Railway

1. **Variáveis de Ambiente Necessárias:**
   ```
   SESSION_SECRET=sua-chave-secreta-aqui
   DATABASE_URL=postgresql://... (fornecido automaticamente pelo Railway)
   ```

2. **Comando de Deploy:**
   ```
   web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 railway_app:app
   ```

3. **Arquivos Importantes:**
   - `railway_app.py` - Aplicação principal para Railway
   - `models_railway.py` - Modelos sem imports circulares  
   - `Procfile` - Configurado para usar railway_app
   - `requirements-railway.txt` - Dependências para produção

## Funcionalidades Disponíveis no Railway

✅ **Funcionam normalmente:**
- Gerenciamento de contatos
- Criação de templates de mensagem
- Criação de campanhas
- Histórico de atividades
- Interface web completa

⚠️ **Limitações no Railway:**
- WhatsApp Web automation (Selenium) não funciona em produção
- Mensagem informativa será exibida na tela de conexão
- Para usar WhatsApp, desenvolva localmente no Replit

## Como Deploy no Railway

1. Conecte seu repositório no Railway
2. Railway detectará automaticamente o `Procfile`
3. Defina a variável `SESSION_SECRET`
4. Deploy será feito automaticamente

Agora seu app deve rodar sem problemas no Railway!
# Deploy no Railway - WhatsApp Automation System

## Pré-requisitos
1. Conta no Railway (railway.app)
2. GitHub/GitLab conectado ao Railway

## ⚠️ SOLUÇÃO PARA ERRO DE SNAPSHOT

Se aparecer "Failed to snapshot repository", faça:

1. **Limpe arquivos cache localmente:**
   ```bash
   git rm --cached -r .cache/ || true
   git add .gitignore
   git commit -m "Clean cache files for Railway deploy"
   ```

2. **Force push se necessário:**
   ```bash
   git push --force-with-lease
   ```

3. **Tente deploy novamente no Railway**

## Passos para Deploy

### 1. Conectar Repositório
1. Acesse railway.app
2. Clique em "New Project"
3. Selecione "Deploy from GitHub repo"
4. Escolha seu repositório

### 2. Configurar Variáveis de Ambiente
No Railway, vá em Settings > Environment Variables e adicione:

```
SESSION_SECRET=sua-chave-secreta-super-forte-aqui
DATABASE_URL=(será configurado automaticamente com PostgreSQL)
RAILWAY_ENVIRONMENT=production
```

### 3. Adicionar PostgreSQL
1. Na dashboard do projeto
2. Clique em "+ New Service"
3. Selecione "PostgreSQL"
4. O Railway conectará automaticamente

### 4. Configurar Buildpacks (se necessário)
```
heroku/python
https://github.com/heroku/heroku-buildpack-apt
```

### 5. Deploy Automático
O Railway detectará automaticamente:
- ✅ `Procfile` - Comando de inicialização
- ✅ `runtime.txt` - Versão do Python
- ✅ `Aptfile` - Dependências do sistema (Firefox)
- ✅ `pyproject.toml` - Dependências Python

## Funcionalidades que Funcionarão 100%

### ✅ WhatsApp Web Real
- Firefox headless otimizado para Railway
- QR codes reais do WhatsApp
- Conexão estável ao WhatsApp Web
- Captura de screenshots para QR codes

### ✅ Sistema Completo
- Gerenciamento de contatos
- Templates de mensagem
- Campanhas automatizadas
- Histórico completo
- Interface responsiva

### ✅ Banco de Dados
- PostgreSQL gerenciado pelo Railway
- Backup automático
- Escalabilidade automática

### ✅ Performance
- Gunicorn com workers otimizados
- Timeouts configurados
- Logs detalhados

## URLs Importantes
- **App**: https://seu-projeto.railway.app
- **Dashboard**: https://railway.app/dashboard
- **Logs**: Disponíveis no dashboard Railway

## Monitoramento
- Logs em tempo real no Railway
- Health checks automáticos
- Restart automático em caso de falha

## Troubleshooting

### Se o deploy falhar:
1. Verifique os logs no Railway
2. Confirme todas as variáveis de ambiente
3. Verifique se o PostgreSQL está conectado

### Se o WhatsApp não conectar:
1. Aguarde 1-2 minutos após deploy
2. Tente reconectar na interface
3. Verifique logs para erros do Selenium

## Custos Estimados Railway
- **Hobby Plan**: $5/mês (500 horas de execução)
- **Pro Plan**: $20/mês (execução ilimitada)
- **PostgreSQL**: Incluído nos planos

Seu sistema estará 100% funcional e pronto para produção! 🚀
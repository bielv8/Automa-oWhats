# WhatsApp Automation Desktop - Guia de Instalação

## 📋 O que é?

Uma versão desktop standalone do sistema WhatsApp Automation que roda localmente no seu computador, sem precisar de deploy ou navegador online.

## 🚀 Como Instalar e Usar

### Método 1: Execução Automática (Recomendado)

1. **Download dos arquivos:**
   - `whatsapp_desktop.py` (aplicação principal)
   - `run_desktop.py` (launcher automático)
   - Copie também a pasta `templates/` com os arquivos HTML

2. **Execute:**
   ```bash
   python run_desktop.py
   ```

O launcher vai:
- ✅ Verificar se Python 3.8+ está instalado
- ✅ Instalar dependências automaticamente
- ✅ Abrir o navegador automaticamente
- ✅ Iniciar a aplicação

### Método 2: Instalação Manual

1. **Instale Python 3.8+** (se não tiver)
2. **Instale dependências:**
   ```bash
   pip install flask werkzeug
   ```
3. **Execute a aplicação:**
   ```bash
   python whatsapp_desktop.py
   ```

## 🌟 Funcionalidades

### ✅ Funcionam Completamente:
- **Interface web moderna** - Acesso via navegador local
- **Gerenciamento de contatos** - Adicionar, listar, buscar
- **Import de CSV** - Importação em lote de contatos
- **Templates de mensagem** - Criar e gerenciar templates
- **Campanhas** - Criar e organizar campanhas
- **Histórico completo** - Log de todas as atividades
- **Database SQLite** - Armazenamento local seguro

### 🔧 Para WhatsApp Automation:
Para conectar com WhatsApp Web, instale dependências extras:
```bash
pip install selenium webdriver-manager qrcode pillow
```

## 📁 Estrutura dos Arquivos

```
WhatsApp Desktop/
├── whatsapp_desktop.py      # Aplicação principal
├── run_desktop.py           # Launcher automático
├── requirements_desktop.txt # Lista de dependências
├── whatsapp_desktop.db      # Database (criado automaticamente)
└── templates/               # Templates HTML (copie do projeto)
    ├── base.html
    ├── index.html
    ├── contacts.html
    ├── templates.html
    ├── campaigns.html
    ├── history.html
    └── whatsapp.html
```

## 🔧 Como Usar

1. **Execute** `python run_desktop.py`
2. **Acesse** `http://localhost:5000` no navegador
3. **Use normalmente** - todas as funcionalidades disponíveis
4. **Para parar** - Ctrl+C no terminal ou acesse `/shutdown`

## 💾 Dados

- **Database:** `whatsapp_desktop.db` (SQLite)
- **Backup:** Copie o arquivo .db para fazer backup
- **Portável:** Leve a pasta inteira para outro computador

## 🆘 Solução de Problemas

### "Python não encontrado"
- Instale Python 3.8+ de python.org
- No Windows, marque "Add to PATH"

### "Módulo não encontrado"
```bash
pip install flask werkzeug
```

### "Porta em uso"
- Feche outros servidores na porta 5000
- Ou modifique a porta no código

### "Erro de permissão no database"
- Execute como administrador (se necessário)
- Verifique permissões da pasta

## 🎯 Vantagens da Versão Desktop

✅ **Sem deploy** - Roda local  
✅ **Sem internet** - Funciona offline  
✅ **Sem limites** - Use quanto quiser  
✅ **Seus dados** - Tudo fica no seu PC  
✅ **Portável** - Leve para qualquer lugar  
✅ **Rápido** - Performance máxima  

**Agora você tem um sistema completo funcionando 100% local!** 🎉
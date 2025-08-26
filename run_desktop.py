#!/usr/bin/env python3
"""
Launcher para WhatsApp Automation Desktop
Execute este arquivo para iniciar a aplicação
"""
import sys
import os
import subprocess
import platform

def check_python():
    """Verifica se Python está instalado"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ é necessário")
        print(f"Versão atual: {version.major}.{version.minor}")
        return False
    return True

def install_requirements():
    """Instala dependências necessárias"""
    print("🔄 Verificando dependências...")
    
    required_packages = ['flask', 'werkzeug']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"📦 Instalando dependências: {', '.join(missing_packages)}")
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {package} instalado")
            except subprocess.CalledProcessError:
                print(f"❌ Erro ao instalar {package}")
                return False
    
    print("✅ Todas as dependências estão instaladas")
    return True

def main():
    """Função principal do launcher"""
    print("🚀 WhatsApp Automation Desktop Launcher")
    print("=" * 50)
    
    # Verifica Python
    if not check_python():
        input("Pressione Enter para sair...")
        return
    
    # Instala dependências
    if not install_requirements():
        print("❌ Falha na instalação das dependências")
        input("Pressione Enter para sair...")
        return
    
    # Executa a aplicação
    try:
        print("🔄 Iniciando aplicação...")
        from whatsapp_desktop import main as run_app
        run_app()
    except ImportError as e:
        print(f"❌ Erro ao importar aplicação: {e}")
        print("Certifique-se que whatsapp_desktop.py está no mesmo diretório")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    
    input("\nPressione Enter para sair...")

if __name__ == '__main__':
    main()
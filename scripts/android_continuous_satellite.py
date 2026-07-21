import os
import sys

# HACK PARA O TERMUX: O Android esconde as bibliotecas do sistema,
# então enganamos o Python para apontar direto para o arquivo do Termux.
# Fazemos isso apenas se estivermos realmente no Termux nativo, e não em um proot (Ubuntu).
import ctypes.util
import os

original_find_library = ctypes.util.find_library

def patch_find_library(name):
    if name == 'portaudio':
        # Verifica se estamos rodando no Termux nativo (e não no proot Ubuntu)
        if "PREFIX" in os.environ and "/com.termux/" in os.environ["PREFIX"]:
            termux_path = '/data/data/com.termux/files/usr/lib/libportaudio.so'
            if os.path.exists(termux_path):
                return termux_path
    return original_find_library(name)

ctypes.util.find_library = patch_find_library

# Adiciona o diretório raiz ao path para que possamos importar `devices.android_satellite`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from devices.android_satellite.main import main
except ImportError as e:
    print(f"Erro ao importar o módulo devices.android_satellite.main: {e}")
    print("Certifique-se de estar rodando a partir da raiz do projeto.")
    sys.exit(1)

if __name__ == "__main__":
    main()

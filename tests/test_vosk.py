import sys
try:
    import vosk
    print("Vosk installed!")
except ImportError:
    print("Vosk missing!")

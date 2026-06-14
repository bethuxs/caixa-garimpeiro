#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Ejecutor de Tests: Estructura de Loops Ciudad-Modalidade
================================================================================

Script que ejecuta:
1. test_loop_structure.py - Tests de estructura del código
2. test_loop_behavior.py - Tests de comportamiento con simulación

Uso:
    python run_all_tests.py
"""

import subprocess
import sys
import os
from pathlib import Path


def print_header(text):
    """Imprimir header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def run_test_file(filepath):
    """Ejecutar un archivo de tests"""
    print(f"\n📋 Ejecutando: {filepath}")
    print("-"*70)
    
    result = subprocess.run(
        [sys.executable, filepath],
        cwd=Path(__file__).parent,
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0


def main():
    """Función principal"""
    print_header("TESTS DE ESTRUCTURA: LOOPS CIUDAD-MODALIDADE")
    
    # Archivos de tests
    test_files = [
        "test_loop_structure.py",
        "test_loop_behavior.py",
        "test_scraper_extraction.py",
        "test_web_security.py",
    ]
    
    # Verificar que existen
    cwd = Path(__file__).parent
    for test_file in test_files:
        test_path = cwd / test_file
        if not test_path.exists():
            print(f"❌ Archivo no encontrado: {test_path}")
            return 1
    
    # Ejecutar tests
    results = {}
    for test_file in test_files:
        success = run_test_file(str(cwd / test_file))
        results[test_file] = success
    
    # Resumen final
    print_header("RESUMEN FINAL")
    
    total_tests = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total_tests - passed
    
    for test_file, success in results.items():
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"{status}: {test_file}")
    
    print("\n" + "="*70)
    print(f"Total: {total_tests} archivos de tests")
    print(f"✅ Pasados: {passed}")
    print(f"❌ Fallidos: {failed}")
    print("="*70 + "\n")
    
    if failed == 0:
        print("🎉 ¡TODOS LOS TESTS PASARON!")
        print("\nValidaciones principales:")
        print("  ✓ Búsqueda independiente por ciudad/modalidade")
        print("  ✓ Extracción real de precio, bairro y modalidade")
        print("  ✓ API de sincronización protegida por token")
        print("  ✓ Endpoint debug oculto fuera de FLASK_DEBUG=true")
        print("\n")
        return 0
    else:
        print("❌ Algunos tests fallaron. Revisa los logs arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

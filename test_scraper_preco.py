#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de validación: Verifica que scraper._extrair_preco() funciona correctamente
"""

import sys
sys.path.insert(0, '/home/beto/www/caixa')

from scraper import CaixaScraper

# ============================================================================
# EJEMPLOS DE TEST
# ============================================================================

# Ejemplo 1: Curitiba - Tingui (del usuario)
html_ejemplo_1 = """
Valor de avaliação: R$ 2.280.000,00
Valor mínimo de venda: R$ 1.453.076,60 ( descuento de 36,27%)
"""

# Ejemplo 2: Venda Online (descuento alto)
html_ejemplo_2 = """
Valor de avaliação: R$ 356.800,00
Valor mínimo de venda: R$ 141.047,00 ( descuento de 60,47%)
"""

# Ejemplo 3: Solo avaliação (sin mínimo)
html_ejemplo_3 = """
Valor de avaliação: R$ 500.000,00
"""

# Ejemplo 4: Precios más bajos
html_ejemplo_4 = """
Valor de avaliação: R$ 45.500,00
Valor mínimo de venda: R$ 22.750,00 ( descuento de 50%)
"""

print("=" * 80)
print("TEST DE VALIDACIÓN - CaixaScraper._extrair_preco()")
print("=" * 80)

tests = [
    ("Curitiba - Tingui", html_ejemplo_1, 1453076.60),
    ("Venda Online Alto Descuento", html_ejemplo_2, 141047.00),
    ("Solo Avaliação", html_ejemplo_3, 500000.00),
    ("Precio Bajo", html_ejemplo_4, 22750.00),
]

pasados = 0
total = len(tests)

for nombre, html, esperado in tests:
    resultado = CaixaScraper._extrair_preco(html)
    match = abs(resultado - esperado) < 0.01
    
    status = "✅ PASADO" if match else "❌ FALLIDO"
    pasados += match
    
    print(f"\n[{nombre}]")
    print(f"  HTML: {html[:80]}...")
    print(f"  Esperado:  R$ {esperado:>12,.2f}")
    print(f"  Resultado: R$ {resultado:>12,.2f}")
    print(f"  {status}")

print("\n" + "=" * 80)
print(f"RESULTADO FINAL: {pasados}/{total} tests pasados")
if pasados == total:
    print("🎉 ¡TODOS LOS TESTS PASARON!")
else:
    print(f"⚠️  {total - pasados} tests fallaron")
print("=" * 80)

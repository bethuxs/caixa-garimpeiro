#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de validación: Verifica la extracción de precio
(versión standalone sin dependencias)
"""

import re

# Copiar la función directamente
@staticmethod
def _extrair_preco(texto: str) -> float:
    """
    Extrai valor numérico de preço de uma string.
    Prioriza "Valor mínimo de venda" sobre "Valor de avaliação".
    """
    if not texto:
        return 0.0
    
    try:
        # Limpieza inicial
        texto_limpio = texto.strip()
        
        # PREFERENCIA 1: Extraer "Valor mínimo de venda" (lo que se paga realmente)
        # Formato: "Valor mínimo de venda: R$ 1.453.076,60"
        match_minimo = re.search(r"Valor\s+mínimo\s+de\s+venda:\s*R\$\s*([\d.]+,\d+)", texto_limpio)
        if match_minimo:
            valor_str = match_minimo.group(1)
            valor = float(valor_str.replace(".", "").replace(",", "."))
            return valor
        
        # PREFERENCIA 2: Extraer "Valor de avaliação" (si no hay mínimo)
        # Formato: "Valor de avaliação: R$ 2.280.000,00"
        match_avaliacao = re.search(r"Valor\s+de\s+avaliação:\s*R\$\s*([\d.]+,\d+)", texto_limpio)
        if match_avaliacao:
            valor_str = match_avaliacao.group(1)
            valor = float(valor_str.replace(".", "").replace(",", "."))
            return valor
        
        # FALLBACK: Método genérico si no encuentra ninguno de los anteriores
        numeros = re.sub(r"[^0-9,.\s]", "", texto_limpio)
        
        # Si houver múltiplos separadores, assume vírgula como decimal
        if numeros.count(",") > 1:
            numeros = numeros.replace(".", "").replace(",", ".")
        elif numeros.count(".") > 1:
            numeros = numeros.replace(".", "", numeros.count(".") - 1)
        else:
            # Trata vírgula como decimal
            numeros = numeros.replace(".", "").replace(",", ".")
        
        return float(numeros) if numeros else 0.0
        
    except (ValueError, AttributeError):
        return 0.0


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

# Ejemplo 5: El ejemplo exacto del usuario
html_ejemplo_5 = """
Valor de avaliação: R$ 2.280.000,00
Valor mínimo de venda: R$ 1.453.076,60 ( descuento de 36,27%)
Casa - 410,32 m2, 3 quarto(s) - Venda Direta Online
Número do imóvel: 155552855307-5
RUA JOAO BATISTA TRENTIN,N. 796 200,  
"""

print("=" * 80)
print("TEST DE VALIDACIÓN - Extracción de Precios")
print("=" * 80)

tests = [
    ("Curitiba - Tingui", html_ejemplo_1, 1453076.60),
    ("Venda Online Alto Descuento", html_ejemplo_2, 141047.00),
    ("Solo Avaliação", html_ejemplo_3, 500000.00),
    ("Precio Bajo", html_ejemplo_4, 22750.00),
    ("Ejemplo EXACTO del Usuario", html_ejemplo_5, 1453076.60),
]

pasados = 0
total = len(tests)

for nombre, html, esperado in tests:
    resultado = _extrair_preco(html)
    match = abs(resultado - esperado) < 0.01
    
    status = "✅ PASADO" if match else "❌ FALLIDO"
    pasados += match
    
    print(f"\n[{nombre}]")
    print(f"  Esperado:  R$ {esperado:>12,.2f}")
    print(f"  Resultado: R$ {resultado:>12,.2f}")
    print(f"  {status}")
    
    if not match:
        print(f"  ERROR: Diferencia de R$ {abs(resultado - esperado):,.2f}")

print("\n" + "=" * 80)
print(f"RESULTADO FINAL: {pasados}/{total} tests pasados")
if pasados == total:
    print("🎉 ¡TODOS LOS TESTS PASARON!")
    print("\n✅ La función _extrair_preco() está correctamente implementada")
    print("✅ Extrae correctamente 'Valor mínimo de venda'")
    print("✅ Maneja correctamente valores formateados con puntos y comas")
else:
    print(f"⚠️  {total - pasados} tests fallaron")
print("=" * 80)

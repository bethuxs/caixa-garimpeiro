#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test para verificar extracción de precios y descuentos.
Prueba con ejemplos reales del portal Caixa.
"""

import re
from typing import Tuple, Optional

# Copiar la función de extracción del scraper
@staticmethod
def _extrair_preco(texto: str) -> float:
    """
    Extrae el precio numérico de un texto.
    Busca "Valor mínimo de venda" primero, si no encuentra usa "Valor de avaliação"
    """
    if not texto:
        return 0.0
    
    # Limpieza inicial
    texto_limpio = texto.strip()
    
    # Intentar extraer "Valor mínimo de venda" primero
    # Formato: "Valor mínimo de venda: R$ 1.453.076,60"
    match_minimo = re.search(r"Valor\s+mínimo\s+de\s+venda:\s*R\$\s*([\d.]+,\d+)", texto_limpio)
    if match_minimo:
        valor_str = match_minimo.group(1)
        try:
            # Convertir "1.453.076,60" a float 1453076.60
            valor = float(valor_str.replace(".", "").replace(",", "."))
            print(f"✓ Extraído VALOR MÍNIMO: {valor} (de: {valor_str})")
            return valor
        except:
            pass
    
    # Si no encuentra "mínimo", intentar "Valor de avaliação"
    match_avaliacao = re.search(r"Valor\s+de\s+avaliação:\s*R\$\s*([\d.]+,\d+)", texto_limpio)
    if match_avaliacao:
        valor_str = match_avaliacao.group(1)
        try:
            valor = float(valor_str.replace(".", "").replace(",", "."))
            print(f"✓ Extraído VALOR DE AVALIAÇÃO: {valor} (de: {valor_str})")
            return valor
        except:
            pass
    
    # Si llega aquí, retornar 0
    print(f"⚠️ No se encontró precio en: {texto_limpio[:100]}...")
    return 0.0


def extrair_descuento(texto: str) -> Tuple[float, str]:
    """
    Extrae el descuento de un inmueble.
    Busca el patrón "descuento de XX,XX%)"
    """
    if not texto:
        return 0.0, ""
    
    # Buscar el descuento en porcentaje
    # Formato: "descuento de 36,27%)"
    match = re.search(r"descuento\s+de\s+([\d,]+)%\)", texto)
    if match:
        descuento_str = match.group(1)
        try:
            descuento = float(descuento_str.replace(",", "."))
            print(f"✓ Extraído DESCUENTO: {descuento}% (de: {descuento_str}%)")
            return descuento, descuento_str
        except:
            pass
    
    print(f"⚠️ No se encontró descuento en: {texto[:100]}...")
    return 0.0, ""


# ============================================================================
# EJEMPLOS DE TEST
# ============================================================================

# Ejemplo 1: Curitiba - Tingui (del usuario)
html_ejemplo_1 = """
<span><font style="font-size:0.80em;">Valor de avaliação: R$ 2.280.000,00<br><b>Valor mínimo de venda: R$ 1.453.076,60</b> ( descuento de 36,27%)</font></span>
"""

# Ejemplo 2: Venda Online (de los tests anteriores)
html_ejemplo_2 = """
<span><font style="font-size:0.80em;">Valor de avaliação: R$ 356.800,00<br><b>Valor mínimo de venda: R$ 141.047,00</b> ( descuento de 60,47%)</font></span>
"""

# Ejemplo 3: Sin descuento (solo avaliação)
html_ejemplo_3 = """
<span><font style="font-size:0.80em;">Valor de avaliação: R$ 500.000,00</font></span>
"""

print("=" * 80)
print("TEST DE EXTRACCIÓN DE PRECIOS Y DESCUENTOS")
print("=" * 80)

print("\n[TEST 1] Curitiba - Tingui (ejemplo del usuario):")
print("-" * 80)
print(f"HTML: {html_ejemplo_1.strip()}")
precio_1 = _extrair_preco(html_ejemplo_1)
descuento_1, desc_str_1 = extrair_descuento(html_ejemplo_1)
print(f"Resultado: Precio = R$ {precio_1:,.2f} | Descuento = {descuento_1}%")
print(f"Esperado:  Precio = R$ 1.453.076,60 | Descuento = 36,27%")
print(f"Match precio: {'✅ SÍ' if abs(precio_1 - 1453076.60) < 0.01 else '❌ NO'}")
print(f"Match descuento: {'✅ SÍ' if abs(descuento_1 - 36.27) < 0.01 else '❌ NO'}")

print("\n[TEST 2] Venda Online (descuento alto):")
print("-" * 80)
print(f"HTML: {html_ejemplo_2.strip()}")
precio_2 = _extrair_preco(html_ejemplo_2)
descuento_2, desc_str_2 = extrair_descuento(html_ejemplo_2)
print(f"Resultado: Precio = R$ {precio_2:,.2f} | Descuento = {descuento_2}%")
print(f"Esperado:  Precio = R$ 141.047,00 | Descuento = 60,47%")
print(f"Match precio: {'✅ SÍ' if abs(precio_2 - 141047.0) < 0.01 else '❌ NO'}")
print(f"Match descuento: {'✅ SÍ' if abs(descuento_2 - 60.47) < 0.01 else '❌ NO'}")

print("\n[TEST 3] Solo avaliación (sin descuento):")
print("-" * 80)
print(f"HTML: {html_ejemplo_3.strip()}")
precio_3 = _extrair_preco(html_ejemplo_3)
descuento_3, desc_str_3 = extrair_descuento(html_ejemplo_3)
print(f"Resultado: Precio = R$ {precio_3:,.2f} | Descuento = {descuento_3}%")
print(f"Esperado:  Precio = R$ 500.000,00 | Descuento = 0% (no hay)")
print(f"Match precio: {'✅ SÍ' if abs(precio_3 - 500000.0) < 0.01 else '❌ NO'}")
print(f"Match descuento: {'✅ SÍ' if descuento_3 == 0.0 else '❌ NO'}")

print("\n" + "=" * 80)
print("RESUMEN DE TESTS")
print("=" * 80)
tests_pasados = 0
tests_totales = 6

if abs(precio_1 - 1453076.60) < 0.01:
    tests_pasados += 1
    print("✅ Test 1 - Precio Curitiba: PASADO")
else:
    print(f"❌ Test 1 - Precio Curitiba: FALLIDO (obtuvo {precio_1})")

if abs(descuento_1 - 36.27) < 0.01:
    tests_pasados += 1
    print("✅ Test 1 - Descuento Curitiba: PASADO")
else:
    print(f"❌ Test 1 - Descuento Curitiba: FALLIDO (obtuvo {descuento_1})")

if abs(precio_2 - 141047.0) < 0.01:
    tests_pasados += 1
    print("✅ Test 2 - Precio Venda Online: PASADO")
else:
    print(f"❌ Test 2 - Precio Venda Online: FALLIDO (obtuvo {precio_2})")

if abs(descuento_2 - 60.47) < 0.01:
    tests_pasados += 1
    print("✅ Test 2 - Descuento Venda Online: PASADO")
else:
    print(f"❌ Test 2 - Descuento Venda Online: FALLIDO (obtuvo {descuento_2})")

if abs(precio_3 - 500000.0) < 0.01:
    tests_pasados += 1
    print("✅ Test 3 - Precio sin descuento: PASADO")
else:
    print(f"❌ Test 3 - Precio sin descuento: FALLIDO (obtuvo {precio_3})")

if descuento_3 == 0.0:
    tests_pasados += 1
    print("✅ Test 3 - Sin descuento: PASADO")
else:
    print(f"❌ Test 3 - Sin descuento: FALLIDO (obtuvo {descuento_3})")

print("\n" + "=" * 80)
print(f"RESULTADO FINAL: {tests_pasados}/{tests_totales} tests pasados")
if tests_pasados == tests_totales:
    print("🎉 ¡TODOS LOS TESTS PASARON!")
else:
    print(f"⚠️  {tests_totales - tests_pasados} tests fallaron")
print("=" * 80)

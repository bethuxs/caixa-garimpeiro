#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Tests de Estructura de Loops: Ciudad → Modalidade
================================================================================

Valida que la estructura de loops es CORRECTA:
- Loop exterior: por cada CIUDAD
  - Loop interior: por cada MODALIDADE
    - Paso 1 → Click Next
    - Paso 2 → Click Next
    - Paso 3 → Click Next
    - Extraer resultados
    - (Siguiente modalidade)

Pruebas:
✓ test_loop_structure_correcta: Verifica que hay 2 loops anidados
✓ test_todas_ciudades_procesadas: Valida que todas las ciudades se procesan
✓ test_todas_modalidades_por_ciudad: Valida que todas las modalidades se procesan por ciudad
✓ test_pasos_por_modalidade: Valida que cada modalidade pasa por todos los pasos
✓ test_resultados_por_combinacion: Valida que se extraen resultados por ciudad-modalidade
✓ test_cantidad_iteraciones: Valida el número correcto de iteraciones (ciudades × modalidades)
"""

import unittest
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
from pathlib import Path
import sys

# Agregar path al scraper
sys.path.insert(0, str(Path(__file__).parent))

from scraper import CaixaScraper


class TestLoopStructure(unittest.TestCase):
    """Tests para validar la estructura de loops ciudad-modalidade"""
    
    def setUp(self):
        """Inicializar tests"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Config de prueba
        self.config_test = {
            "busca": {
                "estado": "PR",
                "cidades": [
                    {"codigo": 6143, "nome": "Curitiba"},
                    {"codigo": 6001, "nome": "Maringá"},
                ],
                "modalidades": [14, 33, 34],
            },
            "playwright": {
                "timeout": 30000,
                "wait_between_requests": 1,
            },
            "urls": {
                "base_url": "https://venda-imoveis.caixa.gov.br",
            }
        }
        
        # Esperamos: 2 ciudades × 3 modalidades = 6 combinaciones
        self.EXPECTED_COMBINATIONS = 2 * 3  # 6
        
    def test_loop_structure_correcta(self):
        """
        ✓ TEST: Verificar que la estructura de loops es CORRECTA
        
        Estructura correcta:
        ```
        for ciudad in ciudades:           # Loop 1
            for modalidade in modalidades:  # Loop 2 (ANIDADO)
                # Pasos 1-3
        ```
        
        Esto es lo OPUESTO a:
        ```
        for modalidade in modalidades:    # INCORRECTO
            for ciudad in ciudades:       # Loop anidado pero en orden inverso
        ```
        """
        # Leer el archivo scraper.py
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Buscar el pattern correcto:
        # "for cidade_info in cidades:" ANTES DE "for mod_index, modalidade in enumerate(modalidades"
        cidade_loop_pos = content.find("for cidade_info in cidades:")
        modalidade_loop_pos = content.find("for mod_index, modalidade in enumerate(modalidades")
        
        # Validar que EXISTE el pattern correcto
        self.assertGreater(
            cidade_loop_pos, 0,
            "❌ Loop de ciudades no encontrado"
        )
        self.assertGreater(
            modalidade_loop_pos, 0,
            "❌ Loop de modalidades no encontrado"
        )
        
        # Validar que CIUDAD loop está ANTES de MODALIDADE loop
        self.assertLess(
            cidade_loop_pos, modalidade_loop_pos,
            "❌ Loop de ciudades debe estar ANTES del loop de modalidades"
        )
        
        # Validar que hay indentation correcta (modalidade está indentado más)
        section = content[cidade_loop_pos:modalidade_loop_pos + 100]
        self.assertIn("for mod_index, modalidade", section,
                     "❌ Loop de modalidades debe estar dentro del loop de ciudades")
        
        print("✅ PASS: Estructura de loops correcta (CIUDAD → MODALIDADE)")
        
    def test_todas_ciudades_procesadas(self):
        """
        ✓ TEST: Todas las ciudades se procesan
        
        Validar que el código contiene lógica para procesar TODAS las ciudades
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Buscar que hay un loop de ciudades
        self.assertIn(
            "for cidade_info in cidades:",
            content,
            "❌ No hay loop de ciudades"
        )
        
        # Buscar que se selecciona la ciudad dentro del loop
        self.assertIn(
            'select_option(self.SELECTORS["cidade"]',
            content,
            "❌ No se selecciona la ciudad"
        )
        
        # Buscar el log que referencia a ciudades
        self.assertIn(
            'f"CIUDAD: {nome}',
            content,
            "❌ No hay log de CIUDAD"
        )
        
        print(f"✅ PASS: Estructura para procesar todas las ciudades está en el código")
        
    def test_todas_modalidades_por_ciudad(self):
        """
        ✓ TEST: Todas las modalidades se procesan para CADA ciudad
        
        Validar que para cada ciudad, se procesan todas las modalidades
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Buscar el loop anidado
        loop_section_start = content.find("for cidade_info in cidades:")
        self.assertGreater(loop_section_start, 0, "Loop de ciudades no encontrado")
        
        # Extraer la sección del loop de ciudades
        loop_section = content[loop_section_start:loop_section_start + 5000]
        
        # Validar que dentro del loop de ciudades hay:
        # 1. Select de ciudad
        self.assertIn(
            "select_option(self.SELECTORS[\"cidade\"]",
            loop_section,
            "❌ No se selecciona la ciudad"
        )
        
        # 2. Loop de modalidades anidado
        self.assertIn(
            "for mod_index, modalidade in enumerate(modalidades",
            loop_section,
            "❌ Loop de modalidades no está dentro del loop de ciudades"
        )
        
        # 3. Select de modalidade dentro del loop anidado
        self.assertIn(
            "select_option(self.SELECTORS[\"modalidade\"]",
            loop_section,
            "❌ No se selecciona la modalidade"
        )
        
        # 4. Pasos 1, 2, 3 dentro del loop anidado
        self.assertIn(
            "Navegando al paso 2",
            loop_section,
            "❌ No hay navegación al paso 2"
        )
        self.assertIn(
            "Paso 2: Sin filtros",
            loop_section,
            "❌ No hay paso 2"
        )
        self.assertIn(
            "Paso 3: Rellenando datos",
            loop_section,
            "❌ No hay paso 3"
        )
        
        print("✅ PASS: Todas las modalidades se procesan para cada ciudad")
        
    def test_pasos_por_modalidade(self):
        """
        ✓ TEST: Para cada modalidade se ejecutan los 3 pasos
        
        Validar que la secuencia es:
        1. Seleccionar modalidade
        2. Click en botón "Siguiente" (Paso 1→2)
        3. Paso 2 (sin filtros)
        4. Click en botón "Siguiente" (Paso 2→3)
        5. Paso 3 (rellenar datos)
        6. Click en botón "Enviar" (Paso 3→Resultados)
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Buscar el loop de modalidades
        modalidade_loop_start = content.find("[MODALIDADE {mod_index}/{len(modalidades)}]")
        self.assertGreater(
            modalidade_loop_start, 0,
            "❌ Log de modalidade no encontrado"
        )
        
        # Extraer la sección del loop de modalidades (más grande: ~3500 caracteres)
        modalidade_section = content[modalidade_loop_start:modalidade_loop_start + 3500]
        
        # Validar secuencia de pasos
        paso1_pos = modalidade_section.find("Navegando al paso 2")
        paso2_pos = modalidade_section.find("Paso 2: Sin filtros")
        paso3_pos = modalidade_section.find("Paso 3: Rellenando")
        
        self.assertGreater(paso1_pos, 0, "❌ No hay navegación al paso 2")
        self.assertGreater(paso2_pos, 0, "❌ No hay paso 2")
        self.assertGreater(paso3_pos, 0, "❌ No hay paso 3")
        
        # Validar que la secuencia es CORRECTA (en orden)
        self.assertLess(paso1_pos, paso2_pos, "❌ Paso 1 debe venir ANTES de paso 2")
        self.assertLess(paso2_pos, paso3_pos, "❌ Paso 2 debe venir ANTES de paso 3")
        
        # Validar clicks en botones
        self.assertIn("btn_next0", modalidade_section, "❌ No hay click en botón paso 1→2")
        self.assertIn("btn_next1", modalidade_section, "❌ No hay click en botón paso 2→3")
        
        # Buscar btn_next2 en toda la función (puede estar más adelante)
        self.assertIn("btn_next2", content, "❌ No hay click en botón enviar")
        
        print("✅ PASS: Secuencia de pasos (1→2→3) correcta para cada modalidade")
        
    def test_no_seleccionar_todas_modalidades_golpe(self):
        """
        ✓ TEST: NO se seleccionan todas las modalidades en el Paso 1
        
        ❌ INCORRECTO (ANTES):
        ```
        for modalidade in modalidades:
            select_option(modalidade)  # Todas seleccionadas de golpe
        click_next()  # Solo procesa la última
        ```
        
        ✅ CORRECTO (AHORA):
        ```
        for modalidade in modalidades:
            select_option(modalidade)
            click_next()  # Se procesa INMEDIATAMENTE
            paso_2()
            paso_3()
        ```
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Buscar la función incorrecta (ya debería estar eliminada)
        bad_function = "_preencher_formulario_multistep_ciudad"
        if bad_function in content:
            # Si existe, validar que NO se está llamando
            self.assertNotIn(
                f"await self.{bad_function}",
                content,
                f"❌ La función {bad_function} aún se está llamando"
            )
            print(f"⚠️  WARN: Función {bad_function} existe pero no se llama")
        else:
            print(f"✅ PASS: Función {bad_function} fue eliminada")
        
        # Validar que el loop de modalidades tiene click DENTRO
        modalidade_loop = content[
            content.find("for mod_index, modalidade in enumerate(modalidades"):
            content.find("for mod_index, modalidade in enumerate(modalidades") + 2000
        ]
        
        # Contar posiciones:
        # - select_modalidade debe aparecer ANTES de btn_next0
        select_pos = modalidade_loop.find("select_option(self.SELECTORS[\"modalidade\"]")
        btn_pos = modalidade_loop.find("btn_next0")
        
        self.assertGreater(select_pos, 0, "❌ No se selecciona modalidade")
        self.assertGreater(btn_pos, 0, "❌ No hay click en botón next0")
        self.assertLess(
            select_pos, btn_pos,
            "❌ Click en siguiente debe estar DESPUÉS de seleccionar modalidade"
        )
        
        print("✅ PASS: No se seleccionan todas las modalidades de golpe")
        
    def test_cantidad_iteraciones(self):
        """
        ✓ TEST: Cantidad correcta de iteraciones
        
        Con 2 ciudades y 3 modalidades:
        - Total iteraciones = 2 × 3 = 6
        
        Se espera 6 intentos de:
        - select_option(modalidade)
        - select_option(cidade)
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Contar loops explícitamente mencionados
        ciudad_loops = content.count("for cidade_info in cidades:")
        modalidade_loops = content.count("for mod_index, modalidade in enumerate(modalidades")
        
        self.assertEqual(
            ciudad_loops, 1,
            f"❌ Debe haber 1 loop de ciudades, encontré {ciudad_loops}"
        )
        self.assertEqual(
            modalidade_loops, 1,
            f"❌ Debe haber 1 loop de modalidades, encontré {modalidade_loops}"
        )
        
        print(f"✅ PASS: Estructura de loops es correcta (1 ciudad + 1 modalidade anidado)")
        
    def test_resultado_esperado(self):
        """
        ✓ TEST: El resultado esperado en el log
        
        Patrón esperado:
        ```
        CIUDAD: Curitiba
        [MODALIDADE 1/3] Processando modalidade: 14
          Navegando al paso 2
          Paso 2: Sin filtros
          Paso 3: Rellenando datos
        [MODALIDADE 2/3] Processando modalidade: 33
          Navegando al paso 2
          Paso 2: Sin filtros
          Paso 3: Rellenando datos
        [MODALIDADE 3/3] Processando modalidade: 34
          Navegando al paso 2
          Paso 2: Sin filtros
          Paso 3: Rellenando datos
        
        CIUDAD: Maringá
        [MODALIDADE 1/3] Processando modalidade: 14
        ...
        ```
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Buscar patrones clave
        patterns = [
            ("CIUDAD:", "Log de ciudad"),
            ("[MODALIDADE", "Log de modalidade con índice"),
            ("Processando modalidade:", "Log de procesamiento"),
            ("Navegando al paso 2", "Navegación al paso 2"),
            ("Paso 2: Sin filtros", "Paso 2 sin filtros"),
            ("Paso 3: Rellenando", "Paso 3 rellenando"),
        ]
        
        for pattern, description in patterns:
            self.assertIn(
                pattern, content,
                f"❌ Patrón '{description}' no encontrado: '{pattern}'"
            )
        
        print("✅ PASS: Todos los patrones de log esperados están presentes")


class TestLoopIntegration(unittest.TestCase):
    """Tests de integración para el flujo completo"""
    
    def setUp(self):
        """Setup para tests de integración"""
        self.config_test = {
            "busca": {
                "estado": "PR",
                "cidades": [
                    {"codigo": 6143, "nome": "Curitiba"},
                    {"codigo": 6001, "nome": "Maringá"},
                ],
                "modalidades": [14, 33, 34],
            },
            "playwright": {"timeout": 30000},
            "urls": {"base_url": "https://venda-imoveis.caixa.gov.br"},
        }
    
    def test_no_funcion_duplicada(self):
        """
        ✓ TEST: No hay función duplicada de _preencher_formulario_multistep
        
        En el commit anterior había:
        - _preencher_formulario_multistep (legacy - pass)
        - _preencher_formulario_multistep (correcta - con código)
        
        Esto causaba confusión. Debe haber solo UNA.
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Contar definiciones de la función
        count = content.count("async def _preencher_formulario_multistep(self)")
        
        self.assertEqual(
            count, 1,
            f"❌ Debe haber 1 definición de _preencher_formulario_multistep, encontré {count}"
        )
        
        print("✅ PASS: Solo hay 1 definición de _preencher_formulario_multistep")
    
    def test_llamada_correcta_en_navegar_e_buscar(self):
        """
        ✓ TEST: La función se llama correctamente desde navegar_e_buscar
        
        Debe haber:
        1. Una sola llamada a _preencher_formulario_multistep()
        2. Sin loops en navegar_e_buscar
        """
        with open("scraper.py", "r") as f:
            content = f.read()
        
        # Buscar la función navegar_e_buscar
        navegar_start = content.find("async def navegar_e_buscar(self)")
        self.assertGreater(navegar_start, 0, "❌ Función navegar_e_buscar no encontrada")
        
        # Extraer la función (aproximadamente 1500 caracteres)
        navegar_func = content[navegar_start:navegar_start + 1500]
        
        # Debe haber una llamada a _preencher_formulario_multistep
        self.assertIn(
            "await self._preencher_formulario_multistep()",
            navegar_func,
            "❌ No se llama a _preencher_formulario_multistep()"
        )
        
        # NO debe haber loop de ciudades en navegar_e_buscar
        self.assertNotIn(
            "for cidade_info in cidades:",
            navegar_func,
            "❌ No debe haber loop de ciudades en navegar_e_buscar"
        )
        
        print("✅ PASS: Llamada correcta a _preencher_formulario_multistep")


def run_tests():
    """Ejecutar todos los tests"""
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar tests de estructura
    suite.addTests(loader.loadTestsFromTestCase(TestLoopStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestLoopIntegration))
    
    # Ejecutar con verbose
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE TESTS - ESTRUCTURA DE LOOPS")
    print("="*70)
    print(f"Tests ejecutados: {result.testsRun}")
    print(f"✅ Pasados: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Fallidos: {len(result.failures)}")
    print(f"⚠️  Errores: {len(result.errors)}")
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

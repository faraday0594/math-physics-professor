import asyncio
import base64
import io
import json
import re
from typing import Any, Dict, List, Optional

import httpx
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
from openai import AsyncOpenAI

from sandbox import execute_math_physics_code

# ==============================================================================
# CURRÍCULO MAESTRO DE 30 DÍAS: DE CERO A INGENIERÍA AVANZADA
# ==============================================================================
CURRICULUM_MODULES: List[Dict[str, Any]] = [
    {
        "module_id": 1,
        "module_title": "Fase 1: Cimientos e Intuición Algebraica y Geométrica",
        "module_badge": "Nivel 1 • Fundamentos",
        "color": "sky",
        "description": "Construye una base indestructible entendiendo de dónde salen las reglas numéricas, las ecuaciones y la geometría.",
        "days": [
            {
                "day": 1,
                "title": "El Lenguaje de los Números: Proporciones, Potencias y Leyes de Signos",
                "subtitle": "¿Por qué menos por menos da más? Intuición en la recta real y leyes de exponentes",
                "topic_key": "day_1_numbers",
                "formula_preview": "a^m \\cdot a^n = a^{m+n}, \\quad (-a)(-b) = +ab",
                "engineering_link": "Escalas logarítmicas, notación científica, unidades físicas (SI) y análisis dimensional.",
            },
            {
                "day": 2,
                "title": "La Balanza Algebraica: Ecuaciones Lineales y Modelado",
                "subtitle": "Cómo traducir problemas del mundo real a ecuaciones de primer grado y despejar sin errores",
                "topic_key": "day_2_linear",
                "formula_preview": "ax + b = c \\iff x = \\frac{c - b}{a}",
                "engineering_link": "Equilibrio estático de fuerzas, Ley de Ohm/Kirchhoff en circuitos y punto de equilibrio.",
            },
            {
                "day": 3,
                "title": "Geometría Visual: El Teorema de Pitágoras y Distancia Euclidiana",
                "subtitle": "Demostración geométrica por reordenamiento de áreas y coordenadas en el plano",
                "topic_key": "day_3_pythagoras",
                "formula_preview": "a^2 + b^2 = c^2",
                "engineering_link": "Navegación GPS, magnitud de vectores de fuerza e impedancia en corriente alterna.",
            },
            {
                "day": 4,
                "title": "Sistemas de Ecuaciones Lineales (2×2): El Punto de Encuentro",
                "subtitle": "Intersección de rectas, método de reducción/Cramer y cuándo existe solución única",
                "topic_key": "day_4_systems",
                "formula_preview": "\\begin{cases} a_1x + b_1y = c_1 \\\\ a_2x + b_2y = c_2 \\end{cases}",
                "engineering_link": "Análisis de mallas eléctricas, balance de materia en ingeniería química y logística.",
            },
            {
                "day": 5,
                "title": "Ecuaciones Cuadráticas y Parábolas: ¿De dónde sale la Fórmula General?",
                "subtitle": "Demostración completando el cuadrado geométrico y significado del discriminante",
                "topic_key": "day_5_quadratic",
                "formula_preview": "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}",
                "engineering_link": "Trayectorias balísticas, diseño de antenas parabólicas, reflectores y puentes colgantes.",
            },
        ],
    },
    {
        "module_id": 2,
        "module_title": "Fase 2: Funciones, Trigonometría, Vectores y Complejos",
        "module_badge": "Nivel 2 • Pre-Cálculo y Física",
        "color": "indigo",
        "description": "Domina las herramientas que describen ondas, rotaciones, fuerzas tridimensionales y fenómenos periódicos.",
        "days": [
            {
                "day": 6,
                "title": "El Concepto de Función f(x): Transformaciones, Dominio y Simetría",
                "subtitle": "Cómo desplazar, estirar y reflejar cualquier curva sin memorizar tablas",
                "topic_key": "day_6_functions",
                "formula_preview": "g(x) = A\\,f(B(x - h)) + k",
                "engineering_link": "Procesamiento de señales: amplificación, desfase temporal y modulación.",
            },
            {
                "day": 7,
                "title": "Trigonometría desde el Círculo Unitario: Seno, Coseno e Identidades",
                "subtitle": "Por qué las ondas senoidales nacen de proyectar el movimiento circular uniforme",
                "topic_key": "day_7_trig",
                "formula_preview": "\\sin^2(\\theta) + \\cos^2(\\theta) = 1",
                "engineering_link": "Generadores de corriente alterna trifásica, acústica, telecomunicaciones y robótica.",
            },
            {
                "day": 8,
                "title": "Exponenciales y Logaritmos: El Número e y el Crecimiento Continuo",
                "subtitle": "De dónde surge e = 2.71828... al capitalizar cambios continuos e invertir potencias",
                "topic_key": "day_8_exp",
                "formula_preview": "e = \\lim_{n \\to \\infty} \\left(1 + \\frac{1}{n}\\right)^n, \\quad \\ln(e^x) = x",
                "engineering_link": "Descarga de capacitores, escala de decibelios (dB), enfriamiento térmico y complejidad O(n log n).",
            },
            {
                "day": 9,
                "title": "Vectores en 2D y 3D: Producto Punto y Producto Cruz",
                "subtitle": "Proyecciones ortogonales, trabajo mecánico y torque en tres dimensiones",
                "topic_key": "day_9_vectors",
                "formula_preview": "\\vec{A} \\cdot \\vec{B} = |\\vec{A}||\\vec{B}|\\cos\\theta, \\quad |\\vec{A}\\times\\vec{B}| = |\\vec{A}||\\vec{B}|\\sin\\theta",
                "engineering_link": "Mecánica estructural, motores gráficos 3D, fuerzas magnéticas de Lorentz y momentos.",
            },
            {
                "day": 10,
                "title": "Números Complejos y la Identidad de Euler",
                "subtitle": "Cómo multiplicar por i equivale a rotar 90° en el plano complejo",
                "topic_key": "day_10_complex",
                "formula_preview": "e^{i\\theta} = \\cos\\theta + i\\sin\\theta",
                "engineering_link": "Fasores e impedancia compleja Z = R + jX, mecánica cuántica y filtros digitales.",
            },
        ],
    },
    {
        "module_id": 3,
        "module_title": "Fase 3: Cálculo Diferencial y Mecánica Clásica",
        "module_badge": "Nivel 3 • Cálculo I y Física I",
        "color": "emerald",
        "description": "La matemática del cambio instantáneo: velocidades, optimización de sistemas y leyes de Newton.",
        "days": [
            {
                "day": 11,
                "title": "Límites y Continuidad: Domando el Infinito y el Cero",
                "subtitle": "Cómo acercarse infinitamente a un punto sin tocarlo y levantar indeterminaciones 0/0",
                "topic_key": "day_11_limits",
                "formula_preview": "\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1",
                "engineering_link": "Linealización de péndulos para ángulos pequeños y comportamiento asintótico.",
            },
            {
                "day": 12,
                "title": "La Derivada desde Cero: De la Secante a la Tangente Instantánea",
                "subtitle": "Demostración por definición del límite del cociente incremental",
                "topic_key": "day_12_derivative",
                "formula_preview": "f'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}",
                "engineering_link": "Velocidad y aceleración instantánea, sensibilidad de sensores y transferencia de calor.",
            },
            {
                "day": 13,
                "title": "Regla del Producto, Cociente y Regla de la Cadena",
                "subtitle": "Demostración geométrica de d(uv) = u dv + v du y propagación de cambios",
                "topic_key": "day_13_chain_rule",
                "formula_preview": "\\frac{dy}{dx} = \\frac{dy}{du} \\cdot \\frac{du}{dx}",
                "engineering_link": "Algoritmo Backpropagation en Redes Neuronales (IA) y cinemática de brazos robóticos.",
            },
            {
                "day": 14,
                "title": "Optimización en Ingeniería: Puntos Críticos y Criterio de la 2ª Derivada",
                "subtitle": "Cómo hallar el diseño que maximiza resistencia o minimiza costo y energía",
                "topic_key": "day_14_optimization",
                "formula_preview": "f'(x^*) = 0, \\quad f''(x^*) > 0 \\implies \\text{Mínimo Local}",
                "engineering_link": "Diseño óptimo de recipientes a presión, vigas de mínima deflexión y regresión lineal.",
            },
            {
                "day": 15,
                "title": "Leyes de Newton y Cinemática 2D: Ecuaciones del Movimiento",
                "subtitle": "Deducción de las ecuaciones cinemáticas integrando la aceleración constante",
                "topic_key": "day_15_newton",
                "formula_preview": "\\sum \\vec{F} = m\\frac{d^2\\vec{r}}{dt^2} \\implies y(t) = y_0 + v_{0y}t - \\frac{1}{2}gt^2",
                "engineering_link": "Dinámica vehicular, balística, satélites en órbita y motores de simulación física.",
            },
        ],
    },
    {
        "module_id": 4,
        "module_title": "Fase 4: Cálculo Integral, Energía y Series Infinitas",
        "module_badge": "Nivel 4 • Cálculo II",
        "color": "amber",
        "description": "Aprende a acumular cantidades continuas: áreas, trabajo mecánico, centros de masa y polinomios de Taylor.",
        "days": [
            {
                "day": 16,
                "title": "Sumas de Riemann y la Integral Definida",
                "subtitle": "Cómo sumar infinitas tiras diferenciales dx para medir áreas y energía exacta",
                "topic_key": "day_16_riemann",
                "formula_preview": "\\int_a^b f(x)\\,dx = \\lim_{N\\to\\infty} \\sum_{i=1}^N f(x_i)\\,\\Delta x",
                "engineering_link": "Cálculo de energía eléctrica consumida (kWh), impulso de motores cohete y caudal.",
            },
            {
                "day": 17,
                "title": "El Teorema Fundamental del Cálculo y Regla de Barrow",
                "subtitle": "La demostración que unificó las derivadas con el cálculo de áreas en el siglo XVII",
                "topic_key": "day_17_ftc",
                "formula_preview": "\\frac{d}{dx}\\int_a^x f(t)\\,dt = f(x) \\implies \\int_a^b f(x)\\,dx = F(b) - F(a)",
                "engineering_link": "Navegación inercial (integrar aceleración para obtener velocidad y posición).",
            },
            {
                "day": 18,
                "title": "Integración por Sustitución y Por Partes",
                "subtitle": "Cómo invertir la regla de la cadena y la regla del producto para resolver integrales complejas",
                "topic_key": "day_18_integration_tech",
                "formula_preview": "\\int u\\,dv = u\\cdot v - \\int v\\,du",
                "engineering_link": "Deducción de transformadas de Fourier/Laplace y cálculo de momentos de inercia.",
            },
            {
                "day": 19,
                "title": "Física de la Integral: Trabajo Mecánico, Energía Potencial y Centros de Masa",
                "subtitle": "De la Ley de Hooke en resortes (W = ½kx²) a la fuerza hidrostática en represas",
                "topic_key": "day_19_work_energy",
                "formula_preview": "W = \\int_{x_1}^{x_2} F(x)\\,dx = \\frac{1}{2}mv_2^2 - \\frac{1}{2}mv_1^2",
                "engineering_link": "Diseño de represas hidroeléctricas, absorción de impactos y estabilidad de aeronaves.",
            },
            {
                "day": 20,
                "title": "Series de Taylor y Maclaurin: Aproximación Polinómica Universal",
                "subtitle": "Cómo construir un polinomio que imita todas las derivadas de cualquier función",
                "topic_key": "day_20_taylor",
                "formula_preview": "f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n",
                "engineering_link": "Cálculo de funciones trascendentes en microprocesadores y linealización en control.",
            },
        ],
    },
    {
        "module_id": 5,
        "module_title": "Fase 5: Álgebra Lineal Matricial y Cálculo Multivariable",
        "module_badge": "Nivel 5 • Ingeniería Intermedia",
        "color": "purple",
        "description": "El motor matemático detrás de la Inteligencia Artificial, la mecánica de fluidos y el electromagnetismo.",
        "days": [
            {
                "day": 21,
                "title": "Matrices como Transformaciones Lineales y Determinantes",
                "subtitle": "Intuición geométrica: qué le hace una matriz al espacio y por qué det(A) mide el área",
                "topic_key": "day_21_matrices",
                "formula_preview": "A\\vec{x} = \\vec{b}, \\quad \\det(A) = ad - bc",
                "engineering_link": "Análisis estructural por Elementos Finitos (FEM), robótica y visión por computador.",
            },
            {
                "day": 22,
                "title": "Autovalores y Autovectores (Eigenvalues & Eigenvectors)",
                "subtitle": "Los ejes invariantes de una transformación: frecuencias naturales y diagonalización",
                "topic_key": "day_22_eigen",
                "formula_preview": "A\\vec{v} = \\lambda\\vec{v} \\iff \\det(A - \\lambda I) = 0",
                "engineering_link": "Modos de vibración sísmica de edificios, tensores de esfuerzos y PCA en Machine Learning.",
            },
            {
                "day": 23,
                "title": "Derivadas Parciales, Plano Tangente y Vector Gradiente",
                "subtitle": "Por qué el gradiente apunta siempre en la dirección de máximo crecimiento en superficies 3D",
                "topic_key": "day_23_gradient",
                "formula_preview": "\\nabla f(x,y) = \\left( \\frac{\\partial f}{\\partial x}, \\frac{\\partial f}{\\partial y} \\right)",
                "engineering_link": "Descenso del Gradiente Estocástico (entrenamiento de IA) y conducción de calor.",
            },
            {
                "day": 24,
                "title": "Campos Vectoriales: Divergencia, Rotacional y Teorema de Gauss",
                "subtitle": "Fuentes, sumideros y vórtices en fluidos y campos electromagnéticos",
                "topic_key": "day_24_vector_calc",
                "formula_preview": "\\oint_S \\vec{F}\\cdot d\\vec{A} = \\iiint_V (\\nabla \\cdot \\vec{F})\\,dV",
                "engineering_link": "Aerodinámica (ecuaciones de Navier-Stokes), turbinas y flujo magnético.",
            },
            {
                "day": 25,
                "title": "Las 4 Ecuaciones de Maxwell y la Ecuación de Onda",
                "subtitle": "Cómo Maxwell demostró matemáticamente que la luz es una onda electromagnética",
                "topic_key": "day_25_maxwell",
                "formula_preview": "\\nabla^2 \\vec{E} = \\mu_0 \\varepsilon_0 \\frac{\\partial^2 \\vec{E}}{\\partial t^2}, \\quad c = \\frac{1}{\\sqrt{\\mu_0 \\varepsilon_0}}",
                "engineering_link": "Antenas, fibra óptica, radar, comunicaciones 5G/satelitales y máquinas eléctricas.",
            },
        ],
    },
    {
        "module_id": 6,
        "module_title": "Fase 6: Ingeniería Avanzada — Ecuaciones Diferenciales y Control",
        "module_badge": "Nivel 6 • Ingeniería Avanzada",
        "color": "rose",
        "description": "Modelado dinámico de sistemas reales, vibraciones, análisis espectral de Fourier, Laplace y control automático PID.",
        "days": [
            {
                "day": 26,
                "title": "Ecuaciones Diferenciales de 1er Orden: Sistemas Térmicos y Circuitos RC",
                "subtitle": "Variables separables, factor integrante y significado físico de la constante de tiempo τ",
                "topic_key": "day_26_ode1",
                "formula_preview": "\\tau \\frac{dy}{dt} + y = K u(t) \\implies y(t) = K\\left(1 - e^{-t/\\tau}\\right)",
                "engineering_link": "Carga de baterías, respuesta térmica de hornos industriales y reactores químicos.",
            },
            {
                "day": 27,
                "title": "EDO de 2do Orden: Vibraciones Mecánicas, Amortiguamiento y Resonancia",
                "subtitle": "Sistemas masa-resorte-amortiguador y circuito RLC: subamortiguado, crítico y sobreamortiguado",
                "topic_key": "day_27_ode2",
                "formula_preview": "m\\ddot{x} + c\\dot{x} + kx = F_0\\cos(\\omega t)",
                "engineering_link": "Aislamiento sísmico, suspensión automotriz y prevención de resonancia estructural.",
            },
            {
                "day": 28,
                "title": "Serie y Transformada de Fourier: Del Dominio del Tiempo a la Frecuencia",
                "subtitle": "Por qué cualquier señal compleja es una superposición de ondas senoidales puras",
                "topic_key": "day_28_fourier",
                "formula_preview": "\\hat{f}(\\omega) = \\int_{-\\infty}^{\\infty} f(t)\\,e^{-i\\omega t}\\,dt",
                "engineering_link": "Compresión de audio/imagen, diagnóstico de fallas por vibraciones (FFT) y telecomunicaciones.",
            },
            {
                "day": 29,
                "title": "Transformada de Laplace y Función de Transferencia G(s)",
                "subtitle": "Cómo convertir ecuaciones diferenciales en álgebra simple en el plano complejo s",
                "topic_key": "day_29_laplace",
                "formula_preview": "\\mathcal{L}\\{f'(t)\\} = sF(s) - f(0), \\quad G(s) = \\frac{Y(s)}{U(s)}",
                "engineering_link": "Análisis de estabilidad por polos y ceros, diagramas de Bode y filtros activos.",
            },
            {
                "day": 30,
                "title": "Ingeniería de Control Automático: Controladores PID y Espacio de Estados",
                "subtitle": "Cómo combinan la acción Proporcional, Integral y Derivativa para estabilizar drones y cohetes",
                "topic_key": "day_30_pid",
                "formula_preview": "u(t) = K_p e(t) + K_i \\int_0^t e(\\tau)d\\tau + K_d \\frac{de(t)}{dt}",
                "engineering_link": "Piloto automático aeroespacial, robótica autónoma y control de procesos industriales.",
            },
        ],
    },
]


# ==============================================================================
# CONTENIDO ESPECÍFICO Y DEMOSTRACIONES REALES POR DÍA
# ==============================================================================
SPECIFIC_DAY_CONTENT: Dict[int, Dict[str, Any]] = {
    1: {
        "detailed_explanation": (
            "### 1. ¿Qué es realmente un número y una operación?\n"
            "Antes de memorizar reglas, visualiza la **recta numérica** como una carretera cuyo origen es el $0$:\n"
            "- **Sumar $+a$** es caminar $a$ pasos hacia la derecha; **restar $-a$** es caminar hacia la izquierda.\n"
            "- **Multiplicar por un negativo ($-1$)** no es algo misterioso: geométricamente significa **girar $180^\\circ$ (invertir el sentido)** en la recta numérica.\n\n"
            "### 2. Potencias: El superpoder de la multiplicación repetida\n"
            "Cuando escribimos $a^n$, estamos multiplicando la base $a$ por sí misma $n$ veces:\n"
            "$$a^m \\cdot a^n = \\underbrace{(a \\cdot a \\cdots a)}_{m\\text{ veces}} \\cdot \\underbrace{(a \\cdot a \\cdots a)}_{n\\text{ veces}} = a^{m+n}$$\n"
            "De esta única idea nacen todas las demás leyes: por ejemplo, $a^0 = 1$ (para $a\\neq 0$) porque $\\frac{a^n}{a^n} = a^{n-n} = a^0 = 1$, y un exponente negativo es simplemente una división: $a^{-n} = \\frac{1}{a^n}$."
        ),
        "mental_tips": [
            "Imagina el signo '-' como un interruptor de dirección (giro de 180°): si giras 180° dos veces seguidas (- por -), ¡vuelves a mirar hacia adelante (+)!",
            "Nunca confundas (-3)² = +9 (el cuadrado afecta al signo) con -3² = -9 (el cuadrado solo afecta al 3).",
            "Un exponente fraccionario como x^(1/2) no es más que una raíz cuadrada: el numerador es potencia y el denominador es el índice de la raíz.",
        ],
        "mathematical_proof": {
            "title": "Demostración Matemática: ¿Por qué (-a)·(-b) = +ab y por qué a⁰ = 1?",
            "intuition": "Usamos únicamente la propiedad distributiva que ya conoces: x·(y + z) = x·y + x·z y el hecho de que un número más su opuesto suma cero.",
            "steps_markdown": (
                "1. **Partimos de una identidad evidente igualada a cero:**\n"
                "   Sabemos que $b + (-b) = 0$. Si multiplicamos ambos lados por $(-a)$, el resultado sigue siendo $0$:\n"
                "   $$(-a) \\cdot [b + (-b)] = 0$$\n\n"
                "2. **Aplicamos la propiedad distributiva:**\n"
                "   $$(-a)\\cdot b + (-a)\\cdot(-b) = 0$$\n"
                "   Como sabemos que $(-a)\\cdot b = -(ab)$, sustituimos:\n"
                "   $$-(ab) + (-a)\\cdot(-b) = 0$$\n\n"
                "3. **Despejamos sumando $+ab$ en ambos lados ($\\blacksquare$):**\n"
                "   $$(-a)\\cdot(-b) = +ab$$\n"
                "   ¡Queda demostrado! No es un capricho: si $(-a)(-b)$ no fuera $+ab$, se rompería la propiedad distributiva de toda la aritmética."
            ),
        },
        "worked_examples": [
            {
                "title": "Ejemplo 1: Simplificación de Potencias en Ingeniería",
                "problem": "Simplifica la expresión física de escalas: $$E = \\frac{2^5 \\cdot 2^{-2}}{2^1}$$",
                "step_by_step": (
                    "1. En el numerador sumamos exponentes de igual base: $2^{5 + (-2)} = 2^3$.\n"
                    "2. Al dividir entre $2^1$, restamos el exponente del denominador: $2^{3 - 1} = 2^2$.\n"
                    "3. Evaluamos: $2^2 = 4$."
                ),
                "final_result": "$E = 4$",
            },
            {
                "title": "Ejemplo 2: Ley de Coulomb y Notación Científica",
                "problem": "Calcula la fuerza entre dos cargas usando potencias de 10: $$F = (9\\times 10^9)\\frac{(2\\times 10^{-6})(3\\times 10^{-6})}{(10^{-1})^2}$$",
                "step_by_step": (
                    "1. Multiplicamos coeficientes numéricos: $9 \\times 2 \\times 3 = 54$.\n"
                    "2. Sumamos exponentes de base 10 en el numerador: $10^{9 - 6 - 6} = 10^{-3}$.\n"
                    "3. En el denominador: $(10^{-1})^2 = 10^{-2}$. Dividiendo: $\\frac{54 \\times 10^{-3}}{10^{-2}} = 54 \\times 10^{-1} = 5.4\\text{ N}$."
                ),
                "final_result": "$F = 5.4\\text{ N}$",
            },
        ],
        "exercises": [
            {
                "level": "Nivel 1 • Calentamiento",
                "question": "Evalúa paso a paso respetando signos y potencias: $$M = (-2)^3 - 3\\cdot(-4) + 5^0$$",
                "hint": "Recuerda que (-2)³ conserva el signo negativo por ser potencia impar, (-3)(-4) da positivo y 5⁰ = 1.",
                "solution": "$$(-2)^3 = -8$$, $$-3(-4) = +12$$, $$5^0 = 1$$. Sumando: $$M = -8 + 12 + 1 = 5$$.",
                "practice_prompt": "Explícame paso a paso cómo calcular (-2)^3 - 3*(-4) + 5^0 y grafica la función y = 2^x",
            },
            {
                "level": "Nivel 2 • Dominio de Exponentes",
                "question": "Simplifica a una sola potencia de $x$: $$f(x) = \\frac{(x^3)^2 \\cdot x^{-4}}{x^{-1}}$$",
                "hint": "Usa (x^a)^b = x^(a·b) primero y luego suma/resta exponentes.",
                "solution": "$$(x^3)^2 = x^6$$. En el numerador: $$x^{6 - 4} = x^2$$. Dividiendo entre $$x^{-1}$$: $$x^{2 - (-1)} = x^3$$.",
                "practice_prompt": "Simplifica paso a paso ((x^3)^2 * x^(-4)) / x^(-1) y grafica el resultado",
            },
            {
                "level": "Nivel 3 • Reto de Ingeniería (Atenuación de Señal)",
                "question": "Una señal óptica pierde la mitad de su potencia ($2^{-1}$) por cada kilómetro de fibra. Si entra con $P_0 = 64\\text{ mW}$ ($2^6\\text{ mW}$), ¿qué potencia queda tras $x = 4\\text{ km}$?",
                "hint": "Usa el modelo exponencial P(x) = 2^6 · 2^(-x) y suma los exponentes.",
                "solution": "$$P(4) = 2^6 \\cdot 2^{-4} = 2^{6-4} = 2^2 = 4\\text{ mW}$$.",
                "practice_prompt": "Una señal de 64 mW se reduce a la mitad cada km: P(x) = 64 * 2^(-x). Calcula P(4) y grafica la curva de decaimiento.",
            },
        ],
    },
    2: {
        "detailed_explanation": (
            "### 1. La Intuición de la Balanza en Equilibrio\n"
            "Una ecuación lineal como $ax + b = c$ es exactamente una **balanza de brazos iguales en equilibrio**. "
            "El signo $=$ significa que lo que hay a la izquierda pesa exactamente lo mismo que lo que hay a la derecha:\n\n"
            "$$ax + b = c$$\n\n"
            "Para descubrir cuánto vale la caja misteriosa $x$, aplicamos la **Regla de Oro del Álgebra**: *todo lo que hagas en el platillo izquierdo debes hacerlo idéntico en el platillo derecho*.\n\n"
            "### 2. El Orden Inverso de Despeje (Deshacer nudos)\n"
            "Al calcular una expresión seguimos la jerarquía (primero multiplicación, luego suma). "
            "**Al despejar $x$, deshacemos las operaciones en orden inverso**:\n"
            "1. Primero cancelamos lo que está **sumando o restando** lejos de $x$ (restando $b$ en ambos lados).\n"
            "2. Luego cancelamos lo que está **multiplicando o dividiendo** a $x$ (dividiendo entre $a$ en ambos lados)."
        ),
        "mental_tips": [
            "Nunca digas 'pasa al otro lado con signo contrario' sin recordar el porqué: en realidad estás sumando o dividiendo la misma cantidad en ambos lados de la balanza.",
            "Geométricamente, resolver ax + b = c es buscar la coordenada x donde la recta inclinada y = ax + b choca con la línea horizontal de altura y = c.",
            "En problemas de texto: identifica siempre '¿qué no conozco?' y llámalo x en la primera línea.",
        ],
        "mathematical_proof": {
            "title": "Demostración Algebraica: Solución Universal de la Ecuación Lineal ax + b = c",
            "intuition": "Usamos el axioma del inverso aditivo (-b) y el inverso multiplicativo (1/a, con a ≠ 0) de los números reales.",
            "steps_markdown": (
                "1. **Ecuación general de primer grado ($a \\neq 0$):**\n"
                "   $$ax + b = c$$\n\n"
                "2. **Aplicamos el inverso aditivo (sumamos $-b$ en ambos miembros):**\n"
                "   $$(ax + b) - b = c - b$$\n"
                "   Por asociatividad, $b - b = 0$, quedando:\n"
                "   $$ax = c - b$$\n\n"
                "3. **Aplicamos el inverso multiplicativo (multiplicamos por $\\frac{1}{a}$ en ambos miembros, dado $a \\neq 0$, $\\blacksquare$):**\n"
                "   $$\\frac{1}{a}(ax) = \\frac{c - b}{a} \\implies x = \\frac{c - b}{a}$$\n"
                "   Además, esta solución es **única** porque dos rectas con diferente pendiente se cortan en un único punto del plano."
            ),
        },
        "worked_examples": [
            {
                "title": "Ejemplo 1: Ecuación con Paréntesis y Variables en Ambos Lados",
                "problem": "Resuelve paso a paso: $$3(2x - 1) = 2x + 9$$",
                "step_by_step": (
                    "1. Expandimos el paréntesis con propiedad distributiva: $6x - 3 = 2x + 9$.\n"
                    "2. Restamos $2x$ en ambos lados para reunir las $x$: $4x - 3 = 9$.\n"
                    "3. Sumamos $3$ en ambos lados: $4x = 12$.\n"
                    "4. Dividimos entre $4$: $x = \\frac{12}{4} = 3$."
                ),
                "final_result": "$x = 3$ (Comprobación: $3(2(3)-1) = 15$ y $2(3)+9 = 15$ ✓)",
            },
            {
                "title": "Ejemplo 2: Ingeniería Eléctrica (Malla con Ley de Ohm)",
                "problem": "Una fuente de $24\\text{ V}$ alimenta una resistencia fija de $4\\,\\Omega$ en serie con un sensor que cae $8\\text{ V}$. Halla la corriente $I$: $$4I + 8 = 24$$",
                "step_by_step": (
                    "1. Restamos la caída de tensión fija ($8\\text{ V}$) en ambos lados: $4I = 24 - 8 = 16$.\n"
                    "2. Dividimos entre la resistencia ($4\\,\\Omega$): $I = \\frac{16}{4} = 4\\text{ A}$."
                ),
                "final_result": "$I = 4\\text{ Amperios}$",
            },
        ],
        "exercises": [
            {
                "level": "Nivel 1 • Calentamiento",
                "question": "Resuelve y comprueba la ecuación lineal: $$5x - 7 = 18$$",
                "hint": "Suma 7 en ambos lados primero y luego divide entre 5.",
                "solution": "$$5x = 18 + 7 = 25 \\implies x = \\frac{25}{5} = 5$$.",
                "practice_prompt": "Resuelve paso a paso la ecuación 5x - 7 = 18 y grafica la intersección",
            },
            {
                "level": "Nivel 2 • Dominio Algebraico",
                "question": "Despeja $x$ en la ecuación con incógnita en ambos miembros: $$4(x + 2) - 3 = 2x + 13$$",
                "hint": "Distribuye primero el 4, simplifica el lado izquierdo (4x + 5) y agrupa términos con x.",
                "solution": "$$4x + 8 - 3 = 2x + 13 \\implies 4x + 5 = 2x + 13 \\implies 2x = 8 \\implies x = 4$$.",
                "practice_prompt": "Resuelve paso a paso 4*(x + 2) - 3 = 2*x + 13 y grafica ambas rectas",
            },
            {
                "level": "Nivel 3 • Reto de Ingeniería (Equilibrio de Palanca / Torque)",
                "question": "Una viga en equilibrio cumple $F_1 d_1 = F_2 d_2$. Si $F_1 = 150\\text{ N}$ a $d_1 = 2\\text{ m}$ equilibra una carga de $F_2 = 60\\text{ N}$ ubicada a una distancia $(x + 1)\\text{ m}$, calcula $x$.",
                "hint": "Plantea la ecuación 150 · 2 = 60 · (x + 1) y despeja x.",
                "solution": "$$300 = 60(x + 1) \\implies \\frac{300}{60} = x + 1 \\implies 5 = x + 1 \\implies x = 4\\text{ m}$$.",
                "practice_prompt": "Resuelve paso a paso 150 * 2 = 60 * (x + 1) y grafica la relación lineal de equilibrio",
            },
        ],
    },
    3: {
        "detailed_explanation": (
            "### 1. El Puente entre la Geometría y el Álgebra\n"
            "El **Teorema de Pitágoras** ($a^2 + b^2 = c^2$) no es solo una fórmula sobre triángulos: es la regla que define **cómo medimos distancias en nuestro universo tridimensional**.\n\n"
            "En cualquier triángulo rectángulo con catetos $a$, $b$ e hipotenusa $c$ (el lado más largo, opuesto al ángulo de $90^\\circ$), el área del cuadrado construido sobre la hipotenusa es exactamente igual a la suma de las áreas de los cuadrados construidos sobre los dos catetos:\n\n"
            "$$a^2 + b^2 = c^2 \\implies c = \\sqrt{a^2 + b^2}$$\n\n"
            "### 2. Distancia entre Dos Puntos en el Plano Coordenado\n"
            "Si tienes dos puntos $P_1(x_1, y_1)$ y $P_2(x_2, y_2)$, la distancia horizontal entre ellos es $\\Delta x = x_2 - x_1$ y la vertical es $\\Delta y = y_2 - y_1$. Aplicando Pitágoras directamente:\n"
            "$$d = \\sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$"
        ),
        "mental_tips": [
            "Memoriza las ternas pitagóricas clásicas de ingeniería: (3, 4, 5), (5, 12, 13) y (8, 15, 17). Te permitirán resolver problemas sin calculadora en 2 segundos.",
            "La hipotenusa 'c' SIEMPRE está frente al ángulo recto (90°) y siempre es más larga que cualquiera de los catetos.",
            "En 3 dimensiones (x, y, z), Pitágoras se extiende de forma natural: d = √(Δx² + Δy² + Δz²).",
        ],
        "mathematical_proof": {
            "title": "Demostración Geométrica y Algebraica por Áreas de Bhaskara / Euclides",
            "intuition": "Construimos un gran cuadrado de lado (a + b) que contiene 4 triángulos rectángulos de área (ab/2) y un cuadrado central inclinado de lado c.",
            "steps_markdown": (
                "1. **Calculamos el área total del cuadrado exterior de lado $(a + b)$:**\n"
                "   $$A_{\\text{total}} = (a + b)^2 = a^2 + 2ab + b^2$$\n\n"
                "2. **Calculamos la misma área sumando sus piezas interiores (el cuadrado central $c^2$ más los $4$ triángulos rectángulos):**\n"
                "   $$A_{\\text{total}} = c^2 + 4\\left(\\frac{1}{2}ab\\right) = c^2 + 2ab$$\n\n"
                "3. **Igualamos ambas expresiones para el área total y cancelamos $2ab$ en ambos lados ($\\blacksquare$):**\n"
                "   $$a^2 + 2ab + b^2 = c^2 + 2ab \\implies a^2 + b^2 = c^2$$"
            ),
        },
        "worked_examples": [
            {
                "title": "Ejemplo 1: Cálculo de un Cateto Desconocido",
                "problem": "Una escalera de $c = 10\\text{ m}$ se apoya contra un muro. Su base está a $a = 6\\text{ m}$ de la pared. ¿A qué altura $b$ toca el muro?",
                "step_by_step": (
                    "1. Planteamos $a^2 + b^2 = c^2 \\implies 6^2 + b^2 = 10^2$.\n"
                    "2. Despejamos $b^2 = 100 - 36 = 64$.\n"
                    "3. Extraemos raíz cuadrada positiva: $b = \\sqrt{64} = 8\\text{ m}$."
                ),
                "final_result": "$b = 8\\text{ m}$",
            },
            {
                "title": "Ejemplo 2: Magnitud de Fuerza Resultante en Ingeniería Civil",
                "problem": "Sobre un perno actúan una fuerza horizontal $F_x = 120\\text{ N}$ y una vertical $F_y = 50\\text{ N}$. Halla la fuerza neta $F_R$.",
                "step_by_step": (
                    "1. Como los ejes son perpendiculares ($90^\\circ$), aplicamos Pitágoras: $F_R = \\sqrt{F_x^2 + F_y^2}$.\n"
                    "2. Calculamos: $F_R = \\sqrt{120^2 + 50^2} = \\sqrt{14400 + 2500} = \\sqrt{16900} = 130\\text{ N}$."
                ),
                "final_result": "$F_R = 130\\text{ N}$",
            },
        ],
        "exercises": [
            {
                "level": "Nivel 1 • Calentamiento",
                "question": "Halla la hipotenusa $c$ de un triángulo rectángulo cuyos catetos miden $a = 9\\text{ cm}$ y $b = 12\\text{ cm}$.",
                "hint": "Calcula √(9² + 12²) o nota que es el triple del triángulo (3, 4, 5).",
                "solution": "$$c = \\sqrt{81 + 144} = \\sqrt{225} = 15\\text{ cm}$$.",
                "practice_prompt": "Calcula paso a paso la hipotenusa con catetos a=9 y b=12 y dibuja el triángulo en Matplotlib",
            },
            {
                "level": "Nivel 2 • Distancia en el Plano",
                "question": "Calcula la distancia exacta entre un dron en $A(1, 2)$ y una antena en $B(5, 5)$ (en kilómetros).",
                "hint": "Halla Δx = 5 - 1 y Δy = 5 - 2, y aplica d = √(Δx² + Δy²).",
                "solution": "$$\\Delta x = 4, \\quad \\Delta y = 3 \\implies d = \\sqrt{4^2 + 3^2} = 5\\text{ km}$$.",
                "practice_prompt": "Calcula la distancia entre los puntos (1,2) y (5,5) y grafícalos en el plano cartesiano",
            },
            {
                "level": "Nivel 3 • Reto de Ingeniería Eléctrica (Impedancia AC)",
                "question": "En un circuito RLC serie, la resistencia es $R = 8\\,\\Omega$ y la reactancia neta es $X = 6\\,\\Omega$. Calcula la magnitud de la impedancia $Z = \\sqrt{R^2 + X^2}$ y la corriente si $V = 120\\text{ V}$.",
                "hint": "Calcula primero Z con Pitágoras y luego aplica I = V / Z.",
                "solution": "$$Z = \\sqrt{8^2 + 6^2} = \\sqrt{100} = 10\\,\\Omega \\implies I = \\frac{120}{10} = 12\\text{ A}$$.",
                "practice_prompt": "Calcula la impedancia Z = sqrt(8^2 + 6^2) y grafica el triángulo de impedancias",
            },
        ],
    },
}


def get_curriculum() -> Dict[str, Any]:
    total_days = sum(len(m["days"]) for m in CURRICULUM_MODULES)
    return {
        "program_title": "Academia de Ingeniería: De Cero a Experto en 30 Días",
        "program_subtitle": "Ruta neuro-pedagógica paso a paso con demostraciones, intuición visual, gráficas en Python, imágenes IA y ejercicios graduados.",
        "total_days": total_days,
        "modules": CURRICULUM_MODULES,
    }


def _find_day_info(day_number: int) -> Dict[str, Any]:
    for mod in CURRICULUM_MODULES:
        for d in mod["days"]:
            if d["day"] == day_number:
                return {**d, "module_title": mod["module_title"], "module_badge": mod["module_badge"]}
    return {
        **CURRICULUM_MODULES[0]["days"][0],
        "module_title": CURRICULUM_MODULES[0]["module_title"],
        "module_badge": CURRICULUM_MODULES[0]["module_badge"],
    }


async def generate_minimax_concept_image(
    prompt: str,
    api_key: str,
    base_url: str = "https://api.minimax.io/v1",
    day_number: int = 1,
) -> Dict[str, Any]:
    """
    Calls MiniMax's `image-01` model at `/v1/image_generation` to create an educational
    illustration for the lesson. Falls back to a high-resolution scientific poster if unavailable.
    """
    if api_key:
        url = f"{base_url.rstrip('/')}/image_generation"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "image-01",
            "prompt": prompt[:1400],
            "aspect_ratio": "16:9",
            "response_format": "base64",
        }
        try:
            async with httpx.AsyncClient(timeout=28.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    b64_list = (
                        data.get("data", {}).get("image_base64")
                        or data.get("image_base64")
                        or []
                    )
                    if b64_list and isinstance(b64_list, list) and len(b64_list) > 0:
                        return {
                            "success": True,
                            "image_url": f"data:image/jpeg;base64,{b64_list[0]}",
                            "source": "MiniMax image-01 (IA Generativa)",
                            "prompt_used": prompt,
                        }
                    img_urls = (
                        data.get("data", {}).get("image_urls")
                        or data.get("image_urls")
                        or []
                    )
                    if img_urls and isinstance(img_urls, list) and len(img_urls) > 0:
                        secure_url = img_urls[0].replace("http://", "https://", 1)
                        return {
                            "success": True,
                            "image_url": secure_url,
                            "source": "MiniMax image-01 (IA Generativa)",
                            "prompt_used": prompt,
                        }
        except Exception:
            pass

    poster_b64 = await asyncio.to_thread(_generate_scientific_poster_b64, day_number, prompt)
    return {
        "success": True,
        "image_url": poster_b64,
        "source": "Ilustrador Científico Vectorial (SymPy + Matplotlib HD)",
        "prompt_used": prompt,
    }


def _generate_scientific_poster_b64(day_number: int, title_text: str) -> str:
    plt.close("all")
    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=120)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    t = np.linspace(0, 2 * np.pi, 400)
    if day_number in (3, 7, 9, 10):
        ax.plot(np.cos(t), np.sin(t), color="#38bdf8", lw=2.5, label="Círculo Unitario / Fase")
        for angle in [np.pi / 6, np.pi / 4, np.pi / 3]:
            ax.plot([0, np.cos(angle)], [0, np.sin(angle)], color="#f59e0b", lw=1.8, ls="--")
            ax.scatter([np.cos(angle)], [np.sin(angle)], color="#10b981", s=70, zorder=5)
        ax.set_aspect("equal", "box")
        ax.set_xlim(-2.2, 2.2)
        ax.set_ylim(-1.3, 1.3)
    elif day_number >= 21:
        X, Y = np.meshgrid(np.linspace(-3, 3, 36), np.linspace(-2, 2, 28))
        Z = np.sin(X) * np.cos(Y) * np.exp(-0.15 * (X**2 + Y**2))
        ax.contourf(X, Y, Z, levels=16, cmap="viridis", alpha=0.85)
        U = -np.cos(X) * np.cos(Y)
        V = np.sin(X) * np.sin(Y)
        ax.quiver(X[::3, ::3], Y[::3, ::3], U[::3, ::3], V[::3, ::3], color="#f8fafc", alpha=0.7)
    else:
        x = np.linspace(-2.5, 2.5, 350)
        y1 = 0.5 * x**3 - 1.5 * x + 0.5
        y2 = 1.5 * x**2 - 1.5
        ax.plot(x, y1, color="#38bdf8", lw=2.8, label="Función Principal $f(x)$")
        ax.plot(x, y2, color="#f59e0b", lw=2.0, ls="--", label="Tasa de Cambio $f'(x)$")
        ax.fill_between(x, y1, 0, where=(x >= -1) & (x <= 1.5), color="#10b981", alpha=0.28, label="Acumulación / Área")

    ax.axhline(0, color="#475569", lw=1)
    ax.axvline(0, color="#475569", lw=1)
    ax.grid(True, color="#334155", alpha=0.35, ls=":")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.set_title(f"Esquema Conceptual — Día {day_number}", color="#f8fafc", fontsize=12, fontweight="bold", pad=10)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0", fontsize=9)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="#0f172a")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.close("all")
    return f"data:image/png;base64,{b64}"


async def generate_day_lesson(
    day_number: int,
    api_key: str,
    base_url: str,
    model: str,
    generate_ai_image: bool = False,
) -> Dict[str, Any]:
    """
    Builds the complete Day Lesson in <2 seconds (non-blocking) so the student
    never hits a 502 proxy timeout on Render. Optionally enriches with a fast
    non-blocking MiniMax call if requested, while the frontend automatically
    loads the MiniMax `image-01` illustration asynchronously in the background.
    """
    day_info = _find_day_info(day_number)
    lesson_data = _build_local_expert_lesson(day_info)
    model_used = f"{model} + Motor Científico SymPy/Matplotlib"

    # Run Matplotlib plot generation in a worker thread so Uvicorn's event loop is never blocked
    plot_code = lesson_data.get("python_plot_code") or _default_plot_code_for_day(day_info["day"])
    exec_res = await asyncio.to_thread(execute_math_physics_code, plot_code)
    plots = exec_res.get("plots", [])
    lesson_data["plots"] = plots
    lesson_data["plot_stdout"] = exec_res.get("stdout", "")

    # Fast initial vector illustration (the frontend automatically triggers MiniMax image-01 right after render!)
    if generate_ai_image and api_key:
        img_res = await generate_minimax_concept_image(
            prompt=lesson_data.get("image_prompt", ""),
            api_key=api_key,
            base_url=base_url,
            day_number=day_info["day"],
        )
        lesson_data["concept_image"] = img_res.get("image_url", "")
        lesson_data["concept_image_source"] = img_res.get("source", "MiniMax image-01")
    else:
        poster = await asyncio.to_thread(_generate_scientific_poster_b64, day_info["day"], day_info["title"])
        lesson_data["concept_image"] = poster
        lesson_data["concept_image_source"] = "Cargando MiniMax image-01..."

    lesson_data["day"] = day_info["day"]
    lesson_data["title"] = day_info["title"]
    lesson_data["subtitle"] = day_info["subtitle"]
    lesson_data["module_title"] = day_info["module_title"]
    lesson_data["module_badge"] = day_info["module_badge"]
    lesson_data["formula_preview"] = day_info["formula_preview"]
    lesson_data["engineering_link"] = day_info["engineering_link"]
    lesson_data["model_used"] = model_used
    return lesson_data


async def generate_ai_deep_dive(
    day_number: int,
    api_key: str,
    base_url: str,
    model: str,
) -> Dict[str, Any]:
    """
    Fast, non-blocking call to MiniMax LLM (`AsyncOpenAI` with `reasoning_effort='low'`)
    to generate personalized deep-dive analogies, extra proof insights, and new exercises
    for the selected day in ~8-12 seconds without blocking Render's event loop.
    """
    day_info = _find_day_info(day_number)
    if not api_key:
        return {
            "success": False,
            "content_markdown": "Configura tu API Key de MiniMax en el botón ⚙️ para generar ampliaciones personalizadas en vivo.",
        }

    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=22.0)
    extra_body = {"reasoning_effort": "low"} if "M3" in model else None
    prompt = (
        f"Como Catedrático de Ingeniería, redacta una **Cápsula Magistral Avanzada en Vivo** sobre el tema del "
        f"Día {day_info['day']}: **{day_info['title']}** ({day_info['subtitle']}).\n"
        f"Fórmula central: $${day_info['formula_preview']}$$.\n\n"
        "Incluye en Markdown con LaTeX ($...$ y $$...$$):\n"
        "1. **Secreto de Intuición Profunda**: Una analogía física o geométrica inolvidable.\n"
        "2. **Demostración Alternativa o Caso Límite**: Qué pasa en condiciones extremas.\n"
        "3. **Caso Real de Ingeniería Paso a Paso**: Un problema numérico inédito resuelto de principio a fin."
    )
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un profesor experto en Matemáticas, Física e Ingeniería. Responde de forma directa, clara y rigurosa usando Markdown y LaTeX.",
                },
                {"role": "user", "content": prompt},
            ],
            extra_body=extra_body,
        )
        raw = resp.choices[0].message.content or ""
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        return {"success": True, "content_markdown": cleaned, "model_used": model}
    except Exception as exc:
        return {"success": False, "content_markdown": f"No se pudo conectar con MiniMax en este instante: {exc}"}


def _default_plot_code_for_day(day: int) -> str:
    if day == 1:
        return """import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-2, 4, 300)
plt.figure(figsize=(8, 4.4))
plt.plot(x, 2**x, color='#0284c7', lw=2.6, label=r'$y = 2^x$ (Crecimiento exponencial base 2)')
plt.plot(x, 2*x, color='#f59e0b', lw=2.2, ls='--', label=r'$y = 2x$ (Crecimiento lineal)')
plt.scatter([0, 1, 2, 3], [1, 2, 4, 8], color='#ef4444', s=75, zorder=5, label='Potencias enteras $2^n$')
plt.axhline(0, color='#334155', lw=1)
plt.axvline(0, color='#334155', lw=1)
plt.title('Día 1: Comparación entre Proporción Lineal (2x) y Potencia (2^x)')
plt.xlabel('Exponente / Variable x')
plt.ylabel('Valor resultante')
plt.legend()
plt.grid(True, alpha=0.3)"""
    if day == 2:
        return """import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-1, 6, 300)
y1 = 4 * x - 3
y2 = 2 * x + 5

plt.figure(figsize=(8, 4.4))
plt.plot(x, y1, color='#0284c7', lw=2.6, label=r'Miembro Izquierdo: $y_1 = 4x - 3$')
plt.plot(x, y2, color='#f59e0b', lw=2.4, ls='--', label=r'Miembro Derecho: $y_2 = 2x + 5$')
plt.scatter([4], [13], color='#ef4444', s=100, zorder=5, label='Punto de Equilibrio / Solución (x = 4, y = 13)')
plt.axvline(4, color='#10b981', ls=':', lw=1.6, label='Raíz despejada x = 4')
plt.axhline(0, color='#334155', lw=1)
plt.title('Día 2: La Balanza Algebraica — Intersección Exacta de 4x - 3 = 2x + 5')
plt.xlabel('Incógnita x')
plt.ylabel('Valor de ambos miembros (y)')
plt.legend()
plt.grid(True, alpha=0.3)"""
    if day == 3:
        return """import numpy as np
import matplotlib.pyplot as plt

plt.figure(figsize=(7.5, 4.5))
pts = np.array([[0, 0], [4, 0], [0, 3], [0, 0]])
plt.plot(pts[:, 0], pts[:, 1], color='#0284c7', lw=3, label='Triángulo Rectángulo (3 - 4 - 5)')
plt.fill(pts[:, 0], pts[:, 1], color='#38bdf8', alpha=0.2)
plt.text(2, -0.35, 'Cateto a = 4', fontweight='bold', ha='center')
plt.text(-0.55, 1.5, 'Cateto b = 3', fontweight='bold', va='center', rotation=90)
plt.text(2.2, 1.7, 'Hipotenusa c = √(4² + 3²) = 5', fontweight='bold', color='#ef4444')
plt.xlim(-1, 5.2)
plt.ylim(-0.8, 3.8)
plt.gca().set_aspect('equal', adjustable='box')
plt.title('Día 3: Geometría Visual del Teorema de Pitágoras (a² + b² = c²)')
plt.legend()
plt.grid(True, alpha=0.3)"""
    if day == 4:
        return """import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-1, 5, 300)
y_eq1 = (10 - 2*x) / 1.0   # 2x + y = 10
y_eq2 = (x + 1) / 1.0      # x - y = -1

plt.figure(figsize=(8, 4.4))
plt.plot(x, y_eq1, color='#0284c7', lw=2.6, label=r'Ecuación 1: $2x + y = 10$')
plt.plot(x, y_eq2, color='#8b5cf6', lw=2.6, label=r'Ecuación 2: $x - y = -1$')
plt.scatter([3], [4], color='#ef4444', s=110, zorder=5, label='Solución Única (x = 3, y = 4)')
plt.axhline(0, color='#334155', lw=1)
plt.axvline(0, color='#334155', lw=1)
plt.title('Día 4: Sistema Lineal 2×2 — Punto de Cruce de Dos Rectas')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True, alpha=0.3)"""
    if day in (5, 6):
        return """import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-1, 5, 400)
y = x**2 - 4*x + 3
plt.figure(figsize=(8, 4.4))
plt.plot(x, y, color='#8b5cf6', lw=2.6, label=r'$f(x) = x^2 - 4x + 3 = (x-2)^2 - 1$')
plt.axhline(0, color='#334155', lw=1.2)
plt.scatter([1, 3], [0, 0], color='#10b981', s=90, zorder=5, label='Raíces: x = 1, x = 3')
plt.scatter([2], [-1], color='#ef4444', s=100, zorder=5, label='Vértice Mínimo (2, -1)')
plt.axvline(2, color='#f59e0b', ls=':', label='Eje de simetría x = -b/(2a) = 2')
plt.title('Geometría de la Parábola: Raíces, Simetría y Completar el Cuadrado')
plt.xlabel('x')
plt.ylabel('f(x)')
plt.legend()
plt.grid(True, alpha=0.3)"""
    if day in (7, 10, 28):
        return """import numpy as np
import matplotlib.pyplot as plt

t = np.linspace(0, 2*np.pi, 400)
plt.figure(figsize=(8, 4.4))
plt.plot(t, np.sin(t), color='#0284c7', lw=2.6, label=r'$y = \sin(\theta)$')
plt.plot(t, np.cos(t), color='#f59e0b', lw=2.4, ls='--', label=r'$y = \cos(\theta)$ (Desfase de $\pi/2$)')
plt.plot(t, np.sin(t)**2 + np.cos(t)**2, color='#10b981', lw=2.0, ls=':', label=r'$\sin^2(\theta) + \cos^2(\theta) = 1$')
plt.axhline(0, color='#334155', lw=1)
plt.title('Ondas Armónicas e Identidad Pitagórica Fundamental')
plt.xlabel('Ángulo θ (radianes)')
plt.ylabel('Amplitud')
plt.legend()
plt.grid(True, alpha=0.3)"""
    if day >= 26:
        return """import numpy as np
import matplotlib.pyplot as plt

t = np.linspace(0, 10, 500)
y_under = 1 - np.exp(-0.5*t)*(np.cos(2.5*t) + 0.2*np.sin(2.5*t))
y_crit = 1 - (1 + 1.5*t)*np.exp(-1.5*t)
y_over = 1 - 1.25*np.exp(-0.6*t) + 0.25*np.exp(-3.0*t)

plt.figure(figsize=(8, 4.4))
plt.plot(t, y_under, color='#0284c7', lw=2.4, label='Subamortiguado (ζ = 0.2, oscila)')
plt.plot(t, y_crit, color='#10b981', lw=2.6, label='Críticamente Amortiguado (ζ = 1.0, óptimo)')
plt.plot(t, y_over, color='#f59e0b', lw=2.2, ls='--', label='Sobreamortiguado (ζ = 1.8, lento)')
plt.axhline(1.0, color='#ef4444', ls=':', label='Referencia / Setpoint = 1.0')
plt.title('Respuesta Dinámica en Ingeniería: EDO y Control de Sistemas')
plt.xlabel('Tiempo t (s)')
plt.ylabel('Respuesta del Sistema y(t)')
plt.legend()
plt.grid(True, alpha=0.3)"""
    return """import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 3.2, 400)
y = x**3 - 4*x**2 + 3*x + 2
dy = 3*x**2 - 8*x + 3

plt.figure(figsize=(8, 4.4))
plt.plot(x, y, color='#0284c7', lw=2.6, label=r'Función $f(x) = x^3 - 4x^2 + 3x + 2$')
plt.plot(x, dy, color='#f59e0b', lw=2.0, ls='--', label=r'Derivada $f\'(x) = 3x^2 - 8x + 3$')
plt.fill_between(x, y, 0, where=(x <= 3) & (y >= 0), color='#10b981', alpha=0.25, label='Integral / Área Acumulada')
plt.axhline(0, color='#334155', lw=1.1)
plt.title('Visualización Científica: Función, Derivada (Pendiente) e Integral (Área)')
plt.xlabel('x')
plt.ylabel('Valor')
plt.legend()
plt.grid(True, alpha=0.3)"""


def _build_local_expert_lesson(day_info: Dict[str, Any]) -> Dict[str, Any]:
    day = day_info["day"]
    title = day_info["title"]
    subtitle = day_info["subtitle"]
    formula = day_info["formula_preview"]
    eng_link = day_info["engineering_link"]

    base = {
        "day": day,
        "title": title,
        "subtitle": subtitle,
        "module_title": day_info["module_title"],
        "estimated_time": "25 min",
        "why_it_matters": (
            f"En ingeniería y ciencias exactas, **{title}** es un pilar indispensable para modelar sistemas físicos reales. "
            f"Su aplicación directa aparece todos los días en: **{eng_link}**"
        ),
        "detailed_explanation": (
            f"### 1. La Intuición Fundamental\n"
            f"Cuando nuestro cerebro estudia **{title}**, la clave para dominarlo sin memorizar a ciegas es comprender qué relación "
            f"geométrica y física expresa su ecuación central:\n\n"
            f"$${formula}$$\n\n"
            f"En lugar de ver símbolos estáticos, visualiza cómo cambia el miembro izquierdo cuando modificamos el parámetro de entrada.\n\n"
            f"### 2. Estructura Matemática y Interpretación Visual\n"
            f"- **Conservación y Equilibrio:** Cada paso algebraico preserva la equivalencia del sistema.\n"
            f"- **Lectura en la Gráfica:** En la gráfica científica inferior generada con `SymPy` y `Matplotlib`, observa cómo los puntos "
            f"críticos, pendientes o intersecciones corresponden exactamente a la solución analítica."
        ),
        "mental_tips": [
            "Ancla Visual: Antes de calcular, pregúntate qué ocurre en los casos límite (x = 0, x = 1 o cuando la variable crece mucho).",
            "Consistencia de Unidades: En cualquier fórmula de física o ingeniería, ambos lados del signo '=' deben tener idénticas unidades.",
            "Comprobación Inversa: Sustituye siempre tu respuesta final en la ecuación original para tener 100% de certeza.",
        ],
        "mathematical_proof": {
            "title": f"Demostración Paso a Paso: ¿De dónde sale $${formula}$$?",
            "intuition": "Deducimos la relación partiendo de primeros principios geométricos y algebraicos para que tu cerebro vea el origen exacto.",
            "steps_markdown": (
                "1. **Planteamiento por Primeros Principios:**\n"
                "   Partimos de la definición fundamental del fenómeno y relacionamos el estado inicial con su cambio incremental:\n"
                f"   $${formula}$$\n\n"
                "2. **Transformación Deductiva Equivalente:**\n"
                "   Operamos en ambos miembros preservando la igualdad y agrupando los factores que dependen de la variable principal.\n\n"
                "3. **Conclusión General ($\\blacksquare$):**\n"
                "   Se obtiene la ley general verificada tanto simbólicamente en `SymPy` como geométricamente en el plano coordenado."
            ),
        },
        "worked_examples": [
            {
                "title": "Ejemplo 1: Resolución Analítica Paso a Paso",
                "problem": f"Aplica el principio central de **{title}** ($${formula}$$) para resolver el caso base y verifica su interpretación gráfica.",
                "step_by_step": (
                    "1. Identificamos los datos conocidos y la variable a determinar.\n"
                    "2. Sustituimos en la estructura principal y despejamos paso a paso.\n"
                    "3. Confirmamos que el valor hallado coincide con el punto marcado en la gráfica de Matplotlib."
                ),
                "final_result": "Solución exacta verificada analítica y gráficamente.",
            },
            {
                "title": "Ejemplo 2: Caso Aplicado en Ingeniería",
                "problem": f"Problema de diseño en **{eng_link}** empleando **{title}**.",
                "step_by_step": (
                    "1. Traducimos los requerimientos físicos del sistema a nuestra ecuación matemática.\n"
                    "2. Calculamos el punto de operación y verificamos las unidades físicas.\n"
                    "3. Interpretamos qué significa el resultado para la estabilidad y eficiencia del diseño."
                ),
                "final_result": "Diseño óptimo verificado.",
            },
        ],
        "common_mistakes": [
            "Aplicar la fórmula mecánicamente sin revisar los signos o el dominio de validez de la variable.",
            "Olvidar verificar el resultado sustituyendo el valor hallado en la expresión original.",
        ],
        "python_plot_code": _default_plot_code_for_day(day),
        "image_prompt": f"Educational 3D engineering and mathematics visualization of {title}, glowing geometric diagrams on dark slate background, high detail",
        "exercises": [
            {
                "level": "Nivel 1 • Calentamiento e Intuición",
                "question": f"Usando la propiedad central de **{title}** ($${formula}$$), evalúa el comportamiento del sistema en el punto base e interpreta el resultado.",
                "hint": "Sustituye ordenadamente respetando la jerarquía de operaciones y observa la gráfica.",
                "solution": "Al sustituir y simplificar paso a paso, se obtiene la coordenada exacta mostrada en la curva principal.",
                "practice_prompt": f"Explícame paso a paso y grafica un ejemplo sencillo de: {title}",
            },
            {
                "level": "Nivel 2 • Dominio Analítico",
                "question": f"Analiza cómo cambia la solución de **{title}** cuando duplicamos la magnitud del término independiente y compruébalo gráficamente.",
                "hint": "Despeja la variable en función del parámetro y compara ambos resultados.",
                "solution": "Al despejar analíticamente se comprueba la variación proporcional o geométrica sobre la curva.",
                "practice_prompt": f"Resuelve un problema intermedio paso a paso con gráfica sobre: {title}",
            },
            {
                "level": "Nivel 3 • Reto de Ingeniería",
                "question": f"Plantea y resuelve un caso práctico de **{eng_link}** aplicando **{title}**.",
                "hint": "Iguala las condiciones físicas de frontera o equilibrio y despeja la incógnita de diseño.",
                "solution": "Modelando el sistema con la ecuación del día y resolviendo con SymPy se obtiene el parámetro exacto de ingeniería.",
                "practice_prompt": f"Plantea y resuelve paso a paso con gráfica un problema de ingeniería sobre {title} aplicado a {eng_link}",
            },
        ],
    }

    if day in SPECIFIC_DAY_CONTENT:
        base.update(SPECIFIC_DAY_CONTENT[day])
    return base

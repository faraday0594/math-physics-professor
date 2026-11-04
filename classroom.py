import json
import re
from typing import Any, Dict, List, Optional
import sympy as sp
from openai import OpenAI

from sandbox import execute_math_physics_code
from local_professor import _extract_math_candidate, TRANSFORMATIONS
from sympy.parsing.sympy_parser import parse_expr

CLASSROOM_SYSTEM_PROMPT = """Eres el "Profesor MiniMax en el Aula", un catedrático extraordinariamente didáctico (estilo 3Blue1Brown / Richard Feynman) que convierte cualquier problema de Matemáticas o Física en una **Clase Magistral Interactiva por Diapositivas (Slides)**.

TU OBJETIVO:
Más allá de solo dar la cuenta fría, debes enseñar **CÓMO SE INTUYE** cada paso, **POR QUÉ** se elige cada herramienta o transformación y **QUÉ SIGNIFICA** geométrica y físicamente.

REGLAS ESTRICTAS DE RESPUESTA:
Debes responder ÚNICAMENTE con un objeto JSON válido (sin texto adicional fuera del JSON, o dentro de un bloque ```json ... ```) con esta estructura exacta:
{
  "course_title": "Título atractivo de la clase magistral",
  "subtitle": "Subtítulo conceptual (ej. De la intuición geométrica al cálculo exacto)",
  "slides": [
    {
      "step_number": 1,
      "badge": "Intuición Inicial",
      "title": "Título de la diapositiva 1",
      "intuition_callout": "Una frase reveladora sobre cómo intuir este paso antes de hacer cuentas.",
      "content_markdown": "Explicación didáctica en Markdown con fórmulas LaTeX ($...$ y $$...$$) bien explicadas.",
      "key_formula": "Fórmula central de esta diapositiva en LaTeX puro (sin $$), ej: \\int_a^b f(x)\\,dx = F(b) - F(a)",
      "python_plot_code": "Código Python completo e independiente usando matplotlib.pyplot as plt y numpy/sympy que genera una gráfica específica para esta diapositiva (o cadena vacía \"\" si no requiere gráfica nueva).",
      "mini_check": {
        "question": "Una breve pregunta reflexiva para el alumno sobre esta diapositiva",
        "answer": "Respuesta clara que confirma la intuición"
      }
    }
  ]
}

DISEÑO DE LAS DIAPOSITIVAS (Genera entre 4 y 5 diapositivas progresivas):
- **Slide 1 (La Gran Idea e Intuición Visual)**: ¿Qué nos están preguntando realmente? ¿Cómo visualizarlo mentalmente sin fórmulas complicadas? Incluye un `python_plot_code` que dibuje el planteamiento inicial del problema (la curva limpia, el diagrama o escenario físico).
- **Slide 2 (La Estrategia / Herramienta Secreta)**: ¿Cómo atacamos el problema? ¿Qué propiedad algebraica, derivada, antiderivada o ley de la física es la llave maestra aquí y por qué funciona?
- **Slide 3 (Construcción Paso a Paso en el Pizarrón)**: El desarrollo detallado donde transformamos las ecuaciones paso a paso explicando el "porqué" de cada signo y cada término. Incluye un `python_plot_code` que muestre el paso intermedio (ej. raíces, vectores descompuestos, función derivada o antiderivada).
- **Slide 4 (El Clímax Visual y Resultado Exacto)**: Unimos las piezas, obtenemos el resultado final y analizamos posibles trampas (como cambios de signo, puntos críticos o límites). Incluye un `python_plot_code` rico y detallado que coloree las regiones, marque los puntos clave y muestre la solución final.
- **Slide 5 (Resumen para Llevar y Reto Mental)**: Qué aprendimos hoy que sirve para resolver mil problemas parecidos.

REGLAS PARA `python_plot_code`:
- Cada `python_plot_code` no vacío se ejecuta de forma independiente en Python con `matplotlib.pyplot as plt`, `numpy as np`, `sympy as sp`.
- NO llames a `plt.show()`. Crea una figura clara con `plt.figure(figsize=(7.5, 4.4))`, títulos, etiquetas, colores elegantes (`#0284c7`, `#10b981`, `#f59e0b`, `#ef4444`, `#8b5cf6`) y `plt.grid(True, alpha=0.3)`.
"""


def _parse_json_from_llm(raw_text: str) -> Optional[Dict[str, Any]]:
    text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    candidate = fence.group(1) if fence else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _attach_plots_to_slides(deck: Dict[str, Any]) -> Dict[str, Any]:
    slides = deck.get("slides", [])
    for slide in slides:
        code = (slide.get("python_plot_code") or "").strip()
        if code:
            exec_res = execute_math_physics_code(code)
            slide["plots"] = exec_res.get("plots", [])
            slide["plot_stdout"] = exec_res.get("stdout", "")
            slide["plot_error"] = exec_res.get("error", "")
        else:
            slide["plots"] = []
    return deck


def generate_classroom_lesson(
    problem_prompt: str,
    previous_answer: str,
    api_key: str,
    base_url: str,
    model: str,
) -> Dict[str, Any]:
    """
    Calls MiniMax to generate a structured multi-slide interactive classroom lesson,
    executes the per-slide Python visualization scripts, and falls back to a rich
    local SymPy+Matplotlib slide generator if MiniMax returns an error.
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    user_msg = (
        f"PROBLEMA PLANTEADO POR EL ESTUDIANTE:\n{problem_prompt}\n\n"
        f"RESOLUCIÓN PREVIA DE REFERENCIA:\n{previous_answer[:3000]}\n\n"
        "Genera ahora la Clase Magistral Interactiva dividida en diapositivas (JSON estricto) "
        "explicando cómo se intuye cada paso y con scripts de Python (`python_plot_code`) "
        "que generen gráficas progresivas para las diapositivas."
    )

    try:
        extra_body = {"reasoning_effort": "medium"} if "M3" in model else None
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CLASSROOM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            extra_body=extra_body,
        )
        raw_content = resp.choices[0].message.content or ""
        parsed = _parse_json_from_llm(raw_content)
        if parsed and isinstance(parsed.get("slides"), list) and len(parsed["slides"]) > 0:
            deck = _attach_plots_to_slides(parsed)
            deck["model_used"] = model
            return deck
    except Exception as exc:
        err_msg = str(exc)
        deck = _build_local_classroom_slides(problem_prompt, previous_answer)
        deck["model_used"] = f"Aula Científica Local (SymPy + Matplotlib)"
        deck["api_notice"] = err_msg
        return deck

    deck = _build_local_classroom_slides(problem_prompt, previous_answer)
    deck["model_used"] = "Aula Científica (SymPy + Matplotlib)"
    return deck


def _build_local_classroom_slides(problem_prompt: str, previous_answer: str) -> Dict[str, Any]:
    """
    Builds a complete 4-slide progressive classroom lesson with custom per-slide
    SymPy + Matplotlib visualizations for any equation, integral, derivative, or physics problem.
    """
    text = (problem_prompt or "2*x - 1 = 5").strip()
    lower = text.lower()

    x = sp.Symbol("x", real=True)
    local_dict = {"x": x, "X": x, "e": sp.E, "pi": sp.pi, "sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "sqrt": sp.sqrt}

    if any(k in lower for k in ["integral", "integrar", "área bajo", "area bajo"]):
        cand = _extract_math_candidate(text)
        if "=" in cand:
            cand = cand.split("=")[-1].strip() or "x**3 - 4*x**2 + 3*x + 2"
        try:
            expr = parse_expr(cand, local_dict=local_dict, transformations=TRANSFORMATIONS)
            if not expr.free_symbols:
                expr = x**3 - 4 * x**2 + 3 * x + 2
        except Exception:
            expr = x**3 - 4 * x**2 + 3 * x + 2

        lim_match = re.search(r"(?:entre|de|desde|\[)\s*(-?\d+(?:\.\d+)?)\s*(?:y|a|hasta|,)\s*(-?\d+(?:\.\d+)?)", lower)
        a_lim = float(lim_match.group(1)) if lim_match else 0.0
        b_lim = float(lim_match.group(2)) if lim_match else 3.0

        F_expr = sp.integrate(expr, x)
        net_val = float(sp.N(sp.integrate(expr, (x, a_lim, b_lim))))
        expr_ltx = sp.latex(expr)
        F_ltx = sp.latex(F_expr)

        deck = {
            "course_title": "Clase Magistral: Intuición y Cálculo de Integrales Definidas",
            "subtitle": f"Comprendiendo paso a paso ∫ ({expr_ltx}) dx en [{a_lim}, {b_lim}]",
            "slides": [
                {
                    "step_number": 1,
                    "badge": "1. Intuición Geométrica",
                    "title": "¿Qué estamos midiendo realmente?",
                    "intuition_callout": "Antes de integrar fórmulas, imagina que la curva es el techo de un terreno y el eje X es el suelo. Integrar es sumar infinitas tiras verticales de ancho dx.",
                    "content_markdown": (
                        f"Observemos primero el comportamiento de nuestra función en el intervalo $[{a_lim}, {b_lim}]$:\n\n"
                        f"$$f(x) = {expr_ltx}$$\n\n"
                        "- Cuando la curva está **por encima del eje $X$** ($f(x) > 0$), las tiras suman **área positiva**.\n"
                        "- Cuando la curva baja **por debajo del eje $X$** ($f(x) < 0$), la integral definida resta ese tramo (**área con signo negativo**)."
                    ),
                    "key_formula": f"f(x) = {expr_ltx}",
                    "python_plot_code": f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
f = sp.sympify("{str(expr)}", locals={{'x': x}})
f_num = sp.lambdify(x, f, 'numpy')
xv = np.linspace({a_lim - 0.5}, {b_lim + 0.5}, 350)
yv = np.broadcast_to(f_num(xv), xv.shape)

plt.figure(figsize=(7.5, 4.3))
plt.plot(xv, yv, color='#0284c7', lw=2.6, label=r'$f(x) = {expr_ltx}$')
plt.axhline(0, color='#334155', lw=1.2)
plt.axvline({a_lim}, color='#f59e0b', ls='--', label='Inicio x = {a_lim}')
plt.axvline({b_lim}, color='#10b981', ls='--', label='Fin x = {b_lim}')
plt.title('Paso 1: Explorando el perfil de la curva f(x)')
plt.xlabel('x')
plt.ylabel('f(x)')
plt.legend()
plt.grid(True, alpha=0.3)""",
                    "mini_check": {
                        "question": "¿Por qué es importante mirar primero si la gráfica cruza el eje X?",
                        "answer": "Porque si cruza el eje X, la integral definida nos dará el área neta (positivos menos negativos), mientras que el área geométrica suma todos los tramos en valor absoluto.",
                    },
                },
                {
                    "step_number": 2,
                    "badge": "2. Aproximación de Riemann",
                    "title": "¿Cómo se intuye una integral? Sumando rectángulos",
                    "intuition_callout": "El símbolo ∫ es una 'S' alargada de 'Suma' inventada por Leibniz: sumamos rectángulos de altura f(x) y base muy delgada Δx.",
                    "content_markdown": (
                        "Si dividimos el intervalo en $N$ rectángulos pequeños de base $\\Delta x$:\n\n"
                        "$$\\text{Área} \\approx \\sum_{i=1}^{N} f(x_i)\\,\\Delta x$$\n\n"
                        "En la gráfica de esta diapositiva puedes ver cómo los rectángulos siguen la silueta de la curva. "
                        "Cuando hacemos los rectángulos infinitamente delgados ($\\Delta x \\to dx$), la suma aproximada se convierte en nuestra **integral exacta**."
                    ),
                    "key_formula": "\\int_a^b f(x)\\,dx = \\lim_{N\\to\\infty} \\sum_{i=1}^N f(x_i)\\,\\Delta x",
                    "python_plot_code": f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
f = sp.sympify("{str(expr)}", locals={{'x': x}})
f_num = sp.lambdify(x, f, 'numpy')
xv = np.linspace({a_lim}, {b_lim}, 300)
yv = np.broadcast_to(f_num(xv), xv.shape)

N = 18
dx = ({b_lim} - ({a_lim})) / N
x_rects = np.linspace({a_lim} + dx/2, {b_lim} - dx/2, N)
y_rects = np.broadcast_to(f_num(x_rects), x_rects.shape)

plt.figure(figsize=(7.5, 4.3))
plt.bar(x_rects, y_rects, width=dx*0.92, color='#38bdf8', alpha=0.45, edgecolor='#0284c7', label=f'Suma de Riemann (N={{N}} rectángulos)')
plt.plot(xv, yv, color='#0f172a', lw=2.3, label='Curva exacta f(x)')
plt.axhline(0, color='#334155', lw=1)
plt.title('Paso 2: Intuición con Rectángulos de Riemann')
plt.xlabel('x')
plt.ylabel('f(x)')
plt.legend()
plt.grid(True, alpha=0.3)""",
                    "mini_check": {
                        "question": "¿Qué ocurre con el error de los escalones cuando el número de rectángulos N tiende a infinito?",
                        "answer": "El error desaparece por completo y la suma de los rectángulos converge al área exacta bajo la curva.",
                    },
                },
                {
                    "step_number": 3,
                    "badge": "3. La Antiderivada F(x)",
                    "title": "El puente mágico: Teorema Fundamental del Cálculo",
                    "intuition_callout": "En vez de sumar infinitos rectángulos a mano, Newton y Barrow descubrieron que basta encontrar una función F(x) cuya derivada sea f(x).",
                    "content_markdown": (
                        "Aplicamos la **regla inversa de la potencia** a cada término ($\\int x^n\\,dx = \\frac{x^{n+1}}{n+1}$):\n\n"
                        f"$$F(x) = \\int \\left({expr_ltx}\\right)\\,dx = {F_ltx}$$\n\n"
                        "Observa en la gráfica cómo la función acumuladora $F(x)$ (en púrpura) **crece** siempre que $f(x) > 0$ y alcanza su valor final acumulado en $x = "
                        f"{b_lim}$."
                    ),
                    "key_formula": f"F(x) = {F_ltx}",
                    "python_plot_code": f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
f = sp.sympify("{str(expr)}", locals={{'x': x}})
F = sp.integrate(f, x)
f_num = sp.lambdify(x, f, 'numpy')
F_num = sp.lambdify(x, F, 'numpy')

xv = np.linspace({a_lim}, {b_lim}, 300)
plt.figure(figsize=(7.5, 4.3))
plt.plot(xv, np.broadcast_to(f_num(xv), xv.shape), color='#0284c7', lw=2, ls='--', label=r' Función tasa $f(x)$')
plt.plot(xv, np.broadcast_to(F_num(xv), xv.shape), color='#8b5cf6', lw=2.8, label=r'Área acumulada $F(x)$')
plt.scatter([{b_lim}], [float(F_num({b_lim}))], color='#ef4444', s=90, zorder=5, label=f'F({b_lim}) = {{float(F_num({b_lim})):.2f}}')
plt.axhline(0, color='#334155', lw=1)
plt.title('Paso 3: La función acumuladora (Antiderivada F(x))')
plt.xlabel('x')
plt.ylabel('Valor')
plt.legend()
plt.grid(True, alpha=0.3)""",
                    "mini_check": {
                        "question": "Si derivamos F(x), ¿qué función recuperamos?",
                        "answer": "Recuperamos exactamente la función original f(x). Por eso integrar y derivar son operaciones inversas.",
                    },
                },
                {
                    "step_number": 4,
                    "badge": "4. Resultado y Regiones Con Signo",
                    "title": "Evaluación Final: Regla de Barrow y Sombras Positivas/Negativas",
                    "intuition_callout": "Separar en verde las zonas donde f(x) > 0 y en rojo donde f(x) < 0 nos permite distinguir la integral neta del área física total.",
                    "content_markdown": (
                        f"Evaluamos $F({b_lim}) - F({a_lim})$:\n\n"
                        f"$$\\int_{{{a_lim}}}^{{{b_lim}}} \\left({expr_ltx}\\right)\\,dx = F({b_lim}) - F({a_lim}) = {net_val:.4g}$$\n\n"
                        "En la gráfica final hemos separado con precisión:\n"
                        "- **Región Verde ($f(x) \\ge 0$):** Aporta área positiva.\n"
                        "- **Región Roja ($f(x) < 0$):** Pequeño valle negativo debajo del eje $X$."
                    ),
                    "key_formula": f"\\int_{{{a_lim}}}^{{{b_lim}}} f(x)\\,dx = {net_val:.4g}",
                    "python_plot_code": f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
f = sp.sympify("{str(expr)}", locals={{'x': x}})
f_num = sp.lambdify(x, f, 'numpy')

xv = np.linspace({a_lim}, {b_lim}, 500)
yv = np.broadcast_to(f_num(xv), xv.shape)

plt.figure(figsize=(7.5, 4.3))
plt.plot(xv, yv, color='#0f172a', lw=2.4, label=r'$f(x) = {expr_ltx}$')
plt.fill_between(xv, yv, 0, where=(yv >= 0), color='#10b981', alpha=0.4, interpolate=True, label='Región Positiva (f > 0)')
plt.fill_between(xv, yv, 0, where=(yv < 0), color='#ef4444', alpha=0.5, interpolate=True, label='Región Negativa (f < 0)')
plt.axhline(0, color='#334155', lw=1.2)
plt.title(f'Paso 4: Resultado Final — Integral Neta = {net_val:.4g}')
plt.xlabel('x')
plt.ylabel('f(x)')
plt.legend()
plt.grid(True, alpha=0.3)""",
                    "mini_check": {
                        "question": "¿Por qué el área geométrica total es un poco mayor que la integral neta cuando hay zona roja?",
                        "answer": "Porque la integral neta resta la zona roja (negativa), mientras que el área geométrica suma su valor absoluto.",
                    },
                },
            ],
        }
        return _attach_plots_to_slides(deck)

    # Generic Equation / Function Classroom Deck
    cand = _extract_math_candidate(text)
    if "=" in cand and not cand.strip().startswith("="):
        l_raw, r_raw = cand.split("=", 1)
    else:
        l_raw, r_raw = cand.lstrip("=") or "2*x - 1", "0"

    try:
        lhs = parse_expr(l_raw.strip() or "2*x - 1", local_dict=local_dict, transformations=TRANSFORMATIONS)
        rhs = parse_expr(r_raw.strip() or "0", local_dict=local_dict, transformations=TRANSFORMATIONS)
    except Exception:
        lhs = 2 * x - 1
        rhs = sp.Integer(5)

    sols = sp.solve(sp.Eq(lhs, rhs), x)
    real_sols = [float(sp.N(s)) for s in sols if s.is_real]
    sol_center = real_sols[0] if real_sols else 0.0
    lhs_ltx = sp.latex(lhs)
    rhs_ltx = sp.latex(rhs)
    diff_expr = sp.simplify(lhs - rhs)
    diff_ltx = sp.latex(diff_expr)
    sol_ltx = ", ".join([sp.latex(s) for s in sols]) or "\\text{Sin raíz real}"

    deck = {
        "course_title": "Clase Magistral: El Arte de Resolver y Visualizar Ecuaciones",
        "subtitle": f"Intuición paso a paso para {lhs_ltx} = {rhs_ltx}",
        "slides": [
            {
                "step_number": 1,
                "badge": "1. Intuición de la Balanza",
                "title": "¿Qué significa el signo '=' en una ecuación?",
                "intuition_callout": "Imagina una balanza de dos platillos en equilibrio perfecto: el lado izquierdo y el lado derecho pesan exactamente lo mismo solo cuando x toma el valor correcto.",
                "content_markdown": (
                    f"Nuestra misión es descubrir qué número escondido detrás de la letra $x$ hace que ambos lados produzcan el mismo valor:\n\n"
                    f"$$\\underbrace{{{lhs_ltx}}}_{{\\text{{Función Izquierda }} y_1(x)}} = \\underbrace{{{rhs_ltx}}}_{{\\text{{Altura Objetivo }} y_2(x)}}$$\n\n"
                    "En vez de ver esto como símbolos abstractos, tracemos primero la curva del lado izquierdo $y_1(x)$ para ver cómo se comporta."
                ),
                "key_formula": f"{lhs_ltx} = {rhs_ltx}",
                "python_plot_code": f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
lhs = sp.sympify("{str(lhs)}", locals={{'x': x}})
f1 = sp.lambdify(x, lhs, 'numpy')
xv = np.linspace({sol_center - 4}, {sol_center + 4}, 300)
yv = np.broadcast_to(f1(xv), xv.shape)

plt.figure(figsize=(7.5, 4.3))
plt.plot(xv, yv, color='#0284c7', lw=2.6, label=r'$y_1(x) = {lhs_ltx}$')
plt.axhline(0, color='#475569', lw=1)
plt.axvline(0, color='#475569', lw=1)
plt.title('Paso 1: Visualizando el miembro izquierdo como una función')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True, alpha=0.3)""",
                "mini_check": {
                    "question": "¿Por qué podemos mantener la igualdad si hacemos la misma operación en ambos lados?",
                    "answer": "Porque si a dos platillos que pesan igual les sumas, restas o divides la misma cantidad, la balanza sigue equilibrada.",
                },
            },
            {
                "step_number": 2,
                "badge": "2. Transformación a Raíz Cero",
                "title": "Llevando todo a un solo lado: f(x) = 0",
                "intuition_callout": "Cualquier ecuación A = B es equivalente a preguntar: ¿cuándo la diferencia (A - B) vale exactamente cero?",
                "content_markdown": (
                    f"Si restamos ${rhs_ltx}$ en ambos lados de la ecuación, unificamos todo en una sola expresión igualada a cero:\n\n"
                    f"$${diff_ltx} = 0$$\n\n"
                    "Geométricamente, esto transforma el problema en buscar el punto donde la curva resultante **cruza el suelo (el eje horizontal $y = 0$)**."
                ),
                "key_formula": f"{diff_ltx} = 0",
                "python_plot_code": f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
diff_e = sp.sympify("{str(diff_expr)}", locals={{'x': x}})
f_diff = sp.lambdify(x, diff_e, 'numpy')
xv = np.linspace({sol_center - 4}, {sol_center + 4}, 300)
yv = np.broadcast_to(f_diff(xv), xv.shape)

plt.figure(figsize=(7.5, 4.3))
plt.plot(xv, yv, color='#8b5cf6', lw=2.6, label=r'$g(x) = {diff_ltx}$')
plt.axhline(0, color='#10b981', lw=2, ls='--', label='Nivel cero (g(x) = 0)')
plt.title('Paso 2: Buscando dónde la diferencia cruza el eje X (y = 0)')
plt.xlabel('x')
plt.ylabel('g(x)')
plt.legend()
plt.grid(True, alpha=0.3)""",
                "mini_check": {
                    "question": "¿Qué representa gráficamente una solución de g(x) = 0?",
                    "answer": "Representa la coordenada x donde la gráfica corta al eje horizontal X.",
                },
            },
            {
                "step_number": 3,
                "badge": "3. Despeje y Cruce Exacto",
                "title": "El Punto de Encuentro y Verificación",
                "intuition_callout": "Al despejar x deshacemos, en orden inverso, las operaciones que rodean a la incógnita.",
                "content_markdown": (
                    f"Resolviendo la ecuación obtenemos nuestra solución exacta:\n\n"
                    f"$$x = {sol_ltx}$$\n\n"
                    "En la gráfica final superponemos ambas curvas ($y_1$ en azul y $y_2$ en naranja) y marcamos en **rojo** el punto exacto donde se intersectan."
                ),
                "key_formula": f"x = {sol_ltx}",
                "python_plot_code": f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
lhs = sp.sympify("{str(lhs)}", locals={{'x': x}})
rhs = sp.sympify("{str(rhs)}", locals={{'x': x}})
f1 = sp.lambdify(x, lhs, 'numpy')
f2 = sp.lambdify(x, rhs, 'numpy')

xv = np.linspace({sol_center - 4}, {sol_center + 4}, 300)
y1 = np.broadcast_to(f1(xv), xv.shape)
y2 = np.broadcast_to(f2(xv), xv.shape)

plt.figure(figsize=(7.5, 4.3))
plt.plot(xv, y1, color='#0284c7', lw=2.6, label=r'$y_1 = {lhs_ltx}$')
plt.plot(xv, y2, color='#f59e0b', lw=2.2, ls='--', label=r'$y_2 = {rhs_ltx}$')
for sx in {real_sols}:
    sy = float(f1(sx))
    plt.scatter([sx], [sy], color='#ef4444', s=110, zorder=5, label=f'Intersección ({{sx:.3g}}, {{sy:.3g}})')
plt.title('Paso 3: Intersección Exacta Comprobada')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True, alpha=0.3)""",
                "mini_check": {
                    "question": "¿Cómo comprobamos en 5 segundos que el resultado es correcto?",
                    "answer": "Sustituyendo el valor hallado de x en la ecuación original y verificando que ambos lados dan el mismo número.",
                },
            },
        ],
    }
    return _attach_plots_to_slides(deck)

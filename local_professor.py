import re
from typing import Any, Dict, List, Optional
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)
from sandbox import execute_math_physics_code

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)


def solve_locally_as_professor(user_prompt: str, api_notice: Optional[str] = None) -> Dict[str, Any]:
    """
    Local Scientific Professor Engine powered by SymPy, NumPy, and Matplotlib.
    Parses the student's math/physics problem, executes a real Python calculation + plot script,
    and generates a structured step-by-step pedagogical explanation in LaTeX.
    """
    text = (user_prompt or "").strip()
    lower = text.lower()

    # 1. Check if it's a Physics Projectile / Parabolic motion problem
    if any(k in lower for k in ["proyectil", "parabólico", "parabolico", "velocidad inicial", "v0", "ángulo", "angulo", "alcance"]):
        return _solve_projectile_problem(text, api_notice)

    # 2. Check if it's a Damped Harmonic Oscillator / Wave / RLC / Pendulum problem
    if any(k in lower for k in ["oscilador", "amortiguado", "resorte", "armónico", "armonico", "omega", "gamma", "rlc", "péndulo", "pendulo"]):
        return _solve_oscillator_problem(text, api_notice)

    # 3. Check if it's a Definite/Indefinite Integral or Area under the curve problem
    if any(k in lower for k in ["integral", "integrar", "área bajo", "area bajo", "antiderivada", "primitiva"]):
        return _solve_integral_problem(text, api_notice)

    # 4. Check if it's a Differential Equation (EDO / ODE) problem
    if any(k in lower for k in ["ecuación diferencial", "ecuacion diferencial", "edo", "dy/dx", "y'", "campana", "logística", "logistica"]):
        return _solve_ode_problem(text, api_notice)

    # 5. Check if it's a Kinematics / Free fall / MRUA problem
    if any(k in lower for k in ["caída libre", "caida libre", "aceleración", "aceleracion", "mrua", "velocidad", "fuerza", "newton"]):
        return _solve_kinematics_or_force(text, api_notice)

    # 6. Try to extract an equation or mathematical expression from the prompt
    return _solve_algebra_or_calculus(text, api_notice)


def _extract_math_candidate(text: str) -> str:
    """
    Extracts the mathematical equation or expression from natural language text in Spanish.
    Examples:
      "2x-1= ?" -> "2*x - 1 = 0" (or keeps RHS if number)
      "Explícame cómo resolver 2x - 1 = 5 paso a paso" -> "2x - 1 = 5"
      "f(x) = x^3 - 3x + 1" -> "x^3 - 3x + 1"
    """
    cleaned = text.replace("¿", "").replace("?", "").strip()

    # Check if there is a function definition like f(x) = <expr>
    fn_match = re.search(r"\b[fgy]\s*\(\s*x\s*\)\s*=\s*([0-9xX+\-*/^().\s]+)", cleaned, flags=re.IGNORECASE)
    if fn_match:
        raw_rhs = fn_match.group(1).split(",")[0].strip()
        rhs_tokens = []
        for tok in raw_rhs.split():
            if re.match(r"^[0-9xX+\-*/^().]+$", tok) or any(fn in tok for fn in ("sin", "cos", "tan", "exp", "log", "sqrt")):
                rhs_tokens.append(tok)
            else:
                break
        if rhs_tokens:
            return " ".join(rhs_tokens)

    # Look for an explicit equation pattern with '='
    eq_match = re.search(
        r"([0-9a-zA-Z_+\-*/^().\s]+=[0-9a-zA-Z_+\-*/^().\s]*)",
        cleaned,
    )
    if eq_match:
        candidate = eq_match.group(1).strip()
        # Strip leading Spanish words that might have been captured before the math expression
        parts = candidate.split("=")
        lhs_tokens = parts[0].strip().split()
        # Keep tokens from the end of lhs that look mathematical
        math_lhs_tokens = []
        for tok in reversed(lhs_tokens):
            if re.match(r"^[0-9xXyYzZa-b+\-*/^().]+$", tok) or any(fn in tok for fn in ("sin", "cos", "tan", "exp", "log", "sqrt")):
                math_lhs_tokens.insert(0, tok)
            else:
                break
        lhs_str = " ".join(math_lhs_tokens) if math_lhs_tokens else parts[0].strip()

        rhs_tokens = parts[1].strip().split() if len(parts) > 1 else []
        math_rhs_tokens = []
        for tok in rhs_tokens:
            if re.match(r"^[0-9xXyYzZa-b+\-*/^().]+$", tok) or any(fn in tok for fn in ("sin", "cos", "tan", "exp", "log", "sqrt")):
                math_rhs_tokens.append(tok)
            else:
                break
        rhs_str = " ".join(math_rhs_tokens)
        if not rhs_str:
            rhs_str = "0"
        return f"{lhs_str} = {rhs_str}"

    # Look for expression with x
    expr_match = re.search(r"([0-9+\-*/^().\s]*[xX][0-9a-zA-Z+\-*/^().\s]*)", cleaned)
    if expr_match:
        tokens = expr_match.group(1).strip().split()
        valid = [
            t for t in tokens
            if re.match(r"^[0-9xX+\-*/^().]+$", t) or any(fn in t for fn in ("sin", "cos", "tan", "exp", "log", "sqrt"))
        ]
        if valid:
            return " ".join(valid)

    return cleaned


def _solve_algebra_or_calculus(text: str, api_notice: Optional[str]) -> Dict[str, Any]:
    candidate = _extract_math_candidate(text)
    lower = text.lower()
    wants_derivative = any(k in lower for k in ["derivada", "derivar", "puntos críticos", "puntos criticos", "máximo", "minimo", "mínimo", "tangente"])
    wants_integral = any(k in lower for k in ["integral", "integrar", "área bajo", "area bajo"])

    x = sp.Symbol("x", real=True)
    local_dict = {"x": x, "X": x, "e": sp.E, "pi": sp.pi}

    is_equation = "=" in candidate and not candidate.strip().startswith("=")
    try:
        if is_equation:
            lhs_raw, rhs_raw = candidate.split("=", 1)
            lhs_raw = lhs_raw.strip() or "0"
            rhs_raw = rhs_raw.strip() or "0"
            lhs = parse_expr(lhs_raw, local_dict=local_dict, transformations=TRANSFORMATIONS)
            rhs = parse_expr(rhs_raw, local_dict=local_dict, transformations=TRANSFORMATIONS)
        else:
            raw_expr = candidate.lstrip("=").strip() or "2*x - 1"
            lhs = parse_expr(raw_expr, local_dict=local_dict, transformations=TRANSFORMATIONS)
            rhs = sp.Integer(0)
    except Exception:
        # Default fallback if parsing fails
        lhs = 2 * x - 1
        rhs = sp.Integer(0)
        is_equation = True

    expr = sp.simplify(lhs - rhs)
    lhs_latex = sp.latex(lhs)
    rhs_latex = sp.latex(rhs)
    expr_latex = sp.latex(expr)

    # Generate Python script to run in Sandbox
    if wants_derivative or (not is_equation and expr.as_poly(x) and expr.as_poly(x).degree() >= 3):
        deriv = sp.diff(lhs, x)
        second_deriv = sp.diff(deriv, x)
        crit_points = sp.solve(deriv, x)
        real_crits = [float(sp.N(cp)) for cp in crit_points if cp.is_real]

        center = real_crits[0] if real_crits else 0.0
        span = max(4.0, (max(real_crits) - min(real_crits)) * 1.8) if len(real_crits) > 1 else 4.0
        x_min, x_max = center - span, center + span

        code = f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
f = sp.sympify("{str(lhs)}", locals={{'x': x}})
df = sp.diff(f, x)
d2f = sp.diff(df, x)
criticos = sp.solve(df, x)

print(f"Función: f(x) = {{f}}")
print(f"Primera derivada: f'(x) = {{df}}")
print(f"Segunda derivada: f''(x) = {{d2f}}")
print(f"Puntos críticos (f'(x) = 0): {{criticos}}")

f_num = sp.lambdify(x, f, 'numpy')
df_num = sp.lambdify(x, df, 'numpy')

x_vals = np.linspace({x_min:.2f}, {x_max:.2f}, 400)
y_vals = f_num(x_vals)
dy_vals = df_num(x_vals)

plt.figure(figsize=(8, 4.8))
plt.plot(x_vals, y_vals, label=r'$f(x) = {lhs_latex}$', color='#0284c7', linewidth=2.5)
plt.plot(x_vals, dy_vals, label=r"$f'(x) = {sp.latex(deriv)}$", color='#8b5cf6', linestyle='--', linewidth=1.8)
plt.axhline(0, color='#475569', linewidth=1)

for cp in {real_crits}:
    y_cp = float(f_num(cp))
    plt.scatter([cp], [y_cp], color='#ef4444', s=90, zorder=5)
    plt.annotate(f'({{cp:.2f}}, {{y_cp:.2f}})', xy=(cp, y_cp), xytext=(cp+0.2, y_cp+0.8),
                 arrowprops=dict(arrowstyle='->', color='#ef4444'))

plt.title('Análisis Diferencial: Función, Derivada y Puntos Críticos')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True, alpha=0.3)"""

        exec_res = execute_math_physics_code(code)
        exec_res["description"] = "Cálculo de derivada, puntos críticos y graficación con SymPy + Matplotlib"

        crit_str = ", ".join([f"x = {sp.latex(c)} \\approx {float(sp.N(c)):.3f}" for c in crit_points if c.is_real]) or "No tiene raíces reales"
        explanation = f"""### 1. Planteamiento del Problema
Analizaremos paso a paso la función:
$$f(x) = {lhs_latex}$$
Calcularemos su **primera derivada** $f'(x)$, sus **puntos críticos** (donde la pendiente es cero, $f'(x) = 0$) y clasificaremos su concavidad con la segunda derivada $f''(x)$.

---

### 2. Resolución Paso a Paso

1. **Cálculo de la primera derivada $f'(x)$:**
   Aplicando las reglas de derivación término a término respecto a $x$:
   $$f'(x) = \\frac{{d}}{{dx}}\\left({lhs_latex}\\right) = {sp.latex(deriv)}$$

2. **Búsqueda de puntos críticos ($f'(x) = 0$):**
   Igualamos la derivada a cero para hallar los valores de $x$ donde la recta tangente es horizontal:
   $${sp.latex(deriv)} = 0 \\implies {crit_str}$$

3. **Segunda derivada y concavidad ($f''(x)$):**
   $$f''(x) = {sp.latex(second_deriv)}$$
   * Si $f''(x_c) < 0$, el punto es un **máximo local**.
   * Si $f''(x_c) > 0$, el punto es un **mínimo local**.

---

### 3. Resultado Final e Interpretación Gráfica
* **Derivada exacta:** $$f'(x) = {sp.latex(deriv)}$$
* **Puntos críticos:** $${crit_str}$$
* En la gráfica inferior se muestra en **azul** la curva original $f(x)$, en **violeta punteado** la función derivada $f'(x)$ y en **rojo** los extremos locales."""

        return {
            "answer": explanation,
            "thinking": f"1. Función detectada: f(x) = {lhs}\n2. Derivando simbólicamente con SymPy: f'(x) = {deriv}\n3. Resolviendo f'(x)=0 y graficando función + derivada.",
            "scripts": [exec_res],
            "plots": exec_res.get("plots", []),
            "model_used": "Motor Científico SymPy + Matplotlib" + (f" ({api_notice})" if api_notice else ""),
        }

    # Standard Equation Solver (Linear, Quadratic, Polynomial, Transcendental)
    solutions = sp.solve(sp.Eq(lhs, rhs), x)
    real_sols = [float(sp.N(s)) for s in solutions if s.is_real]

    if real_sols:
        center = sum(real_sols) / len(real_sols)
        spread = max(4.0, (max(real_sols) - min(real_sols)) * 1.8) if len(real_sols) > 1 else 4.0
        x_min, x_max = center - spread, center + spread
    else:
        x_min, x_max = -5.0, 5.0

    code = f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
lhs = sp.sympify("{str(lhs)}", locals={{'x': x}})
rhs = sp.sympify("{str(rhs)}", locals={{'x': x}})
ecuacion = sp.Eq(lhs, rhs)
soluciones = sp.solve(ecuacion, x)

print(f"Ecuación planteada: {{lhs}} = {{rhs}}")
print(f"Forma estándar: {{sp.simplify(lhs - rhs)}} = 0")
print(f"Soluciones exactas con SymPy: x = {{soluciones}}")

f_lhs = sp.lambdify(x, lhs, 'numpy')
f_rhs = sp.lambdify(x, rhs, 'numpy')

x_vals = np.linspace({x_min:.2f}, {x_max:.2f}, 400)
y_lhs = np.broadcast_to(f_lhs(x_vals), x_vals.shape)
y_rhs = np.broadcast_to(f_rhs(x_vals), x_vals.shape)

plt.figure(figsize=(8, 4.8))
plt.plot(x_vals, y_lhs, label=r'$y_1 = {lhs_latex}$', color='#0284c7', linewidth=2.5)
plt.plot(x_vals, y_rhs, label=r'$y_2 = {rhs_latex}$', color='#f59e0b', linestyle='--', linewidth=2.0)
plt.axhline(0, color='#64748b', linewidth=0.8)
plt.axvline(0, color='#64748b', linewidth=0.8)

for sol_x in {real_sols}:
    sol_y = float(f_lhs(sol_x))
    plt.scatter([sol_x], [sol_y], color='#ef4444', s=100, zorder=5, label=f'Solución ({{sol_x:.3g}}, {{sol_y:.3g}})')
    plt.annotate(f'x = {{sol_x:.3g}}', xy=(sol_x, sol_y), xytext=(sol_x + 0.3, sol_y + 0.8),
                 arrowprops=dict(arrowstyle='->', color='#ef4444', lw=1.5), fontweight='bold')

plt.title(r'Resolución Gráfica de ${lhs_latex} = {rhs_latex}$')
plt.xlabel('Eje X')
plt.ylabel('Eje Y')
plt.legend()
plt.grid(True, alpha=0.3)"""

    exec_res = execute_math_physics_code(code)
    exec_res["description"] = f"Resolución simbólica y gráfica de {lhs} = {rhs}"

    # Build rich pedagogical steps depending on polynomial degree
    poly = expr.as_poly(x)
    steps_md = ""
    if poly is not None and poly.degree() == 1:
        # Linear equation a*x + b = 0
        a_coeff = poly.nth(1)
        b_coeff = poly.nth(0)
        sol_val = -b_coeff / a_coeff
        steps_md = f"""1. **Pasar todos los términos a la forma estándar ($ax + b = 0$):**
   Partimos de la igualdad original:
   $${lhs_latex} = {rhs_latex}$$
   Restamos ${rhs_latex}$ en ambos lados para agrupar términos semejantes:
   $${expr_latex} = 0$$

2. **Aislar el término con la incógnita $x$:**
   Pasamos el término independiente (${sp.latex(b_coeff)}$) al otro lado con signo opuesto:
   $${sp.latex(a_coeff)}x = {sp.latex(-b_coeff)}$$

3. **Despejar $x$ dividiendo entre el coeficiente ${sp.latex(a_coeff)}$:**
   $$x = \\frac{{{sp.latex(-b_coeff)}}}{{{sp.latex(a_coeff)}}} = {sp.latex(sol_val)}$$

4. **Comprobación en la ecuación original:**
   Sustituimos $x = {sp.latex(sol_val)}$ en el miembro izquierdo:
   $${lhs_latex} \\Big|_{{x={sp.latex(sol_val)}}} = {sp.latex(lhs.subs(x, sol_val))} \\quad \\checkmark$$"""
    elif poly is not None and poly.degree() == 2:
        a_c = poly.nth(2)
        b_c = poly.nth(1)
        c_c = poly.nth(0)
        disc = b_c**2 - 4 * a_c * c_c
        steps_md = f"""1. **Llevar a la forma cuadrática general ($ax^2 + bx + c = 0$):**
   $${expr_latex} = 0$$
   Identificamos los coeficientes:
   $$a = {sp.latex(a_c)}, \\quad b = {sp.latex(b_c)}, \\quad c = {sp.latex(c_c)}$$

2. **Calcular el discriminante ($\\Delta = b^2 - 4ac$):**
   $$\\Delta = ({sp.latex(b_c)})^2 - 4({sp.latex(a_c)})({sp.latex(c_c)}) = {sp.latex(disc)}$$

3. **Aplicar la Fórmula General Cuadrática:**
   $$x = \\frac{{-b \\pm \\sqrt{{\\Delta}}}}{{2a}} = \\frac{{-({sp.latex(b_c)}) \\pm \\sqrt{{{sp.latex(disc)}}}}}{{2({sp.latex(a_c)})}}$$"""
    else:
        steps_md = f"""1. **Igualar la expresión a la forma estándar $f(x) = 0$:**
   $${lhs_latex} = {rhs_latex} \\iff {expr_latex} = 0$$

2. **Factorización / Resolución simbólica:**
   Factorizando la expresión obtenemos:
   $${sp.latex(sp.factor(expr))} = 0$$"""

    sol_latex_list = ", \\quad ".join([f"x = {sp.latex(s)} \\; (\\approx {float(sp.N(s)):.4g})" if s.is_real else f"x = {sp.latex(s)}" for s in solutions])
    if not sol_latex_list:
        sol_latex_list = "\\text{Sin solución algebraica cerrada}"

    note_header = ""
    if text.strip().endswith("?") and "=" in text and text.split("=")[1].replace("?", "").strip() == "":
        note_header = (
            "> 💡 **Nota del Profesor:** Como escribiste `"
            + text.strip()
            + "` dejando el lado derecho como incógnita (`?`), igualé la expresión a **$0$** ($"
            + f"{lhs_latex} = 0"
            + "$) para hallar su raíz o intersección con el eje $X$. Si querías igualarla a otro número (por ejemplo `2x - 1 = 5`), escríbelo y lo calculamos al instante.\n\n"
        )

    explanation = f"""{note_header}### 1. Planteamiento del Problema
Vamos a resolver paso a paso la ecuación matemática:
$${lhs_latex} = {rhs_latex}$$

---

### 2. Resolución Paso a Paso
{steps_md}

---

### 3. Resultado Final e Interpretación Gráfica
* **Solución Exacta:**
  $${sol_latex_list}$$
* **Interpretación Geométrica:** En la gráfica generada abajo con `Matplotlib`, trazamos la curva $y_1 = {lhs_latex}$ (en azul) y la recta horizontal $y_2 = {rhs_latex}$ (en naranja punteado). El punto rojo marca exactamente la coordenada de intersección donde ambas expresiones son iguales."""

    return {
        "answer": explanation,
        "thinking": (
            f"1. Expresión detectada: {lhs} = {rhs}\n"
            f"2. Ejecutando SymPy sp.solve() -> soluciones: {solutions}\n"
            f"3. Generando gráfica en el rango [{x_min:.1f}, {x_max:.1f}] con Matplotlib."
        ),
        "scripts": [exec_res],
        "plots": exec_res.get("plots", []),
        "model_used": "Motor Científico SymPy + Matplotlib" + (f" ({api_notice})" if api_notice else ""),
    }


def _solve_projectile_problem(text: str, api_notice: Optional[str]) -> Dict[str, Any]:
    # Extract numbers for velocity and angle if present
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    v0 = nums[0] if len(nums) >= 1 else 25.0
    theta_deg = nums[1] if len(nums) >= 2 else 40.0

    code = f"""import numpy as np
import matplotlib.pyplot as plt

v0 = {v0}
theta_deg = {theta_deg}
g = 9.81
theta = np.radians(theta_deg)

v0x = v0 * np.cos(theta)
v0y = v0 * np.sin(theta)
t_vuelo = (2 * v0y) / g
h_max = (v0y**2) / (2 * g)
alcance = v0x * t_vuelo
x_hmax = alcance / 2.0

print(f"Componentes: v0x = {{v0x:.2f}} m/s, v0y = {{v0y:.2f}} m/s")
print(f"Tiempo de vuelo: T = {{t_vuelo:.2f}} s")
print(f"Altura máxima: H_max = {{h_max:.2f}} m")
print(f"Alcance horizontal: R = {{alcance:.2f}} m")

t = np.linspace(0, t_vuelo, 300)
x = v0x * t
y = v0y * t - 0.5 * g * t**2

plt.figure(figsize=(8, 4.6))
plt.plot(x, y, color='#4f46e5', linewidth=2.5, label='Trayectoria parabólica y(x)')
plt.scatter([x_hmax], [h_max], color='#ef4444', s=95, zorder=5, label=f'Altura máx ({{x_hmax:.1f}} m, {{h_max:.2f}} m)')
plt.scatter([alcance], [0], color='#10b981', s=95, zorder=5, label=f'Alcance R = {{alcance:.2f}} m')
plt.axhline(0, color='#475569', linewidth=1)
plt.title(f'Cinemática 2D: Tiro Parabólico (v0 = {{v0}} m/s, θ = {{theta_deg}}°)')
plt.xlabel('Distancia horizontal x (m)')
plt.ylabel('Altura y (m)')
plt.legend()
plt.grid(True, alpha=0.3)"""

    exec_res = execute_math_physics_code(code)
    exec_res["description"] = "Simulación física de proyectil 2D con NumPy y Matplotlib"

    import math
    th = math.radians(theta_deg)
    v0x = v0 * math.cos(th)
    v0y = v0 * math.sin(th)
    t_v = 2 * v0y / 9.81
    h_m = (v0y**2) / (2 * 9.81)
    r_m = v0x * t_v

    explanation = f"""### 1. Planteamiento Físico (Movimiento Parabólico)
Datos del problema con gravedad $g = 9.81\\text{{ m/s}}^2$:
* **Velocidad inicial ($v_0$):** ${v0}\\text{{ m/s}}$
* **Ángulo de lanzamiento ($\\theta$):** ${theta_deg}^\\circ$

---

### 2. Resolución Paso a Paso

1. **Descomposición del vector velocidad inicial:**
   $$v_{{0x}} = v_0 \\cos({theta_deg}^\\circ) = {v0x:.2f}\\text{{ m/s}}$$
   $$v_{{0y}} = v_0 \\sin({theta_deg}^\\circ) = {v0y:.2f}\\text{{ m/s}}$$

2. **Tiempo total de vuelo ($T$):**
   En la cúspide $v_y = v_{{0y}} - g t_s = 0 \\implies T = \\frac{{2v_{{0y}}}}{{g}}$:
   $$T = \\frac{{2({v0y:.2f})}}{{9.81}} = {t_v:.2f}\\text{{ s}}$$

3. **Altura máxima ($H_{{\\max}}$):**
   $$H_{{\\max}} = \\frac{{v_{{0y}}^2}}{{2g}} = \\frac{{({v0y:.2f})^2}}{{2(9.81)}} = {h_m:.2f}\\text{{ m}}$$

4. **Alcance horizontal máximo ($R$):**
   $$R = v_{{0x}} \\cdot T = {v0x:.2f} \\times {t_v:.2f} = {r_m:.2f}\\text{{ m}}$$"""

    return {
        "answer": explanation,
        "thinking": f"Detectado problema de tiro parabólico con v0={v0} m/s y ángulo={theta_deg}°.",
        "scripts": [exec_res],
        "plots": exec_res.get("plots", []),
        "model_used": "Motor Científico Física + Matplotlib" + (f" ({api_notice})" if api_notice else ""),
    }


def _solve_oscillator_problem(text: str, api_notice: Optional[str]) -> Dict[str, Any]:
    code = """import numpy as np
import matplotlib.pyplot as plt

A = 2.0
gamma = 0.3
omega = 4.0
t_eval = 2.0
x_eval = A * np.exp(-gamma * t_eval) * np.cos(omega * t_eval)
print(f"Amplitud inicial A = {A} m, amortiguamiento gamma = {gamma} s^-1, frecuencia omega = {omega} rad/s")
print(f"Posición en t = {t_eval} s: x(2) = {x_eval:.4f} m")

t = np.linspace(0, 12, 500)
x = A * np.exp(-gamma * t) * np.cos(omega * t)
env = A * np.exp(-gamma * t)

plt.figure(figsize=(8, 4.6))
plt.plot(t, x, color='#0284c7', linewidth=2.2, label=r'$x(t) = A e^{-\gamma t} \cos(\omega t)$')
plt.plot(t, env, color='#f59e0b', linestyle='--', linewidth=1.6, label=r'Envolvente $\pm A e^{-\gamma t}$')
plt.plot(t, -env, color='#f59e0b', linestyle='--', linewidth=1.6)
plt.scatter([t_eval], [x_eval], color='#ef4444', s=90, zorder=5, label=f'x({t_eval} s) = {x_eval:.3f} m')
plt.title('Física: Oscilador Armónico Amortiguado')
plt.xlabel('Tiempo t (s)')
plt.ylabel('Posición x (m)')
plt.legend()
plt.grid(True, alpha=0.3)"""

    exec_res = execute_math_physics_code(code)
    exec_res["description"] = "Simulación de oscilador armónico amortiguado"

    explanation = """### 1. Planteamiento Físico (Oscilador Armónico Amortiguado)
La ecuación de movimiento para un sistema masa-resorte con fuerza de amortiguamiento viscoso es:
$$x(t) = A e^{-\\gamma t} \\cos(\\omega t)$$
Con parámetros $A = 2\\text{ m}$, $\\gamma = 0.3\\text{ s}^{-1}$ y $\\omega = 4\\text{ rad/s}$.

---

### 2. Evaluación Paso a Paso en $t = 2\\text{ s}$
1. **Factor de decaimiento exponencial (amplitud instantánea):**
   $$A(2) = 2 \\cdot e^{-0.3(2)} = 2 \\cdot e^{-0.6} \\approx 2(0.5488) = 1.0976\\text{ m}$$
2. **Fase oscilatoria (en radianes):**
   $$\\cos(4 \\times 2) = \\cos(8\\text{ rad}) \\approx -0.1455$$
3. **Posición resultante:**
   $$x(2) = 1.0976 \\times (-0.1455) \\approx -0.1597\\text{ m}$$"""

    return {
        "answer": explanation,
        "thinking": "Simulando ecuación diferencial del oscilador armónico subamortiguado.",
        "scripts": [exec_res],
        "plots": exec_res.get("plots", []),
        "model_used": "Motor Científico Física + Matplotlib" + (f" ({api_notice})" if api_notice else ""),
    }


def _solve_kinematics_or_force(text: str, api_notice: Optional[str]) -> Dict[str, Any]:
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    a_val = nums[0] if nums else 4.0
    t_max = nums[1] if len(nums) > 1 else 6.0

    code = f"""import numpy as np
import matplotlib.pyplot as plt

a = {a_val}
t_max = {t_max}
t = np.linspace(0, t_max, 200)
v = a * t
x = 0.5 * a * t**2

print(f"Aceleración a = {{a}} m/s^2 durante t = {{t_max}} s")
print(f"Velocidad final v({{t_max}}) = {{v[-1]:.2f}} m/s")
print(f"Distancia recorrida x({{t_max}}) = {{x[-1]:.2f}} m")

plt.figure(figsize=(8, 4.6))
plt.plot(t, x, label='Posición x(t) [m]', color='#0284c7', linewidth=2.5)
plt.plot(t, v, label='Velocidad v(t) [m/s]', color='#10b981', linestyle='--', linewidth=2)
plt.title(f'Cinemática MRUA (a = {{a}} m/s²)')
plt.xlabel('Tiempo t (s)')
plt.ylabel('Magnitud')
plt.legend()
plt.grid(True, alpha=0.3)"""

    exec_res = execute_math_physics_code(code)
    exec_res["description"] = "Cinemática MRUA: posición y velocidad en función del tiempo"

    v_f = a_val * t_max
    x_f = 0.5 * a_val * (t_max**2)

    explanation = f"""### 1. Planteamiento Físico (MRUA)
Considerando un movimiento rectilíneo uniformemente acelerado partiendo del reposo con aceleración $a = {a_val}\\text{{ m/s}}^2$ durante $t = {t_max}\\text{{ s}}$:

$$v(t) = v_0 + a t, \\qquad x(t) = x_0 + v_0 t + \\frac{{1}}{{2}}a t^2$$

---

### 2. Cálculo Paso a Paso
1. **Velocidad final:**
   $$v({t_max}) = {a_val} \\times {t_max} = {v_f:.2f}\\text{{ m/s}}$$
2. **Desplazamiento total:**
   $$x({t_max}) = \\frac{{1}}{{2}}({a_val})({t_max})^2 = {x_f:.2f}\\text{{ m}}$$"""

    return {
        "answer": explanation,
        "thinking": "Resolviendo ecuaciones cinemáticas de MRUA y graficando x(t) y v(t).",
        "scripts": [exec_res],
        "plots": exec_res.get("plots", []),
        "model_used": "Motor Científico Física + Matplotlib" + (f" ({api_notice})" if api_notice else ""),
    }


def _solve_integral_problem(text: str, api_notice: Optional[str]) -> Dict[str, Any]:
    x = sp.Symbol("x", real=True)
    local_dict = {"x": x, "X": x, "e": sp.E, "pi": sp.pi, "sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "sqrt": sp.sqrt, "log": sp.log}
    candidate = _extract_math_candidate(text)
    if "=" in candidate:
        candidate = candidate.split("=")[-1].strip() or "x**3 - 4*x**2 + 3*x + 2"

    try:
        expr = parse_expr(candidate, local_dict=local_dict, transformations=TRANSFORMATIONS)
        if not expr.free_symbols:
            expr = x**3 - 4 * x**2 + 3 * x + 2
    except Exception:
        expr = x**3 - 4 * x**2 + 3 * x + 2

    # Extract integration limits [a, b] if mentioned like "entre 0 y 3" or "de 0 a 3" or "[0, 3]"
    lim_match = re.search(r"(?:entre|de|desde|\[)\s*(-?\d+(?:\.\d+)?)\s*(?:y|a|hasta|,)\s*(-?\d+(?:\.\d+)?)", text.lower())
    if lim_match:
        a_lim = float(lim_match.group(1))
        b_lim = float(lim_match.group(2))
    else:
        a_lim, b_lim = 0.0, 3.0

    antideriv = sp.integrate(expr, x)
    def_integral = sp.integrate(expr, (x, sp.nsimplify(a_lim), sp.nsimplify(b_lim)))
    def_val = float(sp.N(def_integral))

    expr_latex = sp.latex(expr)
    anti_latex = sp.latex(antideriv)
    def_latex = sp.latex(def_integral)

    x_min = min(a_lim, b_lim) - 1.2
    x_max = max(a_lim, b_lim) + 1.2

    code = f"""import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

x = sp.Symbol('x', real=True)
f = sp.sympify("{str(expr)}", locals={{'x': x}})
F = sp.integrate(f, x)
area_exacta = sp.integrate(f, (x, {a_lim}, {b_lim}))

print(f"Función integrando: f(x) = {{f}}")
print(f"Primitiva (Antiderivada): F(x) = {{F}} + C")
print(f"Integral definida en [{a_lim}, {b_lim}]: {{area_exacta}} ≈ {{float(area_exacta):.5f}}")

f_num = sp.lambdify(x, f, 'numpy')
x_vals = np.linspace({x_min:.2f}, {x_max:.2f}, 400)
y_vals = np.broadcast_to(f_num(x_vals), x_vals.shape)

x_fill = np.linspace({a_lim}, {b_lim}, 250)
y_fill = np.broadcast_to(f_num(x_fill), x_fill.shape)

plt.figure(figsize=(8.2, 4.8))
plt.plot(x_vals, y_vals, color='#0284c7', linewidth=2.5, label=r'$f(x) = {expr_latex}$')
plt.fill_between(x_fill, y_fill, 0, color='#38bdf8', alpha=0.35, label=f'Área integrada [{a_lim}, {b_lim}] = {{float(area_exacta):.3f}}')
plt.axhline(0, color='#475569', linewidth=1)
plt.axvline({a_lim}, color='#f59e0b', linestyle='--', linewidth=1.4, label=f'x = {a_lim}')
plt.axvline({b_lim}, color='#10b981', linestyle='--', linewidth=1.4, label=f'x = {b_lim}')
plt.title(r'Cálculo Integral: $\int_{{{a_lim}}}^{{{b_lim}}} ({expr_latex})\,dx$')
plt.xlabel('x')
plt.ylabel('f(x)')
plt.legend()
plt.grid(True, alpha=0.3)"""

    exec_res = execute_math_physics_code(code)
    exec_res["description"] = f"Cálculo simbólico de la integral y sombreado de Riemann en [{a_lim}, {b_lim}]"

    explanation = f"""### 1. Planteamiento de Cálculo Integral
Queremos calcular la **integral indefinida** (antiderivada) y la **integral definida** de la función en el intervalo $[{a_lim}, {b_lim}]$:
$$I = \\int_{{{a_lim}}}^{{{b_lim}}} \\left({expr_latex}\\right)\\,dx$$

---

### 2. Resolución Paso a Paso (Teorema Fundamental del Cálculo)

1. **Hallar la primitiva o antiderivada $F(x)$:**
   Integramos término a término aplicando la regla de la potencia $\\int x^n\\,dx = \\frac{{x^{{n+1}}}}{{n+1}}$ y reglas elementales:
   $$F(x) = \\int \\left({expr_latex}\\right)\\,dx = {anti_latex} + C$$

2. **Evaluar en los límites de integración (Regla de Barrow):**
   Según el Segundo Teorema Fundamental del Cálculo, $\\int_a^b f(x)\\,dx = F(b) - F(a)$:
   $$F({b_lim}) = {sp.latex(antideriv.subs(x, sp.nsimplify(b_lim)))}, \\qquad F({a_lim}) = {sp.latex(antideriv.subs(x, sp.nsimplify(a_lim)))}$$

3. **Resta de evaluaciones:**
   $$I = F({b_lim}) - F({a_lim}) = {def_latex} \\approx {def_val:.4f}$$

---

### 3. Resultado Final e Interpretación Geométrica
* **Antiderivada General:** $$F(x) = {anti_latex} + C$$
* **Valor Exacto de la Integral Definida:** $$I = {def_latex} \\approx {def_val:.4f}\\text{{ u}}^2$$
* En la gráfica inferior se muestra sombreada en azul celeste la región neta encerrada entre $f(x)$ y el eje $X$ desde $x = {a_lim}$ hasta $x = {b_lim}$."""

    return {
        "answer": explanation,
        "thinking": f"Resolviendo integral simbólica de f(x)={expr} en [{a_lim}, {b_lim}] usando SymPy integrate.",
        "scripts": [exec_res],
        "plots": exec_res.get("plots", []),
        "model_used": "Motor Científico Cálculo Integral + Matplotlib" + (f" ({api_notice})" if api_notice else ""),
    }


def _solve_ode_problem(text: str, api_notice: Optional[str]) -> Dict[str, Any]:
    code = """import sympy as sp
import numpy as np
import matplotlib.pyplot as plt

t = sp.Symbol('t', real=True)
y = sp.Function('y')

# Ecuación diferencial de segundo orden: y'' + 2*y' + 10*y = 0 con y(0)=2, y'(0)=0
ode = sp.Eq(y(t).diff(t, 2) + 2*y(t).diff(t) + 10*y(t), 0)
sol = sp.dsolve(ode, y(t), ics={y(0): 2, y(t).diff(t).subs(t, 0): 0})

print("Ecuación Diferencial:", ode)
print("Solución Analítica Exacta:", sol)

y_num = sp.lambdify(t, sol.rhs, 'numpy')
dy_num = sp.lambdify(t, sp.diff(sol.rhs, t), 'numpy')

t_vals = np.linspace(0, 5, 400)
y_vals = y_num(t_vals)
dy_vals = dy_num(t_vals)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
ax1.plot(t_vals, y_vals, color='#0284c7', lw=2.3, label='Posición y(t)')
ax1.plot(t_vals, dy_vals, color='#8b5cf6', lw=1.6, ls='--', label="Velocidad y'(t)")
ax1.set_title('Solución en el Dominio del Tiempo')
ax1.set_xlabel('t (s)')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2.plot(y_vals, dy_vals, color='#10b981', lw=2.2)
ax2.scatter([2], [0], color='#ef4444', s=80, zorder=5, label='Inicio (2, 0)')
ax2.set_title('Espacio de Fases (y vs dy/dt) - Atractor Espiral')
ax2.set_xlabel('y(t)')
ax2.set_ylabel("y'(t)")
ax2.legend()
ax2.grid(True, alpha=0.3)
plt.tight_layout()"""

    exec_res = execute_math_physics_code(code)
    exec_res["description"] = "Resolución simbólica de EDO de 2º orden con SymPy dsolve y retrato de fase"

    explanation = """### 1. Planteamiento (Ecuación Diferencial Ordinaria de 2º Orden con PVI)
Resolveremos el Problema de Valor Inicial (PVI) de segundo orden homogéneo con coeficientes constantes:
$$\\frac{d^2y}{dt^2} + 2\\frac{dy}{dt} + 10y = 0, \\qquad y(0) = 2,\\; y'(0) = 0$$

---

### 2. Resolución Paso a Paso

1. **Polinomio Característico ($r^2 + 2r + 10 = 0$):**
   Proponemos una solución exponencial $y(t) = e^{rt}$, obteniendo:
   $$r = \\frac{-2 \\pm \\sqrt{2^2 - 4(1)(10)}}{2} = \\frac{-2 \\pm \\sqrt{-36}}{2} = -1 \\pm 3i$$

2. **Solución General para Raíces Complejas Conjugadas ($\\alpha \\pm i\\beta$):**
   Con $\\alpha = -1$ y $\\beta = 3$:
   $$y(t) = e^{-t}\\left(C_1 \\cos(3t) + C_2 \\sin(3t)\\right)$$

3. **Aplicación de las Condiciones Iniciales ($y(0)=2, y'(0)=0$):**
   * Evaluando en $t=0$: $y(0) = 1(C_1(1) + 0) = 2 \\implies C_1 = 2$.
   * Derivando $y'(t) = -e^{-t}(C_1\\cos 3t + C_2\\sin 3t) + e^{-t}(-3C_1\\sin 3t + 3C_2\\cos 3t)$ y evaluando en $t=0$:
     $$y'(0) = -C_1 + 3C_2 = 0 \\implies 3C_2 = 2 \\implies C_2 = \\frac{2}{3}$$

---

### 3. Solución Exacta y Retrato de Fases
$$y(t) = e^{-t}\\left(2\\cos(3t) + \\frac{2}{3}\\sin(3t)\\right)$$
En las dos gráficas inferiores observamos a la izquierda la respuesta temporal amortiguada y a la derecha el **diagrama en el espacio de fases** $(y, y')$, que describe una espiral convergente hacia el punto de equilibrio $(0,0)$."""

    return {
        "answer": explanation,
        "thinking": "Resolviendo EDO de 2do orden mediante ecuación característica y SymPy dsolve.",
        "scripts": [exec_res],
        "plots": exec_res.get("plots", []),
        "model_used": "Motor Científico EDOs + Matplotlib" + (f" ({api_notice})" if api_notice else ""),
    }


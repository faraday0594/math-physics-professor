import base64
import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

from sandbox import execute_math_physics_code
from local_professor import solve_locally_as_professor
from classroom import generate_classroom_lesson
from academy import get_curriculum, generate_day_lesson, generate_minimax_concept_image

load_dotenv()

app = FastAPI(title="MiniMax Math & Physics AI Professor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """Eres el "Profesor MiniMax", un profesor universitario y de secundaria experto en Matemáticas y Física, apasionado por enseñar con claridad absoluta, rigor científico y pedagogía visual.

REGLAS PEDAGÓGICAS Y DE EJECUCIÓN:
1. SIEMPRE utiliza la herramienta `run_python_solver` para:
   - Resolver ecuaciones simbólicas o numéricas con `sympy`, `numpy` o `scipy` (nunca calcules a ojo si puedes verificar con código).
   - Generar al menos una gráfica ilustrativa con `matplotlib.pyplot` (`plt`) cuando el problema involucre funciones, ecuaciones (ej. intersección de rectas/curvas), geometría, vectores, cinemática, dinámica, ondas, circuitos o electromagnetismo.
   - En tus gráficas de Matplotlib: agrega título descriptivo, etiquetas en ejes (`xlabel`, `ylabel`), cuadrícula (`plt.grid(True)`), leyenda (`plt.legend()`) y marca con un punto destacado (`plt.scatter` o `plt.annotate`) la solución o punto clave del problema.
2. ESTRUCTURA DE TU EXPLICACIÓN:
   - **Planteamiento del Problema**: Identifica qué nos piden, cuáles son los datos o la expresión matemática/física y qué concepto o fórmula aplica.
   - **Resolución Paso a Paso**: Explica cada transformación algebraica o principio físico como un profesor paciente en el pizarrón, justificando el porqué de cada paso.
   - **Resultado Final**: Destaca el resultado exacto (y su aproximación decimal con unidades si aplica).
   - **Interpretación Gráfica / Física**: Explica brevemente qué se observa en la gráfica generada o qué significa físicamente el resultado.
3. FORMATO MATEMÁTICO (LaTeX):
   - Usa `$...$` para fórmulas en línea (ej. $2x - 1 = 5$) y `$$...$$` en su propia línea para ecuaciones principales o bloques de desarrollo.
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_python_solver",
            "description": (
                "Ejecuta un script de Python con SymPy, NumPy, SciPy y Matplotlib para resolver "
                "problemas matemáticos/físicos con precisión exacta y generar gráficas educativas. "
                "Usa print() para mostrar resultados intermedios/finales y crea figuras con plt (no necesitas plt.savefig, se capturan automáticamente)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Código Python completo a ejecutar (sympy as sp, numpy as np, matplotlib.pyplot as plt ya están disponibles o pueden importarse).",
                    },
                    "explanation_of_script": {
                        "type": "string",
                        "description": "Breve descripción de una línea de lo que calcula y grafica este script.",
                    },
                },
                "required": ["code"],
            },
        },
    }
]


def get_config(custom_api_key: Optional[str] = None, custom_model: Optional[str] = None, custom_base_url: Optional[str] = None):
    api_key = (custom_api_key or os.getenv("MINIMAX_API_KEY", "")).strip()
    base_url = (custom_base_url or os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")).strip()
    model = (custom_model or os.getenv("MINIMAX_MODEL", "MiniMax-M3.1-Flash")).strip()
    asr_model = os.getenv("MINIMAX_ASR_MODEL", "asr-1.0").strip()
    return api_key, base_url, model, asr_model


async def transcribe_audio_minimax(audio_bytes: bytes, filename: str, content_type: str, api_key: str, base_url: str, asr_model: str) -> str:
    """
    Calls MiniMax's /v1/speech_to_text endpoint with model `asr-1.0` to transcribe audio.
    """
    url = f"{base_url.rstrip('/')}/speech_to_text"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (filename or "audio.webm", audio_bytes, content_type or "audio/webm")}
    data = {"model": asr_model, "response_format": "json"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, data=data, files=files)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Error en transcripción de audio MiniMax ({resp.status_code}): {resp.text}",
            )
        payload = resp.json()
        # Extract text from standard ASR response formats
        if isinstance(payload, dict):
            if "text" in payload and payload["text"]:
                return payload["text"]
            if "data" in payload and isinstance(payload["data"], dict) and "text" in payload["data"]:
                return payload["data"]["text"]
        return str(payload)


def extract_thinking_and_clean(content: str, reasoning_content: Optional[str] = None) -> tuple[str, str]:
    """
    Separates <think>...</think> blocks or reasoning_content from the final markdown response.
    """
    thinking_parts = []
    if reasoning_content:
        thinking_parts.append(reasoning_content.strip())

    if content:
        think_matches = re.findall(r"<think>(.*?)</think>", content, flags=re.DOTALL)
        for m in think_matches:
            if m.strip():
                thinking_parts.append(m.strip())
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    return "\n\n".join(thinking_parts), content


def extract_python_blocks_fallback(text: str) -> List[str]:
    """
    If the model wrote ```python ... ``` blocks directly instead of invoking tool calls,
    we can optionally execute them if they import matplotlib/sympy and no tool was called.
    """
    pattern = r"```python\s*(.*?)```"
    return [m.strip() for m in re.findall(pattern, text, flags=re.DOTALL) if m.strip()]


@app.post("/api/solve")
async def solve_problem(
    prompt: str = Form(""),
    history: str = Form("[]"),
    model: str = Form(""),
    reasoning_effort: str = Form("medium"),
    api_key: str = Form(""),
    base_url: str = Form(""),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):
    resolved_key, resolved_base_url, resolved_model, asr_model = get_config(api_key, model, base_url)

    transcribed_text = ""
    if audio is not None and resolved_key:
        audio_bytes = await audio.read()
        if len(audio_bytes) > 0:
            try:
                transcribed_text = await transcribe_audio_minimax(
                    audio_bytes=audio_bytes,
                    filename=audio.filename or "recording.webm",
                    content_type=audio.content_type or "audio/webm",
                    api_key=resolved_key,
                    base_url=resolved_base_url,
                    asr_model=asr_model,
                )
            except Exception as asr_err:
                transcribed_text = f"(Aviso ASR MiniMax sin saldo: {asr_err})"

    combined_user_text = prompt.strip()
    if transcribed_text:
        if combined_user_text:
            combined_user_text = f"{combined_user_text}\n\n[Transcripción de audio del estudiante]: {transcribed_text}"
        else:
            combined_user_text = transcribed_text

    if not combined_user_text and image is None:
        raise HTTPException(status_code=400, detail="Por favor envía un problema en texto, una imagen o un audio.")

    if not resolved_key:
        local_solution = solve_locally_as_professor(
            user_prompt=combined_user_text or "2*x - 1 = 0",
            api_notice="Modo Científico Local Activo (SymPy + Matplotlib)",
        )
        local_solution["transcribed_audio"] = transcribed_text
        return JSONResponse(local_solution)

    # Parse conversation history
    try:
        parsed_history = json.loads(history) if history else []
    except Exception:
        parsed_history = []

    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in parsed_history[-8:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Build multimodal user message
    if image is not None:
        img_bytes = await image.read()
        mime_type = image.content_type or "image/png"
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        user_content: Any = [
            {
                "type": "text",
                "text": combined_user_text
                or "Analiza esta imagen con el problema de matemáticas o física, resuélvelo paso a paso como un profesor profesional y genera la gráfica correspondiente.",
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64_img}"},
            },
        ]
    else:
        user_content = combined_user_text

    messages.append({"role": "user", "content": user_content})

    client = OpenAI(api_key=resolved_key, base_url=resolved_base_url, timeout=90.0)

    executed_scripts: List[Dict[str, Any]] = []
    all_plots: List[str] = []
    all_thinking: List[str] = []

    extra_body: Dict[str, Any] = {}
    if reasoning_effort and "M3" in resolved_model:
        extra_body["reasoning_effort"] = reasoning_effort

    try:
        # Agentic loop (up to 4 tool rounds)
        final_answer = ""
        for round_idx in range(4):
            # En la última ronda forzar a que no llame más herramientas y entregue la respuesta final en texto
            current_tools = TOOLS_SCHEMA if round_idx < 3 else None
            current_tool_choice = "auto" if round_idx < 3 else None

            response = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                tools=current_tools,
                tool_choice=current_tool_choice,
                extra_body=extra_body if extra_body else None,
            )

            msg = response.choices[0].message
            raw_reasoning = getattr(msg, "reasoning_content", None)
            think_text, cleaned_content = extract_thinking_and_clean(msg.content or "", raw_reasoning)
            if think_text:
                all_thinking.append(think_text)

            if msg.tool_calls and round_idx < 3:
                # Append assistant tool call message
                assistant_dict: Dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
                messages.append(assistant_dict)

                for tc in msg.tool_calls:
                    if tc.function.name == "run_python_solver":
                        try:
                            args = json.loads(tc.function.arguments)
                        except Exception:
                            args = {"code": tc.function.arguments}

                        code_to_run = args.get("code", "")
                        script_desc = args.get("explanation_of_script", "Cálculo y graficación científica")
                        exec_res = execute_math_physics_code(code_to_run)
                        exec_res["description"] = script_desc
                        executed_scripts.append(exec_res)
                        all_plots.extend(exec_res.get("plots", []))

                        tool_output = {
                            "success": exec_res["success"],
                            "stdout": exec_res["stdout"],
                            "stderr": exec_res["stderr"],
                            "error": exec_res["error"],
                            "plots_generated": len(exec_res.get("plots", [])),
                            "instruction": "Si tu código falló o generó gráficas, ahora redacta tu explicación completa como profesor paso a paso.",
                        }
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "name": tc.function.name,
                                "content": json.dumps(tool_output, ensure_ascii=False),
                            }
                        )
            else:
                final_answer = cleaned_content
                break

        # Si el modelo agotó sus llamadas de herramientas pero no redactó el texto final, hacer una última llamada para que lo redacte
        if not final_answer.strip() and executed_scripts:
            messages.append({
                "role": "user",
                "content": "Con base en los resultados y gráficas que acabas de generar en Python, redacta ahora tu explicación completa como profesor paso a paso, con planteamiento, desarrollo en LaTeX, resultado final e interpretación geométrica."
            })
            resp_text = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                extra_body=extra_body if extra_body else None,
            )
            msg_t = resp_text.choices[0].message
            _, final_answer = extract_thinking_and_clean(msg_t.content or "", getattr(msg_t, "reasoning_content", None))

        # Fallback: if the model didn't invoke the tool via tool_calls but included a python block with plt/sympy
        if not executed_scripts and final_answer:
            py_blocks = extract_python_blocks_fallback(final_answer)
            for block in py_blocks:
                if any(k in block for k in ("plt.", "sympy", "sp.", "np.", "numpy", "scipy")):
                    exec_res = execute_math_physics_code(block)
                    exec_res["description"] = "Script extraído de la explicación"
                    executed_scripts.append(exec_res)
                    all_plots.extend(exec_res.get("plots", []))

        return JSONResponse(
            {
                "answer": final_answer,
                "thinking": "\n\n---\n\n".join(all_thinking),
                "transcribed_audio": transcribed_text,
                "scripts": executed_scripts,
                "plots": all_plots,
                "model_used": resolved_model,
            }
        )

    except Exception as exc:
        err_str = str(exc)
        # Automatic Fallback to the Local Scientific Professor Engine (SymPy + NumPy + Matplotlib)
        # so the student always gets a complete step-by-step explanation and graph immediately!
        api_notice = "Modo Local Activo — MiniMax API sin saldo (402)" if ("402" in err_str or "1008" in err_str) else "Modo Local Activo"
        local_solution = solve_locally_as_professor(
            user_prompt=combined_user_text or "2*x - 1 = 0",
            api_notice=api_notice,
        )
        local_solution["transcribed_audio"] = transcribed_text
        local_solution["api_warning"] = (
            "Tu API Key de MiniMax reportó saldo insuficiente (HTTP 402 - código 1008), "
            "por lo que el Motor Científico Local (SymPy + Matplotlib) resolvió y graficó tu problema automáticamente."
            if ("402" in err_str or "1008" in err_str)
            else f"Aviso API MiniMax: {err_str}"
        )
        return JSONResponse(local_solution)


@app.post("/api/classroom")
async def create_classroom_slides(payload: Dict[str, Any]):
    """
    Generates an interactive multi-slide classroom presentation explaining the intuition,
    step-by-step reasoning, and per-slide Matplotlib visualizations for a given problem.
    """
    problem_prompt = payload.get("prompt", "")
    previous_answer = payload.get("answer", "")
    custom_key = payload.get("api_key", "")
    custom_model = payload.get("model", "")
    custom_base_url = payload.get("base_url", "")

    resolved_key, resolved_base_url, resolved_model, _ = get_config(custom_key, custom_model, custom_base_url)
    deck = generate_classroom_lesson(
        problem_prompt=problem_prompt,
        previous_answer=previous_answer,
        api_key=resolved_key,
        base_url=resolved_base_url,
        model=resolved_model,
    )
    return JSONResponse(deck)


@app.get("/api/academy/curriculum")
async def academy_curriculum():
    """
    Returns the complete 30-day progressive engineering & math curriculum calendar.
    """
    return JSONResponse(get_curriculum())


@app.post("/api/academy/lesson")
async def academy_day_lesson(payload: Dict[str, Any]):
    """
    Generates a full day's masterclass lesson (detailed explanation with tips,
    rigorous mathematical proof, worked examples, Matplotlib plot, MiniMax image-01
    illustration, graduated exercises, and mini-quiz).
    """
    day_number = int(payload.get("day", 1))
    custom_key = payload.get("api_key", "")
    custom_model = payload.get("model", "")
    custom_base_url = payload.get("base_url", "")
    generate_ai_image = bool(payload.get("generate_ai_image", True))

    resolved_key, resolved_base_url, resolved_model, _ = get_config(custom_key, custom_model, custom_base_url)
    lesson = await generate_day_lesson(
        day_number=day_number,
        api_key=resolved_key,
        base_url=resolved_base_url,
        model=resolved_model,
        generate_ai_image=generate_ai_image,
    )
    return JSONResponse(lesson)


@app.post("/api/academy/generate-image")
async def academy_generate_image(payload: Dict[str, Any]):
    """
    Generates or regenerates an educational illustration using MiniMax image-01.
    """
    prompt = payload.get("prompt", "Educational 3D illustration of mathematics and engineering")
    day_number = int(payload.get("day", 1))
    custom_key = payload.get("api_key", "")
    custom_base_url = payload.get("base_url", "")
    resolved_key, resolved_base_url, _, _ = get_config(custom_key, None, custom_base_url)
    img_res = await generate_minimax_concept_image(
        prompt=prompt,
        api_key=resolved_key,
        base_url=resolved_base_url,
        day_number=day_number,
    )
    return JSONResponse(img_res)


@app.post("/api/run-sandbox")
async def run_sandbox_direct(payload: Dict[str, str]):
    """
    Allows running or testing Python math/physics scripts directly in the Sandbox
    (also powers the interactive local demo mode when testing without API balance).
    """
    code = payload.get("code", "")
    if not code.strip():
        raise HTTPException(status_code=400, detail="El código está vacío.")
    res = execute_math_physics_code(code)
    return JSONResponse(res)


@app.get("/api/config-status")
async def config_status():
    api_key, base_url, model, asr_model = get_config()
    masked = f"{api_key[:10]}...{api_key[-6:]}" if len(api_key) > 16 else ("Configurada" if api_key else "No configurada")
    return {
        "has_key": bool(api_key),
        "masked_key": masked,
        "base_url": base_url,
        "model": model,
        "asr_model": asr_model,
    }


@app.post("/api/save-config")
async def save_config(payload: Dict[str, str]):
    """
    Saves the API key and Base URL persistently into the .env file.
    """
    api_key = payload.get("api_key", "").strip()
    base_url = payload.get("base_url", "").strip() or "https://api.minimax.io/v1"

    if not api_key:
        raise HTTPException(status_code=400, detail="La API Key no puede estar vacía.")

    os.environ["MINIMAX_API_KEY"] = api_key
    os.environ["MINIMAX_BASE_URL"] = base_url

    # Persist to .env if filesystem is writable (local or ephemeral container)
    try:
        env_lines = []
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        updated = False
        new_lines = []
        has_base = False
        for line in env_lines:
            if line.startswith("MINIMAX_API_KEY="):
                new_lines.append(f"MINIMAX_API_KEY={api_key}\n")
                updated = True
            elif line.startswith("MINIMAX_BASE_URL="):
                new_lines.append(f"MINIMAX_BASE_URL={base_url}\n")
                has_base = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"MINIMAX_API_KEY={api_key}\n")
        if not has_base:
            new_lines.append(f"MINIMAX_BASE_URL={base_url}\n")

        with open(".env", "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except OSError:
        pass

    masked = f"{api_key[:10]}...{api_key[-6:]}" if len(api_key) > 16 else "Configurada"
    return {"success": True, "masked_key": masked, "base_url": base_url}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse(
        "static/index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)


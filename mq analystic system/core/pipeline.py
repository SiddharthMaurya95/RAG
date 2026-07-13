import pandas as pd

# =========================
# AGENTS
# =========================
from core.agents.code_agent import generate_code
from core.agents.debug_agent import fix_code
from core.agents.insight_agent import generate_insights
from core.agents.summary_agent import summarize
from core.agents.visualization_agent import VisualizationAgent

# =========================
# ENGINE
# =========================
from core.engine.validator import ensure_result_assignment
from core.engine.executor import CodeExecutor

# =========================
# INTENT ENGINE
# =========================
from core.engine.intent.intent_classifier import Intent_classification

# =========================
# MEMORY
# =========================
from core.memory.chat_memory import ChatMemory

# =========================
# INIT
# =========================
memory = ChatMemory()
executor = CodeExecutor()
intent_engine = Intent_classification()
visualizer = VisualizationAgent()


# =========================
# SAFE EXECUTION (FIXED)
# =========================
def safe_execute(code, df):

    for attempt in range(2):
        try:
            exec_result = executor.execute(code, df)

            if exec_result["success"]:
                return exec_result["result"], {}, [], None
            else:
                error = exec_result["error"]

        except Exception as e:
            error = str(e)

        print(f"\n❌ Execution Error (attempt {attempt+1}):\n{error}")
        print("⚠️ Retrying with fixed code...")

        try:
            code = fix_code(code, error)
            code = ensure_result_assignment(code)
        except Exception as fix_err:
            return None, None, [], str(fix_err)

    return None, None, [], error


# =========================
# RESULT SELECTION
# =========================
def select_best_data(result, env):

    if isinstance(result, (pd.DataFrame, pd.Series)):
        return result

    candidates = [
        v for v in env.values()
        if isinstance(v, (pd.DataFrame, pd.Series))
    ]

    if candidates:
        return max(candidates, key=lambda x: len(x))

    return result


# =========================
# MAIN PIPELINE (FULLY FIXED ✅)
# =========================
def run_pipeline(query, df):

    print("\n🔹 Starting Pipeline...\n")

    base_instructions = "Analyze dataset and extract insights"

    # ✅ INTENT EXTRACTION
    intents, kpis, filters, aggregations = intent_engine.build_intent_prompt(
        base_instructions=base_instructions,
        question=query
    )

    print("✅ INTENTS:", intents)
    print("✅ KPIS:", kpis)
    print("✅ FILTERS:", filters)
    print("✅ AGG:", aggregations)

    # =========================
    # ✅ CODE GENERATION
    # =========================
    code_raw = generate_code(query, df.columns)
    code = ensure_result_assignment(code_raw)

    print("\n✅ Generated Code:\n", code)

    # =========================
    # ✅ EXECUTION
    # =========================
    result, env, images, error = safe_execute(code, df)

    if error:
        return {"error": error}

    # =========================
    # ✅ RESULT SELECTION
    # =========================
    best_data = select_best_data(result, env)

    # =========================
    # ✅ VISUALIZATION
    # =========================
    viz_output = None
    try:
        viz_output = visualizer.visualize(
            best_data,
            intents=intents,
            kpis=kpis
        )
    except Exception as e:
        print("⚠️ Visualization failed:", e)

    # =========================
    # ✅ INSIGHTS
    # =========================
    insights = generate_insights(query, best_data)

    # =========================
    # ✅ SUMMARY
    # =========================
    summary = summarize(insights)

    # =========================
    # ✅ FINAL OUTPUT
    # =========================
    output = {
        "mode": "PYTHON",
        "code": code,
        "result": result,
        "images": images,
        "visualization": viz_output,
        "insights": insights,
        "summary": summary,
        "intent": intents,
        "kpis": kpis,
        "filters": filters,
        "aggregations": aggregations
    }

    memory.add(query, str(result))

    print("\n✅ Pipeline completed successfully\n")

    return output
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64


import matplotlib.pyplot as plt
import pandas as pd
import traceback


class CodeExecutor:

    def __init__(self):
        pass

    def execute(self, code: str, df: pd.DataFrame):
        """
        Executes generated Python code safely.
        Returns:
            result → Data
            has_plot → True/False
        """

        local_vars = {"df": df, "plt": plt, "pd": pd}

        try:
            # ✅ clean code block (remove ```python)
            cleaned_code = self._extract_code(code)

            exec(cleaned_code, {}, local_vars)

            result = local_vars.get("result", None)

            # ✅ Detect plot
            has_plot = self._detect_plot(cleaned_code)

            return {
                "success": True,
                "result": result,
                "has_plot": has_plot
            }

        except Exception as e:
            return {
                "success": False,
                "error": traceback.format_exc(),
                "has_plot": False,
                "result": None
            }

    # -----------------------------------------------------
    def _extract_code(self, code: str):
        if "```" in code:
            return code.split("```python")[-1].split("```")[0]
        return code

    # -----------------------------------------------------
    def _detect_plot(self, code: str):
        plot_keywords = ["plt.show", ".plot(", "plt.bar", "plt.plot"]
        return any(k in code for k in plot_keywords)







# # ===================================
# # ✅ ENSURE RESULT ASSIGNMENT
# # ===================================
# def ensure_result_assignment(code: str) -> str:
#     lines = [line.strip() for line in code.strip().split("\n") if line.strip()]

#     # ✅ If already assigned correctly → keep as is
#     if any(line.startswith("result =") for line in lines):
#         return code

#     # ✅ Find meaningful computation line (reverse search)
#     for i in range(len(lines) - 1, -1, -1):
#         line = lines[i]

#         # ✅ Skip non-computation lines
#         if (
#             line.startswith("plt.") or
#             line.startswith("print") or
#             line.startswith("import") or
#             line.startswith("from") or
#             "show()" in line
#         ):
#             continue

#         # ✅ Assign result to meaningful line
#         if "=" not in line:
#             lines[i] = f"result = {line}"
#             break

#     return "\n".join(lines)


# import re

# def extract_valid_python(code: str) -> str:
#     """
#     Removes non-code text from LLM output
#     """

#     # ✅ Extract code block if present
#     matches = re.findall(r"```(?:python)?\s*(.*?)```", code, re.S)

#     if matches:
#         code = "\n".join(matches)

#     # ✅ Remove lines that are clearly not Python
#     cleaned_lines = []
#     for line in code.split("\n"):
#         line_strip = line.strip()

#         # ❌ Remove conversational text
#         if line_strip.startswith(("Here", "Sure", "This", "You", "The")):
#             continue

#         cleaned_lines.append(line)

#     return "\n".join(cleaned_lines).strip()




# # ===================================
# # ✅ FINAL EXECUTION ENGINE
# # ===================================
# # def execute(code, df):

# #     print("\n🔹 Raw Generated Code:\n", code)

# #     # ✅ STEP 1: CLEAN INVALID TEXT
# #     code = extract_valid_python(code)

# #     # ✅ STEP 2: ENSURE RESULT
# #     code = ensure_result_assignment(code)

# #     print("\n✅ Cleaned Code:\n", code)

# #     exec_env = {
# #         "df": df.copy(),
# #         "pd": pd,
# #         "np": np,
# #         "plt": plt,
# #         "result": None
# #     }

# #     try:
# #         exec(code, exec_env)
# #     except Exception as e:
# #         import traceback
# #         error_msg = traceback.format_exc()
# #         print("\n❌ Execution Error:\n", error_msg)
# #         return None, None, [], error_msg

# #     result = exec_env.get("result")

# #     # ✅ fallback result
# #     if result is None:
# #         for val in exec_env.values():
# #             if isinstance(val, (pd.DataFrame, pd.Series)):
# #                 result = val
# #                 break

# #     if result is None:
# #         result = "No result available"

# #     # ✅ capture plots
# #     images = []
# #     for fig_num in plt.get_fignums():
# #         fig = plt.figure(fig_num)
# #         buf = io.BytesIO()
# #         fig.savefig(buf, format="png")
# #         buf.seek(0)
# #         images.append(base64.b64encode(buf.getvalue()).decode())
# #         plt.close(fig)

# #     return result, exec_env, images, None


# ### below update to wrap the plot
# def execute(code, df):

#     print("\n🔹 Raw Generated Code:\n", code)

#     # ✅ STEP 1: CLEAN INVALID TEXT
#     code = extract_valid_python(code)

#     # ✅ STEP 2: ENSURE RESULT
#     code = ensure_result_assignment(code)

#     print("\n✅ Cleaned Code:\n", code)

#     # =========================
#     # ✅ ✅ SAFE PLOT PATCH (NEW)
#     # =========================
#     SAFE_PLOT_PATCH = """
# import matplotlib.pyplot as plt
# import textwrap

# # ✅ Global figure size
# plt.rcParams["figure.figsize"] = (14, 6)

# # ✅ Wrap X-axis labels automatically
# _original_xticks = plt.xticks
# def safe_xticks(*args, **kwargs):
#     labels = kwargs.get('labels', None)
#     if labels:
#         labels = [textwrap.fill(str(l), 12) for l in labels]
#         kwargs['labels'] = labels
#     kwargs.setdefault('rotation', 0)
#     return _original_xticks(*args, **kwargs)

# plt.xticks = safe_xticks

# # ✅ Ensure layout always fits
# _original_show = plt.show
# def safe_show(*args, **kwargs):
#     plt.tight_layout()
#     return _original_show(*args, **kwargs)

# plt.show = safe_show
# """

#     # ✅ Combine patch + generated code
#     final_code = SAFE_PLOT_PATCH + "\n" + code

#     exec_env = {
#         "df": df.copy(),
#         "pd": pd,
#         "np": np,
#         "plt": plt,
#         "result": None
#     }

#     try:
#         exec(final_code, exec_env)
#     except Exception as e:
#         import traceback
#         error_msg = traceback.format_exc()
#         print("\n❌ Execution Error:\n", error_msg)
#         return None, None, [], error_msg

#     result = exec_env.get("result")

#     # ✅ fallback result
#     if result is None:
#         for val in exec_env.values():
#             if isinstance(val, (pd.DataFrame, pd.Series)):
#                 result = val
#                 break

#     if result is None:
#         result = "No result available"

#     # =========================
#     # ✅ ✅ CAPTURE FIX (IMPROVED)
#     # =========================
#     images = []
#     for fig_num in plt.get_fignums():
#         fig = plt.figure(fig_num)

#         # ✅ Force layout fix before saving
#         fig.tight_layout()

#         buf = io.BytesIO()
#         fig.savefig(buf, format="png", bbox_inches="tight")  # ✅ no cutoff
#         buf.seek(0)

#         images.append(base64.b64encode(buf.getvalue()).decode())
#         plt.close(fig)

#     return result, exec_env, images, None
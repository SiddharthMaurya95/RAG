import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


class VisualizationAgent:

    def __init__(self):
        sns.set(style="whitegrid")

    def visualize(self, result, intents=None, kpis=None):

        try:
            intents = intents or []
            kpis = kpis or []

            # =====================================================
            # ✅ 1. INTENT-DRIVEN VISUALIZATION (PRIMARY LOGIC)
            # =====================================================

            # ✅ TREND → Line chart
            if "trend" in intents:
                self._plot_line(result, title="Trend Analysis")
                return "✅ Line chart (trend)"

            # ✅ RANKING → Bar chart
            if "ranking" in intents:
                self._plot_bar(result, title="Top / Bottom Analysis")
                return "✅ Bar chart (ranking)"

            # ✅ DISTRIBUTION → Histogram
            if "distribution" in intents:
                self._plot_hist(result, title="Distribution Analysis")
                return "✅ Histogram"

            # ✅ COMPARISON → Grouped bar
            if "comparison" in intents:
                self._plot_comparison(result)
                return "✅ Comparison chart"

            # ✅ ANOMALY → Boxplot
            if "anomaly" in intents:
                self._plot_box(result)
                return "✅ Boxplot"

            # =====================================================
            # ✅ 2. FALLBACK (DATA-DRIVEN)
            # =====================================================
            return self._auto_visualize(result)

        except Exception as e:
            return f"❌ Visualization error: {str(e)}"

    # =====================================================
    # ✅ INTENT-BASED FUNCTIONS
    # =====================================================

    def _plot_line(self, result, title="Line Chart"):
        result.plot(kind="line", figsize=(10, 5))
        plt.title(title)
        plt.xlabel("Time / Index")
        plt.ylabel("Value")
        plt.grid(True)
        plt.show()

    def _plot_bar(self, result, title="Bar Chart"):
        result.plot(kind="bar", figsize=(10, 5))
        plt.title(title)
        plt.xlabel("Category")
        plt.ylabel("Value")
        plt.xticks(rotation=30)
        plt.show()

    def _plot_hist(self, result, title="Histogram"):
        if isinstance(result, pd.Series):
            result.plot(kind="hist", bins=20)

        elif isinstance(result, pd.DataFrame):
            result.select_dtypes(include="number").plot(kind="hist", bins=20)

        plt.title(title)
        plt.xlabel("Values")
        plt.ylabel("Frequency")
        plt.show()

    def _plot_comparison(self, result):
        if isinstance(result, pd.DataFrame) and len(result.columns) >= 2:
            sns.barplot(data=result, x=result.columns[0], y=result.columns[1])
            plt.xticks(rotation=30)
            plt.title("Comparison Analysis")
            plt.show()

    def _plot_box(self, result):
        if isinstance(result, pd.DataFrame):
            sns.boxplot(data=result)
            plt.title("Anomaly Detection (Boxplot)")
            plt.show()

    # =====================================================
    # ✅ FALLBACK AUTO VISUALIZATION
    # =====================================================

    def _auto_visualize(self, result):

        if isinstance(result, pd.Series):
            result.plot(kind="bar")
            plt.title("Auto Bar Chart")
            plt.show()
            return "✅ Auto bar chart"

        elif isinstance(result, pd.DataFrame):

            if len(result.columns) == 1:
                result.plot(kind="hist")
                plt.title("Auto Histogram")
                plt.show()
                return "✅ Auto histogram"

            elif len(result.columns) == 2:
                result.plot(kind="bar")
                plt.title("Auto Comparison")
                plt.show()
                return "✅ Auto bar comparison"

            else:
                sns.heatmap(result.corr(), annot=True)
                plt.title("Auto Correlation Heatmap")
                plt.show()
                return "✅ Auto heatmap"

        return "⚠️ No visualization applied"

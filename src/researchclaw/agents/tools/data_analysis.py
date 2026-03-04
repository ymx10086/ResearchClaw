"""Data analysis and visualisation tool.

Provides functions for statistical analysis, data querying, and chart
generation aimed at academic research workflows.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def data_describe(
    file_path: str,
    columns: Optional[list[str]] = None,
    head_rows: int = 5,
) -> dict[str, Any]:
    """Load and describe a data file (CSV, Excel, JSON, TSV).

    Parameters
    ----------
    file_path:
        Path to the data file.
    columns:
        Optional subset of columns to describe.
    head_rows:
        Number of rows to show in the preview (default 5).

    Returns
    -------
    dict
        Data description including shape, dtypes, statistics, and preview.
    """
    try:
        import pandas as pd

        # Auto-detect file type
        ext = Path(file_path).suffix.lower()
        read_funcs = {
            ".csv": pd.read_csv,
            ".tsv": lambda f: pd.read_csv(f, sep="\t"),
            ".xlsx": pd.read_excel,
            ".xls": pd.read_excel,
            ".json": pd.read_json,
            ".parquet": pd.read_parquet,
        }

        reader = read_funcs.get(ext)
        if reader is None:
            return {"error": f"Unsupported file type: {ext}"}

        df = reader(file_path)

        if columns:
            missing = [c for c in columns if c not in df.columns]
            if missing:
                return {"error": f"Columns not found: {missing}"}
            df = df[columns]

        # Build description
        result: dict[str, Any] = {
            "shape": {"rows": df.shape[0], "columns": df.shape[1]},
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "preview": df.head(head_rows).to_string(),
            "missing_values": df.isnull().sum().to_dict(),
        }

        # Add statistics for numeric columns
        numeric_df = df.select_dtypes(include="number")
        if not numeric_df.empty:
            result["statistics"] = numeric_df.describe().to_dict()

        return result

    except ImportError:
        return {"error": "pandas not installed. Run: pip install pandas"}
    except Exception as e:
        logger.exception("Data describe failed")
        return {"error": f"Failed to describe data: {e}"}


def data_query(
    file_path: str,
    query: str,
    output_format: str = "text",
) -> dict[str, Any]:
    """Query a data file using pandas expressions.

    Parameters
    ----------
    file_path:
        Path to the data file.
    query:
        Pandas query string (e.g. ``"age > 25 and score >= 90"``) or
        a Python expression using ``df`` (e.g. ``"df.groupby('category').mean()"``).
    output_format:
        ``"text"`` (default), ``"csv"``, or ``"json"``.

    Returns
    -------
    dict
        Query result with ``data``, ``shape``, and ``preview``.
    """
    try:
        import pandas as pd

        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        elif ext == ".json":
            df = pd.read_json(file_path)
        elif ext == ".tsv":
            df = pd.read_csv(file_path, sep="\t")
        else:
            return {"error": f"Unsupported file type: {ext}"}

        # Try pandas query first, then eval
        try:
            result_df = df.query(query)
        except Exception:
            # Allow more complex expressions
            local_vars = {"df": df, "pd": pd}
            import numpy as np

            local_vars["np"] = np
            result = eval(
                query,
                {"__builtins__": {}},
                local_vars,
            )  # noqa: S307
            if isinstance(result, pd.DataFrame):
                result_df = result
            elif isinstance(result, pd.Series):
                result_df = result.to_frame()
            else:
                return {"data": str(result), "type": type(result).__name__}

        if output_format == "csv":
            return {
                "data": result_df.to_csv(index=False),
                "shape": list(result_df.shape),
            }
        elif output_format == "json":
            return {
                "data": result_df.to_json(orient="records"),
                "shape": list(result_df.shape),
            }
        else:
            return {
                "data": result_df.to_string(),
                "shape": list(result_df.shape),
                "preview": result_df.head(20).to_string(),
            }

    except ImportError:
        return {"error": "pandas not installed. Run: pip install pandas"}
    except Exception as e:
        logger.exception("Data query failed")
        return {"error": f"Query failed: {e}"}


def plot_chart(
    chart_type: str,
    data: Optional[dict[str, list]] = None,
    file_path: Optional[str] = None,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    figsize: tuple[int, int] = (10, 6),
    style: str = "seaborn-v0_8-whitegrid",
    save_path: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a publication-quality chart.

    Parameters
    ----------
    chart_type:
        Chart type: ``"line"``, ``"scatter"``, ``"bar"``, ``"hist"``,
        ``"box"``, ``"violin"``, ``"heatmap"``, ``"pie"``.
    data:
        Inline data as ``{column_name: [values]}``.
    file_path:
        Path to a data file (CSV/Excel) to load data from.
    x_column:
        Column name for x-axis.
    y_column:
        Column name for y-axis.
    title:
        Chart title.
    xlabel:
        X-axis label.
    ylabel:
        Y-axis label.
    figsize:
        Figure size as ``(width, height)`` in inches.
    style:
        Matplotlib style name.
    save_path:
        Optional path to save the figure. If None, returns base64.
    **kwargs:
        Additional arguments passed to the plot function.

    Returns
    -------
    dict
        Result with ``path`` (if saved) or ``base64_png`` image data.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np

        # Load data
        df = None
        if file_path:
            import pandas as pd

            ext = Path(file_path).suffix.lower()
            if ext == ".csv":
                df = pd.read_csv(file_path)
            elif ext in (".xlsx", ".xls"):
                df = pd.read_excel(file_path)
        elif data:
            import pandas as pd

            df = pd.DataFrame(data)

        if df is None:
            return {
                "error": "No data provided. Specify 'data' or 'file_path'.",
            }

        # Set style
        try:
            plt.style.use(style)
        except Exception:
            plt.style.use("default")

        fig, ax = plt.subplots(figsize=figsize)

        x = df[x_column] if x_column and x_column in df.columns else None
        y = df[y_column] if y_column and y_column in df.columns else None

        # Create chart
        if chart_type == "line":
            if x is not None and y is not None:
                ax.plot(x, y, **kwargs)
            else:
                df.plot(ax=ax, **kwargs)
        elif chart_type == "scatter":
            if x is not None and y is not None:
                ax.scatter(x, y, **kwargs)
            else:
                return {"error": "Scatter plot requires x_column and y_column"}
        elif chart_type == "bar":
            if x is not None and y is not None:
                ax.bar(x, y, **kwargs)
            else:
                df.plot.bar(ax=ax, **kwargs)
        elif chart_type == "hist":
            col = df[y_column] if y_column else df.iloc[:, 0]
            ax.hist(col, **kwargs)
        elif chart_type == "box":
            df.plot.box(ax=ax, **kwargs)
        elif chart_type == "pie":
            if y_column:
                df.set_index(x_column or df.columns[0])[y_column].plot.pie(
                    ax=ax,
                    autopct="%1.1f%%",
                    **kwargs,
                )
        elif chart_type == "heatmap":
            numeric_df = df.select_dtypes(include="number")
            im = ax.imshow(numeric_df.corr(), cmap="coolwarm", aspect="auto")
            ax.set_xticks(range(len(numeric_df.columns)))
            ax.set_yticks(range(len(numeric_df.columns)))
            ax.set_xticklabels(numeric_df.columns, rotation=45, ha="right")
            ax.set_yticklabels(numeric_df.columns)
            fig.colorbar(im)
        else:
            return {"error": f"Unknown chart type: {chart_type}"}

        if title:
            ax.set_title(title, fontsize=14, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        plt.tight_layout()

        # Save or return as base64
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return {"path": save_path, "status": "saved"}
        else:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode("utf-8")
            return {"base64_png": b64, "status": "generated"}

    except ImportError as e:
        return {
            "error": f"Missing dependency: {e}. Run: pip install matplotlib pandas",
        }
    except Exception as e:
        logger.exception("Chart generation failed")
        return {"error": f"Chart generation failed: {e}"}

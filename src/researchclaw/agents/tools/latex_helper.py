"""LaTeX helper tool.

Provides LaTeX template generation, syntax checking, and common
academic writing utilities.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Templates ───────────────────────────────────────────────────────────────

_TEMPLATES: dict[str, str] = {
    "article": r"""\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{cite}
\usepackage{geometry}
\geometry{margin=1in}

\title{%(title)s}
\author{%(author)s}
\date{%(date)s}

\begin{document}

\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

\section{Introduction}
\label{sec:intro}

\section{Related Work}
\label{sec:related}

\section{Method}
\label{sec:method}

\section{Experiments}
\label{sec:experiments}

\section{Results}
\label{sec:results}

\section{Conclusion}
\label{sec:conclusion}

\bibliographystyle{plain}
\bibliography{references}

\end{document}
""",
    "ieee": r"""\documentclass[conference]{IEEEtran}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{cite}

\title{%(title)s}
\author{
    \IEEEauthorblockN{%(author)s}
    \IEEEauthorblockA{%(affiliation)s}
}

\begin{document}

\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

\begin{IEEEkeywords}
%(keywords)s
\end{IEEEkeywords}

\section{Introduction}

\section{Related Work}

\section{Proposed Method}

\section{Experimental Setup}

\section{Results and Discussion}

\section{Conclusion}

\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}
""",
    "acl": r"""\documentclass[11pt,a4paper]{article}
\usepackage[hyperref]{acl2023}
\usepackage{times}
\usepackage{latexsym}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{booktabs}

\title{%(title)s}

\author{%(author)s \\
  %(affiliation)s \\
  \texttt{%(email)s}}

\begin{document}
\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

\section{Introduction}

\section{Related Work}

\section{Method}

\section{Experiments}

\section{Results}

\section{Analysis}

\section{Conclusion}

\bibliography{references}
\bibliographystyle{acl_natbib}

\end{document}
""",
    "neurips": r"""\documentclass{article}
\usepackage[preprint]{neurips_2024}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{hyperref}
\usepackage{url}
\usepackage{booktabs}
\usepackage{amsfonts}
\usepackage{nicefrac}
\usepackage{microtype}

\title{%(title)s}

\author{
  %(author)s \\
  %(affiliation)s \\
  \texttt{%(email)s}
}

\begin{document}

\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

\section{Introduction}

\section{Related Work}

\section{Method}

\section{Experiments}

\section{Results}

\section{Conclusion}

\bibliography{references}
\bibliographystyle{plain}

\end{document}
""",
    "beamer": r"""\documentclass{beamer}
\usetheme{Madrid}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}

\title{%(title)s}
\author{%(author)s}
\institute{%(affiliation)s}
\date{%(date)s}

\begin{document}

\frame{\titlepage}

\begin{frame}{Outline}
    \tableofcontents
\end{frame}

\section{Introduction}
\begin{frame}{Introduction}
    \begin{itemize}
        \item Background
        \item Motivation
        \item Contributions
    \end{itemize}
\end{frame}

\section{Method}
\begin{frame}{Proposed Method}
\end{frame}

\section{Experiments}
\begin{frame}{Experimental Results}
\end{frame}

\section{Conclusion}
\begin{frame}{Conclusion}
    \begin{itemize}
        \item Summary
        \item Future Work
    \end{itemize}
\end{frame}

\begin{frame}{References}
    \bibliographystyle{plain}
    \bibliography{references}
\end{frame}

\end{document}
""",
    "table": r"""\begin{table}[%(position)s]
\centering
\caption{%(caption)s}
\label{tab:%(label)s}
\begin{tabular}{%(columns)s}
\toprule
%(header)s \\
\midrule
%(rows)s \\
\bottomrule
\end{tabular}
\end{table}
""",
    "figure": r"""\begin{figure}[%(position)s]
\centering
\includegraphics[width=%(width)s\textwidth]{%(filename)s}
\caption{%(caption)s}
\label{fig:%(label)s}
\end{figure}
""",
    "algorithm": r"""\begin{algorithm}[%(position)s]
\caption{%(caption)s}
\label{alg:%(label)s}
\begin{algorithmic}[1]
\Require %(input)s
\Ensure %(output)s
\State %(steps)s
\end{algorithmic}
\end{algorithm}
""",
}


def latex_template(
    template_name: str,
    title: str = "Paper Title",
    author: str = "Author Name",
    **kwargs: str,
) -> str:
    """Generate a LaTeX template.

    Parameters
    ----------
    template_name:
        Template name: ``"article"``, ``"ieee"``, ``"acl"``, ``"neurips"``,
        ``"beamer"``, ``"table"``, ``"figure"``, ``"algorithm"``.
    title:
        Document/element title.
    author:
        Author name(s).
    **kwargs:
        Additional template variables (e.g. ``abstract``, ``affiliation``,
        ``keywords``, ``date``, ``email``).

    Returns
    -------
    str
        Generated LaTeX source.
    """
    template = _TEMPLATES.get(template_name)
    if template is None:
        available = ", ".join(sorted(_TEMPLATES.keys()))
        return f"Unknown template: {template_name}. Available: {available}"

    # Build substitution dict with defaults
    subs: dict[str, str] = {
        "title": title,
        "author": author,
        "abstract": kwargs.get("abstract", "Your abstract here."),
        "affiliation": kwargs.get("affiliation", "University"),
        "email": kwargs.get("email", "author@university.edu"),
        "keywords": kwargs.get("keywords", "keyword1, keyword2"),
        "date": kwargs.get("date", r"\today"),
        "position": kwargs.get("position", "htbp"),
        "caption": kwargs.get("caption", "Caption"),
        "label": kwargs.get("label", "label"),
        "columns": kwargs.get("columns", "lcc"),
        "header": kwargs.get("header", "Column 1 & Column 2 & Column 3"),
        "rows": kwargs.get("rows", "data1 & data2 & data3"),
        "width": kwargs.get("width", "0.8"),
        "filename": kwargs.get("filename", "figure.pdf"),
        "input": kwargs.get("input", "Input description"),
        "output": kwargs.get("output", "Output description"),
        "steps": kwargs.get("steps", r"\State Step 1"),
    }

    try:
        return template % subs
    except KeyError as e:
        return f"Template requires variable: {e}"


def latex_compile_check(latex_source: str) -> dict[str, Any]:
    """Check LaTeX source for common syntax errors.

    Parameters
    ----------
    latex_source:
        LaTeX source code to check.

    Returns
    -------
    dict
        Result with ``valid`` (bool), ``errors`` (list), ``warnings`` (list).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check matching braces
    open_braces = latex_source.count("{")
    close_braces = latex_source.count("}")
    if open_braces != close_braces:
        errors.append(
            f"Mismatched braces: {open_braces} opening, {close_braces} closing",
        )

    # Check matching environments
    begin_envs = re.findall(r"\\begin\{(\w+)\}", latex_source)
    end_envs = re.findall(r"\\end\{(\w+)\}", latex_source)

    begin_counts: dict[str, int] = {}
    for env in begin_envs:
        begin_counts[env] = begin_counts.get(env, 0) + 1
    end_counts: dict[str, int] = {}
    for env in end_envs:
        end_counts[env] = end_counts.get(env, 0) + 1

    for env in set(list(begin_counts.keys()) + list(end_counts.keys())):
        b = begin_counts.get(env, 0)
        e = end_counts.get(env, 0)
        if b != e:
            errors.append(
                f"Environment '{env}': {b} \\begin vs {e} \\end",
            )

    # Check for document class
    if r"\documentclass" not in latex_source:
        warnings.append("No \\documentclass found")

    # Check for begin/end document
    if r"\begin{document}" not in latex_source:
        warnings.append("No \\begin{document} found")
    if r"\end{document}" not in latex_source:
        warnings.append("No \\end{document} found")

    # Check for common mistakes
    if re.search(r"\\cite\{\s*\}", latex_source):
        warnings.append("Empty \\cite{} found")
    if re.search(r"\\ref\{\s*\}", latex_source):
        warnings.append("Empty \\ref{} found")
    if re.search(r"\\label\{\s*\}", latex_source):
        warnings.append("Empty \\label{} found")

    # Check for undefined labels
    labels = set(re.findall(r"\\label\{([^}]+)\}", latex_source))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", latex_source))
    undefined_refs = refs - labels
    if undefined_refs:
        warnings.append(f"Potentially undefined references: {undefined_refs}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

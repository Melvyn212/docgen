#!/usr/bin/env python3
"""
Génère des tableaux d'honneur en lot à partir d'un fichier JSON de configuration,
sans modifier le template LaTeX.
"""

import json
import re
import subprocess
from pathlib import Path


def escape_tex(value: str) -> str:
    """Échappe les caractères LaTeX courants."""
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in str(value):
        out.append(repl.get(ch, ch))
    return "".join(out)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_macros(entry: dict, defaults: dict) -> str:
    macros = {
        "AVGOVERRIDE": entry["avg"],
        "STUDENTNAME": entry["name"],
        "CLASSLEVEL": entry.get("class_level", defaults.get("class_level", "Classe")),
        "RANKVAL": entry.get("rank", defaults.get("rank", "1")),
        "CLASSSIZEVAL": entry.get("class_size", defaults.get("class_size", "30")),
        "TERMVAL": entry.get("term", defaults.get("term", "T1")),
        "ACADEMICYEARVAL": entry.get("academic_year", defaults.get("academic_year", "2025--2026")),
        "SCHOOLNAME": defaults.get("school_name", "Établissement"),
        "SCHOOLCITY": defaults.get("school_city", "Ville"),
    }
    parts = [f"\\def\\{k}{{{escape_tex(v)}}}" for k, v in macros.items()]
    return "".join(parts)


def safe_jobname(base: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", base)


def render_one(template: Path, out_dir: Path, jobname: str, macro_block: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    tex_input = macro_block + f"\\input{{{template.as_posix()}}}"
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-jobname={jobname}",
        f"-output-directory={out_dir.as_posix()}",
        tex_input,
    ]
    # Deux passes pour stabiliser les références (supprime le warning "Label(s) may have changed")
    subprocess.run(cmd, check=True)
    subprocess.run(cmd, check=True)


def main():
    cfg = load_config(Path("config/honor_batch.json"))
    template = Path(cfg.get("template", "templates_latex/tableau_honneur.tex"))
    out_dir = Path(cfg.get("output_dir", "out_honor"))
    defaults = cfg.get("defaults", {})
    students = cfg.get("students", [])
    prefix = cfg.get("job_prefix", "honor_")

    for idx, student in enumerate(students, start=1):
        macro_block = build_macros(student, defaults)
        base = f"{prefix}{student.get('avg', idx)}_{idx}"
        jobname = safe_jobname(base)
        render_one(template, out_dir, jobname, macro_block)


if __name__ == "__main__":
    main()

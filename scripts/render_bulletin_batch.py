#!/usr/bin/env python3
"""
Génère des bulletins scolaires en lot à partir d'un JSON de configuration,
en injectant les macros en ligne sans modifier le template.
Deux passes XeLaTeX (renderer configured via XELATEX_PASSES=2 en contexte).
"""

import json
import re
import subprocess
from pathlib import Path


def escape_tex(value: str) -> str:
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
    return "".join(repl.get(ch, ch) for ch in str(value))


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_macros(entry: dict, defaults: dict) -> str:
    def to_float(val):
        try:
            return float(str(val).replace(",", "."))
        except Exception:
            return None

    def split_subjects():
        subs = entry.get("subjects", defaults.get("subjects", []))
        primary_count = int(defaults.get("primary_count", 7))
        return subs[:primary_count], subs[primary_count:]

    def render_rows(subs):
        if not subs:
            return r"\textit{À compléter} & -- & -- & \textit{Notes à insérer} & -- \\"
        rows = []
        for s in subs:
            name = escape_tex(s.get("name", ""))
            avg = escape_tex(s.get("avg", "--"))
            coef = escape_tex(s.get("coef", "--"))
            comment = escape_tex(s.get("comment", ""))
            teacher = escape_tex(s.get("teacher", ""))
            rows.append(f"{name} & {avg} & {coef} & {comment} & {teacher} \\\\")
        return "".join(rows)

    def compute_avg(subs):
        weights = []
        values = []
        for s in subs:
            a = to_float(s.get("avg"))
            c = to_float(s.get("coef", 0))
            if a is not None and c not in (None, 0):
                values.append(a * c)
                weights.append(c)
        if not weights:
            return "--"
        return f"{sum(values)/sum(weights):.2f}"

    main_subs, comp_subs = split_subjects()
    main_rows = render_rows(main_subs)
    comp_rows = render_rows(comp_subs)
    main_avg = compute_avg(main_subs)
    comp_avg = compute_avg(comp_subs)

    term_label = entry.get("term_label", defaults.get("term_label", "Trimestre 1"))
    trim_code = entry.get("trim_code", defaults.get("trim_code", "1"))
    if isinstance(trim_code, str):
        if trim_code.upper() in {"T1", "1"}:
            trim_code = "1"
        elif trim_code.upper() in {"T2", "2"}:
            trim_code = "2"
        elif trim_code.upper() in {"T3", "3"}:
            trim_code = "3"
    if isinstance(term_label, str) and trim_code == "1":
        if "2" in term_label:
            trim_code = "2"
        elif "3" in term_label:
            trim_code = "3"

    macros = {
        # noms des macros alignés sur le template
        "STUDENTNAME": entry["name"],
        "MATRICULE": entry.get("matricule", defaults.get("matricule", "")),
        "AVGVAL": entry.get("avg", ""),
        "WEIGHTEDVAL": entry.get("weighted", ""),
        "RANKVAL": entry.get("rank", ""),
        "HONORVAL": entry.get("honor", ""),
        "CLASSNAME": entry.get("class_name", defaults.get("class_name", "")),
        "CLASSSIZE": entry.get("class_size", defaults.get("class_size", "")),
        "TERMLABEL": entry.get("term_label", defaults.get("term_label", "")),
        "ACADEMICYEAR": entry.get("academic_year", defaults.get("academic_year", "")),
        "SCHOOLNAME": entry.get("school_name", defaults.get("school_name", "")),
        "SCHOOLCOUNTRY": entry.get("school_country", defaults.get("school_country", "")),
        "SCHOOLCITY": entry.get("school_city", defaults.get("school_city", "")),
        "SCHOOLADDRESS": entry.get("school_address", defaults.get("school_address", "")),
        "SCHOOLPHONE": entry.get("school_phone", defaults.get("school_phone", "")),
        "SCHOOLEMAIL": entry.get("school_email", defaults.get("school_email", "")),
        "CLASSBEST": entry.get("class_best_avg", defaults.get("class_best_avg", "")),
        "CLASSAVG": entry.get("class_avg", defaults.get("class_avg", "")),
        "CLASSMIN": entry.get("class_min_avg", defaults.get("class_min_avg", "")),
        "GENERALAPP": entry.get("general_appreciation", defaults.get("general_appreciation", "")),
        "CONDUCT": entry.get("conduct", defaults.get("conduct", "")),
        "SANCTION": entry.get("sanction", defaults.get("sanction", "")),
        "TRIMCODE": trim_code,
        "MAINROWS": main_rows,
        "COMPROWS": comp_rows,
        "MAINAVG": main_avg,
        "COMPAVG": comp_avg,
        "YEARAVG": entry.get("year_avg", defaults.get("year_avg", "")),
        "TRIMONEAVG": entry.get("t1_avg", defaults.get("t1_avg", "")),
        "TRIMTWOAVG": entry.get("t2_avg", defaults.get("t2_avg", "")),
    }
    parts = []
    raw_macros = {"SUBJECTROWS", "MAINROWS", "COMPROWS"}
    for k, v in macros.items():
        if k in raw_macros:
            parts.append(f"\\def\\{k}{{{v}}}")
        else:
            parts.append(f"\\def\\{k}{{{escape_tex(v)}}}")
    # force deux passes côté renderer
    parts.append("\\def\\XELATEX_PASSES{2}")
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
    # deux passes pour stabiliser (et en plus XELATEX_PASSES=2 côté renderer)
    subprocess.run(cmd, check=True)
    subprocess.run(cmd, check=True)


def main():
    cfg = load_config(Path("config/bulletin_batch.json"))
    template = Path(cfg.get("template", "templates_latex/bulletin.tex"))
    out_dir = Path(cfg.get("output_dir", "out_bulletins"))
    defaults = cfg.get("defaults", {})
    students = cfg.get("students", [])
    prefix = cfg.get("job_prefix", "bulletin_")

    for idx, student in enumerate(students, start=1):
        macro_block = build_macros(student, defaults)
        base = f"{prefix}{student.get('matricule', student.get('avg', idx))}_{idx}"
        jobname = safe_jobname(base)
        render_one(template, out_dir, jobname, macro_block)


if __name__ == "__main__":
    main()

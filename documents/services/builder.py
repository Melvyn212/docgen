import json
import logging
import subprocess
from pathlib import Path

from django.conf import settings
from django.db.models import Avg
from django.utils import timezone

from schools.models import Grade, TermResult, FollowUp, Subject
from documents.models import Document

logger = logging.getLogger(__name__)

LATEX_REPLACEMENTS = {
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


def latex_escape(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    return "".join(LATEX_REPLACEMENTS.get(ch, ch) for ch in value)

DEFAULT_THEMES = {
    "BULLETIN": {
        "colors": {
            "bg": "F9FAFB",
            "card": "FFFFFF",
            "primary": "0F172A",
            "muted": "64748B",
            "footer": "1E3A8A",
        },
        "logo": {
            "enabled": True,
            "path": str(Path("logo.png")),
            "override_school_logo": False,
        },
        "watermark": {
            "enabled": True,
            "path": str(Path("filigrame.png")),
        },
        "school": {
            "name": "",
            "country": "",
            "city": "",
            "phone": "",
            "email": "",
        },
    },
    "HONOR": {
        "colors": {
            "gold_bg": "FBF3D0",
            "gold": "C9A24D",
            "primary": "1E3A8A",
            "muted": "475569",
        },
        "logo": {
            "enabled": True,
            "path": str(Path("logo.png")),
            "override_school_logo": False,
        },
        "watermark": {
            "enabled": True,
            "path": str(Path("filigrame.png")),
        },
        "school": {
            "name": "",
            "country": "",
            "city": "",
            "phone": "",
            "email": "",
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_theme_path(path_value) -> str:
    if not path_value:
        return ""
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = Path(settings.BASE_DIR) / candidate
    if candidate.exists():
        return str(candidate)
    logger.warning("Theme asset not found: %s", candidate)
    return ""


def _ensure_default_filigrane(asset_root: Path):
    """
    Compile templates_latex/filigrane.tex into assets/filigrane.pdf if missing.
    This avoids manual steps and runs once until the file exists.
    """
    target_pdf = asset_root / "filigrane.pdf"
    if target_pdf.exists():
        return
    source_tex = Path(settings.BASE_DIR) / "templates_latex" / "filigrane.tex"
    if not source_tex.exists():
        return
    asset_root.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                getattr(settings, "XELATEX_BIN", "xelatex"),
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={asset_root}",
                source_tex.name,
            ],
            cwd=source_tex.parent,
            check=True,
            capture_output=True,
            timeout=60,
        )
        logger.info("Compiled default filigrane into assets: %s", target_pdf)
    except Exception as exc:
        logger.warning("Unable to compile default filigrane.tex: %s", exc)


def _load_theme(doc_type: str) -> dict:
    theme_files = getattr(settings, "LATEX_THEME_FILES", {})
    theme_file = theme_files.get(doc_type)
    defaults = DEFAULT_THEMES.get(doc_type, {})
    if not theme_file:
        return defaults

    try:
        parsed = json.loads(Path(theme_file).read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            logger.warning("Theme config is not an object for %s: %s", doc_type, theme_file)
            parsed = {}
    except FileNotFoundError:
        logger.warning("Theme config file not found for %s: %s", doc_type, theme_file)
        parsed = {}
    except json.JSONDecodeError as exc:
        logger.warning("Theme config JSON invalid for %s: %s", doc_type, exc)
        parsed = {}

    return _deep_merge(defaults, parsed)


def build_context(doc: Document) -> dict:
    theme = _load_theme(doc.doc_type)
    theme_colors = theme.get("colors", {})
    theme_logo = theme.get("logo", {})
    theme_watermark = theme.get("watermark", {})
    theme_school = theme.get("school", {})
    default_colors = DEFAULT_THEMES.get(doc.doc_type, {}).get("colors", {})
    asset_root = Path(settings.BASE_DIR) / "assets"
    _ensure_default_filigrane(asset_root)
    asset_root.mkdir(parents=True, exist_ok=True)

    student = doc.student
    school = student.klass.school
    term_result = TermResult.objects.get(student=student, term=doc.term)
    # Rappels T1/T2 et moyenne annuelle (si disponibles)
    term_map = {tr.term: tr for tr in TermResult.objects.filter(student=student)}
    t1_avg_val = term_map.get("T1").average if term_map.get("T1") else None
    t2_avg_val = term_map.get("T2").average if term_map.get("T2") else None
    # moyenne annuelle simple (moyenne des averages disponibles)
    year_avg_val = None
    avg_values = [v for v in (t1_avg_val, t2_avg_val, term_result.average) if v is not None]
    if avg_values:
        year_avg_val = sum([float(v) for v in avg_values]) / len(avg_values)
    grades = Grade.objects.filter(student=student).select_related("subject")
    follow = FollowUp.objects.filter(student=student).first()
    class_results = TermResult.objects.filter(student__klass=student.klass, term=doc.term)

    # Construit la liste des matières à partir du catalogue (pour ne pas perdre les compléments si une note manque)
    subjects = []
    grade_map = {g.subject_id: g for g in grades}
    all_subjects = Subject.objects.filter(school=school).order_by("name")

    def fmt_decimal(value):
        if value is None:
            return ""
        try:
            return f"{float(value):.2f}"
        except Exception:
            return str(value)

    for subj in all_subjects:
        g = grade_map.get(subj.id)
        subjects.append(
            {
                "name": latex_escape(subj.name),
                "avg": fmt_decimal(getattr(g, "average", None)) or "--",
                "coef": fmt_decimal(subj.coefficient),
                "app": latex_escape(getattr(g, "get_appreciation_display", lambda: "À évaluer")()),
                "teacher": latex_escape(subj.teacher_name),
            }
        )

    # flatten follow-up for injection
    follow_context = {
        "ASSIDUITE": follow.assiduite if follow else "",
        "PONCTUALITE": follow.ponctualite if follow else "",
        "COMPORTEMENT": follow.comportement if follow else "",
        "PARTICIPATION": follow.participation if follow else "",
    }

    school_name = latex_escape(theme_school.get("name") or school.name)
    school_country = latex_escape(theme_school.get("country") or school.country)
    school_city = latex_escape(theme_school.get("city") or "")
    school_phone = latex_escape(theme_school.get("phone") or "")
    school_email = latex_escape(theme_school.get("email") or "")
    school_address = latex_escape(school.address)
    school_motto = latex_escape(school.motto or "UNITÉ — PROGRÈS — JUSTICE")

    try:
        logo_path = school.logo.path
    except Exception:
        logo_path = ""

    theme_logo_path = _resolve_theme_path(theme_logo.get("path"))
    if theme_logo.get("override_school_logo"):
        logo_path = theme_logo_path
    elif not logo_path:
        logo_path = theme_logo_path

    # fallback: uniquement assets/logo.png si aucune source définie ou existante
    fallback_logo_candidates = [asset_root / "logo.png"]
    for cand in fallback_logo_candidates:
        if (not logo_path or not Path(logo_path).exists()) and cand.exists():
            logo_path = str(cand)
            break

    logo_enabled = theme_logo.get("enabled", True)
    if not logo_enabled:
        logo_path = ""
    has_logo = 1 if logo_enabled and logo_path and Path(logo_path).exists() else 0

    # Préférence pour un filigrane précompilé en PDF (plus léger à charger)
    fallback_wm = ""
    wm_candidates = [
        asset_root / "filigrane.pdf",
        asset_root / "filigrame.pdf",
        asset_root / "filigrane.png",
        asset_root / "filigrame.png",
    ]
    for cand in wm_candidates:
        if cand.exists():
            fallback_wm = str(cand)
            break

    wm_path_candidate = _resolve_theme_path(theme_watermark.get("path")) or fallback_wm
    wm_enabled = theme_watermark.get("enabled", True)
    wm_path_str = wm_path_candidate if wm_enabled else ""
    has_wm = 1 if wm_path_str and Path(wm_path_str).exists() else 0

    def color_value(key: str, fallback: str = "000000") -> str:
        return theme_colors.get(key, default_colors.get(key, fallback))

    color_context = {}
    if doc.doc_type == "BULLETIN":
        color_context = {
            "BULLETIN_COLOR_BG": color_value("bg", "F9FAFB"),
            "BULLETIN_COLOR_CARD": color_value("card", "FFFFFF"),
            "BULLETIN_COLOR_PRIMARY": color_value("primary", "0F172A"),
            "BULLETIN_COLOR_MUTED": color_value("muted", "64748B"),
            "BULLETIN_COLOR_FOOTER": color_value("footer", "1E3A8A"),
        }
    elif doc.doc_type == "HONOR":
        color_context = {
            "HONOR_COLOR_GOLD_BG": color_value("gold_bg", "FBF3D0"),
            "HONOR_COLOR_GOLD": color_value("gold", "C9A24D"),
            "HONOR_COLOR_PRIMARY": color_value("primary", "1E3A8A"),
            "HONOR_COLOR_MUTED": color_value("muted", "475569"),
        }

    # Date locale (français)
    def format_date_fr(dt):
        MONTHS = {
            1: "janvier",
            2: "février",
            3: "mars",
            4: "avril",
            5: "mai",
            6: "juin",
            7: "juillet",
            8: "août",
            9: "septembre",
            10: "octobre",
            11: "novembre",
            12: "décembre",
        }
        return f"{dt.day:02d} {MONTHS.get(dt.month, '')} {dt.year}"

    today_dt = timezone.localtime(
        term_result.created_at if hasattr(term_result, "created_at") else timezone.now()
    ).date()
    today_label = format_date_fr(today_dt)

    context = {
        "SCHOOL_NAME": school_name,
        "SCHOOL_ADDRESS": school_address,
        "SCHOOL_COUNTRY": school_country,
        "SCHOOL_CITY": school_city,
        "SCHOOL_PHONE": school_phone,
        "SCHOOL_EMAIL": school_email,
        "SCHOOL_MOTTO": school_motto,
        "ACADEMIC_YEAR": school.academic_year,
        "LOGO_PATH": logo_path,
        "HAS_LOGO": has_logo,
        "WATERMARK_PATH": wm_path_str,
        "HAS_WATERMARK": has_wm,
        "ASSET_DIR": str(asset_root) if asset_root.exists() else "",
        "DOC_TYPE": doc.doc_type,
        "STUDENT_NAME": latex_escape(f"{student.first_name} {student.last_name}"),
        "MATRICULE": latex_escape(student.matricule),
        "CLASS_NAME": latex_escape(student.klass.name),
        "CLASS_LEVEL": latex_escape(student.klass.level),
        "CLASS_SIZE": student.klass.total_students,
        "TERM": doc.term,
        "AVG": term_result.average,
        "WEIGHTED": term_result.weighted_total,
        "RANK": term_result.rank,
        "HONOR_BOARD": "Oui" if term_result.honor_board else "Non",
        "TODAY": today_label,
    }

    # Rappels et moyenne annuelle formatés
    context.update(
        {
            "T1_AVG": fmt_decimal(t1_avg_val),
            "T2_AVG": fmt_decimal(t2_avg_val),
            "YEAR_AVG": fmt_decimal(year_avg_val),
        }
    )

    # Informations de classe
    class_best_avg = class_results.order_by("-average").values_list("average", flat=True).first()
    class_avg = class_results.aggregate(avg=Avg("average")).get("avg")

    def fmt_decimal(value):
        if value is None:
            return ""
        try:
            return f"{float(value):.2f}"
        except Exception:
            return str(value)

    context.update(
        {
            "TERM_LABEL": {"T1": "Trimestre 1", "T2": "Trimestre 2", "T3": "Trimestre 3"}.get(doc.term, doc.term),
            "CLASS_BEST_AVG": fmt_decimal(class_best_avg),
            "CLASS_AVG": fmt_decimal(class_avg),
        }
    )

    if follow:
        general_appreciation = (
            f"Assiduité : {follow.assiduite}/20. Ponctualité : {follow.ponctualite}/20.\n"
            f"Comportement : {follow.comportement}/20. Participation : {follow.participation}/20."
        )
    else:
        general_appreciation = (
            "Élève sérieux et impliqué. Les résultats sont globalement satisfaisants,\n"
            "avec un excellent niveau dans les matières scientifiques.\n"
            "Des efforts supplémentaires sont attendus dans certaines disciplines\n"
            "littéraires afin d'améliorer l'équilibre général."
        )

    def weighted_avg(subs):
        vals, weights = [], []
        for s in subs:
            try:
                a = float(s.get("avg", 0))
                c = float(s.get("coef", 0))
            except Exception:
                continue
            if c > 0:
                vals.append(a * c)
                weights.append(c)
        if not weights:
            return "--"
        return f"{sum(vals)/sum(weights):.2f}"

    primary_count = getattr(settings, "BULLETIN_PRIMARY_COUNT", 7)
    main_subs = subjects[:primary_count]
    comp_subs = subjects[primary_count:]

    def render_rows(subs):
        if not subs:
            return r"\textit{À compléter} & -- & -- & \textit{Notes à insérer} & -- \\"
        return "".join(
            f"{s['name']} & {s['avg']} & {s['coef']} & {s['app']} & {s['teacher']} \\\\"
            for s in subs
        )

    main_rows = render_rows(main_subs)
    comp_rows = render_rows(comp_subs)
    main_avg = weighted_avg(main_subs)
    comp_avg = weighted_avg(comp_subs)

    class_best_avg = class_results.order_by("-average").values_list("average", flat=True).first()
    class_avg = class_results.aggregate(avg=Avg("average")).get("avg")
    class_min = class_results.order_by("average").values_list("average", flat=True).first()

    context.update(
        {
            "TERM_LABEL": {"T1": "Trimestre 1", "T2": "Trimestre 2", "T3": "Trimestre 3"}.get(doc.term, doc.term),
            "CLASS_BEST_AVG": fmt_decimal(class_best_avg),
            "CLASS_AVG": fmt_decimal(class_avg),
            "CLASS_MIN": fmt_decimal(class_min),
        }
    )

    # template loop markers for subjects (honor placeholder legacy)
    subject_rows = []
    for item in subjects:
        row = "<<SUBJECT_NAME>> & <<SUBJECT_AVG>> & <<SUBJECT_COEF>> & <<SUBJECT_APP>> & <<SUBJECT_TEACHER>> \\\\"
        row = row.replace("<<SUBJECT_NAME>>", item["name"])
        row = row.replace("<<SUBJECT_AVG>>", str(item["avg"]))
        row = row.replace("<<SUBJECT_COEF>>", str(item["coef"]))
        row = row.replace("<<SUBJECT_APP>>", item["app"])
        row = row.replace("<<SUBJECT_TEACHER>>", item["teacher"])
        subject_rows.append(row)

    context["GENERAL_APPRECIATION"] = latex_escape(general_appreciation)
    context["SUBJECT_ROWS"] = "\n".join(subject_rows) or "% no subjects"
    context.update(color_context)
    context.update(follow_context)

    # Macros pour le template bulletin (sans underscores)
    term_code = {"T1": "1", "T2": "2", "T3": "3"}.get(doc.term, "1")
    macros = {
        "TRIMCODE": term_code,
        "TERMLABEL": context["TERM_LABEL"],
        "ACADEMICYEAR": latex_escape(context["ACADEMIC_YEAR"]),
        "SCHOOLNAME": school_name,
        "SCHOOLCOUNTRY": school_country,
        "SCHOOLCITY": school_city,
        "SCHOOLADDRESS": school_address,
        "SCHOOLPHONE": school_phone,
        "SCHOOLEMAIL": school_email,
        "STUDENTNAME": context["STUDENT_NAME"],
        "CLASSNAME": context["CLASS_NAME"],
        "MATRICULE": context["MATRICULE"],
        "CLASSSIZE": context["CLASS_SIZE"],
        "AVGVAL": fmt_decimal(context["AVG"]),
        "WEIGHTEDVAL": fmt_decimal(context["WEIGHTED"]),
        "RANKVAL": context["RANK"],
        "HONORVAL": context["HONOR_BOARD"],
        "CLASSBEST": context["CLASS_BEST_AVG"],
        "CLASSAVG": context["CLASS_AVG"],
        "CLASSMIN": context["CLASS_MIN"],
        "MAINROWS": main_rows,
        "COMPROWS": comp_rows,
        "MAINAVG": main_avg,
        "COMPAVG": comp_avg,
        "YEARAVG": fmt_decimal(context.get("YEAR_AVG", "")),
        "TRIMONEAVG": fmt_decimal(context.get("T1_AVG", "")),
        "TRIMTWOAVG": fmt_decimal(context.get("T2_AVG", "")),
        "GENERALAPP": context["GENERAL_APPRECIATION"],
        "CONDUCT": follow_context["COMPORTEMENT"] or "Bonne",
        "SANCTION": "N/A",
        "TODAYVAL": today_label,
    }
    if logo_path:
        macros["logopath"] = logo_path

    context["_MACROS"] = macros
    # passes XeLaTeX : 2 pour bulletin et tableau d'honneur afin de stabiliser les refs/overlays
    context["XELATEX_PASSES"] = 2 if doc.doc_type in ("BULLETIN", "HONOR") else 1
    return context

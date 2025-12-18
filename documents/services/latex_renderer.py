import shutil
import subprocess
import tempfile
from pathlib import Path

import logging

from django.conf import settings


class LatexRenderError(Exception):
    pass


class LatexRenderer:
    """
    Renders a LaTeX template by simple placeholder replacement and compiles it with XeLaTeX.
    Placeholders use the form <<PLACEHOLDER>>.
    """

    def __init__(self, template_path: Path, context: dict):
        self.template_path = Path(template_path)
        self.context = context
        self.logger = logging.getLogger(__name__)
        try:
            self.passes = max(1, int(context.get("XELATEX_PASSES", getattr(settings, "LATEX_DEFAULT_PASSES", 1))))
        except Exception:
            self.passes = 1

    def render_tex(self, dest_dir: Path) -> Path:
        tex = self.template_path.read_text(encoding="utf-8")
        # Inject template directory and default assets so logos/filigranes remain accessibles dans le tmpdir
        context = dict(self.context)
        asset_dir = self.template_path.parent
        context.setdefault("ASSET_DIR", str(asset_dir))
        # Copie éventuelle du dossier assets fourni (logos/filigranes) dans le tmpdir pour conserver les chemins relatifs
        assets_source = Path(context.get("ASSET_DIR"))
        assets_dest = dest_dir / "assets"
        if assets_source.exists() and assets_source.is_dir():
            try:
                if not assets_dest.exists():
                    shutil.copytree(assets_source, assets_dest)
            except Exception:
                pass

        # Logos par défaut
        if not context.get("LOGO_PATH"):
            default_logo = asset_dir / "logo.png"
            if default_logo.exists():
                context["LOGO_PATH"] = str(default_logo)
        context.setdefault(
            "HAS_LOGO",
            1 if context.get("LOGO_PATH") and Path(context["LOGO_PATH"]).exists() else 0,
        )

        # Filigrane par défaut
        if not context.get("WATERMARK_PATH"):
            default_wm = asset_dir / "filigrame.png"
            if default_wm.exists():
                context["WATERMARK_PATH"] = str(default_wm)
        context.setdefault(
            "HAS_WATERMARK",
            1 if context.get("WATERMARK_PATH") and Path(context["WATERMARK_PATH"]).exists() else 0,
        )

        macros = context.pop("_MACROS", None)

        for key, value in context.items():
            tex = tex.replace(f"<<{key}>>", str(value))

        if macros:
            macro_lines = [f"% injected"]
            for name, value in macros.items():
                # ignore macro names containing spaces
                if not name:
                    continue
                macro_lines.append(f"\\def\\{name}{{{value}}}")
            macro_block = "\n".join(macro_lines) + "\n"
            if "\\begin{document}" in tex:
                tex = tex.replace("\\begin{document}", macro_block + "\\begin{document}", 1)
            else:
                tex = macro_block + tex

        out = dest_dir / "document.tex"
        out.write_text(tex, encoding="utf-8")
        self.logger.info(
            "LaTeX render prepared",
            extra={
                "template": str(self.template_path),
                "dest_dir": str(dest_dir),
                "logo_path": context.get("LOGO_PATH", ""),
                "watermark_path": context.get("WATERMARK_PATH", ""),
                "has_logo": context.get("HAS_LOGO", 0),
                "has_watermark": context.get("HAS_WATERMARK", 0),
            },
        )
        return out

    def compile_pdf(self, tex_path: Path) -> Path:
        workdir = tex_path.parent
        cmd = [
            getattr(settings, "XELATEX_BIN", "xelatex"),
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_path.name,
        ]
        run_logs = []
        try:
            for idx in range(self.passes):
                result = subprocess.run(
                    cmd,
                    cwd=workdir,
                    check=True,
                    capture_output=True,
                    timeout=60,
                    text=True,
                )
                run_logs.append(
                    f"""PASS {idx+1}: {' '.join(cmd)}
STDOUT:
{result.stdout}

STDERR:
{result.stderr}
""".strip()
                )
            log_path = workdir / f"{tex_path.stem}.compile.log"
            log_path.write_text("\n\n".join(run_logs).strip(), encoding="utf-8")
            self.logger.info(
                "LaTeX compiled successfully",
                extra={
                    "tex": str(tex_path),
                    "pdf": str(workdir / (tex_path.stem + ".pdf")),
                },
            )
        except subprocess.CalledProcessError as exc:
            log_path = workdir / (tex_path.stem + ".log")
            log_content = ""
            if log_path.exists():
                log_content = log_path.read_text(encoding="utf-8", errors="ignore")
                # pour debug : fournir le début et la fin du log
                start = log_content[:1200]
                end = log_content[-1200:] if len(log_content) > 1200 else ""
                log_content = start + ("\n…\n" if end else "") + end
            if run_logs:
                run_log_str = "\n\n".join(run_logs)
                log_content = (run_log_str + "\n\n" + log_content) if log_content else run_log_str
            # Ajoute aussi la sortie immédiate du process pour debug web
            if exc.stdout or exc.stderr:
                log_content = (
                    (log_content + "\n\n" if log_content else "")
                    + f"STDOUT:\n{exc.stdout}\n\nSTDERR:\n{exc.stderr}"
                )
            logging.getLogger(__name__).error("XeLaTeX failed: %s", exc)
            raise LatexRenderError(log_content or str(exc)) from exc
        return workdir / (tex_path.stem + ".pdf")

    def generate(self) -> bytes:
        tmpdir = Path(
            tempfile.mkdtemp(
                prefix="latexdoc_",
                dir=getattr(settings, "LATEX_TMP_DIR", None) or None,
            )
        )
        tex = None
        try:
            tex = self.render_tex(tmpdir)
            pdf_path = self.compile_pdf(tex)
            return pdf_path.read_bytes()
        finally:
            # Sauvegarde optionnelle des logs/tex dans un répertoire dédié (y compris en cas d'erreur)
            log_dir = getattr(settings, "LATEX_LOG_DIR", None)
            if not log_dir:
                # fallback vers media/latex_logs
                log_dir = Path(getattr(settings, "MEDIA_ROOT", Path("."))) / "latex_logs"
            if tex is not None and log_dir:
                # Sous-dossier par type de document (si fourni)
                doc_type = str(self.context.get("DOC_TYPE", "generic")).lower()
                log_dir = Path(log_dir) / doc_type
                log_dir.mkdir(parents=True, exist_ok=True)
                suffix = tmpdir.name
                for ext in (".log", ".compile.log", ".tex"):
                    src = tmpdir / f"{tex.stem}{ext}"
                    if src.exists():
                        dest = log_dir / f"{tex.stem}_{suffix}{ext}"
                        shutil.copy(src, dest)
                        self.logger.info("LaTeX log archived", extra={"src": str(src), "dest": str(dest)})
            shutil.rmtree(tmpdir, ignore_errors=True)

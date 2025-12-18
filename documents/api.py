from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse, HttpResponse, FileResponse
from django.utils import timezone

from documents.models import Document, Batch
from documents.tasks import generate_document
from documents.services.metrics import mark_pending, mark_failed
from documents.services.builder import build_context
from documents.services.latex_renderer import LatexRenderer
from schools.models import Student, TermResult
from django.conf import settings
from documents.services.metrics import reset_metrics
from pathlib import Path
import zipfile
import os


class DocumentRequestSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(required=True)
    term = serializers.ChoiceField(choices=[c[0] for c in TermResult.TERM_CHOICES])
    force_new = serializers.BooleanField(required=False, default=False)


class GenerateBulletinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data["student_id"]
        term = serializer.validated_data["term"]
        force_new = serializer.validated_data.get("force_new", False)
        student = get_object_or_404(Student, pk=student_id)
        if not TermResult.objects.filter(student=student, term=term).exists():
            return Response(
                {"detail": "TermResult manquant pour cet élève/terme."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            existing = None
            if not force_new:
                existing = (
                    Document.objects.select_for_update()
                    .filter(student=student, term=term, doc_type="BULLETIN")
                    .order_by("-created_at")
                    .first()
                )
            enqueue = True
            if existing:
                prev_status = existing.status
                if existing.status == "READY":
                    return Response({"id": existing.id, "status": existing.status}, status=status.HTTP_200_OK)
                if existing.status == "PENDING":
                    enqueue = False  # déjà en file, on ne duplique pas
                doc = existing
                doc.status = "PENDING"
                doc.pdf_path = ""
                doc.completed_at = None
                doc.save(update_fields=["status", "pdf_path", "completed_at"])
                if prev_status != "PENDING":
                    mark_pending(doc.id)
            else:
                doc = Document.objects.create(
                    student=student, term=term, doc_type="BULLETIN", status="PENDING", pdf_path="", completed_at=None
                )
                mark_pending(doc.id)

        try:
            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                res = generate_document.apply(args=[doc.id])
                pdf_url = res.get()
                return Response({"id": doc.id, "status": "READY", "pdf_url": pdf_url}, status=status.HTTP_200_OK)
            if enqueue:
                generate_document.delay(doc.id)
        except Exception as exc:
            doc.status = "FAILED"
            doc.completed_at = timezone.now()
            doc.save(update_fields=["status", "completed_at"])
            mark_failed(doc.id)
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"id": doc.id, "status": doc.status}, status=status.HTTP_202_ACCEPTED)


class GenerateHonorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data["student_id"]
        term = serializer.validated_data["term"]
        force_new = serializer.validated_data.get("force_new", False)
        student = get_object_or_404(Student, pk=student_id)
        if not TermResult.objects.filter(student=student, term=term).exists():
            return Response(
                {"detail": "TermResult manquant pour cet élève/terme."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            existing = None
            if not force_new:
                existing = (
                    Document.objects.select_for_update()
                    .filter(student=student, term=term, doc_type="HONOR")
                    .order_by("-created_at")
                    .first()
                )
            enqueue = True
            if existing:
                prev_status = existing.status
                if existing.status == "READY":
                    return Response({"id": existing.id, "status": existing.status}, status=status.HTTP_200_OK)
                if existing.status == "PENDING":
                    enqueue = False
                doc = existing
                doc.status = "PENDING"
                doc.pdf_path = ""
                doc.completed_at = None
                doc.save(update_fields=["status", "pdf_path", "completed_at"])
                if prev_status != "PENDING":
                    mark_pending(doc.id)
            else:
                doc = Document.objects.create(
                    student=student, term=term, doc_type="HONOR", status="PENDING", pdf_path="", completed_at=None
                )
                mark_pending(doc.id)

        try:
            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                res = generate_document.apply(args=[doc.id])
                pdf_url = res.get()
                return Response({"id": doc.id, "status": "READY", "pdf_url": pdf_url}, status=status.HTTP_200_OK)
            if enqueue:
                generate_document.delay(doc.id)
        except Exception as exc:
            doc.status = "FAILED"
            doc.completed_at = timezone.now()
            doc.save(update_fields=["status", "completed_at"])
            mark_failed(doc.id)
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"id": doc.id, "status": doc.status}, status=status.HTTP_202_ACCEPTED)


class DownloadDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        doc = get_object_or_404(Document, pk=pk, status="READY")
        return Response({"path": doc.pdf_path, "id": doc.id, "type": doc.doc_type})


class ResetMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reset_metrics()
        return Response({"detail": "Métriques réinitialisées"}, status=status.HTTP_200_OK)


class StreamBulletinView(APIView):
    """
    Génération éphémère : compile et stream le PDF sans le stocker ni créer de Document.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data["student_id"]
        term = serializer.validated_data["term"]
        student = get_object_or_404(Student, pk=student_id)
        term_result = TermResult.objects.filter(student=student, term=term).first()
        if not term_result:
            return Response({"detail": "TermResult manquant pour cet élève/terme."}, status=status.HTTP_400_BAD_REQUEST)

        context = build_context(Document(student=student, term=term, doc_type="BULLETIN"))
        template = settings.LATEX_TEMPLATES["BULLETIN"]
        renderer = LatexRenderer(Path(template), context)
        pdf_bytes = renderer.generate()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        filename = f"bulletin_{student_id}_{term}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class StreamHonorView(APIView):
    """
    Génération éphémère : compile et stream le PDF du tableau d'honneur sans le stocker.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data["student_id"]
        term = serializer.validated_data["term"]
        student = get_object_or_404(Student, pk=student_id)
        term_result = TermResult.objects.filter(student=student, term=term).first()
        if not term_result:
            return Response({"detail": "TermResult manquant pour cet élève/terme."}, status=status.HTTP_400_BAD_REQUEST)

        context = build_context(Document(student=student, term=term, doc_type="HONOR"))
        template = settings.LATEX_TEMPLATES["HONOR"]
        renderer = LatexRenderer(Path(template), context)
        pdf_bytes = renderer.generate()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        filename = f"honor_{student_id}_{term}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ============================
# Batch (zip) generation
# ============================


class BatchItemSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    term = serializers.ChoiceField(choices=[c[0] for c in TermResult.TERM_CHOICES])
    type = serializers.ChoiceField(choices=["BULLETIN", "HONOR"])


class BatchCreateSerializer(serializers.Serializer):
    items = serializers.ListField(child=BatchItemSerializer(), allow_empty=False)
    force_new = serializers.BooleanField(required=False, default=False)


class CreateBatchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]
        force_new = serializer.validated_data.get("force_new", False)

        batch = Batch.objects.create(status="PENDING", documents=[])
        doc_ids = []
        with transaction.atomic():
            for item in items:
                student = get_object_or_404(Student, pk=item["student_id"])
                if not TermResult.objects.filter(student=student, term=item["term"]).exists():
                    raise serializers.ValidationError(
                        {"detail": f"TermResult manquant pour l'élève {student.id} / {item['term']}"}
                    )
                doc = Document.objects.create(
                    student=student,
                    term=item["term"],
                    doc_type=item["type"],
                    status="PENDING",
                    pdf_path="",
                    completed_at=None,
                )
                doc_ids.append(doc.id)
                mark_pending(doc.id)
                if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                    generate_document.apply(args=[doc.id])
                elif not force_new:
                    generate_document.delay(doc.id)
                else:
                    generate_document.delay(doc.id)

            batch.documents = doc_ids
            batch.status = "IN_PROGRESS"
            batch.save(update_fields=["documents", "status"])

        return Response({"batch_id": batch.id, "count": len(doc_ids), "status": batch.status}, status=status.HTTP_202_ACCEPTED)


class BatchStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk)
        docs = list(Document.objects.filter(id__in=batch.documents))
        status_counts = {"READY": 0, "PENDING": 0, "FAILED": 0}
        for d in docs:
            status_counts[d.status] = status_counts.get(d.status, 0) + 1

        # update batch status
        if status_counts.get("FAILED", 0) > 0:
            batch.status = "FAILED"
        elif status_counts.get("READY", 0) == len(docs) and docs:
            batch.status = "READY"
        else:
            batch.status = "IN_PROGRESS"
        batch.save(update_fields=["status"])

        zip_url = None
        zip_path = ""
        if batch.status == "READY":
            zip_file = batch.zip_full_path()
            if not zip_file.exists():
                zip_file.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for d in docs:
                        if not d.pdf_path or not os.path.exists(d.pdf_path):
                            continue
                        arcname = os.path.basename(d.pdf_path)
                        zf.write(d.pdf_path, arcname=arcname)
                batch.zip_path = str(zip_file)
                batch.completed_at = timezone.now()
                batch.save(update_fields=["zip_path", "completed_at"])
            zip_path = str(batch.zip_full_path())
            media_url = getattr(settings, "MEDIA_URL", "").rstrip("/")
            if media_url:
                zip_url = f"{media_url}/batches/{batch.zip_full_path().name}"

        return Response(
            {
                "id": batch.id,
                "status": batch.status,
                "counts": status_counts,
                "zip_path": zip_path,
                "zip_url": zip_url,
            }
        )


class BatchDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        batch = get_object_or_404(Batch, pk=pk, status="READY")
        zip_path = batch.zip_full_path()
        if not zip_path.exists():
            return Response({"detail": "Archive manquante"}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(open(zip_path, "rb"), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{zip_path.name}"'
        return response

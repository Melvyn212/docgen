from django.db import models
from schools.models import Student, TermResult
from django.conf import settings
from pathlib import Path


class Document(models.Model):
    DOC_TYPES = [("BULLETIN", "Bulletin"), ("HONOR", "HonorBoard")]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("READY", "Ready"),
        ("FAILED", "Failed"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.CharField(max_length=2, choices=TermResult.TERM_CHOICES)
    doc_type = models.CharField(max_length=10, choices=DOC_TYPES)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PENDING")
    pdf_path = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    first_download_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.student} - {self.term}"

    class Meta:
        indexes = [
            models.Index(fields=["student", "term"], name="document_student_term_idx"),
        ]


class Batch(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In progress"),
        ("READY", "Ready"),
        ("FAILED", "Failed"),
    ]

    documents = models.JSONField(default=list)  # liste d'IDs de Document
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    zip_path = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    first_download_at = models.DateTimeField(null=True, blank=True)

    def batches_dir(self) -> Path:
        return Path(getattr(settings, "MEDIA_ROOT", Path("."))) / "batches"

    def zip_full_path(self) -> Path:
        batches_dir = self.batches_dir()
        batches_dir.mkdir(parents=True, exist_ok=True)
        return batches_dir / f"batch_{self.id}.zip"

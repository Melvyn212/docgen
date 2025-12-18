from django.contrib import admin

from .models import School, Class, Student, Subject, Grade, TermResult, FollowUp


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "academic_year")
    search_fields = ("name", "country", "academic_year")


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "school", "total_students")
    list_filter = ("school", "level")
    search_fields = ("name", "level", "school__name")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "matricule", "klass")
    search_fields = ("first_name", "last_name", "matricule", "klass__name", "klass__school__name")
    list_filter = ("klass",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "coefficient", "teacher_name", "school")
    list_filter = ("school",)
    search_fields = ("name", "teacher_name", "school__name")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "average", "appreciation")
    list_filter = ("appreciation", "subject__school")
    search_fields = ("student__first_name", "student__last_name", "subject__name")


@admin.register(TermResult)
class TermResultAdmin(admin.ModelAdmin):
    list_display = ("student", "term", "average", "rank", "honor_board")
    list_filter = ("term", "honor_board")
    search_fields = ("student__first_name", "student__last_name", "student__matricule")


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ("student", "assiduite", "ponctualite", "comportement", "participation")
    search_fields = ("student__first_name", "student__last_name", "student__matricule")

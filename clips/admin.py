from django.conf import settings
from django.contrib import admin
from django.db.models import Count

from .models import Clip, Report, ViewEvent


def report_admin_threshold() -> int:
    return int(getattr(settings, 'REPORT_ADMIN_THRESHOLD', 5))


class HighReportCountFilter(admin.SimpleListFilter):
    title = '通報数'
    parameter_name = 'report_level'

    def lookups(self, request, model_admin):
        threshold = report_admin_threshold()
        return (
            ('high', f'{threshold}件以上（要確認）'),
            ('low', f'{threshold}件未満'),
        )

    def queryset(self, request, queryset):
        threshold = report_admin_threshold()
        qs = queryset.annotate(_report_total=Count('reports', distinct=True))
        if self.value() == 'high':
            return qs.filter(_report_total__gte=threshold)
        if self.value() == 'low':
            return qs.filter(_report_total__lt=threshold)
        return queryset


class ReportInline(admin.TabularInline):
    model = Report
    extra = 0
    readonly_fields = ('reason', 'detail', 'reporter', 'created_at')
    can_delete = False


@admin.register(Clip)
class ClipAdmin(admin.ModelAdmin):
    list_display = (
        'tweet_id',
        'view_count',
        'submitted_by',
        'created_at',
        'report_count',
        'needs_review',
    )
    list_filter = (HighReportCountFilter, 'created_at')
    search_fields = ('tweet_id', 'url')
    readonly_fields = ('tweet_id', 'url', 'view_count', 'created_at')
    inlines = [ReportInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _report_total=Count('reports', distinct=True),
        )

    @admin.display(description='通報数', ordering='_report_total')
    def report_count(self, obj):
        return getattr(obj, '_report_total', obj.reports.count())

    @admin.display(description='要確認', boolean=True)
    def needs_review(self, obj):
        total = getattr(obj, '_report_total', obj.reports.count())
        return total >= report_admin_threshold()


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Only reports on clips that already have REPORT_ADMIN_THRESHOLD+ reports."""

    list_display = ('clip', 'reason', 'reporter', 'created_at', 'detail_short', 'clip_report_total')
    list_filter = ('reason', 'created_at')
    search_fields = ('clip__tweet_id', 'detail')
    raw_id_fields = ('clip', 'reporter')

    def get_queryset(self, request):
        threshold = report_admin_threshold()
        return (
            super()
            .get_queryset(request)
            .annotate(clip_report_total=Count('clip__reports', distinct=True))
            .filter(clip_report_total__gte=threshold)
        )

    @admin.display(description='詳細')
    def detail_short(self, obj):
        return (obj.detail or '')[:40]

    @admin.display(description='クリップ通報数', ordering='clip_report_total')
    def clip_report_total(self, obj):
        return getattr(obj, 'clip_report_total', obj.clip.reports.count())


@admin.register(ViewEvent)
class ViewEventAdmin(admin.ModelAdmin):
    list_display = ('clip', 'created_at')
    list_filter = ('created_at',)
    raw_id_fields = ('clip',)

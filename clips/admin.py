from django.contrib import admin

from .models import Clip, Report, ViewEvent


class ReportInline(admin.TabularInline):
    model = Report
    extra = 0
    readonly_fields = ('reason', 'detail', 'reporter', 'created_at')
    can_delete = False


@admin.register(Clip)
class ClipAdmin(admin.ModelAdmin):
    list_display = ('tweet_id', 'view_count', 'submitted_by', 'created_at', 'report_count')
    list_filter = ('created_at',)
    search_fields = ('tweet_id', 'url')
    readonly_fields = ('tweet_id', 'url', 'view_count', 'created_at')
    inlines = [ReportInline]

    @admin.display(description='通報数')
    def report_count(self, obj):
        return obj.reports.count()


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('clip', 'reason', 'reporter', 'created_at', 'detail_short')
    list_filter = ('reason', 'created_at')
    search_fields = ('clip__tweet_id', 'detail')
    raw_id_fields = ('clip', 'reporter')

    @admin.display(description='詳細')
    def detail_short(self, obj):
        return (obj.detail or '')[:40]


@admin.register(ViewEvent)
class ViewEventAdmin(admin.ModelAdmin):
    list_display = ('clip', 'created_at')
    list_filter = ('created_at',)
    raw_id_fields = ('clip',)

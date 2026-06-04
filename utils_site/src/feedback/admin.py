"""Admin for tool ratings: moderation list + per-tool quality dashboard."""

from django.contrib import admin
from django.db.models import Avg, Count
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import ToolRating


@admin.register(ToolRating)
class ToolRatingAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "tool_slug",
        "rating",
        "short_comment",
        "lang",
        "is_approved",
        "is_spam",
        "operation_link",
    )
    list_filter = (
        "tool_slug",
        "rating",
        "is_approved",
        "is_spam",
        "lang",
        "created_at",
    )
    search_fields = ("comment", "tool_slug", "session_key")
    readonly_fields = ("created_at", "updated_at", "operation_run", "ip_address")
    actions = ("approve_selected", "mark_spam")
    list_per_page = 50

    @admin.display(description="comment")
    def short_comment(self, obj):
        if not obj.comment:
            return "—"
        return obj.comment[:80] + ("…" if len(obj.comment) > 80 else "")

    @admin.display(description="operation")
    def operation_link(self, obj):
        if not obj.operation_run_id:
            return "—"
        url = reverse("admin:users_operationrun_change", args=[obj.operation_run_id])
        return format_html('<a href="{}">#{}</a>', url, obj.operation_run_id)

    @admin.action(description="Approve selected ratings")
    def approve_selected(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Mark selected as spam")
    def mark_spam(self, request, queryset):
        queryset.update(is_spam=True)

    def get_urls(self):
        return [
            path(
                "quality-dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="feedback_quality_dashboard",
            ),
        ] + super().get_urls()

    def dashboard_view(self, request):
        per_tool = (
            ToolRating.objects.values("tool_slug")
            .annotate(avg=Avg("rating"), n=Count("id"))
            .order_by("avg")
        )
        recent_low = (
            ToolRating.objects.filter(rating__lte=3)
            .select_related("operation_run")
            .order_by("-created_at")[:50]
        )
        context = {
            **self.admin_site.each_context(request),
            "title": "Tool quality dashboard",
            "per_tool": per_tool,
            "recent_low": recent_low,
        }
        return TemplateResponse(request, "admin/feedback/dashboard.html", context)

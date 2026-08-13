from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView

from .forms import ClipSubmitForm, ReportForm, SignUpForm, UsernameAuthenticationForm
from .models import Clip, Report, ViewEvent
from .x_url import embed_html


TAB_LABELS = {
    'latest': '最新',
    '24h': '24時間',
    'week': '1週間',
    'all': '歴代',
}


def _clips_for_tab(tab: str):
    now = timezone.now()
    if tab == 'latest':
        return Clip.objects.all().order_by('-created_at'), 'latest'
    if tab == '24h':
        since = now - timedelta(hours=24)
        qs = (
            Clip.objects.annotate(
                period_views=Count(
                    'view_events',
                    filter=Q(view_events__created_at__gte=since),
                )
            )
            .order_by('-period_views', '-created_at')
        )
        return qs, '24h'
    if tab == 'week':
        since = now - timedelta(days=7)
        qs = (
            Clip.objects.annotate(
                period_views=Count(
                    'view_events',
                    filter=Q(view_events__created_at__gte=since),
                )
            )
            .order_by('-period_views', '-created_at')
        )
        return qs, 'week'
    return Clip.objects.all().order_by('-view_count', '-created_at'), 'all'


def _session_view_map(request) -> dict:
    raw = request.session.get('clip_views', {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): int(v) for k, v in raw.items() if str(k).isdigit()}


def _should_count_view(request, clip_id: int) -> bool:
    """Same session cannot re-count the same clip within VIEW_DEDUP_SECONDS."""
    dedup = getattr(settings, 'VIEW_DEDUP_SECONDS', 60)
    now_ts = int(timezone.now().timestamp())
    views = _session_view_map(request)
    key = str(clip_id)
    last = views.get(key)
    if last is not None and now_ts - last < dedup:
        return False
    views[key] = now_ts
    if len(views) > 200:
        cutoff = now_ts - dedup
        views = {k: v for k, v in views.items() if v >= cutoff}
    request.session['clip_views'] = views
    request.session.modified = True
    return True


def _record_view(request, clip: Clip) -> bool:
    if not _should_count_view(request, clip.pk):
        return False
    ViewEvent.objects.create(clip=clip)
    Clip.objects.filter(pk=clip.pk).update(view_count=F('view_count') + 1)
    return True


def feed(request, tab='latest'):
    if tab not in TAB_LABELS:
        tab = 'latest'
    clips_qs, active_tab = _clips_for_tab(tab)
    clips = list(clips_qs[:50])
    report_form = ReportForm()
    for clip in clips:
        clip.embed = embed_html(clip.tweet_id, width=350)
    return render(request, 'clips/feed.html', {
        'clips': clips,
        'active_tab': active_tab,
        'tabs': TAB_LABELS,
        'report_form': report_form,
        'report_reasons': Report.Reason.choices,
    })


@require_POST
def clip_view(request, pk):
    """Record an in-app view when a clip becomes visible on the feed."""
    clip = get_object_or_404(Clip, pk=pk)
    counted = _record_view(request, clip)
    clip.refresh_from_db()
    return JsonResponse({
        'ok': True,
        'counted': counted,
        'view_count': clip.view_count,
    })


def clip_detail(request, pk):
    """Kept for direct links; main UX is feed embeds."""
    clip = get_object_or_404(Clip, pk=pk)
    _record_view(request, clip)
    clip.refresh_from_db()
    return redirect('clips:feed')


@login_required
def clip_submit(request):
    if request.method == 'POST':
        form = ClipSubmitForm(request.POST)
        if form.is_valid():
            tweet_id = form.cleaned_data['tweet_id']
            Clip.objects.create(
                url=form.cleaned_data['url'],
                tweet_id=tweet_id,
                submitted_by=request.user,
            )
            messages.success(request, 'クリップを投稿しました。')
            return redirect('clips:feed')
    else:
        form = ClipSubmitForm()
    return render(request, 'clips/submit.html', {
        'form': form,
        'tabs': TAB_LABELS,
    })


@require_POST
def clip_report(request, pk):
    clip = get_object_or_404(Clip, pk=pk)
    form = ReportForm(request.POST)
    next_url = request.POST.get('next') or reverse('clips:feed')
    if form.is_valid():
        report = form.save(commit=False)
        report.clip = clip
        if request.user.is_authenticated:
            report.reporter = request.user
        report.save()
        messages.success(request, '通報を受け付けました。確認のうえ対応します。')
    else:
        messages.error(request, '通報に失敗しました。理由を選択してください。')
    return redirect(next_url)


CONTACT_EMAIL = 'heart.appdev@gmail.com'


def _legal_context():
    return {'tabs': TAB_LABELS, 'contact_email': CONTACT_EMAIL}


def about(request):
    return render(request, 'clips/about.html', _legal_context())


def guide(request):
    return render(request, 'clips/guide.html', _legal_context())


def contact(request):
    return render(request, 'clips/contact.html', _legal_context())


def terms(request):
    return render(request, 'clips/terms.html', _legal_context())


def privacy(request):
    return render(request, 'clips/privacy.html', _legal_context())


@require_GET
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse('clips:sitemap'))
    body = '\n'.join([
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        f'Sitemap: {sitemap_url}',
        '',
    ])
    return HttpResponse(body, content_type='text/plain; charset=utf-8')


@require_GET
def sitemap_xml(request):
    paths = [
        reverse('clips:feed'),
        reverse('clips:feed_tab', kwargs={'tab': '24h'}),
        reverse('clips:feed_tab', kwargs={'tab': 'week'}),
        reverse('clips:feed_tab', kwargs={'tab': 'all'}),
        reverse('clips:about'),
        reverse('clips:guide'),
        reverse('clips:contact'),
        reverse('clips:terms'),
        reverse('clips:privacy'),
    ]
    urls_xml = []
    for path in paths:
        loc = request.build_absolute_uri(path)
        urls_xml.append(f'  <url>\n    <loc>{loc}</loc>\n  </url>')
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(urls_xml)
        + '\n</urlset>\n'
    )
    return HttpResponse(body, content_type='application/xml; charset=utf-8')


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'clips/signup.html'
    success_url = reverse_lazy('clips:feed')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, 'アカウントを作成しました。')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tabs'] = TAB_LABELS
        return ctx


class ClipsLoginView(LoginView):
    template_name = 'clips/login.html'
    authentication_form = UsernameAuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tabs'] = TAB_LABELS
        return ctx


class ClipsLogoutView(LogoutView):
    next_page = reverse_lazy('clips:feed')

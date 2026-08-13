from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Clip, Report, ViewEvent
from .x_url import extract_tweet_id, normalize_status_url


class XUrlTests(TestCase):
    def test_extract_x_url(self):
        tid = extract_tweet_id('https://x.com/someone/status/1234567890123456789')
        self.assertEqual(tid, '1234567890123456789')

    def test_extract_twitter_url_with_query(self):
        tid = extract_tweet_id(
            'https://twitter.com/someone/status/9876543210?s=20'
        )
        self.assertEqual(tid, '9876543210')

    def test_normalize(self):
        url = normalize_status_url('https://x.com/foo/status/111')
        self.assertEqual(url, 'https://x.com/i/status/111')


class ClipAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
        )

    def test_feed_public(self):
        res = self.client.get(reverse('clips:feed'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'valorant')
        self.assertContains(res, 'ランキング')
        self.assertContains(res, 'brand-valorant')

    def test_submit_requires_login(self):
        res = self.client.get(reverse('clips:submit'))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

    def test_submit_and_reject_duplicate(self):
        self.client.login(username='testuser', password='testpass123')
        url = 'https://x.com/player/status/555666777888'
        res = self.client.post(reverse('clips:submit'), {
            'url': url,
            'is_valorant': 'on',
        })
        self.assertEqual(Clip.objects.count(), 1)
        clip = Clip.objects.get()
        self.assertEqual(clip.tweet_id, '555666777888')
        self.assertRedirects(res, reverse('clips:feed'))

        res2 = self.client.post(reverse('clips:submit'), {
            'url': 'https://twitter.com/other/status/555666777888',
            'is_valorant': 'on',
        })
        self.assertEqual(Clip.objects.count(), 1)
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, '既に登録')

    def test_view_count_increments_once_per_dedup(self):
        clip = Clip.objects.create(
            url='https://x.com/i/status/1',
            tweet_id='1',
            submitted_by=self.user,
        )
        view_url = reverse('clips:view', kwargs={'pk': clip.pk})
        res1 = self.client.post(view_url)
        self.assertEqual(res1.status_code, 200)
        clip.refresh_from_db()
        self.assertEqual(clip.view_count, 1)
        self.assertEqual(ViewEvent.objects.filter(clip=clip).count(), 1)

        res2 = self.client.post(view_url)
        self.assertEqual(res2.status_code, 200)
        data = res2.json()
        self.assertFalse(data['counted'])
        clip.refresh_from_db()
        self.assertEqual(clip.view_count, 1)

    def test_feed_shows_embed_markup(self):
        Clip.objects.create(url='https://x.com/i/status/99', tweet_id='99')
        res = self.client.get(reverse('clips:feed'))
        self.assertContains(res, 'twitter-tweet')
        self.assertContains(res, 'report-toggle')
        self.assertContains(res, '通報')
        self.assertContains(res, 'embed-click-catcher')
        self.assertNotContains(res, '再生する')
        self.assertNotContains(res, '#1')

    def test_rank_shown_on_all_tab(self):
        Clip.objects.create(url='https://x.com/i/status/98', tweet_id='98')
        res = self.client.get(reverse('clips:feed_tab', kwargs={'tab': 'all'}))
        self.assertContains(res, 'class="rank"')
        self.assertContains(res, '>1<')
        self.assertNotContains(res, '#1')

    def test_feed_does_not_auto_count_views(self):
        clip = Clip.objects.create(url='https://x.com/i/status/77', tweet_id='77')
        self.client.get(reverse('clips:feed'))
        clip.refresh_from_db()
        self.assertEqual(clip.view_count, 0)
        self.assertEqual(ViewEvent.objects.filter(clip=clip).count(), 0)

    def test_hud_frame_present(self):
        Clip.objects.create(url='https://x.com/i/status/88', tweet_id='88')
        res = self.client.get(reverse('clips:feed'))
        self.assertContains(res, 'hud-frame')
        self.assertContains(res, 'theme-a')

    def test_tabs_order_all_time(self):
        c1 = Clip.objects.create(url='https://x.com/i/status/10', tweet_id='10', view_count=5)
        c2 = Clip.objects.create(url='https://x.com/i/status/20', tweet_id='20', view_count=9)
        res = self.client.get(reverse('clips:feed_tab', kwargs={'tab': 'all'}))
        self.assertEqual(res.status_code, 200)
        clips = list(res.context['clips'])
        self.assertEqual(clips[0].pk, c2.pk)
        self.assertEqual(clips[1].pk, c1.pk)

    def test_week_tab_uses_period_views(self):
        hot = Clip.objects.create(url='https://x.com/i/status/30', tweet_id='30', view_count=100)
        cold = Clip.objects.create(url='https://x.com/i/status/40', tweet_id='40', view_count=1)
        now = timezone.now()
        ViewEvent.objects.create(clip=cold, created_at=now)
        # force created_at on cold's event - auto_now_add ignores kwargs on create in some versions
        ViewEvent.objects.filter(clip=cold).update(created_at=now)
        ViewEvent.objects.create(clip=hot)
        ViewEvent.objects.filter(clip=hot).update(created_at=now - timedelta(days=10))

        res = self.client.get(reverse('clips:feed_tab', kwargs={'tab': 'week'}))
        clips = list(res.context['clips'])
        self.assertEqual(clips[0].pk, cold.pk)

    def test_report_without_login(self):
        clip = Clip.objects.create(url='https://x.com/i/status/50', tweet_id='50')
        res = self.client.post(reverse('clips:report', kwargs={'pk': clip.pk}), {
            'reason': Report.Reason.NOT_VALORANT,
            'detail': 'apex',
            'next': reverse('clips:feed'),
        })
        self.assertRedirects(res, reverse('clips:feed'))
        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(Report.objects.get().detail, 'apex')

    def test_signup_with_username(self):
        res = self.client.post(reverse('clips:signup'), {
            'username': 'newbie',
            'password1': 'complex-pass-99',
            'password2': 'complex-pass-99',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(username='newbie').exists())

    def test_signup_rejects_case_insensitive_duplicate(self):
        User.objects.create_user(username='TakenName', password='complex-pass-99')
        res = self.client.post(reverse('clips:signup'), {
            'username': 'takenname',
            'password1': 'complex-pass-99',
            'password2': 'complex-pass-99',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '既に使われています')
        self.assertEqual(User.objects.filter(username__iexact='takenname').count(), 1)

    def test_login_case_insensitive(self):
        User.objects.create_user(username='CoolPlayer', password='complex-pass-99')
        res = self.client.post(reverse('clips:login'), {
            'username': 'coolplayer',
            'password': 'complex-pass-99',
        })
        self.assertEqual(res.status_code, 302)

    def test_seo_meta_on_feed(self):
        res = self.client.get(reverse('clips:feed'))
        self.assertContains(res, 'name="description"', html=False)
        self.assertContains(res, 'ValorantのX（Twitter）クリップを視聴回数でランキング', html=False)
        self.assertContains(res, 'property="og:title"', html=False)
        self.assertContains(res, 'property="og:description"', html=False)
        self.assertContains(res, 'property="og:type"', html=False)
        self.assertContains(res, 'property="og:url"', html=False)
        self.assertContains(res, 'property="og:image"', html=False)
        self.assertContains(res, 'rel="icon"', html=False)
        self.assertContains(res, 'clips/favicon.png', html=False)
        self.assertContains(res, 'clips/og.png', html=False)

    def test_robots_txt(self):
        res = self.client.get(reverse('clips:robots'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/plain; charset=utf-8')
        self.assertIn(b'User-agent: *', res.content)
        self.assertIn(b'Disallow: /admin/', res.content)
        self.assertIn(b'Sitemap:', res.content)
        self.assertIn(b'sitemap.xml', res.content)

    def test_sitemap_xml(self):
        res = self.client.get(reverse('clips:sitemap'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('xml', res['Content-Type'])
        body = res.content.decode('utf-8')
        self.assertIn('<urlset', body)
        self.assertIn('/ranking/24h/', body)
        self.assertIn('/ranking/week/', body)
        self.assertIn('/ranking/all/', body)
        self.assertIn('/terms/', body)
        self.assertIn('/privacy/', body)


class ReportAdminThresholdTests(TestCase):
    def setUp(self):
        self.clip = Clip.objects.create(url='https://x.com/i/status/60', tweet_id='60')

    def _add_reports(self, n):
        for i in range(n):
            Report.objects.create(
                clip=self.clip,
                reason=Report.Reason.OTHER,
                detail=f'r{i}',
            )

    def test_report_admin_hides_below_threshold(self):
        from clips.admin import ReportAdmin

        self._add_reports(4)
        ma = ReportAdmin(Report, admin.site)
        qs = ma.get_queryset(request=None)
        self.assertEqual(qs.count(), 0)

    def test_report_admin_shows_at_threshold(self):
        from clips.admin import ReportAdmin

        self._add_reports(5)
        ma = ReportAdmin(Report, admin.site)
        qs = ma.get_queryset(request=None)
        self.assertEqual(qs.count(), 5)
        self.assertTrue(all(r.clip_id == self.clip.pk for r in qs))

    def test_reports_still_saved_below_threshold(self):
        self._add_reports(3)
        self.assertEqual(Report.objects.filter(clip=self.clip).count(), 3)

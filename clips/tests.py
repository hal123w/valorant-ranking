from datetime import timedelta

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
            username='user@example.com',
            email='user@example.com',
            password='testpass123',
        )

    def test_feed_public(self):
        res = self.client.get(reverse('clips:feed'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'valorantランキング')

    def test_submit_requires_login(self):
        res = self.client.get(reverse('clips:submit'))
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

    def test_submit_and_reject_duplicate(self):
        self.client.login(username='user@example.com', password='testpass123')
        url = 'https://x.com/player/status/555666777888'
        res = self.client.post(reverse('clips:submit'), {
            'url': url,
            'is_valorant': 'on',
        })
        self.assertEqual(Clip.objects.count(), 1)
        clip = Clip.objects.get()
        self.assertEqual(clip.tweet_id, '555666777888')
        self.assertRedirects(res, reverse('clips:detail', kwargs={'pk': clip.pk}))

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
        detail = reverse('clips:detail', kwargs={'pk': clip.pk})
        res1 = self.client.get(detail)
        self.assertEqual(res1.status_code, 200)
        clip.refresh_from_db()
        self.assertEqual(clip.view_count, 1)
        self.assertEqual(ViewEvent.objects.filter(clip=clip).count(), 1)

        res2 = self.client.get(detail)
        self.assertEqual(res2.status_code, 200)
        clip.refresh_from_db()
        self.assertEqual(clip.view_count, 1)

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
        })
        self.assertRedirects(res, reverse('clips:detail', kwargs={'pk': clip.pk}))
        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(Report.objects.get().detail, 'apex')

    def test_signup_with_email(self):
        res = self.client.post(reverse('clips:signup'), {
            'email': 'new@example.com',
            'password1': 'complex-pass-99',
            'password2': 'complex-pass-99',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(username='new@example.com').exists())

import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

# x.com / twitter.com / mobile.twitter.com status URLs
_STATUS_RE = re.compile(
    r'^https?://(?:www\.|mobile\.)?(?:twitter\.com|x\.com)/[^/]+/status/(\d+)',
    re.IGNORECASE,
)


def extract_tweet_id(url: str) -> str:
    """Return tweet/status id from an X/Twitter status URL."""
    text = (url or '').strip()
    match = _STATUS_RE.match(text)
    if not match:
        # Also accept URL with query/fragment by parsing path
        try:
            parsed = urlparse(text)
        except ValueError as exc:
            raise ValidationError('URLの形式が正しくありません。') from exc

        host = (parsed.netloc or '').lower()
        if host.startswith('www.'):
            host = host[4:]
        if host.startswith('mobile.'):
            host = host[7:]
        if host not in ('twitter.com', 'x.com'):
            raise ValidationError(
                'X（Twitter）の投稿URLのみ投稿できます。'
                '例: https://x.com/username/status/1234567890'
            )
        parts = [p for p in parsed.path.split('/') if p]
        if len(parts) >= 3 and parts[1].lower() == 'status' and parts[2].isdigit():
            return parts[2]
        raise ValidationError(
            'X（Twitter）の投稿URLのみ投稿できます。'
            '例: https://x.com/username/status/1234567890'
        )
    return match.group(1)


def normalize_status_url(url: str) -> str:
    """Normalize to https://x.com/i/status/<id> for stable unique storage."""
    tweet_id = extract_tweet_id(url)
    return f'https://x.com/i/status/{tweet_id}'


def embed_html(tweet_id: str) -> str:
    """Official X embed blockquote markup (widgets.js loads client-side)."""
    href = f'https://x.com/i/status/{tweet_id}'
    return (
        f'<blockquote class="twitter-tweet" data-theme="dark" data-dnt="true">'
        f'<a href="{href}"></a></blockquote>'
    )

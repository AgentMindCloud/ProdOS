"""Local, deterministic marketing draft templates (spec section 13).

Every function below takes the confirmed-data context from
``produceros.marketing.context.build_project_context`` and returns
``(title, body)``. Templates never invent streaming numbers, awards,
press coverage, collaborations, credits, achievements, or quotes -- any
field that isn't confirmed renders as ``[fill in]`` for the producer to
complete by hand. Output is always Markdown-friendly plain text and is
always saved as a *draft*; nothing here sends or publishes anything.
"""

from __future__ import annotations

from collections.abc import Callable

from produceros.models.enums import MarketingDraftType

TemplateFn = Callable[[dict], tuple[str, str]]


def _release_announcement(ctx: dict) -> tuple[str, str]:
    title = f"Release Announcement -- {ctx['title']}"
    body = f"""**{ctx['artist_name']} -- "{ctx['title']}"**

Release type: {ctx['release_type']}
Release date: {ctx['release_date']}
Genre: {ctx['genre']} ({ctx['mood']})

[Write 2-3 sentences introducing the release in your own voice -- what it is,
why you made it, what listeners should expect.]

Featuring: {ctx['featured_artists']}

Available via: {ctx['distributor']}

#NewMusic #{ctx['genre'].replace(' ', '')}
"""
    return title, body


def _instagram_caption(ctx: dict) -> tuple[str, str]:
    title = f"Instagram Caption -- {ctx['title']}"
    body = f""""{ctx['title']}" is out now. 🎧

[One or two lines about the track in your voice.]

🔗 Link in bio
🎵 {ctx['genre']} | {ctx['mood']}

#{ctx['artist_name'].replace(' ', '')} #NewRelease
"""
    return title, body


def _tiktok_caption(ctx: dict) -> tuple[str, str]:
    title = f"TikTok Caption -- {ctx['title']}"
    body = f""""{ctx['title']}" 🔥 [add a hook line here]

out now everywhere 🎧

#fyp #newmusic #{ctx['genre'].replace(' ', '')}
"""
    return title, body


def _youtube_description(ctx: dict) -> tuple[str, str]:
    title = f"YouTube Description -- {ctx['title']}"
    body = f"""{ctx['artist_name']} -- "{ctx['title']}"

[Write a short description of the track/video.]

Genre: {ctx['genre']}
Release date: {ctx['release_date']}
Stream/download: {ctx['distributor']}

Credits:
[List confirmed contributors here -- writers, producers, performers.]

#music #{ctx['genre'].replace(' ', '')}
"""
    return title, body


def _short_video_hook(ctx: dict) -> tuple[str, str]:
    title = f"Short-Video Hooks -- {ctx['title']}"
    body = f"""Hook ideas for short-form video (each needs your own footage/performance):

1. [Open on the drop of "{ctx['title']}" -- describe the visual.]
2. [Show a before/after of the {ctx['mood']} vibe of the track.]
3. [React to hearing the {ctx['bpm']} BPM {ctx['musical_key']} arrangement for the first time.]

Pick the hook that matches footage you actually have.
"""
    return title, body


def _behind_the_scenes(ctx: dict) -> tuple[str, str]:
    title = f"Behind-the-Scenes Ideas -- {ctx['title']}"
    body = f"""Behind-the-scenes content ideas for "{ctx['title']}":

- [Show the FL Studio session / arrangement view.]
- [Talk through the {ctx['genre']} sound design choices you actually made.]
- [Share one specific challenge you solved while producing this track.]

Only use footage/screens you're comfortable sharing publicly.
"""
    return title, body


def _production_breakdown(ctx: dict) -> tuple[str, str]:
    title = f"Production Breakdown Ideas -- {ctx['title']}"
    body = f"""Production breakdown outline for "{ctx['title']}":

- Tempo/key: {ctx['bpm']} BPM, {ctx['musical_key']}
- Instrumentation: {ctx['instruments']}
- Vocal style: {ctx['vocal_style']}

[Describe your actual signal chain / plugin choices / arrangement decisions.
Do not claim techniques you did not use.]
"""
    return title, body


def _email_announcement(ctx: dict) -> tuple[str, str]:
    title = f"Email Announcement -- {ctx['title']}"
    body = f"""Subject: New release: "{ctx['title']}"

Hi [name],

{ctx['artist_name']}'s new {ctx['release_type']}, "{ctx['title']}," is out {ctx['release_date']}.

[Write a short personal note about the release.]

Listen here: [add link once available]

Thanks for listening,
{ctx['artist_name']}
"""
    return title, body


def _creator_outreach(ctx: dict) -> tuple[str, str]:
    title = f"Creator Outreach -- {ctx['title']}"
    body = f"""Subject: Track for your next video -- "{ctx['title']}"

Hi [creator name],

I produce {ctx['genre']} music and think "{ctx['title']}" ({ctx['bpm']} BPM, {ctx['mood']}) could
fit your content. [Add why you think it's a fit for their specific channel.]

Happy to share a download link or discuss usage terms.

Thanks,
{ctx['artist_name']}
"""
    return title, body


def _dj_outreach(ctx: dict) -> tuple[str, str]:
    title = f"DJ Outreach -- {ctx['title']}"
    body = f"""Subject: New {ctx['genre']} track for your sets -- "{ctx['title']}"

Hi [DJ name],

Sending over "{ctx['title']}" ({ctx['bpm']} BPM, {ctx['musical_key']}) -- a {ctx['mood']} {ctx['genre']}
track I think could work in your sets. [Add specific context about their style/sets.]

Download / stems on request.

{ctx['artist_name']}
"""
    return title, body


def _playlist_outreach(ctx: dict) -> tuple[str, str]:
    title = f"Playlist Outreach -- {ctx['title']}"
    body = f"""Subject: Submission for [playlist name] -- "{ctx['title']}"

Hi [curator name],

Submitting "{ctx['title']}" by {ctx['artist_name']} for consideration.

Genre: {ctx['genre']} | Mood: {ctx['mood']} | Release date: {ctx['release_date']}
Distributor: {ctx['distributor']}

[Add one sentence on why it fits this specific playlist.]

Link: [add link once available]

Thanks for considering it,
{ctx['artist_name']}
"""
    return title, body


def _sync_pitch(ctx: dict) -> tuple[str, str]:
    title = f"Sync Pitch -- {ctx['title']}"
    body = f"""Track: "{ctx['title']}" -- {ctx['artist_name']}
Genre/mood: {ctx['genre']} / {ctx['mood']}
Tempo/key: {ctx['bpm']} BPM, {ctx['musical_key']}
Instrumentation: {ctx['instruments']}
Vocal style: {ctx['vocal_style']}
Explicit status: {ctx['explicit_status']}

Rights: [confirm master/composition owner and clearance status before sending]

[Add a one-line pitch describing the scene/placement this track suits.]

Contact: [add your contact info]
"""
    return title, body


def _press_release_outline(ctx: dict) -> tuple[str, str]:
    title = f"Press Release Outline -- {ctx['title']}"
    body = f"""FOR IMMEDIATE RELEASE

{ctx['artist_name']} Releases "{ctx['title']}"

[City, date] -- {ctx['artist_name']} today released "{ctx['title']}," a {ctx['genre']} {ctx['release_type']}
available via {ctx['distributor']}.

[Add 2-3 paragraphs: background on the artist, the making of this release,
and where to hear it. Do not include quotes, press mentions, or achievements
that have not actually happened.]

Release date: {ctx['release_date']}

Contact: [add press contact info]
"""
    return title, body


def _four_week_campaign(ctx: dict) -> tuple[str, str]:
    title = f"4-Week Campaign Plan -- {ctx['title']}"
    body = f"""4-week campaign outline for "{ctx['title']}" (release date: {ctx['release_date']}):

Week 1 (-3): Teaser content + playlist/DJ/creator outreach begins.
Week 2 (-2): Behind-the-scenes + production breakdown content.
Week 3 (-1): Final teaser, pre-save/pre-add push, press outline sent.
Week 0 (release): Release announcement across channels, email announcement.

[Fill in specific dates and assign each item to a real content asset or deadline.]
"""
    return title, body


def _six_week_campaign(ctx: dict) -> tuple[str, str]:
    title = f"6-Week Campaign Plan -- {ctx['title']}"
    body = f"""6-week campaign outline for "{ctx['title']}" (release date: {ctx['release_date']}):

Week 1 (-5): Concept/hook content, start creator outreach.
Week 2 (-4): Behind-the-scenes content.
Week 3 (-3): Production breakdown, DJ/playlist outreach.
Week 4 (-2): Press release outline sent, pre-save push begins.
Week 5 (-1): Final teaser content, email announcement drafted.
Week 0 (release): Release day push across all channels.

[Fill in specific dates and assign each item to a real content asset or deadline.]
"""
    return title, body


def _post_release_campaign(ctx: dict) -> tuple[str, str]:
    title = f"Post-Release Campaign Plan -- {ctx['title']}"
    body = f"""Post-release plan for "{ctx['title']}" (released {ctx['release_date']}):

Week 1: Thank-you post, share early listener reactions you actually received.
Week 2: Production breakdown / behind-the-scenes follow-up content.
Week 3: Remix/alternate version consideration (if applicable).
Ongoing: Monitor analytics (Analytics tab) and update this plan based on real data only.

[Fill in specific dates and content assets.]
"""
    return title, body


TEMPLATES: dict[MarketingDraftType, TemplateFn] = {
    MarketingDraftType.RELEASE_ANNOUNCEMENT: _release_announcement,
    MarketingDraftType.INSTAGRAM_CAPTION: _instagram_caption,
    MarketingDraftType.TIKTOK_CAPTION: _tiktok_caption,
    MarketingDraftType.YOUTUBE_DESCRIPTION: _youtube_description,
    MarketingDraftType.SHORT_VIDEO_HOOK: _short_video_hook,
    MarketingDraftType.BEHIND_THE_SCENES: _behind_the_scenes,
    MarketingDraftType.PRODUCTION_BREAKDOWN: _production_breakdown,
    MarketingDraftType.EMAIL_ANNOUNCEMENT: _email_announcement,
    MarketingDraftType.CREATOR_OUTREACH: _creator_outreach,
    MarketingDraftType.DJ_OUTREACH: _dj_outreach,
    MarketingDraftType.PLAYLIST_OUTREACH: _playlist_outreach,
    MarketingDraftType.SYNC_PITCH: _sync_pitch,
    MarketingDraftType.PRESS_RELEASE_OUTLINE: _press_release_outline,
    MarketingDraftType.FOUR_WEEK_CAMPAIGN: _four_week_campaign,
    MarketingDraftType.SIX_WEEK_CAMPAIGN: _six_week_campaign,
    MarketingDraftType.POST_RELEASE_CAMPAIGN: _post_release_campaign,
}

TEMPLATE_VERSION = "1"


def render(draft_type: MarketingDraftType, context: dict) -> tuple[str, str]:
    fn = TEMPLATES.get(draft_type)
    if fn is None:
        raise ValueError(f"No template registered for {draft_type}")
    return fn(context)

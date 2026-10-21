# Platform rules for titles, descriptions and hashtags

Checked on 2026-10-20. Platforms change these often; if a composer rejects
text, trust the composer and update this file and `scripts/build_report.py`.

## Limits

| Platform | Title | Main text | Visible before "more" | Hashtags |
|---|---|---|---|---|
| YouTube Shorts | 100 | Description 5,000 | ~150 chars | 3–8 here. Over 60 makes YouTube ignore all of them (older guides say 15). The first 3 show above the title. |
| TikTok | none | Caption 2,200 via API/schedulers, ~4,000 in the app | ~100–125 | 3–6. Hashtags, emoji and @mentions count toward the caption. |
| Instagram Reels | none | Caption 2,200, hashtags included | ~125 | **Max 5.** Instagram began capping hashtags at five per post in Dec 2025 (gradual rollout). |
| Facebook Reels | 255 | Post text 63,206 | ~125 on mobile | 1–3. They do little on Facebook. |

`build_report.py` enforces the hard limits plus our own targets:

| Platform | Title target | Main text target (hashtags included) |
|---|---|---|
| YouTube | 85–100 | 1,500–5,000 |
| TikTok | n/a | 1,000–2,200 (stay ≤2,200 so it also posts through schedulers) |
| Instagram | n/a | 1,800–2,200 |
| Facebook | 150–255 | 1,000+ |

## "Useful maximum": the default length rule

Titles go near the limit; long main texts carry real content. Never pad to hit a number:
YouTube treats keyword stuffing and excessive tags as spam, and only the first
~125 characters show in any feed. Structure every main text the same way:

1. **Hook line (first ~125 chars):** the most curiosity-inducing fact of the clip. This is the only part most people see.
2. **What happens:** the moment in 2–4 sentences, with names and numbers from the transcript.
3. **Context from the full video:** stakes, premise and what came before or after. This is where the extra length comes from, and it is real content.
4. **Search phrases:** work the terms people actually search ("weight loss transformation", "couple challenge") into natural sentences. TikTok and YouTube index captions.
5. **Call to action:** a question that invites comments, or "follow for part 2".
6. **Credit:** "Original video: <creator> — <title>" (plus the link on YouTube). Clipping without credit looks like stolen content.
7. **Hashtags** go last. `build_report.py` appends them; never type them into the text yourself.

Platform tone:
- **YouTube:** the title is a headline with the hook in the first ~40 chars (mobile cuts there). The description is the most "article-like" of the four. No `<` or `>` anywhere, because YouTube rejects them.
- **TikTok:** conversational, short paragraphs, keyword-rich (TikTok search). Emoji are fine sparingly; each counts as 2.
- **Instagram:** line breaks between short paragraphs, and ask people to save or share. Only 5 hashtags, so make each count.
- **Facebook:** the title reads like a story headline. Write the description as you would tell the story to a friend, ending with a question to drive comments.

## Hashtags

There is no free source of live hashtag volume. TikTok Creative Center shows only the top 3
without logging in, and those are usually branded contests. Never claim a tag is "trending" unless a source
you actually read says so. Build each set from:

- **1 creator or brand tag** when it fits (#MrBeast). Keep proper names as they are, in any language.
- **1–2 broad high-volume tags** for the topic (#weightloss, #fitness, #podcast).
- **2–3 specific tags** for this exact moment (#weightlossjourney, #couplegoals, #fearofheights).
- Tags in the **output language**. A Spanish clip uses #bajardepeso, not #weightloss.
- No filler tags (#fyp, #viral, #foryou): no measurable reach, and on YouTube they read as spam.

Before writing, run one web search for current tags in the topic and output language
("trending hashtags <topic> <platform> <month year>"), and prefer tags that several sources agree on.
If the user is logged in to TikTok Creative Center in the browser, its hashtag list
filtered by industry and region is the best source. Do not log in for them.

## Sources (2026-10-20)

- Instagram 5-hashtag cap: https://www.socialsamosa.com/news-2/instagram-hashtags-five-per-post-10923075 · caption limit: https://www.sendible.com/insights/instagram-character-limit
- TikTok caption limits: https://www.socialync.io/blog/social-media-platform-limits-guide-2026 · https://recurpost.com/tiktok-scheduler/tiktok-character-limits-and-hashtags/
- Facebook Reels title/caption: https://docs.upload-post.com/resources/character-limits · https://kompozy.io/specs/facebook-reels-caption-character-limit
- YouTube limits and hashtags: https://hashtagtools.io/blog/youtube-shorts-character-limits-title-description-hashtags-2026 · https://touhfa.art/blog/seo/youtube-hashtags-guide/
- YouTube search filters (for research): https://9to5google.com/2026/01/08/youtube-search-filters/

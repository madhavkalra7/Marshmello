import json
import os
import time
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from datetime import timedelta

import yt_dlp
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from youtube_search import YoutubeSearch

from .ai.ai_client import AIClientError, MarshmelloAIClient
from .models import ai_generated_playlist, listening_analytics, playlist_song, playlist_user


with open(os.path.join(settings.BASE_DIR, "card.json"), "r", encoding="utf-8") as f:
    CONTAINER = json.load(f)


CURATED_CATEGORY_QUERIES = {
    "Haryanvi": [
        "latest haryanvi songs",
        "masoom sharma songs",
        "dhanda nyoliwala songs",
    ],
    "Punjabi": [
        "latest punjabi songs",
        "karan aujla songs",
        "diljit dosanjh songs",
        "shubh punjabi songs",
    ],
    "Bhakti": [
        "hanuman bhajan",
        "krishna bhajan",
        "shiv bhajan",
        "ram bhajan",
    ],
}
CURATED_BUCKET_CACHE = {"Haryanvi": [], "Punjabi": [], "Bhakti": []}
CURATED_BUCKET_CACHE_TS = 0
CURATED_BUCKET_CACHE_TTL_SECONDS = 6 * 60 * 60
AUDIO_URL_CACHE = {}
AUDIO_URL_CACHE_TTL_SECONDS = 12 * 60
AI_CLIENT = None


def _song_from_search_result(search_item):
    video_id = (search_item.get("id") or "").strip()
    if not video_id:
        return None

    thumbnails = search_item.get("thumbnails") or []
    thumbnail = thumbnails[0] if thumbnails else f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    title = (search_item.get("title") or "Untitled Song").strip()
    channel = (search_item.get("channel") or "Unknown Artist").strip()

    return [thumbnail, title, channel, video_id]


def _song_from_search_result_dict(search_item):
    song = _song_from_search_result(search_item)
    if song is None:
        return None

    return {
        "thumbnail": song[0],
        "title": song[1],
        "channel": song[2],
        "id": song[3],
    }


def _dedupe_songs_by_video_id(songs):
    unique_songs = []
    seen_video_ids = set()

    for song in songs:
        if len(song) < 4:
            continue
        video_id = str(song[3]).strip()
        if not video_id or video_id in seen_video_ids:
            continue
        seen_video_ids.add(video_id)
        unique_songs.append(song)

    return unique_songs


def _get_curated_bucket_songs():
    global CURATED_BUCKET_CACHE
    global CURATED_BUCKET_CACHE_TS

    now = int(time.time())
    if now - CURATED_BUCKET_CACHE_TS <= CURATED_BUCKET_CACHE_TTL_SECONDS and any(CURATED_BUCKET_CACHE.values()):
        return CURATED_BUCKET_CACHE

    fetched = {"Haryanvi": [], "Punjabi": [], "Bhakti": []}

    for bucket_name, queries in CURATED_CATEGORY_QUERIES.items():
        bucket_songs = []
        for query in queries:
            try:
                search_results = YoutubeSearch(query, max_results=8).to_dict()
            except Exception:
                continue

            for search_item in search_results:
                song = _song_from_search_result(search_item)
                if song is not None:
                    bucket_songs.append(song)

            bucket_songs = _dedupe_songs_by_video_id(bucket_songs)
            if len(bucket_songs) >= 18:
                break

        fetched[bucket_name] = bucket_songs[:18]

    CURATED_BUCKET_CACHE = fetched
    CURATED_BUCKET_CACHE_TS = now
    return CURATED_BUCKET_CACHE


def _bucket_name(song, source_name):
    title = str(song[1]).lower() if len(song) > 1 else ""
    artist = str(song[2]).lower() if len(song) > 2 else ""
    text = f"{title} {artist}"
    source = (source_name or "").strip().lower()

    haryanvi_keywords = [
        "dhanda nyoliwala", "masoom sharma", "haryanvi", "haryanavi", "renuka panwar", "sapna"
    ]
    punjabi_keywords = [
        "punjabi", "karan aujla", "diljit", "ap dhillon", "shubh", "sidhu moose wala", "gippy", "jass"
    ]
    bhakti_keywords = [
        "bhakti", "bhajan", "aarti", "hanuman", "shiv", "krishna", "ram", "mahadev", "devotional"
    ]

    if any(keyword in text for keyword in bhakti_keywords):
        return "Bhakti"
    if any(keyword in text for keyword in haryanvi_keywords):
        return "Haryanvi"
    if any(keyword in text for keyword in punjabi_keywords):
        return "Punjabi"
    if "bhakti" in source or "bhajan" in source:
        return "Bhakti"
    if "punjabi" in source:
        return "Punjabi"
    if "haryanvi" in source:
        return "Haryanvi"
    if source == "spanish":
        return "Spanish"
    return "English"


def _build_home_container(container):
    buckets = {
        "Haryanvi": [],
        "Punjabi": [],
        "English": [],
        "Bhakti": [],
        "Spanish": [],
    }

    for playlist in container:
        source_name = playlist[0] if len(playlist) > 0 else ""
        songs = playlist[1] if len(playlist) > 1 else []
        for song in songs:
            bucket = _bucket_name(song, source_name)
            buckets[bucket].append(song)

    curated_buckets = _get_curated_bucket_songs()
    for bucket_name in ["Haryanvi", "Punjabi", "Bhakti"]:
        buckets[bucket_name].extend(curated_buckets.get(bucket_name, []))

    for bucket_name in buckets.keys():
        buckets[bucket_name] = _dedupe_songs_by_video_id(buckets[bucket_name])

    ordered = [
        ["Haryanvi", buckets["Haryanvi"], "haryanvi"],
        ["Punjabi", buckets["Punjabi"], "punjabi"],
        ["English", buckets["English"], "english"],
        ["Bhakti", buckets["Bhakti"], "bhakti"],
    ]

    if buckets["Spanish"]:
        ordered.append(["Spanish", buckets["Spanish"], "spanish"])

    return ordered


def _get_ai_client():
    global AI_CLIENT
    if AI_CLIENT is None:
        AI_CLIENT = MarshmelloAIClient()
    return AI_CLIENT


def _current_playlist_user(request):
    return playlist_user.objects.get_or_create(username=str(request.user))[0]


def _liked_song_ids_for_user(cur_user):
    return list(
        cur_user.playlist_song_set.values_list("song_youtube_id", flat=True)
    )


def _request_data(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads((request.body or b"{}").decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST


def _search_songs(query, max_results=10):
    query = (query or "").strip()
    if not query:
        return []

    try:
        search_results = YoutubeSearch(query, max_results=max_results).to_dict()
    except Exception:
        return []

    songs = []
    seen = set()
    for item in search_results:
        song = _song_from_search_result_dict(item)
        if song is None:
            continue
        if song["id"] in seen:
            continue
        seen.add(song["id"])
        songs.append(song)
    return songs


def _group_search_cards(song_list):
    return [song_list[:10:2], song_list[1:10:2]]


def _fallback_command_parse(command_text):
    text = str(command_text or "").strip().lower()
    if not text:
        return {"action": "unknown", "confidence": 0.0, "reason": "Empty command."}

    rules = [
        ("pause", ["pause", "stop"]),
        ("play_next", ["next", "skip"]),
        ("play_previous", ["previous", "back", "restart"]),
        ("repeat", ["repeat", "replay"]),
        ("play_similar", ["similar", "related"]),
        ("toggle_like", ["like", "favorite", "favourite", "heart"]),
        ("play", ["play", "resume", "start"]),
    ]

    for action, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return {"action": action, "confidence": 0.72, "reason": "Fallback parser rule matched."}

    return {"action": "unknown", "confidence": 0.35, "reason": "Fallback parser could not infer action."}

def default(request):
    global CONTAINER
    if request.user.is_anonymous:
        return redirect('/login')

    if request.method == "POST":
        add_playlist(request)
        return HttpResponse("")

    song = "kSFJGEHDCrQ"
    home_container = _build_home_container(CONTAINER)
    cur_user = _current_playlist_user(request)
    liked_song_ids = _liked_song_ids_for_user(cur_user)
    return render(
        request,
        "player.html",
        {
            "CONTAINER": home_container,
            "song": song,
            "liked_song_ids_json": json.dumps(liked_song_ids),
        },
    )

def signup(request):
    context = {"username": True, "email": True}
    if not request.user.is_anonymous:
        return redirect("/")
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if (username,) in User.objects.values_list("username"):
            context["username"] = False
            return render(request, "signup.html", context)

        if (email,) in User.objects.values_list("email"):
            context["email"] = False
            return render(request, "signup.html", context)

        playlist_user.objects.create(username=username)
        new_user = User.objects.create_user(username, email, password)
        new_user.save()
        login(request, new_user)
        return redirect("/")
    return render(request, "signup.html", context)


def login_auth(request):
    if not request.user.is_anonymous:
        return redirect("/")
    if request.method == "POST":
        identifier = (request.POST.get("username") or "").strip()
        password = request.POST.get("password")

        user = authenticate(username=identifier, password=password)

        if user is None and identifier:
            email_user = User.objects.filter(email__iexact=identifier).first()
            if email_user is not None:
                user = authenticate(username=email_user.username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            context = {"case": False}
            return render(request, "login.html", context)

    context = {"case": True}
    return render(request, "login.html", context)



def logout_auth(request):
    logout(request)
    return redirect("/login")


def _extract_playable_audio_url(video_id):
    cached_entry = AUDIO_URL_CACHE.get(video_id)
    now = int(time.time())
    if cached_entry and cached_entry.get("expires_at", 0) > now:
        return cached_entry.get("url")

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_retries": 3,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.youtube.com/",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=False
        )

    if info is None:
        raise Exception("Could not fetch stream details")

    if isinstance(info, dict) and "entries" in info:
        info = next((entry for entry in (info.get("entries") or []) if entry), None) or {}

    direct_url = (info or {}).get("url")
    if direct_url:
        AUDIO_URL_CACHE[video_id] = {
            "url": direct_url,
            "expires_at": now + AUDIO_URL_CACHE_TTL_SECONDS,
        }
        return direct_url

    formats = (info or {}).get("formats") or []
    playable_audio_formats = [
        fmt for fmt in formats if fmt.get("url") and fmt.get("acodec") not in (None, "none")
    ]
    if playable_audio_formats:
        playable_audio_formats.sort(
            key=lambda fmt: (
                fmt.get("abr") or 0,
                fmt.get("asr") or 0,
                fmt.get("filesize") or 0,
            ),
            reverse=True,
        )
        best_url = playable_audio_formats[0]["url"]
        AUDIO_URL_CACHE[video_id] = {
            "url": best_url,
            "expires_at": now + AUDIO_URL_CACHE_TTL_SECONDS,
        }
        return best_url

    raise Exception("No playable audio URL found")

def get_audio_url(request, video_id):
    try:
        return JsonResponse({"url": _extract_playable_audio_url(video_id)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_audio_stream(request, video_id):
    upstream_response = None
    try:
        audio_url = _extract_playable_audio_url(video_id)

        upstream_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://www.youtube.com/",
        }
        incoming_range = request.headers.get("Range")
        if incoming_range:
            upstream_headers["Range"] = incoming_range

        upstream_request = urllib_request.Request(audio_url, headers=upstream_headers)
        upstream_response = urllib_request.urlopen(upstream_request, timeout=20)

        response_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Range",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Accept-Ranges": "bytes",
        }

        content_length = upstream_response.headers.get("Content-Length")
        content_range = upstream_response.headers.get("Content-Range")
        content_type = upstream_response.headers.get("Content-Type") or "audio/mpeg"
        if content_length:
            response_headers["Content-Length"] = content_length
        if content_range:
            response_headers["Content-Range"] = content_range

        status_code = getattr(upstream_response, "status", 200)

        def generate():
            try:
                while True:
                    chunk = upstream_response.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                upstream_response.close()

        return StreamingHttpResponse(
            generate(),
            status=status_code,
            content_type=content_type,
            headers=response_headers,
        )
    except HTTPError as e:
        error_msg = f"Upstream HTTP Error {e.code}: {e.reason}"
        print(f"Exception in get_audio_stream: {error_msg}")
        return HttpResponse(error_msg, status=e.code, content_type="text/plain")
    except URLError as e:
        error_msg = f"Upstream URL Error: {e.reason}"
        print(f"Exception in get_audio_stream: {error_msg}")
        return HttpResponse(error_msg, status=502, content_type="text/plain")
    except Exception as e:
        error_msg = str(e)
        print(f"Exception in get_audio_stream: {error_msg}")
        return HttpResponse(error_msg, status=500, content_type='text/plain')


def playlist(request):
    if request.user.is_anonymous:
        return redirect("/login")
    cur_user = _current_playlist_user(request)

    try:
        song_id = (request.GET.get("song_id") or "").strip()
        song_title = (request.GET.get("song") or "").strip()
        if song_id:
            cur_user.playlist_song_set.filter(song_youtube_id=song_id).delete()
        elif song_title:
            cur_user.playlist_song_set.filter(song_title=song_title).delete()
    except Exception:
        pass

    if request.method == "POST":
        add_playlist(request)
        return HttpResponse("")

    song = "kSFJGEHDCrQ"
    user_playlist = cur_user.playlist_song_set.all()
    liked_song_ids = _liked_song_ids_for_user(cur_user)
    recent_ai_playlists = ai_generated_playlist.objects.filter(user=cur_user)[:8]
    return render(
        request,
        "playlist.html",
        {
            "song": song,
            "user_playlist": user_playlist,
            "recent_ai_playlists": recent_ai_playlists,
            "liked_song_ids_json": json.dumps(liked_song_ids),
        },
    )


def search(request):
    if request.user.is_anonymous:
        return redirect("/login")

    if request.method == "POST":
        add_playlist(request)
        return HttpResponse("")

    query = (request.GET.get("search") or "").strip()
    if not query:
        return redirect("/")

    songs = _search_songs(query, max_results=10)
    song_li = _group_search_cards(songs)
    default_song = song_li[0][0]["id"] if song_li and song_li[0] else "kSFJGEHDCrQ"

    cur_user = _current_playlist_user(request)
    liked_song_ids = _liked_song_ids_for_user(cur_user)
    return render(
        request,
        "search.html",
        {
            "CONTAINER": song_li,
            "song": default_song,
            "search_query": query,
            "liked_song_ids_json": json.dumps(liked_song_ids),
        },
    )


@require_http_methods(["POST"])
def toggle_like(request):
    if request.user.is_anonymous:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    payload = _request_data(request)
    song_id = str(payload.get("songid") or payload.get("song_id") or "").strip()
    if not song_id:
        return JsonResponse({"ok": False, "error": "Missing song id"}, status=400)

    cur_user = _current_playlist_user(request)
    existing_song = cur_user.playlist_song_set.filter(song_youtube_id=song_id).first()
    if existing_song is not None:
        existing_song.delete()
        return JsonResponse({"ok": True, "liked": False, "song_id": song_id})

    title = str(payload.get("title") or "Untitled Song").strip()[:200]
    channel = str(payload.get("channel") or "Unknown Artist").strip()[:100]
    duration = str(payload.get("duration") or "00:00").strip()[:7]
    date = str(payload.get("date") or timezone.now().strftime("%d/%m/%Y")).strip()[:12]

    album_src = ""
    try:
        songdic = (YoutubeSearch(title or song_id, max_results=1).to_dict())[0]
        thumbs = songdic.get("thumbnails") or []
        album_src = thumbs[0] if thumbs else f"https://img.youtube.com/vi/{song_id}/mqdefault.jpg"
    except Exception:
        album_src = f"https://img.youtube.com/vi/{song_id}/mqdefault.jpg"

    cur_user.playlist_song_set.create(
        song_title=title,
        song_dur=duration,
        song_albumsrc=album_src,
        song_channel=channel,
        song_date_added=date,
        song_youtube_id=song_id,
    )
    return JsonResponse({"ok": True, "liked": True, "song_id": song_id})


@require_http_methods(["POST"])
def ai_chat(request):
    if request.user.is_anonymous:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    payload = _request_data(request)
    prompt = str(payload.get("prompt") or payload.get("query") or "").strip()
    if not prompt:
        return JsonResponse({"ok": False, "error": "Prompt is required"}, status=400)

    try:
        structured = _get_ai_client().build_music_chat_query(prompt)
    except AIClientError as exc:
        structured = {"query": prompt, "mood": "mixed", "genre": "mixed"}
    except Exception:
        structured = {"query": prompt, "mood": "mixed", "genre": "mixed"}

    songs = _search_songs(structured["query"], max_results=12)
    return JsonResponse(
        {
            "ok": True,
            "input": prompt,
            "structured": structured,
            "songs": songs,
        }
    )


@require_http_methods(["POST"])
def ai_playlist(request):
    if request.user.is_anonymous:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    payload = _request_data(request)
    prompt = str(payload.get("prompt") or "").strip()
    save_playlist = str(payload.get("save") or "false").lower() in {"1", "true", "yes"}
    if not prompt:
        return JsonResponse({"ok": False, "error": "Prompt is required"}, status=400)

    try:
        generated = _get_ai_client().build_smart_playlist(prompt)
    except AIClientError as exc:
        generated = {
            "title": "Smart Playlist",
            "description": f"Generated from: {prompt}",
            "queries": [prompt],
        }
    except Exception:
        generated = {
            "title": "AI Playlist",
            "description": f"Generated from: {prompt}",
            "queries": [prompt],
        }

    playlist_items = []
    aggregated = []
    seen = set()
    for query in generated["queries"][:6]:
        songs = _search_songs(query, max_results=4)
        playlist_items.append({"query": query, "songs": songs})
        for song in songs:
            sid = song["id"]
            if sid in seen:
                continue
            seen.add(sid)
            aggregated.append(song)

    saved_id = None
    if save_playlist:
        cur_user = _current_playlist_user(request)
        created = ai_generated_playlist.objects.create(
            user=cur_user,
            prompt=prompt,
            title=generated["title"],
            description=generated["description"],
            queries=generated["queries"],
        )
        saved_id = created.id

    return JsonResponse(
        {
            "ok": True,
            "input": prompt,
            "playlist": generated,
            "items": playlist_items,
            "songs": aggregated,
            "saved_id": saved_id,
        }
    )


@require_http_methods(["POST"])
def ai_command(request):
    if request.user.is_anonymous:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    payload = _request_data(request)
    command = str(payload.get("command") or payload.get("prompt") or "").strip()
    if not command:
        return JsonResponse({"ok": False, "error": "Command is required"}, status=400)

    try:
        parsed = _get_ai_client().parse_player_command(command)
    except AIClientError as exc:
        parsed = _fallback_command_parse(command)
    except Exception:
        parsed = {"action": "unknown", "confidence": 0.0, "reason": "Fallback parser used."}

    return JsonResponse({"ok": True, "input": command, "parsed": parsed})


@require_http_methods(["POST"])
def ai_search(request):
    if request.user.is_anonymous:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    payload = _request_data(request)
    prompt = str(payload.get("prompt") or payload.get("query") or "").strip()
    if not prompt:
        return JsonResponse({"ok": False, "error": "Query is required"}, status=400)

    try:
        plan = _get_ai_client().build_hybrid_search_plan(prompt)
    except AIClientError as exc:
        plan = {
            "keyword_query": prompt,
            "semantic_query": prompt,
            "mood": "any",
            "genre": "any",
            "era": "any",
        }
    except Exception:
        plan = {
            "keyword_query": prompt,
            "semantic_query": prompt,
            "mood": "any",
            "genre": "any",
            "era": "any",
        }

    keyword_results = _search_songs(plan["keyword_query"], max_results=8)
    semantic_results = _search_songs(plan["semantic_query"], max_results=8)

    merged = []
    seen = set()
    for source, bucket in (("keyword", keyword_results), ("semantic", semantic_results)):
        for song in bucket:
            sid = song["id"]
            if sid in seen:
                continue
            seen.add(sid)
            merged.append(
                {
                    "id": sid,
                    "title": song["title"],
                    "channel": song["channel"],
                    "thumbnail": song["thumbnail"],
                    "source": source,
                }
            )

    return JsonResponse(
        {
            "ok": True,
            "input": prompt,
            "plan": plan,
            "keyword_results": keyword_results,
            "semantic_results": semantic_results,
            "results": merged,
        }
    )


@require_http_methods(["POST"])
def analytics_track(request):
    if request.user.is_anonymous:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    payload = _request_data(request)
    cur_user = _current_playlist_user(request)

    song_id = str(payload.get("song_id") or payload.get("songid") or "").strip()
    title = str(payload.get("title") or "").strip()
    genre = str(payload.get("genre") or "unknown").strip() or "unknown"
    mood = str(payload.get("mood") or "unknown").strip() or "unknown"
    event_type = str(payload.get("event_type") or listening_analytics.EVENT_PLAY).strip()

    try:
        listen_seconds = int(float(payload.get("listen_seconds") or 0))
    except (TypeError, ValueError):
        listen_seconds = 0

    if event_type not in {
        listening_analytics.EVENT_PLAY,
        listening_analytics.EVENT_COMPLETE,
        listening_analytics.EVENT_SKIP,
    }:
        event_type = listening_analytics.EVENT_PLAY

    listening_analytics.objects.create(
        user=cur_user,
        song_youtube_id=song_id,
        song_title=title,
        genre=genre,
        mood=mood,
        listen_seconds=max(0, listen_seconds),
        event_type=event_type,
    )

    return JsonResponse({"ok": True})


def analytics_dashboard(request):
    if request.user.is_anonymous:
        return redirect("/login")

    cur_user = _current_playlist_user(request)
    events = listening_analytics.objects.filter(user=cur_user)

    top_genres_qs = (
        events.values("genre")
        .annotate(count=Count("id"))
        .order_by("-count")[:6]
    )
    top_genres = [item["genre"] for item in top_genres_qs]
    top_genres_counts = [item["count"] for item in top_genres_qs]

    now = timezone.now()
    last_week = now - timedelta(days=6)
    weekly_qs = (
        events.filter(created_at__date__gte=last_week.date())
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(play_count=Count("id"), seconds=Sum("listen_seconds"))
        .order_by("day")
    )

    weekly_labels = [item["day"].strftime("%a") for item in weekly_qs]
    weekly_play_counts = [item["play_count"] for item in weekly_qs]
    weekly_seconds = [int(item["seconds"] or 0) for item in weekly_qs]

    total_plays = events.count()
    total_seconds = int(events.aggregate(total=Sum("listen_seconds"))["total"] or 0)
    top_songs = (
        events.exclude(song_title="")
        .values("song_title")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )

    context = {
        "song": "kSFJGEHDCrQ",
        "top_genres": top_genres_qs,
        "top_songs": top_songs,
        "total_plays": total_plays,
        "total_seconds": total_seconds,
        "top_genres_labels_json": json.dumps(top_genres),
        "top_genres_counts_json": json.dumps(top_genres_counts),
        "weekly_labels_json": json.dumps(weekly_labels),
        "weekly_play_counts_json": json.dumps(weekly_play_counts),
        "weekly_seconds_json": json.dumps(weekly_seconds),
        "liked_song_ids_json": json.dumps(_liked_song_ids_for_user(cur_user)),
    }
    return render(request, "analytics.html", context)




def add_playlist(request):
    if request.user.is_anonymous:
        return False

    cur_user = _current_playlist_user(request)
    song_id = str(request.POST.get("songid") or "").strip()
    title = str(request.POST.get("title") or "").strip()
    if not song_id:
        return False

    if cur_user.playlist_song_set.filter(song_youtube_id=song_id).exists():
        return False

    album_src = f"https://img.youtube.com/vi/{song_id}/mqdefault.jpg"
    try:
        songdic = (YoutubeSearch(title or song_id, max_results=1).to_dict())[0]
        thumbs = songdic.get("thumbnails") or []
        if thumbs:
            album_src = thumbs[0]
    except Exception:
        pass

    cur_user.playlist_song_set.create(
        song_title=(title or "Untitled Song")[:200],
        song_dur=str(request.POST.get("duration") or "00:00")[:7],
        song_albumsrc=album_src,
        song_channel=str(request.POST.get("channel") or "Unknown Artist")[:100],
        song_date_added=str(request.POST.get("date") or timezone.now().strftime("%d/%m/%Y"))[:12],
        song_youtube_id=song_id,
    )
    return True

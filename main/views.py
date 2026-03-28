from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import playlist_user
from django.urls.base import reverse
from django.contrib.auth import authenticate,login,logout
from youtube_search import YoutubeSearch
import json
import os
import time
from django.conf import settings
from django.http import JsonResponse
import yt_dlp
# import cardupdate



with open(os.path.join(settings.BASE_DIR, 'card.json'), 'r') as f:
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


def _song_from_search_result(search_item):
    video_id = (search_item.get("id") or "").strip()
    if not video_id:
        return None

    thumbnails = search_item.get("thumbnails") or []
    thumbnail = thumbnails[0] if thumbnails else f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
    title = (search_item.get("title") or "Untitled Song").strip()
    channel = (search_item.get("channel") or "Unknown Artist").strip()

    return [thumbnail, title, channel, video_id]


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

def default(request):
    global CONTAINER
    if request.user.is_anonymous:
        return redirect('/login')

    if request.method == 'POST':

        add_playlist(request)
        return HttpResponse("")

    song = 'kSFJGEHDCrQ'
    home_container = _build_home_container(CONTAINER)
    return render(request, 'player.html',{'CONTAINER':home_container, 'song':song})

def signup(request):
    context= {'username':True,'email':True}
    if not request.user.is_anonymous:
        return redirect('/')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if (username,) in User.objects.values_list("username",) :
            context['username'] = False
            return render(request,'signup.html',context)

        elif (email,) in User.objects.values_list("email",):
            context['email'] = False
            return render(request,'signup.html',context)

        playlist_user.objects.create(username=username)
        new_user = User.objects.create_user(username,email,password)
        new_user.save()
        login(request,new_user)
        return redirect('/')
    return render(request,'signup.html',context)


def login_auth(request):
    if not request.user.is_anonymous:
        return redirect('/')
    if request.method == 'POST':
        identifier = (request.POST.get('username') or '').strip()
        password = request.POST.get('password')
        # print(User.objects.values_list("password",))

        user = authenticate(username=identifier, password=password)

        # Fallback: allow login via email as well.
        if user is None and identifier:
            email_user = User.objects.filter(email__iexact=identifier).first()
            if email_user is not None:
                user = authenticate(username=email_user.username, password=password)

        if user is not None:
            # A backend authenticated the credentials
            login(request,user)
            return redirect('/')

        else:
            # No backend authenticated the credentials
            context= {'case':False}
            return render(request,'login.html',context)


    context= {'case':True}
    return render(request,'login.html',context)



def logout_auth(request):
    logout(request)
    return redirect('/login')

def get_audio_url(request, video_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
            url = info['url']
        return JsonResponse({'url': url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def playlist(request):
    if request.user.is_anonymous:
        return redirect('/login')
    cur_user = playlist_user.objects.get(username = request.user)
    try:
      song = request.GET.get('song')
      song = cur_user.playlist_song_set.get(song_title=song)
      song.delete()
    except:
      pass
    if request.method == 'POST':
        add_playlist(request)
        return HttpResponse("")
    song = 'kSFJGEHDCrQ'
    user_playlist = cur_user.playlist_song_set.all()
    # print(list(playlist_row)[0].song_title)
    return render(request, 'playlist.html', {'song':song,'user_playlist':user_playlist})


def search(request):
  if request.method == 'POST':

    add_playlist(request)
    return HttpResponse("")
  try:
    search = request.GET.get('search')
    song = YoutubeSearch(search, max_results=10).to_dict()
    song_li = [song[:10:2],song[1:10:2]]
    # print(song_li)
  except:
    return redirect('/')

  return render(request, 'search.html', {'CONTAINER': song_li, 'song':song_li[0][0]['id']})




def add_playlist(request):
    cur_user = playlist_user.objects.get(username = request.user)

    if (request.POST['title'],) not in cur_user.playlist_song_set.values_list('song_title', ):

        songdic = (YoutubeSearch(request.POST['title'], max_results=1).to_dict())[0]
        song__albumsrc=songdic['thumbnails'][0]
        cur_user.playlist_song_set.create(song_title=request.POST['title'],song_dur=request.POST['duration'],
        song_albumsrc = song__albumsrc,
        song_channel=request.POST['channel'], song_date_added=request.POST['date'],song_youtube_id=request.POST['songid'])

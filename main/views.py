from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import playlist_user
from django.urls.base import reverse
from django.contrib.auth import authenticate,login,logout
from youtube_search import YoutubeSearch
import json
import os
from django.conf import settings
from django.http import JsonResponse
import yt_dlp
# import cardupdate



with open(os.path.join(settings.BASE_DIR, 'card.json'), 'r') as f:
    CONTAINER = json.load(f)


def _bucket_name(song, source_name):
    title = str(song[1]).lower() if len(song) > 1 else ""
    artist = str(song[2]).lower() if len(song) > 2 else ""
    text = f"{title} {artist}"
    source = (source_name or "").strip().lower()

    haryanvi_keywords = [
        "dhanda nyoliwala", "masoom sharma", "haryanvi", "haryanavi"
    ]
    punjabi_keywords = [
        "punjabi", "karan aujla", "diljit", "ap dhillon"
    ]
    bhakti_keywords = [
        "bhakti", "bhajan", "aart", "aarti", "hanuman", "shiv", "krishna", "ram"
    ]

    if any(keyword in text for keyword in bhakti_keywords):
        return "Bhakti"
    if any(keyword in text for keyword in haryanvi_keywords):
        return "Haryanvi"
    if any(keyword in text for keyword in punjabi_keywords):
        return "Punjabi"
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

    ordered = [
        ["Haryanvi", buckets["Haryanvi"], ""],
        ["Punjabi", buckets["Punjabi"], ""],
        ["English", buckets["English"], ""],
        ["Bhakti", buckets["Bhakti"], ""],
    ]

    if buckets["Spanish"]:
        ordered.append(["Spanish", buckets["Spanish"], ""])

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

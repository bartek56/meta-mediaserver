from __future__ import unicode_literals
import sys
import getopt
import youtube_dl
import os
import warnings
import metadata_mp3
from datetime import datetime
from configparser import ConfigParser


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

CONFIG_FILE='/etc/mediaserver/youtubedl.ini'

f = open("/etc/mediaserver/minidlna.conf","r")
content = f.readlines()

for x in content:
    if "media_dir=A" in x:
        parameter = x.split("A,")
        musicPath = parameter[1]
        musicPath=musicPath.replace('\n','')
        musicPath=musicPath.replace('\r','')
        PLAYLISTS_PATH="%s/Youtube list/"%(musicPath)

# tests path
#PLAYLISTS_PATH='/tmp/music/Youtube list/'
#CONFIG_FILE='/etc/mediaserver/youtubedl_test.ini'

def update_metadata_from_YTplaylist(url, playlistName):
    path=PLAYLISTS_PATH+playlistName
    albumName="YT "+playlistName
    if not os.path.exists(path):
        os.makedirs(path)
    trackNumber = len([f for f in os.listdir(path) if f.endswith('.mp3')])

    ydl_opts = {
            'addmetadata': True,
            }  
    results = youtube_dl.YoutubeDL(ydl_opts).extract_info(url,download=False)
    if not results:
       warningInfo="ERROR: not extract_info in results"
       print (bcolors.FAIL + warningInfo + bcolors.ENDC)
       return
   
    artistList = []
    playlistIndexList = []
    songsTitleList = []
    for i in results['entries']:
        
        playlistIndexList.append(i['playlist_index'])
        songsTitleList.append(i['title'])
       
        if "artist" in i:
            artistList.append(i['artist'])
        else:
            artistList.append("")

    for x in range(len(songsTitleList)):
        metadata_mp3.add_metadata_playlist(PLAYLISTS_PATH, playlistIndexList[x], playlistName, artistList[x], songsTitleList[x])


def download_video_playlist(url, playlistName):
    path=PLAYLISTS_PATH+playlistName
    if not os.path.exists(path):
      os.makedirs(path)

    ydl_opts = {
          'format': 'bestaudio/best',
          'download_archive': path+'/downloaded_songs.txt',
          'addmetadata': True,
          'outtmpl': path+'/'+'%(title)s.%(ext)s',
          'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
             }],
          'ignoreerrors': True
          }  
    results = youtube_dl.YoutubeDL(ydl_opts).extract_info(url)

    for i in results['entries']:
       if i is None:
           warningInfo="ERROR: not extract_info in results"
           print (bcolors.FAIL + warningInfo + bcolors.ENDC)
           return 0

    artistList = []
    playlistIndexList = []
    songsTitleList = []

    for i in results['entries']:
        
        playlistIndexList.append(i['playlist_index'])
        songsTitleList.append(i['title'])
       
        if "artist" in i:
            artistList.append(i['artist'])
        else:
            artistList.append("")

    songCounter=0
    for x in range(len(songsTitleList)):
        metadata_mp3.add_metadata_playlist(PLAYLISTS_PATH, playlistIndexList[x], playlistName, artistList[x], songsTitleList[x])
        songCounter+=1
  
    info = "[INFO] downloaded  %s songs"%(songCounter)
    print (bcolors.OKGREEN + info + bcolors.ENDC)
    return songCounter


def download_playlists():
    songsCounter = 0
    config = ConfigParser()
    config.read(CONFIG_FILE)
    for section_name in config.sections():
        if section_name != "GLOBAL":
            songsCounter += download_video_playlist(config[section_name]['link'], config[section_name]['name'])
    summary = "[SUMMARY] downloaded  %s songs"%(songsCounter)
    print (bcolors.OKGREEN + summary + bcolors.ENDC)

def download_mp3(url):
    path=PLAYLISTS_PATH+"/test"


    if not os.path.exists(path):
      os.makedirs(path)

    info = "[INFO] start download MP3 from link %s "%(url)
#    print (bcolors.OKGREEN + info + bcolors.ENDC)

    ydl_opts = {
          'format': 'bestaudio/best',
          'addmetadata': True,
          'outtmpl': path+'/'+'%(title)s.%(ext)s',
          'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
             }],
          'ignoreerrors': True
          }
    result = youtube_dl.YoutubeDL(ydl_opts).extract_info(url)

    songTitle = result['title']
    artist = result['artist']
    album = result['album']

    return metadata_mp3.add_metadata_song(path, album, artist, songTitle)


def main():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("---------  " + dt_string + "  ---------") 

    download_playlists()

#    print(download_mp3("https://youtu.be/6vm9s44uNQA"))
#    url="https://www.youtube.com/playlist?list=PL6uhlddQJkfiB-7Td9IIYbYM0DsPjxAt0"
#    playlistName = "imprezka"
#    update_metadata_from_YTplaylist(url, playlistName)

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("---------  " + dt_string + "  ---------") 
    print ("\n")

if __name__ == '__main__':
    main()

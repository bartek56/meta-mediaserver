from __future__ import unicode_literals
import sys
import getopt
import youtube_dl
import os
import warnings
import argparse
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

class YoutubeDownloader():
    def __init__(self):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        print("---------  " + dt_string + "  ---------") 
        minidlnaConfigFile = "/etc/mediaserver/minidlna.conf"

        self.CONFIG_FILE='/etc/mediaserver/youtubedl.ini'

        if os.path.isfile(minidlnaConfigFile):
            f = open(minidlnaConfigFile,"r")
            content = f.readlines()
    
            for x in content:
                if "media_dir=A" in x:
                    parameter = x.split("A,")
                    musicPath = parameter[1]
                    musicPath=musicPath.replace('\n','')
                    musicPath=musicPath.replace('\r','')
                    self.PLAYLISTS_PATH="%s/Youtube list/"%(musicPath)
                    break
        else:
            config = ConfigParser()
            config.read(self.CONFIG_FILE)
            self.PLAYLISTS_PATH = config["GLOBAL"]["path"]
           
        # tests path
        #self.PLAYLISTS_PATH='/tmp/music/Youtube list/'
        #self.CONFIG_FILE='/etc/mediaserver/youtubedl_test.ini'


    def update_metadata_from_YTplaylist(self, url, playlistName):
        path=os.path.join(self.PLAYLISTS_PATH, playlistName)

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
            metadata_mp3.add_metadata_playlist(self.PLAYLISTS_PATH, playlistIndexList[x], playlistName, artistList[x], songsTitleList[x])


    def download_playlist_mp3(self, url, playlistName):
        path=os.path.join(self.PLAYLISTS_PATH, playlistName)
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
            metadata_mp3.add_metadata_playlist(self.PLAYLISTS_PATH, playlistIndexList[x], playlistName, artistList[x], songsTitleList[x])
            songCounter+=1
  
        info = "[INFO] downloaded  %s songs"%(songCounter)
        print (bcolors.OKGREEN + info + bcolors.ENDC)
        return songCounter


    def download_playlists(self):
        songsCounter = 0
        config = ConfigParser()
        config.read(self.CONFIG_FILE)
        for section_name in config.sections():
            if section_name != "GLOBAL":
                songsCounter += self.download_playlist_mp3(config[section_name]['link'], config[section_name]['name'])
        summary = "[SUMMARY] downloaded  %s songs"%(songsCounter)
        print (bcolors.OKGREEN + summary + bcolors.ENDC)

    def download_mp3(self, url):
        path=os.getcwd()

        info = "[INFO] start download MP3 from link %s "%(url)
    #    print (bcolors.OKGREEN + info + bcolors.ENDC)
        print(info)

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

        songTitle = ""
        artist = ""
        album = ""
    
        if "title" in result:
            songTitle = result['title'] 
        if "artist" in result:
            artist = result['artist'] 
        if "album" in result:
            album = result['album']
   
        fullPath =  metadata_mp3.add_metadata_song(path, album, artist, songTitle)
        
        metadata = {"path": fullPath}
        if(artist is not None):
            metadata["artist"] = artist
        metadata["title"] = songTitle
        if(album is not None):
            metadata["album"] = album
        return metadata 


    def download_4k(self, url):
        path=os.getcwd()
      
        info = "[INFO] start download video [high quality] from link %s "%(url)
        print(info)
    
        ydl_opts = {
              'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
              'addmetadata': True,
              'outtmpl': path+'/'+'%(title)s_4k.%(ext)s',
              'ignoreerrors': True
              }  
        result = youtube_dl.YoutubeDL(ydl_opts).extract_info(url)
        full_path= "%s/%s_4k.%s"%(path,result['title'],result['ext'])
    
    
        metadata = {"title": result['title'], 
                     "path": full_path }
        return metadata
    
    
    def download_720p(self, url):
        path=os.getcwd()
       
        info = "[INFO] start download video [medium quality] from link %s "%(url)
        print(info)
    
        ydl_opts = {
              'format': 'bestvideo[height=720]/mp4',
              'addmetadata': True,
              'outtmpl': path+'/'+'%(title)s_720p.%(ext)s',
              'ignoreerrors': True
              }  
        result = youtube_dl.YoutubeDL(ydl_opts).extract_info(url)
    
        full_path = "%s/%s_720p.%s"%(path,result['title'],result['ext'])
        metadata = {"title": result['title'], 
                     "path": full_path }
        return metadata



    def download_360p(self, url):
        path=os.getcwd()
        
        info = "[INFO] start download video [low quality] from link %s "%(url)
        print(info)
    
        ydl_opts = {
              'format': 'worse[height<=360]/mp4',
              'addmetadata': True,
              'outtmpl': path+'/'+'%(title)s_360p.%(ext)s',
              'ignoreerrors': True
              }
    
        result = youtube_dl.YoutubeDL(ydl_opts).extract_info(url)
        full_path = "%s/%s_360p.%s"%(path,result['title'],result['ext'])
    
        metadata = {"title": result['title'], 
                     "path": full_path }
        return metadata

    def summary(self):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        print("---------  " + dt_string + "  ---------") 
        print ("\n")

       
if __name__ == '__main__':
    my_parser = argparse.ArgumentParser()
    my_parser.add_argument('-t','--type',
                       action='store',
                       choices=['360', '720', '4k', 'mp3'],
                       dest='mode',
                       help='what do you want download')
    my_parser.add_argument('-l','--link',
                       action='store',
                       dest='link',
                       help='link to youtube')


    args = my_parser.parse_args()
#    url="https://www.youtube.com/playlist?list=PL6uhlddQJkfiB-7Td9IIYbYM0DsPjxAt0"
#    playlistName = "imprezka"
#    update_metadata_from_YTplaylist(url, playlistName)

   
    yt = YoutubeDownloader()

    if args.mode == None:
        yt.download_playlists()
    else:
        if args.link is None:
            my_parser.error("-l (--link) is require")
        if args.mode == '360':
            yt.download_360p(args.link)
        elif args.mode == "720":
            yt.download_720p(args.link)
        elif args.mode == "4k":
            yt.download_4k(args.link)
        elif args.mode == "mp3":
            yt.download_mp3(args.link)
    yt.summary()

from __future__ import unicode_literals
import sys
import getopt
import youtube_dl
import os
import warnings
from datetime import datetime
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
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
        MUSIC_PATH="%s/quick download/"%(musicPath)
        PLAYLISTS_PATH="%s/Youtube list/"%(musicPath)
    if "media_dir=V" in x:
        parameter = x.split("V,")
        musicPath = parameter[1]
        VIDEO_PATH="%s/quick download/"%(musicPath)
        VIDEO_PATH=VIDEO_PATH.replace('\n','')
        VIDEO_PATH=VIDEO_PATH.replace('\r','')

# tests path
#MUSIC_PATH='/tmp/music/quick_download/'
#VIDEO_PATH='/tmp/video/quick_download/'
#PLAYLISTS_PATH='/tmp/music/Youtube list/'
#CONFIG_FILE='/etc/mediaserver/youtubedl_test.ini'

def convert_song_name(songName):
    songName = songName.replace(" -", " - ")
    songName = songName.replace("- ", " - ")

    songName = songName.replace("(Oficial Video HD)", "")
    songName = songName.replace("(Official Video HD)", "")
    songName = songName.replace("[Official Video HD]", "")
    songName = songName.replace("[Official Music Video]", "")
    songName = songName.replace("(Official Music Video)", "")

    songName = songName.replace("(Official Lyric Video)", "")

    songName = songName.replace("( Official Video )", "")
    songName = songName.replace("(Official Video)", "")
    songName = songName.replace("[Official Video]", "")
    songName = songName.replace("(official video)", "")
    songName = songName.replace("(Official video)", "")
    songName = songName.replace("[OFFICIAL VIDEO]", "")
    songName = songName.replace("(OFFICIAL VIDEO)", "")
    songName = songName.replace("(Video Official)", "")
    songName = songName.replace("[Video Official]", "")
    songName = songName.replace("(VIDEO OFFICIAL)", "")
      
    songName = songName.replace("(Oficial Video)", "")
    songName = songName.replace("[Oficial Video]", "")
    songName = songName.replace("(OFICIAL VIDEO)", "")
    songName = songName.replace("(Video Oficial)", "")
    songName = songName.replace("[Video Oficial]", "")
    songName = songName.replace("(VIDEO OFICIAL)", "")
  
    songName = songName.replace("Video Oficial", "")
    songName = songName.replace("Video Official", "")
    songName = songName.replace("Oficial Video", "")
    songName = songName.replace("Official Video", "")

    songName = songName.replace("(Audio)", "")
    
    songName = songName.replace("(Official Audio)", "")
    songName = songName.replace("[Official Audio]", "")

    songName = songName.replace("   ", " ")   
    songName = songName.replace("  ", " ")   
    songName = songName.replace("  ", " ")   
    songName = songName.replace(" _", "")

    return songName

def rename_song_name(songName):
    songName = convert_song_name(songName)
    ext = ".xyz"
    songName = "%s%s"%(songName,ext)

    songName = songName+".xyz"
    songName = songName.replace("  .xyz", ".xyz")
    songName = songName.replace(" .xyz", ".xyz")
    songName = songName.replace(".xyz", "")
    
    return songName

def rename_song_file(path, fileName):

    originalFileName = fileName 
    
    fileName = convert_song_name(fileName)

    fileName = fileName.replace("  .mp3", ".mp3")
    fileName = fileName.replace(" .mp3", ".mp3")

    originalFileNameWithPath=os.path.join(path, originalFileName)
    fileNameWithPath = os.path.join(path, fileName)
    os.rename(originalFileNameWithPath, fileNameWithPath)

    return fileName

def convert_songname_on_metadata(songName):
    slots = songName.split(" - ")
    metadata ={ 'tracknumber': "1",}
    if len(slots) == 2:
      metadata['artist'] = slots[0]
      metadata['title'] = slots[1]
    elif len(slots) < 2:
      slots = songName.split("-")
      if len(slots) == 2:
        metadata['artist'] = slots[0]
        metadata['title'] = slots[1]
      else:
        metadata['title'] = songName
        metadata['artist'] = ""
    else:
      metadata['artist'] = slots[0]
      name=""
      i=0
      for slots2 in slots:
        if i > 0:
          if i > 1:
            name+="-"
          name+=slots[i]
        i=i+1  
      metadata['title'] = name

    return metadata


def update_metadata(playlistName):
      path=PLATLISTS_PATH+playlistName
      albumName="YT "+playlistName

      filesList = [f for f in os.listdir(path) if f.endswith(".mp3")]
      for x in range(len(filesList)):
        originalFileName = filesList[x]

        newFileName = rename_song_file(path, originalFileName)
        newSongName = newFileName.replace(".mp3", "")
        
        metadataSongName = convert_songname_on_metadata(newSongName)
        newFileNameWithPath = os.path.join(path, newFileName)
        if not os.path.isfile(newFileNameWithPath):
            warningInfo="WARNING: %s not exist"%(newFileName)
            warnings.warn(warningInfo, Warning)
            print(bcolors.WARNING + warningInfo + bcolors.ENDC)
            continue
        metatag = EasyID3(newFileNameWithPath)
        metatag['album'] = albumName
        metatag['artist'] = metadataSongName['artist']
        metatag['title'] = metadataSongName['title']
        metatag.save()
        print(bcolors.OKGREEN + "[ID3] Added metadata" + bcolors.ENDC)
        audio = MP3(newFileNameWithPath, ID3=EasyID3)
        print (newFileNameWithPath)
        print (audio.pprint())


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

    artistList = [i['artist'] for i in results['entries']]
    playlistIndexList = [i['playlist_index'] for i in results['entries']]
    songsTitleList = [i['title'] for i in results['entries']]
    for x in range(len(songsTitleList)):
        add_metadata_playlist(playlistIndexList[x], playlistName, artistList[x], songsTitleList[x])


def add_metadata_playlist(trackNumber, playlistName, artist, songName):
    path=PLAYLISTS_PATH+playlistName
    albumName="YT "+playlistName

    mp3ext=".mp3"
    fileName="%s%s"%(songName,mp3ext)
      
    if not os.path.isfile(os.path.join(path, fileName)):
        songName = songName.replace("/", "_")
        songName = songName.replace("|", "_")
        songName = songName.replace("\"", "'")
        songName = songName.replace(":", "-")
        fileName="%s%s"%(songName,mp3ext)
    if not os.path.isfile(os.path.join(path, fileName)):
        songName = rename_song_name(songName)
        fileName="%s%s"%(songName,mp3ext)
    if not os.path.isfile(os.path.join(path, fileName)):
        warningInfo="WARNING: %s not exist"%(fileName)
        print (bcolors.WARNING + warningInfo + bcolors.ENDC)
        return

    newFileName = rename_song_file(path, fileName)
    newSongName = newFileName.replace(".mp3", "")

    metadataSongName = convert_songname_on_metadata(newSongName)
    newFileNameWithPath = os.path.join(path, newFileName)
        
    metatag = EasyID3(newFileNameWithPath)
    metatag['album'] = albumName
    if artist is not None:
        metatag['artist'] = artist
    else:
        metatag['artist'] = metadataSongName['artist']
    metatag['title'] = metadataSongName['title']
    metatag['tracknumber'] = str(trackNumber)
    metatag.save()
    print (bcolors.OKGREEN + "[ID3] Added metadata" + bcolors.ENDC)
    print (newFileNameWithPath)
    audio = MP3(newFileNameWithPath, ID3=EasyID3)
    print (audio.pprint())

def add_metadata_song(albumName, artist, songName):
    path=MUSIC_PATH

    mp3ext=".mp3"
    fileName="%s%s"%(songName,mp3ext)
      
    if not os.path.isfile(os.path.join(path, fileName)):
        songName = songName.replace("/", "_")
        songName = songName.replace("|", "_")
        songName = songName.replace("\"", "'")
        songName = songName.replace(":", "-")
        fileName="%s%s"%(songName,mp3ext)
    if not os.path.isfile(os.path.join(path, fileName)):
        songName = rename_song_name(songName)
        fileName="%s%s"%(songName,mp3ext)
    if not os.path.isfile(os.path.join(path, fileName)):
        warningInfo="WARNING: %s not exist"%(fileName)
        print (bcolors.WARNING + warningInfo + bcolors.ENDC)
        return

    newFileName = rename_song_file(path, fileName)
    newSongName = newFileName.replace(".mp3", "")

    metadataSongName = convert_songname_on_metadata(newSongName)
    newFileNameWithPath = os.path.join(path, newFileName)
        
    metatag = EasyID3(newFileNameWithPath)
    if albumName is not None:
        metatag['album'] = albumName
    if artist is not None:
        metatag['artist'] = artist
    else:
        metatag['artist'] = metadataSongName['artist']
    metatag['title'] = metadataSongName['title']
    metatag.save()
    print (bcolors.OKGREEN + "[ID3] Added metadata" + bcolors.ENDC)
    print (newFileNameWithPath)
    audio = MP3(newFileNameWithPath, ID3=EasyID3)
    print (audio.pprint())


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

    songsTitleList = [i['title'] for i in results['entries']]
    playlistIndexList = [i['playlist_index'] for i in results['entries']]
    artistList = [i['artist'] for i in results['entries']]
        
    songCounter=0
    for x in range(len(songsTitleList)):
        add_metadata_playlist(playlistIndexList[x], playlistName, artistList[x], songsTitleList[x])
        songCounter+=1
  
    info = "[INFO] downloaded  %s songs"%(songCounter)
    print (bcolors.OKGREEN + info + bcolors.ENDC)
    return songCounter


def download_mp3(url):
    path=MUSIC_PATH
    if not os.path.exists(path):
      os.makedirs(path)
    
    info = "[INFO] start download MP3 from link %s "%(url)
    print (bcolors.OKGREEN + info + bcolors.ENDC)

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
        
    add_metadata_song(album, artist, songTitle)

def download_high_video(url):
    path=VIDEO_PATH
    if not os.path.exists(path):
      os.makedirs(path)
    
    info = "[INFO] start download video [high quality] from link %s "%(url)
    print (bcolors.OKGREEN + info + bcolors.ENDC)

    ydl_opts = {
          'format': 'bestvideo+bestaudio/mp4',
          'addmetadata': True,
          'outtmpl': path+'/'+'%(title)s.%(ext)s',
          'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
#                'preferredformat': 'mp4',
             }],
          'ignoreerrors': True
          }  
    youtube_dl.YoutubeDL(ydl_opts).extract_info(url)

def download_medium_video(url):
    path=VIDEO_PATH
    if not os.path.exists(path):
      os.makedirs(path)
    
    info = "[INFO] start download video [medium quality] from link %s "%(url)
    print (bcolors.OKGREEN + info + bcolors.ENDC)

    ydl_opts = {
          'format': 'best[height=720]/mp4',
          'addmetadata': True,
          'outtmpl': path+'/'+'%(title)s.%(ext)s',
          'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
#                'preferredformat': 'mp4',
             }],
          'ignoreerrors': True
          }  
    youtube_dl.YoutubeDL(ydl_opts).extract_info(url)


def download_low_video(url):
    path=VIDEO_PATH
    if not os.path.exists(path):
      os.makedirs(path)
    
    info = "[INFO] start download video [low quality] from link %s "%(url)
    print (bcolors.OKGREEN + info + bcolors.ENDC)

    ydl_opts = {
          'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
          'addmetadata': True,
          'outtmpl': path+'/'+'%(title)s.%(ext)s',
          'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
#                'preferredformat': 'mp4',
             }],
          'ignoreerrors': True
          }  
    youtube_dl.YoutubeDL(ydl_opts).download([url])

def download_playlists():
    songsCounter = 0
    config = ConfigParser()
    config.read(CONFIG_FILE)
    for section_name in config.sections():
        if section_name != "GLOBAL":
            songsCounter += download_video_playlist(config[section_name]['link'], config[section_name]['name'])
    summary = "[SUMMARY] downloaded  %s songs"%(songsCounter)
    print (bcolors.OKGREEN + summary + bcolors.ENDC)


def main(argv):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("---------  " + dt_string + "  ---------") 

    link = ''
    isMusic = False
    isVideo = False

    isLow = False
    isMedium = False
    isHigh = False
    isPlaylists = False

    try:
        opts, args = getopt.getopt(argv,"hpm:v:q:",["playlists","music=","video=","quality="])
    except getopt.GetoptError:
       print ('downloadFromYoutube.py --playlists/--music/--video <link> --quality <l/m/h> ')
       sys.exit(2)
    for opt, arg in opts:
       if opt == '-h':
          print ('downloadFromYoutube.py --playlists/--music/--video <link> --quality <l/m/h> ')
          sys.exit()
       elif opt in ("-p,--playlists"):
           isPlaylists=True
       elif opt in ("-m", "--music"):
          link = arg
          isMusic = True
       elif opt in ("-v", "--video"):
          link = arg
          isVideo = True
       elif opt in ("-q","--quality"):
          if arg=='l':
              isLow=True
          elif arg=='m':
              isMedium = True
          elif arg=='h':
              isHigh = True

    if isPlaylists:
        download_playlists()

    if isMusic:
        download_mp3(link)
   
    if isVideo:
        if isLow:
            download_low_video(link)
        if isMedium:
            download_medium_video(link)
        if isHigh:
            download_high_video(link)

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("---------  " + dt_string + "  ---------") 
    print ("\n")

if __name__ == '__main__':
    main(sys.argv[1:])

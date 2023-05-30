import os
import subprocess
import sys

class DownloadSubtitles():
    def __init__(self):
        self.qnapiConfigFile = "/etc/mediaserver/qnapi.ini"

    def downloadSubtitlesForTvShow(self, languages:list, dirPath):
        result = {}
        for language in languages:
            self.configQNapi(language)
            videoDirectory = dirPath
            filesList = os.listdir(videoDirectory)
            for movie in filesList:
                if (".mp4" in movie or ".mkv" in movie) and ".part" not in movie:
                            movieFullPath = os.path.join(videoDirectory, movie)
                            if self.qnapi(movieFullPath):
                                fileName = movieFullPath.replace(".mkv","")
                                fileName = fileName.replace(".mp4","")
                                srtOldFile = "%s.srt"%(fileName)
                                srtNewFile = "%s.%s.srt"%(fileName, language)
                                os.rename(srtOldFile, srtNewFile)
                                print("Downloaded:\t",srtNewFile)
                                if movie not in result.keys():
                                    result[movie] = []
                                result[movie].append(language)
                    
        return result            

    def downloadSubtitles(self, languages:list):
        result = {}
        for language in languages:
            self.configQNapi(language)
            videoDirectory = os.path.join(self.lookingForVideoDir(),"movies")
            filesList = os.listdir(videoDirectory)
            moviesList = []
            for x in filesList:
                if os.path.isdir(os.path.join(videoDirectory,x)):
                    moviesList.append(x)
            for movieDir in moviesList:
                movieDirFullPath = os.path.join(videoDirectory, movieDir)
                filesInMovieDir = os.listdir(movieDirFullPath)
                if not movieDir in result:
                   result[movieDir] = []
                if not self.subtitlesExist(filesInMovieDir, language):
                    for movie in filesInMovieDir:                
                        if (".mp4" in movie or ".mkv" in movie) and ".part" not in movie:
                            movieFullPath = os.path.join(movieDirFullPath, movie)
                            if self.qnapi(movieFullPath):
                                fileName = movieFullPath.replace(".mkv","")
                                fileName = fileName.replace(".mp4","")
                                srtOldFile = "%s.srt"%(fileName)
                                srtNewFile = "%s.%s.srt"%(fileName, language)
                                os.rename(srtOldFile, srtNewFile)
                                print("Downloaded:\t",srtNewFile)
                                result[movieDir].append(language)
                else:
                    print(language, "subtitle exists for movie",movieDir)
                    result[movieDir].append(language)
                    
        return result            

    def lookingForSubtitles(self):
            result = {}
            videoDirectory = os.path.join(self.lookingForVideoDir(),"movies")
            filesList = os.listdir(videoDirectory)
            moviesList = []
            for x in filesList:
                if os.path.isdir(os.path.join(videoDirectory,x)):
                    moviesList.append(x)
            for movieDir in moviesList:
                movieDirFullPath = os.path.join(videoDirectory, movieDir)
                filesInMovieDir = os.listdir(movieDirFullPath)
                if not movieDir in result:
                   result[movieDir] = []
                for movie in filesInMovieDir:                
                   if ".srt" in movie:
                       result[movieDir].append(movie)
                   
            return result            


    def configQNapi(self, language):
        file = open(self.qnapiConfigFile, "r")
        replacement = ""
        for line in file:
            if "language=" in line:            
                line = "language=%s\n"%(language)
            replacement = replacement + line

        file.close()
        fout = open(self.qnapiConfigFile, "w")
        fout.write(replacement)
        fout.close()
    
    def subtitlesExist(self, filesInDir, language):
        partName = ".%s.srt"%(language)
        for x in filesInDir:
            if partName in x:
                return True
        return False

    def qnapi(self, fileNameWithPath):
        print("Looking for\t", fileNameWithPath)
        out = subprocess.run(["qnapi", fileNameWithPath], capture_output=True, text=True, cwd="/etc/mediaserver")

        result = out.stdout
        movieName = fileNameWithPath.split('/')[-1]
        if "Nie znaleziono napisow!" in result:
            print("Nie znaleziono napisów dla filmu:", movieName)
            return False
        elif "Nie znaleziono pliku!" in result:
            print("nieznaleziono pliku", movieName)
            return False
        else:
            return True

    def lookingForVideoDir(self):
        fileNameWithPath = "/etc/mediaserver/minidlna.conf"
        file = open(fileNameWithPath, "r")
        videoDir = ""
        # using the for loop
        for line in file:
            if "media_dir=V" in line: 
                videoDir = line.split(',')[1].strip()
        file.close()
        return videoDir


if __name__ == "__main__":
    download = DownloadSubtitles()
    if len(sys.argv) == 2:
        pathForTvShows = sys.argv[1]
        print("Download subtitles for:", pathForTvShows)
        if os.path.isdir(pathForTvShows):
            result = download.downloadSubtitlesForTvShow(["eng", "pl"], pathForTvShows)
            result = sorted(result.items())
            for key, value in result:
                print(key, ": ", value)
        else:
            print("wrong path")
    else:
        result = download.downloadSubtitles(["eng","pl"])

        result2 = download.lookingForSubtitles()
        result2 = sorted(result2.items())
        for key,value in result2:
            print(key, value)

        result = sorted(result.items())
        for key, value in result:
            print(key, ": ", value)


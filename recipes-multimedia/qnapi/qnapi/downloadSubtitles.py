import os
import subprocess


class DownloadSubtitles():
    def __init__(self, language):
        self.language = language
        self.qnapiConfigFile = "/etc/mediaserver/qnapi.ini"
        self.configQNapi()
        self.downloadSubtitles()

    def downloadSubtitles(self):
        videoDirectory = os.path.join(self.lookingForVideoDir(),"movies")
        filesList = os.listdir(videoDirectory)
        moviesList = []
        for x in filesList:
            if os.path.isdir(os.path.join(videoDirectory,x)):
                moviesList.append(x)
        for movieDir in moviesList:
            movieDirFullPath = os.path.join(videoDirectory, movieDir)
            filesInMovieDir = os.listdir(movieDirFullPath)
            if not self.subtitlesExist(filesInMovieDir):
                for movie in filesInMovieDir:                
                    if (".mp4" in movie or ".mkv" in movie) and ".part" not in movie:
                        movieFullPath = os.path.join(movieDirFullPath, movie)
                        if self.qnapi(movieFullPath):
                            fileName = movieFullPath.replace(".mkv","")
                            fileName = fileName.replace(".mp4","")
                            srtOldFile = "%s.srt"%(fileName)
                            srtNewFile = "%s.%s.srt"%(fileName, self.language)
                            os.rename(srtOldFile, srtNewFile)
                            print("Downloaded:\t",srtNewFile)
            else:
                print(self.language, "subtitle exists for movie",movieDir)

    def configQNapi(self):
        file = open(self.qnapiConfigFile, "r")
        replacement = ""
        for line in file:
            if "language=" in line:            
                line = "language=%s\n"%(self.language)
            replacement = replacement + line

        file.close()
        fout = open(self.qnapiConfigFile, "w")
        fout.write(replacement)
        fout.close()
    
    def subtitlesExist(self, filesInDir):
        partName = ".%s.srt"%(self.language)
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
    DownloadSubtitles("eng")
    DownloadSubtitles("pl")


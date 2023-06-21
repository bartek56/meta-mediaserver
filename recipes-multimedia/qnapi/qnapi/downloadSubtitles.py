import os
import subprocess
import json
import shutil
import sys

class DownloadSubtitles():
    def __init__(self):
        self.qnapiConfigFile = "/etc/mediaserver/qnapi.ini"

    def mergeSubtitlesLoop(self, videoDirectory):
        filesList = os.listdir(videoDirectory)
        for movie in filesList:
            if (".mp4" in movie or ".mkv" in movie) and ".part" not in movie:
                self.mergeSubtitlesToVideoFile(videoDirectory, movie)


    def mergeSubtitlesToVideoFile(self, videoDirectory, movie):
        ext = movie.split('.')[-1]
        movieName = movie.replace(".%s"%ext,"")
        print(movieName,"start")
        movieTemp = "%s_temp.%s"%(movieName, ext)
        movieFullPath = os.path.join(videoDirectory, movie)
        movieTempFullPath = os.path.join(videoDirectory, movieTemp)
        subtitlesName = "%s.pl.%s"%(movieName,"srt")
        subtitlesNamePath = os.path.join(videoDirectory, subtitlesName)
        availableSubtitles = self.getAvailableSubtitlesFromMovie(movieFullPath)
        if "pl" in availableSubtitles:
            print("video contains pl and eng subtitles")
            return
        if not os.path.exists(subtitlesNamePath):
            print("subtitles doesn't exist: ", subtitlesNamePath)
            return

        preLen = len(availableSubtitles)
        if ext == "mkv":
            subtitleType = "ass"
        elif ext == "mp4":
            subtitleType = "mov_text"
        else:
            print("error with subtitle type")
            return

        if preLen == 0:
            return
        print(availableSubtitles)
        if not self.addPlSubtitlesToMovie(subtitlesNamePath, movieFullPath, movieTempFullPath, preLen, subtitleType):
            return
        availableSubtitles = self.getAvailableSubtitlesFromMovie(movieTempFullPath)
        postLen = len(availableSubtitles)
        if postLen == preLen:
            return

        os.remove(movieFullPath)
        shutil.copy2(movieTempFullPath, movieFullPath)
        os.remove(movieTempFullPath)

        print(availableSubtitles)
        print(movieName,"succesfull")
        print("-----------------------------")


    def getAvailableSubtitlesFromMovie(self, movie):
        process = subprocess.run(['ffprobe', '-of','json', '-show_entries', 'format:stream', movie], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        #output, errors = process.communicate()
        #print(errors.decode('utf-8'))
        #print(output.decode('utf-8'))
        result = json.loads(process.stdout)
        subtitlesIndexesOfStream = []
        if "streams" not in result:
            print("error with ffprobe result")
            return []

        streams = result["streams"]
        #print(streams)
        for x in range(len(streams)):
            codecName = streams[x]["codec_name"]
            codecType = streams[x]["codec_type"]

            #print(codecName)
            #print(codecType)
            if codecType == "subtitle":
                subtitlesIndexesOfStream.append(x)

        availableSubtitles = []
        for index in subtitlesIndexesOfStream:
            #print(streams[index])
            #print("language:", streams[index]['tags']['language'])
            if "language" in streams[index]['tags']:
                availableSubtitles.append(streams[index]['tags']['language'])

        return availableSubtitles

    def addPlSubtitlesToMovie(self, subtitles, movie, movieTemp, indexOfNewSubtitle, subtitleType):
        #ffmpeg -i Manifest\ S02E01\ Fasten\ Your\ Seatbelts.mkv -i Manifest\ S02E01\ Fasten\ Your\ Seatbelts.pl.srt -map 0 -map 1 -c copy -c:s:1 ass -metadata:s:s:1 language='pl' Manifest\ S02E01\ Fasten\ Your\ Seatbelts_pl.mkv
        metadataArgument = "-metadata:s:s:%s"%(str(indexOfNewSubtitle))
        ffmpeg_args = ['ffmpeg', '-y', '-i', movie, "-i", subtitles, "-map", "0", "-map", "1","-c", "copy","-c:s:1", subtitleType, metadataArgument, "language=pl", movieTemp]

        process = subprocess.Popen(ffmpeg_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        #debug, error = process.communicate()
        #print(debug)

        return process.returncode == 0

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

    if len(sys.argv) == 3:
        pathForTvShows = sys.argv[1]
        if not os.path.isdir(pathForTvShows):
            print("wrong path")
            exit()
        type = sys.argv[2]
        if type == "--download" or type=="-t":
            print("Download subtitles for:", pathForTvShows)
            result = download.downloadSubtitlesForTvShow(["eng", "pl"], pathForTvShows)
            result = sorted(result.items())
            for key, value in result:
                print(key, ": ", value)
        elif type == "--merge" or type == "-m":
            print("merge subtitles in:", pathForTvShows)
            download.mergeSubtitlesLoop(pathForTvShows)

    else:
        result = download.downloadSubtitles(["eng","pl"])

        result2 = download.lookingForSubtitles()
        result2 = sorted(result2.items())
        for key,value in result2:
            print(key, value)

        result = sorted(result.items())
        for key, value in result:
            print(key, ": ", value)


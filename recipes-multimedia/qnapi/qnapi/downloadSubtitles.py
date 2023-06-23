import os
import subprocess
import json
import shutil
import sys

class MergeSubtitles():

    def mergeSubtitlesLoop(self, videoDirectory):
        filesList = os.listdir(videoDirectory)
        for movie in filesList:
            if (".mp4" in movie or ".mkv" in movie) and ".part" not in movie:
                self.mergeSubtitlesToVideoFile(videoDirectory, movie)
                print("")


    def mergeSubtitlesToVideoFile(self, videoDirectory, movie):
        ext = movie.split('.')[-1]
        movieName = movie.replace(".%s"%ext,"")
        print("|------ ",movieName," ------|")
        movieTemp = "%s_temp.%s"%(movieName, ext)
        movieFullPath = os.path.join(videoDirectory, movie)
        movieTempFullPath = os.path.join(videoDirectory, movieTemp)
        subtitlesPlName = "%s.pl.%s"%(movieName,"srt")
        subtitlesPlNamePath = os.path.join(videoDirectory, subtitlesPlName)
        subtitlesEngName = "%s.eng.%s"%(movieName,"srt")
        subtitlesEngNamePath = os.path.join(videoDirectory, subtitlesEngName)
        subtitlesPlIsAvailable = os.path.exists(subtitlesPlNamePath)
        subtitlesEngIsAvailable = os.path.exists(subtitlesEngNamePath)

        availableSubtitles = self.getAvailableSubtitlesFromMovie(movieFullPath)
        if not isinstance(availableSubtitles, list):
            print("error with veryfing number os subtitles after procesing")
            return
        if len(availableSubtitles) > 0:
            availableSubtitlesStr = ""
            for x in availableSubtitles:
                availableSubtitlesStr += x
                availableSubtitlesStr += " "

            print("available subtitles:", availableSubtitlesStr)

        if not isinstance(availableSubtitles, list):
            print("error with get available subtitles")
            return
        if "pol" in availableSubtitles and "eng" in availableSubtitles:
            print("video contains pl and eng subtitles")
            return
        if not subtitlesPlIsAvailable and not subtitlesEngIsAvailable:
            print("external files with subtitles doesn't exists")
            return

        preLen = len(availableSubtitles)
        if ext == "mkv":
            subtitleType = "ass"
        elif ext == "mp4":
            subtitleType = "mov_text"
        else:
            print("error with subtitle type")
            return

        if("pol" not in availableSubtitles and "eng" not in availableSubtitles):
            if subtitlesEngIsAvailable and subtitlesPlIsAvailable:
                print("merge PL and Eng subtitles")
                if not self.addEngAndPlSubtitlesToMovie({"eng":subtitlesEngNamePath, "pl": subtitlesPlNamePath},movieFullPath, movieTempFullPath, preLen, subtitleType):
                    print("failed to add pl and eng subtitles")
                    return
            else:
                print("pol and eng subtitles are not available")
                if subtitlesPlIsAvailable:
                    print("add only PL subtitles")
                    if not self.addPlSubtitlesToMovie(subtitlesPlNamePath, movieFullPath, movieTempFullPath, preLen, subtitleType):
                        print("error to add PL subtitles")
                        return
                elif subtitlesEngIsAvailable:
                    print("add only Eng subtitles")
                    if not self.addEngSubtitlesToMovie(subtitlesEngNamePath, movieFullPath, movieTempFullPath, preLen, subtitleType):
                        print("error to add Eng subtitles")
                        return
        elif("pol" not in availableSubtitles and "eng" in availableSubtitles):
            print("merge only pl subtitles")
            if not os.path.exists(subtitlesPlNamePath):
                print("Polish subtitles doesn't exist: ", subtitlesPlNamePath)
                return
            if not self.addPlSubtitlesToMovie(subtitlesPlNamePath, movieFullPath, movieTempFullPath, preLen, subtitleType):
                print("error to add PL subtitles")
                return
        elif("pol" in availableSubtitles and "eng" not in availableSubtitles):
            print("merge only eng subtiles")
            if not os.path.exists(subtitlesEngNamePath):
                print("English subtitles doesn't exist: ", subtitlesEngNamePath)
                return
            if not self.addEngSubtitlesToMovie(subtitlesEngNamePath, movieFullPath, movieTempFullPath, preLen, subtitleType):
                print("error to add Eng subtitles")
                return

        availableSubtitles = self.getAvailableSubtitlesFromMovie(movieTempFullPath)
        if not isinstance(availableSubtitles, list):
            print("error with veryfing number os subtitles after procesing")
            return

        postLen = len(availableSubtitles)
        if postLen == preLen:
            print("subtitles were not added")
            return

        if len(availableSubtitles) > 0:
            availableSubtitlesStr = ""
            for x in availableSubtitles:
                availableSubtitlesStr += x
                availableSubtitlesStr += " "

            print("available subtitles:", availableSubtitlesStr)

        os.remove(movieFullPath)
        shutil.copy2(movieTempFullPath, movieFullPath)
        os.remove(movieTempFullPath)

        print("succesfull")


    def getAvailableSubtitlesFromMovie(self, movie):
        process = subprocess.run(['ffprobe', '-of','json', '-show_entries', 'format:stream', movie], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        #output, errors = process.communicate()
        #print(errors.decode('utf-8'))
        #print(output.decode('utf-8'))
        result = json.loads(process.stdout)
        subtitlesIndexesOfStream = []
        if "streams" not in result:
            print("error with ffprobe result")
            return -1

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
        ffmpeg_args = ['ffmpeg', '-hide_banner','-loglevel', 'error', '-y', '-i', movie, "-i", subtitles, "-map", "0", "-map", "1","-c", "copy","-c:s", subtitleType, metadataArgument, "language=pol", movieTemp]

        process = subprocess.Popen(ffmpeg_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        debug, error = process.communicate()
        print(str(error))

        return process.returncode == 0

    def addEngSubtitlesToMovie(self, subtitles, movie, movieTemp, indexOfNewSubtitle, subtitleType):
        #ffmpeg -i Manifest\ S02E01\ Fasten\ Your\ Seatbelts.mkv -i Manifest\ S02E01\ Fasten\ Your\ Seatbelts.pl.srt -map 0 -map 1 -c copy -c:s:1 ass -metadata:s:s:1 language='pl' Manifest\ S02E01\ Fasten\ Your\ Seatbelts_pl.mkv
        metadataArgument = "-metadata:s:s:%s"%(str(indexOfNewSubtitle))
        ffmpeg_args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', movie, "-i", subtitles, "-map", "0", "-map", "1","-c", "copy","-c:s", subtitleType, metadataArgument, "language=eng", movieTemp]

        process = subprocess.Popen(ffmpeg_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        debug, error = process.communicate()
        print(str(error))

        return process.returncode == 0


    def addEngAndPlSubtitlesToMovie(self, subtitles:dict, movie, movieTemp, indexOfNewSubtitle, subtitleType):
        # ffmpeg -y -i Room.2015.1080p.BRRip.x264.AAC-ETRG.mp4 -i Room.2015.1080p.BRRip.x264.AAC-ETRG.eng.srt -i Room.2015.1080p.BRRip.x264.AAC-ETRG.pl.srt 
        # -map 0 -map 1 -map 2 -c copy -c:s mov_text -c:s mov_text 
        # -metadata:s:s:0 language='eng' -metadata:s:s:1 language='pol' test_eng_pl.mp4
        metadataArgumentEng = "-metadata:s:s:%s"%(str(indexOfNewSubtitle))
        metadataArgumentPl = "-metadata:s:s:%s"%(str(indexOfNewSubtitle+1))
        ffmpeg_args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', movie, "-i", subtitles["eng"], '-i', subtitles["pl"],
                       "-map", "0", "-map", "1", "-map", "2","-c", "copy","-c:s", subtitleType, "-c:s", subtitleType,
                       metadataArgumentEng, "language=eng", metadataArgumentPl, "language=pol", movieTemp]

        process = subprocess.Popen(ffmpeg_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        debug, error = process.communicate()
        print(str(error))

        return process.returncode == 0

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
    merge = MergeSubtitles()

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
            merge.mergeSubtitlesLoop(pathForTvShows)

    else:
        result = download.downloadSubtitles(["eng","pl"])

        result2 = download.lookingForSubtitles()
        result2 = sorted(result2.items())
        for key,value in result2:
            print(key, value)

        result = sorted(result.items())
        for key, value in result:
            print(key, ": ", value)


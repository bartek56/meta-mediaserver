<!DOCTYPE HTML>
<html lang="pl">

<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <link rel="stylesheet" href="bootstrap-5.0.0/css/bootstrap.min.css" />
    <link rel="stylesheet" href="bootstrap-icons-1.5.0/font/bootstrap-icons.css">
    <link rel="stylesheet" href="./style.css">

    <title>Media Server</title>
    <script src="bootstrap-5.0.0/js/bootstrap.bundle.min.js"></script>
    <script type="text/javascript" src="http://code.jquery.com/jquery-1.7.1.min.js"></script>

</head>

<body>
    <header id="page-media" class="site-header">

        <nav class="navbar navbar-expand-sm bg-secondary navbar-dark fixed-top">

            <div class="container-fluid">

                <button type="button" class="navbar-toggler" data-bs-toggle="collapse" data-bs-target="#myTogglerNav"
                    aria-controls="#myTogglerNav" aria-label="Toggle Navigation">
                    <span class="navbar-toggler-icon"></span>
                </button>

                <a class="navbar-brand" href="index.html">
                    Media Server
                </a>

                <section class="collapse navbar-collapse" id="myTogglerNav">
                    <div class="navbar-nav ms-auto">
                       <a class="nav-item nav-link" href="/index.php">Home</a>
                       <a class="nav-item nav-link" href="/youtubedl/index.html">Download</a>
                       <a class="nav-item nav-link" href="/youtubedl/playlists.html">Playlists</a>
                       <a class="nav-item nav-link" href="/youtubedl/alarm.html">Alarm</a>
                    </div>
                </section>
            </div>
        </nav>
    </header>
    <div id="carouselExampleIndicators" class="carousel slide" data-bs-ride="carousel">
        <div class="carousel-indicators">
            <button type="button" data-bs-target="#carouselExampleIndicators" data-bs-slide-to="0" class="active"
                aria-current="true" aria-label="Slide 1"></button>
            <button type="button" data-bs-target="#carouselExampleIndicators" data-bs-slide-to="1"
                aria-label="Slide 2"></button>
            <button type="button" data-bs-target="#carouselExampleIndicators" data-bs-slide-to="2"
                aria-label="Slide 3"></button>
        </div>
        <div class="carousel-inner">
            <div class="carousel-item active">
                <img src="images/IMG_20210611_210755.jpg" class="d-block w-100" alt="...">
            </div>
            <div class="carousel-item">
                <img src="images/IMG_20210722_105646.jpg" class="d-block w-100" alt="...">
            </div>
            <div class="carousel-item">
                <img src="images/IMG_20210722_150715.jpg" class="d-block w-100" alt="...">
            </div>
        </div>
        <button class="carousel-control-prev" type="button" data-bs-target="#carouselExampleIndicators"
            data-bs-slide="prev">
            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Previous</span>
        </button>
        <button class="carousel-control-next" type="button" data-bs-target="#carouselExampleIndicators"
            data-bs-slide="next">
            <span class="carousel-control-next-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Next</span>
        </button>
    </div>
    <br>
    <br>
    <br>


    <div class="container">
        <div class="row">
            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href="' + 'http://' + window.location.hostname + ':8080' + 
                            '" ><img src="ympd.svg" height="150" alt="" border="0" ></a>');
                    </script>
                    <h2>Music Player</h2>
                </center>
            </div>
            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href="' + window.location.protocol + '//' + window.location.hostname +
                        '/ampache/' + '" ><img src="ampache.png" height="150" alt="" border="0" ></a>');
                    </script>
                    <h2>Music Server</h2>
            </div>

            <div class="col-md">
                <center>
                    <td>
                        <script language="JavaScript">
                            document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':8096' +
                                '" ><img src="jellyfin.png" height="150" alt="" border="0"/> </a>');
                        </script>
                        <h2>Jellyfin</h2>
                    </td>
                </center>
            </div>




            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':8090' + 
                            '" ><img src="filebrowser.png" height="150" alt="" border="0"> </a>');
                    </script>
                    <h2>File Browser</h2>

                </center>

            </div>
            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':9981' +
                            '" ><img src="tvheadend.png" height="150" alt="" border="0"> </a>');
                    </script>
                    <h2>TvHeadEnd</h2>
                </center>
            </div>
        </div>
        <div class="row top-buffer">
            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href=ftp://' + window.location.hostname +
                            '><img src="ftp.png" height="150" alt="" border="0"/> </a>');
                    </script>
                    <h2>FTP</h2>
                </center>
            </div>

            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href=smb://' + window.location.hostname + 
                            '><img src="samba.png" height="150" alt="" border="0" /> </a> ');
                    </script>
                    <h2>Samba</h2>
                </center>
            </div>

            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href="' + 'http://' + window.location.hostname + ':8200' +
                            '" ><img src="dlna.png" height="150" alt="" border="0" /> </a> ');
                    </script>
                    <h2>DLNA status</h2>
                </center>

            </div>

            <div class="col-md">
                <center>
                    <script language="JavaScript">
                         document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + '/youtubedl' +
                            "/index.html" +
                            '" ><img src="youtubedl.png" height="150" alt="" border="0" /> </a>');
                    </script>
                    <center>
                        <h2>Youtube-DL</h2>
                    </center>
                </center>
            </div>
            <div class="col-md">
                <center>
                    <script language="JavaScript">
                        document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':9091' +
                            '" ><img src="transmission.png" height="150" alt="" border="0" />  </a> ');
                    </script>
                    <h2>Torrent</h2>
                </center>

            </div>
        </div>
    </div>

    <br>
    <br>
    <br>
    <br>

    <footer class="footer">
        <p class="text-center">

              <a class="bi-github" style="font-size: 2rem;" href="https://github.com/bartek56" role="img" aria-label="GitHub"></a>
              <a class="bi bi-linkedin" style="font-size: 2rem;" href="https://www.linkedin.com/in/bbrzozowski23/"> </a>
              <a class="bi bi-facebook" style="font-size: 2rem;" href="https://www.facebook.com/bartosz.brzozowski23"> </a>


        </p>

        <div class="container">
            <p class="text-muted text-center">Serwer Multimedialny. Administrator Bartosz Brzozowski. &copy; Wszelkie
                prawa zastrzeżone.</p>
        </div>

    </footer>
</body>

</html>

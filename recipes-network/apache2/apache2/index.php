<!DOCTYPE HTML>
<html lang="pl">
<head>
<meta charset="utf-8" />
<title>Media Server</title>
<meta name="description" content="Serwer multimedialny" />
	<meta name="keywords" content="Informacje o salonie kosmetycznym"" />
	<meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1" />
	<link rel="stylesheet" href="style.css" type="text/css" />	
</head>
<body id="background">

<div id="container">
<div id="left">
</div>
<div id="mybody">
	<center>
<table  border="0" cellpadding="0" cellspacing="40">
<tr>

	<td>
			<script language="JavaScript">
document.write('<a href="' + 'http://' + window.location.hostname + ':8080' + window.location.pathname + 
	'" ><img src="ympd.svg" height="150" alt="" border="0" >' );
			</script>
	<center><h2>Music Player</h2></center>
	</td>

	<td>
			<script language="JavaScript">
document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + window.location.pathname + 
'/ampache/' + '" ><img src="ampache.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>Music Server</h2></center>
	</td>

	<td>
			<script language="JavaScript">
document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':8096' + window.location.pathname + 
	'" ><img src="jellyfin.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>Jellyfin</h2></center>
	</td>

	<td>
			<script language="JavaScript">
document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':8090' + window.location.pathname +
	'" ><img src="filebrowser.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>File Browser</h2></center>

	<td>
			<script language="JavaScript">
document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + window.location.pathname + '/tvheadend' +
	'" ><img src="tvheadend.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>TvHeadEnd</h2></center>
	</td>

	</td>





<!--
	<td>
			<script language="JavaScript">
document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':2202' + window.location.pathname + 
	'" ><img src="ubooquity.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>Ubooquity</h2></center>

	</td>
-->

	
</tr>
</table>
</center>
<center>

<table border="0" cellpadding="0" cellspacing="40">
<tr>
	<td>
			<script language="JavaScript">
document.write('<a href=ftp://' + window.location.hostname + window.location.pathname + 
	'><img src="ftp.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>FTP</h2></center>

	</td>
	<td>
			<script language="JavaScript">
document.write('<a href=smb://' + window.location.hostname + window.location.pathname + 
	'><img src="samba.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>Samba</h2></center>

	</td>
	<td>
			<script language="JavaScript">
document.write('<a href="' + 'http://' + window.location.hostname + ':8200' + window.location.pathname + 
	'" ><img src="dlna.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>DLNA status</h2></center>

	</td>

	<td>
			<script language="JavaScript">
document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':9080' + window.location.pathname + 
	'" ><img src="alarm.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>Alarm</h2></center>

	</td>

	<td>
			<script language="JavaScript">
document.write('<a href="' + window.location.protocol + '//' + window.location.hostname + ':9091' + window.location.pathname + 
	'" ><img src="transmission.png" height="150" alt="" border="0" >' );
			</script>
	<center><h2>Torrent</h2></center>

	</td>


</tr>

</table>
	</center>

</div>
<!--
<div id="right">
</div>
-->
<div id="footer">
Serwer Multimedialny. Administrator Bartosz Brzozowski. &copy; Wszelkie prawa zastrzeżone.
</div>


</div>
</body>
</html>

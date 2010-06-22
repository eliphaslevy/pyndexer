var playerobj = null;
function createplayer(playerheight, href) {
	if (playerobj != null) {
		// FIXME could re-use the existing player. but I don't know yet how to resize him...
	}
	// will change from default to 350 if video files detected
	var so = new SWFObject('http://dl.dropbox.com/u/552/pyndexer/1.0/player.swf','playerobj','600',playerheight,'9');
	so.addParam('allowfullscreen','true');
	so.addParam('allowscriptaccess','always');
	so.addParam('bgcolor','#FFFFFF');
	so.addVariable('playerready','getPlayerId');
	so.addVariable('file',href);
	so.addVariable('autostart','true');
	so.addVariable('screencolor','#FFFFFF');
	so.write('playerdiv');
	document.getElementById('jwplayerrow').style['display']='';
}
function getPlayerId(obj) {
	playerobj = document.getElementsByName(obj.id)[0]; 
} 
function playthis(img, href) {
	var loc = window.location.href.split('/');
	delete loc[loc.length-1];
	href = loc.join('/')+href;
	if ( img.className == 'sprite s_film' ) {
		createplayer(350, href);
	} else {
		createplayer(24, href);
	}
}

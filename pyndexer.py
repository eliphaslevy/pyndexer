#!/usr/bin/env python
#	pyndexer.py - Generates index.html recursively for a given directory
#	Copyleft Eliphas Levy Theodoro
#	This script was primarily made for use with the Public Folder
#	feature of Dropbox - http://www.getdropbox.com
#	See more information and get help at http://forums.getdropbox.com/topic.php?id=3075
#	Some ideas/code got from AJ's version at http://dl.getdropbox.com/u/259928/www/indexerPY/index.html

import getopt, re
from os import path, getcwd, chdir, walk
from sys import argv, exit
from datetime import datetime as dt
from locale import setlocale, strxfrm, LC_ALL
setlocale(LC_ALL,"")

version = "0.7"
"""
ChangeLog
2009-05-03.0.1
	First try
2009-05-03.0.2
	Ordering folders and files. Forgot it.
2009-05-06.0.3
	Ignoring the index file on the list
2009-09-10.0.4
	File sort order ignoring case
2009-12-07.0.5
	Added two decimal digits to HumanSize
	File sort order with locale (removed case insensitive kludge)
2010-01-16.0.6
	Added JW player support to MP3 files, if JW player files are found on the same folder
		Required files: (player.swf, swfobject.js)
	Added ?dl suffix on links to "generic" files (not html/htm/txt/php)
		Makes the browser download it instead of opening. Change viewInBrowser var to remove other files
	If an index.html file is found on the folder, check it against the new one for differences before overwriting
		Saves a sync action on dropbox and a recent events
	Added a non-recursive togglable option: (-R,--recursive) or (-N,--nonrecursive) - still defaults to recursive!
		Change recursiveDirs variable if want to change the default
	Added verbose (-v,--verbose) option to print indexed files and folders individually
	Added ignorePattern option: (-i,--ignore), accepting python's regex, ex: ['index\..*','\..*']
		You can ignore multiple patterns with multiple --ignore arguments
2010-02-04.0.7
	Added listing encryption (AES-256-CBC) support with javascript
		http://www.vincentcheung.ca/jsencryption/
"""

### Mutable variables

# Index file name
indexFileName = "index.html"
# Date format
dateFormat = "%Y-%m-%d&nbsp;%H:%M"
# If you want to NOT see the TOTAL directory size (including child dirs) in the dir entry, put False in here
recurseDirSize = True
# Do you want recursive diving into the subfolders by default?
recursiveDirs = True
# "Encrypt this folder" file trigger
cryptTrigger = 'encrypt.txt'
# Files ignored by default: index file itself, all files starting with dots (unix way to say "hidden")
ignorePattern = [re.escape(indexFileName), re.escape(cryptTrigger), '\..*']
# Files that will NOT have the ?dl (download, not display) suffix on links
viewInBrowser = ['html','htm','txt','php']
# Files to place the "play" radio button option
jwPlayExts = ['mp3']
# JWPlayer files to look for
jwPlayerFiles = ['player.swf','swfobject.js']
# JS encryption script
aesScript = '<script type="text/javascript" src="http://www.vincentcheung.ca/jsencryption/jsencryption.js"></script>'

#### Change this HTML to your needs. The "%(keyword)s" will be replaced by their respective values.

# javascript to place when files of "playable" type are found
htPlayerScript = """
		<script type="text/javascript" src="swfobject.js"></script>
		<script type="text/javascript">
			function toggle(rad){
				var song = rad.value;
				var swf = new SWFObject('player.swf','player','400','24','9','#ffffff');
				swf.addParam('allowfullscreen','false');
				swf.addParam('allowscriptaccess','never');
				swf.addParam('wmode','opaque');
				swf.addVariable('file',song);
				swf.addVariable('autostart','true');
				swf.write('player');
			}
		</script>"""

jsDecrypt = """
			<TR><TD COLSPAN="3"><A HREF="javascript:decryptText('maindiv')">Show encrypted file listing</A></TD></TR>
"""

# htmlBase
# accepts: {currentFolder} {playerScript} {aesScript} {aesCipher} {maincontents}
htmlBase = """
<HTML>
	<HEAD>
		<TITLE>Dropbox :: Folder listing :: %(currentFolder)s</TITLE>
		<link rel="shortcut icon" href="http://www.getdropbox.com/static/1238803391/images/favicon.ico"/>
		<link href="http://www.getdropbox.com/static/1241315492/css/sprites.css" rel="stylesheet" type="text/css" media="screen"/>
		<style type="text/css"><!--
			body, td { font-family:lucida grande, lucida sans unicode, verdana; font-size:12px; }
			a               { color:#1F75CC; text-decoration:none; }
			a:hover         { color:#1F75CC; text-decoration:underline; }
			a:visited       { color:#1F75CC; text-decoration:none; }
			a:visited:hover { color:#1F75CC; text-decoration:underline; }
			#player { float: right; top: 10px; }
			#dir:hover  { background-color:#D7ECFF; }
			#file:hover { background-color:#D7ECFF; }
			#sprite{background-image:(url:http://www.getdropbox.com/static/89816/images/sprites/sprites.png)}
		--></style>
		%(playerScript)s
		%(aesScript)s
	</HEAD>
	<BODY><CENTER><DIV id="maindiv" title="%(aesCipher)s">
		%(maincontents)s
	</DIV></CENTER></BODY>
</HTML>
"""
# accepts {currentFolder}
tableStart = """
		<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="2" WIDTH="800">
			<TR><TD colspan="3">
				<DIV id="player"><!--replaced by js--></DIV>
				<A HREF="http://www.getdropbox.com/">
					<IMG BORDER="0" ALT="dropbox" SRC="http://www.getdropbox.com/static/images/main_logo.png">
				</A>
				<HR SIZE="1" COLOR="#C0C0C0">
			</TD></TR>
			<TR>
				<TD><B>Contents of %(currentFolder)s:</B></TD>
				<TD align="right"><B>Size</B></TD>
				<TD align="right"><B>Date</B></TD>
			</TR>
"""
# accepts {genDate} {genVersion}
tableEnd = """
			<TR><TD colspan="3"><HR SIZE="1" COLOR="#C0C0C0"></TD></TR>
			<TR>
				<TD>
					<SPAN id=lastmodified><FONT COLOR="#808080">
						Index file generated on %(genDate)s with
						<A HREF="http://dl.getdropbox.com/u/552/pyndexer/index.html">pyndexer</A>
						v.%(genVersion)s
					</FONT></SPAN>
				</TD>
				<TD ALIGN="right" colspan=2>
					<IMG BORDER="0" ALT="dropbox" SRC="http://www.getdropbox.com/static/images/gray_logo.gif">
					<FONT COLOR="#808080">&copy; 2009 Dropbox</FONT>
				</TD>
			</TR>
		</TABLE>
"""



# parentLink
# used on child folders - the root folder do not provide this "up" link.
# accepts: {indexFileName}
htParentLink = """
			<TR id="dir"><TD colspan="3">
				<A HREF="../%(indexFileName)s">
					<IMG BORDER="0" ALT="up" SRC="http://www.getdropbox.com/static/images/icons/icon_spacer.gif"
						style="vertical-align:middle;" class="sprite s_arrow_turn_up" />
					Parent directory
				</A>
			</TD></TR>
"""

# directory row
# accepts: {dirName} {dirSize} {dirDate}
htDirRow = """
			<TR id="dir">
				<TD>
					<A HREF="%(dirName)s/index.html">
						<IMG BORDER="0" ALT="folder" SRC="http://www.getdropbox.com/static/images/icons/icon_spacer.gif"
							style="vertical-align:middle;" class="sprite s_folder" />
						%(dirName)s
					</A>
				</TD>
				<TD align="right">%(dirSize)s</TD>
				<TD align="right">%(dirDate)s</TD>
			</TR>
"""

# static image of the file type
# accepts: {fileType}
htFileTypeImg = """<IMG BORDER="0" ALT="file" SRC="http://www.getdropbox.com/static/images/icons/icon_spacer.gif" style="vertical-align:middle;" class="sprite %(fileType)s" />"""

# file to be played: radio button input
# accepts: {fileName}
htPlayerInput = """<input type="radio" name="playthis" title="Click to play" value="%(fileName)s" onclick="toggle(this)"/>"""

# file row
# accepts: {fileLink} {imgFile} {fileName} {radioButton} {fileSize} {fileDate}
htFileRow = """
			<TR id="file">
				<TD><A HREF="%(fileLink)s">%(imgFile)s %(fileName)s</A>%(radioButton)s</TD>
				<TD align="right">%(fileSize)s</TD>
				<TD align="right">%(fileDate)s</TD>
			</TR>
"""

# HTML ends here. From now on, the real script.

### helper things

# temporary file types dict for sprites
fileTypes = {
	('jpg', 'jpeg', 'jpe', 'ico', 'gif', 'png', 'bmp', 'psd', 'tif', 'tiff', 'cr2', 'crw', 'nef'):'s_page_white_picture',
	'pdf': 's_page_white_acrobat',
	('doc', 'docx', 'odt', 'sxw', 'rtf', 'out'): 's_page_white_word',
	'txt': 's_page_white_text',
	('xls', 'ods', 'sxc', 'csv', 'uos'): 's_page_white_excel',
	('ppt', 'odp', 'sxi', 'uop', 'keynote'): 's_page_white_powerpoint',
	('xml', 'py', 'cmd', 'bat', 'html', 'htm'): 's_page_white_code',
	'c': 's_page_white_c',
	'php': '_php',
	('rar', '7z', 'gz', 'bz2', 'tar', 'tgz'): 's_page_white_compressed',
	'iso': 's_page_white_dvd',
	('mp3', 'aac', 'wav', 'midi', 'flac', 'ogg', 'm4a', 'm4p', 'shn', 'aiff'): 's_page_white_sound',
	('dll', 'exe', 'com'): 's_page_white_gear',
	}
# on first run let's make the dict right
for exts, desc in fileTypes.items():
	if not type(exts) == type(tuple()): continue
	for ext in exts: fileTypes[ext] = desc
	del(fileTypes[exts])
del desc, exts

def ignoreThis(thisname):
	for r in ignorePattern:
		if re.match(r, thisname, re.IGNORECASE):
			vprint('    ign:  %s' % thisname)
			return True
	return False

def jwPlayThis(files):
	r = False
	# do we have files of the play type?
	for f in files:
		if path.splitext(f)[1][1:].lower() in jwPlayExts:
			r = True
			break
	# ... but, are player files around?
	for f in jwPlayerFiles:
		if f not in files:
			r = False
	return r

def vprint(msg):
	if verbose: print msg

def HumanSize(bytes):
	"""Humanize a given byte size"""
	if bytes/1024/1024:
		return "%.2f&nbsp;MB" % round(bytes/1024/1024.0,2)
	elif bytes/1024:
		return "%d&nbsp;KB" % round(bytes/1024.0)
	else:
		return "%d&nbsp;B&nbsp;&nbsp;" % bytes

def Usage():
	me = path.basename(argv[0])
	recdefaults = ('(default)','')
	if not recursiveDirs:
		recdefaults = ('','(default)')
	print """%s
  Creates index.html files for proper display of folder contents on a website.

Usage: %s [args] [Folder1] [...] [FolderN]
  Starts index creation on [Folder1] and others.
  If no folder name given, defaults to Current Working Directory (CWD)
""" % (me, me)
	print """Optional arguments:
  -h --help          This help text
  -v --verbose       Print indexed folders and files to be linked
  -i --ignore        Ignore this file pattern (python's regex re.match)
  -R --recursive     Index subfolders %s
  -N --nonrecursive  Index the specified folders only %s
""" % recdefaults
	raw_input("Press <ENTER> to exit...")
	exit(1)

### The function that actually does the job

def index(dirname):
	chdir(dirname)
	# we will use this dict to know the real directory sizes of all the tree (even including subdirs!)
	dirSizes = {}
	rootDir = getcwd()
	for curDir, dirs, files in walk(rootDir, topdown=not recursiveDirs):
		# indexed count
		indexedFiles, indexedDirs = 0, 0

		# sort by locale
		dirs.sort(key = lambda k: strxfrm( k ) )
		files.sort(key = lambda k: strxfrm( k ) )

		# calculate disk usage for this directory - caveat: the new index.html size will not count :)
		dirSizes[curDir] = dirSizes.get(curDir, 0) + sum([path.getsize(path.join(curDir,f)) for f in files])

		# generate index for this dir
		print('\nINFO: indexing "%s" (%s)' % (curDir, HumanSize(dirSizes[curDir]).replace('&nbsp;','')))

		# temp index file string
		fileIndex = ""

		# header and footer dicts
		htmlBaseDict = dict(
			currentFolder = path.basename(curDir),
			playerScript = '',
			aesScript = '',
			aesCipher = 'maindiv',
			maincontents = '',
			genDate = dt.now().strftime(dateFormat),
			genVersion = version,
		)

		# put player script if file requirements are met
		playableFolder = False
		if jwPlayThis(files):
			htmlBaseDict['playerScript'] = htPlayerScript
			playableFolder = True
		htmlBaseDict['playerScript'] = htPlayerScript

		# verify if we need to provide a parent link
		if not curDir == rootDir:
			vprint('    link: parent folder')
			fileIndex += htParentLink % {'indexFileName':indexFileName}

		# write folder links
		if recursiveDirs:
			for dirName in dirs:
				if ignoreThis(dirName): continue # jump ignored files
				fullDirName = path.join(curDir, dirName)
				fullDirDate = dt.fromtimestamp(path.getmtime(fullDirName)).strftime(dateFormat)
				d = { 'dirName': dirName, 'dirSize': HumanSize(dirSizes[fullDirName]), 'dirDate': fullDirDate}
				fileIndex += htDirRow % d
				vprint('    dir:  %s' % dirName)
				indexedDirs+=1

		# write file links
		for fileName in files:
			if ignoreThis(fileName): continue # jump ignored files
			fileExt = path.splitext(fileName)[1][1:].lower()
			fileLink = fileName
			if not fileExt in viewInBrowser:
				fileLink = '%s?dl' % fileName
			fullFileName = path.join(curDir, fileName)
			fullFileDate = dt.fromtimestamp(path.getmtime(fullFileName)).strftime(dateFormat)
			imgFile = htFileTypeImg % { 'fileType': fileTypes.get(path.splitext(fileName)[-1][1:].lower(),'s_page_white') }
			d = {   'fileLink': fileLink, 'imgFile': imgFile, 'fileName': fileName, 'radioButton': '',
				'fileSize': HumanSize(path.getsize(fullFileName)), 'fileDate': fullFileDate }
			if playableFolder and fileExt in jwPlayExts:
				d['radioButton'] = htPlayerInput % {'fileName': fileName}
			fileIndex += htFileRow % d
			vprint('    file: %s' % fileName)
			indexedFiles+=1

		# Show indexed file count
		print('    total:   %d dirs, %d files' % (len(dirs), len(files)))
		print('    indexed: %d dirs, %d files' % (indexedDirs, indexedFiles))

		# Constructing index file, without encryption first
		htmlBaseDict['maincontents'] = tableStart % htmlBaseDict + fileIndex + tableEnd % htmlBaseDict
		htmlContents = htmlBase % htmlBaseDict
		# XXX Unfortunately, we can't decrypt the file first without bugging the user,
		#     so will encrypted listings will always need to be remade. Any toughts?

		# see if we really need to write the new index file
		writeIndex = True
		if indexFileName in files:
			oldIndex = file(path.join(curDir, indexFileName)).read()
			# remove gen.date and version
			reg = re.compile('<SPAN id=lastmodified>.*?</SPAN>',re.DOTALL)
			oldIndex = re.sub(reg, '', oldIndex)
			newIndex = re.sub(reg, '', htmlContents)
			if oldIndex == newIndex:
				writeIndex = False
				print('    info:    listing not changed, no need to update')
			del oldIndex, newIndex

		if writeIndex and hascrypto and cryptTrigger in files:
			print('    info:    encryption file found, will encrypt listing.')
			password, password2 = '1','2'
			while 1:
				password  = raw_input('*** give password for encryption:\n    ')
				password2 = raw_input('*** confirm:\n    ')
				if password == password2: break
				print('WARN: passwords did not match, do it again.')
			ciphertext = encrypt(htmlBaseDict['maincontents'], password)
			htmlBaseDict['aesScript'] = aesScript
			htmlBaseDict['aesCipher'] = '\n'.join(wrap(ciphertext, 64))
			htmlBaseDict['maincontents'] = tableStart % htmlBaseDict + jsDecrypt + tableEnd % htmlBaseDict
			htmlContents = htmlBase % htmlBaseDict

		if writeIndex:
			htIndexFile = file(path.join(curDir, indexFileName),"w")
			htIndexFile.write(htmlContents)
			htIndexFile.close()

		# get real full directory usage:
		# the trick here is having the walk function be called from bottom up, so the subdirs get calculated first
		if recurseDirSize and curDir != rootDir: # climb up tree adding sizes to parents
			curDirSize = dirSizes[curDir]
			while curDir != rootDir: # no do...while in python led me to reuse curDir here :(
				curDir = path.dirname(curDir)
				dirSizes[curDir] = dirSizes.get(curDir, 0) + curDirSize

		# jump off the loop if not recursive
		if not recursiveDirs: break

try:
	from M2Crypto import EVP
	from os import urandom
	from hashlib import md5
	from cStringIO import StringIO
	from textwrap import wrap
	hascrypto = True
except ImportError:
	print('INFO: no M2Crypto support detected')
	hascrypto = False
def encrypt(string, password):
	prefix = 'Salted__'
	salt = urandom(8)
	hash = ['']
	for i in range(4):
		hash.append(md5(hash[i] + password + salt).digest() )
	key, iv =  hash[1] + hash[2], hash[3] + hash[4]
	del hash
	cipher = EVP.Cipher(alg='aes_256_cbc', key=key, iv=iv, op=1)
	inpb, outb = StringIO(string), StringIO()
	while 1:
		buf = inpb.read()
		if not buf: break
		outb.write(cipher.update(buf))
		outb.write(cipher.final())
	ciphertext = outb.getvalue()
	inpb.close()
	outb.close()
	return (prefix+salt+ciphertext).encode('base64')

# Execution
if __name__ == "__main__":
	# argument checking
	try:
		opts, dirnames = getopt.getopt(argv[1:], 'hvi:RN', ['help','verbose','ignore=','recursive','nonrecursive'])
	except getopt.GetoptError, err:
		print 'ERR:  ', str(err)
		Usage()

	verbose = True
	for o, a in opts:
		if o in ('-h','--help'):
			Usage()
		elif o in ('-v','--verbose'):
			verbose = True
			vprint('INFO: verbose mode set')
		elif o in ('-i','--ignore'):
			ignorePattern.append(a)
			vprint('INFO: adding "%s" to ignore filter' % a)
		elif o in ('-R','--recursive'):
			recursiveDirs = True
			vprint('INFO: recursive mode set')
		elif o in ('-N','--nonrecursive'):
			recursiveDirs = False
			vprint('INFO: nonrecursive mode set')
	for d in dirnames:
		if not path.isdir(d):
			print "Invalid folder name: %s" % d
			Usage()
	if not dirnames:
		print('WARN: No folder names given, will index:\n    "%s"' % getcwd())
		dirnames.append(getcwd())


	for dirname in dirnames:
		index(dirname)

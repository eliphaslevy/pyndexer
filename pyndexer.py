#!/usr/bin/env python
# coding: utf-8
#	pyndexer.py - Generates index.html recursively for a given directory
#	Copyleft Eliphas Levy Theodoro
#	This script was primarily made for use with the Public Folder
#	feature of Dropbox - http://www.dropbox.com
#	See more information and get help at http://forums.dropbox.com/topic.php?id=3075
#	Some ideas/code got from AJ's version at http://dl.dropbox.com/u/259928/www/indexerPY/index.html

version = "1.0ALPHA" # Request-for-comments ALPHA build!

helptext="""pyndexer - Python indexer for dropbox public folders
  Creates index.html files for proper display of folder contents on a website. Usage:

pyndexer [Folder1] [...] [FolderN]
  Starts index creation on [Folder1] and others.
  If no folder name given, will read configured sections on the INI file.
"""

CHANGELOG="""
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
2010-06-28.1.0 "mamooth version" ALPHA-TESTING
	Major split up of things, some rewrite
		External files for HTML, CSS, and javascript
		Global configuration file
		All command-line options dumped in favor of the config file
		You should designate a proper folder for this script from now on!
	Always non-recursive now, designate the folders to index in the config file
	Sync up with some changes from Andrew's 0.8 version (see forum thread for his changes)
	Will index all registered folders when called with no parameters
	Added the jwplayer to play the 'playinbrowser' files, like mp3 and mp4
	TODO:
		wxwindow GUI on no parameters to ease preferences file edition
		javascript sorting, like andrew's version, but I want it to be locale-aware!
	Known issues:
		item count for folders can give away that there is a hidden folder
"""


# temporary file types dict for sprites - try to make it ordered by type, somewhat.
fileTypes = {
# web common
	'pdf': 's_page_white_acrobat',
	'txt': 's_page_white_text',
	('css', 'js', 'htm', 'html', 'xml'): 's_page_white_code',
# images
	('gif', 'jpg', 'jpeg', 'jpe', 'png'): 's_page_white_picture',
	('ico', 'icns'): 's_page_white_picture',
	('bmp', 'psd', 'tif', 'tiff', 'cr2', 'crw', 'nef'):'s_page_white_picture',
# office
	('doc', 'docx', 'odt', 'sxw', 'rtf', 'out'): 's_page_white_word',
	('xls', 'ods', 'sxc', 'csv', 'uos'): 's_page_white_excel',
	('ppt', 'odp', 'sxi', 'uop', 'keynote'): 's_page_white_powerpoint',
# script/languages
	'java': 's_page_white_cup',
	'php': 's_page_white_php',
	'rb': 's_page_white_ruby',
	('c','h'): 's_page_white_c',
	('bat', 'cmd', 'py', 'pl', 'sh'): 's_page_white_code',
# compressed
	('7z', 'bz2', 'gz', 'rar', 'tar', 'tbz', 'tgz', 'zip'): 's_page_white_compressed',
# audio/video
	('aiff', 'aac', 'flac', 'm4a', 'midi', 'mp3', 'oga', 'ogg', 'shn', 'wav', 'wma'): 's_page_white_sound',
	('avi', 'm4v', 'mp4', 'mpeg', 'mpg', 'ogv', 'mkv', 'mov', 'wmv'): 's_film',
# others
	('dmg', 'iso'): 's_page_white_dvd',
	('dll', 'exe', 'com'): 's_page_white_gear',
	None: 's_page_white',
	}
# on first run let's make the dict right
for exts, desc in fileTypes.items():
	if not type(exts) == type(tuple()): continue
	for ext in exts: fileTypes[ext] = desc
	del(fileTypes[exts])
del desc, exts

import os, sys, codecs, ConfigParser
from hashlib import md5
from xml.dom import minidom
from datetime import datetime as dt
from locale import setlocale, strcoll, LC_ALL
from urllib import urlopen
from fnmatch import fnmatch
import sqlite3
from base64 import b64decode
from pickle import loads

hascrypto=False
try:
	from M2Crypto import EVP
	from cStringIO import StringIO
	from textwrap import wrap
	hascrypto = True
except ImportError:
	print('INFO: no M2Crypto support detected')

# On windows command line, python <=2.5 will not handle unicode correctly. This works around this.
def GetArgv():
	'''code adapted from http://code.activestate.com/recipes/572200/'''
	if sys.platform != 'win32':
		return sys.argv
	else:
		from ctypes import POINTER, byref, cdll, c_int, windll
		from ctypes.wintypes import LPCWSTR, LPWSTR
		GetCommandLineW = cdll.kernel32.GetCommandLineW
		GetCommandLineW.argtypes = []
		GetCommandLineW.restype = LPCWSTR
		CommandLineToArgvW = windll.shell32.CommandLineToArgvW
		CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
		CommandLineToArgvW.restype = POINTER(LPWSTR)
		cmd = GetCommandLineW()
		argc = c_int(0)
		argv = CommandLineToArgvW(cmd, byref(argc))
		if argc.value > 0:
				if argc.value - len(sys.argv) == 1:
						start = 1
				else:
						start = 0
				return [argv[i] for i in xrange(start, argc.value)]
		else:
				return []

# dropbox path finder borrowed from my pyDropConflicts
def GetDbFolder():
	if sys.platform == 'win32':
		assert os.environ.has_key('APPDATA'), Exception('APPDATA env variable not found')
		dbpath = os.path.join(os.environ['APPDATA'],'Dropbox')
	elif sys.platform in ('linux2','darwin'):
		assert os.environ.has_key('HOME'), Exception('HOME env variable not found')
		dbpath = os.path.join(os.environ['HOME'],'.dropbox')
	else: # FIXME other archs?
		raise Exception('platform %s not known, please report' % sys.platform)
	print "Locating dropbox's database (%s)" % sys.platform
	if os.path.isfile(os.path.join(dbpath,'config.db')):
		dbfn, dbfnver = os.path.join(dbpath,'config.db'), 2
	elif os.path.isfile(os.path.join(dbpath, 'dropbox.db')):
		dbfn, dbfnver = os.path.join(dbpath,'dropbox.db'), 1
	else:
		raise Exception('Dropbox database not found, is dropbox installed?')
	dbpath, dbfile = os.path.dirname(dbfn), os.path.basename(dbfn)

	print 'Reading dropbox database'
	lastdir = os.getcwd()
	os.chdir(dbpath)
	connection = sqlite3.connect(dbfile, isolation_level=None)
	os.chdir(lastdir)
	cursor = connection.cursor()
	cursor.execute('SELECT value FROM config WHERE key="dropbox_path"')
	row = cursor.fetchone()
	cursor.close()
	connection.close()
	print 'Done reading database'
	if row is None:
		if sys.platform == 'win32':
			import ctypes
			dll = ctypes.windll.shell32
			buf = ctypes.create_string_buffer(300)
			dll.SHGetSpecialFolderPathA(None, buf, 0x0005, False)
			dbfolder = os.path.join(buf.value,'My Dropbox')
		elif sys.platform in ('linux2','darwin'):
			dbfolder = os.path.join(os.environ['HOME'],'Dropbox')
		else:
			raise Exception('platform %s not known, please report' % sys.platform)
		print 'No dropbox path defined in config, using default location %s' % dbfolder
		return dbfolder
	else:
		if dbfnver == 1:
			return loads(b64decode(row[0]))
		elif dbfnver == 2:
			return row[0]
		else:
			raise Exception('Dropbox database version not correctly identified?')


def getElem(html,tag,tid=None,cls=None):
	'''Gets an element by ID or class'''
	for e in html.getElementsByTagName(tag):
		if tid:
			if e.getAttribute('id')==tid: return e
		elif cls:
			if e.getAttribute('class')==cls: return e
		else:
			return e
	return None


def delElem(e):
	'''removes a dom child from the parent'''
	e.parentNode.removeChild(e)
	e.parentNode=None


def setTextNodes(node,dic):
	for e in node.childNodes:
		if e.nodeType == e.TEXT_NODE:
			e.replaceWholeText(e.wholeText % dic)


def setEntryRow(tdata,dic):
	for td in tdata:
		if td.getAttribute('class') == u'row1':
			a = td.getElementsByTagName('a')[0]
			a.setAttribute('href', a.getAttribute('href') % dic)
			setTextNodes(a, dic)
			img = td.getElementsByTagName('img')[0]
			img.setAttribute('class', img.getAttribute('class') % dic)
		elif td.getAttribute('class') == u'row2':
			setTextNodes(td, dic)
		elif td.getAttribute('class') == u'row3':
			setTextNodes(td, dic)


def patmatch(somename, patlist): # magic!
	return sum([fnmatch(somename, pat) and 1 or 0 for pat in patlist])


def HumanSize(bytes):
	'''Humanize a given byte size'''
	if bytes/1024/1024/1024:
		return "%.2f GB" % round(bytes/1024/1024/1024.0,2)
	elif bytes/1024/1024:
		return "%.2f MB" % round(bytes/1024/1024.0,2)
	elif bytes/1024:
		return "%d KB" % round(bytes/1024.0)
	else:
		return "%d bytes" % bytes


def encrypt(string, password):
	'''Encrypt with AES some string'''
	prefix = 'Salted__'
	salt = os.urandom(8)
	hash = ['']
	for i in range(4):
		hash.append(md5(hash[i] + password.encode('ascii') + salt).digest() )
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


def lsdir(config, dirname):
	'''reads config, then list directories and files'''
	# FIXME this should be tweaked, it's re-reading a default config everytime.
	# at least these ones should not be needing to change based on folder
	confdict = {}
	allvars = (
		# global vars
		'my_source','pyndexer_url', 'dropbox_referrer','indexfilename','dateformat',
		# local vars
		'sortby','subdirsize','ignorepattern','viewinbrowser','playinbrowser','skipdir','password',
		)
	section = 'DEFAULT'
	splitdirname = dirname.replace(config.get('DEFAULT','publicfolder'),'')
	if splitdirname in config.sections():
		section = splitdirname
	for k in allvars:
		if k == 'dateformat': # date format needs to be raw because of the percents
			confdict[k] = config.get(section, k, 1).encode('ascii')
		elif k in ('ignorepattern','viewinbrowser','playinbrowser'): # this is list
			confdict[k] = [i.strip() for i in config.get(section, k).split(',')]
		else:
			confdict[k] = config.get(section, k)

	dirs, files = [], {}
	for name in os.listdir(dirname):
		if patmatch(name, confdict['ignorepattern']):
			continue # ignored folder/file
		n = os.path.join(dirname, name)
		if os.path.isdir(n):
			# disabled because of recursivity... need sub folder counts :( FIXME
			#if confdict[n]['skipdir'] == 'yes': continue # explicitly ignored folder
			dirs.append(n)
		elif os.path.islink(n) and os.path.isdir(os.path.realpath(n)):
			# XXX will choke in infinite loops, be aware. (untested!)
			dirs.append(os.path.abspath(os.path.realpath(n)))
		elif os.path.isfile(n):
			files[n]=dict(
				size=os.path.getsize(n),
				ctime=os.path.getmtime(n),
				)
		else:
			raise Exception('Ouch, do not know what to do with "%s". Abort.' % name)
	ctime = os.path.getmtime(dirname)
	size = sum([files[f]['size'] for f in files])

	return dict(confdict=confdict, ctime=ctime, size=size, count=len(dirs)+len(files), dirs=dirs, files=files)


def walkdir(config, indexingdict, parent, dirname):
	'''recursive list'''
	if indexingdict.has_key(dirname): return
	indexingdict[dirname] = lsdir(config, dirname)
	indexingdict[dirname]['parent'] = parent
	for subdir in indexingdict[dirname]['dirs']:
		walkdir(config, indexingdict, dirname, subdir)
		#XXX should I recursively add sizes and counts? (untested)
		#indexingdict[dirname]['size'] += indexingdict[subdir]['size']
		#indexingdict[dirname]['count'] += indexingdict[subdir]['count']


def getNodesDict(htmlbase):
	dic = {}
	dic['jsenc'] = getElem(htmlbase, 'script', 'jsenc')
	dic['encryptedrow'] = getElem(htmlbase, 'tr','encryptedrow')

	dic['jsswfobj'] = getElem(htmlbase, 'script', 'jsswfobj')
	dic['jsjwplay'] = getElem(htmlbase, 'script', 'jsjwplay')
	dic['jwplayerrow'] = getElem(htmlbase, 'tr','jwplayerrow')
	dic['playerdiv'] = getElem(htmlbase, 'span','playerdiv')

	dic['md5span'] = getElem(htmlbase, 'span','md5span')

	dic['title'] = getElem(htmlbase, 'title')
	dic['dropboxref'] = getElem(htmlbase, 'a','dropboxref')
	dic['currentfolderth'] = getElem(htmlbase, 'th','currentfolderth')
	dic['lastmodifiedth'] = getElem(htmlbase, 'th','lastmodifiedth')
	dic['pyndexerref'] = getElem(htmlbase, 'a','pyndexerref')

	dic['updirtr'] = getElem(htmlbase, 'tr','updirtr')
	dic['updirref'] = getElem(htmlbase, 'a','updirref')

	dic['maintablebody'] = getElem(htmlbase, 'tbody','maintablebody')
	dic['emptytr'] = getElem(htmlbase, 'tr','emptytr')
	dic['direntry'] = getElem(htmlbase, 'tr',None,'direntry')
	dic['fileentry'] = getElem(htmlbase, 'tr',None,'fileentry')
	for k in dic:
		if not dic[k]:
			raise Exception('Ooops, html template not ok. (%s parse failed)' % k)
	return dic


def index(template, indexingdict, dirname):
	'''write the index file.'''
	'''globals needed: config'''
	c = indexingdict[dirname]['confdict']
	if c['skipdir'] != 'no':
		return False
	htmlbase = minidom.parse(template)
	dic = getNodesDict(htmlbase)
	# remove base html objects for folders and files
	delElem(dic['emptytr'])
	delElem(dic['direntry'])
	delElem(dic['fileentry'])

	dirs = indexingdict[dirname]['dirs']
	files = indexingdict[dirname]['files']

	if c['sortby'] == 'name':
		dirnames  = sorted(dirs, cmp=strcoll)
		filenames = sorted(files, cmp=strcoll)
	elif c['sortby'] == 'size':
		dirnames  = sorted(dirs,  key = lambda k: indexingdict[k]['size'] )
		filenames = sorted(files, key = lambda k: files[k]['size'] )
	elif c['sortby'] == 'date':
		dirnames  = sorted(dirs,  key = lambda k: indexingdict[k]['ctime'] )
		filenames = sorted(files, key = lambda k: files[k]['ctime'] )
	else:
		raise Exception('on folder %s: unknown sortby method' % dirname)

	basedirname = os.path.basename(dirname)

	dropboxref = c['dropbox_referrer']
	dic['dropboxref'].setAttribute('href', dic['dropboxref'].getAttribute('href') % dict(dropboxref=dropboxref))

	setTextNodes(dic['title'], dict(currentfolder=basedirname))
	setTextNodes(dic['currentfolderth'].getElementsByTagName('b')[0], dict(currentfolder=basedirname))

	parent = indexingdict[dirname]['parent']
	if parent is None or indexingdict[parent]['confdict']['skipdir'] == 'yes':
		dic['updirtr'].parentNode.removeChild(dic['updirtr'])
		del(dic['updirtr'])
	else:
		setEntryRow(dic['updirtr'].getElementsByTagName('td'), dict(indexfilename=c['indexfilename']))

	for subdirname in dirnames:
		basesubdirname = os.path.basename(subdirname)
		skipdir = indexingdict[subdirname]['confdict']['skipdir']
		if skipdir == 'yes':
			continue # FIXME counts of parent are skewed because of this :( - see other FIXME on lsdir
			#Exception('Barf, skipdir==yes in index, should not happen. Report')
		if skipdir != 'no': # just make a link to requested file
			dirname_link = basesubdirname+'/'+skipdir
		else: # recursive
			dirname_link = basesubdirname+'/'+c['indexfilename']

		if c['subdirsize'] == 'size':
			size = HumanSize(indexingdict[subdirname]['size'])
		elif c['subdirsize'] == 'count':
			size = '%s items' % indexingdict[subdirname]['count']
		ctime = dt.fromtimestamp(indexingdict[subdirname]['ctime']).strftime(c['dateformat'])
		d = dict(
			dirname_link=dirname_link,
			dirname_text=basesubdirname,
			dirsize=size,
			dirdate=ctime,
			)
		newrow = htmlbase.importNode(dic['direntry'], True)
		newrow = dic['maintablebody'].appendChild(newrow)
		setEntryRow(newrow.getElementsByTagName('td'), d)

	playfiles = 0
	for filename in filenames:
		basefilename = os.path.basename(filename)

		size = HumanSize(files[filename]['size'])
		ctime = dt.fromtimestamp(files[filename]['ctime']).strftime(c['dateformat'])
		ftype = fileTypes.get(os.path.splitext(filename)[1].lstrip('.'), fileTypes[None])
		if patmatch(basefilename, c['viewinbrowser']):
			basefilenamelnk = basefilename
		else:
			basefilenamelnk = basefilename+'?dl'

		d = dict(filename_link=basefilenamelnk, filename_text=basefilename, filename_type=ftype, filesize=size, filedate=ctime)
		newrow = htmlbase.importNode(dic['fileentry'], True)
		newrow = dic['maintablebody'].appendChild(newrow)
		setEntryRow(newrow.getElementsByTagName('td'), d)

		if patmatch(basefilename, c['playinbrowser']):
			playfiles += 1
			img = newrow.getElementsByTagName('img')[0]
			audiolink="javascript:playthis(this, '%s');" % basefilename
			img.setAttribute('onclick', audiolink)

	if playfiles:
		dic['playerdiv'].childNodes[0].replaceWholeText('Some media files can be played online, click on the file icon.')
	else:
		delElem(dic['jsswfobj'])
		delElem(dic['jsjwplay'])
		delElem(dic['jwplayerrow'])

	if not getElem(htmlbase, 'tr', None, 'direntry') and not getElem(htmlbase, 'tr', None, 'fileentry'):
		newrow = htmlbase.importNode(dic['emptytr'], True)
		newrow = dic['maintablebody'].appendChild(newrow)

	gendate = dt.now().strftime(c['dateformat'])
	setTextNodes(dic['lastmodifiedth'], dict(gendate=gendate))
	a = dic['pyndexerref']
	a.setAttribute('href', a.getAttribute('href') % dict(pyndexer_url=c['pyndexer_url']))
	setTextNodes(a, dict(pyndexer_ver=version))

	tbodychildrenxml = ''
	for child in dic['maintablebody'].getElementsByTagName('tr'):
		if child.getAttribute('id') == 'encryptedrow': continue
		tbodychildrenxml += child.toxml().encode('utf-8', 'xmlcharrefreplace')

	if hascrypto and c['password'] != '':
		for child in dic['maintablebody'].getElementsByTagName('tr'):
			if child.getAttribute('id') == 'encryptedrow': continue
			delElem(child)
		for child in dic['maintablebody'].childNodes: # remove empty text
			if child.nodeType == child.TEXT_NODE:
				delElem(child)
		ciphertext = encrypt(tbodychildrenxml, c['password'])
		cipherwrap = '\n'.join(wrap(ciphertext, 64))
		dic['maintablebody'].setAttribute('title', cipherwrap)
	else:
		dic['maintablebody'].removeAttribute('title')
		delElem(dic['jsenc'])
		delElem(dic['encryptedrow'])

	# see if we really need to write the new index file.
	# using md5 to 'compress' info wrote. if the same, no need to rewrite
	# will add password on end of the md5 - (so will reindex on passwd change)
	md5digest = md5(tbodychildrenxml + c['password']).hexdigest()
	setTextNodes(dic['md5span'], dict(md5span=md5digest))

	indexfilename = os.path.join(dirname,c['indexfilename'])
	if os.path.isfile(indexfilename): # already there
		try:
			oldindex = minidom.parse(indexfilename)
			oldmd5span = getElem(oldindex, 'span', 'md5span')
			if oldmd5span:
				oldmd5digest = oldmd5span.firstChild.wholeText
				if md5digest == oldmd5digest: # wee, a disk write spared ;)
					return False
		except Exception: # uh, some problem parsing, or not generated by me, anyway, rewrite the index
			pass
	file(indexfilename,'wb').write(htmlbase.toxml().encode('utf-8', 'xmlcharrefreplace'))
	return True


def walkindex(template, indexingdict, dirname):
	'''recursive indexing, stopping on ignored children'''
	indexed = []
	if index(template, indexingdict, dirname):
		indexed.append(dirname)
		for subdir in indexingdict[dirname]['dirs']:
			indexed += walkindex(template, indexingdict, subdir)
	return indexed


# Execution
if __name__ == "__main__":
	setlocale(LC_ALL,"")
	config = ConfigParser.SafeConfigParser()
	# will use this as startup for my dependencies if not found in same dir as me
	base_source = "http://dl.dropbox.com/u/552/pyndexer/1.0/"
	argv = GetArgv()

	mypath = os.path.abspath(os.path.dirname(argv[0]))
	ini = os.path.join(mypath,'pyndexer.ini')
	if not os.path.isfile(ini):
		# FIXME should be less stubborn. I could have the defaults inside here.
		# Anyway, we need the default template file, so...
		print 'Downloading default INI file...'
		file(ini,'wb').write(urlopen(base_source+'pyndexer.empty.ini').read())
	print 'Reading config file %s' % ini
	config.readfp(codecs.open(ini,'r','utf-8'))

	template = os.path.join(mypath,'pyndexer.template.html')
	if not os.path.isfile(template):
		print 'Downloading default HTML template...'
		file(template,'wb').write(urlopen(base_source+'pyndexer.template.html').read())

	dbfolder = GetDbFolder()
	assert os.path.isdir(dbfolder), Exception('Did not find Dropbox folder, please report')
	publicfolder = os.path.join(dbfolder,'Public'+os.path.sep)
	config.set('DEFAULT','publicfolder', publicfolder)

	if len(argv) > 1:
		dirnames = [ os.path.abspath(d) for d in argv[1:] ]
	else:
		# XXX: should open a GUI at some point in the future
		try:
			if config.sections():
				print '\nWill process the following configured folders:'
				for d in sorted(config.sections()):
					print d
				raw_input('\nPress ^C to cancel, or ENTER to confirm:')
				dirnames = [ os.path.join(publicfolder, d) for d in sorted(config.sections()) ]
			else:
				raw_input('No configured folders found, ENTER to exit:')
				sys.exit(1)
		except KeyboardInterrupt:
			sys.exit(1)
	for d in dirnames:
		assert os.path.isdir(d), Exception(u'%s is not a folder' % d)

	indexingdict = {}
	indexed = []
	print '\nStarting index\n'
	for dirname in dirnames:
		fulldirname = os.path.abspath(dirname)
		if fulldirname in indexed: continue
		# W:walking, I:indexing, then OK or Ign (up-to-date or explicitly ignored)
		print '%s: [' % dirname.replace(config.get('DEFAULT','publicfolder'),''),
		try:
			print 'W',
			walkdir(config, indexingdict, None, fulldirname)
			print 'I',
			result = walkindex(template, indexingdict, fulldirname)
			if result:
				indexed += result
				print 'OK ] (%d folders)' % len(result)
			else:
				print 'Ign ]'
		except Exception, e:
			print 'Exception raised, aborting:'
			print e
			raise
	if indexed:
		print '\nFinished. Folders indexed:'
		for d in indexed: print d
	else:
		print '\nFinished. No folders where indexed (up-to-date or ignored).'
	raw_input('Press ENTER to exit...')
	# That's all folks!

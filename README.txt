   Original: http://dl.dropbox.com/u/552/pyndexer/README-FIRST.html

  Description of the script

   As it is now, public files are only public if you know the address of
   them.

   As a workaround, this script generates an index.html for a folder and all
   folders within, with the public links for all files inside.

  ChangeLog

   Read it on the script itself, or the pyndexer.html auto-generated
   beautifully colored file :)
   As of now, it's in the 0.7 version, released in 2010-02-04.

  License

   Copyleft. Feel free to copy, edit, and share your thoughts and patches ;)

   Dropbox Forum's discussion thread:
   http://forums.dropbox.com/topic.php?id=3075

  Install

   Windows (XP, Vista, 7):
   Download pyndexer.exe if you do not have a python environment. Maybe you
   need MSVCR71.dll too, it is there to download if needed.
   There is also a nocrypto version that is half the size if you do not want
   AES encryption support.

   Linux, OSX:
   Download the pyndexer.py script and set its permission to execute (chmod
   +x pyndexer.py or use your "explorer" thing).

  Usage

 pyndexer [args] [Folder1] [...] [FolderN]
   Starts index creation on [Folder1] and others.
   If no folder name given, defaults to Current Working Directory (CWD)
 Optional arguments:
   -h --help          This help text
   -v --verbose       Print indexed folders and files to be linked
   -i --ignore        Ignore this file pattern (python's regex re.match)
   -R --recursive     Index subfolders (default)
   -N --nonrecursive  Index the specified folders only

   It is a terminal (console, text-only, white-on-black scary!) program!
   Run it from your favorite terminal (shell) program and pass to it the name
   of the folder you want to index as the first argument. If no arguments are
   passed, it will index the Current Working Directory ($CWD) - the place
   from where you ran it.
   You can drag and drop a folder to the script to automatically "pass" it as
   the argument.

   If in windows (using the EXE version), you can make a place a shortcut to
   it on the special folder "Send To" (open explorer and go to "shell:sendto"
   to open it) so you can right-click some public folder, go to the Send To
   context menu and select pyndexer, and it will index it.

  Encryption

   pyndexer now supports AES-256-CBC encryption of the file listing, if you
   want to keep the files somewhat hidden. The EXE version includes the AES
   support, but if you use the script version, you will need M2Crypto
   installed. Use apt-get or something else to install it, like:

 apt-get install python-m2crypto (ubuntu)
 easy_install m2crypto (python's setuptools)

   Just put a file named "encrypt.txt" on some folder and it will prompt you
   to provide a password for this folder's listing when indexing.
   It will NOT encrypt the files, just the links that point to them, so
   bewarned. Thanks to Vincent Cheung's jsencript the user's browser will
   decrypt it on-the-fly.

  WARNING: DEFAULTS TO WORK RECURSIVELY.

   Meaning it WILL overwrite ALL index.html files in the pointed folder and
   subfolders!
   Side note: You can always use the revisions feature of dropbox to revert a
   lost index.html.

  Bonus

   If you want to be able to listen to some MP3 on your public folder, go to
   the "playertest" subfolder and get the player.swf and swfobject.js files
   and put on the folder where the music files are.
   It will NOT make a whole MP3 library playable for you, it was deliberately
   done this way to be difficult to share your entire music with the world.
   Remember, dropbox is NOT a content distribution system!

from distutils.core import setup
import py2exe, os, shutil
import sys
sys.path.append('../../dbconfig')
py = "pyndexer"
desc = "Python Public Dropbox Indexer"
ver = "1.1.1"
p2e_opts = dict(
	bundle_files=1,
	compressed=1,
	optimize=2,
	ascii=1,
	packages=["encodings"],
	dist_dir=".",
	includes=["dbconfig"],
	dll_excludes=["msvcr71.dll"],
)
setup(name=py, version=ver, description=desc, zipfile=None,
	console=[dict(script=py+'.py', dest_base=py)],
	options=dict(py2exe=p2e_opts),)

os.system('upx %s.exe' % py)
import colorize
colorize.colorize_file('%s.py' % py, file('%s.html' % py,'w'))
try:
	shutil.rmtree('build/')
except:
	pass

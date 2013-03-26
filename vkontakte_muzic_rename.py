#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

_path = os.path.dirname(os.path.realpath(__file__))
input_files = sys.argv[1:]
if len(input_files) == 0:
	print "Files not found!"
	sys.exit(0)

def ffmpeg(s,d,track):
	d_tmp = d+'.converting.mp3'
	app = 'ffmpeg'
	app_path = os.path.join(_path,'bin',app)
	atr = [ app_path,
				'-y',
				'-i',s,
				'-threads','auto',
				'-vsync','2'
	]
	def unicode_string(string):
		return string
	if 'Name' in track:
		atr.append('-metadata')
		atr.append('title='+unicode_string(track['Name'].strip()))
	if 'Artist' in track:
		atr.append('-metadata')
		atr.append('artist='+unicode_string(track['Artist'].strip()))
	atr.append('-acodec')
	atr.append('copy')
	atr.append(d_tmp)
	subprocess.Popen(atr, stdout=subprocess.PIPE).communicate()[0]
	os.rename(d_tmp,d+'.mp3')

for file in input_files:
	f_name = os.path.splitext(os.path.basename(file))[0]
	params = f_name.split(' - ',1)
	if len(params) > 1:
		params = {'Name':params[0],'Artist':params[1]}
	ffmpeg(file,os.path.join(_path,'mp3',f_name),params)
#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
import subprocess
import json
import platform
import ConfigParser
import codecs

_save_param = []
_path = os.path.dirname(os.path.realpath(__file__))
_is_win = 0
_is_lin = 0
if platform.system() == 'Windows':
	_is_win = 1
	reload(sys)
	sys.setdefaultencoding("cp1251")
if platform.system() == 'Linux':
	_is_lin = 1

config = ConfigParser.ConfigParser()
config_name = 'config.cfg'
if not os.path.exists(os.path.join(_path,config_name)):
	print "Config file ("+config_name+") not found!"
	sys.exit(0)
else:
	config.readfp(codecs.open(os.path.join(_path,config_name), 'r', 'utf-8'))

_out = config.get('Main', 'output')
	
input_files = sys.argv[1:]
if len(input_files) == 0:
	print "Files for converting not found!"
	sys.exit(0)

def ffmpeg(s,d,params):
		print 'FFmpeg: open',s
		out_ext = '.m4v'
		d_tmp = d+'.converting'+out_ext
		app = 'ffmpeg' + ('.exe' if _is_win else '_linux' if _is_lin else '')
		app_path = os.path.join(_path,'bin',app)
		atr = [ app_path,
					'-y',
					'-i',s,
					'-threads','0',
					'-preset','slow',
					'-strict','-2'
		]
		atr += params
		atr.append(d_tmp)
		subprocess.Popen(atr, stdout=subprocess.PIPE).communicate()[0]
		if os.path.getsize(d_tmp) == 0:
			os.remove(d_tmp)
			return 0
		else:
			os.rename(d_tmp,d+out_ext)
			return 1

def get_info(s):
	print 'FFprobe: open',s
	app = 'ffprobe' + ('.exe' if _is_win else '_linux' if _is_lin else '')
	app_path = os.path.join(_path,'bin',app)
	atr = [ app_path,
				'-i','"'+s.replace("`","\`")+'"',
				'-print_format','json','-show_streams', '-show_format'
	]
	process = subprocess.Popen((' ').join(atr), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	json_out = ''
	writeing = 0
	while True:
		buff = process.stdout.readline().replace('\r','').replace('\n','')
		if buff == '' and process.poll() != None: 
			break
		if writeing == 0 and len(buff) > 0 and buff[0] == '{':
			writeing = 1
		if writeing == 0 and len(buff) > 0 and buff.strip() == '"streams": [':
			buff = "{" + buff
			writeing = 1
		if writeing:
			json_out += buff
		if writeing and len(buff) > 0 and buff[0] == '}':
			writeing = 0
	process.wait()
	return json.loads(json_out)

def select_streams(info):
	global _save_param
	if not 'streams' in info:
		print('Streams not found!')
		return ['-c','copy','-c:v','h264','-c:a','aac'];
	streams = {}
	v_count = 0
	a_count = 0
	o_count = 0
	for stream in info['streams']:
		def g(i,e=''):
			return str(stream[i]) if i in stream else e
		l_id = g('index','-1')
		l_lang = ''
		l_title = ''
		if 'tags' in stream:
			l_lang = stream['tags']['language'] if 'language' in stream['tags'] else ''
			l_title = stream['tags']['title'] if 'title' in stream['tags'] else '[No title]'
		l_type = g('codec_type')
		l_codec = g('codec_name')
		if l_type == 'video':
			v_count += 1
		elif l_type == 'audio':
			a_count += 1
		else:
			o_count += 1
		l_sample_rate = g('sample_rate')
		l_bit_rate = g('bit_rate')
		l_channel = g('channels')
		l_resol = g('width')+'x'+g('height')
		l_def = stream['disposition']['default']
		if len(l_resol) == 1: l_resol = ''
		streams[l_id] = {
			'type'  : l_type,
			'codec' : l_codec,
			'bit_rate' : l_bit_rate
		}
		print 'Stream:',l_id, \
				('('+l_lang+')' if l_lang!='' else '') + \
				(', [D]' if l_def else '') + \
				(', '+l_bit_rate if l_bit_rate else '') + \
				(', '+l_type.capitalize()+': '+l_codec) + \
				(', ch '+l_channel if l_channel else '') + \
				(', '+l_resol if l_resol else '') + \
				(', '+l_title if l_title else '')
	save_query = ''
	if v_count == 1 and a_count == 1 and o_count == 0:
		stream_arr = '0 1'
	elif len(_save_param) == 0:				
		stream_arr = raw_input('Enter stream numers (spase for split): ')
		save_query = raw_input('Use for all? Enter (y/n): ')
	else:
		stream_arr = _save_param
	if len(save_query.lower()) > 0 and save_query.lower()[0] == 'y':
		_save_param = stream_arr
	stream_arr = stream_arr.split(' ')
	param_map = []
	param_encode = []
	n = 0
	for indx in stream_arr:
		param_map.append('-map')
		param_map.append('0:'+indx)
		if streams[indx]['type'] == 'audio' and streams[indx]['codec'] != 'aac':
			param_encode.append('-c:'+str(n))
			param_encode.append('aac')

			#param_encode.append('-q:'+str(n))
			#param_encode.append('1')
			
			if len(streams[indx]['bit_rate']) > 0:
				param_encode.append('-b:'+str(n))
				param_encode.append(streams[indx]['bit_rate'])
			n += 1
			continue
		if streams[indx]['type'] == 'video' and streams[indx]['codec'] != 'h264':
			param_encode.append('-c:'+str(n))
			param_encode.append('h264')

			#param_encode.append('-q:'+str(n))
			#param_encode.append('1')

			n += 1
			continue
		if streams[indx]['type'] == 'subtitle' and streams[indx]['codec'] == 'subrip':
			param_encode.append('-c:'+str(n))
			param_encode.append('mov_text')
			n += 1
			continue

		param_encode.append('-c:'+str(n))
		param_encode.append('copy')
		n += 1

	return param_map + param_encode

for file in input_files:
	if len(_out) == 0:
		_out = os.path.dirname(file)
	f_name = os.path.splitext(os.path.basename(file))[0]
	f_name = os.path.join(_out,f_name)
	info = get_info(file)
	params = select_streams(info)
	ffmpeg(file,f_name,params)
	print "Dune!",f_name

print "All dune!"
for file in input_files:
	print "From folder:", os.path.dirname(file)
	print "File:", os.path.basename(file)
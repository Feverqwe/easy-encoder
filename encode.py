#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import sys
import subprocess
import json
#sound_num = raw_input('Hi! ')
#print sound_num
_path = os.path.dirname(os.path.realpath(__file__))

input_files = sys.argv[1:]
if len(input_files) == 0:
	input_files = []
	input_files.append('/Volumes/320/Dumb & Dumber.1994.BDRip-AVC.Unrated.mkv')

def ffmpeg(s,d,params):
        print 'FFmpeg: open',s
        out_ext = '.m4v'
        d_tmp = d+'.converting'+out_ext
        app = 'ffmpeg'
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
	app = 'ffprobe'
	app_path = os.path.join(_path,'bin',app)
	atr = [ app_path,
				'-i','"'+s.replace("`","\`").replace("\"","\\\"")+'"',
				'-print_format','json','-show_streams', '-show_format'
	]
	process = subprocess.Popen((' ').join(atr), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	json_out = ''
	writeing = 0
	while True:
		buff = process.stdout.readline()
		if buff == '' and process.poll() != None: 
			break
		if buff[0] == '{':
			writeing = 1
		if writeing:
			json_out += buff
	process.wait()
	return json.loads(json_out)

def select_streams(info):
	if not 'streams' in info:
		print('Streams not found!')
		return '';
	streams = {}
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
	stream_arr = raw_input('Select stream! ').split(' ')
	param_map = []
	param_encode = []
	n = 0
	for indx in stream_arr:
		param_map.append('-map')
		param_map.append('0:'+indx)
		if streams[indx]['type'] == 'audio' and streams[indx]['codec'] != 'aac':
			param_encode.append('-c:'+str(n))
			param_encode.append('aac')
			if len(streams[indx]['bit_rate']) > 0:
				param_encode.append('-b:'+str(n))
				param_encode.append(streams[indx]['bit_rate'])
			n += 1
			continue
		if streams[indx]['type'] == 'video' and streams[indx]['codec'] != 'h264':
			param_encode.append('-c:'+str(n))
			param_encode.append('h264')
			n += 1
			continue
		if streams[indx]['type'] == 'subtitle':
			param_encode.append('-c:'+str(n))
			param_encode.append('mov_text')
			n += 1
			continue

		param_encode.append('-c:'+str(n))
		param_encode.append('copy')
		n += 1

	return param_map + param_encode

for file in input_files:
	f_name = os.path.splitext(os.path.basename(file))[0]
	f_name = os.path.join(_path,f_name)
	info = get_info(file)
	params = select_streams(info)
	ffmpeg(file,f_name,params)

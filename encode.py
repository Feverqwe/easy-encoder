#!/usr/bin/python3
# -*- coding: UTF-8 -*-
import sys
import os
import subprocess
import json
import platform
import codecs
import re

_config = {
    "ffmpeg_path": os.path.join("bin","ffmpeg"),
    "ffprobe_path": os.path.join("bin","ffprobe"),
    "path": os.path.dirname(os.path.realpath(__file__)),
    "output": "",
    "force_stream_select": 0,
    "force_audio_encode": 0,
    "force_video_encode": 0,
    "enable_video_scale": 1,
    "video_scale_width": 1366,
    "out_extension": "mp4",
    "out_prefix": "",
    "additional_ffmpeg_attr": ["-threads", "4"],
    "search_file_ext": ["avi", "mkv", "ts", "wma", "wmv", "mp4"]
}

config_filename = 'config.json'
config_path = os.path.join(_config['path'], config_filename)
if not os.path.exists(config_path):
    print ("Config file (" + config_filename + ") not found!")
    sys.exit(0)
else:
    with open(config_path) as json_file:
        config_file = json.load(json_file)
        for key in config_file:
            _config[key] = config_file[key]


_save_rewrite = ''
_save_param = []

_auto_output_path = 0
if len(_config['output']) == 0:
    _auto_output_path = 1

_is_win = 0
_is_lin = 0
if platform.system() == 'Windows':
    _is_win = 1
if platform.system() == 'Linux':
    _is_lin = 1

_input_files = sys.argv[1:]

print (sys.argv)



if len(_input_files) == 1:
    folder = _input_files[0]
    if os.path.isdir(folder):
        _input_files = []
        for file in os.listdir(folder):
            full_path = os.path.realpath(os.path.join(folder, file))
            if os.path.isdir(full_path):
                continue
            ex = file.split('.')[-1]
            if ex in _config['search_file_ext']:
                _input_files.append(full_path)
    print ("Loaded files:", '\n'.join(_input_files))

if len(_input_files) == 0:
    print ( "Files for converting not found!" )
    sys.exit(0)

class encode_file:
    file = None
    name = None
    folder = None
    out_ext = None
    out_folder = None
    out_path = None
    ff_probe = _config['ffprobe_path']
    ff_mpeg = _config['ffmpeg_path']
    ff_mpeg_path = None
    ff_probe_path = None
    _path = os.path.dirname(os.path.realpath(__file__))
    streams = []
    video_codec = None
    audio_codec = None
    subtitle_codec = None
    out_prefix = None
    ff_out_tmp_name = None

    def get_best_codec(self):
        atr = [self.ff_mpeg_path,
               '-codecs'
        ]
        out = subprocess.getoutput(atr)
        #out, err =  p.communicate()

        #print "==========output=========="
        #print out
        #if err:
        #    print "========= error ========"
        #    print err
        for line in out.split("\n"):
            if len(line) < 3:
                continue
            if line[0] == ' ':
                line = line[1:]
            is_encode = 1 if line[1] == 'E' else 0
            if is_encode == 0:
                continue
            line = re.sub(r"\s+",' ',line).strip().split(' ')
            if len(line) < 2:
                continue
            codec = line[1]
            a_l = 0
            v_l = 0
            s_l = 0
            if self.out_ext == 'm4v' or self.out_ext == 'mp4' or self.out_ext == 'mkv':
                if codec == 'libfdk_aac':
                    if a_l > 4: continue
                    self.audio_codec = codec
                    a_l = 4
                if codec == 'libfaac':
                    if a_l > 3: continue
                    self.audio_codec = codec
                    a_l = 3
                if codec == 'aac':
                    if a_l > 2: continue
                    self.audio_codec = codec
                    a_l = 2
                if codec == 'libvo_aacenc':
                    if a_l > 1: continue
                    self.audio_codec = codec
                    a_l = 1
                if codec == 'h264':
                    if v_l > 1: continue
                    self.video_codec = codec
                    v_l = 1
                if codec == 'libx264':
                    if v_l > 2: continue
                    self.video_codec = codec
                    v_l = 2
                if codec == 'subrip' and self.out_ext == 'mkv':
                    if s_l > 2: continue
                    self.subtitle_codec = codec
                    s_l = 2
                if codec == 'mov_text':
                    if s_l > 1: continue
                    self.subtitle_codec = codec
                    s_l = 1

    def get_encode_params(self, stream):
            force = 0
            need_scale = 0
            default = ['-c:%stream_num%','copy']
            if stream['codec_name'] in ['mjpeg','png']:
                return default
            if _config['force_video_encode'] and stream['codec_type'] == 'video':
                force = 1
            if _config['enable_video_scale'] and stream['codec_type'] == 'video' and stream['width'] > _config['video_scale_width']:
                force = 1
                need_scale = 1
            if _config['force_audio_encode'] and stream['codec_type'] == 'audio':
                force = 1
            if force == 0 and self.out_ext in ['m4v','mp4'] and stream['codec_name'] in ['h264', 'aac']:
                return default
            if force == 0 and self.out_ext in ['mkv'] and stream['codec_name'] in ['h264', 'aac', 'ac3']:
                return default
            if self.out_ext in ['m4v','mp4'] and stream['codec_name'] in ['mov_text']:
                return default
            if self.out_ext in ['mkv'] and stream['codec_name'] in ['mov_text', 'subrip']:
                return default

            stream['encode_params'] = default

            if stream['codec_type'] == 'video':
                if self.out_ext in ['m4v','mp4','mkv']:
                    stream['encode_params'] = ['-c:%stream_num%',self.video_codec,'-preset', 'slow','-crf', '18','-maxrate','10M'] #crf 18 replace to qp 20!
                    if need_scale:
                        stream['encode_params'] += ["-filter:%stream_num%", "scale=w=" + str(_config['video_scale_width']) + ":h=trunc(" + str(_config['video_scale_width']) + "/dar/2)*2:flags=1"]
            elif stream['codec_type'] == 'audio':
                if self.out_ext in ['m4v','mp4','mkv']:
                    stream['encode_params'] = ['-c:%stream_num%',self.audio_codec] #,'-aq', '100'
                    if 'bit_rate' in stream:
                        stream['encode_params'] += ['-b:%stream_num%',stream['bit_rate']]
                    #if 'channels' in stream:
                    #    stream['encode_params'] += ['-ac:%stream_num%',str(stream['channels'])]
                    if 'sample_rate' in stream:
                        stream['encode_params'] += ['-ar:%stream_num%',stream['sample_rate']]
                    if self.audio_codec == 'aac':
                        stream['encode_params'] += ['-strict','-2']
            elif stream['codec_type'] == 'subtitle':
                if self.out_ext in ['m4v','mp4','mkv']:
                    stream['encode_params'] = ['-c:%stream_num%',self.subtitle_codec]

            return stream['encode_params']

    def get_stream_list(self, file):
        print ( "Read file info: "+os.path.basename(file) )
        atr = [self.ff_probe_path, '-show_format', '-of', 'json', '-show_streams', '-loglevel', 'quiet', file]
        out = subprocess.getoutput(atr)
        #print "==========output=========="
        #print out
        #if err:
        #    print "========= error ========"
        #    print err
        probe = json.loads(out)
        tmp_strem_list = []
        strem_list = {'streams':[],'file':None}
        if 'streams' in probe:
            tmp_strem_list = probe['streams']
        for stream in tmp_strem_list:
            item = stream
            language = stream['tags']['language'] if 'tags' in stream and 'language' in stream['tags'] else ''
            default = '[D]' if 'disposition' in stream and 'default' in stream['disposition'] else ''
            bit_rate = str(stream['bit_rate']) if 'bit_rate' in stream else ''
            stream_type = stream['codec_type'] if 'codec_type' in stream else ''
            stream_codec = stream['codec_name'] if 'codec_name' in stream else ''
            channels = str(stream['channels']) if 'channels' in stream else ''
            resolution = ''
            if 'width' in item and 'height' in item:
                resolution = str(item['width'])+'x'+str(item['height'])
            title = stream['tags']['title'] if 'tags' in stream and 'title' in stream['tags'] else ''
            filename = stream['tags']['filename'] if 'tags' in stream and 'filename' in stream['tags'] else ''
            mimetype = stream['tags']['mimetype'] if 'tags' in stream and 'mimetype' in stream['tags'] else ''

            item['desc'] = ''
            if len(language) > 0:
                item['desc'] += '('+language+')'
            if len(default) > 0:
                item['desc'] += default
            if len(bit_rate) > 0:
                item['desc'] += ', '+bit_rate
            if len(stream_type) > 0 and len(stream_codec) > 0:
                item['desc'] += ', '+stream_type.capitalize() +': '+stream_codec
            if len(channels) > 0:
                item['desc'] += ', ch'+channels
            if len(resolution) > 0:
                item['desc'] += ', '+resolution
            if len(title) > 0:
                item['desc'] += ', '+title
            if len(filename) > 0:
                item['desc'] += ', attach: '+filename
            if len(mimetype) > 0:
                item['desc'] += ' ('+mimetype+')'

            if len(stream_codec) == 0:
                print ( "Warning! Unknown codec in stream! Skiped!\n\tStream: "+str(item['index'])+' '+item['desc'] )
                continue

            item['encode_params'] =self.get_encode_params(stream)
            strem_list['streams'].append(item)

        strem_list['file'] = os.path.realpath(file)
        self.streams.append(strem_list)

    def get_sub_files(self):
        file_list = []
        for fn in os.listdir(self.folder):
            if fn[:len(self.name)] == self.name and fn.split('.')[-1] == 'srt':
                file_list.append(os.path.realpath( os.path.join( self.folder, fn ) ) )
        file_list.sort()
        for f in file_list:
            self.get_stream_list( f )

    def ffmpeg(self, atr):
        atr.append(self.ff_out_tmp_name)
        print ( "="*60 )
        print ( "Command line:", ' '.join(atr) )
        print ( "="*60 )
        subprocess.call(atr)
        #out, err =  p.communicate()
        if os.path.getsize(self.ff_out_tmp_name) == 0:
            os.remove(self.ff_out_tmp_name)
            return 0
        #if err:
        #    return 0
        os.rename(self.ff_out_tmp_name, self.out_path)
        return 1

    def select_streams(self):
        global _save_param
        _no_stream_mode = 0
        streams = []
        file_num = 0
        for f in self.streams:
            if file_num == 0 and len(f['streams']) == 0:
                print ( "In file ("+f['file']+") don't found any streams! Go in to NO_STREAM_MODE!" )
                _no_stream_mode = 1
            for stream in f['streams']:
                streams.append([stream,f['file']])
            file_num += 1

        if _no_stream_mode:
            self.ffmpeg(['-y','-i',self.file] + _config['additional_ffmpeg_attr'] + ['-c', 'copy', '-c:v', self.video_codec, '-c:a', self.audio_codec, '-c:s', self.subtitle_codec])
            return

        save_query = ''
        num = 0
        l_f = ''
        v_c = 0
        a_c = 0
        s_c = 0
        all_array = []
        for s in streams:
            stream = s[0]
            if l_f != s[1]:
                print ( "File: "+os.path.basename(s[1]) )
                l_f = s[1]
            if stream['codec_type'] == 'video':
                v_c+=1
            if stream['codec_type'] == 'audio':
                a_c+=1
            if stream['codec_type'] == 'subtitle':
                s_c+=1
            try:
                print ( 'Stream:', num, stream['desc'] )
            except:
                import urllib
                print ( 'Stream:', num, "<Bad name>" )
            all_array.append(num)
            num += 1
        if v_c == 1 and a_c == 1 and s_c == 0 and _config['force_stream_select'] == 0:
            stream_arr = [0, 1]
        elif len(_save_param) == 0:
            stream_arr = input('Enter stream numbers (spase for split, -1 for all): ')
            if len(_input_files) > 1:
                save_query = input('Use for all? Enter (y/n): ').lower()
            if stream_arr == '-1':
                stream_arr = all_array
            else:
                stream_arr = stream_arr.split(' ')
            if len(save_query) > 0 and save_query[0] == 'y':
                _save_param = stream_arr
        else:
            stream_arr = _save_param
        input_ = []
        params = []
        maps = []
        fn = ''
        file_num = -1
        stream_num = 0
        for num in stream_arr:
            item = streams[int(num)]
            stream = item[0]
            if item[1] != fn:
                fn = item[1]
                input_ += ['-i',fn]
                file_num += 1
            maps += [ '-map', str(file_num)+':'+str(stream['index']) ]
            stream_params = []
            for param in stream['encode_params']:
                if type(param) == str:
                    stream_params.append(param.replace('%stream_num%',str(stream_num)))
                else:
                    stream_params.append(param)
            params += stream_params
            stream_num += 1

        atr = []
        atr.append(self.ff_mpeg_path)
        atr.append('-y')

        atr += input_

        atr +=_config['additional_ffmpeg_attr']
        atr += maps
        atr += params

        self.ffmpeg(atr)

    def run(self):
        global _save_rewrite
        save_rewrite = ''
        if os.path.exists(self.out_path):
            print ( "Output file exists!", self.out_path )
            if len(_save_rewrite) == 0:
                rewrite = input('Rewrite file? Enter (y/n): ').lower()
                if len(_input_files) > 1:
                    save_rewrite = input('Use for all? Enter (y/n): ').lower()
                if len(save_rewrite) > 0 and save_rewrite[0] == 'y':
                    _save_rewrite = rewrite
            else:
                rewrite = _save_rewrite
            if len(rewrite) > 0 and rewrite[0] == 'y':
                os.remove(self.out_path)
            else:
                return
        self.get_best_codec()
        self.get_stream_list(self.file)
        self.get_sub_files()
        self.select_streams()
        print ( "Dune!", self.name + '.' + self.out_ext )

    def __init__(self, filename):
        self.streams = []
        self.video_codec = None
        self.audio_codec = None
        self.subtitle_codec = None
        self.out_prefix = _config['out_prefix']
        self.ff_probe_path = os.path.join(self._path, self.ff_probe) + ('.exe' if _is_win else '')
        self.ff_mpeg_path = os.path.join(self._path, self.ff_mpeg) + ('.exe' if _is_win else '')
        self.file = os.path.realpath(filename)
        self.folder = os.path.dirname(self.file)
        self.name = os.path.splitext(os.path.basename(self.file))[0]
        if _auto_output_path:
            self.out_folder = self.folder
        else:
            self.out_folder = os.path.realpath(_config['output'])
        self.out_ext = _config['out_extension']
        self.ff_out_tmp_name = os.path.join(self.out_folder, self.out_prefix + self.name+ '.converting.' + self.out_ext);
        self.out_path = os.path.join(self.out_folder, self.out_prefix + self.name + '.' + self.out_ext)
        self.run()


for file in _input_files:
    encode_file(file)

print ( "All dune!" )
for file in _input_files:
    print ( "From folder:", os.path.dirname(file) )
    print ( "File:", os.path.basename(file) )
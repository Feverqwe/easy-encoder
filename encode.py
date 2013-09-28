#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
import subprocess
import json
import platform
import ConfigParser
import codecs
import re

_acodec = ''
_acodec_param = ''
_vcodec = ''
_app_probe = 'ffprobe' #.exe _linux
_app_encode = 'ffmpeg'

#_app_probe = 'avprobe'
#_app_encode = 'avconv'

_out_ext = '.m4v'

_save_param = []
_path = os.path.dirname(os.path.realpath(__file__))

_force_stream_select = 0
_force_audio_encode = 0
_force_video_encode = 0

_scale = 1
_scale_w = 1366
#1280

config = ConfigParser.ConfigParser()
config_name = 'config.cfg'
if not os.path.exists(os.path.join(_path, config_name)):
    print "Config file (" + config_name + ") not found!"
    sys.exit(0)
else:
    config.readfp(codecs.open(os.path.join(_path, config_name), 'r', 'utf-8'))

try:
    _out = config.get('Main', 'output')
except:
    pass
try:
    _force_stream_select = config.getint('Main', 'force_stream_select')
except:
    pass
try:
    _force_audio_encode = config.getint('Main', 'force_audio_encode')
except:
    pass
try:
    _force_video_encode = config.getint('Main', 'force_video_encode')
except:
    pass
try:
    _scale = config.getint('Main', 'enable_scale')
except:
    pass
try:
    _scale_w = config.getint('Main', 'scale_width')
except:
    pass
try:
    _out_ext = config.get('Main', 'out_extension')
except:
    pass

_scale_atr = ["-filter:v", "scale=w=" + str(_scale_w) + ":h=trunc(" + str(_scale_w) + "/dar/2)*2:flags=1"]

_auto_out = 0
if len(_out) == 0:
    _auto_out = 1

_is_win = 0
_is_lin = 0
if platform.system() == 'Windows':
    _is_win = 1
    reload(sys)
    sys.setdefaultencoding("cp1251")
if platform.system() == 'Linux':
    _is_lin = 1

_input_files = sys.argv[1:]
if len(_input_files) == 0:
    print "Files for converting not found!"
    _input_files=["\\\\192.168.0.1\\Torrents\\Films\\Generation.Um.2012.BluRay.720p.mkv"]
    #sys.exit(0)
if len(_input_files) == 1:
    folder = _input_files[0]
    if os.path.isdir(folder):
        _input_files = []
        for file in os.listdir(folder):
            full_path = os.path.realpath(os.path.join(folder, file))
            if os.path.isdir(full_path):
                continue
            ex = file.split('.')[-1]
            if ex in ['avi', 'mkv', 'ts', 'wma', 'mp4']:
                _input_files.append(full_path)
    print "Loaded files:", '\n'.join(_input_files)
if len(_input_files) == 0:
    print "Files for converting not found!"
    sys.exit(0)


def get_aac_codec():
    global _acodec
    global _acodec_param
    global _vcodec
    print '*mpeg: get codecs'
    app = _app_encode + ('.exe' if _is_win else '_linux' if _is_lin else '')
    app_path = os.path.join(_path, 'bin', app)
    atr = [app_path,
           '-codecs'
    ]
    process = subprocess.Popen((' ').join(atr), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    aprio = 0
    vprio = 0
    acodec = ''
    vcodec = ''
    param = []
    while True:
        buff = process.stdout.readline().replace('\r', '').replace('\n', '')
        if buff == '' and process.poll() != None:
            break
        t1 = re.sub(r'[DEVASTIL.]*', '', buff[:7])
        t2 = t1 + buff[7:]
        codec_var = t2.strip().split(" ")[0]
        if codec_var == "libfdk_aac":
            if aprio > 4: continue
            acodec = 'libfdk_aac'
            param = []
            aprio = 4
        if codec_var == "libfaac":
            if aprio > 3: continue
            acodec = 'libfaac'
            param = []
            aprio = 3
        if codec_var == "aac":
            if aprio > 2: continue
            acodec = 'aac'
            param = ['-strict', '-2']
            aprio = 2
        if codec_var == "libvo_aacenc":
            if aprio != 0: continue
            acodec = 'libvo_aacenc'
            param = []
            aprio = 1
        if codec_var == "h264":
            if vprio != 0: continue
            vcodec = 'h264'
            vprio = 1
        if codec_var == "libx264":
            if vprio > 2: continue
            vcodec = 'libx264'
            vprio = 2

    process.wait()
    _acodec = acodec
    _acodec_param = param
    _vcodec = vcodec


def ffmpeg(s, d, params, sub_imput):
    print '*mpeg: open', s
    d_tmp = d + '.converting' + _out_ext
    app = _app_encode + ('.exe' if _is_win else '_linux' if _is_lin else '')
    app_path = os.path.join(_path, 'bin', app)
    atr = [app_path,
           '-y',
           '-i', s,
    ]
    atr += sub_imput
    atr += ['-threads', '4',
           '-preset', 'slow',
           '-crf', '18', #20 recomend #18 big file
    ]
    atr.append('-f')
    atr.append('mp4')
    atr += _acodec_param
    atr += params
    if _scale:
        atr += _scale_atr
    atr.append(d_tmp)
    print "="*60
    print "Command line:", ' '.join(atr)
    print "="*60
    subprocess.Popen(atr, stdout=subprocess.PIPE).communicate()[0]
    if os.path.getsize(d_tmp) == 0:
        os.remove(d_tmp)
        return 0
    else:
        os.rename(d_tmp, d + _out_ext)
        return 1


def get_info(s):
    print '*probe: open', s
    app = _app_info + ('.exe' if _is_win else '_linux' if _is_lin else '')
    app_path = os.path.join(_path, 'bin', app)
    atr = [app_path,
           '"' + s.replace("$", "\$").replace("`", "\`") + '"',
           '-of', 'json', '-show_format', '-show_streams'
    ]
    process = subprocess.Popen((' ').join(atr), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    json_out = ''
    writeing = 0
    tmp_err = 0
    while True:
        buff = process.stdout.readline().replace('\r', '').replace('\n', '')
        if buff == '' and process.poll() != None:
            break
        if writeing == 0 and len(buff) > 0 and buff[0] == '{':
            writeing = 1
        if writeing == 0 and len(buff) > 0 and buff.strip() == '"streams": [':
            buff = "{" + buff
            writeing = 1
        #on error>>
        if writeing == 0 and len(buff) > 0 and buff.strip() == 'Metadat{  "format" : {':
            buff = '{ "format" : {'''
            writeing = 1
            tmp_err = 1
        if tmp_err == 1 and writeing == 1 and buff == '  ]}':
            json_out += buff
            writeing = 0
        #<<on error
        if writeing == 1 and len(buff) > 15 and ( buff[0:15] == 'avprobe version' or buff[0:15] == 'ffprobe version' ):
            writeing = 0
        if writeing:
            json_out += buff
        if writeing and len(buff) > 0 and buff[0] == '}':
            writeing = 0
    process.wait()
    try:
        out = json.loads(json_out)
    except Exception:
        try:
            out = json.loads(json_out.decode("cp1251"))
        except Exception:
            out = json.loads(json_out.decode("utf-8", "ignore"))
    return out


def select_streams(info):
    global _save_param, _scale
    if not 'streams' in info:
        print('Streams not found!')
        return ['-c', 'copy', '-c:v', 'h264', '-c:a', 'aac'], -1;
    streams = {}
    v_count = 0
    a_count = 0
    o_count = 0
    all_arr = []
    for stream in info['streams']:
        def g(i, e=''):
            return str(stream[i]) if i in stream else e

        l_id = g('index', '-1')
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
        l_resol = g('width') + 'x' + g('height')
        tmp_w = g('width')
        if _scale == 1 and l_codec != "mjpeg" and len(tmp_w) > 0 and int(tmp_w) > 0 and int(tmp_w) <= _scale_w:
            _scale = 0
        l_def = stream['disposition']['default'] if 'disposition' in stream and 'default' in stream[
            'disposition'] else ''
        if len(l_resol) == 1: l_resol = ''
        streams[l_id] = {
        'type': l_type,
        'codec': l_codec,
        'bit_rate': l_bit_rate
        }
        all_arr.append(l_id)
        print 'Stream:', l_id, \
            ('(' + l_lang + ')' if l_lang != '' else '') + \
            (', [D]' if l_def else '') + \
            (', ' + l_bit_rate if l_bit_rate else '') + \
            (', ' + l_type.capitalize() + ': ' + l_codec) + \
            (', ch ' + l_channel if l_channel else '') + \
            (', ' + l_resol if l_resol else '') + \
            (', ' + l_title if l_title else '')
    save_query = ''
    if v_count == 1 and a_count == 1 and o_count == 0 and _force_stream_select == 0:
        stream_arr = '0 1'
    elif len(_save_param) == 0:
        stream_arr = raw_input('Enter stream numbers (spase for split, -1 for all): ')
        if len(_input_files) > 1:
            save_query = raw_input('Use for all? Enter (y/n): ').lower()
    else:
        stream_arr = _save_param
    if len(save_query) > 0 and save_query[0] == 'y':
        _save_param = stream_arr
    if stream_arr == "-1":
        stream_arr = all_arr
    else:
        stream_arr = stream_arr.split(' ')
    param_encode = []
    n = 0
    for indx in stream_arr:
        param_encode.append('-map')
        param_encode.append('0:' + indx)
    for indx in stream_arr:
        if (streams[indx]['codec'] == 'unknown'):
            continue
        if streams[indx]['type'] == 'audio' and (streams[indx]['codec'] != 'aac' or _force_audio_encode == 1):
            param_encode.append('-c:' + str(n))
            param_encode.append(_acodec)

            #param_encode.append('-q:'+str(n))
            #param_encode.append('1')

            if len(streams[indx]['bit_rate']) > 0:
                param_encode.append('-b:' + str(n))
                param_encode.append(streams[indx]['bit_rate'])
            n += 1
            continue
        if streams[indx]['type'] == 'video' and (
                    streams[indx]['codec'] != 'h264' or _scale == 1 or _force_video_encode == 1 ):
            param_encode.append('-c:' + str(n))
            param_encode.append(_vcodec)

            #param_encode.append('-q:'+str(n))
            #param_encode.append('1')

            n += 1
            continue
        if streams[indx]['type'] == 'subtitle' and streams[indx]['codec'] == 'subrip':
            param_encode.append('-c:' + str(n))
            param_encode.append('mov_text')
            n += 1
            continue

        param_encode.append('-c:' + str(n))
        param_encode.append('copy')
        n += 1

    return param_encode, n


#get_aac_codec()

def get_sub_files(path, name, codec_count):
    input = []
    params = []
    f_num = 1
    c_num = codec_count
    for fn in os.listdir(path):
        if fn[:len(name)] == name and fn.split('.')[-1] == 'srt':
            add = raw_input('I found "srt" file ( '+fn+' ), add it? (y/n): ').lower()
            if add != "y":
                continue
            input.append('-i')
            input.append(os.path.join(path, fn))
            params.append('-map')
            params.append(str(f_num)+':0')
            params.append('-c:'+str(c_num))
            params.append('mov_text')
            c_num += 1
            f_num += 1
    return params, input

class encode_file(file):
    file = None
    name = None
    ext = None
    folder = None
    out_folder = None
    out_path = None
    ff_probe = _app_probe
    ff_mpeg = _app_encode
    ff_mpeg_path = None
    ff_probe_path = None
    ff_stream_list = []
    ff_input_list = []
    _path = os.path.dirname(os.path.realpath(__file__))
    streams = []

    def get_stream_list(self, file):
        import subprocess
        cmnd = [self.ff_probe_path, '-show_format', '-pretty', '-of', 'json', '-show_streams', '-loglevel', 'quiet', file]
        p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err =  p.communicate()
        #print "==========output=========="
        #print out
        #if err:
        #    print "========= error ========"
        #    print err
        probe = json.loads(out)
        tmp_strem_list = []
        strem_list = {}
        strem_list['streams'] = []
        if 'streams' in probe:
            tmp_strem_list = probe['streams']
        for stream in tmp_strem_list:
            item = {}
            item['language'] = stream['tags']['language'] if 'tags' in stream and 'language' in stream['tags'] else None
            item['title'] = stream['tags']['title'] if 'tags' in stream and 'title' in stream['tags'] else None
            item['type'] = stream['codec_type'] if 'codec_type' in stream else None
            item['codec'] = stream['codec_name'] if 'codec_name' in stream else None
            item['sample_rate'] = stream['sample_rate'] if 'sample_rate' in stream else None
            item['bit_rate'] = stream['bit_rate'] if 'bit_rate' in stream else None
            item['channels'] = stream['channels'] if 'channels' in stream else None
            item['width'] = stream['width'] if 'width' in stream else None
            item['height'] = stream['height'] if 'height' in stream else None
            item['default'] = stream['disposition']['default'] if 'disposition' in stream and 'default' in stream['disposition'] else None
            item['index'] = stream['index'] if 'index' in stream else None
            strem_list['streams'].append(item)
        strem_list['file'] = os.path.realpath(file)
        self.streams.append(strem_list)

    def get_sub_files(self):
        for fn in os.listdir(self.folder):
            if fn[:len(self.name)] == self.name and fn.split('.')[-1] == 'srt':
                get_stream_list( os.path.realpath( os.path.join( self.folder, fn ) ) )

    def __init__(self, file):
        import os
        self.ff_probe_path = os.path.join(self._path, 'bin', self.ff_probe) + ('.exe' if _is_win else '_linux' if _is_lin else '')
        self.ff_mpeg_path = os.path.join(self._path, 'bin', self.ff_mpeg) + ('.exe' if _is_win else '_linux' if _is_lin else '')
        self.file = os.path.realpath(file)
        self.folder = os.path.dirname(self.file)
        self.name = os.path.splitext(os.path.basename(self.file))[0]
        self.ext = self.file.split('.')[-1]
        if _auto_out:
            self.out_folder = self.folder
        else:
            self.out_folder = os.path.realpath(_out)
        self.out_path = os.path.join(self.out_folder, self.name + _out_ext)
        print self.out_path
        if os.path.exists(self.out_path):
            print "Exists!", self.out_path
        else:
            self.get_stream_list(self.file)
            self.get_sub_files()
            print self.streams
            #select_streams()
            #get_sub_files()
            #ffmpeg()
            #print "Dune!", f_name


for file in _input_files:
    encode_file(file)

print "All dune!"
for file in _input_files:
    print "From folder:", os.path.dirname(file)
    print "File:", os.path.basename(file)
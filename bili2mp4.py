# -*- coding: utf-8 -*-
# bilibili 手机离线缓存转换
import json
import os
import sys
import re
import shutil
import argparse


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("video_dir", type=str, help="视频目录文件夹")
parser.add_argument("-n", "--nopause", action="store_true", help="转换完成后直接退出程序，用于脚本批量执行")
parser.description = r"""转换bilibili安卓客户端的离线缓存视频到mp4文件. version:0.2-x64

    Q: bilibili安卓客户端的缓存文件在哪里？
    A: 该离线文件通常在手机的 'Android\data\tv.danmaku.bili\download' 文件夹中.
    Q: 如何使用本工具进行转换？
    A: 前述download文件夹中每个文件都对应一个视频or视频集锦，将这个视频文件夹复制到本地并运行命令: 'bili2mp4.py <视频目录文件夹>'
    Q: 转换后的视频保存在哪里？
    A: 所有转换的视频和弹幕文件会保存在当前路径下的 'bili2mp4_output' 文件夹.
    Q: 如何找到我想要的视频中对应文件夹？
    A: 我的经验是按照你的下载日期对应即可.
    Q: 如何在播放视频时加载弹幕文件？
    A: 推荐使用<弹弹play>播放器，可以自动识别并加载弹幕文件.
    Q: 出问题了？
    A: 请向 github.com/bitdust/bili2mp4 反馈并求助."""
args = parser.parse_args()

SCRIPT_DIR = os.path.split(os.path.realpath(__file__))[0] # 程序所在位置
MAIN_DIR = os.path.abspath(args.video_dir) # 视频文件夹
WORKING_DIR = os.getcwd()
if not os.path.exists('bili2mp4_output'):
    os.mkdir("bili2mp4_output")
OUTPUT_DIR = os.path.abspath('bili2mp4_output') # 输出文件夹

# 检查ffmpeg是否存在,并设置ffmpeg工具路径
FFMPEG_CMD = ""
if sys.platform=='win32':
    ffmpeg_name = "ffmpeg.exe"
else:
    ffmpeg_name = "ffmpeg"
if hasattr(sys,'_MEIPASS'): # 判断是否为 pyinstaller 打包环境
    FFMPEG_CMD = os.path.join(sys._MEIPASS, ffmpeg_name)
    if not os.path.exists(FFMPEG_CMD):
        print(r"pyinstall打包出问题啦，ffmpeg找不到!")
        sys.exit(-1)
else:
    if os.path.exists(os.path.join(SCRIPT_DIR,ffmpeg_name)):
        FFMPEG_CMD = os.path.join(SCRIPT_DIR,ffmpeg_name) # 优先使用自带的 ffmpeg
    elif shutil.which(ffmpeg_name) is not None:
        FFMPEG_CMD = ffmpeg_name
    else:
        print(r"找不到ffmpeg命令，请安装ffmpeg或下载ffmepg并放在同一目录下.")
        sys.exit(-1)

def ffmpeg_concat_m4s(segments:list, video_name:str):
    # 进入输出目录，并将指定的m4s文件使用ffmpeg进行连接，输出在同一目录中并修改文件名
    os.chdir(OUTPUT_DIR)
    input_str = ""
    for segment in segments:
        input_str += f" -i {segment}"
    cmd_str = f"""{FFMPEG_CMD} -loglevel quiet {input_str} -c copy -y "{video_name}.mp4" """
    status = os.system(cmd_str)
    os.chdir(WORKING_DIR)
    return status


def ffmpeg_concat_blv(segments:list, video_name:str):
    # 进入输出目录，并将指定的blv文件使用ffmpeg进行连接，输出在同一目录中并修改文件名
    os.chdir(OUTPUT_DIR)
    input_file = open('input.txt', 'w')
    for segment in segments:
        input_file.write(f"""file '{segment}' \n""")
    input_file.close()
    cmd_str = f"""{FFMPEG_CMD} -loglevel quiet -f concat -i input.txt -c copy -y "{video_name}.mp4" """
    status = os.system(cmd_str)
    os.remove('input.txt')
    os.chdir(WORKING_DIR)
    return status


def build_title(entry_dict:dict):
    # 提取标题是个很麻烦的事
    title = entry_dict["title"].strip() # 主标题
    if 'ep' in entry_dict.keys():
        if entry_dict['ep']["index_title"] == '':
            title += "-"
            title += entry_dict['ep']["index"].strip()
        else:
            title += "-"
            title += "-".join([entry_dict['ep']["index"],entry_dict['ep']["index_title"]]).strip()
    if 'page_data' in entry_dict.keys():
        title += "-"
        title += entry_dict['page_data']["part"].strip()
    title = re.sub(r"[\/\\\:\*\?\"\<\>\|]", " ", title) # 过滤文件名中的非法字符
    return title


def convert_episode(episode_path : str):
    # 解析每一集视频，转换文件，提取弹幕xml并输出到output目录中
    entry_file = os.path.join(episode_path,'entry.json') # 元信息json文件
    with open(entry_file, 'r', encoding='utf-8') as f:
        entry_dict = json.load(f, encoding='utf-8')
    episode_name = build_title(entry_dict)    
    # 输出弹幕文件
    danmuku_path = os.path.join(episode_path,'danmaku.xml')
    if os.path.exists(danmuku_path):
        shutil.copy(danmuku_path, os.path.join(OUTPUT_DIR,episode_name+'.xml'))
    # 处理视频文件
    tag_type = entry_dict["type_tag"] # 视频的存储类型，也是视频文件的存放目录名称
    seg_path = os.path.join(episode_path, tag_type)
    video_segments = [i for i in os.listdir(seg_path) if ('.blv'==os.path.splitext(i)[1] or '.m4s'==os.path.splitext(i)[1])]
    for segment in video_segments:
        shutil.copy(os.path.join(episode_path,tag_type,segment), OUTPUT_DIR)
    if 'flv' in tag_type:
        status = ffmpeg_concat_blv(video_segments, episode_name)
    elif tag_type.isdigit():
        status = ffmpeg_concat_m4s(video_segments, episode_name)
    else:
        status = -1
        print(f"未知格式: {tag_type} 转换失败.")
    for segment in video_segments:
        os.remove(os.path.join(OUTPUT_DIR,segment))
    if status==0:
        print(f"{episode_name} 转换完成.")
        return(0)
    else:
        print(f"{episode_name} 转换失败.")
        return(-1)

item_cnt = 0
for item in os.listdir(MAIN_DIR):
    # 遍历主文件夹
    sub_dir = os.path.join(MAIN_DIR,item)
    if os.path.isdir(sub_dir) and ('entry.json' in os.listdir(sub_dir)):
        status = convert_episode(sub_dir) # 处理每集视频
        if status==0:
            item_cnt = item_cnt+1
print(f"已转换 {item_cnt} 个视频.")
if args.nopause:
    sys.exit(0)
else:
    input("Press Enter to exit.")
    sys.exit(0)
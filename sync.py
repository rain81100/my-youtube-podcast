import os
import json
import urllib.request
import xml.etree.ElementTree as ET
import subprocess

# 配置参数
# ⚠️ 请确保填写了正确的 24 位频道 ID (形如 UCxxxxxxxxxxxx)
YOUTUBE_CHANNEL_ID = "UC8UCbiPrm2zN9nZHKdTevZA" 
LIST_FILE = "list.json"

# 可用的公开 Invidious 实例 API（如果第一个失败会自动尝试后面的）
INVIDIOUS_INSTANCES = [
    "https://invidious.vps.net.ua",
    "https://inv.tux.digital",
    "https://yewtu.be",
    "https://iv.melmac.space"
]

# 1. 读取已有列表
if os.path.exists(LIST_FILE):
    with open(LIST_FILE, 'r', encoding='utf-8') as f:
        audio_list = json.load(f)
else:
    audio_list = []

def get_latest_video_from_rss(channel_id):
    """通过 RSS 获取最新视频 ID 和标题"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(rss_url, headers=headers)
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()
    root = ET.fromstring(xml_data)
    ns = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    entry = root.find('ns:entry', ns)
    if entry is not None:
        video_id = entry.find('yt:videoId', ns).text
        video_title = entry.find('ns:title', ns).text
        return video_id, video_title
    return None, None

def download_audio_via_invidious(video_id, output_filename):
    """通过 Invidious 镜像接口获取音频流并下载"""
    for instance in INVIDIOUS_INSTANCES:
        try:
            print(f"正在尝试通过镜像站 {instance} 解析音频...")
            api_url = f"{instance}/api/v1/videos/{video_id}"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode('utf-8'))
            
            # 寻找音频流 (adaptiveFormats 中 type 包含 audio/ 且 container 为 m4a 或 webm)
            audio_url = None
            if 'adaptiveFormats' in data:
                for fmt in data['adaptiveFormats']:
                    if fmt.get('type', '').startswith('audio/'):
                        audio_url = fmt.get('url')
                        break
            
            if not audio_url and 'formatStreams' in data:
                # 如果没找到纯音频，退而求其次找包含音频的普通视频流
                audio_url = data['formatStreams'][0].get('url')
                
            if audio_url:
                print("成功解析到音频流，开始下载...")
                # 将流下载为临时文件
                temp_file = "temp_audio"
                urllib.request.urlretrieve(audio_url, temp_file)
                
                # 使用 FFmpeg 将其转换为标准的 128k mp3
                print("正在使用 FFmpeg 转换为 MP3...")
                subprocess.run([
                    'ffmpeg', '-y', '-i', temp_file, 
                    '-vn', '-ar', '44100', '-ac', '2', 
                    '-b:a', '128k', output_filename
                ], check=True)
                
                # 删除临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return True
        except Exception as e:
            print(f"当前镜像站解析或下载失败: {str(e)}，尝试下一个...")
            continue
    return False

try:
    print("正在通过 RSS 读取频道最新动态...")
    video_id, video_title = get_latest_video_from_rss(YOUTUBE_CHANNEL_ID)
    
    if video_id and video_title:
        filename = f"{video_id}.mp3"
        
        # 2. 检查是否已经下载过
        if not any(item['id'] == video_id for item in audio_list):
            print(f"发现新视频: {video_title} (ID: {video_id})")
            
            # 3. 执行免验证下载
            success = download_audio_via_invidious(video_id, filename)
            
            if success:
                # 更新列表并只保留最新的 5 条音频
                audio_list.insert(0, {"id": video_id, "title": video_title, "filename": filename})
                
                if len(audio_list) > 5:
                    old_audio = audio_list.pop()
                    if os.path.exists(old_audio['filename']):
                        os.remove(old_audio['filename'])
                
                with open(LIST_FILE, 'w', encoding='utf-8') as f:
                    json.dump(audio_list, f, ensure_ascii=False, indent=4)
                    
                print("🎉 同步及 MP3 转换圆满完成！")
            else:
                raise Exception("所有开源解析接口均无法获取此视频音频，请稍后再试。")
        else:
            print("已经是最新音频，无需更新。")
    else:
        print("未能在 RSS 中找到视频，请检查 YOUTUBE_CHANNEL_ID 是否正确。")

except Exception as e:
    print(f"脚本执行最终出错: {str(e)}")
    raise e

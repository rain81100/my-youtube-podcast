import os
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
import yt_dlp

# 配置参数
# ⚠️ 注意：这里请填写频道的唯一ID（Channel ID），形如 UCxxxxxxxxxxxx
# 如果你只有类似 @username 的名字，可以在网页上右键查看源代码搜 "channelId" 找到，或者通过第三方工具查询。
YOUTUBE_CHANNEL_ID = "UC8UCbiPrm2zN9nZHKdTevZA" 
LIST_FILE = "list.json"

# 1. 读取已有列表
if os.path.exists(LIST_FILE):
    with open(LIST_FILE, 'r', encoding='utf-8') as f:
        audio_list = json.load(f)
else:
    audio_list = []

def get_latest_video_from_rss(channel_id):
    """通过无需验证的 RSS 源直接获取最新视频信息"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request(rss_url, headers=headers)
    
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()
        
    root = ET.fromstring(xml_data)
    # XML 命名空间处理
    ns = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    
    # 获取第一个 entry（最新视频）
    entry = root.find('ns:entry', ns)
    if entry is not None:
        video_id = entry.find('yt:videoId', ns).text
        video_title = entry.find('ns:title', ns).text
        return video_id, video_title
    return None, None

try:
    print("正在通过 RSS 读取频道最新动态...")
    video_id, video_title = get_latest_video_from_rss(YOUTUBE_CHANNEL_ID)
    
    if video_id and video_title:
        filename = f"{video_id}.mp3"
        
        # 2. 检查是否已经下载过
        if not any(item['id'] == video_id for item in audio_list):
            print(f"发现新视频: {video_title} (ID: {video_id}), 开始下载...")
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # 3. 极限伪装配置：针对单视频下载
            download_opts = {
                'format': 'bestaudio/best',
                'outtmpl': filename,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                # 全套移动端及模拟浏览器伪装，配合單 URL 绕过检测
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios', 'android', 'mweb'],
                        'skip': ['webpage']
                    }
                },
                'youtube_include_dash_manifest': False,
                'youtube_include_hls_manifest': False,
                'nocheckcertificate': True,
                'quiet': False
            }
            
            with yt_dlp.YoutubeDL(download_opts) as ydl_dl:
                ydl_dl.download([video_url])
            
            # 更新列表并只保留最新的 5 条音频
            audio_list.insert(0, {"id": video_id, "title": video_title, "filename": filename})
            
            if len(audio_list) > 5:
                old_audio = audio_list.pop()
                if os.path.exists(old_audio['filename']):
                    os.remove(old_audio['filename'])
            
            with open(LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(audio_list, f, ensure_ascii=False, indent=4)
                
            print("同步及文件更新完成！")
        else:
            print("已经是最新音频，无需更新。")
    else:
        print("未能在 RSS 中找到视频，请检查 YOUTUBE_CHANNEL_ID 是否正确。")

except Exception as e:
    print(f"脚本执行出错: {str(e)}")
    raise e

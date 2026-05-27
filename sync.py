import os
import json
import urllib.request
import xml.etree.ElementTree as ET
import subprocess

# 配置参数
# ⚠️ 请确保填写的还是那个 24 位的频道 ID
YOUTUBE_CHANNEL_ID = "UC8UCbiPrm2zN9nZHKdTevZA" 
LIST_FILE = "list.json"

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

def download_via_cobalt_api(video_id, output_filename):
    """利用专业的 Cobalt 高级免封接口直接提取音频文件"""
    url = f"https://api.cobalt.tools/"
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 构建 Cobalt API 专属的请求体
    payload = json.dumps({
        "url": video_url,
        "isAudioOnly": True,      # 只要音频
        "audioFormat": "mp3",     # 只要标准的 mp3
        "audioBitrate": "128"     # 128k 码率
    }).encode('utf-8')
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        print("正在提交视频给免封中转解析接口...")
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as res:
            response_data = json.loads(res.read().decode('utf-8'))
        
        # 接口会直接返回一个可供 GitHub Actions 高速下载的直接音频流 URL
        download_url = response_data.get('url')
        
        if download_url:
            print("解析成功！正在下载中转音频文件...")
            # 顺着这个高速 URL 直接把转好的 MP3 存下来
            urllib.request.urlretrieve(download_url, output_filename)
            return True
        else:
            print(f"接口返回异常: {response_data}")
            return False
            
    except Exception as e:
        print(f"Cobalt 接口调用或下载失败: {str(e)}")
        return False

try:
    print("正在通过 RSS 读取频道最新动态...")
    video_id, video_title = get_latest_video_from_rss(YOUTUBE_CHANNEL_ID)
    
    if video_id and video_title:
        filename = f"{video_id}.mp3"
        
        # 2. 检查是否已经下载过
        if not any(item['id'] == video_id for item in audio_list):
            print(f"发现新视频: {video_title} (ID: {video_id})")
            
            # 3. 执行无痛免封下载
            success = download_via_cobalt_api(video_id, filename)
            
            if success:
                # 更新列表并只保留最新的 5 条音频
                audio_list.insert(0, {"id": video_id, "title": video_title, "filename": filename})
                
                if len(audio_list) > 5:
                    old_audio = audio_list.pop()
                    if os.path.exists(old_audio['filename']):
                        os.remove(old_audio['filename'])
                
                with open(LIST_FILE, 'w', encoding='utf-8') as f:
                    json.dump(audio_list, f, ensure_ascii=False, indent=4)
                    
                print("🎉 恭喜！通过中转隧道成功绕过封锁，音频已成功存入仓库！")
            else:
                raise Exception("中转解析通道暂时不可用。")
        else:
            print("已经是最新音频，无需更新。")
    else:
        print("未能在 RSS 中找到视频，请检查 YOUTUBE_CHANNEL_ID 是否正确。")

except Exception as e:
    print(f"脚本执行最终出错: {str(e)}")
    raise e

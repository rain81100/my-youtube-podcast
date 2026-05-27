import os
import json
import yt_dlp

# 配置参数
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@wongkim728/streams" # ⚠️ 确保修改为目标账号URL
LIST_FILE = "list.json"

# 1. 读取已有列表
if os.path.exists(LIST_FILE):
    with open(LIST_FILE, 'r', encoding='utf-8') as f:
        audio_list = json.load(f)
else:
    audio_list = []

# 2. 增强型配置：伪装成移动端客户端，绕过 "Sign in to confirm you're not a bot"
base_opts = {
    'extract_audio': True,
    'format': 'bestaudio/best',
    'playlistend': 1,  # 只取最新那一个
    # 核心：使用 ios/android 客户端伪装，避免触发人机验证
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android'],
            'skip': ['webpage']
        }
    },
    # 强制不使用可能会暴露 GitHub Actions 服务器特征的某些网页端接口
    'youtube_include_dash_manifest': False,
    'youtube_include_hls_manifest': False,
}

# 3. 检查最新视频
try:
    with yt_dlp.YoutubeDL(base_opts) as ydl:
        info = ydl.extract_info(YOUTUBE_CHANNEL_URL, download=False)
        if 'entries' in info and len(info['entries']) > 0:
            latest_video = info['entries'][0]
            video_id = latest_video['id']
            video_title = latest_video['title']
            filename = f"{video_id}.mp3"
            
            # 4. 检查是否已经下载过
            if not any(item['id'] == video_id for item in audio_list):
                print(f"发现新视频: {video_title}, 开始下载...")
                
                # 合并配置用于实际下载转码
                download_opts = base_opts.copy()
                download_opts.update({
                    'outtmpl': filename,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '128',
                    }],
                })
                
                with yt_dlp.YoutubeDL(download_opts) as ydl_dl:
                    ydl_dl.download([f"https://www.youtube.com/watch?v={video_id}"])
                
                # 更新列表并只保留最新的 5 条音频，防止仓库体积过大
                audio_list.insert(0, {"id": video_id, "title": video_title, "filename": filename})
                
                # 删掉旧音频文件（如果列表中超过5条）
                if len(audio_list) > 5:
                    old_audio = audio_list.pop()
                    if os.path.exists(old_audio['filename']):
                        os.remove(old_audio['filename'])
                
                # 写入更新后的 json
                with open(LIST_FILE, 'w', encoding='utf-8') as f:
                    json.dump(audio_list, f, ensure_ascii=False, indent=4)
                    
                print("同步及本地文件更新完成！")
            else:
                print("已经是最新音频，无需更新。")
        else:
            print("未能提取到频道内的视频列表，请确认频道URL是否正确或对方近期是否有发布视频。")

except Exception as e:
    print(f"脚本执行出错: {str(e)}")
    # 抛出异常确保 GitHub Actions 能显示失败以便查看排查，但上面的报错已经被捕获处理
    raise e

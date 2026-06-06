# FrameDrop

将视频抽帧转换为定格动画效果的桌面工具。

## 功能

- 导入视频（支持 MP4/AVI/MOV/MKV，支持拖拽导入）
- 设置抽帧间隔（每隔多少秒抽取 1 帧，支持小数，滑块 + 输入框联动）
- 设置目标帧率（控制回放速度，滑块 + 输入框联动）
- 实时预览定格动画效果
- 预览进度条，可拖动跳帧，支持左右方向键前进/后退 1 秒
- 播放/暂停控制
- 导出为 MP4 或 GIF（导出时同名文件确认覆盖）

## 安装依赖

```
pip install -r requirements.txt
```

## 安装 FFmpeg

导出功能需要 FFmpeg：

```
winget install Gyan.FFmpeg
```

安装后重启终端。

## 使用

```
python main.py
```

1. 点击"选择视频"或拖拽视频文件到窗口
2. 调整抽帧间隔（默认每 0.2 秒抽 1 帧）
3. 调整目标帧率（默认 4 FPS）
4. 预览效果满意后点击"导出"
5. 选择 MP4 或 GIF 格式，选择保存路径

## 技术栈

- **GUI**: PySide6
- **帧提取**: OpenCV
- **视频导出**: FFmpeg
- **Python**: 3.9+

## 项目结构

```
FrameDrop/
├── main.py               # 入口
├── logo.png              # 应用图标
├── core/
│   ├── extractor.py      # 帧提取
│   └── exporter.py       # 视频导出
├── ui/
│   ├── preview_widget.py # 预览组件（进度条、播放控制）
│   └── main_window.py    # 主窗口
└── tests/                # 单元测试
```

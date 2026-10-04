# seeneo for Claude Code and Codex

[English](#english) · [ไทย](#ไทย) · [中文](#中文)

---

## English

**seeneo** is a video editing plugin for Claude Code and Codex. Your agent edits your own videos on your own computer. It can cut silences and flubbed lines, put clips in order, add Thai, English or Chinese captions, reframe for Reels, TikTok or Shorts, add music and export an mp4. It's free, needs no account, and your footage stays on your machine.

### What's included

- **`seeneo-local`** is a set of free tools that run on your computer: `probe` (read file info), `frames` (look at the footage), `find_silence` (find dead air), `transcribe` (speech to captions) and `render` (cut and export).
- **`seeneo-edit`** is the skill your agent follows: edit locally, check a draft, then render the final.
- **`seeneo`** (optional) connects to seeneo.ai server tasks: AI video shots (Powered by MiniMax H3, not available in every country), hosted rendering of animated HTML overlays, and private cloud storage. It needs sign-in.

### Requirements

You need Claude Code or the Codex CLI with plugin support, plus `ffmpeg` (which includes `ffprobe`) and `uv` on your PATH.

| OS | Install |
|---|---|
| macOS | `brew install ffmpeg-full uv` (captions need `ffmpeg-full`) |
| Windows | `winget install Gyan.FFmpeg` and `winget install astral-sh.uv`, then open a new terminal |
| Linux (Debian/Ubuntu) | `sudo apt install ffmpeg`, then `curl -LsSf https://astral.sh/uv/install.sh \| sh` for uv. On other distros, use your package manager. |

To check, run `ffmpeg -version`, `ffprobe -version` and `uv --version`. You don't need to install Python yourself, because uv takes care of it. For Thai captions, the free Kanit font (Google Fonts) looks better. Without it, the tools use a Thai font from your system.

### Install

**Claude Code:** run these in Claude Code, then restart it.

```
/plugin marketplace add Boom-Vitt/seeneo-plugin
/plugin install seeneo@seeneo
```

**Codex:** run these in a terminal, then start a new Codex session.

```
codex plugin marketplace add Boom-Vitt/seeneo-plugin
codex plugin add seeneo@seeneo
```

Codex may ask before each tool call. To let the local tools run without asking, add this to `~/.codex/config.toml`:

```toml
[plugins."seeneo@seeneo".mcp_servers.seeneo-local]
default_tools_approval_mode = "approve"
```

Try asking: *"Cut the silences out of ~/Videos/talk.mp4, add English captions and make it 9:16."*

**Where files go:** In Claude Code, finished files go to a `seeneo-out` folder inside the folder you started Claude Code in. To use another folder, set `SEENEO_OUT_DIR` before you start Claude Code. In Codex, they go to a `seeneo-out` folder next to your first video, because Codex doesn't tell the plugin which folder you're working in.

**Update:** in Claude Code run `/plugin marketplace update seeneo`. In Codex run `codex plugin marketplace upgrade`.

### Privacy

- **Local tools run entirely on your computer.** Your videos, audio and exports stay there. There's no account and no usage tracking.
- **Two one-time downloads.** The first start downloads the tools' Python packages. The first transcription downloads speech-recognition files, which are then kept for later use. The tools send nothing else online.
- **Your agent sees what the tools return.** Contact sheets, transcripts and file details go back to Claude Code or Codex, which may send them to its AI provider like the rest of your conversation. seeneo receives none of it.
- **The seeneo.ai server is used only when you ask for something your computer can't do**, such as an AI video shot, a hosted overlay render or a cloud copy. The skill tells your agent to ask before uploading anything and to name the files it would send.
- Uploaded files are stored privately in your seeneo.ai account. Download links are private and expire quickly, and you can delete a project at any time. A prompt-only AI shot sends just your text prompt.

### Free and paid

| | Cost | Account |
|---|---|---|
| Plugin and local tools | Always free | None |
| seeneo server tasks | Paid steps use credits (1 credit = THB 1). Your agent shows the exact price and waits for your OK before every paid step. | seeneo.ai sign-in. Today, credits need an active seeneo plan (THB 299/month). |
| seeneo.ai website app | seeneo plan, THB 299/month | seeneo.ai account |

To sign in for server tasks, use your seeneo.ai account. In Claude Code, run `/mcp` and choose `seeneo`. In Codex, run `codex mcp login seeneo` in a terminal and finish signing in in your browser. Sign-in always happens on the seeneo.ai sign-in page in your browser. seeneo never asks you to paste an API key, token or password into your agent or a config file. You don't have to sign in to use the local tools.

### Uninstall

Claude Code:

```
/plugin uninstall seeneo@seeneo
/plugin marketplace remove seeneo
```

Codex:

```
codex plugin remove seeneo@seeneo
codex plugin marketplace remove seeneo
```

To sign out of seeneo first, go to `/mcp` → `seeneo` → Clear authentication in Claude Code, or run `codex mcp logout seeneo` for Codex. Your exports in `seeneo-out` stay where they are, so delete them yourself if you want. The speech-recognition files are in `~/.cache/seeneo/speech` (or `SEENEO_MODEL_DIR` if you set it), and deleting that folder frees the space. The Python packages are in uv's cache. `uv cache clean` removes them, but it also clears the caches of your other projects.

---

## ไทย

**seeneo** คือปลั๊กอินตัดต่อวิดีโอสำหรับ Claude Code และ Codex ที่ให้เอเจนต์ช่วยตัดต่อวิดีโอของคุณบนเครื่องคุณเอง ทำได้ตั้งแต่ตัดช่วงเงียบหรือช่วงที่พูดผิดออก เรียงคลิป ใส่ซับไทย อังกฤษ หรือจีน ปรับเป็นแนวตั้งสำหรับ Reels, TikTok, Shorts ใส่เพลง แล้วส่งออกเป็น mp4 ได้เลย ใช้ฟรี ไม่ต้องสมัครบัญชี และวิดีโอของคุณอยู่ในเครื่องของคุณ

### มีอะไรบ้าง

- **`seeneo-local`** ชุดเครื่องมือฟรีที่ทำงานบนเครื่องคุณ ได้แก่ `probe` (อ่านข้อมูลไฟล์), `frames` (ดูภาพจากวิดีโอ), `find_silence` (หาช่วงเงียบ), `transcribe` (ถอดเสียงเป็นซับ) และ `render` (ตัดต่อและส่งออก)
- **`seeneo-edit`** สกิลที่บอกขั้นตอนให้เอเจนต์ คือตัดต่อบนเครื่อง ดูฉบับร่างก่อน แล้วค่อยเรนเดอร์ไฟล์จริง
- **`seeneo`** (ไม่บังคับ) เชื่อมต่องานบนเซิร์ฟเวอร์ seeneo.ai เช่น สร้างช็อตวิดีโอ AI (Powered by MiniMax H3 · ใช้ไม่ได้ในบางประเทศ) เรนเดอร์โอเวอร์เลย์ HTML แบบเคลื่อนไหวบนเซิร์ฟเวอร์ และพื้นที่เก็บไฟล์ส่วนตัวบนคลาวด์ ต้องเข้าสู่ระบบก่อนใช้

### สิ่งที่ต้องมี

ต้องมี Claude Code หรือ Codex CLI เวอร์ชันที่รองรับปลั๊กอิน และติดตั้ง `ffmpeg` (มี `ffprobe` มาด้วย) กับ `uv` ให้เรียกใช้จากเทอร์มินัลได้

| ระบบ | วิธีติดตั้ง |
|---|---|
| macOS | `brew install ffmpeg-full uv` (ต้องใช้ `ffmpeg-full` เพื่อใส่ซับไตเติล) |
| Windows | `winget install Gyan.FFmpeg` และ `winget install astral-sh.uv` แล้วเปิดเทอร์มินัลใหม่ |
| Linux (Debian/Ubuntu) | `sudo apt install ffmpeg` และติดตั้ง uv ด้วย `curl -LsSf https://astral.sh/uv/install.sh \| sh` ส่วนดิสโทรอื่นใช้ตัวจัดการแพ็กเกจของดิสโทรนั้นได้เลย |

เช็กว่าพร้อมใช้ด้วย `ffmpeg -version`, `ffprobe -version` และ `uv --version` ไม่ต้องลง Python เอง เพราะ uv จัดการให้ ถ้าทำซับไทย แนะนำฟอนต์ Kanit (ฟรีจาก Google Fonts) จะดูสวยกว่า ถ้าไม่ได้ลงไว้ เครื่องมือจะใช้ฟอนต์ไทยที่มีในเครื่องแทน

### ติดตั้ง

**Claude Code:** พิมพ์คำสั่งนี้ใน Claude Code แล้วปิดและเปิด Claude Code ใหม่

```
/plugin marketplace add Boom-Vitt/seeneo-plugin
/plugin install seeneo@seeneo
```

**Codex:** พิมพ์คำสั่งนี้ในเทอร์มินัล แล้วเริ่มเซสชัน Codex ใหม่

```
codex plugin marketplace add Boom-Vitt/seeneo-plugin
codex plugin add seeneo@seeneo
```

Codex อาจถามก่อนเรียกใช้เครื่องมือแต่ละครั้ง ถ้าอยากให้เครื่องมือ local ทำงานได้เลยโดยไม่ต้องถาม ให้เพิ่มบรรทัดนี้ใน `~/.codex/config.toml`

```toml
[plugins."seeneo@seeneo".mcp_servers.seeneo-local]
default_tools_approval_mode = "approve"
```

ลองสั่งดู เช่น *"ตัดช่วงเงียบออกจาก ~/Videos/talk.mp4 ใส่ซับไทย แล้วทำเป็นแนวตั้ง 9:16"*

**ไฟล์ไปอยู่ที่ไหน:** ใน Claude Code ไฟล์ที่ทำเสร็จจะอยู่ในโฟลเดอร์ `seeneo-out` ภายในโฟลเดอร์ที่คุณเปิด Claude Code ถ้าอยากเก็บไว้ที่อื่น ให้ตั้งค่า `SEENEO_OUT_DIR` ก่อนเปิด Claude Code ส่วนใน Codex ไฟล์จะอยู่ในโฟลเดอร์ `seeneo-out` ข้างวิดีโอไฟล์แรกของคุณ เพราะ Codex ไม่ได้บอกปลั๊กอินว่าคุณทำงานอยู่ในโฟลเดอร์ไหน

**อัปเดต:** ใน Claude Code พิมพ์ `/plugin marketplace update seeneo` ใน Codex ใช้ `codex plugin marketplace upgrade`

### ความเป็นส่วนตัว

- **เครื่องมือ local ทำงานบนเครื่องคุณทั้งหมด** วิดีโอ เสียง และไฟล์ที่ส่งออกอยู่ในเครื่องคุณ ไม่ต้องมีบัญชี และไม่มีการติดตามการใช้งาน
- **ดาวน์โหลดแค่ 2 อย่าง และโหลดครั้งเดียว** ตอนเปิดใช้ครั้งแรกจะโหลดไลบรารี Python ของเครื่องมือ และตอนถอดเสียงครั้งแรกจะโหลดไฟล์ที่ใช้ถอดเสียงเก็บไว้ใช้ต่อ นอกจากนี้ตัวเครื่องมือไม่ส่งอะไรออกไปทางอินเทอร์เน็ตอีก
- **เอเจนต์ของคุณเห็นผลลัพธ์จากเครื่องมือ** ภาพตัวอย่างเฟรม ข้อความถอดเสียง และข้อมูลไฟล์จะถูกส่งกลับไปที่ Claude Code หรือ Codex ซึ่งอาจส่งต่อไปยังผู้ให้บริการ AI ของเอเจนต์เหมือนข้อความอื่นในแชต seeneo ไม่ได้รับข้อมูลเหล่านี้
- **จะใช้เซิร์ฟเวอร์ seeneo.ai ก็ต่อเมื่อคุณขอสิ่งที่เครื่องคุณทำเองไม่ได้** เช่น ช็อตวิดีโอ AI, เรนเดอร์โอเวอร์เลย์บนเซิร์ฟเวอร์ หรือเก็บสำเนาไว้บนคลาวด์ สกิลกำหนดให้เอเจนต์ต้องถามคุณก่อนอัปโหลดทุกครั้ง และต้องบอกว่าจะส่งไฟล์ไหนบ้าง
- ไฟล์ที่อัปโหลดจะเก็บแบบส่วนตัวในบัญชี seeneo.ai ของคุณ ลิงก์ดาวน์โหลดเป็นลิงก์ส่วนตัวที่หมดอายุในเวลาไม่นาน และคุณลบโปรเจกต์ได้ทุกเมื่อ ถ้าสร้างช็อต AI จากข้อความอย่างเดียว จะส่งไปแค่ข้อความที่คุณพิมพ์

### ฟรีกับแบบเสียเงิน

| | ค่าใช้จ่าย | บัญชี |
|---|---|---|
| ปลั๊กอินและเครื่องมือ local | ฟรีเสมอ | ไม่ต้องมี |
| งานบนเซิร์ฟเวอร์ seeneo | งานที่มีค่าใช้จ่ายจะใช้เครดิต (1 เครดิต = 1 บาท) โดยเอเจนต์จะแจ้งราคาที่แน่นอนและรอให้คุณตกลงก่อนทุกครั้ง | เข้าสู่ระบบ seeneo.ai และตอนนี้การใช้เครดิตต้องมีแพ็กเกจ seeneo ที่ยังใช้งานอยู่ (299 บาท/เดือน) |
| แอป seeneo.ai บนเว็บ | แพ็กเกจ seeneo 299 บาท/เดือน | บัญชี seeneo.ai |

วิธีเข้าสู่ระบบเพื่อใช้งานบนเซิร์ฟเวอร์ (ใช้บัญชี seeneo.ai): ใน Claude Code พิมพ์ `/mcp` แล้วเลือก `seeneo` ส่วนใน Codex พิมพ์ `codex mcp login seeneo` ในเทอร์มินัล แล้วเข้าสู่ระบบให้เสร็จในเบราว์เซอร์ การเข้าสู่ระบบทำผ่านหน้าเข้าสู่ระบบของ seeneo.ai ในเบราว์เซอร์เท่านั้น seeneo จะไม่ขอให้คุณวาง API key, โทเค็น หรือรหัสผ่านลงในเอเจนต์หรือไฟล์ตั้งค่า ถ้าใช้แค่เครื่องมือ local ไม่ต้องเข้าสู่ระบบ

### ถอนการติดตั้ง

Claude Code:

```
/plugin uninstall seeneo@seeneo
/plugin marketplace remove seeneo
```

Codex:

```
codex plugin remove seeneo@seeneo
codex plugin marketplace remove seeneo
```

ถ้าต้องการออกจากระบบ seeneo ให้ทำก่อนถอนการติดตั้ง ใน Claude Code ไปที่ `/mcp` → `seeneo` → Clear authentication ส่วนใน Codex พิมพ์ `codex mcp logout seeneo` ไฟล์ที่ส่งออกไว้ใน `seeneo-out` จะยังอยู่ ลบเองได้ตามต้องการ ไฟล์ที่ใช้ถอดเสียงเก็บอยู่ใน `~/.cache/seeneo/speech` (หรือ `SEENEO_MODEL_DIR` ถ้าตั้งไว้) ลบโฟลเดอร์นี้เพื่อคืนพื้นที่ได้ ส่วนไลบรารี Python อยู่ในแคชของ uv ล้างได้ด้วย `uv cache clean` (คำสั่งนี้ล้างแคชของ uv ทั้งหมด รวมถึงของโปรเจกต์อื่นด้วย)

---

## 中文

**seeneo** 是一款适用于 Claude Code 和 Codex 的视频剪辑插件，让你的 AI 助手直接在你的电脑上剪辑你自己的视频：剪掉静音和口误、调整片段顺序、加上泰语、英语或中文字幕、改成适合 Reels、TikTok、Shorts 的竖屏、配乐，最后导出 mp4。插件免费使用，无需注册，视频素材不会离开你的电脑。

### 包含什么

- **`seeneo-local`**：在你电脑上运行的免费工具，包括 `probe`（读取文件信息）、`frames`（查看画面）、`find_silence`（查找静音段）、`transcribe`（语音转字幕）和 `render`（剪辑并导出）。
- **`seeneo-edit`**：AI 助手遵循的技能，先在本地剪辑，看过草稿后再导出成片。
- **`seeneo`**（可选）：连接 seeneo.ai 服务器功能，包括生成 AI 视频镜头（Powered by MiniMax H3，部分国家/地区不可用）、在服务器上渲染 HTML 动画叠加层，以及私密云端存储。需要先登录。

### 环境要求

需要支持插件的 Claude Code 或 Codex CLI，并安装 `ffmpeg`（自带 `ffprobe`）和 `uv`，确保在终端里能直接运行。

| 系统 | 安装方式 |
|---|---|
| macOS | `brew install ffmpeg-full uv`（字幕需要 `ffmpeg-full`） |
| Windows | `winget install Gyan.FFmpeg` 和 `winget install astral-sh.uv`，然后重新打开终端 |
| Linux（Debian/Ubuntu） | `sudo apt install ffmpeg`，uv 用 `curl -LsSf https://astral.sh/uv/install.sh \| sh` 安装；其他发行版请使用相应的包管理器 |

可以用 `ffmpeg -version`、`ffprobe -version` 和 `uv --version` 检查是否装好。无需自己安装 Python，uv 会自动处理。做泰语字幕时建议安装免费的 Kanit 字体（Google Fonts），显示效果更好；没有安装时会使用系统自带的泰文字体。

### 安装

**Claude Code**：在 Claude Code 中输入以下命令，然后重启 Claude Code。

```
/plugin marketplace add Boom-Vitt/seeneo-plugin
/plugin install seeneo@seeneo
```

**Codex**：在终端中运行以下命令，然后开启新的 Codex 会话。

```
codex plugin marketplace add Boom-Vitt/seeneo-plugin
codex plugin add seeneo@seeneo
```

Codex 可能会在每次调用工具前询问你。如果想让本地工具直接运行、不再询问，请在 `~/.codex/config.toml` 中加入：

```toml
[plugins."seeneo@seeneo".mcp_servers.seeneo-local]
default_tools_approval_mode = "approve"
```

可以这样试试：*“把 ~/Videos/talk.mp4 里的静音段剪掉，加上中文字幕，做成 9:16 竖屏。”*

**文件保存位置**：在 Claude Code 中，导出的文件保存在你启动 Claude Code 的文件夹下的 `seeneo-out` 里；如需换个位置，请在启动 Claude Code 前设置环境变量 `SEENEO_OUT_DIR`。在 Codex 中，文件保存在第一个视频所在文件夹的 `seeneo-out` 里，因为 Codex 不会告诉插件你当前在哪个文件夹工作。

**更新**：在 Claude Code 中输入 `/plugin marketplace update seeneo`；在 Codex 中运行 `codex plugin marketplace upgrade`。

### 隐私

- **本地工具完全在你的电脑上运行。** 视频、音频和导出文件都留在本地。无需账号，也不会追踪使用情况。
- **仅需下载两项内容，各下载一次。** 首次启动时会下载工具所需的 Python 组件，首次转写时会下载语音识别文件并保存下来，以后重复使用。除此之外，工具本身不会再联网。
- **你的 AI 助手会看到工具返回的内容。** 预览拼图、转写文本和文件信息会返回给 Claude Code 或 Codex，它们可能会像对话中的其他内容一样发送给其 AI 服务商。seeneo 不会收到这些内容。
- **只有当你需要电脑本身做不到的功能时，才会用到 seeneo.ai 服务器**，例如 AI 视频镜头、服务器渲染叠加层或云端副本。技能要求 AI 助手在上传任何文件前先征得你的同意，并说明要上传哪些文件。
- 上传的文件私密保存在你的 seeneo.ai 账号中。下载链接仅限你本人访问，且很快失效，你也可以随时删除项目。纯文字生成的 AI 镜头只会发送你写的文字描述。

### 免费与付费

| | 费用 | 账号 |
|---|---|---|
| 插件和本地工具 | 始终免费 | 不需要 |
| seeneo 服务器功能 | 付费操作使用积分（1 积分 = 1 泰铢）。每项付费操作前，AI 助手都会先告诉你准确价格，等你同意后才执行。 | 需要登录 seeneo.ai。目前使用积分还需要有效的 seeneo 套餐（每月 299 泰铢）。 |
| seeneo.ai 网页版 | seeneo 套餐，每月 299 泰铢 | seeneo.ai 账号 |

如需使用服务器功能，请用 seeneo.ai 账号登录：在 Claude Code 中输入 `/mcp` 并选择 `seeneo`；在 Codex 中，在终端运行 `codex mcp login seeneo`，然后在浏览器中完成登录。登录始终在浏览器中的 seeneo.ai 登录页面完成，seeneo 绝不会要求你把 API 密钥、令牌或密码粘贴到 AI 助手或配置文件中。只使用本地工具时无需登录。

### 卸载

Claude Code：

```
/plugin uninstall seeneo@seeneo
/plugin marketplace remove seeneo
```

Codex：

```
codex plugin remove seeneo@seeneo
codex plugin marketplace remove seeneo
```

如需退出 seeneo 登录，请在卸载前操作：在 Claude Code 中进入 `/mcp` → `seeneo` → Clear authentication，在 Codex 中运行 `codex mcp logout seeneo`。`seeneo-out` 里的导出文件会保留，需要的话请自行删除。语音识别文件在 `~/.cache/seeneo/speech`（如设置了 `SEENEO_MODEL_DIR` 则在该目录）中，删除该文件夹即可释放空间。Python 组件在 uv 的缓存里，`uv cache clean` 可以清除，但会连其他项目的缓存一起清空。

---

License: [MIT](LICENSE)

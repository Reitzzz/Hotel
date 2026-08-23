# 项目概况

- 单文件 Tkinter 桌面应用：hotel_manager.py，仅用标准库，无 requirements.txt，无自动化测试。
- 修改代码后用 `D:\Python\python.exe hotel_manager.py` 启动 GUI 做冒烟验证。
- 文件名 hotel_manager.py 是工作区定位标记（与 .git 一起被 find_workspace_dir 识别），不要改名，否则打包版会找不到 data/ 目录。

# Python 环境约定

- 不要使用 PATH 中的裸 `python` 命令；它可能指向 LibreOffice 内置 Python。
- 运行脚本和安装依赖时，统一使用 `D:\Python\python.exe`。

# 数据文件约定（重要）

- 数据按年存放在 `data/hotel_stay_records_<年份>.md`（UTF-8），表头固定 9 列：
  名称 | 入住时间 | 间夜 | 房型 | 总价 | 积分 | 开业信息 | 版本 | 备注
- 入住时间格式为 `M.D-M.D`（如 1.16-1.18，跨年写 12.30-1.2）；间夜由应用自动计算为 `N间夜`。
- 单元格中的 `|` 必须写成全角 `｜`，连续空白会被折叠为一个空格；积分留空时存 `/`。
- 记录按入住日期排序，保存时整个文件被重写；列数不符的行会被判为格式异常并导致应用拒绝保存。
  手工编辑数据文件时必须严格保持表格结构。
- `data_backups/autosave/*.bak` 由应用在每次写入时自动刷新，不要手工编辑。
- `data_backups/` 下的日期目录是历史快照，保留旧表头格式属正常现象，应用会自动迁移，不要去改。

# 打包发布

- 打包发布版时，使用：

  ```powershell
  D:\Python\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name HotelManagerWithIcon --icon C:\Users\16088\Desktop\Code\Hotel\assets\app-icon.ico --distpath release\HotelManager hotel_manager.py
  ```

- 图标参数必须使用绝对路径，避免 PyInstaller 在临时 spec 目录中找不到图标文件。
- 上面的命令是 PowerShell 语法；如果在 Git Bash 中执行，distpath 要写成 `release/HotelManager`（正斜杠），
  否则 `\H` 被转义，产物会输出到错误的 `releaseHotelManager/` 目录。
- 打包完成后删除工作区里的 `build/`、`HotelManagerWithIcon.spec`、`__pycache__/`，仓库不跟踪这些中间产物。
- 打包产物 release/HotelManager/HotelManagerWithIcon.exe 需提交进仓库：改代码后重新打包并连同 exe 一起提交。

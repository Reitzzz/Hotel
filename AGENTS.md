# Python 环境约定

- 不要使用 PATH 中的裸 `python` 命令；它可能指向 LibreOffice 内置 Python。
- 运行脚本、执行测试和安装依赖时，统一使用 `D:\Python\python.exe`。
- 打包发布版时，使用：

  ```powershell
  D:\Python\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name HotelManagerWithIcon --icon C:\Users\16088\Desktop\Code\Hotel\assets\app-icon.ico --distpath release\HotelManager hotel_manager.py
  ```

- 图标参数必须使用绝对路径，避免 PyInstaller 在临时 spec 目录中找不到图标文件。

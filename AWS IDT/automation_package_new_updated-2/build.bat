pyinstaller -F .\redirect_tkinter.py  --hidden-import=configparser  --onefile
pyinstaller -F .\terminationStack.py  --hidden-import=configparser  --onefile
pyinstaller -F .\streetLampAutomation.py  --hidden-import=configparser  --onefile
pyinstaller -F .\my_logger.py  --hidden-import=configparser  --onefile
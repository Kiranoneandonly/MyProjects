[CmdletBinding()] Param(
    $pythonVersion = "3.6.2",
    $pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion.exe",
    $pythonDownloadPath = "C:\Tools\python-$pythonVersion.exe",
    $pythonInstallDir = "C:\Tools\Python$pythonVersion"
)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
(New-Object Net.WebClient).DownloadFile($pythonUrl, $pythonDownloadPath)
& $pythonDownloadPath /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir=$pythonInstallDir
#if ($LASTEXITCODE -ne 0) {
#    throw "The python installer at '$pythonDownloadPath' exited with error code '$LASTEXITCODE'"
#}

# setting the path variables
#[Environment]::SetEnvironmentVariable("PATH", "${env:path};${pythonInstallDir}", "Machine")

pip install boto3

aws configure

python .\streetLampAutomation.py kbilgund-idt
# Lanza run_bloques.sh como proceso de Windows independiente de la sesión de Claude (retomable: volver a ejecutar este script reanuda).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bash = 'C:\Program Files\Git\bin\bash.exe'
Start-Process -FilePath $bash -ArgumentList @('-lc', "'$($here -replace '\','/')/run_bloques.sh'") -WindowStyle Hidden

param(
    [Parameter(Mandatory)][string]$OllamaPath,
    [string]$DataDirectory = (Join-Path $PSScriptRoot '..\private\analyst\model-runtime')
)
# A separate local process and model store. No user/system environment changes.
$ErrorActionPreference = 'Stop'
$taskData = [IO.Path]::GetFullPath($DataDirectory)
if (-not (Test-Path -LiteralPath $OllamaPath -PathType Leaf)) { throw 'Ollama executable missing.' }
if (Get-NetTCPConnection -LocalPort 11435 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 11435 already has a listener. Inspect its recorded owner before reusing it.'
}
New-Item -ItemType Directory -Path $taskData -Force | Out-Null
$taskEnv = @{
    OLLAMA_HOST='127.0.0.1:11435'; OLLAMA_MODELS=(Join-Path $taskData 'models')
    OLLAMA_NO_CLOUD='1'; OLLAMA_NUM_PARALLEL='1'; OLLAMA_MAX_LOADED_MODELS='1'
    OLLAMA_CONTEXT_LENGTH='4096'; OLLAMA_KEEP_ALIVE='0'
    CUDA_VISIBLE_DEVICES='-1'; HIP_VISIBLE_DEVICES='-1'; ROCR_VISIBLE_DEVICES='-1'
    GGML_VK_VISIBLE_DEVICES='-1'
}
$taskStamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$taskStdout=Join-Path $taskData ("server-$taskStamp.stdout.log")
$taskStderr=Join-Path $taskData ("server-$taskStamp.stderr.log")
$taskProcess = Start-Process -FilePath $OllamaPath -ArgumentList 'serve' -Environment $taskEnv -WindowStyle Hidden -PassThru -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr
try { $taskProcess.PriorityClass = 'BelowNormal' } catch { }
$taskOwner=[pscustomobject]@{pid=$taskProcess.Id;started_utc=[DateTime]::UtcNow.ToString('o');executable=$OllamaPath;endpoint='http://127.0.0.1:11435';models=$taskEnv.OLLAMA_MODELS;cpu_request_threads=2;gpu_request_layers=0;cloud_disabled=$true;stdout=$taskStdout;stderr=$taskStderr}
$taskOwner | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskData "owner-$taskStamp.json") -Encoding utf8
$taskOwner | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskData 'owner.json') -Encoding utf8
Write-Output "Separate analyst runtime started as PID $($taskProcess.Id), loopback port 11435. Read owner.json and server logs to verify startup."

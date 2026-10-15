param(
    [Parameter(Mandatory)][string]$OllamaPath,
    [Parameter(Mandatory)][string]$ModelsDirectory,
    [Parameter(Mandatory)][string]$DataDirectory
)
# Separate GPU acceptance endpoint. Never replaces 11434 or 11435.
$ErrorActionPreference='Stop'
if(Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue){throw 'GPU acceptance port already occupied; inspect its owner.'}
if(-not(Test-Path -LiteralPath $OllamaPath -PathType Leaf) -or -not(Test-Path -LiteralPath $ModelsDirectory -PathType Container)){throw 'Installed runtime/model store missing.'}
$taskData=[IO.Path]::GetFullPath($DataDirectory)
New-Item -ItemType Directory -Path $taskData -Force | Out-Null
$taskStamp=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$taskEnv=@{
    OLLAMA_HOST='127.0.0.1:11436'; OLLAMA_MODELS=[IO.Path]::GetFullPath($ModelsDirectory)
    OLLAMA_NO_CLOUD='1'; OLLAMA_NOPRUNE='1'; OLLAMA_NUM_PARALLEL='1'
    OLLAMA_MAX_LOADED_MODELS='1'; OLLAMA_MAX_QUEUE='1'; OLLAMA_CONTEXT_LENGTH='4096'
    OLLAMA_KEEP_ALIVE='0'; OLLAMA_VULKAN='1'; OLLAMA_IGPU_ENABLE='1'
    CUDA_VISIBLE_DEVICES='-1'; HIP_VISIBLE_DEVICES='-1'; ROCR_VISIBLE_DEVICES='-1'
    GGML_VK_VISIBLE_DEVICES='0'
}
$taskStdout=Join-Path $taskData ('server-'+$taskStamp+'.stdout.log')
$taskStderr=Join-Path $taskData ('server-'+$taskStamp+'.stderr.log')
$taskProcess=Start-Process -FilePath $OllamaPath -ArgumentList 'serve' -Environment $taskEnv -WindowStyle Hidden -PassThru -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr
try{$taskProcess.PriorityClass='BelowNormal'}catch{}
$taskOwner=[ordered]@{pid=$taskProcess.Id;started_utc=[DateTime]::UtcNow.ToString('o');executable=$OllamaPath;endpoint='http://127.0.0.1:11436';models=$taskEnv.OLLAMA_MODELS;backend_requested='Vulkan device 0';cloud_disabled=$true;no_prune=$true;stdout=$taskStdout;stderr=$taskStderr}
$taskOwner | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskData 'owner.json') -Encoding utf8
$taskOwner | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskData ('owner-'+$taskStamp+'.json')) -Encoding utf8
$taskOwner | ConvertTo-Json

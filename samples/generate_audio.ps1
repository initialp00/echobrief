# Generates sample incident-brief audio files (WAV) from text using the
# built-in Windows text-to-speech engine, plus matching .txt transcripts.
#
# Usage:  pwsh -File samples/generate_audio.ps1   (or run in Windows PowerShell)
# Output: samples/audio/*.wav  and  samples/transcripts/*.txt

Add-Type -AssemblyName System.Speech

$root        = Split-Path -Parent $MyInvocation.MyCommand.Path
$audioDir    = Join-Path $root "audio"
$scriptDir   = Join-Path $root "transcripts"
New-Item -ItemType Directory -Force -Path $audioDir  | Out-Null
New-Item -ItemType Directory -Force -Path $scriptDir | Out-Null

# Each brief: file name, preferred voice, and the spoken incident text.
$briefs = @(
    @{
        name  = "01-api-gateway-redis"
        voice = "Microsoft Zira Desktop"
        text  = "This is Nishil with an incident brief. At 14:32 UTC we started seeing elevated 5xx errors on the API gateway. Error rate peaked at 23 percent around 14:38. The auth service was returning connection timeouts. Root cause was Redis connection pool exhaustion after a config change deployed at 14:15. We rolled back the config at 14:47 and error rates normalised by 14:52. Action items: increase the connection pool size, add a connection pool monitoring alert, and add a config change freeze window during peak hours."
    },
    @{
        name  = "02-checkout-latency-db"
        voice = "Microsoft Hazel Desktop"
        text  = "Hi, this is Priya with a post incident brief. Around 21:05 UTC checkout requests started timing out. About 40 percent of users could not complete purchases. The payments service was hitting a connection limit on the primary database after an autoscaling misconfiguration pushed too many pods at 20:50. We reduced the max pod count and restarted the payments service at 21:20, and checkout recovered by 21:28. Follow ups: cap the payments pod count, add a database connection saturation alert, and review the autoscaling policy."
    },
    @{
        name  = "03-dns-resolution-outage"
        voice = "Microsoft Zira Desktop"
        text  = "This is Marcus reporting an incident. At 08:14 UTC internal services could not resolve DNS for the payments and notifications domains, causing a complete outage for background jobs. The cause was an expired internal certificate on the DNS resolver that was not rotated by automation. We manually rotated the certificate and restarted the resolver at 08:39, and resolution recovered by 08:45. Action items: fix the certificate rotation automation, add an expiry alert 30 days out, and add a synthetic DNS health check."
    },
    @{
        name  = "04-cache-stampede-minor"
        voice = "Microsoft Hazel Desktop"
        text  = "Hey, this is Aisha with a quick brief. At 12:03 UTC we saw a brief latency bump on the product catalog service after a cache node restarted, triggering a small cache stampede. Impact was minor, a few slow requests for about two minutes. No user reports. The cache warmed up and latency returned to normal by 12:06. Action items: add request coalescing on cache misses and stagger cache node restarts."
    }
)

foreach ($b in $briefs) {
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try { $synth.SelectVoice($b.voice) } catch { }  # fall back to default voice
    $synth.Rate = -1  # slightly slower for clarity

    $wavPath = Join-Path $audioDir ($b.name + ".wav")
    $txtPath = Join-Path $scriptDir ($b.name + ".txt")

    $synth.SetOutputToWaveFile($wavPath)
    $synth.Speak($b.text)
    $synth.SetOutputToNull()
    $synth.Dispose()

    Set-Content -Path $txtPath -Value $b.text -Encoding UTF8
    $sizeKb = [math]::Round((Get-Item $wavPath).Length / 1KB, 1)
    Write-Host ("generated {0}.wav ({1} KB) + transcript" -f $b.name, $sizeKb)
}

Write-Host "Done. Audio in samples/audio, transcripts in samples/transcripts."

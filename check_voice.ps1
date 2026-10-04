Add-Type -AssemblyName System.Speech
$clipfarmVoice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$clipfarmVoice.SetOutputToWaveFile((Join-Path $PSScriptRoot 'checks\speech.wav'))
$clipfarmVoice.Rate = -1
$clipfarmVoice.Speak('Here is a mistake that can ruin your first video. You spend hours choosing a camera, and forget to tell a clear story. My first recording was beautiful, but nobody understood the point. Then I tried a simple experiment. I recorded the same idea on my phone, and started with the result. The difference was dramatic. People stayed because they wanted to know how it happened. So before recording your next video, write one sentence. What should the viewer remember? Build your opening around that sentence. Show an example, explain what changed, and finish with one useful action. A better camera can improve the picture. A better story gives people a reason to watch. Try it on your next recording and compare the results.')
$clipfarmVoice.Dispose()

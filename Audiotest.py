from gtts import gTTS

# Create a TTS object with the message
tts = gTTS("Left", lang='en')

# Save the audio file
tts.save("/home/pi/hailo-rpi5-examples/basic_pipelines/audios/left.wav")

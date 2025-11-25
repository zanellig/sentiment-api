from pysentimiento import create_analyzer

sentiment_analyzer = create_analyzer(task="sentiment", lang="es")
emotion_analyzer = create_analyzer(task="emotion", lang="es")
hate_speech_analyzer = create_analyzer(task="hate_speech", lang="es")

sent_prediction = sentiment_analyzer.predict("Odio este frío!!!")
emot_prediction = emotion_analyzer.predict("Odio este frío!!!")
hate_prediction = hate_speech_analyzer.predict("Odio este frío!!!")

print(sent_prediction)
print(emot_prediction)
print(hate_prediction)
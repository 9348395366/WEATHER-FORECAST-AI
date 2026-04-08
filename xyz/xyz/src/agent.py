
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import re
from typing import Callable, Dict, Iterable, Tuple


@dataclass
class AgentContext:
    latitude: float
    longitude: float
    dataset_summary: Dict[str, object] | None
    model_metrics: Dict[str, object] | None
    location_label: str | None = None
    last_suggested_intent: str | None = None


@dataclass
class AgentResult:
    reply: str
    tool_used: str | None = None
    suggested_intent: str | None = None


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _contains_word(text: str, words: Iterable[str]) -> bool:
    tokens = re.findall(r"[\w']+", text, flags=re.UNICODE)
    return any(token in words for token in tokens)


TIME_GREETINGS = {
    "en": {
        "morning": "Good morning",
        "afternoon": "Good afternoon",
        "evening": "Good evening",
        "night": "Good night",
    },
    "hi": {
        "morning": "सुप्रभात",
        "afternoon": "नमस्कार",
        "evening": "शुभ संध्या",
        "night": "शुभ रात्रि",
    },
    "or": {
        "morning": "ଶୁଭ ସକାଳ",
        "afternoon": "ନମସ୍କାର",
        "evening": "ଶୁଭ ସନ୍ଧ୍ୟା",
        "night": "ଶୁଭ ରାତ୍ରି",
    },
}


DEFAULT_STRIP_PREFIXES = {
    "current_weather": ["Current conditions:"],
    "forecast_summary": ["Next 12 hours:"],
    "air_quality": ["Air quality:"],
    "uv_index": ["Current UV index:"],
    "wind": ["Wind"],
    "humidity": ["Current humidity:"],
    "visibility": ["Visibility:"],
    "pressure": ["Surface pressure:"],
    "location": ["You are near:", "Location:"],
    "dataset_summary": ["Dataset rows:"],
    "model_summary": ["Model MAE:"],
}


BASE_PACK: Dict[str, object] = {
    "greetings": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "good night"],
    "help_words": ["help", "what can you do", "capabilities", "options"],
    "thanks_words": ["thanks", "thank you", "thx", "appreciate"],
    "bye_words": ["bye", "goodbye", "see you", "later"],
    "how_are_you": ["how are you", "how are u", "how's it going", "how are things"],
    "identity_words": ["who are you", "what are you", "your name"],
    "affirm_words": {"yes", "yeah", "yep", "ok", "okay", "sure", "please"},
    "affirm_phrases": ["go ahead", "do it", "sounds good", "please do"],
    "negative_words": {"no", "nope", "nah", "not now"},
    "app_info_words": [
        "app info",
        "application info",
        "application details",
        "app details",
        "app overview",
        "application overview",
        "about the app",
        "about this app",
        "about the application",
    ],
    "all_details_words": [
        "all details",
        "all information",
        "full details",
        "all stats",
        "all data",
        "show all",
        "show everything",
        "give me everything",
        "all application information",
        "all application details",
    ],
    "intent_titles": {
        "current_weather": "Current weather",
        "forecast_summary": "Forecast",
        "air_quality": "Air quality",
        "uv_index": "UV index",
        "wind": "Wind",
        "humidity": "Humidity",
        "visibility": "Visibility",
        "pressure": "Pressure",
        "location": "Location",
        "dataset_summary": "Dataset",
        "model_summary": "Model",
    },
    "prefixes": {
        "current_weather": "Here's the latest:",
        "forecast_summary": "Here's a quick look:",
        "air_quality": "Air quality check:",
        "uv_index": "UV check:",
        "wind": "Wind right now:",
        "humidity": "Humidity right now:",
        "visibility": "Visibility right now:",
        "pressure": "Pressure right now:",
        "location": "I'm using this location:",
        "dataset_summary": "Dataset summary:",
        "model_summary": "Model summary:",
    },
    "follow_ups": {
        "current_weather": "Want the forecast or air quality next?",
        "forecast_summary": "Want current conditions too?",
        "air_quality": "Want the UV index as well?",
        "uv_index": "Want air quality details too?",
        "wind": "Want current conditions or the forecast?",
        "humidity": "Want wind or air quality next?",
        "visibility": "Want current conditions or the forecast?",
        "pressure": "Want current conditions or the forecast?",
        "location": "Want current conditions for this location?",
        "dataset_summary": "Want model performance too?",
        "model_summary": "Want dataset stats as well?",
    },
    "responses": {
        "thanks": "You're welcome. Want to check anything else?",
        "bye": "Anytime. Come back if you need updates.",
        "how_are_you": "Doing well. {greeting}! Want current conditions or the forecast?",
        "identity": "I'm your weather assistant. Want current conditions or a forecast?",
        "negative": "No worries. What would you like to check instead?",
        "help": (
            "I can share current conditions, a short-term forecast, air quality, UV index, "
            "wind, humidity, visibility, pressure, your location label, and dataset/model summaries. "
            "You can ask for multiple items in one message and I'll combine them. "
            "Want current conditions or the forecast?"
        ),
        "all_details_header": "Here is everything I can share right now:",
        "combined_header": "Here is a combined update:",
        "starter": (
            "I'm best at weather, air quality, and dataset/model questions. "
            "Want current conditions, a forecast, or air quality?"
        ),
        "app_details_header": "App details:",
        "app_details_tip": "Tip: ask multiple items in one message and I'll combine them.",
        "no_details": "I don't have any details available right now.",
        "capabilities_line": (
            "- Capabilities: current conditions, short-term forecast, air quality (AQI/PM2.5/PM10), "
            "UV index, wind, humidity, visibility, pressure, and location label."
        ),
        "location_line": "- Location context: {location}.",
        "dataset_line": "- Dataset: {rows} rows, range {start} to {end}, columns: {columns}.",
        "dataset_missing": "- Dataset: not available yet.",
        "model_line": "- Model: MAE {mae:.3f} (data source: {source}).",
        "model_missing": "- Model: metrics are not available yet.",
        "dataset_summary_template": "Dataset rows: {rows}. Range {start} to {end}. Columns: {columns}.",
        "dataset_summary_missing": "Dataset summary isn't available yet.",
        "model_summary_template": "Model MAE: {mae:.3f} (data source: {source}).",
        "model_summary_missing": "Model metrics are not available yet.",
    },
    "ui": {
        "intro_message": "Hey! I'm here to help. Ask about the weather or just say hi.",
        "vent_label": "Let me know if you need to vent.",
        "choose_conversation": "Choose conversation",
        "voice_toggle": "Voice Output",
        "wake_word_toggle": "Wake Word (Hi Siri)",
        "language_label": "Language",
        "placeholder": "Type a message...",
        "send_label": "Send",
        "wake_word_trigger": "hi",
    },
}


LANGUAGE_OVERRIDES: Dict[str, Dict[str, object]] = {
    "hi": {
        "greetings": ["नमस्ते", "हाय", "हेलो", "सुप्रभात", "शुभ संध्या", "नमस्कार"],
        "help_words": ["मदद", "सहायता", "क्या कर सकते हो", "क्या कर सकते हैं"],
        "thanks_words": ["धन्यवाद", "शुक्रिया"],
        "bye_words": ["अलविदा", "फिर मिलेंगे", "चलते हैं"],
        "how_are_you": ["कैसे हो", "कैसे हैं", "क्या हाल है"],
        "identity_words": ["तुम कौन हो", "आप कौन हैं", "तुम्हारा नाम", "आपका नाम"],
        "affirm_words": {"हाँ", "हां", "जी", "ठीक", "ठीक है", "ज़रूर", "जरूर"},
        "affirm_phrases": ["कर दीजिए", "कर दो"],
        "negative_words": {"नहीं", "ना", "मत"},
        "app_info_words": ["ऐप जानकारी", "ऐप विवरण", "ऐप के बारे में"],
        "all_details_words": ["सब जानकारी", "सब विवरण", "सब कुछ", "पूरी जानकारी"],
        "intent_titles": {
            "current_weather": "वर्तमान मौसम",
            "forecast_summary": "पूर्वानुमान",
            "air_quality": "वायु गुणवत्ता",
            "uv_index": "यूवी इंडेक्स",
            "wind": "हवा",
            "humidity": "नमी",
            "visibility": "दृश्यता",
            "pressure": "दबाव",
            "location": "स्थान",
            "dataset_summary": "डेटासेट",
            "model_summary": "मॉडल",
        },
        "prefixes": {
            "current_weather": "यह रहा ताज़ा अपडेट:",
            "forecast_summary": "यह रहा त्वरित अपडेट:",
            "air_quality": "वायु गुणवत्ता:",
            "uv_index": "यूवी जांच:",
            "wind": "अभी हवा:",
            "humidity": "अभी नमी:",
            "visibility": "अभी दृश्यता:",
            "pressure": "अभी दबाव:",
            "location": "मैं यह स्थान उपयोग कर रहा हूँ:",
            "dataset_summary": "डेटासेट सारांश:",
            "model_summary": "मॉडल सारांश:",
        },
        "follow_ups": {
            "current_weather": "क्या आप पूर्वानुमान या वायु गुणवत्ता देखना चाहेंगे?",
            "forecast_summary": "क्या आप वर्तमान स्थिति भी चाहेंगे?",
            "air_quality": "यूवी इंडेक्स भी देखना चाहेंगे?",
            "uv_index": "वायु गुणवत्ता विवरण भी चाहेंगे?",
            "wind": "वर्तमान स्थिति या पूर्वानुमान देखना चाहेंगे?",
            "humidity": "हवा या वायु गुणवत्ता देखना चाहेंगे?",
            "visibility": "वर्तमान स्थिति या पूर्वानुमान देखना चाहेंगे?",
            "pressure": "वर्तमान स्थिति या पूर्वानुमान देखना चाहेंगे?",
            "location": "इस स्थान के लिए वर्तमान मौसम चाहिए?",
            "dataset_summary": "मॉडल प्रदर्शन भी चाहिए?",
            "model_summary": "डेटासेट आँकड़े भी चाहिए?",
        },
        "responses": {
            "thanks": "कोई बात नहीं। कुछ और देखना चाहते हैं?",
            "bye": "जब भी चाहिए, आ जाइए।",
            "how_are_you": "मैं ठीक हूँ। {greeting}! वर्तमान मौसम चाहिए या पूर्वानुमान?",
            "identity": "मैं आपका मौसम सहायक हूँ। वर्तमान मौसम या पूर्वानुमान चाहिए?",
            "negative": "ठीक है। आप क्या देखना चाहेंगे?",
            "help": (
                "मैं वर्तमान स्थिति, छोटा पूर्वानुमान, वायु गुणवत्ता, यूवी इंडेक्स, "
                "हवा, नमी, दृश्यता, दबाव, स्थान, और dataset/model सारांश बता सकता हूँ। "
                "आप एक संदेश में कई चीज़ें पूछ सकते हैं। "
                "वर्तमान मौसम या पूर्वानुमान चाहिए?"
            ),
            "all_details_header": "यह रहा सब कुछ जो मैं अभी साझा कर सकता हूँ:",
            "combined_header": "यह रहा संयुक्त अपडेट:",
            "starter": (
                "मैं मौसम, वायु गुणवत्ता, और dataset/model सवालों में सबसे अच्छा हूँ। "
                "वर्तमान मौसम, पूर्वानुमान, या वायु गुणवत्ता?"
            ),
            "app_details_header": "ऐप विवरण:",
            "app_details_tip": "टिप: एक संदेश में कई चीज़ें पूछें, मैं जोड़ दूँगा।",
            "no_details": "अभी कोई विवरण उपलब्ध नहीं है।",
            "capabilities_line": (
                "- क्षमताएँ: वर्तमान स्थिति, छोटा पूर्वानुमान, वायु गुणवत्ता (AQI/PM2.5/PM10), "
                "यूवी इंडेक्स, हवा, नमी, दृश्यता, दबाव, और स्थान लेबल।"
            ),
            "location_line": "- स्थान संदर्भ: {location}.",
            "dataset_line": "- डेटासेट: {rows} पंक्तियाँ, सीमा {start} से {end}, कॉलम: {columns}.",
            "dataset_missing": "- डेटासेट: अभी उपलब्ध नहीं।",
            "model_line": "- मॉडल: MAE {mae:.3f} (डेटा स्रोत: {source}).",
            "model_missing": "- मॉडल: मीट्रिक्स अभी उपलब्ध नहीं।",
            "dataset_summary_template": "डेटासेट पंक्तियाँ: {rows}. सीमा {start} से {end}. कॉलम: {columns}.",
            "dataset_summary_missing": "डेटासेट सारांश अभी उपलब्ध नहीं है।",
            "model_summary_template": "मॉडल MAE: {mae:.3f} (डेटा स्रोत: {source}).",
            "model_summary_missing": "मॉडल मीट्रिक्स अभी उपलब्ध नहीं हैं।",
        },
        "ui": {
            "intro_message": "नमस्ते! मैं मदद के लिए हूँ। मौसम के बारे में पूछें या बस नमस्ते कहें।",
            "vent_label": "अगर कुछ कहना हो तो बताइए।",
            "choose_conversation": "बातचीत चुनें",
            "voice_toggle": "आवाज़ आउटपुट",
            "wake_word_toggle": "वेक वर्ड (Hi Siri)",
            "language_label": "भाषा",
            "placeholder": "संदेश लिखें...",
            "send_label": "भेजें",
            "wake_word_trigger": "नमस्ते",
        },
    },
    "or": {
        "greetings": ["ନମସ୍କାର", "ହେଲୋ", "ହାଇ"],
        "help_words": ["ସହାୟତା", "ମଦଦ", "କଣ କରିପାରିବେ"],
        "thanks_words": ["ଧନ୍ୟବାଦ"],
        "bye_words": ["ବିଦାୟ", "ଆଉ ଦେଖାହେବ"],
        "how_are_you": ["କେମିତି ଅଛ", "କେମିତି ଅଛନ୍ତି"],
        "identity_words": ["ତୁମେ କିଏ", "ଆପଣ କିଏ", "ତୁମର ନାମ"],
        "affirm_words": {"ହଁ", "ଠିକ୍", "ନିଶ୍ଚୟ"},
        "affirm_phrases": ["କରନ୍ତୁ"],
        "negative_words": {"ନା", "ନୁହେଁ"},
        "app_info_words": ["ଆପ୍ ସୂଚନା", "ଆପ୍ ବିବରଣୀ"],
        "all_details_words": ["ସବୁ ସୂଚନା", "ସବୁ ବିବରଣୀ", "ସବୁ କିଛି"],
        "intent_titles": {
            "current_weather": "ଏବେର ପାଣିପାଗ",
            "forecast_summary": "ପୂର୍ବାନୁମାନ",
            "air_quality": "ବାୟୁ ଗୁଣତା",
            "uv_index": "ୟୁଭି ଇଣ୍ଡେକ୍ସ",
            "wind": "ପବନ",
            "humidity": "ଆର୍ଦ୍ରତା",
            "visibility": "ଦୃଶ୍ୟମାନତା",
            "pressure": "ଚାପ",
            "location": "ଅବସ୍ଥାନ",
            "dataset_summary": "ଡାଟାସେଟ୍",
            "model_summary": "ମଡେଲ୍",
        },
        "prefixes": {
            "current_weather": "ନବୀନତମ ସୂଚନା:",
            "forecast_summary": "ସଂକ୍ଷିପ୍ତ ଅପଡେଟ୍:",
            "air_quality": "ବାୟୁ ଗୁଣତା:",
            "uv_index": "ୟୁଭି ଯାଞ୍ଚ:",
            "wind": "ଏବେ ପବନ:",
            "humidity": "ଏବେ ଆର୍ଦ୍ରତା:",
            "visibility": "ଏବେ ଦୃଶ୍ୟମାନତା:",
            "pressure": "ଏବେ ଚାପ:",
            "location": "ମୁଁ ଏହି ଅବସ୍ଥାନ ବ୍ୟବହାର କରୁଛି:",
            "dataset_summary": "ଡାଟାସେଟ୍ ସାରଂଶ:",
            "model_summary": "ମଡେଲ୍ ସାରଂଶ:",
        },
        "follow_ups": {
            "current_weather": "ପୂର୍ବାନୁମାନ କିମ୍ବା ବାୟୁ ଗୁଣତା ଦେଖିବେ?",
            "forecast_summary": "ଏବେର ପାଣିପାଗ ମଧ୍ୟ ଚାହାଁନ୍ତି କି?",
            "air_quality": "ୟୁଭି ଇଣ୍ଡେକ୍ସ ମଧ୍ୟ ଦେଖିବେ?",
            "uv_index": "ବାୟୁ ଗୁଣତା ବିସ୍ତାର ଚାହାଁନ୍ତି କି?",
            "wind": "ଏବେର ପାଣିପାଗ କିମ୍ବା ପୂର୍ବାନୁମାନ ଦେଖିବେ?",
            "humidity": "ପବନ କିମ୍ବା ବାୟୁ ଗୁଣତା ଦେଖିବେ?",
            "visibility": "ଏବେର ପାଣିପାଗ କିମ୍ବା ପୂର୍ବାନୁମାନ ଦେଖିବେ?",
            "pressure": "ଏବେର ପାଣିପାଗ କିମ୍ବା ପୂର୍ବାନୁମାନ ଦେଖିବେ?",
            "location": "ଏହି ଅବସ୍ଥାନ ପାଇଁ ଏବେର ପାଣିପାଗ ଚାହାଁନ୍ତି କି?",
            "dataset_summary": "ମଡେଲ୍ ପରିଣାମ ମଧ୍ୟ ଚାହାଁନ୍ତି କି?",
            "model_summary": "ଡାଟାସେଟ୍ ତଥ୍ୟ ମଧ୍ୟ ଚାହାଁନ୍ତି କି?",
        },
        "responses": {
            "thanks": "ଧନ୍ୟବାଦ! ଆଉ କିଛି ଦେଖିବେ କି?",
            "bye": "ଯେତେବେଳେ ଚାହିଁବେ ଫେରନ୍ତୁ।",
            "how_are_you": "ମୁଁ ଭଲ ଅଛି। {greeting}! ଏବେର ପାଣିପାଗ କିମ୍ବା ପୂର୍ବାନୁମାନ?",
            "identity": "ମୁଁ ଆପଣଙ୍କ ପାଣିପାଗ ସହାୟକ। ଏବେର ପାଣିପାଗ କିମ୍ବା ପୂର୍ବାନୁମାନ?",
            "negative": "ଠିକ୍ ଅଛି। ଆଉ କଣ ଦେଖିବେ?",
            "help": (
                "ମୁଁ ଏବେର ପାଣିପାଗ, ସ୍ଵଳ୍ପ ସମୟର ପୂର୍ବାନୁମାନ, ବାୟୁ ଗୁଣତା, ଯୁଭି, "
                "ପବନ, ଆର୍ଦ୍ରତା, ଦୃଶ୍ୟମାନତା, ଚାପ, ଅବସ୍ଥାନ, ଏବଂ dataset/model ସାରଂଶ କହିପାରିବି। "
                "ଏକ ମେସେଜରେ ଅନେକ ଜିନିଷ ପଚାରନ୍ତୁ। "
                "ଏବେର ପାଣିପାଗ କିମ୍ବା ପୂର୍ବାନୁମାନ?"
            ),
            "all_details_header": "ଏହା ହେଉଛି ମୋ ପାଖରେ ଥିବା ସମସ୍ତ ତଥ୍ୟ:",
            "combined_header": "ଏଠାରେ ଯୁକ୍ତ ଅପଡେଟ୍:",
            "starter": (
                "ମୁଁ ପାଣିପାଗ, ବାୟୁ ଗୁଣତା, ଏବଂ dataset/model ପ୍ରଶ୍ନରେ ସହାୟକ। "
                "ଏବେର ପାଣିପାଗ, ପୂର୍ବାନୁମାନ, କିମ୍ବା ବାୟୁ ଗୁଣତା?"
            ),
            "app_details_header": "ଆପ୍ ବିବରଣୀ:",
            "app_details_tip": "ଟିପ୍: ଏକ ମେସେଜରେ ଅନେକ ଜିନିଷ ପଚାରନ୍ତୁ, ମୁଁ ମିଶାଇଦେବି।",
            "no_details": "ଏବେ କୌଣସି ତଥ୍ୟ ନାହିଁ।",
            "capabilities_line": (
                "- ସମର୍ଥତା: ଏବେର ପାଣିପାଗ, ସ୍ଵଳ୍ପ ପୂର୍ବାନୁମାନ, ବାୟୁ ଗୁଣତା (AQI/PM2.5/PM10), "
                "ୟୁଭି ଇଣ୍ଡେକ୍ସ, ପବନ, ଆର୍ଦ୍ରତା, ଦୃଶ୍ୟମାନତା, ଚାପ, ଏବଂ ଅବସ୍ଥାନ ଲେବେଲ୍।"
            ),
            "location_line": "- ଅବସ୍ଥାନ ସନ୍ଦର୍ଭ: {location}.",
            "dataset_line": "- ଡାଟାସେଟ୍: {rows} ପଙ୍କ୍ତି, ସୀମା {start} ରୁ {end}, କଲମ୍: {columns}.",
            "dataset_missing": "- ଡାଟାସେଟ୍: ଏଯାବତ୍ ଉପଲବ୍ଧ ନୁହେଁ।",
            "model_line": "- ମଡେଲ୍: MAE {mae:.3f} (ଡାଟା ସ୍ରୋତ: {source}).",
            "model_missing": "- ମଡେଲ୍: ମିଟ୍ରିକ୍ସ ଏଯାବତ୍ ଉପଲବ୍ଧ ନୁହେଁ।",
            "dataset_summary_template": "ଡାଟାସେଟ୍ ପଙ୍କ୍ତି: {rows}. ସୀମା {start} ରୁ {end}. କଲମ୍: {columns}.",
            "dataset_summary_missing": "ଡାଟାସେଟ୍ ସାରଂଶ ଏଯାବତ୍ ଉପଲବ୍ଧ ନୁହେଁ।",
            "model_summary_template": "ମଡେଲ୍ MAE: {mae:.3f} (ଡାଟା ସ୍ରୋତ: {source}).",
            "model_summary_missing": "ମଡେଲ୍ ମିଟ୍ରିକ୍ସ ଏଯାବତ୍ ଉପଲବ୍ଧ ନୁହେଁ।",
        },
        "ui": {
            "intro_message": "ନମସ୍କାର! ମୁଁ ସହାୟତା କରିବି। ପାଣିପାଗ ବିଷୟରେ ପଚାରନ୍ତୁ କିମ୍ବା ନମସ୍କାର କହନ୍ତୁ।",
            "vent_label": "କିଛି କହିବାକୁ ଚାହୁଁଲେ କୁହନ୍ତୁ।",
            "choose_conversation": "କଥୋପକଥନ ବାଛନ୍ତୁ",
            "voice_toggle": "ଭଉସ ଆଉଟପୁଟ୍",
            "wake_word_toggle": "ୱେକ୍ ୱର୍ଡ (Hi Siri)",
            "language_label": "ଭାଷା",
            "placeholder": "ସନ୍ଦେଶ ଲେଖନ୍ତୁ...",
            "send_label": "ପଠାନ୍ତୁ",
            "wake_word_trigger": "ନମସ୍କାର",
        },
    },
}


def _deep_clone(value: object) -> object:
    if isinstance(value, dict):
        return {key: _deep_clone(val) for key, val in value.items()}
    if isinstance(value, list):
        return list(value)
    if isinstance(value, set):
        return set(value)
    return value


def _deep_update(base: Dict[str, object], updates: Dict[str, object]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)  # type: ignore[index]
        else:
            base[key] = value


def get_language_pack(language: str) -> Dict[str, object]:
    pack = _deep_clone(BASE_PACK)  # type: ignore[arg-type]
    overrides = LANGUAGE_OVERRIDES.get(language)
    if overrides:
        _deep_update(pack, overrides)
    return pack


def _time_greeting(now: dt.datetime | None = None, language: str = "en") -> str:
    now = now or dt.datetime.now()
    hour = now.hour
    greetings = TIME_GREETINGS.get(language, TIME_GREETINGS["en"])
    if 5 <= hour < 12:
        return greetings["morning"]
    if 12 <= hour < 17:
        return greetings["afternoon"]
    if 17 <= hour < 21:
        return greetings["evening"]
    return greetings["night"]


class WeatherAgent:
    def __init__(
        self,
        tools: Dict[str, Callable[[], str]],
        *,
        intent_predictor: Callable[[str], Tuple[str, float] | None] | None = None,
        min_confidence: float = 0.45,
        language: str = "en",
    ):
        pack = get_language_pack(language)
        self.tools = tools
        self.language = language
        self.intent_predictor = intent_predictor
        self.min_confidence = min_confidence
        self.responses = pack["responses"]
        self.greetings = list(pack["greetings"])
        self.help_words = list(pack["help_words"])
        self.thanks_words = list(pack["thanks_words"])
        self.bye_words = list(pack["bye_words"])
        self.how_are_you = list(pack["how_are_you"])
        self.identity_words = list(pack["identity_words"])
        self.affirm_words = set(pack["affirm_words"])
        self.affirm_phrases = list(pack["affirm_phrases"])
        self.negative_words = set(pack["negative_words"])
        self.app_info_words = list(pack["app_info_words"])
        self.all_details_words = list(pack["all_details_words"])
        self.intent_titles = pack["intent_titles"]
        self.prefixes = pack["prefixes"]
        self.follow_ups = pack["follow_ups"]
        self.strip_prefixes = DEFAULT_STRIP_PREFIXES
        self.all_details_intents = [
            "current_weather",
            "forecast_summary",
            "air_quality",
            "uv_index",
            "wind",
            "humidity",
            "visibility",
            "pressure",
            "location",
            "dataset_summary",
            "model_summary",
        ]
        self.suggested = {
            "current_weather": "forecast_summary",
            "forecast_summary": "current_weather",
            "air_quality": "uv_index",
            "uv_index": "air_quality",
            "wind": "current_weather",
            "humidity": "current_weather",
            "visibility": "current_weather",
            "pressure": "current_weather",
            "location": "current_weather",
            "dataset_summary": "model_summary",
            "model_summary": "dataset_summary",
        }
        self.intents = [
            ("air_quality", ["air quality", "aqi", "pollution", "pm2.5", "pm10"]),
            ("uv_index", ["uv", "ultraviolet"]),
            ("wind", ["wind", "breeze", "gust"]),
            ("humidity", ["humidity", "humid"]),
            ("visibility", ["visibility", "fog", "haze"]),
            ("pressure", ["pressure", "barometer"]),
            ("location", ["where am i", "location", "address", "city", "place"]),
            ("forecast_summary", ["forecast", "tomorrow", "next", "week", "later"]),
            ("current_weather", ["current", "now", "today", "right now", "temperature", "weather"]),
            ("dataset_summary", ["dataset", "data", "history", "archive"]),
            ("model_summary", ["model", "accuracy", "mae", "train"]),
        ]

    def _apply_location_context(self, reply: str, context: AgentContext) -> str:
        if context.location_label:
            if reply.startswith("Current conditions:"):
                reply = reply.replace("Current conditions:", f"Current conditions for {context.location_label}:")
            if reply.startswith("Next 12 hours:"):
                reply = reply.replace("Next 12 hours:", f"Next 12 hours for {context.location_label}:")
        return reply

    def _strip_prefix(self, reply: str, prefixes: Iterable[str]) -> str:
        reply = reply.strip()
        for prefix in prefixes:
            if reply.lower().startswith(prefix.lower()):
                trimmed = reply[len(prefix):].lstrip(" :.-")
                return trimmed if trimmed else reply
        return reply

    def _resolve_intent(self, intent: str, context: AgentContext) -> str:
        if intent in self.tools:
            return self.tools[intent]()
        if intent == "dataset_summary":
            if context.dataset_summary:
                summary = context.dataset_summary
                return self.responses["dataset_summary_template"].format(
                    rows=summary["rows"],
                    start=summary["start"],
                    end=summary["end"],
                    columns=", ".join(summary["columns"]),
                )
            return self.responses["dataset_summary_missing"]
        if intent == "model_summary":
            if context.model_metrics:
                mae = context.model_metrics.get("mae")
                source = context.model_metrics.get("source", "n/a")
                return (
                    self.responses["model_summary_template"].format(mae=mae, source=source)
                    if mae is not None
                    else self.responses["model_summary_missing"]
                )
            return self.responses["model_summary_missing"]
        return "That information isn't available yet."

    def _matched_intents(self, text: str) -> list[str]:
        matches: list[str] = []
        for intent, phrases in self.intents:
            if _contains_any(text, phrases):
                if intent in self.tools or intent in ("dataset_summary", "model_summary"):
                    if intent not in matches:
                        matches.append(intent)
        return matches

    def _multi_intent_reply(self, intents: Iterable[str], context: AgentContext, header: str) -> str:
        lines = []
        for intent in intents:
            reply = self._resolve_intent(intent, context)
            reply = self._apply_location_context(reply, context)
            reply = self._strip_prefix(reply, self.strip_prefixes.get(intent, []))
            title = self.intent_titles.get(intent, intent.replace("_", " ").title())
            lines.append(f"- {title}: {reply}")
        if not lines:
            return self.responses["no_details"]
        return f"{header}\n" + "\n".join(lines)

    def _app_overview(self, context: AgentContext) -> str:
        location = context.location_label or f"{context.latitude:.3f}, {context.longitude:.3f}"
        lines = [
            self.responses["capabilities_line"],
            self.responses["location_line"].format(location=location),
        ]
        if context.dataset_summary:
            summary = context.dataset_summary
            lines.append(
                self.responses["dataset_line"].format(
                    rows=summary["rows"],
                    start=summary["start"],
                    end=summary["end"],
                    columns=", ".join(summary["columns"]),
                )
            )
        else:
            lines.append(self.responses["dataset_missing"])
        if context.model_metrics:
            mae = context.model_metrics.get("mae")
            source = context.model_metrics.get("source", "n/a")
            if mae is not None:
                lines.append(self.responses["model_line"].format(mae=mae, source=source))
            else:
                lines.append(self.responses["model_missing"])
        else:
            lines.append(self.responses["model_missing"])
        lines.append(self.responses["app_details_tip"])
        return f"{self.responses['app_details_header']}\n" + "\n".join(lines)

    def _decorate(self, reply: str, intent: str, context: AgentContext) -> tuple[str, str | None]:
        if reply.lower().startswith("weather api error") or reply.lower().startswith("air quality api error"):
            return reply, None

        reply = self._apply_location_context(reply, context)

        prefix = self.prefixes.get(intent)
        if prefix:
            reply = f"{prefix} {reply}"

        follow_up = self.follow_ups.get(intent)
        suggested = self.suggested.get(intent)
        if follow_up:
            reply = f"{reply} {follow_up}"
            return reply, suggested

        return reply, None

    def respond(self, message: str, context: AgentContext) -> AgentResult:
        text = message.lower().strip()

        if _contains_any(text, self.thanks_words):
            return AgentResult(self.responses["thanks"])

        if _contains_any(text, self.bye_words):
            return AgentResult(self.responses["bye"])

        if _contains_any(text, self.how_are_you):
            greeting = _time_greeting(language=self.language)
            return AgentResult(
                self.responses["how_are_you"].format(greeting=greeting),
                None,
                "current_weather",
            )

        if _contains_any(text, self.identity_words):
            return AgentResult(self.responses["identity"], None, "current_weather")

        if (
            _contains_word(text, self.affirm_words)
            or _contains_any(text, self.affirm_phrases)
        ) and context.last_suggested_intent in self.tools:
            intent = context.last_suggested_intent
            reply = self.tools[intent]()
            decorated, suggested = self._decorate(reply, intent, context)
            return AgentResult(decorated, intent, suggested)

        if _contains_word(text, self.negative_words) and context.last_suggested_intent:
            return AgentResult(self.responses["negative"])

        if _contains_any(text, self.greetings):
            location_hint = f" around {context.location_label}" if context.location_label else ""
            greeting = _time_greeting(language=self.language)
            return AgentResult(
                f"{greeting}! I can help with weather{location_hint}. Want current conditions or the forecast?",
                None,
                "current_weather",
            )

        if _contains_any(text, self.help_words):
            return AgentResult(self.responses["help"], None, "current_weather")

        if _contains_any(text, self.all_details_words):
            intents = [
                intent
                for intent in self.all_details_intents
                if intent in self.tools or intent in ("dataset_summary", "model_summary")
            ]
            reply = self._multi_intent_reply(intents, context, self.responses["all_details_header"])
            return AgentResult(reply)

        if _contains_any(text, self.app_info_words):
            return AgentResult(self._app_overview(context))

        matched_intents = self._matched_intents(text)
        if matched_intents:
            if len(matched_intents) > 1:
                reply = self._multi_intent_reply(matched_intents, context, self.responses["combined_header"])
                return AgentResult(reply)
            intent = matched_intents[0]
            reply = self._resolve_intent(intent, context)
            decorated, suggested = self._decorate(reply, intent, context)
            return AgentResult(decorated, intent, suggested)

        if self.intent_predictor:
            predicted = self.intent_predictor(message)
            if predicted:
                intent, confidence = predicted
                if confidence >= self.min_confidence:
                    if intent == "app_info":
                        return AgentResult(self._app_overview(context))
                    if intent == "all_details":
                        intents = [
                            intent
                            for intent in self.all_details_intents
                            if intent in self.tools or intent in ("dataset_summary", "model_summary")
                        ]
                        reply = self._multi_intent_reply(intents, context, self.responses["all_details_header"])
                        return AgentResult(reply)
                    if intent in self.tools or intent in ("dataset_summary", "model_summary"):
                        reply = self._resolve_intent(intent, context)
                        decorated, suggested = self._decorate(reply, intent, context)
                        return AgentResult(decorated, intent, suggested)

        return AgentResult(self.responses["starter"], None, "current_weather")

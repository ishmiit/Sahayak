/* Sahayak phone app. Talks only to the node it was served from (CSP enforces this).
   All message and model text is inserted with textContent, never as HTML. */
(() => {
  "use strict";

  const T = {
    hi: {
      node_pill: "बिना इंटरनेट", node_pill_phone: "फ़ोन पर · बिना इंटरनेट",
      foot_phone: "सहायक इसी फ़ोन पर चल रहा है। आप जो लिखते हैं, वह फ़ोन से बाहर नहीं जाता।",
      phone_mode_note: "अभी नोड से नहीं जुड़े: जाँच इसी फ़ोन पर होती है और कुछ भी बाहर नहीं जाता। बोलकर पूछने और एजेंट से मदद के लिए CSC के Wi-Fi पर आएँ।",
      checked_phone: "इस फ़ोन पर जाँच", pack_old: "जाँच के नियम {days} दिन पुराने हैं; CSC पर फ़ोन अपडेट कराएँ", qr_no_detector: "यह फ़ोन नोड के बिना QR नहीं पढ़ सकता। CSC पर आकर जाँचें, या QR के साथ आया मैसेज लिखकर जाँचें।",
      home_title: "नमस्ते! मैं सहायक हूँ।",
      home_sub: "मेरी मदद से आप मैसेज में ठगी की जाँच कर सकते हैं और जान सकते हैं कि आपका हक क्या है, बिना इंटरनेट के।",
      tile_check: "मैसेज जाँचें", tile_check_sub: "क्या यह ठगी है?",
      tile_benefits: "मेरा हक क्या है?", tile_benefits_sub: "पेंशन, बीमा, योजनाएँ",
      tile_help: "मदद अभी: 1930", tile_help_sub: "पैसे गए? तुरंत कॉल करें",
      check_title: "मैसेज जाँचें", check_label: "मैसेज यहाँ चिपकाएँ या लिखें",
      sender_add: "भेजने वाले का नाम या नंबर जोड़ें", sender_label: "भेजने वाला या कॉल करने वाला",
      itype_sms: "SMS / मैसेज", itype_call: "फ़ोन कॉल",
      check_btn: "जाँचें", checking: "जाँच हो रही है…", try_examples: "या एक उदाहरण आज़माएँ:",
      in_simple_words: "आसान शब्दों में", explaining: "सहायक समझा रहा है…",
      why: "क्यों?", what_to_do: "अब क्या करें?",
      call_1930: "पैसे गए? 1930 पर कॉल करें", speak_btn: "सुनें", complaint_btn: "शिकायत का ड्राफ़्ट", check_another: "दूसरा मैसेज जाँचें",
      safety_ok: "यह जवाब कैसे जाँचा गया", safety_checks: "ये जाँचें हुईं:",
      complaint_title: "1930 शिकायत का ड्राफ़्ट",
      complaint_note: "यह ड्राफ़्ट इसी फ़ोन पर रहता है। 1930 पर कॉल करते समय या cybercrime.gov.in पर शिकायत करते समय इसका इस्तेमाल करें।",
      c_when: "कब हुआ", c_channel: "कैसे आया (SMS, कॉल, WhatsApp)", c_number: "ठग का नंबर", c_upi: "UPI ID (अगर हो)",
      c_link: "लिंक (अगर हो)", c_lost: "कितने पैसे गए (₹)", c_txn: "ट्रांज़ैक्शन ID (अगर हो)", c_message: "मैसेज",
      print_btn: "प्रिंट करें", back: "वापस",
      foot: "सहायक इसी नोड पर चलता है। आप जो लिखते हैं, वह इंटरनेट पर नहीं जाता।",
      err_empty: "पहले मैसेज चिपकाएँ या लिखें।", err_network: "नोड से नहीं जुड़ पाए। Wi-Fi जाँचें।",
      no_voice: "इस फ़ोन में आवाज़ नहीं मिली।",
      checked_in: "इस नोड पर जाँच", ms: "मि.से.", pack: "पैक", model_text: "मॉडल", template_text: "जाँचे-परखे वाक्य",
      channel_sms: "SMS", channel_call: "फ़ोन कॉल",
      real_benefits: "असली योजनाएँ यहाँ सुरक्षित जाँचें: मेरा हक क्या है?",
      mode_text: "मैसेज", mode_call: "फ़ोन कॉल", mode_qr: "QR कोड", mode_ocr: "स्क्रीनशॉट",
      call_label: "कॉल पर क्या कहा गया? बोलकर या लिखकर बताएँ",
      qr_label: "जिस QR को स्कैन करने को कहा गया, उसकी फ़ोटो लें", qr_btn: "QR की फ़ोटो लें या चुनें",
      qr_reading: "QR पढ़ रहा हूँ…", qr_none: "फ़ोटो में QR नहीं मिला। पास से, सीधी फ़ोटो लें।", qr_try: "उदाहरण QR:",
      qr_pays: "पैसे किसको जाएँगे", qr_upi: "UPI ID", qr_amount: "रकम",
      ocr_label: "मैसेज का स्क्रीनशॉट या फ़ोटो चुनें", ocr_btn: "स्क्रीनशॉट चुनें",
      ocr_reading: "स्क्रीनशॉट पढ़ रहा हूँ… (कुछ सेकंड)", ocr_none: "स्क्रीनशॉट में कुछ लिखा हुआ नहीं मिला।", ocr_off: "इस नोड पर स्क्रीनशॉट पढ़ना चालू नहीं है। मैसेज लिखकर या बोलकर जाँचें।",
      ocr_review: "स्क्रीनशॉट से यह पढ़ा गया। गलती हो तो ठीक करें, फिर जाँचें।",
      ask_agent: "एजेंट से पूछें (काउंटर पर)", ticket_title: "आपका नंबर", ticket_sub: "काउंटर पर एजेंट आपका नंबर बुलाएँगे। तब तक यह स्क्रीन खुली रखें।",
      ticket_ok: "ठीक है", agent_offline: "अभी कोई एजेंट नहीं जुड़ा। काउंटर पर जाकर पूछें।",
      voice_settings: "आवाज़ और अक्षर", voice_female: "महिला आवाज़", voice_male: "पुरुष आवाज़",
      speed_normal: "सामान्य गति", speed_slow: "धीमी गति", sound_on: "स्क्रीन पढ़कर सुनाना चालू", sound_off: "स्क्रीन पढ़कर सुनाना बंद",
      voice_ready: "आवाज़ इसी नोड पर चलती है: सुनना और बोलना, बिना इंटरनेट।",
      voice_phone: "नोड की आवाज़ नहीं मिली; फ़ोन की अपनी आवाज़ इस्तेमाल हो रही है।",
      mic_dictate: "बोलकर लिखें (दबाकर रखें)", mic_answer: "बोलकर जवाब दें (दबाकर रखें)",
      mic_dictate_upload: "फ़ोन के रिकॉर्डर से बोलकर लिखें", mic_answer_upload: "फ़ोन के रिकॉर्डर से बोलकर जवाब दें",
      mic_listening: "सुन रहा हूँ… बोलकर छोड़ें", mic_thinking: "समझ रहा हूँ…",
      mic_short: "बटन दबाकर रखें, बोलें, फिर छोड़ें।", mic_none: "कुछ सुनाई नहीं दिया। फिर से बोलें।",
      mic_secure: "यहाँ बोलने के लिए फ़ोन का रिकॉर्डर खुलेगा; दबाकर बोलने के लिए नोड का सुरक्षित (https) पता खोलें।", mic_denied: "माइक की अनुमति नहीं मिली।",
      heard: "मैंने सुना", heard_as: "जवाब", is_right: "क्या यह सही है?", yes_right: "हाँ, सही है", say_again: "नहीं, फिर से",
      not_understood: "समझ नहीं आया। फिर से बोलें, या नीचे से चुनें।", check_low_conf: "देख लें कि मैसेज ठीक लिखा गया है।",
      years_word: "साल",
      nav_intro: "कुछ छोटे सवालों के जवाब दें। फिर पता चलेगा कि 12 सरकारी योजनाओं में से आपको क्या मिल सकता है, कहाँ जाना है और कौन-से कागज़ ले जाने हैं।",
      nav_promise_1: "ज़्यादा से ज़्यादा 8 सवाल",
      nav_promise_2: "आपका नाम नहीं पूछा जाएगा",
      nav_promise_3: "जवाब इंटरनेट पर नहीं जाते, नोड कुछ सेव नहीं करता",
      nav_start: "शुरू करें", nav_try: "या एक उदाहरण देखें:", nav_covers: "योजनाएँ:",
      q_count: "सवाल {n} · ज़्यादा से ज़्यादा {max}", next: "आगे",
      age_label: "उम्र (साल)", age_unsure: "ठीक उम्र नहीं पता? यहाँ से चुनें:", age_err: "0 से 120 के बीच उम्र लिखें।",
      g_eligible: "आपको मिल सकता है", g_likely: "शायद मिल सकता है — सबूत साथ ले जाएँ", g_check: "दफ़्तर में पूछें",
      g_unlock: "बैंक खाता खुलने के बाद", g_have: "पहले से मिल रहा है", g_not_eligible: "आपके लिए नहीं",
      st_eligible: "मिल सकता है", st_likely: "शायद — सबूत लगेगा", st_check: "पूछें", st_unlock: "खाता खुलने के बाद",
      st_have: "पहले से मिल रहा है", st_not_eligible: "नहीं",
      nav_summary: "{total} योजनाओं में से {n} आपके काम की", nav_summary_none: "इन योजनाओं में से अभी कोई आप पर लागू नहीं दिखती।",
      details: "कागज़, जगह और कारण", why_label: "क्यों", benefit_label: "क्या मिलता है", docs_label: "कौन-से कागज़ ले जाएँ",
      where_label: "कहाँ जाएँ", say_label: "काउंटर पर ऐसे कहें", how_label: "कैसे पता करें", source_label: "स्रोत", checked_label: "जाँचा",
      have_label: "मुझे यह पहले से मिल रहा है",
      health_title: "पहले सेहत: मुफ़्त इलाज", nav_slip: "पर्ची बनाएँ (CSC के लिए)", nav_change: "पिछला जवाब बदलें", nav_restart: "फिर से शुरू करें",
      questions_asked: "सवाल",
      slip_title: "सहायक — योजना पर्ची", slip_answers: "जवाब", slip_schemes: "योजनाएँ", slip_date: "तारीख",
      slip_no_name: "नाम नहीं रखा गया", slip_qr: "QR कोड, जिसमें ये जवाब हैं",
      slip_operator: "CSC ऑपरेटर: QR में यही जवाब हैं, दोबारा पूछने की ज़रूरत नहीं।",
      trust_offline: "इंटरनेट नहीं चाहिए", trust_private: "आपका नाम नहीं पूछता", trust_voice: "पढ़कर सुनाता है",
      install_title: "सहायक को होम स्क्रीन पर रखें", install_sub: "एक बार रखें, फिर बिना इंटरनेट भी खुलेगा",
      text_size: "अक्षरों का आकार", size_normal: "सामान्य", size_large: "बड़ा", size_xl: "सबसे बड़ा",
      voice_label: "आवाज़", speed_label: "बोलने की गति",
      paste_check: "मैसेज चिपकाकर जाँचें",
      paste_empty: "कॉपी किया हुआ कोई मैसेज नहीं मिला। SMS में मैसेज को दबाकर रखें और कॉपी करें।",
      paste_denied: "चिपकाने की अनुमति नहीं मिली। नीचे के बॉक्स को दबाकर रखें और चिपकाएँ (Paste) चुनें।",
      checked_msg: "जाँचा गया मैसेज", share_btn: "परिवार को सावधान करें", share_intro: "सहायक ने एक मैसेज जाँचा",
      share_try: "आप भी जाँचें, बिना इंटरनेट:",
      docs_all_title: "CSC पर ये कागज़ साथ ले जाएँ", docs_all_sub: "ऊपर की सभी योजनाओं के लिए एक सूची",
      docs_for_n: "{n} योजनाओं के लिए", docs_for_one: "{name} के लिए",
      lang_title: "अपनी भाषा चुनें", lang_close: "बंद करें",
      lang_note: "यह भाषा मशीन से अनुवाद की गई है; किसी मूल वक्ता ने अभी इसे जाँचा नहीं है।",
      lang_detect: "सहायक हिंदी, अंग्रेज़ी और हिंग्लिश में लिखे मैसेज पढ़ता है। किसी और भाषा के मैसेज पर “जाँच नहीं हो सकी” आता है।",
      lang_mic_off: "सहायक से बोलकर बात सिर्फ़ हिंदी और अंग्रेज़ी में होती है। कृपया लिखें या चिपकाएँ।",

      tab_home: "होम", tab_check: "जाँच", tab_benefits: "मेरा हक", tab_learn: "सीखें",
      tile_learn: "ठगी पहचानो", tile_learn_sub: "छोटा खेल: ठगी है या असली?", game_new: "नया",
      learn_sub: "हर राउंड में 5 मैसेज और कॉल आते हैं। आप तय करें: ठगी या असली? फिर देखें कि सहायक को कौन-से सुराग मिले। सही जवाब पर अंक और बैज मिलते हैं।",
      play_round: "एक राउंड खेलें", level_label: "स्तर", points: "अंक",
      next_level: "{name} तक पहुँचने के लिए {n} अंक और", top_level: "आप सबसे ऊँचे स्तर पर हैं। नज़र ऐसे ही तेज़ रखें!",
      streak_days: "लगातार {n} दिन", badges_count: "{total} में से {n} बैज",
      daily_title: "आज का मैसेज", daily_sub: "हर दिन एक नया मैसेज। +20 बोनस अंक।", daily_play: "खेलें",
      daily_done: "आज का हो गया। कल नया मैसेज आएगा।",
      badges_title: "बैज", badge_progress: "{total} में से {n}", badge_won: "मिल गया",
      badge_otp: "OTP रक्षक", badge_otp_d: "OTP माँगना और नकली कस्टमर केयर",
      badge_upi: "QR जानकार", badge_upi_d: "पैसे देने का वादा करने वाले QR कोड",
      badge_kyc: "धमकी पकड़ने वाले", badge_kyc_d: "KYC, खाता बंद और बिजली कटने की धमकी",
      badge_arrest: "नकली पुलिस पकड़ने वाले", badge_arrest_d: "नकली पुलिस, CBI और मुसीबत में फँसे रिश्तेदार",
      badge_prize: "इनाम पर शक करने वाले", badge_prize_d: "लॉटरी, इनाम और पार्सल की चालें",
      badge_money: "आसान कमाई से सावधान", badge_money_d: "नौकरी, लोन और जल्दी अमीर बनने के ऑफ़र",
      badge_scheme: "योजना साथी", badge_scheme_d: "नकली योजना, फ़ीस और योजना के ऐप",
      badge_real: "असली पहचानने वाले", badge_real_d: "असली मैसेज को असली पहचानना",
      lvl_1: "सीखने वाले", lvl_2: "सतर्क", lvl_3: "तेज़ नज़र", lvl_4: "ठगी का कवच", lvl_5: "ठगी पहचान गुरु",
      play_question: "ठगी या असली?", ans_scam: "ठगी", ans_real: "असली",
      swipe_hint: "अपना जवाब दबाएँ, या कार्ड को उसकी ओर सरकाएँ।",
      card_sms: "मैसेज", card_call: "फ़ोन कॉल: कॉल करने वाले ने क्या कहा", card_n: "{total} में से {n}",
      fb_right: "सही!", fb_wrong: "इस बार नहीं", fb_real: "यह असली मैसेज है।", fb_clues: "सुराग", fb_remember: "याद रखें",
      fb_real_tip: "असली बैंक या सरकारी मैसेज आपको जानकारी या कोड देता है। वह कभी OTP या PIN बताने, या किसी व्यक्ति को पैसे भेजने को नहीं कहता।",
      combo: "लगातार {n} सही!", see_score: "मेरा स्कोर देखें",
      done_perfect: "शानदार! आपने हर एक को पहचान लिया।", done_good: "तेज़ नज़र!", done_ok: "अच्छी शुरुआत। हर राउंड में एक नई चाल सीखेंगे।",
      done_score: "{total} में से {n} सही", done_points: "+{n} अंक", new_badge: "नया बैज!",
      play_again: "फिर खेलें", share_game: "परिवार को चुनौती दें", done_btn: "हो गया",
      share_game_text: "मैंने सहायक पर {total} में से {n} मैसेज सही पहचाने: ठगी या असली। क्या आप मुझसे ज़्यादा पहचान सकते हैं?",
      game_private: "आपका स्कोर इसी फ़ोन पर रहता है। कुछ भी कहीं नहीं भेजा जाता।",
      level_up: "नया स्तर: {name}!", next_card: "अगला",
      appearance: "रंग-रूप", theme_auto: "अपने-आप", theme_light: "हल्का", theme_titanium: "सफ़ेद टाइटेनियम", theme_dark: "गहरा",
    },
    en: {
      node_pill: "Offline", node_pill_phone: "On phone · offline",
      foot_phone: "Sahayak is running on this phone. Nothing you type leaves it.",
      phone_mode_note: "Not connected to the node: checks run on this phone and nothing leaves it. For voice and help from the agent, come to the CSC's Wi-Fi.",
      checked_phone: "Checked on this phone in", pack_old: "scam patterns are {days} days old; update this phone at the CSC", qr_no_detector: "This phone cannot read QR codes without the node. Check it at the CSC, or type the message that came with the QR.",
      home_title: "Namaste! I am Sahayak.",
      home_sub: "I can check a message for fraud and tell you what you are owed, without internet.",
      tile_check: "Check a message", tile_check_sub: "Is it a scam?",
      tile_benefits: "What am I owed?", tile_benefits_sub: "Pensions, insurance, schemes",
      tile_help: "Help now: 1930", tile_help_sub: "Lost money? Call right away",
      check_title: "Check a message", check_label: "Paste or type the message here",
      sender_add: "Add the sender's name or number", sender_label: "Sender or caller",
      itype_sms: "SMS / message", itype_call: "Phone call",
      check_btn: "Check", checking: "Checking…", try_examples: "Or try an example:",
      in_simple_words: "In simple words", explaining: "Sahayak is explaining…",
      why: "Why?", what_to_do: "What to do now",
      call_1930: "Lost money? Call 1930", speak_btn: "Listen", complaint_btn: "Complaint draft", check_another: "Check another",
      safety_ok: "How this answer was checked", safety_checks: "Checks that ran:",
      complaint_title: "1930 complaint draft",
      complaint_note: "This draft stays on this device. Use it when you call 1930 or file at cybercrime.gov.in.",
      c_when: "When did it happen", c_channel: "How it came (SMS, call, WhatsApp)", c_number: "Fraudster's number",
      c_upi: "UPI ID (if any)", c_link: "Link (if any)", c_lost: "Money lost (₹)", c_txn: "Transaction ID (if any)", c_message: "Message",
      print_btn: "Print", back: "Back",
      foot: "Sahayak runs on this node. Nothing you type goes to the internet.",
      err_empty: "Paste or type a message first.", err_network: "Could not reach the node. Check the Wi-Fi.",
      no_voice: "No voice found on this phone.",
      checked_in: "Checked on this node in", ms: "ms", pack: "pack", model_text: "model", template_text: "vetted sentences",
      channel_sms: "SMS", channel_call: "Phone call",
      real_benefits: "Check the real schemes safely here: What am I owed?",
      mode_text: "Message", mode_call: "Phone call", mode_qr: "QR code", mode_ocr: "Screenshot",
      call_label: "What did the caller say? Speak or type it",
      qr_label: "Take a photo of the QR you were asked to scan", qr_btn: "Take or choose a photo of the QR",
      qr_reading: "Reading the QR…", qr_none: "No QR code found. Take a closer, straight photo.", qr_try: "Example QR codes:",
      qr_pays: "Money goes to", qr_upi: "UPI ID", qr_amount: "Amount",
      ocr_label: "Choose a screenshot or photo of the message", ocr_btn: "Choose a screenshot",
      ocr_reading: "Reading the screenshot… (a few seconds)", ocr_none: "No text found in the screenshot.", ocr_off: "Screenshot reading is not set up on this node. Type or say the message instead.",
      ocr_review: "This is what I read from the screenshot. Fix any mistakes, then check.",
      ask_agent: "Ask the agent (at the counter)", ticket_title: "Your number", ticket_sub: "The agent at the counter will call your number. Keep this screen open until then.",
      ticket_ok: "OK", agent_offline: "No agent is connected right now. Please ask at the counter.",
      voice_settings: "Voice and text size", voice_female: "Female voice", voice_male: "Male voice",
      speed_normal: "Normal speed", speed_slow: "Slower", sound_on: "Reading screens aloud: on", sound_off: "Reading screens aloud: off",
      voice_ready: "Voice runs on this node: listening and speaking, without internet.",
      voice_phone: "No voice on the node; using the phone's own voice.",
      mic_dictate: "Speak the message (hold)", mic_answer: "Answer by speaking (hold)",
      mic_dictate_upload: "Speak the message with the phone's recorder", mic_answer_upload: "Answer with the phone's recorder",
      mic_listening: "Listening… let go when done", mic_thinking: "Working it out…",
      mic_short: "Hold the button, speak, then let go.", mic_none: "I didn't catch anything. Please try again.",
      mic_secure: "Here, speaking opens the phone's recorder; for hold-to-talk, open the node's secure (https) address.", mic_denied: "Microphone permission was not given.",
      heard: "I heard", heard_as: "Answer", is_right: "Is that right?", yes_right: "Yes, that's right", say_again: "No, again",
      not_understood: "I could not match that. Say it again, or pick below.", check_low_conf: "Check that the message was written down correctly.",
      years_word: "years",
      nav_intro: "Answer a few short questions and I will tell you which of 12 government schemes you can get, where to go and which papers to take.",
      nav_promise_1: "At most 8 questions",
      nav_promise_2: "I will not ask your name",
      nav_promise_3: "Answers never go to the internet; the node saves nothing",
      nav_start: "Start", nav_try: "Or see an example:", nav_covers: "Schemes:",
      q_count: "Question {n} · at most {max}", next: "Next",
      age_label: "Age (years)", age_unsure: "Not sure of your exact age? Pick a range:", age_err: "Enter an age between 0 and 120.",
      g_eligible: "You can get", g_likely: "Likely — take proof", g_check: "Ask at the office",
      g_unlock: "After you open a bank account", g_have: "Already getting", g_not_eligible: "Not for you",
      st_eligible: "You can get", st_likely: "Likely — needs proof", st_check: "Ask", st_unlock: "After an account",
      st_have: "Already getting", st_not_eligible: "No",
      nav_summary: "{n} of {total} schemes are worth a visit", nav_summary_none: "None of these schemes seems to apply right now.",
      details: "Papers, place and reasons", why_label: "Why", benefit_label: "What you get", docs_label: "Papers to take",
      where_label: "Where to go", say_label: "Say this at the counter", how_label: "How to check", source_label: "Source", checked_label: "checked",
      have_label: "I already get this",
      health_title: "Health first: free treatment", nav_slip: "Make a slip (for the CSC)", nav_change: "Change last answer", nav_restart: "Start again",
      questions_asked: "questions",
      slip_title: "Sahayak scheme slip", slip_answers: "Answers", slip_schemes: "Schemes", slip_date: "Date",
      slip_no_name: "No name kept", slip_qr: "QR code holding these answers",
      slip_operator: "CSC operator: the QR holds these answers, so there is no need to ask again.",
      trust_offline: "No internet needed", trust_private: "Never asks your name", trust_voice: "Reads it out loud",
      install_title: "Keep Sahayak on your home screen", install_sub: "Add it once; it opens without internet too",
      text_size: "Text size", size_normal: "Normal", size_large: "Large", size_xl: "Largest",
      voice_label: "Voice", speed_label: "Speaking speed",
      paste_check: "Paste and check",
      paste_empty: "Nothing is copied yet. In your SMS app, press and hold the message, then tap Copy.",
      paste_denied: "Paste was not allowed. Press and hold the box below, then choose Paste.",
      checked_msg: "The message checked", share_btn: "Warn your family", share_intro: "Sahayak checked a message",
      share_try: "Check yours too, no internet needed:",
      docs_all_title: "Take these papers to the CSC", docs_all_sub: "One list for every scheme above",
      docs_for_n: "for {n} schemes", docs_for_one: "for {name}",
      lang_title: "Choose your language", lang_close: "Close",
      lang_note: "This language is a machine translation, not yet checked by a native speaker.",
      lang_detect: "Sahayak reads messages in Hindi, English and Hinglish. A message in another language gets “Could not check”.",
      lang_mic_off: "Speaking to Sahayak works in Hindi and English only. Please type or paste.",

      tab_home: "Home", tab_check: "Check", tab_benefits: "Benefits", tab_learn: "Learn",
      tile_learn: "Spot the scam", tile_learn_sub: "A quick game: is it a scam or real?", game_new: "New",
      learn_sub: "Each round shows 5 messages and calls. Decide: scam or real? Then see the clues Sahayak found. Right answers earn points and badges.",
      play_round: "Play a round", level_label: "Level", points: "points",
      next_level: "{n} more points to {name}", top_level: "You are at the top level. Keep your eyes sharp!",
      streak_days: "{n}-day streak", badges_count: "{n} of {total} badges",
      daily_title: "Today's message", daily_sub: "One new message every day. +20 bonus points.", daily_play: "Play",
      daily_done: "Done for today. A new one comes tomorrow.",
      badges_title: "Badges", badge_progress: "{n} of {total}", badge_won: "Earned",
      badge_otp: "OTP Guardian", badge_otp_d: "OTP asks and fake customer care",
      badge_upi: "QR Expert", badge_upi_d: "QR codes that promise money",
      badge_kyc: "Threat Buster", badge_kyc_d: "KYC, account-block and power-cut threats",
      badge_arrest: "Fake Police Buster", badge_arrest_d: "Fake police, CBI and relatives in trouble",
      badge_prize: "Prize Skeptic", badge_prize_d: "Lotteries, prizes and parcel tricks",
      badge_money: "Easy-Money Alarm", badge_money_d: "Jobs, loans and get-rich offers",
      badge_scheme: "Scheme Saathi", badge_scheme_d: "Fake schemes, fees and scheme apps",
      badge_real: "Real-Deal Detective", badge_real_d: "Knowing a real message when you see one",
      lvl_1: "Learner", lvl_2: "Alert", lvl_3: "Sharp Eyes", lvl_4: "Scam Shield", lvl_5: "Scam Guru",
      play_question: "Scam or real?", ans_scam: "Scam", ans_real: "Real",
      swipe_hint: "Tap your answer, or swipe the card towards it.",
      card_sms: "Message", card_call: "Phone call: what the caller said", card_n: "{n} of {total}",
      fb_right: "Right!", fb_wrong: "Not this time", fb_real: "This one is a real message.", fb_clues: "The clues", fb_remember: "Remember",
      fb_real_tip: "A real bank or government message gives you information or a code. It never asks you to share an OTP or PIN, or to send money to a person.",
      combo: "{n} in a row!", see_score: "See my score",
      done_perfect: "Perfect! You caught every one.", done_good: "Sharp eyes!", done_ok: "Good start. Every round teaches a new trick.",
      done_score: "{n} of {total} right", done_points: "+{n} points", new_badge: "New badge!",
      play_again: "Play again", share_game: "Challenge your family", done_btn: "Done",
      share_game_text: "I spotted {n} of {total} messages right on Sahayak: scam or real. Can you beat my score?",
      game_private: "Your score stays on this phone. Nothing is sent anywhere.",
      level_up: "Level up: {name}!", next_card: "Next",
      appearance: "Appearance", theme_auto: "Automatic", theme_light: "Light", theme_titanium: "White Titanium", theme_dark: "Dark",
    },
  };
  // The language list's own note, in Hindi or English only (it describes every other language on the list).
  const SHEET_NOTE = {
    hi: "हर स्क्रीन और हर जवाब आपकी भाषा में। चुनी हुई भाषा इसी फ़ोन पर रहती है।",
    en: "Every screen and every answer in your language. Your choice stays on this phone.",
  };

  // Verdict glyphs (Material Symbols names, drawn by web/fonts/symbols.woff2).
  const ICONS = { scam: "gpp_bad", suspicious: "warning", no_signs: "verified_user", unreadable: "help" };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const state = { lang: loadLang(), check: null, message: "", explanation: null, health: null, nodeless: false };

  function loadLang() {
    try { return localStorage.getItem("sahayak.lang") || "en"; } catch { return "en"; }  // English until the person picks
  }
  function saveLang(lang) {
    try { localStorage.setItem("sahayak.lang", lang); } catch { /* private mode */ }
  }
  // ---------------------------------------------------------------- languages
  // Hindi and English are the engines' own languages. Every other language is a display layer: the engines
  // answer in Hindi and English exactly as before, and web/i18n.js puts their English into the chosen language
  // from web/i18n/<code>.json (scripts/i18n_build.py). Calls to the node always carry hi or en (base()).
  const BUILTIN = [
    { code: "hi", name: "हिंदी", english: "Hindi", dir: "ltr", base: "hi" },
    { code: "en", name: "English", english: "English", dir: "ltr", base: "en" },
  ];
  const langs = { index: null, packs: {}, tr: {} };
  const isBuiltin = (code) => code === "hi" || code === "en";
  const metaOf = (code) => langs.packs[code] || BUILTIN.find((b) => b.code === code)
    || (langs.index || []).find((x) => x.code === code) || null;
  // The language the engines answer in for this display language, and the one shown on the line under each answer.
  const base = (code = state.lang) => (isBuiltin(code) ? code : ((metaOf(code) || {}).base === "hi" ? "hi" : "en"));
  const second = (code = state.lang) => (code === "hi" ? "en" : code === "en" ? "hi" : base(code));
  const other = second;
  const DANDA = new Set(["hi", "mr", "ne", "mai", "doi", "brx", "sa", "kok", "bn", "as", "mni", "or", "pa"]);
  const stopFor = (code = state.lang) => (DANDA.has(code) ? "।" : ["ur", "ks", "sd"].includes(code) ? "۔" : code === "sat" ? "᱾" : ".");
  const t = (key) => (isBuiltin(state.lang) ? T[state.lang][key] : ((langs.packs[state.lang] || {}).ui || {})[key])
    ?? T[base()][key] ?? T.en[key] ?? key;

  // An English string from an engine, in the display language (null: no translation, show the base language).
  function trEn(en) {
    const tx = langs.tr[state.lang];
    if (!tx || typeof en !== "string") return null;
    let hit = tx.lookup(en);
    if (hit === null && en.includes("; ")) {  // a benefits answer that names several choices
      const parts = en.split("; ").map((p) => tx.lookup(p));
      if (parts.every((p) => p !== null)) hit = parts.join("; ");
    }
    return hit === null ? null : isolateLatin(hit);
  }
  // In a right-to-left language, a link, code or name in Latin letters keeps its own order when the line wraps.
  function isolateLatin(text) {
    if ((metaOf(state.lang) || {}).dir !== "rtl") return text;
    return text.replace(/[A-Za-z0-9][A-Za-z0-9.\-/@:_]*[A-Za-z0-9]/g, (run) => `\u2066${run.replace(/-/g, "-\u2060")}\u2069`);
  }
  // The actions of a verdict card, { en: [...], hi: [...] }, as one list in the display language.
  function trList(lists) {
    if (!lists) return [];
    if (isBuiltin(state.lang)) return lists[state.lang] || [];
    return (lists.en || []).map((a, i) => trEn(a) ?? (lists[base()] || [])[i] ?? a);
  }

  async function loadLangPack(code) {
    if (isBuiltin(code) || langs.packs[code]) return;
    if (!/^[a-z]{2,3}$/.test(code) || !window.SahayakI18n) throw new Error(`no language ${code}`);
    const res = await fetch(`${ROOT}app/i18n/${code}.json`);
    if (!res.ok) throw new Error(`language ${code}: HTTP ${res.status}`);
    const pack = await res.json();
    langs.tr[code] = window.SahayakI18n.create(pack);
    langs.packs[code] = pack;
  }

  async function loadLangIndex() {
    if (langs.index) return langs.index;
    try {
      const res = await fetch(`${ROOT}app/i18n/index.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      langs.index = await res.json();
      return langs.index;
    } catch {
      return BUILTIN;  // offline before the list was ever fetched: Hindi and English still work
    }
  }

  async function setLanguage(code) {
    try { await loadLangPack(code); } catch { toast(t("err_network")); return false; }
    state.lang = code;
    saveLang(code);
    applyI18n();
    return true;
  }

  // The top-bar button shows the current language: its first letter (two for Perso-Arabic script), EN for English.
  function shortLabel(code) {
    if (code === "en") return "EN";
    const m = metaOf(code);
    const name = m ? m.name : code;
    try {
      if (window.Intl && Intl.Segmenter) {
        const parts = [...new Intl.Segmenter(code, { granularity: "grapheme" }).segment(name)].map((s) => s.segment);
        return (m && m.dir === "rtl" ? parts.slice(0, 2) : parts.slice(0, 1)).join("");
      }
    } catch { /* fall through */ }
    return name.slice(0, 2);
  }

  async function openLangSheet() {
    const list = await loadLangIndex();
    const sheet = $("#lang-sheet");
    $("#lang-sheet-note").textContent = SHEET_NOTE[base()];
    $("#lang-list").replaceChildren(...list.map((l) => el("button", {
      type: "button", class: "lang-opt", lang: l.code, dir: l.dir === "rtl" ? "rtl" : "ltr",
      "aria-current": l.code === state.lang ? "true" : null,
      onclick: async () => { if (await setLanguage(l.code)) closeLangSheet(); },
    }, el("b", {}, l.name), el("small", { lang: "en", dir: "ltr" }, l.english))));
    openSheet(sheet);
    const current = $('.lang-opt[aria-current="true"]', sheet) || $(".lang-opt", sheet);
    if (current) current.focus();
  }
  function closeLangSheet() {
    closeSheet($("#lang-sheet"), () => $("#lang-toggle").focus());
  }
  // A sheet slides away (and its dimming fades) before it is hidden.
  function closeSheet(sheet, then) {
    if (sheet.hidden || sheet.classList.contains("closing")) return;
    const token = {};
    sheet.closeToken = token;
    const done = () => {
      if (sheet.closeToken !== token) return;  // opened again while it was sliding away, or already closed
      sheet.closeToken = null;
      sheet.hidden = true;
      sheet.classList.remove("closing");
      sheet.style.transform = "";
      if (then) then();
    };
    if (reduceMotion()) { done(); return; }
    sheet.classList.add("closing");
    sheet.addEventListener("animationend", (e) => { if (e.target === sheet) done(); }, { once: true });
    setTimeout(done, 450);  // in case the animation never reports its end
  }
  function openSheet(sheet) {
    sheet.closeToken = null;
    sheet.classList.remove("closing");
    sheet.style.transform = "";
    sheet.hidden = false;
  }
  // Drag a sheet down by its top to close it, as on an iPhone.
  function dragToClose(sheet, close) {
    let start = null;
    sheet.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".lang-list, button, a, input")) return;
      start = { y: e.clientY, id: e.pointerId, dy: 0 };
      sheet.setPointerCapture(e.pointerId);
      sheet.classList.add("dragging");
    });
    sheet.addEventListener("pointermove", (e) => {
      if (!start || e.pointerId !== start.id) return;
      start.dy = Math.max(0, e.clientY - start.y);
      sheet.style.transform = `translateY(${start.dy}px)`;
    });
    const end = () => {
      if (!start) return;
      const far = start.dy > 90;
      start = null;
      sheet.classList.remove("dragging");
      if (far) close(); else sheet.style.transform = "";
    };
    sheet.addEventListener("pointerup", end);
    sheet.addEventListener("pointercancel", end);
  }

  // Arrows and chevrons point the other way in a right-to-left language.
  const FLIP = new Set(["arrow_back", "arrow_forward", "chevron_right", "chevron_left"]);

  function applyI18n() {
    const meta = metaOf(state.lang) || {};
    document.documentElement.lang = state.lang;
    document.documentElement.dir = meta.dir === "rtl" ? "rtl" : "ltr";
    $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    $$("[data-i18n-label]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nLabel)); });
    $$(".ms").forEach((m) => { if (FLIP.has(m.textContent.trim())) m.classList.add("flip"); });
    $("#lang-toggle").textContent = shortLabel(state.lang);
    $("#lang-note").textContent = "";  // no translation note on the home screen
    $("#lang-note").hidden = true;
    if (state.check) renderResult(state.check);
    renderExamples();
    renderNavIntro();
    if (nav.question) renderQuestion();
    if (nav.result) { renderNavResult(); renderSlip(); }
    setupMessageMic();
    renderVoiceStatus();
    if (state.mode) setMode(state.mode);
    if (state.check) renderQRBox(state.check);
    renderLearn();
    if (game.round) { renderPlay(); if (!$('[data-screen="game-done"]').hidden) renderDone(); }
    updateNavTitle();
  }

  // ---------------------------------------------------------------- navigation
  // The tab each screen belongs to: the bar at the bottom shows where the person is.
  const TAB_OF = { home: "home", check: "check", result: "check", complaint: "check", benefits: "benefits", question: "benefits",
    "benefits-result": "benefits", slip: "benefits", learn: "learn", play: "learn", "game-done": "learn" };
  // How deep each screen sits in its tab: going deeper pushes the new screen in from the side, as in iOS; coming
  // back pops it; changing tab cross-fades.
  const DEPTH = { home: 0, check: 0, benefits: 0, learn: 0, result: 1, complaint: 2, question: 1, "benefits-result": 2,
    slip: 3, play: 1, "game-done": 2 };
  let currentScreen = "home";
  function markScreen(screen) {
    document.body.dataset.at = screen;  // not data-screen: that names the sections
    const tabs = $$(".tab");
    const index = tabs.findIndex((b) => b.dataset.tab === TAB_OF[screen]);
    const bar = $(".tabbar");
    if (index >= 0 && bar.style.getPropertyValue("--i") !== String(index)) {
      if (bar.style.getPropertyValue("--i") !== "") replay($(".tab-lens"), "moving");
      bar.style.setProperty("--i", String(index));
    }
    tabs.forEach((b) => {
      const on = b.dataset.tab === TAB_OF[screen];
      if (on && !b.hasAttribute("aria-current")) replay(b, "tab-bounce");
      if (on) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
  }
  // go(screen, { render, focus, dir }): render runs inside the transition, so the old screen is captured first.
  function go(screen, opts = {}) {
    const from = currentScreen;
    currentScreen = screen;
    const update = () => {
      if (opts.render) opts.render();
      $$(".screen").forEach((s) => { s.hidden = s.dataset.screen !== screen; });
      markScreen(screen);
      window.scrollTo({ top: 0 });
      if (screen === "learn") renderLearn();
      updateNavTitle();
      const f = opts.focus && $(opts.focus);
      if (f) f.focus({ preventScroll: true });
      if (screen === "check") setTimeout(() => $("#msg").focus({ preventScroll: true }), 60);
    };
    const dir = opts.dir || (from === screen ? (opts.render ? "push" : "")
      : TAB_OF[from] !== TAB_OF[screen] ? "fade" : (DEPTH[screen] || 0) >= (DEPTH[from] || 0) ? "push" : "pop");
    if (dir && document.startViewTransition && !reduceMotion()) {
      const root = document.documentElement;
      root.dataset.nav = dir;
      const vt = document.startViewTransition(update);
      vt.finished.finally(() => { if (root.dataset.nav === dir) delete root.dataset.nav; });
    } else {
      update();
    }
    if (screen === "learn") loadGame().catch(() => {});
    if (voice.auto) speakScreen(screen);
  }

  // ---------------------------------------------------------------- motion
  // Everything here moves with transform and opacity only, and stops for "reduce motion".
  function reduceMotion() { return Boolean(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches); }
  // Restart a CSS animation on an element that stays on the page.
  function replay(node, cls) {
    if (!node || reduceMotion()) return;
    node.classList.remove(cls);
    void node.offsetWidth;
    node.classList.add(cls);
    node.addEventListener("animationend", () => node.classList.remove(cls), { once: true });
  }
  // While Sahayak reads a message, a glow flows round the edge of the screen, as Apple Intelligence does. The answer
  // waits at most a little over half a second for it, so the person sees that the message was read.
  function glowOn() {
    if (reduceMotion()) return 0;
    const g = $("#glow");
    g.hidden = false;
    requestAnimationFrame(() => g.classList.add("on"));
    $("#msg").classList.add("scanning");
    return performance.now();
  }
  function glowOff() {
    const g = $("#glow");
    g.classList.remove("on");
    $("#msg").classList.remove("scanning");
    setTimeout(() => { if (!g.classList.contains("on")) g.hidden = true; }, 400);
  }
  const glowAtLeast = (started) => (started ? new Promise((done) => setTimeout(done, Math.max(0, 650 - (performance.now() - started)))) : null);
  // The edges of the screen flash once in the answer's colour: red for a scam, green for a right answer.
  function edgeFlash(kind) {
    if (reduceMotion()) return;
    const tone = { scam: "red", wrong: "red", suspicious: "orange", no_signs: "green", right: "green" }[kind];
    if (!tone) return;
    const f = el("div", { class: `edge-flash ${tone}`, "aria-hidden": "true" });
    document.body.append(f);
    setTimeout(() => f.remove(), 1300);
  }
  // A number that counts up to its new value, easing out, the way Apple's activity numbers do.
  function countUp(node, to, { from = 0, ms = 750, format = String } = {}) {
    if (!node) return;
    if (reduceMotion() || to === from) { node.textContent = format(to); return; }
    const start = performance.now();
    node.textContent = format(from);
    const step = (now) => {
      const k = Math.min(1, (now - start) / ms);
      node.textContent = format(Math.round(from + (to - from) * (1 - Math.pow(1 - k, 3))));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  // The bar: clear at the top of a screen, frosted once the page scrolls under it; the screen's own title moves
  // into the bar when its large title scrolls away.
  let titleNode = null;
  function screenTitleNode() {
    const sec = $(`section.screen[data-screen="${currentScreen}"]`);
    if (!sec) return null;
    if (currentScreen === "result") return $(".v-label", sec);
    if (currentScreen === "benefits-result") return $(".nav-summary .big", sec);
    return $(".large-title, .screen-head h2, .play-q, .done-title, :scope > h2", sec);
  }
  function updateNavTitle() {
    titleNode = screenTitleNode();
    $("#nav-title").textContent = titleNode ? titleNode.textContent : "";
    onScroll();
  }
  let scrollQueued = false;
  function onScroll() {
    scrollQueued = false;
    if (currentScreen === "home" && !reduceMotion()) {
      const y = Math.min(window.scrollY, 260);
      const intro = $(".intro");
      intro.style.transform = y > 0 ? `translateY(${(y * 0.32).toFixed(1)}px)` : "";
      intro.style.opacity = y > 0 ? String(Math.max(0, 1 - y / 230).toFixed(3)) : "";
    }
    const bar = $(".topbar");
    bar.classList.toggle("scrolled", window.scrollY > 2);
    const edge = bar.getBoundingClientRect().bottom;
    bar.classList.toggle("titled", Boolean(titleNode && titleNode.textContent.trim() && titleNode.getClientRects().length
      && titleNode.getBoundingClientRect().bottom < edge - 2));
  }
  window.addEventListener("scroll", () => { if (!scrollQueued) { scrollQueued = true; requestAnimationFrame(onScroll); } }, { passive: true });

  // What each screen says when it opens (the scam verdict speaks itself in runCheck).
  function speakScreen(screen) {
    const say = {
      home: () => joinSpoken([t("home_title"), t("home_sub")]),
      check: () => joinSpoken([t("check_title"), t("check_label")]),
      benefits: () => joinSpoken([t("tile_benefits"), t("nav_intro")]),
      question: spokenQuestion,
      "benefits-result": spokenResult,
      learn: () => joinSpoken([t("tile_learn"), t("learn_sub")]),
    }[screen];
    if (say) speak(say());
  }
  document.addEventListener("click", (e) => {
    const target = e.target.closest("[data-go]");
    if (target) { e.preventDefault(); go(target.dataset.go); }
  });

  // ---------------------------------------------------------------- toast
  let toastTimer;
  function toast(msg, kind) {
    let el = $(".toast");
    if (!el) { el = document.createElement("div"); el.setAttribute("role", "status"); document.body.append(el); }
    el.className = kind ? `toast ${kind}` : "toast";
    el.textContent = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.remove(), 3500);
  }
  function hideToast() {  // a "reading..." notice goes as soon as the answer is in
    clearTimeout(toastTimer);
    const el = $(".toast");
    if (el) el.remove();
  }

  // ---------------------------------------------------------------- the node, or this phone on its own
  // On the CSC's Wi-Fi every answer comes from the node. Away from it (at home, where the scam message
  // or call actually arrives) the scam check and the benefits interview run in this browser instead, from
  // the same packs the node verified and served, which the service worker keeps (web/checker.js,
  // web/navigator.js). Nothing leaves the phone either way. The stand-alone build has no node at all.
  // The stand-alone build marks its page with <meta name="sahayak-standalone"> (scripts/build_tryit.py).
  const STANDALONE = Boolean(document.querySelector('meta[name="sahayak-standalone"]'));
  const ROOT = STANDALONE ? "" : "/";  // static files: relative in the stand-alone build
  const local = { ready: null, checker: null, nav: null, demo: null, packs: [] };
  let nodeRetryAt = 0;  // after a failed call, go straight to the phone for a while instead of waiting again

  class NodeUnreachable extends Error {}

  function loadLocal() {
    if (!local.ready) {
      local.ready = (async () => {
        const get = async (name) => {
          const res = await fetch(`${ROOT}phone-packs/${name}.json`);
          if (!res.ok) throw new Error(`pack ${name}: HTTP ${res.status}`);
          return res.json();
        };
        const [fraud, patterns, model, schemes, demo] = await Promise.all(
          ["fraud", "scam_patterns", "fraud_model", "schemes", "demo"].map(get));
        local.checker = window.SahayakChecker.create({ fraud: fraud.data, patterns: patterns.data, model: model.data,
          fraudSha256: fraud.sha256 });
        local.nav = window.SahayakNavigator.create(schemes.data);
        local.demo = demo.data;
        local.packs = [fraud, patterns, model, schemes, demo].map(({ name, version, date, sha256, signed_by }) =>
          ({ name, version, date, sha256, signed_by }));
      })();
      local.ready.catch(() => { local.ready = null; });  // try again next time
    }
    return local.ready;
  }

  async function nodeApi(path, body) {
    if (STANDALONE || Date.now() < nodeRetryAt) throw new NodeUnreachable(path);
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 4000);
    let res;
    try {
      res = await fetch(path, {
        signal: ctl.signal,
        ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
      });
    } catch {
      throw new NodeUnreachable(path);
    } finally {
      clearTimeout(timer);
    }
    if (!res.ok) throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status });
    setNodeless(false);
    return res.json();
  }

  // What this phone can answer by itself, in the same shape as the node's API.
  const LOCAL_API = {
    "/api/check": (b) => ({ ...local.checker.check(b.text, { sender: b.sender, inputType: b.input_type }), where: "phone" }),
    "/api/examples": () => local.demo,
    "/api/navigator": () => local.nav.catalog(),
    "/api/navigator/next": (b) => local.nav.next(b.answers || {}),
    "/api/navigator/result": (b) => local.nav.result(b.answers || {}, b.already || []),
  };

  async function api(path, body) {
    try {
      return await nodeApi(path, body);
    } catch (e) {
      if (!(e instanceof NodeUnreachable) || !LOCAL_API[path]) throw e;
      setNodeless(true);
      await loadLocal();
      return LOCAL_API[path](body || {});
    }
  }

  // Without the node: no voice input (recognition runs on the node), no screenshot reading, no agent
  // queue; QR codes only where the browser can read them itself.
  function setNodeless(on) {
    if (STANDALONE) on = true;
    if (on) nodeRetryAt = Date.now() + 30000;
    if (state.nodeless === on) return;
    state.nodeless = on;
    if (on) {
      state.health = null;
      voice.nodeOk = false;  // the phone's own voice reads the screens
    } else {
      loadHealth();
    }
    renderNodeMode();
  }

  function renderNodeMode() {
    const off = Boolean(state.nodeless);
    for (const [sel, key] of [["#node-pill [data-i18n]", "node_pill"], [".foot [data-i18n]", "foot"]]) {
      const node = $(sel);
      node.dataset.i18n = off ? `${key}_phone` : key;  // applyI18n keeps it on a language switch
      node.textContent = t(node.dataset.i18n);
    }
    $("#node-pill").classList.toggle("phone", off);
    $("#phone-mode-note").hidden = !off;
    $('input[name="mode"][value="ocr"]').closest("label").hidden = off;
    $("#btn-agent-check").hidden = off;
    $("#btn-agent-nav").hidden = off;
    if (off && state.mode === "ocr") setMode("text");
    setupMessageMic();
    if (nav.question) renderQuestionMic();
    renderVoiceStatus();
  }

  // ---------------------------------------------------------------- four ways in
  // A typed or spoken message, a description of a call, a photo of a QR code, or a screenshot.
  state.mode = "text";
  function setMode(mode) {
    state.mode = mode;
    $$('input[name="mode"]').forEach((r) => { r.checked = r.value === mode; });
    const image = mode === "qr" || mode === "ocr";
    $("#mode-text").hidden = image;
    $("#mode-image").hidden = !image;
    $("#msg-label").textContent = t(mode === "call" ? "call_label" : "check_label");
    $("#ocr-review").hidden = mode !== "ocr" || !$("#msg").value;
    $("#image-label").textContent = t(mode === "qr" ? "qr_label" : "ocr_label");
    $("#image-btn-label").textContent = t(mode === "qr" ? "qr_btn" : "ocr_btn");
    const input = $("#image-input");
    if (mode === "qr") input.setAttribute("capture", "environment"); else input.removeAttribute("capture");
    $("#btn-paste").hidden = !canPaste || mode !== "text";
    $("#qr-try-label").hidden = mode !== "qr";
    $("#qr-examples").hidden = mode !== "qr";
  }
  $$('input[name="mode"]').forEach((r) => r.addEventListener("change", () => {
    if (r.value === "ocr" && state.mode !== "ocr") $("#msg").value = "";
    setMode(r.value);
  }));

  // Phone cameras make photos of 3 to 12 MB; the node reads QR codes and text at under 2,000 pixels
  // anyway, so a large photo is shrunk here first: a much quicker upload on a busy Wi-Fi.
  async function shrinkPhoto(blob, longest = 2000) {
    try {
      if (blob.size < 1500000 || !("createImageBitmap" in window)) return blob;
      const bmp = await createImageBitmap(blob);
      const scale = longest / Math.max(bmp.width, bmp.height);
      if (scale >= 1) { bmp.close(); return blob; }
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(bmp.width * scale);
      canvas.height = Math.round(bmp.height * scale);
      canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height);
      bmp.close();
      const out = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
      return out || blob;
    } catch {
      return blob;  // the node shrinks it too, and refuses only what no camera makes
    }
  }

  async function postImage(path, blob) {
    if (STANDALONE || Date.now() < nodeRetryAt) throw new NodeUnreachable(path);
    const body = await shrinkPhoto(blob);
    let res;
    try {
      res = await fetch(path, { method: "POST", headers: { "Content-Type": body.type || "application/octet-stream" }, body });
    } catch {
      throw new NodeUnreachable(path);
    }
    if (!res.ok) throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status });
    return res.json();
  }

  // Without the node: the browser's own QR reader (Chrome on Android has one), then the same UPI
  // analysis and scam check as the node, on this phone. A demo card's payload needs no reader.
  async function qrOnPhone(blob, payload) {
    await loadLocal();
    let text = payload;
    if (!text) {
      if (!("BarcodeDetector" in window)) throw Object.assign(new Error("no QR reader"), { status: 501 });
      const codes = await new window.BarcodeDetector({ formats: ["qr_code"] }).detect(await createImageBitmap(blob));
      if (!codes.length) throw Object.assign(new Error("no QR code"), { status: 422 });
      text = codes[0].rawValue;
    }
    const { check_text: checkText, ...qr } = local.checker.analyseQR(text);
    return { ...local.checker.check(checkText, { inputType: "qr" }), qr, where: "phone" };
  }

  async function checkQR(blob, payload) {
    toast(t("qr_reading"));
    const started = glowOn();
    try {
      let card;
      try {
        if (!blob) throw new NodeUnreachable("qr");
        card = await postImage(`/api/qr?lang=${base()}`, blob);
      } catch (e) {
        if (!(e instanceof NodeUnreachable)) throw e;
        if (blob) setNodeless(true);
        card = await qrOnPhone(blob, payload);
      }
      await glowAtLeast(started);
      hideToast();
      state.check = card; state.message = ""; state.explanation = null;
      renderResult(card);
      go("result", { focus: "#headline" });
      edgeFlash(card.verdict);
      buzz(card);
      if (voice.auto) speak(joinSpoken([tr(card.label), ...(card.qr.facts || []).map((f) => tr(f))]));
    } catch (e) {
      toast(t(e.status === 422 ? "qr_none" : e.status === 501 ? "qr_no_detector" : "err_network"));
    } finally {
      glowOff();
    }
  }

  async function readScreenshot(blob) {
    toast(t("ocr_reading"));
    try {
      const out = await postImage("/api/ocr", blob);
      hideToast();
      if (!out.text) { toast(t("ocr_none")); return; }
      $("#msg").value = out.text;
      setMode("ocr");
      $("#mode-text").hidden = false;
      $("#mode-image").hidden = true;
      $("#ocr-review").hidden = false;
      $("#msg").focus();
      if (voice.auto) speak(t("ocr_review"));
    } catch (e) {
      toast(t(e.status === 422 ? "ocr_none" : e.status === 503 || e instanceof NodeUnreachable ? "ocr_off" : "err_network"));
    }
  }

  $("#image-input").addEventListener("change", () => {
    const file = $("#image-input").files && $("#image-input").files[0];
    $("#image-input").value = "";
    if (!file) return;
    if (state.mode === "qr") checkQR(file); else readScreenshot(file);
  });

  async function loadQRExamples() {
    let list = [];
    try { list = (await api("/api/examples")).qr_examples || []; } catch { list = []; }
    $("#qr-examples").replaceChildren(...list.map((ex) => el("button", { type: "button", class: "chip", onclick: async () => {
      if (state.nodeless) { checkQR(null, ex.payload); return; }
      const res = await fetch(`/api/demo/qr/${ex.id}`).catch(() => null);
      if (res && res.ok) checkQR(await res.blob()); else checkQR(null, ex.payload);
    } }, icon("qr_code_2"), tr(ex.label))));
  }

  function renderQRBox(card) {
    const box = $("#qr-box");
    const q = card.qr;
    if (!q) { box.hidden = true; return; }
    const rows = [];
    const row = (key, value, cls) => el("div", { class: `qr-row${cls ? ` ${cls}` : ""}` },
      el("span", { class: "qr-k" }, t(key)), el("span", { class: "qr-v" }, value));
    if (q.kind === "upi") {
      if (q.name || q.payee) rows.push(row("qr_pays", q.name || q.payee));
      if (q.payee) rows.push(row("qr_upi", q.payee));
      if (q.amount_text) rows.push(row("qr_amount", q.amount_text, "qr-amount"));
    }
    box.replaceChildren(...rows, ...(q.facts || []).map((f) => el("p", { class: "qr-fact" }, tr(f))));
    box.hidden = !rows.length && !(q.facts || []).length;
  }

  // ---------------------------------------------------------------- examples
  let examples = [];
  async function loadExamples() {
    try { examples = (await api("/api/examples")).examples || []; } catch { examples = []; }
    renderExamples();
  }
  function useExample(ex) {
    setMode(ex.input_type === "call" ? "call" : "text");
    $("#msg").value = ex.text;
    $("#sender").value = ex.sender || "";
    if (ex.sender) $("details.extra").open = true;
    return runCheck();
  }
  function renderExamples() {
    const root = $("#examples");
    root.replaceChildren(...examples.map((ex) => {
      return el("button", { type: "button", class: "chip", onclick: () => useExample(ex) },
        icon(ex.input_type === "call" ? "phone_in_talk" : "sms"), tr(ex.label));
    }));
  }

  // ---------------------------------------------------------------- check
  async function runCheck() {
    const text = $("#msg").value.trim();
    if (!text) { toast(t("err_empty")); $("#msg").focus(); return; }
    const btn = $("#btn-check");
    const label = $("#btn-check .btn-label");
    btn.disabled = true; btn.classList.add("loading"); label.textContent = t("checking");
    const sender = $("#sender").value.trim() || null;
    const input_type = state.mode === "call" ? "call" : state.mode === "ocr" ? "ocr" : "text";
    const started = glowOn();
    try {
      const card = await api("/api/check", { text, sender, input_type, lang: base() });
      await glowAtLeast(started);
      state.check = card; state.message = text; state.explanation = null;
      renderResult(card);
      go("result", { focus: "#headline" });
      edgeFlash(card.verdict);
      buzz(card);
      if (voice.auto) speak(spokenSummary(card), state.lang);
      if (card.where !== "phone") explain(card.id);  // the vetted reasons already explain a phone check
    } catch {
      toast(t("err_network"));
    } finally {
      btn.disabled = false; btn.classList.remove("loading"); label.textContent = t("check_btn");
      glowOff();
    }
  }
  $("#btn-check").addEventListener("click", runCheck);

  async function explain(id) {
    const box = $("#explain");
    box.classList.add("loading");
    $("#explain-text").textContent = t("explaining");
    try {
      const out = await api("/api/explain", { id });
      if (!state.check || state.check.id !== id) return; // user moved on
      state.explanation = out;
      if (out.card && out.card.verdict !== state.check.verdict) {  // model raised "no signs" to "suspicious"
        state.check = out.card;
        renderResult(out.card);
      } else {
        renderExplanation();
      }
    } catch {
      state.explanation = null;
      renderExplanation();
    }
  }

  // ---------------------------------------------------------------- result
  // One line of a card: the display language, and under it the same line in the second language (hi or en).
  function bilingualItem(mainText, subText, extraClass) {
    const li = document.createElement("li");
    if (extraClass) li.className = extraClass;
    const main = document.createElement("span");
    main.textContent = mainText;
    const sub = document.createElement("span");
    sub.className = "en"; sub.lang = second(); sub.dir = "auto"; sub.textContent = subText;
    li.append(main, sub);
    return li;
  }

  function renderResult(card) {
    const v = $("#verdict");
    v.className = `verdict ${card.verdict}`;
    v.replaceChildren(
      el("span", { class: "v-glyph", "aria-hidden": "true" }, icon(ICONS[card.verdict])),
      el("div", { class: "v-words" },
        el("div", { class: "v-label" }, tr(card.label)),
        el("div", { class: "v-label-2", lang: second(), dir: "auto" }, card.label[second()])));

    $("#headline").textContent = tr(card.headline);
    replay($("#headline"), "rise-in");
    renderQRBox(card);
    $("#reasons").replaceChildren(...card.reasons.map((r) => bilingualItem(tr(r.text), r.text[second()], r.hard ? "hard" : "")));
    $("#actions").replaceChildren(...trList(card.actions).map((a, i) => bilingualItem(a, (card.actions[second()] || [])[i] || "")));
    // 1930 is for money already lost, and a complaint needs a message Sahayak could read and found signs in.
    const nothingFound = card.verdict === "no_signs" || card.verdict === "unreadable";
    $("#btn-1930").hidden = nothingFound;
    $("#btn-complaint").hidden = nothingFound;
    // A fake scheme message: offer the real thing, checked safely on this node.
    const schemeBait = card.signals.some((s) => s.id === "govt_scheme_bait")
      || ["govt_scheme", "govt_payment"].includes(card.category && card.category.id);
    $("#btn-real-benefits").hidden = !(schemeBait && card.verdict !== "no_signs");
    $("#btn-share").hidden = !canShare || !["scam", "suspicious"].includes(card.verdict);
    $("#checked").hidden = !state.message;
    $("#checked-text").textContent = state.message;
    renderExplanation();
    renderMeta();
  }

  // The model writes only in languages it has been cleared for; elsewhere the reasons
  // below already say everything, so the "In simple words" box stays hidden.
  function modelWrote(out, lang) {
    return Boolean(out && out.source !== "template" && out.safety && out.safety.langs && out.safety.langs[lang]);
  }
  function modelExpected(lang) {
    if (state.nodeless || (state.check && state.check.where === "phone")) return false;
    const llm = state.health && state.health.llm;
    return Boolean(llm && llm.available && (state.health.llm_langs || []).includes(lang));
  }

  function renderExplanation() {
    const box = $("#explain");
    const out = state.explanation;
    const card = state.check;
    if (!card) return;
    if (!out) {
      $("#safety-badge").hidden = true;  // nothing to vouch for until an explanation arrives (never, for a QR card)
      $("#safety-detail").hidden = true;
      $("#safety-badge").setAttribute("aria-expanded", "false");
      box.hidden = !modelExpected(state.lang);
      box.classList.add("loading");
      $("#explain-text").textContent = t("explaining");
      return;
    }
    box.classList.remove("loading");
    box.hidden = !modelWrote(out, state.lang);
    $("#explain-text").textContent = out.explanation[base()] || "";
    renderSafety(out);
    renderMeta();
  }

  function renderSafety(out) {
    const badge = $("#safety-badge");
    const detail = $("#safety-detail");
    badge.textContent = t("safety_ok");
    badge.hidden = false;
    const checks = (out.safety && out.safety.checks) || [];
    const lines = checks.filter((c) => c.lang === base()).map((c) => `${c.passed ? "✓" : "✗"} ${c.id.replace(/_/g, " ")}`);
    const src = out.source === "template" ? t("template_text") : `${t("model_text")}: ${out.model || ""}`;
    detail.replaceChildren();
    const p = document.createElement("div"); p.textContent = `${t("safety_checks")} (${src})`;
    const ul = document.createElement("ul");
    (lines.length ? lines : ["✓ vetted template"]).forEach((line) => { const li = document.createElement("li"); li.textContent = line; ul.append(li); });
    detail.append(p, ul);
  }
  $("#safety-badge").addEventListener("click", () => {
    const d = $("#safety-detail");
    d.hidden = !d.hidden;
    $("#safety-badge").setAttribute("aria-expanded", String(!d.hidden));
  });

  function renderMeta() {
    const card = state.check;
    if (!card) return;
    const parts = [`${t(card.where === "phone" ? "checked_phone" : "checked_in")} ${card.timing_ms.total} ${t("ms")}`,
      `${t("pack")} ${card.pack.version}`];
    // Away from the node the phone checks with the patterns it last fetched; say when they are getting old.
    const fraud = card.where === "phone" ? local.packs.find((p) => p.name === "fraud") : null;
    const days = fraud && fraud.date ? Math.floor((Date.now() - Date.parse(fraud.date)) / 86400000) : 0;
    if (days > 45) parts.push(fmt(t("pack_old"), { days }));
    const out = state.explanation;
    if (modelWrote(out, state.lang) && out.tokens_per_s) parts.push(`${out.model} · ${out.tokens_per_s} tok/s`);
    $("#meta").textContent = parts.join(" · ");
  }

  function spokenSummary(card) {
    const first = trList(card.actions)[0] || "";
    return `${tr(card.label)}. ${tr(card.headline)} ${first}`;
  }

  // ---------------------------------------------------------------- voice: speech out
  // The node speaks with offline Hindi and English voices; the phone's own voice is the
  // fallback. Amounts, helplines and acronyms are turned into words on the node.
  function loadPref(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } }
  function savePref(key, value) { try { localStorage.setItem(key, value); } catch { /* private mode */ } }
  const voice = {
    auto: loadPref("sahayak.voice.auto", "0") === "1",  // off until the person turns it on
    gender: loadPref("sahayak.voice.gender", "female"),
    slow: loadPref("sahayak.voice.slow", "0") === "1",
    nodeOk: true,  // false once the node says it has no voice installed
    token: 0,
    audio: null,
  };

  function stopSpeaking() {
    voice.token += 1;
    if (voice.audio) { voice.audio.pause(); voice.audio = null; }
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }

  function splitSentences(text) {
    return text.split(/(?<=[।.?!])\s+/).map((s) => s.trim()).filter(Boolean)
      .flatMap((s) => (s.length > 480 ? s.match(/[\s\S]{1,460}(\s|$)/g) : [s]));
  }

  // A node speaking for many phones at once can take seconds over a sentence it has not said before.
  // If the first sentence of a screen is not back in time, this phone reads the screen in its own voice.
  const FIRST_SENTENCE_MS = 4000;

  async function ttsBlob(text, lang, ms = 0) {
    const ctrl = "AbortController" in window ? new AbortController() : null;
    const timer = ms && ctrl ? setTimeout(() => ctrl.abort(), ms) : null;
    try {
      const res = await fetch("/api/tts", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, lang, voice: voice.gender, speed: voice.slow ? 0.75 : 0.9 }),
        signal: ctrl ? ctrl.signal : undefined,
      });
      if (res.status === 503) voice.nodeOk = false;
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.blob();
    } finally {
      clearTimeout(timer);
    }
  }

  function phoneVoice(lang) {
    if (!("speechSynthesis" in window)) return null;
    const want = lang;  // a voice for this very language: "hi" for hi-IN, "ta" for ta-IN
    return window.speechSynthesis.getVoices().find((vo) => vo.lang && vo.lang.toLowerCase().replace("_", "-").split("-")[0] === want) || null;
  }

  function playBlob(blob, token) {
    return new Promise((resolve, reject) => {
      if (token !== voice.token) { resolve(); return; }
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      voice.audio = audio;
      const finish = (err) => { URL.revokeObjectURL(url); if (err) reject(err); else resolve(); };
      audio.onended = () => finish();
      audio.onerror = () => finish(new Error("audio"));
      // Browsers refuse sound before the first tap; that is not an error worth a fallback.
      audio.play().catch((e) => (e && e.name === "NotAllowedError" ? finish() : finish(e)));
    });
  }

  function phoneSpeak(text, lang) {
    if (!("speechSynthesis" in window) || !text) return false;
    const synth = window.speechSynthesis;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang === "hi" ? "hi-IN" : lang === "en" ? "en-IN" : ((metaOf(lang) || {}).tts || lang);
    const v = phoneVoice(lang);
    if (v) u.voice = v;
    u.rate = voice.slow ? 0.75 : 0.92;
    synth.speak(u);
    return Boolean(v);
  }

  // Sentence by sentence: the next sentence is fetched while the current one plays, so the
  // first words come quickly even for a long screen. Returns false only if no voice exists.
  function speak(text, lang = state.lang) {
    stopSpeaking();
    if (!text) return false;
    // The node speaks Hindi and English. Another language is read only by a voice of its own on the phone;
    // with none, nothing is said rather than the words read out in the wrong language's voice.
    if (!isBuiltin(lang)) return phoneVoice(lang) ? phoneSpeak(text, lang) : false;
    if (!voice.nodeOk) return phoneSpeak(text, lang);
    const token = voice.token;
    const parts = splitSentences(text);
    // Only the first sentence has a deadline (later ones are fetched while the one before plays), and
    // only when the phone has a voice of its own for this language to take over with.
    const fetchPart = (i) => {
      const p = ttsBlob(parts[i], lang, i === 0 && phoneVoice(lang) ? FIRST_SENTENCE_MS : 0);
      p.catch(() => {});
      return p;
    };
    (async () => {
      let next = fetchPart(0);
      for (let i = 0; i < parts.length; i += 1) {
        let blob;
        try { blob = await next; } catch { if (token === voice.token) phoneSpeak(parts.slice(i).join(" "), lang); return; }
        if (token !== voice.token) return;
        if (i + 1 < parts.length) next = fetchPart(i + 1);
        try { await playBlob(blob, token); } catch { if (token === voice.token) phoneSpeak(parts.slice(i).join(" "), lang); return; }
        if (token !== voice.token) return;
      }
    })();
    return true;
  }

  function renderSoundToggle() {
    const b = $("#sound-toggle");
    b.setAttribute("aria-pressed", String(voice.auto));
    b.setAttribute("aria-label", t(voice.auto ? "sound_on" : "sound_off"));
    b.title = t(voice.auto ? "sound_on" : "sound_off");
  }
  $("#sound-toggle").addEventListener("click", () => {
    voice.auto = !voice.auto;
    savePref("sahayak.voice.auto", voice.auto ? "1" : "0");
    renderSoundToggle();
    if (voice.auto) speak(t("sound_on")); else stopSpeaking();
  });
  $$('input[name="vgender"]').forEach((r) => {
    r.checked = r.value === voice.gender;
    r.addEventListener("change", () => { voice.gender = r.value; savePref("sahayak.voice.gender", r.value); speak(t(`voice_${r.value}`)); });
  });
  $$('input[name="vspeed"]').forEach((r) => {
    r.checked = r.value === (voice.slow ? "slow" : "normal");
    r.addEventListener("change", () => { voice.slow = r.value === "slow"; savePref("sahayak.voice.slow", voice.slow ? "1" : "0"); speak(t(`speed_${r.value}`)); });
  });

  function renderVoiceStatus() {
    const h = state.health;
    const nodeVoice = Boolean(h && h.voice && h.voice.tts && (h.voice.tts[state.lang] || []).length);
    const lines = [t(nodeVoice ? "voice_ready" : isBuiltin(state.lang) || phoneVoice(state.lang) ? "voice_phone" : "no_voice")];
    if (!canListen) lines.push(t("mic_secure"));
    $("#voice-status").textContent = lines.join(" ");
    renderSoundToggle();
  }

  // ---------------------------------------------------------------- voice: speech in
  // Hold to talk. web/mic.js records 16 kHz mono audio and the node recognises it offline.
  // Browsers open the mic only on a secure origin: localhost on the node, or HTTPS (Phase 6).
  const Mic = window.SahayakMic || { canListen: false, start: async () => {}, stop: () => null };
  const canListen = Mic.canListen;
  let micBusy = false;
  const micGlyph = () => el("span", { class: "mic-glyph", "aria-hidden": "true" }, icon("mic"));

  async function asr(wav, params) {
    const q = new URLSearchParams({ lang: base(), ...params });
    const res = await fetch(`/api/asr?${q}`, { method: "POST", headers: { "Content-Type": wav.type || "application/octet-stream" }, body: wav });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  // Where the browser will not open the mic (a plain-HTTP address), the phone's own recorder
  // app still can: the file it returns (m4a, amr, ogg…) goes to the same recognition on the node.
  function recorderButton(labelKey, onAudio) {
    const label = el("span", { class: "mic-label" }, t(`${labelKey}_upload`));
    const input = el("input", { type: "file", accept: "audio/*", capture: true, hidden: true });
    const btn = el("button", { type: "button", class: "mic upload" }, micGlyph(), label, input);
    btn.addEventListener("click", (e) => { if (e.target !== input) input.click(); });
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      input.value = "";
      if (!file || micBusy) return;
      label.textContent = t("mic_thinking");
      micBusy = true;
      try { await onAudio(file); } finally { micBusy = false; label.textContent = t(`${labelKey}_upload`); }
    });
    return btn;
  }

  // A big hold-to-talk button with a level bar. `onAudio(wav)` gets the finished recording.
  function micButton(labelKey, onAudio) {
    const bar = el("span", { class: "mic-bar" });
    const label = el("span", { class: "mic-label" }, t(labelKey));
    const btn = el("button", { type: "button", class: "mic", "aria-label": t(labelKey) }, micGlyph(), label, el("span", { class: "mic-meter" }, bar));
    if (!canListen) return recorderButton(labelKey, onAudio);
    let starting = null;
    const reset = () => { btn.classList.remove("on"); label.textContent = t(labelKey); bar.style.transform = "scaleX(0)"; };
    const start = (e) => {
      if (starting || micBusy) return;
      if (e && e.pointerId !== undefined) btn.setPointerCapture(e.pointerId);
      btn.classList.add("on");
      label.textContent = t("mic_listening");
      stopSpeaking();
      starting = Mic.start(bar).catch((err) => {
        reset();
        toast(t(err && err.name === "NotAllowedError" ? "mic_denied" : "mic_none"));
        throw err;
      });
    };
    const end = async () => {
      if (!starting) return;
      const pending = starting;
      starting = null;
      try { await pending; } catch { return; }
      const wav = Mic.stop();
      reset();
      if (!wav) { toast(t("mic_short")); return; }
      label.textContent = t("mic_thinking");
      micBusy = true;
      try { await onAudio(wav); } finally { micBusy = false; label.textContent = t(labelKey); }
    };
    btn.addEventListener("pointerdown", (e) => { e.preventDefault(); start(e); });
    btn.addEventListener("pointerup", end);
    btn.addEventListener("pointercancel", end);
    btn.addEventListener("contextmenu", (e) => e.preventDefault());
    btn.addEventListener("keydown", (e) => {  // keyboard: Space or Enter starts, again stops
      if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); if (starting) end(); else start(); }
    });
    return btn;
  }

  function setupMessageMic() {
    if (!isBuiltin(state.lang)) {  // the node hears Hindi and English only; say so, and what it reads
      $("#mic-msg").replaceChildren(el("p", { class: "note" }, `${t("lang_detect")} ${t("lang_mic_off")}`));
      return;
    }
    if (state.nodeless) { $("#mic-msg").replaceChildren(); return; }  // speech is recognised on the node
    $("#mic-msg").replaceChildren(micButton("mic_dictate", async (wav) => {
      try {
        const out = await asr(wav, {});
        if (!out.text) { toast(t("mic_none")); return; }
        const box = $("#msg");
        box.value = (box.value.trim() ? `${box.value.trimEnd()} ` : "") + out.text;
        if (out.confidence < 0.6) toast(t("check_low_conf"));
      } catch {
        toast(t("err_network"));
      }
    }));
  }
  $("#btn-speak").addEventListener("click", () => {
    const card = state.check;
    if (!card) return;
    const expl = state.explanation && isBuiltin(state.lang) ? state.explanation.explanation[state.lang] : "";
    const text = [tr(card.label), expl || tr(card.headline), ...trList(card.actions)].join(". ");
    if (!speak(text, state.lang)) toast(t("no_voice"));
  });

  // ---------------------------------------------------------------- fewer steps for the person
  // Paste and check in one tap (the browser allows reading the clipboard only on a secure page, after a tap).
  const canPaste = Boolean(window.isSecureContext && navigator.clipboard && navigator.clipboard.readText);
  $("#btn-paste").addEventListener("click", async () => {
    let text = "";
    try { text = (await navigator.clipboard.readText()).trim(); } catch { toast(t("paste_denied")); $("#msg").focus(); return; }
    if (!text) { toast(t("paste_empty")); return; }
    $("#msg").value = text.slice(0, 4000);
    runCheck();
  });

  // "Check another" starts with an empty box; the back arrow keeps the message for editing.
  $("#btn-check-another").addEventListener("click", () => {
    $("#msg").value = "";
    $("#sender").value = "";
    $("details.extra").open = false;
    setMode("text");
  });

  // A short buzz when the verdict is Scam: felt even before it is read (phones that can vibrate).
  function buzz(card) {
    if (card.verdict === "scam" && navigator.vibrate) {
      try { navigator.vibrate([180, 90, 180]); } catch { /* not allowed here */ }
    }
  }

  // Warn the family: the verdict and the advice, never the message itself. The person chooses where it goes.
  const mobile = /Android|iPhone|iPad/i.test(navigator.userAgent);
  const canShare = Boolean(navigator.share) || mobile;
  function shareText() {
    const card = state.check;
    const lines = [`${t("share_intro")}: ${tr(card.label)}${stopFor()}`, tr(card.headline), ...trList(card.actions).slice(0, 2)];
    if (STANDALONE) lines.push(`${t("share_try")} ${location.origin}${location.pathname}`);
    return lines.join("\n");
  }
  $("#btn-share").addEventListener("click", async () => {
    if (!state.check) return;
    const text = shareText();
    if (navigator.share) {
      try { await navigator.share({ text }); } catch { /* the person closed the share sheet */ }
      return;
    }
    location.href = `whatsapp://send?text=${encodeURIComponent(text)}`;  // a plain-HTTP node page cannot use the share sheet
  });

  // Text size, kept on this phone: Rosh 27's larger-text steps for people who find the screen hard to read.
  function applyTextSize(size) {
    document.documentElement.dataset.textSize = size;
    $$('input[name="tsize"]').forEach((r) => { r.checked = r.value === size; });
  }
  applyTextSize(loadPref("sahayak.textsize", "normal"));
  $$('input[name="tsize"]').forEach((r) => r.addEventListener("change", () => {
    savePref("sahayak.textsize", r.value);
    applyTextSize(r.value);
  }));

  // Appearance, kept on this phone: Automatic follows the phone; Light, White Titanium and Dark stay as chosen.
  const THEMES = ["auto", "light", "titanium", "dark"];
  const THEME_BAR = { light: "#F9F9F9", titanium: "#F2F1EE", dark: "#161617" };  // the browser's own bar
  function applyTheme(theme) {
    if (!THEMES.includes(theme)) theme = "auto";
    if (theme === "auto") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme;
    $$('meta[name="theme-color"]').forEach((m) => {
      if (!m.dataset.auto) m.dataset.auto = m.content;
      m.content = theme === "auto" ? m.dataset.auto : THEME_BAR[theme];
    });
    $$('input[name="theme"]').forEach((r) => { r.checked = r.value === theme; });
  }
  applyTheme(loadPref("sahayak.theme", "auto"));
  $$('input[name="theme"]').forEach((r) => r.addEventListener("change", () => {
    savePref("sahayak.theme", r.value);
    applyTheme(r.value);
  }));

  // Keep it on the home screen: where the browser offers it (Chrome on Android, over HTTPS), one tap.
  let installPrompt = null;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    installPrompt = e;
    $("#btn-install").hidden = false;
  });
  $("#btn-install").addEventListener("click", async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    try { await installPrompt.userChoice; } catch { /* dismissed */ }
    installPrompt = null;
    $("#btn-install").hidden = true;
  });
  window.addEventListener("appinstalled", () => { $("#btn-install").hidden = true; });

  // ---------------------------------------------------------------- complaint draft
  $("#btn-complaint").addEventListener("click", () => {
    const card = state.check;
    if (!card) return;
    const f = $("#complaint-form");
    const now = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    f.when.value = now;
    f.channel.value = card.input_type === "call" ? t("channel_call") : t("channel_sms");
    f.number.value = (card.extracted.mobiles[0] || $("#sender").value || "");
    f.upi.value = card.extracted.upi_ids[0] || "";
    f.link.value = card.extracted.links[0] || "";
    f.lost.value = "";
    f.txn.value = "";
    f.message.value = state.message;
    go("complaint");
  });
  $("#btn-print").addEventListener("click", () => {
    const s = $('[data-screen="complaint"]');
    s.classList.add("printing");
    window.print();
    s.classList.remove("printing");
    api("/api/counters/slip", { kind: "fraud" }).catch(() => {});
  });

  // ---------------------------------------------------------------- "Ask the agent"
  // Puts the case in the console's queue and shows the person a big ticket number. The agent
  // sees the verdict or the scheme results; message text never leaves the node's memory.
  async function askAgent(body) {
    try {
      const out = await api("/api/queue", { ...body, lang: base() });
      $("#ticket-no").textContent = out.ticket;
      openSheet($("#ticket"));
      $("#ticket-ok").focus();
      if (voice.auto) speak(`${t("ticket_title")}: ${out.ticket.replace("-", " ")}. ${t("ticket_sub")}`);
    } catch {
      toast(t("agent_offline"));
    }
  }
  $("#btn-agent-check").addEventListener("click", () => { if (state.check) askAgent({ kind: "check", check_id: state.check.id }); });
  $("#btn-agent-nav").addEventListener("click", () => askAgent({ kind: "benefits", answers: nav.answers }));
  $("#ticket-ok").addEventListener("click", () => closeSheet($("#ticket")));
  dragToClose($("#ticket"), () => closeSheet($("#ticket")));
  dragToClose($("#lang-sheet"), closeLangSheet);

  // ---------------------------------------------------------------- benefits navigator
  // The node decides everything (rules live in the schemes pack); the phone only asks the
  // question it is given and shows the result. All text goes in through textContent.
  const NAV_GROUPS = ["eligible", "likely", "check", "unlock", "have", "not_eligible"];
  const USEFUL = ["eligible", "likely", "check", "unlock", "have"];
  const TRUTH_ICON = { T: "check_circle", L: "contrast", U: "help", F: "cancel" };
  const SLIP_MARK = { eligible: "✓", likely: "≈", check: "?", unlock: "→" };
  const nav = { catalog: null, answers: {}, order: [], question: null, result: null, already: new Set(), session: null };
  const newSession = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)).replace(/-/g, "").slice(0, 24);

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    node.append(...kids.flat(2).filter((kid) => kid != null && kid !== false));
    return node;
  }
  // A bilingual { en, hi } object from an engine or a pack, in the display language.
  const tr = (obj) => {
    if (!obj) return "";
    if (isBuiltin(state.lang)) return obj[state.lang] ?? obj.en;
    return trEn(obj.en) ?? obj[base()] ?? obj.en ?? "";
  };
  // A Material Symbols glyph; hidden from screen readers, so it never changes what is read out.
  const icon = (name, cls) => el("span", { class: `ms${cls ? ` ${cls}` : ""}${FLIP.has(name) ? " flip" : ""}`, "aria-hidden": "true" }, name);
  const fmt = (s, vars) => s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
  const hostOf = (url) => { try { return new URL(url).host.replace(/^www\./, ""); } catch { return ""; } };

  async function loadNavigator() {
    try { nav.catalog = await api("/api/navigator"); } catch { nav.catalog = null; }
    renderNavIntro();
  }

  function renderNavIntro() {
    const c = nav.catalog;
    $("#nav-demos").replaceChildren(...(c ? c.demos : []).map((d) =>
      el("button", { type: "button", class: "chip", onclick: () => navDemo(d) }, icon("person"), tr(d.label))));
    $("#nav-covers").textContent = c ? `${t("nav_covers")} ${c.schemes.map((s) => s.short).join(" · ")}` : "";
  }

  function navReset() {
    Object.assign(nav, { answers: {}, order: [], question: null, result: null, already: new Set(), session: newSession() });
  }

  async function navNext() {
    try {
      const out = await api("/api/navigator/next", { answers: nav.answers });
      if (out.done) { await navResult(); return; }
      nav.question = out.question;
      const back = nav.back;
      nav.back = false;
      go("question", { render: renderQuestion, focus: "#q-text", dir: back ? "pop" : "push" });
    } catch {
      toast(t("err_network"));
    }
  }

  function navAnswer(value) {
    nav.answers[nav.question.id] = value;
    nav.order.push(nav.question.id);
    navNext();
  }

  function navBack() {
    if (!nav.order.length) { go("benefits"); return; }
    delete nav.answers[nav.order.pop()];
    nav.result = null;
    nav.back = true;
    navNext();
  }

  async function fetchNavResult() {
    nav.result = await api("/api/navigator/result", { answers: nav.answers, already: [...nav.already], session: nav.session, lang: base() });
    renderNavResult();
  }

  async function navResult() {
    try {
      await fetchNavResult();
      go("benefits-result", { focus: "#nav-summary" });
    } catch {
      toast(t("err_network"));
    }
  }

  function navDemo(demo) {
    navReset();
    nav.answers = { ...demo.answers };
    nav.order = Object.keys(demo.answers);
    return navResult();
  }

  // ---- one question per screen
  function renderQuestion() {
    const q = nav.question;
    if (!q) return;
    $("#q-count").textContent = fmt(t("q_count"), { n: q.number, max: q.max_questions });
    $("#q-bar").style.width = `${Math.round((100 * q.number) / q.max_questions)}%`;
    $("#q-text").textContent = tr(q.text);
    $("#q-help").textContent = tr(q.help);
    let body;
    if (q.kind === "age") body = ageInput(q);
    else if (q.kind === "multi") body = multiInput(q);
    else body = [el("div", { class: "opts" }, q.options.map((o) =>
      el("button", { type: "button", class: "opt", onclick: () => navAnswer(o.id) }, tr(o.label))))];
    $("#q-body").replaceChildren(...body);
    renderQuestionMic();
  }

  // ---- answering by voice: the node recognises and matches; the person confirms
  function renderQuestionMic() {
    const q = nav.question;
    $("#q-confirm").hidden = true;
    if (!isBuiltin(state.lang)) { $("#q-mic").replaceChildren(el("p", { class: "note" }, t("lang_mic_off"))); return; }
    if (state.nodeless) { $("#q-mic").replaceChildren(); return; }
    $("#q-mic").replaceChildren(micButton("mic_answer", async (wav) => {
      const params = { question: q.id };
      if (q.options) params.options = q.options.map((o) => o.id).join(",");
      try {
        const out = await asr(wav, params);
        if (nav.question !== q) return;  // the person moved on
        if (!out.text) { toast(t("mic_none")); return; }
        confirmHeard(q, out);
      } catch {
        toast(t("err_network"));
      }
    }));
  }

  function answerLabel(q, answer) {
    if (q.kind === "age") return `${answer} ${t("years_word")}`;
    if (q.kind === "multi") {
      return answer.length ? q.options.filter((o) => answer.includes(o.id)).map((o) => tr(o.label)).join("; ") : tr(q.none);
    }
    const o = q.options.find((x) => x.id === answer);
    return o ? tr(o.label) : String(answer);
  }

  function confirmHeard(q, out) {
    const box = $("#q-confirm");
    const understood = out.answer !== null && out.answer !== undefined;
    const kids = [el("p", { class: "heard" }, `${t("heard")}: “${out.text}”`)];
    if (understood) {
      kids.push(
        el("p", { class: "heard-as" }, `${t("heard_as")}: `, el("b", {}, answerLabel(q, out.answer))),
        el("p", { class: "heard-q" }, t("is_right")),
        el("div", { class: "cta-row" },
          el("button", { type: "button", class: "primary", onclick: () => { box.hidden = true; navAnswer(out.answer); } }, t("yes_right")),
          el("button", { type: "button", class: "secondary", onclick: () => { box.hidden = true; stopSpeaking(); } }, t("say_again"))));
    } else {
      kids.push(el("p", {}, t("not_understood")));
    }
    box.replaceChildren(...kids);
    box.hidden = false;
    box.scrollIntoView({ block: "nearest", behavior: "smooth" });
    if (voice.auto) speak(understood ? `${t("heard_as")}: ${answerLabel(q, out.answer)}. ${t("is_right")}` : t("not_understood"));
  }

  function ageInput(q) {
    const input = el("input", { type: "number", inputmode: "numeric", min: "0", max: "120", "aria-label": t("age_label"),
      placeholder: t("age_label"), class: "age-input" });
    const submit = () => {
      const n = Number(input.value);
      if (input.value === "" || !Number.isInteger(n) || n < 0 || n > 120) { toast(t("age_err")); input.focus(); return; }
      navAnswer(n);
    };
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    return [
      el("div", { class: "age-row" }, input, el("button", { type: "button", class: "primary", onclick: submit }, t("next"), icon("arrow_forward"))),
      el("p", { class: "try" }, t("age_unsure")),
      el("div", { class: "bands" }, q.bands.map((b) =>
        el("button", { type: "button", class: "opt", onclick: () => navAnswer(b.id) }, tr(b.label)))),
    ];
  }

  function multiInput(q) {
    const chosen = new Set();
    const nextBtn = el("button", { type: "button", class: "primary", disabled: true, onclick: () => navAnswer([...chosen]) }, t("next"), icon("arrow_forward"));
    const toggles = q.options.map((o) => {
      const b = el("button", { type: "button", class: "opt toggle", "aria-pressed": "false" },
        el("span", { class: "tick", "aria-hidden": "true" }), el("span", {}, tr(o.label)));
      b.addEventListener("click", () => {
        if (chosen.has(o.id)) chosen.delete(o.id); else chosen.add(o.id);
        b.setAttribute("aria-pressed", String(chosen.has(o.id)));
        nextBtn.disabled = chosen.size === 0;
      });
      return b;
    });
    return [
      el("div", { class: "opts" }, toggles),
      el("div", { class: "cta-row" },
        el("button", { type: "button", class: "secondary", onclick: () => navAnswer([]) }, tr(q.none)), nextBtn),
    ];
  }

  // Join spoken parts so each one stays its own sentence: the node then finds each part
  // ready-made in its speech cache instead of synthesising a new combination.
  function joinSpoken(parts) {
    const stop = stopFor();
    return parts.map((p) => (p || "").trim()).filter(Boolean).map((p) => (/[।.?!]$/.test(p) ? p : p + stop)).join(" ");
  }

  function spokenQuestion() {
    const q = nav.question;
    if (!q) return "";
    const choices = q.kind === "age" ? [] : q.options.map((o) => tr(o.label));
    if (q.kind === "multi") choices.push(tr(q.none));
    return joinSpoken([tr(q.text), tr(q.help), ...choices]);
  }

  // ---- result
  function renderNavResult() {
    const r = nav.result;
    if (!r) return;
    const byId = Object.fromEntries(r.schemes.map((s) => [s.id, s]));
    const useful = USEFUL.reduce((n, g) => n + r.groups[g].length, 0);
    $("#nav-summary").replaceChildren(
      el("div", { class: "big" }, useful ? fmt(t("nav_summary"), { n: useful, total: r.schemes.length }) : t("nav_summary_none")),
      el("div", { class: "profile" }, r.profile.map((p) => el("span", { class: "pchip" }, `${tr(p.short)}: ${tr(p.answer)}`))));
    // Health cover first: free hospital treatment is often the most valuable line on the page, and the
    // card is made at this very counter. Every word and amount here comes from the signed schemes pack.
    const health = r.schemes.filter((s) => s.family === "health" && ["eligible", "likely", "check"].includes(s.status));
    $("#nav-health").replaceChildren(...(health.length ? [el("section", { class: "health-callout" },
      el("div", { class: "hc-title" }, t("health_title")),
      health.map((s) => el("div", { class: "hc-item" },
        el("div", { class: "hc-name" }, `${tr(s.name)} · ${t(`st_${s.status}`)}`),
        s.benefit_now ? el("div", { class: "hc-now" }, tr(s.benefit_now)) : null,
        el("p", { class: "hc-say" }, `${t("say_label")}: “${tr(s.counter)}”`))))] : []));
    const blocks = NAV_GROUPS.filter((g) => r.groups[g].length).map((g) => {
      const cards = r.groups[g].map((id) => schemeCard(byId[id]));
      if (g === "not_eligible") {
        return el("details", { class: "group g-not_eligible" }, el("summary", {}, `${t("g_not_eligible")} (${cards.length})`), cards);
      }
      return el("section", { class: `group g-${g}` }, el("h3", {}, t(`g_${g}`), el("span", { class: "count" }, String(cards.length))), cards);
    });
    $("#nav-groups").replaceChildren(...blocks);
    renderDocsList(r, byId);
    $("#nav-amount-note").textContent = tr(r.notes.amount);
    $("#nav-fraud-note").textContent = tr(r.notes.fraud);
    $("#nav-meta").textContent = `${r.asked} ${t("questions_asked")} · ${t("pack")} ${r.pack.name} v${r.pack.version} · ${r.timing_ms} ${t("ms")}`;
  }

  // Every paper the schemes worth a visit ask for, once each, the most needed first: one list to carry to the CSC.
  function renderDocsList(r, byId) {
    const docs = new Map();
    for (const id of ["eligible", "likely", "check"].flatMap((g) => r.groups[g])) {
      for (const d of byId[id].documents) {
        const key = (d.en || "").split(" (")[0].trim().toLowerCase();
        const entry = docs.get(key) || { d, schemes: [] };
        if (!entry.schemes.includes(byId[id].short)) entry.schemes.push(byId[id].short);
        docs.set(key, entry);
      }
    }
    const list = [...docs.values()].sort((a, b) => b.schemes.length - a.schemes.length);
    $("#nav-docs").replaceChildren(...(list.length ? [el("section", { class: "docs-all" },
      el("div", { class: "docs-all-title" }, t("docs_all_title")),
      el("p", { class: "docs-all-sub" }, t("docs_all_sub")),
      el("ul", { class: "docs" }, list.map(({ d, schemes }) => el("li", {}, el("label", {},  // tick each paper off as it is found
        el("input", { type: "checkbox" }),
        el("span", {}, tr(d), el("small", {}, schemes.length > 1 ? fmt(t("docs_for_n"), { n: schemes.length })
          : fmt(t("docs_for_one"), { name: schemes[0] }))))))))] : []));
  }

  function schemeCard(s) {
    const head = el("div", { class: "s-head" },
      el("span", { class: `st st-${s.status}` }, t(`st_${s.status}`)),
      el("h4", {}, tr(s.name)),
      s.benefit_now && s.status !== "not_eligible" ? el("div", { class: "s-now" }, tr(s.benefit_now)) : null,
      el("p", { class: "s-what" }, tr(s.what)));
    const why = el("ul", { class: "why" }, s.reasons.map((r) =>
      el("li", { class: `t-${r.truth}` }, icon(TRUTH_ICON[r.truth], "ti"), el("span", {}, tr(r.text)))));
    if (s.status === "not_eligible") return el("article", { class: `scheme s-${s.status}` }, head, why);
    const sources = s.sources.map((x) => `${x.publisher}${x.page_date ? `, ${x.page_date}` : ""} (${hostOf(x.url)})`).join(" · ");
    const details = el("details", {}, el("summary", {}, t("details")),
      el("h5", {}, t("why_label")), why,
      s.unlock ? el("p", { class: "unlock" }, tr(s.unlock.hint)) : null,
      s.check_how ? [el("h5", {}, t("how_label")), el("p", {}, tr(s.check_how))] : null,
      el("h5", {}, t("benefit_label")), el("p", {}, tr(s.benefit)),
      el("h5", {}, t("docs_label")), el("ul", { class: "docs" }, s.documents.map((d) => el("li", {}, tr(d)))),
      el("h5", {}, t("where_label")), el("p", {}, tr(s.where)),
      el("h5", {}, t("say_label")), el("blockquote", { class: "say" }, tr(s.counter)),
      el("button", { type: "button", class: "chip", onclick: () => { if (!speak(tr(s.counter), state.lang)) toast(t("no_voice")); } },
        icon("volume_up"), t("speak_btn")),
      s.notes.length ? el("ul", { class: "s-notes" }, s.notes.map((n) => el("li", {}, tr(n)))) : null,
      el("p", { class: "src" }, `${t("source_label")}: ${sources} · ${t("checked_label")} ${s.sources[0].checked}`));
    // "I already get this" makes no sense for a scheme that first needs a bank account.
    const have = s.status === "unlock" ? null : el("label", { class: "have" },
      el("input", { type: "checkbox", checked: nav.already.has(s.id), onchange: (e) => toggleHave(s.id, e.target.checked) }),
      t("have_label"));
    return el("article", { class: `scheme s-${s.status}` }, head, details, have);
  }

  async function toggleHave(id, on) {
    if (on) nav.already.add(id); else nav.already.delete(id);
    try { await fetchNavResult(); } catch { toast(t("err_network")); }
  }

  function spokenResult() {
    const r = nav.result;
    if (!r) return "";
    const byId = Object.fromEntries(r.schemes.map((s) => [s.id, s]));
    const parts = [$("#nav-summary .big").textContent];
    for (const g of ["eligible", "likely", "check", "unlock"]) {
      for (const id of r.groups[g]) {
        const s = byId[id];
        parts.push(tr(s.name), t(`st_${s.status}`), s.benefit_now ? tr(s.benefit_now) : "");
      }
    }
    return joinSpoken(parts);
  }

  // ---- printable slip
  function renderSlip() {
    const r = nav.result;
    if (!r) return;
    const byId = Object.fromEntries(r.schemes.map((s) => [s.id, s]));
    const ids = ["eligible", "likely", "check", "unlock"].flatMap((g) => r.groups[g]);
    const items = ids.map((id) => {
      const s = byId[id];
      return el("li", {},
        el("div", { class: "slip-sname" }, `${SLIP_MARK[s.status]} ${tr(s.name)} — ${t(`st_${s.status}`)}${s.benefit_now ? ` · ${tr(s.benefit_now)}` : ""}`),
        el("div", {}, el("b", {}, `${t("where_label")}: `), tr(s.where)),
        el("div", { class: "slip-docs" }, el("b", {}, `${t("docs_label")}: `), s.documents.map((d) => el("span", { class: "doc" }, `☐ ${tr(d)}`))),
        el("div", { class: "slip-say" }, `“${tr(s.counter)}”`));
    });
    $("#slip-sheet").replaceChildren(
      el("div", { class: "slip-head" },
        r.slip.qr ? el("img", { class: "slip-qr", src: r.slip.qr, alt: t("slip_qr"), width: "128", height: "128" }) : null,
        el("div", {},
          el("h2", {}, t("slip_title")),
          el("p", {}, `${t("slip_date")}: ${r.slip.date} · ${t("slip_no_name")}`),
          r.slip.qr ? el("p", { class: "slip-op" }, t("slip_operator")) : null)),
      el("h3", {}, t("slip_answers")),
      el("ul", { class: "slip-answers" }, r.profile.map((p) => el("li", {}, el("b", {}, `${tr(p.short)}: `), tr(p.answer)))),
      el("h3", {}, t("slip_schemes")),
      items.length ? el("ol", { class: "slip-schemes" }, items) : el("p", {}, t("nav_summary_none")),
      el("p", { class: "slip-note" }, tr(r.notes.amount)),
      el("p", { class: "slip-note" }, tr(r.notes.fraud)),
      el("p", { class: "slip-note" }, tr(r.notes.decision)),
      el("p", { class: "slip-foot" }, `${t("pack")} ${r.pack.name} v${r.pack.version} (${r.pack.date})`));
  }

  $("#btn-nav-start").addEventListener("click", () => { navReset(); navNext(); });
  $("#btn-q-back").addEventListener("click", navBack);
  $("#btn-q-listen").addEventListener("click", () => { if (!speak(spokenQuestion(), state.lang)) toast(t("no_voice")); });
  $("#btn-nav-listen").addEventListener("click", () => { if (!speak(spokenResult(), state.lang)) toast(t("no_voice")); });
  $("#btn-nav-change").addEventListener("click", navBack);
  $("#btn-nav-restart").addEventListener("click", () => { navReset(); go("benefits"); });
  $("#btn-slip").addEventListener("click", () => { renderSlip(); go("slip"); });
  $("#btn-slip-print").addEventListener("click", () => {
    const s = $('[data-screen="slip"]');
    s.classList.add("printing");
    window.print();
    s.classList.remove("printing");
    api("/api/counters/slip", { kind: "scheme" }).catch(() => {});
  });

  // ---------------------------------------------------------------- Spot the scam: the awareness game
  // Messages and calls the team wrote to mirror reported scams (web/game.json, made by scripts/build_game.py). The
  // person says Scam or Real; then this phone's own checker shows its clues and what to do, so the game teaches
  // exactly what a real check would say. Points, level, streak and badges stay on this phone (localStorage): nothing
  // is sent and nothing is counted on the node.
  const GAME_KEY = "sahayak.game.v1";
  const ROUND = 5;            // cards in a round
  const BADGE_NEED = 3;       // right answers of one kind that earn its badge
  const LEVELS = [0, 50, 150, 300, 600];
  const BADGES = ["otp", "upi", "kyc", "arrest", "prize", "money", "scheme", "real"];
  const BADGE_ICON = { otp: "password", upi: "qr_code_2", kyc: "lock", arrest: "local_police", prize: "redeem",
    money: "trending_up", scheme: "account_balance", real: "verified" };
  const game = { cards: null, loading: null, round: null, state: loadGameState() };

  function loadGameState() {
    const blank = { points: 0, rounds: 0, best: 0, streak: 0, lastDay: "", dailyDay: "", seen: [], right: {}, badges: [] };
    try { return { ...blank, ...(JSON.parse(localStorage.getItem(GAME_KEY)) || {}) }; } catch { return blank; }
  }
  function saveGame() { try { localStorage.setItem(GAME_KEY, JSON.stringify(game.state)); } catch { /* private mode */ } }
  const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const today = () => isoDay(new Date());
  const yesterday = () => { const d = new Date(); d.setDate(d.getDate() - 1); return isoDay(d); };
  const liveStreak = () => ([today(), yesterday()].includes(game.state.lastDay) ? game.state.streak : 0);
  function touchStreak() {
    const s = game.state;
    if (s.lastDay === today()) return;
    s.streak = s.lastDay === yesterday() ? s.streak + 1 : 1;
    s.lastDay = today();
  }
  function levelOf(points) {
    let i = 0;
    while (i + 1 < LEVELS.length && points >= LEVELS[i + 1]) i++;
    const next = LEVELS[i + 1];
    return { n: i + 1, name: t(`lvl_${i + 1}`), next, frac: next ? (points - LEVELS[i]) / (next - LEVELS[i]) : 1 };
  }
  const vibrate = (pattern) => { if (navigator.vibrate) { try { navigator.vibrate(pattern); } catch { /* not allowed */ } } };

  function loadGame() {
    if (!game.loading) {
      game.loading = (async () => {
        const [res] = await Promise.all([fetch(`${ROOT}app/game.json`), loadLocal()]);
        if (!res.ok) throw new Error(`game: HTTP ${res.status}`);
        game.cards = (await res.json()).cards;
      })();
      game.loading.catch(() => { game.loading = null; });
    }
    return game.loading;
  }

  // A ring that fills, as in Apple's Fitness rings: the level on the Learn screen, the score at the end of a round.
  const SVG_NS = "http://www.w3.org/2000/svg";
  function ringSvg(size, stroke, frac, withTrack) {
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    const svg = document.createElementNS(SVG_NS, "svg");
    for (const [k, v] of [["width", size], ["height", size], ["viewBox", `0 0 ${size} ${size}`], ["aria-hidden", "true"]]) svg.setAttribute(k, v);
    const circle = (cls) => {
      const e = document.createElementNS(SVG_NS, "circle");
      for (const [k, v] of [["cx", size / 2], ["cy", size / 2], ["r", r], ["fill", "none"], ["stroke-width", stroke], ["class", cls]]) e.setAttribute(k, v);
      return e;
    };
    if (withTrack) svg.append(circle("track"));
    const arc = circle("arc");
    arc.style.strokeDasharray = String(c);
    arc.style.strokeDashoffset = String(c);
    svg.append(arc);
    const to = c * (1 - Math.max(0, Math.min(1, frac)));
    requestAnimationFrame(() => requestAnimationFrame(() => { arc.style.strokeDashoffset = String(to); }));
    return svg;
  }
  function ring(size, stroke, frac, cls, label, small) {
    return el("div", { class: `ring${cls ? ` ${cls}` : ""}`, style: null },
      ringSvg(size, stroke, frac, true),
      el("div", { class: "ring-num" }, el("span", {}, label, small ? el("small", {}, small) : null)));
  }
  // A badge's medal: grey with a part-drawn ring while it is being earned, in its colour once earned.
  function medal(id, frac) {
    const won = frac >= 1;
    const m = el("span", { class: `medal m-${id}${won ? " won" : ""}`, "aria-hidden": "true" }, icon(BADGE_ICON[id]));
    if (!won && frac > 0) m.append(ringSvg(68, 3, frac, false));
    return m;
  }
  const badgeProgress = (id) => Math.min(BADGE_NEED, game.state.right[id] || 0);
  const badgeLine = (id) => (game.state.badges.includes(id) ? t("badge_won") : fmt(t("badge_progress"), { n: badgeProgress(id), total: BADGE_NEED }));

  function renderLearn() {
    const s = game.state;
    const lv = levelOf(s.points);
    const streak = liveStreak();
    $("#level-card").replaceChildren(
      el("div", { class: "lc-top" },
        ring(76, 8, lv.frac, "", String(lv.n)),
        el("div", { class: "lc-text" },
          el("span", { class: "lc-over" }, `${t("level_label")} ${lv.n}`),
          el("b", { class: "lc-name" }, lv.name),
          el("span", { class: "lc-points" }, `${s.points} ${t("points")}`))),
      el("p", { class: "lc-next" }, lv.next ? fmt(t("next_level"), { n: lv.next - s.points, name: t(`lvl_${lv.n + 1}`) }) : t("top_level")),
      el("div", { class: "lc-stats" },
        el("span", { class: `stat streak${streak ? "" : " cold"}` }, icon("local_fire_department"), el("span", {}, fmt(t("streak_days"), { n: streak }))),
        el("span", { class: "stat medals" }, icon("workspace_premium"),
          el("span", {}, fmt(t("badges_count"), { n: s.badges.length, total: BADGES.length })))));
    const done = s.dailyDay === today();
    const daily = $("#daily-card");
    daily.className = `daily-card${done ? " done" : ""}`;
    daily.replaceChildren(
      el("span", { class: "tile-icon", "aria-hidden": "true" }, icon(done ? "task_alt" : "today")),
      el("div", { class: "daily-text" }, el("b", {}, t("daily_title")), el("span", {}, t(done ? "daily_done" : "daily_sub"))),
      done ? null : el("button", { type: "button", class: "tinted", onclick: () => startRound(true) }, t("daily_play")));
    $("#badges").replaceChildren(...BADGES.map((id) => {
      const won = s.badges.includes(id);
      return el("button", { type: "button", class: `badge${won ? " won" : ""}`,
        "aria-label": `${t(`badge_${id}`)}: ${badgeLine(id)}. ${t(`badge_${id}_d`)}`,
        onclick: (e) => {
          if (won) replay(e.currentTarget.querySelector(".medal"), "spin");
          toast(`${t(`badge_${id}`)}: ${t(`badge_${id}_d`)}`, won ? "award" : null);
        } },
      medal(id, won ? 1 : badgeProgress(id) / BADGE_NEED),
      el("span", { class: "badge-name" }, t(`badge_${id}`)),
      el("span", { class: "badge-prog" }, badgeLine(id)));
    }));
    // the points count up from what the person last saw here
    const shown = game.shownPoints ?? s.points;
    countUp($(".lc-points", $("#level-card")), s.points, { from: shown, format: (v) => `${v} ${t("points")}` });
    game.shownPoints = s.points;
    renderLearnBadge();
  }
  // On the home screen: "New" until the first round, then a dot while today's message waits.
  function renderLearnBadge() {
    const b = $("#learn-badge");
    const s = game.state;
    if (!s.rounds) { b.className = "tile-badge"; b.textContent = t("game_new"); b.hidden = false; }
    else if (s.dailyDay !== today()) { b.className = "tile-badge dot"; b.textContent = ""; b.hidden = false; }
    else b.hidden = true;
  }

  const shuffle = (list) => {
    const a = list.slice();
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  };
  // Five cards: one or two real messages, and scams of different kinds, the kinds whose badge is still to earn first.
  function pickRound(daily) {
    const cards = game.cards;
    if (daily) {  // the same message for everyone on a given day
      let h = 7;
      for (const ch of today()) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
      return [cards[h % cards.length]];
    }
    const s = game.state;
    const seen = new Set(s.seen);
    const fresh = (list) => { const f = list.filter((c) => !seen.has(c.id)); return f.length ? f : list; };
    const nReal = Math.random() < 0.5 ? 1 : 2;
    const kinds = shuffle(BADGES.filter((b) => b !== "real")).sort((a, b) => s.badges.includes(a) - s.badges.includes(b));
    const scams = [];
    for (const kind of kinds) {
      if (scams.length >= ROUND - nReal) break;
      const pool = shuffle(fresh(cards.filter((c) => c.badge === kind)));
      if (pool.length) scams.push(pool[0]);
    }
    const reals = shuffle(fresh(cards.filter((c) => c.badge === "real"))).slice(0, ROUND - scams.length);
    return shuffle([...scams, ...reals]);
  }

  async function startRound(daily = false) {
    try { await loadGame(); } catch { toast(t("err_network")); return; }
    game.round = { daily, cards: pickRound(daily), i: 0, right: 0, combo: 0, points: 0, results: [], newBadges: [],
      levelBefore: levelOf(game.state.points).n, answered: false, checked: null };
    go("play", { dir: "push" });
    renderPlay();
    speakCard();
  }

  function renderPlay() {
    const r = game.round;
    if (!r) return;
    $("#play-dots").replaceChildren(...r.cards.map((_, i) =>
      el("i", { class: i < r.results.length ? (r.results[i] ? "right" : "wrong") : i === r.i ? "now" : null })));
    $("#play-score").replaceChildren(icon("star"), el("span", { class: "num" }, String(r.points)));
    if (r.answered && r.gain && !r.counted) {  // the new points count up once
      r.counted = true;
      countUp($("#play-score .num"), r.points, { from: r.points - r.gain, ms: 600 });
    }
    $("#play-count").textContent = fmt(t("card_n"), { n: r.i + 1, total: r.cards.length });
    renderMsgCard(r.cards[r.i], r.answered ? r.checked : null);
    $("#answer-row").hidden = r.answered;
    $("#swipe-hint").hidden = r.answered;
    $("#feedback").hidden = !r.answered;
    if (r.answered) renderFeedback();
  }

  // The card looks like the thing itself: a received SMS bubble, or the words of a phone call.
  function renderMsgCard(card, checked) {
    const call = card.input_type === "call";
    const bubble = el("div", { class: "bubble", dir: "auto", lang: card.lang === "hi" ? "hi" : "en" });
    if (checked && card.truth === "scam") markFlags(bubble, card.text, checked); else bubble.textContent = card.text;
    const box = $("#msg-card");
    box.className = `msg-card${call ? " mc-call" : ""}${checked ? "" : " deal"}`;
    box.style.transform = "";
    box.replaceChildren(
      el("div", { class: "mc-head" },
        el("span", { class: "mc-avatar", "aria-hidden": "true" }, icon(call ? "call" : "person")),
        el("div", { class: "mc-who" },
          el("b", { dir: "auto" }, card.sender || t(call ? "card_call" : "card_sms")),
          card.sender ? el("span", {}, t(call ? "card_call" : "card_sms")) : null)),
      bubble,
      el("span", { class: "stamp s-scam", "aria-hidden": "true" }, t("ans_scam")),
      el("span", { class: "stamp s-real", "aria-hidden": "true" }, t("ans_real")));
  }

  // After the answer, a scam card marks what the checker itself pulled out of it: links, phone numbers, UPI IDs,
  // and the words OTP or PIN when it found an ask for them.
  function markFlags(node, text, checked) {
    const lower = text.toLowerCase();
    const ranges = [];
    const ex = checked.extracted || {};
    for (const v of [...(ex.links || []), ...(ex.upi_ids || [])]) {
      const needle = String(v).toLowerCase();
      if (needle.length < 4) continue;
      for (let at = lower.indexOf(needle); at >= 0; at = lower.indexOf(needle, at + needle.length)) ranges.push([at, at + needle.length]);
    }
    for (const v of ex.mobiles || []) {  // a number as written, with or without spaces: 90000 12345
      const digits = String(v).replace(/\D/g, "").slice(-10);
      if (digits.length < 8) continue;
      for (const m of text.matchAll(new RegExp(digits.split("").join("[\\s-]?"), "g"))) ranges.push([m.index, m.index + m[0].length]);
    }
    if ((checked.signals || []).some((sg) => /otp|pin|secret/.test(sg.id))) {
      for (const m of text.matchAll(/\b(?:OTP|PIN|CVV)\b|ओटीपी/gi)) ranges.push([m.index, m.index + m[0].length]);
    }
    ranges.sort((a, b) => a[0] - b[0]);
    const parts = [];
    let pos = 0;
    for (const [a, b] of ranges) {
      if (a < pos) continue;
      if (a > pos) parts.push(text.slice(pos, a));
      parts.push(el("mark", {}, text.slice(a, b)));
      pos = b;
    }
    parts.push(text.slice(pos));
    node.replaceChildren(...parts);
  }

  function answer(saysScam) {
    const r = game.round;
    if (!r || r.answered || !local.checker) return;
    const card = r.cards[r.i];
    const s = game.state;
    const right = saysScam === (card.truth === "scam");
    r.checked = local.checker.check(card.text, { sender: card.sender, inputType: card.input_type });
    r.answered = true;
    r.wasRight = right;
    r.results.push(right);
    r.gain = 0;
    if (right) {
      r.right++;
      r.combo++;
      r.gain = 10 + (r.combo >= 3 ? 5 : 0);  // three in a row and more: a bonus
      r.points += r.gain;
      s.points += r.gain;
      s.right[card.badge] = (s.right[card.badge] || 0) + 1;
      if (s.right[card.badge] >= BADGE_NEED && !s.badges.includes(card.badge)) { s.badges.push(card.badge); r.newBadges.push(card.badge); }
      vibrate(18);
    } else {
      r.combo = 0;
      vibrate([40, 60, 40]);
    }
    s.seen = [...s.seen.filter((id) => id !== card.id), card.id].slice(-40);
    saveGame();
    edgeFlash(right ? "right" : "wrong");
    renderPlay();
    if (r.gain) popPoints(r.gain);
    const title = $("#feedback .fb-title");
    if (title) title.focus({ preventScroll: true });
    $("#feedback").scrollIntoView({ block: "nearest", behavior: "smooth" });
    if (voice.auto) speak(joinSpoken([t(right ? "fb_right" : "fb_wrong"), card.truth === "scam" ? tr(r.checked.headline) : t("fb_real")]));
  }

  // A tick or a cross drawn with one stroke, as in Apple Pay's "Done".
  function drawnMark(right) {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "mark");
    for (const d of right ? ["M5.5 12.5l4.2 4.2L18.5 7.5"] : ["M7 7l10 10", "M17 7L7 17"]) {
      const path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", d);
      path.setAttribute("pathLength", "1");
      svg.append(path);
    }
    return svg;
  }
  // Ten sparks thrown out from the tick.
  function burst() {
    if (reduceMotion()) return null;
    const box = el("span", { class: "burst", "aria-hidden": "true" });
    for (let i = 0; i < 10; i++) {
      const spark = el("i", {});
      spark.style.setProperty("--a", `${i * 36 + (i % 2 ? 10 : 0)}deg`);
      spark.style.setProperty("--d", `${30 + (i % 3) * 8}px`);
      box.append(spark);
    }
    return box;
  }

  function popPoints(gain) {
    const score = $("#play-score");
    score.classList.remove("bump");
    void score.offsetWidth;  // restart the animation
    score.classList.add("bump");
    const pop = el("span", { class: "pop", "aria-hidden": "true" }, `+${gain}`);
    score.append(pop);
    setTimeout(() => pop.remove(), 1000);
  }

  function renderFeedback() {
    const r = game.round;
    const card = r.cards[r.i];
    const c = r.checked;
    const scam = card.truth === "scam";
    const last = r.i + 1 >= r.cards.length;
    const kids = [el("div", { class: `fb-head ${r.wasRight ? "right" : "wrong"}` },
      el("span", { class: "fb-icon", "aria-hidden": "true" }, drawnMark(r.wasRight), r.wasRight ? burst() : null),
      el("div", { class: "fb-words" },
        el("div", { class: "fb-title", tabindex: "-1" }, t(r.wasRight ? "fb_right" : "fb_wrong")),
        el("div", { class: "fb-truth" }, scam ? tr(c.headline) : t("fb_real")),
        r.wasRight && r.combo >= 3 ? el("span", { class: "combo" }, icon("local_fire_department"), fmt(t("combo"), { n: r.combo })) : null))];
    if (scam) {
      kids.push(el("p", { class: "fb-label" }, t("fb_clues")),
        el("ul", { class: "reasons" }, c.reasons.map((x) => el("li", { class: x.hard ? "hard" : null }, el("span", {}, tr(x.text))))));
      const first = trList(c.actions)[0];
      if (first) kids.push(el("p", { class: "fb-label" }, t("fb_remember")), el("div", { class: "fb-tip" }, first));
    } else {
      kids.push(el("p", { class: "fb-label" }, t("fb_remember")), el("div", { class: "fb-tip" }, t("fb_real_tip")));
    }
    kids.push(el("button", { type: "button", class: "primary big", onclick: nextCard },
      t(last ? "see_score" : "next_card"), icon(last ? "emoji_events" : "arrow_forward")));
    $("#feedback").replaceChildren(...kids);
  }

  function speakCard() {
    const r = game.round;
    if (!voice.auto || !r) return;
    const card = r.cards[r.i];
    speak(card.text, card.lang === "hi" ? "hi" : "en");
  }

  function nextCard() {
    const r = game.round;
    if (!r || r.leaving) return;
    if (r.i + 1 >= r.cards.length) { finishRound(); return; }
    const deal = () => {
      r.leaving = false;
      r.i++;
      r.answered = false;
      r.checked = null;
      r.counted = false;
      renderPlay();
      window.scrollTo({ top: 0 });
      speakCard();
    };
    if (reduceMotion()) { deal(); return; }
    // the answered card flies off towards the answer it was, then the next one is dealt
    r.leaving = true;
    $("#feedback").classList.add("leaving");
    $("#msg-card").classList.add(r.cards[r.i].truth === "scam" ? "fly-scam" : "fly-real");
    window.scrollTo({ top: 0, behavior: "smooth" });
    setTimeout(deal, 260);
  }

  function finishRound() {
    const r = game.round;
    const s = game.state;
    if (r.daily) {
      s.dailyDay = today();
      if (r.right) { s.points += 20; r.points += 20; }  // today's message, answered right: the bonus
    }
    s.rounds++;
    s.best = Math.max(s.best, r.right);
    touchStreak();
    const lv = levelOf(s.points);
    r.levelUp = lv.n > r.levelBefore ? lv.n : 0;
    saveGame();
    go("game-done", { focus: "#done-title", render: () => {
      renderDone();
      if (voice.auto) speak(joinSpoken([$("#done-title").textContent, $("#done-sub").textContent]));
    } });
    if (r.right === r.cards.length && r.cards.length > 1) setTimeout(confetti, 450);  // once the screen has arrived
    vibrate(r.newBadges.length || r.levelUp ? [20, 40, 20, 40, 60] : 20);
  }

  function renderDone() {
    const r = game.round;
    if (!r) return;
    const n = r.right;
    const total = r.cards.length;
    $("#done-ring").replaceChildren(ring(156, 16, n / total, "green", `${n}/${total}`));
    countUp($("#done-ring .ring-num span"), n, { ms: 900, format: (v) => `${v}/${total}` });
    $("#done-title").textContent = t(n === total ? "done_perfect" : n / total >= 0.6 ? "done_good" : "done_ok");
    $("#done-sub").textContent = fmt(t("done_score"), { n, total });
    $("#done-points").replaceChildren(icon("star"), el("span", { class: "num" }, fmt(t("done_points"), { n: r.points })));
    countUp($("#done-points .num"), r.points, { ms: 1100, format: (v) => fmt(t("done_points"), { n: v }) });
    const awards = r.newBadges.map((id, i) => {
      const a = el("div", { class: "award" }, medal(id, 1),
        el("div", { class: "award-words" }, el("small", {}, t("new_badge")), el("b", {}, t(`badge_${id}`)), el("span", {}, t(`badge_${id}_d`))));
      a.style.animationDelay = `${0.25 + i * 0.15}s`;
      return a;
    });
    if (r.levelUp) {
      awards.unshift(el("div", { class: "award level" },
        el("div", { class: "twinkle-wrap" }, ring(52, 6, 1, "", String(r.levelUp)),
          reduceMotion() ? null : el("span", { class: "twinkles", "aria-hidden": "true" }, el("i", {}), el("i", {}), el("i", {}), el("i", {}))),
        el("div", { class: "award-words" }, el("small", {}, `${t("level_label")} ${r.levelUp}`), el("b", {}, fmt(t("level_up"), { name: t(`lvl_${r.levelUp}`) })))));
    }
    $("#done-badges").replaceChildren(...awards);
    $("#btn-game-share").hidden = !canShare;
  }

  // A burst of confetti for a perfect round (not with reduced motion).
  function confetti() {
    if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const colors = ["#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#007AFF", "#AF52DE", "#FF2D55"];
    const box = el("div", { class: "confetti", "aria-hidden": "true" });
    for (let i = 0; i < 70; i++) {
      const bit = el("i", {});
      bit.style.left = `${Math.random() * 100}%`;
      bit.style.background = colors[i % colors.length];
      bit.style.animationDuration = `${1.8 + Math.random() * 1.6}s`;
      bit.style.animationDelay = `${Math.random() * 0.5}s`;
      bit.style.transform = `rotate(${Math.random() * 180}deg)`;
      box.append(bit);
    }
    document.body.append(box);
    setTimeout(() => box.remove(), 4200);
  }

  // Swipe the card towards an answer: towards Scam or towards Real, whichever side the button is on.
  function setupSwipe() {
    const box = $("#msg-card");
    let start = null;
    let dx = 0;
    const rtl = () => document.documentElement.dir === "rtl";
    const toScam = (d) => (rtl() ? d > 0 : d < 0);
    const stamps = (k, scam) => {
      const a = $(".stamp.s-scam", box);
      const b = $(".stamp.s-real", box);
      if (a) a.style.opacity = scam ? String(k) : "0";
      if (b) b.style.opacity = scam ? "0" : String(k);
    };
    box.addEventListener("pointerdown", (e) => {
      if (!game.round || game.round.answered || e.button > 0) return;
      start = { x: e.clientX, id: e.pointerId };
      dx = 0;
      box.classList.remove("settle");
      box.classList.add("dragging");
    });
    box.addEventListener("pointermove", (e) => {
      if (!start || e.pointerId !== start.id) return;
      dx = e.clientX - start.x;
      if (Math.abs(dx) > 6 && !box.hasPointerCapture(e.pointerId)) box.setPointerCapture(e.pointerId);
      box.style.transform = `perspective(900px) translateX(${dx}px) rotateY(${(dx / 14).toFixed(1)}deg) rotate(${(dx / 30).toFixed(1)}deg)`;
      stamps(Math.min(1, Math.abs(dx) / 90), toScam(dx));
    });
    const end = () => {
      if (!start) return;
      start = null;
      box.classList.remove("dragging");
      box.classList.add("settle");
      if (Math.abs(dx) > 90) { answer(toScam(dx)); return; }
      box.style.transform = "";
      stamps(0, false);
    };
    box.addEventListener("pointerup", end);
    box.addEventListener("pointercancel", end);
  }
  setupSwipe();

  $("#btn-play").addEventListener("click", () => startRound(false));
  $("#btn-ans-scam").addEventListener("click", () => answer(true));
  $("#btn-ans-real").addEventListener("click", () => answer(false));
  $("#btn-play-quit").addEventListener("click", () => { stopSpeaking(); game.round = null; go("learn"); });
  $("#btn-play-again").addEventListener("click", () => startRound(false));
  $("#btn-game-share").addEventListener("click", async () => {
    const r = game.round;
    if (!r) return;
    const lines = [fmt(t("share_game_text"), { n: r.right, total: r.cards.length })];
    if (STANDALONE) lines.push(`${location.origin}${location.pathname}`);
    const text = lines.join("\n");
    if (navigator.share) {
      try { await navigator.share({ text }); } catch { /* the person closed the share sheet */ }
      return;
    }
    location.href = `whatsapp://send?text=${encodeURIComponent(text)}`;
  });

  // ---------------------------------------------------------------- language, health, offline cache
  $("#lang-toggle").addEventListener("click", () => { openLangSheet(); });
  $("#lang-close").addEventListener("click", closeLangSheet);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#lang-sheet").hidden) closeLangSheet(); });

  async function loadHealth() {
    try {
      const h = await api("/api/health");
      state.health = h;
      const fraud = (h.packs || []).find((p) => p.name === "fraud");
      $("#pack-version").textContent = fraud ? `fraud pack v${fraud.version}` : "";
      $("#node-pill").title = `Sahayak node ${h.version}`;
      voice.nodeOk = Boolean(h.voice && h.voice.tts && (h.voice.tts.hi || []).length);
      renderVoiceStatus();
    } catch (e) {
      if (!(e instanceof NodeUnreachable)) return;
      setNodeless(true);  // away from the node: say so, and show the packs this phone checks with
      loadLocal().then(() => {
        const fraud = local.packs.find((p) => p.name === "fraud");
        $("#pack-version").textContent = fraud ? `fraud pack v${fraud.version}` : "";
      }).catch(() => {});
    }
  }

  // The service worker keeps the app, the on-phone checker and its packs (browsers allow it only on a
  // secure page: the node's HTTPS address, or the stand-alone build on an HTTPS site).
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register(`${ROOT}sw.js`).catch(() => {});
    // Ask the browser to keep the offline copy when the phone runs short of space. Chrome and Safari decide
    // quietly; Firefox would ask the person, so it is not asked there.
    if (navigator.storage && navigator.storage.persist && !/Firefox\//.test(navigator.userAgent)) {
      navigator.storage.persisted().then((kept) => kept || navigator.storage.persist()).catch(() => {});
    }
  }

  // Deep links: ?lang=en, ?screen=check|benefits, ?demo=<example id>, ?nav=start|<persona id>.
  // A QR code printed on a demo card can open straight to its verdict or benefits result.
  const params = new URLSearchParams(location.search);
  if (params.get("lang") && /^[a-z]{2,3}$/.test(params.get("lang"))) state.lang = params.get("lang");
  if (params.get("theme")) applyTheme(params.get("theme"));  // ?theme=titanium, for a demo; not kept
  applyI18n();
  // A language other than Hindi or English shows once its translation is loaded (cached for offline use).
  if (!isBuiltin(state.lang)) {
    const wanted = state.lang;
    loadLangPack(wanted).then(() => { if (state.lang === wanted) { saveLang(wanted); applyI18n(); } })
      .catch(() => { if (state.lang === wanted) { state.lang = "en"; saveLang("en"); applyI18n(); } });
  }
  setMode("text");
  markScreen("home");
  renderLearnBadge();
  updateNavTitle();
  if (!reduceMotion()) {
    document.body.classList.add("intro-play");
    setTimeout(() => document.body.classList.remove("intro-play"), 1600);
  }
  loadQRExamples();
  Promise.all([loadExamples(), loadNavigator()]).then(() => {
    const demo = examples.find((ex) => ex.id === params.get("demo"));
    const persona = nav.catalog && nav.catalog.demos.find((d) => d.id === params.get("nav"));
    // "Share to Sahayak" from the SMS app (Web Share Target): the shared text opens as a check
    const shared = [params.get("text"), params.get("url")].filter(Boolean).join(" ").trim();
    if (shared) {
      go("check");
      setMode("text");
      $("#msg").value = shared.slice(0, 4000);
      runCheck();
    } else if (demo) useExample(demo);
    else if (persona) navDemo(persona);
    else if (params.get("qr")) {  // ?qr=<example id>: a printed demo card's QR opens its check
      setMode("qr");
      const ex = ((local.demo || {}).qr_examples || []).find((x) => x.id === params.get("qr"));
      if (state.nodeless) { if (ex) checkQR(null, ex.payload); } else {
        fetch(`/api/demo/qr/${encodeURIComponent(params.get("qr"))}`).then((r) => (r.ok ? r.blob() : null)).then((b) => b && checkQR(b));
      }
    }
    else if (params.get("answers")) {
      try {
        const raw = params.get("answers").replace(/-/g, "+").replace(/_/g, "/");
        navDemo({ answers: JSON.parse(decodeURIComponent(escape(atob(raw)))) });
      } catch { go("benefits"); }
    }
    else if (params.get("nav") === "start") { navReset(); navNext(); }
    else if (params.get("play")) startRound(params.get("play") === "daily");
    else if (params.get("screen")) go(params.get("screen"));
  });
  if (STANDALONE) setNodeless(true); else loadHealth();
  // Load the on-phone checker in the background, so it is ready (and kept by the service worker) before
  // the person walks away from the node.
  setTimeout(() => loadLocal().catch(() => {}), 1500);
  if ("speechSynthesis" in window) window.speechSynthesis.getVoices();  // warm the voice list
})();

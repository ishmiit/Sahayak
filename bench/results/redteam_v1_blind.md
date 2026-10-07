# Blind red-team set v1

182 messages (118 scams, 64 genuine) written on 6–7 Oct 2026 by a separate AI model working blind (it never saw Sahayak's code, rules, packs or test sets), from 2025–26 scam advisories (I4C, police, banks, news). The genuine messages are deliberately hard: real OTPs for a delivery agent, the government's own 'there is no digital arrest' message, bank alerts, a gas-booking code. 15 scams and 5 genuine messages are in Indian languages Sahayak does not read yet (Tamil, Telugu, Bengali, Marathi, Malayalam, Gujarati, Kannada, Punjabi, Odia, Urdu). Scored once on 2026-10-07, on fraud pack 1.5.0, before anyone on the team read the messages. Reproduce: `python bench/redteam/build_redteam_v1.py`, `python bench/eval_redteam_v1.py --report`.

## First run (the numbers to quote)

A scam counts as caught when Sahayak says Scam or Suspicious. "Not checked" means Sahayak said it could not read the language and gave the safe-default advice instead of a verdict.

| | Scams caught | Scams missed | Scams not checked | Genuine flagged (false alarm) | Genuine not checked |
| --- | --- | --- | --- | --- | --- |
| Sahayak, Hindi, English, Hinglish | 92 / 103 (89%) (95% CI 82–94%) | 11 | 0 | 14 / 59 (24%) (95% CI 15–36%) | 0 |
| Keyword blocklist, same messages | 51 / 103 (50%) | 52 | – | 25 / 59 (42%) | – |
| Sahayak, other Indian languages | 5 / 15 (33%) | 0 | 10 | 1 / 5 (20%) | 4 |
| Sahayak, all 182 | 97 / 118 (82%) | 11 | 10 | 15 / 64 (23%) | 4 |
| Keyword blocklist, all | 54 / 118 (46%) | 64 | – | 27 / 64 (42%) | – |

By input type (Sahayak, all languages):

| Input | Scams caught | Genuine flagged |
| --- | --- | --- |
| call | 17 / 25 (68%) | 5 / 8 (62%) |
| qr | 8 / 8 (100%) | 0 / 4 (0%) |
| text | 72 / 85 (85%) | 10 / 52 (19%) |

Sahayak's wrong answers on the first run (missed scams and false alarms):

- rt1-013 (genuine, relative_money_request, en, call; read as suspicious): "My brother called from his usual number this morning. His salary is late this month and he asked if I could lend him ₹5,000 for his son's school trip;"
- rt1-015 (scam, refund_sent_by_mistake, hi, call; read as no_signs): 'एक आदमी का फोन आया, बोला मैं आपके पापा का पुराना दोस्त हूँ, उन्हें पैसे भेजने हैं पर उनका नंबर नहीं लग रहा, आपके खाते में भेज देता हूँ। फिर ₹20,000 जम'
- rt1-026 (scam, courier_customs, hi, text; read as no_signs): 'डेल्हीवरी: पता अधूरा होने के कारण आपका पार्सल डिलीवर नहीं हो सका। दोबारा डिलीवरी के लिए केवल ₹5 शुल्क देकर पता अपडेट करें: dlvry-in . help/pay (स्पेस '
- rt1-028 (genuine, lpg_delivery_code, hinglish, call; read as scam): 'Gas agency se call aaya ki kal cylinder aayega, ₹853 ready rakhna, aur jab cylinder mil jaye tab delivery wale ko SMS wala DAC code bata dena.'
- rt1-038 (genuine, awareness, ta, text; read as suspicious): "தமிழ்நாடு காவல்துறை சைபர் குற்றப் பிரிவு: 'டிஜிட்டல் கைது' என்று எதுவும் இல்லை. காவல்துறை, CBI அல்லது சுங்கத் துறை யாரையும் வீடியோ அழைப்பில் கைது செய்"
- rt1-056 (genuine, power_cut_notice, hinglish, call; read as suspicious): 'Bijli office se lineman ka phone aaya ki kal subah 10 se 2 baje tak hamare area me maintenance ke liye light nahi rahegi. Bas batane ke liye call kiya'
- rt1-065 (genuine, debit_alert, en, text; read as suspicious): 'Sent Rs.640.00\nFrom HDFC Bank A/C *4417\nTo ANNAPURNA SWEETS\nOn 06/10/26\nRef 627914258803\nNot You?\nCall 18002586161/SMS BLOCK UPI to 7304412958'
- rt1-071 (scam, rent_property_advance, en, call; read as no_signs): "I found a flat on a Facebook group. The owner says he's a Navy officer posted in Vizag so he can't show it, and the guard doesn't have keys. He sent p"
- rt1-084 (scam, matrimonial, hi, text; read as no_signs): 'नमस्ते, मैं स्नेहा, सिंगापुर में रहती हूँ। मैट्रिमोनी साइट पर आपकी प्रोफाइल देखी, आप बहुत सुलझे हुए लगे। मेरे मामा जी एक गोल्ड ट्रेडिंग प्लेटफॉर्म चला'
- rt1-094 (scam, sextortion, hinglish, text; read as no_signs): 'Tumhari video call ki recording mere paas hai 😈 2 ghante me ₹21,000 bhejo warna tumhare saare Facebook friends aur family group me bhej dungi. Upar sc'
- rt1-100 (scam, credit_card_otp, en, call; read as no_signs): "A very polite lady from my bank's credit card department called. She knew my name and the last 4 digits of my card. She said I'm eligible for a free l"
- rt1-111 (genuine, shop_promotion, hinglish, text; read as suspicious): 'Gupta Garments, Sadar Bazar 🪔 Diwali Dhamaka! ₹2,000 ki kharidari par lucky draw coupon FREE. Bumper inaam: Scooty, LED TV, mixer. Draw 6 Nov ko dukaa'
- rt1-120 (scam, pilgrimage_booking, en, text; read as no_signs): 'Kedarnath Heli Service (Pawan Hans authorised agent): Last 4 seats for 18 Oct from Phata helipad, ₹6,200 per person (return). Book now by paying 50% a'
- rt1-124 (genuine, delivery_otp, en, call; read as scam): 'The Flipkart delivery boy called to say he was at my gate. I went down, he handed me the parcel and then asked me to tell him the 4-digit OTP that cam'
- rt1-125 (genuine, csc_camp, hi, text; read as scam): 'ग्राम पंचायत रामपुर: शनिवार 10 अक्टूबर को पंचायत भवन में आयुष्मान कार्ड, ई-श्रम कार्ड और वय वंदना कार्ड बनाने का कैंप सुबह 10 से 4 बजे तक लगेगा। आधार '
- rt1-128 (scam, fake_job_fee, en, call; read as no_signs): "A lady called saying she's from an airline recruitment agency and I've been selected for an airport ground staff job at Delhi airport, salary ₹32,000."
- rt1-134 (genuine, job_interview, en, text; read as scam): 'Dear Anjali, you have been shortlisted for the Customer Support Associate (Hindi/English) role at Orbit BPO Services. Walk-in interview: Fri 9 Oct 202'
- rt1-137 (genuine, credit_alert, en, text; read as scam): 'ICICI Bank Acct XX902 credited with Rs 32,450.00 on 01-Oct-26; NEFT-SUNRISE AUTO COMPONENTS PVT LTD-SALARY SEP. Avl Bal Rs 36,118.20. To report a disp'
- rt1-149 (genuine, relative_money_request, hi, text; read as scam): 'माँ, मकान मालिक को 5 तारीख तक किराया देना है, ₹6,000 मेरे SBI वाले खाते में डाल देना जब टाइम मिले। रात को ऑफिस के बाद फोन करता हूँ।'
- rt1-154 (scam, fake_charity, en, text; read as no_signs): '🙏 Please help 4-year-old Aarav fighting blood cancer at Tata Memorial, Mumbai. He needs ₹18 lakh for a bone-marrow transplant in 3 days. Every ₹100 co'
- rt1-157 (scam, call_forwarding, en, call; read as no_signs): "A courier delivery guy called and said he's near my house with a Blue Dart parcel but the address is incomplete. He said to confirm delivery I just ha"
- rt1-158 (scam, rent_property_advance, hi, text; read as no_signs): 'अयोध्या राम मंदिर से सिर्फ 3 किमी पर रजिस्ट्री वाला प्लॉट, मात्र ₹4.5 लाख में। आज ₹21,000 टोकन देकर बुक करें, कल से रेट बढ़ जाएंगे। साइट विज़िट की ज़र'
- rt1-163 (genuine, relative_money_request, hinglish, text; read as suspicious): 'Bhaiya, college fees ki last date 10 tarikh hai, ₹4,500 bhej doge? Wahi purane account me jo papa use karte hain. Koi jaldi nahi, kal tak chalega. Gha'
- rt1-171 (genuine, shop_promotion, en, text; read as scam): "Big Festive Sale is LIVE! Up to 80% off on fashion + extra 10% instant discount on select bank cards. Hurry, today's deals end at midnight. Shop now: "
- rt1-176 (genuine, job_interview, hinglish, text; read as suspicious): 'Hi Rahul, Swastik Motors se Pooja bol rahi hoon. Aapne mechanic helper post ke liye apply kiya tha. Kal subah 11 baje workshop pe aa jaana - Bhosari M'
- rt1-177 (genuine, job_interview, hinglish, call; read as suspicious): 'Ek ladki ka call aaya Orbit BPO se, boli maine Naukri pe jo apply kiya tha uske liye interview hai Thursday ko 11 baje, Sector 62 wale office me. Resu'

## Post-freeze log

- 7 Oct, fraud pack 1.6.0: fixes for the first run's errors (a bank's SMS-BLOCK footer beside its toll-free number, calm family requests, the writer's own bank, the delivery code given at the door, invitations to come in person or bring papers, power cuts for maintenance, discounts on bank cards, Hinglish and Hindi blackmail, gold-trading pitches, donation appeals to a personal UPI ID, job fees, money 'sent by mistake'). Each change was measured on every set before it was kept: 0 lost catches, 0 new false alarms. Two diagnosis groups (USSD call forwarding; spaced-out links and booking advances) did not finish and their misses remain.
- 7 Oct, fraud pack 1.7.0: a call-forwarding code (*401*, **21*, also said aloud: rt1-157), an advance or token for something you cannot see first (rt1-071 rent, rt1-120 helicopter seats, rt1-158 plot), a fee through a link for a failed delivery and a link split with spaces (rt1-026), and 'confirmation code' read out on a call (rt1-100). Each rule was also tested on new wordings and genuine look-alikes (tests/test_signals_1_7.py) and measured on every set: no catch lost, no new false alarm.

Re-scored 2026-10-07 on fraud pack 1.7.0: Hindi/English/Hinglish scams caught 103 / 103 (100%), genuine flagged 0 / 59 (0%). These messages informed the fixes, so the re-score is not an unbiased test; the first run stays the number to quote.

**What this does not show.** The messages are realistic but written for the test, not received by real people; real messages collected with consent (ScamBench v1) and the field morning are the next steps. A "could not check" protects a person from a false green, but it does not protect them from the scam: reading more languages is on the roadmap.

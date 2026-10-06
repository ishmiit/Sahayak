"""Build the red-team set v0 (bench/redteam/redteam_v0.jsonl): messages written to get past Sahayak.

Each scam takes a known scam and disguises it with one evasion technique (hidden characters,
spaced or look-alike letters, links written out in words, a warning wrapped around the ask, a
spoofed bank sender, ...). The genuine messages are hard negatives: real kinds of message that
share words with scams (OTPs meant for a delivery agent, bank awareness SMS, shop offers on a
short link). Written by the team on 6 Oct 2026, before the checker was run on any of them; the
first run is the number to quote (see bench/results/redteam_v0.md).

Usage: python bench/build_redteam.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "bench" / "redteam" / "redteam_v0.jsonl"
ZW = "​"  # zero-width space
ZWJ = "‍"  # zero-width joiner

# (technique, lang, text, sender)
SCAMS = [
    # hidden characters inside the words the checks look for
    ("zero_width", "en", f"Your SBI account is blocked. Share the O{ZW}T{ZW}P sent to your phone to unblock it immediately.", None),
    ("zero_width", "en", f"Dear customer, your K{ZW}Y{ZW}C has expired. Update now at http://sbi-kyc{ZWJ}-update.xyz or your account will be closed.", None),
    ("zero_width", "hi", f"आपका खाता बंद हो जाएगा। तुरंत ओ{ZW}टी{ZW}पी बताएं ताकि हम इसे चालू रख सकें।", None),
    # letters spaced out, dotted or hyphenated
    ("spaced_letters", "en", "URGENT: your account will be suspended today. Tell our officer the O T P you just received to stop it.", None),
    ("spaced_letters", "hinglish", "Bhai bank se bol raha hu, aapka K-Y-C pending hai. Jo o.t.p aaya hai woh bata do, abhi update kar dete hai.", None),
    ("spaced_letters", "en", "Your electricity will be cut tonight at 9.30 pm as your last bill was not updated. Call our officer at 9 8 7 6 5 4 3 2 1 0 immediately.", None),
    # digits for letters
    ("leetspeak", "en", "Y0ur acc0unt is bl0cked. Share the 0TP to verify y0ur identity and rest0re access.", None),
    ("leetspeak", "en", "KYC upd4te pending! Click http://kyc-upd4te.top/login within 24 hours or your bank account will be fr0zen.", None),
    # full-width and look-alike letters
    ("lookalike_letters", "en", "Your ＳＢＩ account KYC has expired. Share the ＯＴＰ with our executive to keep it active.", None),
    ("lookalike_letters", "en", "Your НDFС Bank account will be blocked. Verify now: http://hdfc-verify.online", None),  # Cyrillic Н and С
    # links written so they do not look like links
    ("link_in_words", "en", "Your PAN is not linked, your account will be blocked today. Visit sbi-pan-link dot xyz to update now.", None),
    ("link_in_words", "en", "Claim your Rs 5,000 cashback before midnight: hxxp://cashback-paytm[.]top/claim", None),
    ("link_in_words", "hinglish", "Aapka bijli connection aaj raat kat jayega. Turant update karo: bijli-bill-update (dot) site", None),
    ("link_shouted", "en", "FINAL NOTICE: YOUR KYC HAS EXPIRED. UPDATE AT WWW.SBI-KYC-VERIFY.XYZ OR ACCOUNT WILL BE BLOCKED.", None),
    # links that put a real bank's name in front of a scam domain
    ("official_name_in_link", "en", "Your net banking is locked. Unlock it here: https://onlinesbi.sbi.secure-login.xyz/unlock", None),
    ("official_name_in_link", "en", "Dear customer, complete your KYC at https://www.sbi.co.in@kyc-update.top to avoid suspension.", None),
    ("official_name_in_link", "en", "Income tax refund of Rs 15,490 approved. Submit bank details at https://incometax.gov.in.refund-portal.site", None),
    ("punycode", "en", "Your account needs re-verification. Login at https://xn--sbi-yno-9xa.com/verify within 2 hours.", None),
    # short links only
    ("short_link", "en", "Congratulations! You have won an iPhone 16 in the Flipkart lucky draw. Claim: https://bit.ly/3fKx9Qp", None),
    ("short_link", "hinglish", "Aapka PM Kisan ka paisa ruka hua hai. Yahan details bharo: https://tinyurl.com/pmk-2026", None),
    # no link at all: call this number
    ("callback_only", "en", "Rs 49,999 has been debited from your account for an iPhone order. If not done by you, call our helpdesk at 8240012345 immediately to cancel.", None),
    ("callback_only", "hi", "आपके खाते से ₹25,000 कटने वाले हैं। यह आपने नहीं किया तो तुरंत 7003456789 पर कॉल करें।", None),
    # calm, polite, no urgency words
    ("polite", "en", "Good afternoon sir. This is Priya from your bank's customer desk. For the annual verification, kindly share the 6 digit number you received a moment ago. Thank you for your cooperation.", None),
    ("polite", "en", "Hello madam, your SBI reward points worth Rs 7,250 are ready to redeem. You can redeem them on our page at sbi-rewardz.in at your convenience.", None),
    # the ask wrapped in a warning, so it reads like advice
    ("advisory_wrapped", "en", "SBI never asks for your OTP. For your safety our verification officer will call you shortly; tell him the code you receive so he can confirm it is really you.", None),
    ("advisory_wrapped", "en", "Beware of fraudsters! To protect your account from fraud, update your KYC at http://sbi-secure-kyc.xyz today.", None),
    ("advisory_wrapped", "hi", "सावधान! ठगों से बचने के लिए अपना खाता सुरक्षित करें। हमारे अधिकारी को आया हुआ ओटीपी बताएं।", None),
    ("not_a_scam_claim", "en", "This is not a scam, it is an official RBI scheme. Pay the processing fee of Rs 999 to receive your Rs 50,000 grant.", None),
    ("not_a_scam_claim", "hinglish", "Ye fraud nahi hai bhai, genuine company hai. Bas 1500 registration fee bhejo aur ghar baithe 30,000 mahina kamao.", None),
    # a spoofed bank header on a scam
    ("spoofed_sender", "en", "Your account KYC has expired. Update immediately at http://sbi-kyc-renew.top or your account will be frozen.", "VM-SBIBNK"),
    ("spoofed_sender", "en", "Dear customer, to stop an unauthorised transaction of Rs 18,000, share the OTP sent to you with our fraud team when they call.", "AD-HDFCBK"),
    # a harmless start, the ask at the end
    ("padded", "en", "Happy Diwali to you and your family! May this festival bring joy and prosperity. Also, your bank KYC is pending, please share the OTP you get today so we can complete it.", None),
    ("padded", "hi", "नमस्ते जी, आशा है आप और परिवार स्वस्थ हैं। आज मौसम बहुत अच्छा है। आपका बिजली कनेक्शन आज रात काटा जाएगा, तुरंत 9876543210 पर संपर्क करें।", None),
    # words broken across lines, as a forwarded screenshot text often is
    ("line_breaks", "en", "Your account will be blo\ncked. Share the O\nTP immediately to stop it.", None),
    # emoji everywhere
    ("emoji", "en", "🎉🎉 CONGRATS 🎉 You won ₹25,00,000 in KBC lottery 💰💰 Pay ₹12,500 tax 👉 to claim 📞 WhatsApp 9876501234", None),
    ("emoji", "hinglish", "🚨 Aapka account BLOCK 🔒 hone wala hai 🚨 turant OTP 🔢 bhejo ✅ warna paisa 💸 gaya", None),
    # Hindi written with English words in Devanagari, and romanised Hindi
    ("devanagari_english", "hi", "डियर कस्टमर, आपका केवाईसी एक्सपायर हो गया है। अपडेट करने के लिए लिंक पर क्लिक करें: http://kyc-update.click", None),
    ("devanagari_english", "hi", "आपका पार्सल कस्टम्स में सीज़ हो गया है, उसमें ड्रग्स मिले हैं। सीबीआई ऑफिसर से बात करने के लिए 1 दबाएं।", None),
    ("romanised_variants", "hinglish", "Sir aapka khaata band hone wala hai. Jo otp aya hai wo batao jaldi, varna kal se paisa nahi nikal paoge.", None),
    ("romanised_variants", "hinglish", "Mubarak ho! Aapne 25 lakh ki lottery jeeti hai. Inaam lene ke liye 15000 processing charge jama karein.", None),
    # code words for the OTP
    ("otp_synonym", "en", "Our system sent you a 6 digit verification number just now. Please read it out to our agent to complete your account update.", None),
    ("otp_synonym", "hinglish", "Aapke phone pe ek message aaya hoga 6 number wala, woh number mujhe bata do, aapka refund process ho jayega.", None),
    # scams the pack has fewer words for
    ("novel_task_job", "en", "Part-time job: like YouTube videos and earn Rs 3,000 a day from home. Message our HR on Telegram @hr_priya_jobs to start today.", None),
    ("novel_task_job", "hinglish", "Ghar baithe kaam: sirf Google Maps pe review do aur har review ka 150 rupaye pao. Abhi WhatsApp karo 9123456780.", None),
    ("novel_olx_buyer", "en", "Hi, I am in the Army, posted far away. I will buy your sofa for your full price. I am sending a QR code, scan it and enter your UPI PIN to receive the money.", None),
    ("novel_crypto", "en", "Invest Rs 10,000 in our crypto trading group and get Rs 1 lakh in 7 days, guaranteed returns. Join: t.me/crypto_profit_india", None),
    ("novel_sim_swap", "en", "Your SIM card will be deactivated in 2 hours due to pending e-KYC. Call 9988776655 and press 1 to re-verify.", None),
    ("novel_electricity_app", "hinglish", "Bijli bill update nahi hua, aaj raat 9:30 baje connection kat jayega. Turant hamare officer ko call karo aur 'Electricity Update' app download karo.", None),
    ("novel_family_voice", "hi", "पापा मैं मुसीबत में हूँ, पुलिस ने पकड़ लिया है। ये मेरे दोस्त का नंबर है, जल्दी 50,000 इस UPI पर भेज दो: rahulhelp@ybl", None),
    ("novel_sextortion", "en", "I have your private video call recording. Pay Rs 20,000 to this UPI or I will send it to all your contacts and family.", None),
    ("novel_courier_fee", "en", "India Post: your parcel is held at the warehouse due to an incomplete address. Pay Rs 25 redelivery fee at indiapost-redelivery.top within 12 hours.", None),
    ("novel_traffic_challan", "en", "Your vehicle has a pending traffic challan of Rs 2,000. Pay now to avoid court action: https://echallan-parivahan.online/pay", None),
]

GENUINE = [
    ("genuine_otp", "en", "482913 is your OTP for the transaction of Rs 1,250 at Amazon. Valid for 5 minutes. Do not share it with anyone. -SBI", "VM-SBIBNK"),
    ("genuine_otp", "hi", "आपका ओटीपी 739104 है। यह 10 मिनट तक मान्य है। किसी के साथ साझा न करें। -HDFC Bank", "AD-HDFCBK"),
    ("genuine_delivery_otp", "en", "Your Flipkart order is out for delivery. Share OTP 5521 with the delivery agent only when you receive the package.", "VM-FLPKRT"),
    ("genuine_delivery_otp", "hinglish", "Aapka Swiggy order aa raha hai. Delivery partner ko OTP 2280 bata dena jab order mil jaye.", "JD-SWIGGY"),
    ("genuine_awareness", "en", "RBI says: Never share your OTP, PIN or card details with anyone, not even bank staff. Report fraud on 1930 or cybercrime.gov.in.", "VM-RBISAY"),
    ("genuine_awareness", "hi", "सावधान! बैंक कभी भी फोन पर ओटीपी या पिन नहीं माँगता। धोखाधड़ी की शिकायत 1930 पर करें।", "VM-SBIBNK"),
    ("genuine_awareness", "en", "Digital arrest is a scam. No police, CBI or customs officer arrests anyone over a video call. If you get such a call, hang up and dial 1930.", None),
    ("genuine_kyc_official", "en", "Dear customer, your KYC is due for periodic update. Please visit your nearest branch or update through the YONO app. Ignore if already done. -SBI", "VM-SBIBNK"),
    ("genuine_txn_alert", "en", "Rs 2,500.00 debited from A/c XX4421 on 05-10-26 to VPA shyamkirana@okaxis. Not you? Call 1800 1234 or SMS BLOCK to 9223008333. -SBI", "VM-SBIBNK"),
    ("genuine_txn_alert", "hi", "आपके खाते XX7781 में ₹6,000 जमा हुए: PM-KISAN किस्त। -बैंक ऑफ़ बड़ौदा", "VM-BOBTXN"),
    ("genuine_govt", "en", "Dear farmer, the 21st instalment of PM-KISAN has been released. Check your status at pmkisan.gov.in", "VM-PMKISN"),
    ("genuine_govt", "hi", "प्रिय लाभार्थी, आपका आयुष्मान कार्ड तैयार है। डाउनलोड करें: beneficiary.nha.gov.in", "VM-NHAGOV"),
    ("genuine_short_link_promo", "en", "Diwali sale at Sharma Electronics, Lajpat Nagar: 20% off on all fans and coolers till Sunday. Catalogue: https://bit.ly/sharma-diwali", "VM-SHRMEL"),
    ("genuine_personal_money", "hinglish", "Bhai kal ki movie ke tickets ke 450 bhej dena jab time mile, mera UPI wahi hai.", None),
    ("genuine_personal", "hi", "बेटा, कल सुबह 10 बजे डॉक्टर के पास जाना है, याद से आ जाना।", None),
    ("genuine_personal", "en", "Hi, the building gate code changed to 4521 from today. Please don't share it with outsiders. - Society office", None),
    ("genuine_bill", "en", "Your electricity bill of Rs 1,340 for September is generated. Due date 15-10-2026. Pay via your bank app or at the nearest bill counter.", "VM-BSESRJ"),
    ("genuine_upi_request", "en", "Ramesh Kumar has requested Rs 250 for 'dinner split' on Google Pay. Pay only if you know Ramesh.", None),
    ("genuine_courier", "en", "India Post: your Speed Post article EK123456789IN is out for delivery today. Track at indiapost.gov.in", "VM-INDPST"),
    ("genuine_job", "en", "Thank you for applying to the Data Entry Operator post at Sharma & Co. Your interview is on 10 Oct at 11 am at our Karol Bagh office. No fee is charged at any stage.", None),
    ("genuine_insurance", "en", "Your PMJJBY cover of Rs 2 lakh has been renewed for 2026-27; Rs 436 auto-debited from A/c XX4421. -Canara Bank", "VM-CNRBNK"),
    ("genuine_refund", "en", "Refund of Rs 499 for your cancelled order #40213 has been processed to your original payment method. It will reflect in 5-7 working days. -Myntra", "VM-MYNTRA"),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, items in (("scam", SCAMS), ("genuine", GENUINE)):
        for technique, lang, text, sender in items:
            rows.append({"id": f"rt-{len(rows) + 1:03d}", "label": label, "technique": technique, "lang": lang,
                         "text": text, "sender": sender, "source": "team-written red-team v0, 6 Oct 2026"})
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} messages ({len(SCAMS)} scam, {len(GENUINE)} genuine) to {OUT}")


if __name__ == "__main__":
    main()

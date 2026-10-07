# PublicBench v0: real published messages

137 messages (103 scams, 34 genuine) that authorities, banks, courts and fact-checkers have published, collected on 6–7 Oct 2026 by an AI research agent that never saw Sahayak's code, rules or test sets. 107 are word for word; the rest are call scripts told by victims or police, or an outlet's translation. Private names and every phone number were replaced with fictional ones of the same shape. Scored once on 2026-10-07 (fraud pack 1.5.0), before anyone on the team read the messages. Reproduce: `python bench/eval_public_v0.py --report`; sources in `bench/public/`.

## First run (the numbers to quote)

| Messages | Scams caught (95% Wilson CI) | Scams missed | Could not check | Genuine flagged (95% Wilson CI) |
| --- | --- | --- | --- | --- |
| All | 67 / 103 (65%) (55–74%) | 30 | 6 | 11 / 34 (32%) (19–49%) |
| Hindi, English, Hinglish | 67 / 97 (69%) (59–77%) | 30 | 0 | 11 / 34 (32%) (19–49%) |
| Word-for-word only | 53 / 75 (71%) (60–80%) | 22 | 0 | 11 / 32 (34%) (20–52%) |
| Text messages | 52 / 80 (65%) (54–75%) | 22 | 6 | 11 / 34 (32%) (19–49%) |
| Call scripts | 15 / 23 (65%) (45–81%) | 8 | 0 | 0 / 0 (0–0%) |
| Other Indian languages | 0 / 6 (0%) (0–39%) | 0 | 6 | 0 / 0 (0–0%) |
| Dev half (fixes may learn from it) | 39 / 59 (66%) (53–77%) | 16 | 4 | 5 / 14 (36%) (16–61%) |
| Test half (kept unread) | 28 / 44 (64%) (49–76%) | 14 | 2 | 6 / 20 (30%) (15–52%) |
| Keyword blocklist, all | 64 / 103 (62%) | 39 | – | 17 / 34 (50%) |

Sahayak's wrong answers on the first run, dev half only (20 more in the test half are counted above but not listed, so that half stays unread until the fixes are done):

- pub-004 (scam, army_olx_buyer, en, call; read as no_signs): 'The fraudster told me he would make the payment only through a bank account. He sent QR code of Re 1 and asked me to scan it and receive money so that'
- pub-013 (scam, digital_arrest, en, call, verbatim; read as no_signs): 'Hello. This is Bangalore traffic police. An accident report has been filed against you. To know more press zero.'
- pub-015 (scam, digital_arrest, hi, call, verbatim; read as no_signs): 'हेलो अमित, मैं एसीपी राठौर साइबर क्राइम करौल बाग दिल्ली से बोल रहा हूं, आप गंदी फिल्म देखते हैं। अगर मामले को खत्म करना है तो फार्म 31 भरना होगा और उस'
- pub-031 (scam, fake_debit_alert, en, call, verbatim; read as no_signs): 'Hello dear customer. This is a call from Mobiquick pay later. We have got a request for making a transaction of ₹1,429 from an unknown device. If you '
- pub-039 (scam, fake_govt_scheme, hi, text, verbatim; read as no_signs): 'निशुल्क पंजिकरण कीजिए समय अवधि जल्दी ही खत्म होने वाली है। अभी राज्यों मे जिला अनुसार नियुक्ति प्राप्त होगी। योग्यता 10वी 12वी स्नातक टेक्निकल डिप्लोम'
- pub-040 (scam, fake_govt_scheme, hi, text, verbatim; read as no_signs): 'महत्वपूर्ण खबर ! 15 अप्रैल, 2024 से, भारत सरकार का केंद्रीय स्वास्थ्य मंत्रालय 50 से 85 वर्ष की आयु के वरिष्ठ नागरिकों को मुफ्त स्वास्थ्य बीमा प्रदान '
- pub-056 (scam, investment_stock_group, en, text, verbatim; read as no_signs): 'Welcome to the Goldman Sachs Asset Management. This group is founded by Matthew Bradley, creating a learning community for Indian stock enthusiasts. P'
- pub-057 (scam, investment_stock_group, en, text, verbatim; read as no_signs): 'Do you want to invest in the stock market? And what type of stocks do you want to invest in?'
- pub-071 (scam, loan_app, hi, text; read as no_signs): 'छह दिन बीत जाने के बाद, महिला को मैसेज मिला, जिसमें लोन चुकाने के लिए कहा गया। उसने जवाब दिया कि उसके पास इस समय पैसे नहीं है। उसे कुछ दिन चाहिए लेकिन'
- pub-073 (scam, otp_forward_account_takeover, en, text, verbatim; read as no_signs): 'I accidentally sent you a message. Please forward it quickly.'
- pub-080 (scam, prize_lottery_kbc, en, text, verbatim; read as no_signs): 'REF : RBI/0147/14\nDate- 09-08-2026\n\nLETTER OF GUARANTEE\n\nDear\nMr. Ramesh K R\nWe congratulate you for the prize amount of 15,00,000/- your amount will '
- pub-084 (scam, prize_lottery_kbc, hi, text, verbatim; read as no_signs): 'अनुबंध प्रिय ग्राहक तुम्हारा जीवन अच्छा है कि आप 25,00,000 का भुगतान कर सकते हैं, केबीसी JIO विभाग द्वारा कंपनी की राशि और विनियमों का पूरी तरह से उपय'
- pub-088 (scam, rbi_impersonation, en, text, verbatim; read as no_signs): 'To,\nSHRI RAKESH MEHRA\nDate: 13/07/2026\nFrom,\nThe Manager of RBI,\nArun Kundra\nSub:- To pay the tax for releasing the payments.\n\nRespect Sir,\n\nWe are dr'
- pub-089 (scam, relative_emergency, en, call; read as no_signs): 'The scammer, who claimed he was a police officer, told Mr Verma that his 18-year-old son had been caught with a gang of rapists and needed Rs30,000 so'
- pub-098 (scam, sextortion, en, text, verbatim; read as no_signs): 'This is to let you know of the attached court order against your Internet IP traffic by the Indian Intelligence Bureau, Department of Research and Ana'
- pub-100 (scam, sextortion, hi, call; read as no_signs): 'बाद में उस व्यक्ति ने महिला को वीडियो कॉल पर कपड़े उतारने के लिए कहा और उसकी जानकारी के बिना ही उसे रिकॉर्ड कर लिया. फिर, 11 जुलाई को, उसने महिला को फ'
- pub-105 (genuine, bank_notice, en, text, verbatim; read as suspicious): 'Due to scheduled maintenance activity, SBI UPI services will be temporarily unavailable from 00:15 hrs to 01:00 hrs on 04.09.2026 (IST). The activity '
- pub-111 (genuine, electricity_bill, hi, text, verbatim; read as suspicious): 'आपका वर्तमान प्रीपेड बकाया 2000 रुपये है। तीन दिन में भुगतान न करने पर आपकी बिजली कभी भी कट सकती है। बिजली चालू रखने के लिए दिए गए लिंक पर कम से कम 22'
- pub-123 (genuine, income_tax, en, text, verbatim; read as suspicious): 'Dear AAXXXXXXIA, Urgent: Your AY 2026-27 ITR is pending for verification. e-Verify now to avoid any impact on return processing. Ignore if e-Verified.'
- pub-126 (genuine, lpg_booking, en, text, verbatim; read as scam): 'As per the available income tax records, your (or linked family member’s) gross taxable income exceeds the prescribed limit of ₹ 10 lakh. If you wish '
- pub-135 (genuine, security_alert, en, text, verbatim; read as suspicious): 'Dear customer, you have accessed profile section of your internet banking on 16.07.2021 at 17:40pm if not, please change your passwords immediately SB'

## Post-freeze log

- 7 Oct, fraud pack 1.6.0: the blind red team's fixes, plus fixes learned from the DEV half only: fake police and court notices, a fee to 'release' a payment, prize letters, a relative 'arrested' and money to 'clear his name', Hindi blackmail, 'I accidentally sent you a message, forward it', a call asking you to dial the code you received, a QR code named before 'scan it and receive', stock-group openers, and a told call is never a bank alert. A rule that a message asking for nothing counts against a scam was tested and rejected: it lost 8 catches.

Re-scored 2026-10-07 on fraud pack 1.6.0. **Test half (never read, so a fair estimate):** scams caught 28 / 44 (64%) before, 30 / 44 (68%) after; genuine flagged 6 / 20 (30%) before, 6 / 20 (30%) after. All 137 (the dev half informed the fixes): 83 / 103 (81%) caught, 11 / 34 (32%) flagged. The first run stays the number to quote.

**What this does not show.** Published messages are the ones that went viral or reached a fact-checker, so they lean towards well-known scam types; nobody's own inbox is here. The genuine set is small and mostly English (Income Tax, bank and OTP messages). Consented messages from people's own phones (ScamBench v1) and the field morning remain the next steps.

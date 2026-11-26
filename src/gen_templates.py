"""Deterministic synthetic dataset generator for ScamShield BD."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

SEED = 42

BRANDS_ALL = [
    "bKash",
    "Nagad",
    "Rocket",
    "Upay",
    "GP",
    "Robi",
    "Banglalink",
    "Daraz",
    "Pathao",
    "Steadfast",
    "SA Paribahan",
    "Bdjobs",
    "DBBL",
    "City Bank",
]
MFS_BRANDS = ["bKash", "Nagad", "Rocket", "Upay", "DBBL", "City Bank"]
TELECOM_BRANDS = ["GP", "Robi", "Banglalink"]
COURIER_BRANDS = ["Steadfast", "SA Paribahan", "Pathao", "Daraz"]
JOB_BRANDS = ["Bdjobs", "Daraz", "Pathao"]

AMOUNTS = ["500", "1,200", "2,000", "5,000", "10,000", "50,000", "300", "1,500", "25,000"]
TIMES = ["1 hour", "24 hours", "30 minutes", "3 days"]
NAMES = ["Rahim", "Karim", "Nusrat", "Tanvir", "Farhana", "Sakib", "Rafiq", "Tasnim"]
PHONES = ["01XXXXXXXXX", "+8801XXXXXXXXX"]


def _make_link(rng: random.Random, brand: str) -> str:
    slug = brand.lower().replace(" ", "-")
    choices = [
        f"hxxps://{slug}-claim[.]top",
        f"hxxps://bd-verify[.]xyz/{slug}",
        f"hxxp://track-parcel[.]info/{slug}",
        f"hxxps://{slug}-kyc[.]top/verify",
        f"hxxps://reward-{slug}[.]xyz",
    ]
    return rng.choice(choices)


def _fill_slots(rng: random.Random, template: str, brand: str | None = None) -> tuple[str, str]:
    chosen_brand = brand or rng.choice(BRANDS_ALL)
    text = template.format(
        brand=chosen_brand,
        amount=rng.choice(AMOUNTS),
        link=_make_link(rng, chosen_brand),
        phone=rng.choice(PHONES),
        time=rng.choice(TIMES),
        name=rng.choice(NAMES),
        otp=f"{rng.randint(100000, 999999)}",
        order_id=f"{rng.randint(1000, 9999)}",
    )
    return text, chosen_brand.lower().replace(" ", "_")


def _template_bank() -> list[dict]:
    """Return >=10 distinct scenario templates per class (classes 0..5)."""
    return [
        # ---------------- CLASS 0: Legitimate (10 scenarios) ----------------
        {
            "scenario_id": "scen_0_01",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": MFS_BRANDS,
            "variants": [
                "{brand}: Cash-in of Tk {amount} from {phone} successful. Current balance Tk 12,450.",
                "{brand} Cash Out Tk {amount} successful. Fee Tk 15. Balance Tk 4,800.",
                "আপনার {brand} অ্যাকাউন্টে {amount} টাকা ক্যাশ-ইন সফল হয়েছে। বর্তমান ব্যালেন্স ৮,৫০০ টাকা।",
                "Apnar {brand} account e Tk {amount} send money successful hoyeche. Balance Tk 3,200.",
            ],
        },
        {
            "scenario_id": "scen_0_02",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": MFS_BRANDS + TELECOM_BRANDS,
            "variants": [
                "{brand} OTP is {otp} for your login. Do not share this code with anyone.",
                "আপনার {brand} ওটিপি হলো {otp}। এটি কখনোই কারো সাথে শেয়ার করবেন না।",
                "{brand} verification code: {otp}. Valid for {time}. Kauke ei code bolben na.",
                "Never share your {brand} PIN or OTP {otp}. Staff will never ask for it.",
            ],
        },
        {
            "scenario_id": "scen_0_03",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": TELECOM_BRANDS + ["DBBL", "City Bank"],
            "variants": [
                "Reminder: Your {brand} monthly bill of Tk {amount} is due in {time}. Pay via official app.",
                "আপনার {brand} বিল {amount} টাকা আগামী {time} এর মধ্যে পরিশোধ করুন।",
                "Apnar {brand} postpaid bill Tk {amount} due ache. Official app diye pay korun.",
            ],
        },
        {
            "scenario_id": "scen_0_04",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand}: Your order #{order_id} is out for delivery today. Rider {phone} will call.",
                "{brand} আপডেট: আপনার অর্ডার #{order_id} আজ ডেলিভারি করা হবে।",
                "Apnar {brand} parcel #{order_id} Chattogram hub e pouchheche. Branch theke collect korun.",
            ],
        },
        {
            "scenario_id": "scen_0_05",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": ["DBBL", "City Bank"],
            "variants": [
                "{brand} Alert: Tk {amount} debited from A/C **4412 at POS. Available balance Tk 24,100.",
                "{brand}: আপনার অ্যাকাউন্ট থেকে {amount} টাকা ডেবিট হয়েছে। কোনো সমস্যা হলে ১৬২২১-এ কল করুন।",
                "{brand} card transaction Tk {amount} approved. Info er jonno official helpline e jogajog korun.",
            ],
        },
        {
            "scenario_id": "scen_0_06",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Bdjobs"],
            "variants": [
                "{brand}: Your job application for Junior Analyst has been viewed by the employer.",
                "{brand} নোটিশ: আপনার সাক্ষাৎকারের তারিখ আগামী সপ্তাহে নির্ধারণ করা হয়েছে।",
                "Hi {name}, {brand} e apnar profile update hoyeche. Dashboard e check korun.",
            ],
        },
        {
            "scenario_id": "scen_0_07",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": TELECOM_BRANDS,
            "variants": [
                "{brand}: Tk {amount} recharge successful. Validity extended by 30 days.",
                "ধন্যবাদ! আপনার {brand} নম্বরে {amount} টাকা রিচার্জ সফল হয়েছে।",
                "Apnar {brand} number e Tk {amount} recharge hoyeche. Current balance Tk 145.",
            ],
        },
        {
            "scenario_id": "scen_0_08",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Pathao", "Daraz"],
            "variants": [
                "{brand}: Thank you for riding with us. Your trip fare was Tk {amount}.",
                "{brand}: আপনার অর্ডার #{order_id} সফলভাবে ডেলিভার হয়েছে। আমাদের সাথে থাকার জন্য ধন্যবাদ।",
                "Hi {name}, apnar {brand} order #{order_id} delivered hoyeche. Invoice email e pathano hoyeche.",
            ],
        },
        {
            "scenario_id": "scen_0_09",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": BRANDS_ALL,
            "variants": [
                "Hi {name}, meeting ta {time} pore hobe. Office e chole esho.",
                "{name}, আজকে সন্ধ্যায় বাসায় ফিরতে একটু দেরি হবে।",
                "Hey {name}, did you receive the notes I sent yesterday? Let me know.",
            ],
        },
        {
            "scenario_id": "scen_0_10",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": MFS_BRANDS,
            "variants": [
                "{brand} Statement: Total incoming Tk {amount} this month. View details in app.",
                "{brand} সিকিউরিটি টিপস: কখনোই পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।",
                "{brand} notice: Scheduled maintenance tonight for {time}. Services will resume shortly.",
            ],
        },
        # ---------------- CLASS 1: MFS/OTP Scam (10 scenarios) ----------------
        {
            "scenario_id": "scen_1_01",
            "label": 1,
            "techniques": "T1|T2|T5",
            "action": 1,
            "brands": MFS_BRANDS,
            "variants": [
                "Ami {brand} agent, bhul kore apnar number e Tk {amount} chole gese. Taka ferot dite PIN ta bolen.",
                "ভাই ভুল করে আপনার {brand} নম্বরে {amount} টাকা চলে গেছে। দয়া করে ওটিপি ও পিন দিন ফেরত নেওয়ার জন্য।",
                "This is {brand} agent {name}. I sent Tk {amount} by mistake. Share your OTP to reverse it.",
            ],
        },
        {
            "scenario_id": "scen_1_02",
            "label": 1,
            "techniques": "T1|T2|T5",
            "action": 1,
            "brands": MFS_BRANDS,
            "variants": [
                "{brand} Alert: Your account will be blocked in {time} due to KYC. Send NID and PIN to verify.",
                "জরুরি নোটিশ: কেওয়াইসি আপডেট না করলে {time} এর মধ্যে আপনার {brand} অ্যাকাউন্ট বন্ধ হবে। পিন ও এনআইডি পাঠান।",
                "Dear {brand} user, KYC update na korle account block hobe. {time} er moddhe OTP ar PIN pathan.",
            ],
        },
        {
            "scenario_id": "scen_1_03",
            "label": 1,
            "techniques": "T1|T2",
            "action": 1,
            "brands": ["DBBL", "City Bank", "Daraz"],
            "variants": [
                "{brand} refund team: send your card number, expiry date, and CVV to process Tk {amount} refund.",
                "{brand} সাপোর্ট: আপনার {amount} টাকা রিফান্ড পেতে কার্ড নম্বর এবং সিভিভি কোড দিন।",
                "{brand} helpline: apnar Tk {amount} refund korte card details ar OTP ta reply korun.",
            ],
        },
        {
            "scenario_id": "scen_1_04",
            "label": 1,
            "techniques": "T1|T2|T5|T6",
            "action": 1,
            "brands": ["Bdjobs", "Daraz", "Pathao"],
            "variants": [
                "Congratulations! Selected for {brand} remote job paying Tk {amount}/month. Reply with OTP & NID to activate payroll.",
                "{brand} চাকরির অফার: বেতন {amount} টাকা। জয়েনিং কনফার্ম করতে আপনার ফোনে আসা ওটিপি এবং পাসওয়ার্ড দিন।",
                "{brand} job offer confirmed! Salary Tk {amount}. Joining er jonno apnar OTP ar bank PIN share korun.",
            ],
        },
        {
            "scenario_id": "scen_1_05",
            "label": 1,
            "techniques": "T1|T2|T5",
            "action": 1,
            "brands": MFS_BRANDS,
            "variants": [
                "{brand} Helpline: Unusual login detected on your account. Reply with 6-digit OTP within {time} to prevent lock.",
                "{brand} হেল্পলাইন: আপনার অ্যাকাউন্টে সন্দেহজনক লগইন হয়েছে। ব্লক এড়াতে এখনই ৬ সংখ্যার কোড পাঠান।",
                "{brand} security: Apnar account hack howar risk e ache. Save korte ekhoni OTP ta din.",
            ],
        },
        {
            "scenario_id": "scen_1_06",
            "label": 1,
            "techniques": "T2|T5",
            "action": 1,
            "brands": MFS_BRANDS,
            "variants": [
                "To claim your Tk {amount} cashback from {brand}, enter your PIN and OTP at {link}.",
                "{brand} থেকে {amount} টাকা ক্যাশব্যাক পেতে {link} লিংকে গিয়ে পিন ও ওটিপি দিন।",
                "Apnar {brand} Tk {amount} bonus claim korte {link} e giye PIN ar OTP submit korun.",
            ],
        },
        {
            "scenario_id": "scen_1_07",
            "label": 1,
            "techniques": "T1|T2|T5",
            "action": 1,
            "brands": TELECOM_BRANDS,
            "variants": [
                "{brand} SIM Verification: Your SIM will be deactivated in {time}. Send NID front/back photo and OTP.",
                "{brand} সতর্কতা: বায়োমেট্রিক আপডেট না করলে {time} পর সিম বন্ধ হবে। এনআইডি ও ওটিপি পাঠান।",
                "{brand} notice: SIM off hoye jabe {time} er moddhe. Verify korte NID ar OTP pathan.",
            ],
        },
        {
            "scenario_id": "scen_1_08",
            "label": 1,
            "techniques": "T1|T2",
            "action": 1,
            "brands": ["DBBL", "City Bank"],
            "variants": [
                "I am calling from {brand} Head Office. Your ATM card is expired; tell me your internet banking password and OTP.",
                "{brand} হেড অফিস থেকে বলছি। আপনার কার্ড সচল রাখতে পাসওয়ার্ড এবং ওটিপি বলুন।",
                "{brand} officer bolchi: apnar account upgrade korte internet banking password ar OTP lagbe.",
            ],
        },
        {
            "scenario_id": "scen_1_09",
            "label": 1,
            "techniques": "T1|T2|T4",
            "action": 1,
            "brands": MFS_BRANDS,
            "variants": [
                "You won Tk {amount} in {brand} Eid offer! Share your {brand} PIN so our officer can credit it.",
                "{brand} ঈদ বোনাস {amount} টাকা জিতেছেন! টাকা নিতে আপনার {brand} পিন ও ওটিপি জানান।",
                "Apni {brand} lottery te Tk {amount} jitechen. Taka pathate apnar PIN ar OTP bolen.",
            ],
        },
        {
            "scenario_id": "scen_1_10",
            "label": 1,
            "techniques": "T1|T2|T5",
            "action": 1,
            "brands": MFS_BRANDS,
            "variants": [
                "{brand} Server Upgrade: Login again at {link} with your phone number and PIN within {time}.",
                "{brand} সার্ভার আপডেট চলছে। অ্যাকাউন্ট সচল রাখতে {link} লিংকে পিন দিয়ে লগইন করুন।",
                "{brand} account active rakhte {time} er moddhe {link} e giye mobile number o PIN din.",
            ],
        },
        # ---------------- CLASS 2: Prize/Lottery Scam (10 scenarios) ----------------
        {
            "scenario_id": "scen_2_01",
            "label": 2,
            "techniques": "T1|T3|T4",
            "action": 2,
            "brands": MFS_BRANDS + TELECOM_BRANDS,
            "variants": [
                "Congratulations! You won a brand new car & Tk {amount} in {brand} Mega Draw. Pay Tk 500 registration fee to {phone}.",
                "অভিনন্দন! {brand} মেগা ড্র-তে আপনি {amount} টাকা জিতেছেন। পুরস্কার পেতে ৫০০ টাকা ফি পাঠান।",
                "{brand} lucky draw te apni Tk {amount} jitechen! Claim korte Tk 300 fee {phone} e pathan.",
            ],
        },
        {
            "scenario_id": "scen_2_02",
            "label": 2,
            "techniques": "T1|T4|T5",
            "action": 3,
            "brands": TELECOM_BRANDS,
            "variants": [
                "Free 15GB data gift from {brand} for you! Tap {link} now, offer expires in {time}.",
                "{brand} থেকে ফ্রি ২০ জিবি ইন্টারনেট গিফট! {time} এর মধ্যে {link} লিংকে ক্লিক করুন।",
                "{brand} anniversary offer: Free 10GB data! Ekhoni {link} e click korun, time {time}.",
            ],
        },
        {
            "scenario_id": "scen_2_03",
            "label": 2,
            "techniques": "T3|T4",
            "action": 2,
            "brands": MFS_BRANDS + ["Daraz"],
            "variants": [
                "Scratch and win Tk {amount} cash prize! Deposit Tk 300 processing charge to unlock your reward.",
                "স্ক্র্যাচ করে জিতে নিন {amount} টাকা! টাকা তুলতে ৩০০ টাকা প্রসেসিং ফি জমা দিন।",
                "Apni scratch card e Tk {amount} jitechen. Taka tulte Tk 250 charge pay korun {phone} e.",
            ],
        },
        {
            "scenario_id": "scen_2_04",
            "label": 2,
            "techniques": "T1|T4|T5",
            "action": 3,
            "brands": MFS_BRANDS,
            "variants": [
                "{brand} Cashback Bonanza: You won Tk {amount}! Click {link} within {time} to claim.",
                "{brand} ক্যাশব্যাক অফার: আপনি {amount} টাকা পেয়েছেন! দাবি করতে {link} ভিজিট করুন।",
                "{brand} Eid cashback Tk {amount} apnar jonno! Claim korte {link} e jan {time} er moddhe.",
            ],
        },
        {
            "scenario_id": "scen_2_05",
            "label": 2,
            "techniques": "T1|T4",
            "action": 4,
            "brands": MFS_BRANDS,
            "variants": [
                "{brand} anniversary spin & win Tk {amount}! Download the reward app: {link}",
                "{brand} বর্ষপূর্তি উপলক্ষে স্পিন করে {amount} টাকা জিতুন! অ্যাপ ডাউনলোড করুন: {link}",
                "{brand} spin wheel e Tk {amount} jitechen! App install korun ekhan theke: {link}",
            ],
        },
        {
            "scenario_id": "scen_2_06",
            "label": 2,
            "techniques": "T3|T4|T5",
            "action": 2,
            "brands": ["Daraz", "Pathao"],
            "variants": [
                "You are selected for a free iPhone 15 from {brand} loyalty reward! Pay Tk {amount} delivery charge first.",
                "{brand} থেকে আপনি ফ্রি স্মার্টফোন জিতেছেন! ডেলিভারি চার্জ {amount} টাকা পাঠিয়ে কনফার্ম করুন।",
                "Apni {brand} customer reward e free smartphone peyechn! Just Tk {amount} delivery fee din.",
            ],
        },
        {
            "scenario_id": "scen_2_07",
            "label": 2,
            "techniques": "T4|T5",
            "action": 5,
            "brands": TELECOM_BRANDS + MFS_BRANDS,
            "variants": [
                "Lottery Winner Alert! Your number won Tk {amount} in {brand} draw. Call {phone} within {time} to claim.",
                "লটারি বিজয়ী! আপনার নম্বর {brand} ড্র-তে {amount} টাকা জিতেছে। {time} এর মধ্যে {phone} নম্বরে কল করুন।",
                "Apnar number {brand} lottery te Tk {amount} jiteche. Prize nite {phone} e call korun.",
            ],
        },
        {
            "scenario_id": "scen_2_08",
            "label": 2,
            "techniques": "T3|T4",
            "action": 2,
            "brands": ["DBBL", "City Bank"],
            "variants": [
                "{brand} Golden Jubilee Gift: You won Tk {amount}. Transfer Tk 500 VAT fee to release funds.",
                "{brand} গোল্ডেন জুবিলি উপহার {amount} টাকা জিতেছেন। ভ্যাট বাবদ ৫০০ টাকা পাঠান।",
                "{brand} gift voucher Tk {amount} jitechen. Tax fee Tk 400 pathale taka release hobe.",
            ],
        },
        {
            "scenario_id": "scen_2_09",
            "label": 2,
            "techniques": "T4|T5",
            "action": 3,
            "brands": ["Daraz", "bKash"],
            "variants": [
                "Mystery Box Winner! Claim your Tk {amount} {brand} voucher before it expires in {time}: {link}",
                "মিস্ট্রি বক্স জিতেছেন! {time} শেষ হওয়ার আগে {link} থেকে {amount} টাকার ভাউচার নিন।",
                "{brand} mystery gift Tk {amount} voucher claim korte {link} e click korun.",
            ],
        },
        {
            "scenario_id": "scen_2_10",
            "label": 2,
            "techniques": "T1|T3|T4",
            "action": 2,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand} Lucky Customer: A gift parcel worth Tk {amount} is waiting for you. Pay Tk 350 customs fee to claim.",
                "{brand} থেকে আপনার জন্য {amount} টাকার গিফট পার্সেল এসেছে। কাস্টমস ফি ৩৫০ টাকা পরিশোধ করুন।",
                "{brand} gift parcel peyechn Tk {amount} er! Customs charge Tk 300 dile release hobe.",
            ],
        },
        # ---------------- CLASS 3: Fake Job/Investment (10 scenarios) ----------------
        {
            "scenario_id": "scen_3_01",
            "label": 3,
            "techniques": "T6",
            "action": 4,
            "brands": ["Bdjobs", "Daraz"],
            "variants": [
                "Work from home! Earn Tk {amount} daily with just 1 hour on your phone. Join Telegram: {link}",
                "ঘরে বসে প্রতিদিন {amount} টাকা আয় করুন! কোনো অভিজ্ঞতা লাগবে না। টেলিগ্রামে যোগ দিন: {link}",
                "Ghor bose din e Tk {amount} income korun! WhatsApp group e join korun: {link}",
            ],
        },
        {
            "scenario_id": "scen_3_02",
            "label": 3,
            "techniques": "T6",
            "action": 4,
            "brands": ["Bdjobs", "Daraz"],
            "variants": [
                "Part-time job: Like YouTube videos & follow pages, earn Tk {amount} per task! Join now: {link}",
                "পার্ট-টাইম কাজ: ইউটিউব ভিডিও লাইক করে প্রতিদিন {amount} টাকা ইনকাম। আজই জয়েন করুন: {link}",
                "Facebook page like korle protek like e 50 taka, daily Tk {amount} income. Group e join korun: {link}",
            ],
        },
        {
            "scenario_id": "scen_3_03",
            "label": 3,
            "techniques": "T3|T6",
            "action": 2,
            "brands": MFS_BRANDS,
            "variants": [
                "Double your money in {time}! Invest Tk {amount} in our VIP crypto pool and get 300% return. Send to {phone}.",
                "মাত্র {time} এ টাকা ডাবল! {amount} টাকা ইনভেস্ট করলে ৩০০% লাভ পাবেন। {phone} নম্বরে পাঠান।",
                "Crypto investment scheme: Tk {amount} invest korle {time} e 3x profit! {brand} korun {phone} e.",
            ],
        },
        {
            "scenario_id": "scen_3_04",
            "label": 3,
            "techniques": "T3|T6",
            "action": 2,
            "brands": ["Bdjobs"],
            "variants": [
                "Europe & Dubai Work Visa available! Salary Tk {amount}/month. Pay Tk 5,000 file processing fee today.",
                "বিদেশে চাকরির সুবর্ণ সুযোগ! মাসিক বেতন {amount} টাকা। ভিসা প্রসেসিং ফি ৫,০০০ টাকা অগ্রিম পাঠান।",
                "Abroad work visa confirmed with Tk {amount} salary! Advance registration fee Tk 3,000 din {phone} e.",
            ],
        },
        {
            "scenario_id": "scen_3_05",
            "label": 3,
            "techniques": "T1|T3|T6",
            "action": 2,
            "brands": ["Daraz", "Pathao"],
            "variants": [
                "{brand} merchant task: Buy products via our link, get full refund + 20% commission. Deposit Tk {amount} to start.",
                "{brand} টাস্ক প্রোগ্রাম: প্রোডাক্ট রিভিউ করে {amount} টাকা বোনাস পান। শুরু করতে {amount} টাকা ডিপোজিট করুন।",
                "{brand} online task: 5 ta order complete korle Tk {amount} profit. First e Tk 1,000 deposit korun.",
            ],
        },
        {
            "scenario_id": "scen_3_06",
            "label": 3,
            "techniques": "T3|T6",
            "action": 2,
            "brands": ["Bdjobs"],
            "variants": [
                "{brand} Urgent Hiring: Data entry operator, Tk {amount}/month. Pay Tk 500 ID card registration fee to {phone}.",
                "{brand} নিয়োগ বিজ্ঞপ্তি: ডাটা এন্ট্রি অপারেটর, বেতন {amount} টাকা। রেজিস্ট্রেশন ফি ৫০০ টাকা পাঠান।",
                "{brand} e chakri confirmed! Monthly Tk {amount}. Security deposit Tk 1,000 pathan {phone} e.",
            ],
        },
        {
            "scenario_id": "scen_3_07",
            "label": 3,
            "techniques": "T5|T6",
            "action": 5,
            "brands": ["Bdjobs"],
            "variants": [
                "Guaranteed passive income Tk {amount}/week via automated trading bot. WhatsApp {phone} within {time}!",
                "অটোমেটেড ট্রেডিং বট দিয়ে সপ্তাহে {amount} টাকা নিশ্চিত আয়! বিস্তারিত জানতে {phone} নম্বরে মেসেজ দিন।",
                "Daily Tk {amount} guaranteed earning with zero risk! Limited seats, call {phone} now.",
            ],
        },
        {
            "scenario_id": "scen_3_08",
            "label": 3,
            "techniques": "T6",
            "action": 4,
            "brands": MFS_BRANDS,
            "variants": [
                "Download our earning app and earn Tk {amount} daily by watching ads! Install now: {link}",
                "অ্যাড দেখে প্রতিদিন {amount} টাকা ইনকাম করুন! অ্যাপ ডাউনলোড লিংক: {link}",
                "App install kore ad dekhlei daily Tk {amount} {brand} e withdraw! Link: {link}",
            ],
        },
        {
            "scenario_id": "scen_3_09",
            "label": 3,
            "techniques": "T3|T5|T6",
            "action": 2,
            "brands": MFS_BRANDS,
            "variants": [
                "VIP Forex Signal Group: Turn Tk {amount} into Tk 50,000 in {time}. Pay membership fee to {phone}.",
                "ভিআইপি ফরেক্স সিগন্যাল: {time} এ {amount} টাকা থেকে ৫০,০০০ টাকা আয়। মেম্বারশিপ ফি পাঠান {phone} এ।",
                "Join VIP investment group, {time} e Tk {amount} profit sure. Entry fee Tk 1,000 {brand} korun.",
            ],
        },
        {
            "scenario_id": "scen_3_10",
            "label": 3,
            "techniques": "T1|T6",
            "action": 3,
            "brands": ["Bdjobs", "Pathao"],
            "variants": [
                "{brand} Freelancer Portal: Earn Tk {amount} per assignment. Sign up immediately at {link}.",
                "{brand} ফ্রিল্যান্সিং প্রজেক্ট: প্রতিটি কাজে {amount} টাকা পেমেন্ট। রেজিস্টার করুন: {link}",
                "{brand} home-based job: Tk {amount} per project. Apply korte {link} e click korun.",
            ],
        },
        # ---------------- CLASS 4: Delivery/Parcel Phishing (10 scenarios) ----------------
        {
            "scenario_id": "scen_4_01",
            "label": 4,
            "techniques": "T1|T3",
            "action": 2,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand}: Parcel #{order_id} held at Dhaka hub. Pay Tk {amount} storage fee via {link} to release.",
                "{brand}: আপনার পার্সেল #{order_id} হাব-এ আটকে আছে। ছাড়াতে {amount} টাকা স্টোরেজ ফি দিন: {link}",
                "{brand} notice: Parcel #{order_id} atke ase. Tk {amount} delivery fee pay korun {link} e.",
            ],
        },
        {
            "scenario_id": "scen_4_02",
            "label": 4,
            "techniques": "T1|T3|T5",
            "action": 2,
            "brands": COURIER_BRANDS,
            "variants": [
                "Customs Hold: Your overseas parcel #{order_id} via {brand} requires Tk {amount} duty within {time}. Pay to {phone}.",
                "কাস্টমস নোটিশ: আপনার বিদেশি পার্সেল #{order_id} ছাড়াতে {time} এর মধ্যে {amount} টাকা শুল্ক পরিশোধ করুন।",
                "{brand} Customs: Overseas parcel clear korte Tk {amount} duty lagbe {time} er moddhe. bKash korun {phone} e.",
            ],
        },
        {
            "scenario_id": "scen_4_03",
            "label": 4,
            "techniques": "T1|T5",
            "action": 3,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand}: Delivery failed due to incomplete address. Update your address within {time} at {link} or parcel returns.",
                "{brand}: ভুল ঠিকানার কারণে পার্সেল ডেলিভারি হয়নি। {time} এর মধ্যে {link} লিংকে ঠিকানা আপডেট করুন।",
                "{brand} alert: Address missing bole parcel delivery hoyni. {link} e giye address confirm korun.",
            ],
        },
        {
            "scenario_id": "scen_4_04",
            "label": 4,
            "techniques": "T1|T3|T5",
            "action": 2,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand} Express: Redelivery charge Tk 45 required for parcel #{order_id}. Pay now at {link}.",
                "{brand} এক্সপ্রেস: পার্সেল #{order_id} পুনরায় ডেলিভারির জন্য ৪৫ টাকা চার্জ পরিশোধ করুন: {link}",
                "{brand}: Apnar parcel #{order_id} redelivery korte Tk 50 fee pay korte hobe {link} e.",
            ],
        },
        {
            "scenario_id": "scen_4_05",
            "label": 4,
            "techniques": "T1",
            "action": 3,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand} Tracking: Your package #{order_id} has arrived. Download tracking slip here: {link}",
                "{brand} ট্র্যাকিং: আপনার প্যাকেজ #{order_id} পৌঁছেছে। স্লিপ দেখতে {link} লিংকে ক্লিক করুন।",
                "{brand}: Apnar parcel #{order_id} track korte ebong receive korte {link} e tap korun.",
            ],
        },
        {
            "scenario_id": "scen_4_06",
            "label": 4,
            "techniques": "T1|T5",
            "action": 5,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand}: Urgent! Parcel #{order_id} will be auctioned in {time}. Call {phone} immediately to confirm.",
                "{brand}: জরুরি! {time} এর মধ্যে যোগাযোগ না করলে পার্সেল #{order_id} বাতিল হবে। কল করুন {phone}।",
                "{brand} urgent: Apnar parcel #{order_id} return hoye jabe {time} por. Ekhoni {phone} e call korun.",
            ],
        },
        {
            "scenario_id": "scen_4_07",
            "label": 4,
            "techniques": "T1|T3",
            "action": 2,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand} COD Verification: Pre-pay Tk {amount} security deposit for your order #{order_id} at {link}.",
                "{brand} সিওডি ভেরিফিকেশন: অর্ডার #{order_id} কনফার্ম করতে {amount} টাকা অগ্রিম পরিশোধ করুন।",
                "{brand}: Order #{order_id} dispatch korte Tk {amount} advance courier charge pathan {phone} e.",
            ],
        },
        {
            "scenario_id": "scen_4_08",
            "label": 4,
            "techniques": "T1|T3|T5",
            "action": 2,
            "brands": COURIER_BRANDS,
            "variants": [
                "Airport Cargo {brand}: Diplomatic parcel #{order_id} clearance fee Tk {amount} due in {time}.",
                "এয়ারপোর্ট কার্গো {brand}: আপনার আন্তর্জাতিক পার্সেল ক্লিয়ারেন্সের জন্য {amount} টাকা ফি দিন।",
                "{brand} Airport Hub: Foreign parcel #{order_id} release korte Tk {amount} clearance fee din.",
            ],
        },
        {
            "scenario_id": "scen_4_09",
            "label": 4,
            "techniques": "T1",
            "action": 4,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand} Smart Locker: Install our courier app at {link} to generate your parcel pickup QR code.",
                "{brand} স্মার্ট লকার: পার্সেল #{order_id} সংগ্রহের কিউআর কোড পেতে অ্যাপ ডাউনলোড করুন: {link}",
                "{brand}: Parcel pickup code pete {link} theke amader delivery app install korun.",
            ],
        },
        {
            "scenario_id": "scen_4_10",
            "label": 4,
            "techniques": "T1|T3",
            "action": 3,
            "brands": COURIER_BRANDS,
            "variants": [
                "{brand}: Weight mismatch on parcel #{order_id}. Pay Tk 120 extra surcharge via {link} to avoid delay.",
                "{brand}: পার্সেল #{order_id} এর ওজন বেশি হওয়ায় অতিরিক্ত ১২০ টাকা চার্জ দিন: {link}",
                "{brand} notice: Parcel #{order_id} extra weight charge Tk 100 dite {link} e jan.",
            ],
        },
        # ---------------- CLASS 5: Promotional Spam (10 scenarios) ----------------
        {
            "scenario_id": "scen_5_01",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Daraz", "Pathao"],
            "variants": [
                "{brand} Eid Mega Sale! Flat 30% discount on electronics and fashion. Use code EID30.",
                "{brand} ঈদ মেগা সেল! সব পণ্যে ৩০% পর্যন্ত ছাড়। আজই শপিং করুন!",
                "{brand} 11.11 offer! Sob item e 25% discount, voucher code SAVE25.",
            ],
        },
        {
            "scenario_id": "scen_5_02",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": TELECOM_BRANDS,
            "variants": [
                "{brand} Offer: Get 10GB + 200 mins at Tk {amount} for 30 days. Dial *121*50# to activate.",
                "{brand} স্পেশাল প্যাক: মাত্র {amount} টাকায় ১০ জিবি ইন্টারনেট ৭ দিন মেয়াদে! ডায়াল *১২১#।",
                "{brand} bundle offer: Tk {amount} e 15GB data, meyad 15 din. My{brand} app theke nin.",
            ],
        },
        {
            "scenario_id": "scen_5_03",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": MFS_BRANDS,
            "variants": [
                "Get 10% instant cashback on mobile recharge via {brand} app! Offer valid till Friday.",
                "{brand} অ্যাপ দিয়ে রিচার্জে ১০% ক্যাশব্যাক! অফারটি সীমিত সময়ের জন্য।",
                "{brand} app diye bill pay korle 5% cashback paben. Offer valid for {time}.",
            ],
        },
        {
            "scenario_id": "scen_5_04",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Generic"],
            "variants": [
                "Learn Spoken English & IELTS in 30 days! New batch admission going on. Visit our Dhanmondi campus.",
                "৩০ দিনে ইংরেজি শিখুন! নতুন ব্যাচে ভর্তি চলছে। বিস্তারিত জানতে আমাদের অফিসে আসুন।",
                "IELTS crash course e 40% discount! Admission cholche, limited seat available.",
            ],
        },
        {
            "scenario_id": "scen_5_05",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Generic"],
            "variants": [
                "Luxury ready flats in Uttara & Bashundhara! Book a site visit this weekend with 0% interest EMI.",
                "উত্তরা ও বসুন্ধরায় রেডি ফ্ল্যাট বিক্রয় চলছে! সহজ কিস্তিতে আজই বুকিং দিন।",
                "Purbachal e plot booking cholche! Easy installment facility, visit our Gulshan office.",
            ],
        },
        {
            "scenario_id": "scen_5_06",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Pathao"],
            "variants": [
                "{brand} Food: Enjoy 20% off on your next 3 orders over Tk 400 with promo code FOOD20.",
                "{brand} ফুড: আপনার পছন্দের রেস্টুরেন্টে ২০% ছাড় পেতে FOOD20 কোড ব্যবহার করুন।",
                "{brand} ride e 50% discount! Promo code RIDE50 use korun aajkei.",
            ],
        },
        {
            "scenario_id": "scen_5_07",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["DBBL", "City Bank"],
            "variants": [
                "{brand} Credit Card: Enjoy Buy-1-Get-1 buffet at leading 5-star hotels this weekend.",
                "{brand} ক্রেডিট কার্ডে পাচ্ছেন বাই-ওয়ান-গেট-ওয়ান বুফে অফার!",
                "{brand} cardholders get 15% off at partner restaurants across Dhaka.",
            ],
        },
        {
            "scenario_id": "scen_5_08",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Generic"],
            "variants": [
                "Grand Opening of Aarong & Lifestyle Outlet at Mirpur! Flat 15% off all weekend.",
                "মিরপুরে নতুন ফ্যাশন শোরুম উদ্বোধন উপলক্ষে সব পণ্যে ১৫% ছাড়!",
                "Winter collection eshe geche! Sob jacket o sweater e 20% discount cholche.",
            ],
        },
        {
            "scenario_id": "scen_5_09",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Generic"],
            "variants": [
                "Full Health Checkup package at Tk {amount} only! Includes CBC, lipid profile, and ECG.",
                "মাত্র {amount} টাকায় সম্পূর্ণ হেলথ চেকআপ প্যাকেজ! আজই অ্যাপয়েন্টমেন্ট বুক করুন।",
                "Dental scaling & checkup offer at Tk {amount} only. Friday open ache.",
            ],
        },
        {
            "scenario_id": "scen_5_10",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Daraz"],
            "variants": [
                "{brand} Flash Sale starts at midnight! Up to Tk {amount} off on smartphones and laptops.",
                "{brand} ফ্ল্যাশ সেল শুরু হবে রাত ১২টায়! স্মার্টফোনে {amount} টাকা পর্যন্ত ছাড়।",
                "{brand} PayDay Sale: Free delivery on orders above Tk 500!",
            ],
        },
    ]


def generate_hard_negatives(rng: random.Random, n_per_type: int = 45) -> list[dict]:
    """Generate hard-negative legitimate rows (scam warnings quoting scams, OTP warnings)."""
    rows: list[dict] = []

    quote_warnings = [
        "Bhai, ei rokom SMS asle vuleo reply dis na: 'You won Tk {amount} from {brand}, send PIN'. Eta pura scam!",
        "সতর্ক থাকুন! অনেকেই মেসেজ পাচ্ছে যে '{brand} পার্সেল আটকে আছে, {amount} টাকা ফি দিন'। এগুলো প্রতারণা।",
        "Hey {name}, my cousin got a text saying '{brand} KYC blocked, send OTP'. Don't fall for these phishing links!",
        "Friend warned me today: never click '{link}' even if it says '{brand} free 10GB gift'.",
        "দেখ তো {name}, কেউ আমাকে '{brand} লটারিতে {amount} টাকা জিতেছেন, পিন দিন' লিখে পাঠিয়েছে—আমি ব্লক করে দিয়েছি।",
    ]
    otp_warnings = [
        "{brand} Security Alert: Your OTP is {otp}. Nobody from {brand} will ever ask for your OTP or PIN.",
        "{brand} সতর্কীকরণ: আপনার ওটিপি {otp}। কোনো এজেন্ট বা কাস্টমার কেয়ার কখনোই ওটিপি চায় না।",
        "If someone calls claiming to be {brand} and asks for OTP {otp} after a mistaken transfer, hang up immediately.",
        "{brand} Dispute Alert: If you did not authorize Tk {amount}, freeze your card in the official app.",
    ]

    for i in range(n_per_type):
        text, group = _fill_slots(rng, rng.choice(quote_warnings))
        rows.append(
            {
                "scenario_id": f"scen_hn_quote_{(i % 5) + 1:02d}",
                "group": f"hn_{group}",
                "text": text,
                "label": 0,
                "techniques": "NONE",
                "action": 0,
            }
        )

    for i in range(n_per_type):
        text, group = _fill_slots(rng, rng.choice(otp_warnings), brand=rng.choice(MFS_BRANDS))
        rows.append(
            {
                "scenario_id": f"scen_hn_otp_{(i % 4) + 1:02d}",
                "group": f"hn_{group}",
                "text": text,
                "label": 0,
                "techniques": "NONE",
                "action": 0,
            }
        )
    return rows


def _format_conversation(rng: random.Random, turns: list[tuple[str, str]]) -> str:
    """Format (role, text) turns with varied speaker prefixes joined by ' ||| '."""
    style = rng.choice(["SR", "AB", "SY", "CY", "NONE"])
    mapping = {
        "SR": ("S: ", "R: "),
        "AB": ("A: ", "B: "),
        "SY": ("[Sender] ", "[You] "),
        "CY": ("Caller: ", "You: "),
        "NONE": ("", ""),
    }
    s_prefix, r_prefix = mapping[style]
    parts = [f"{s_prefix if role == 'S' else r_prefix}{msg}" for role, msg in turns]
    return " ||| ".join(parts)


def generate_conversations(rng: random.Random, n_per_class: int = 45) -> list[dict]:
    """Generate 2-8 turn conversations with delayed scam hooks and Priority Order labels."""
    rows: list[dict] = []

    conv_specs = [
        # Class 0: Legit conversation (even if discussing a suspicious message)
        {
            "scenario_id": "scen_conv_0_01",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": MFS_BRANDS,
            "turns": [
                ("S", "Hey {name}, free acho?"),
                ("R", "Ha bolo, ki hoyeche?"),
                ("S", "Ekta SMS ashlo je ami {brand} e Tk {amount} jitesi, PIN chaitese."),
                ("R", "Oita fake! {brand} kokhono PIN chay na. Number ta block kore dao."),
                ("S", "Thanks bhai, block kore disi."),
            ],
        },
        {
            "scenario_id": "scen_conv_0_02",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": COURIER_BRANDS,
            "turns": [
                ("S", "Hello, {brand} rider bolchi. Apnar parcel #{order_id} niye aschi."),
                ("R", "Ami Bashundhara gate er samne achi. Koto taka COD?"),
                ("S", "Tk {amount} cash on delivery. 5 minute e pouchacchi."),
                ("R", "Thik ache, ami wait korchi."),
            ],
        },
        # Class 1: Delayed hook MFS/OTP scam (also tests Priority Rule: job/prize + OTP -> 1)
        {
            "scenario_id": "scen_conv_1_01",
            "label": 1,
            "techniques": "T1|T2|T5",
            "action": 1,
            "brands": MFS_BRANDS,
            "turns": [
                ("S", "Assalamu Alaikum {name} vai, kemon achen?"),
                ("R", "Wa Alaikum Assalam, bhalo. Apni ke bolchen?"),
                ("S", "Ami {brand} customer care theke bolchi. Apnar account verification pending."),
                ("R", "Oh, ki korte hobe?"),
                ("S", "Kichu na, just apnar phone e ekta 6-digit OTP gese, oita bolen noile {time} por account off hobe."),
            ],
        },
        {
            "scenario_id": "scen_conv_1_02",
            "label": 1,
            "techniques": "T1|T2|T5|T6",
            "action": 1,
            "brands": ["Bdjobs", "Daraz"],
            "turns": [
                ("S", "Hi {name}, I saw your CV on {brand}. Are you looking for a remote role?"),
                ("R", "Yes, what is the salary?"),
                ("S", "Tk {amount} per month, flexible hours."),
                ("R", "Sounds great, how do I join?"),
                ("S", "Send the OTP we just sent to your phone and your {brand} password to activate payroll."),
            ],
        },
        # Class 2: Delayed hook Prize/Lottery scam (Priority: prize parcel + customs -> 2)
        {
            "scenario_id": "scen_conv_2_01",
            "label": 2,
            "techniques": "T3|T4",
            "action": 2,
            "brands": MFS_BRANDS + ["Daraz"],
            "turns": [
                ("S", "Hello, congratulations!"),
                ("R", "For what?"),
                ("S", "You have been selected for our {brand} customer loyalty reward."),
                ("R", "What is the reward?"),
                ("S", "A gift parcel worth Tk {amount}. Just pay Tk 500 delivery charge to {phone} to claim."),
            ],
        },
        # Class 3: Delayed hook Fake Job / Investment
        {
            "scenario_id": "scen_conv_3_01",
            "label": 3,
            "techniques": "T1|T3|T6",
            "action": 2,
            "brands": JOB_BRANDS,
            "turns": [
                ("S", "Hi, we have a work-from-home opening at {brand}."),
                ("R", "What kind of work is it?"),
                ("S", "Simple product rating tasks, 30 mins a day."),
                ("R", "Okay, how much does it pay?"),
                ("S", "Tk {amount} weekly. You just need to deposit Tk 2,000 security first via {phone}."),
            ],
        },
        # Class 4: Delayed hook Delivery/Parcel phishing
        {
            "scenario_id": "scen_conv_4_01",
            "label": 4,
            "techniques": "T1|T3|T5",
            "action": 2,
            "brands": COURIER_BRANDS,
            "turns": [
                ("S", "Hello {name}, calling from {brand} airport cargo."),
                ("R", "Yes, is my parcel here?"),
                ("S", "Parcel #{order_id} arrived from abroad today."),
                ("R", "When will it be delivered?"),
                ("S", "Customs cleared only after you pay Tk {amount} storage fee at {link} within {time}."),
            ],
        },
        # Class 5: Promotional chat
        {
            "scenario_id": "scen_conv_5_01",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Daraz", "Pathao"],
            "turns": [
                ("S", "Hi {name}! {brand} Winter Mega Sale starts tonight."),
                ("R", "Oh nice, what is the discount?"),
                ("S", "Flat 30% off with promo code WINTER30 on all items."),
            ],
        },
    ]

    specs_by_class: dict[int, list[dict]] = {c: [] for c in range(6)}
    for spec in conv_specs:
        specs_by_class[spec["label"]].append(spec)

    for cls in range(6):
        cls_specs = specs_by_class[cls]
        for i in range(n_per_class):
            spec = cls_specs[i % len(cls_specs)]
            brand = rng.choice(spec["brands"])
            # Optionally vary turn count between 2 and len(turns) while keeping final hook
            turns = list(spec["turns"])
            if len(turns) > 3 and rng.random() < 0.35:
                turns = [turns[0], turns[-1]]
            filled_turns = [(role, _fill_slots(rng, msg, brand=brand)[0]) for role, msg in turns]
            text = _format_conversation(rng, filled_turns)
            rows.append(
                {
                    "scenario_id": spec["scenario_id"],
                    "group": f"conv_{brand.lower().replace(' ', '_')}",
                    "text": text,
                    "label": spec["label"],
                    "techniques": spec["techniques"],
                    "action": spec["action"],
                }
            )
    return rows


def generate_domain_shifts(rng: random.Random, n_per_class: int = 25) -> list[dict]:
    """Generate formal emails, call transcripts, and long broadcast notices across all classes."""
    rows: list[dict] = []
    domain_specs = [
        {
            "scenario_id": "scen_dom_0",
            "label": 0,
            "techniques": "NONE",
            "action": 0,
            "brands": ["DBBL", "City Bank", "Daraz"],
            "variants": [
                "Subject: Monthly Statement Ready\nDear {name},\nYour {brand} statement for this month totaling Tk {amount} is available in the official portal. Never share your OTP or PIN with anyone.\nRegards,\n{brand} Support",
                "[Call Transcript] Agent: Thank you for calling {brand}. Your order #{order_id} is scheduled for delivery tomorrow. Customer: Thank you. Agent: Have a great day.",
            ],
        },
        {
            "scenario_id": "scen_dom_1",
            "label": 1,
            "techniques": "T1|T2|T5",
            "action": 1,
            "brands": MFS_BRANDS,
            "variants": [
                "Subject: URGENT KYC Suspension Notice\nDear {brand} Customer,\nYour account is flagged for suspicious activity and will be suspended in {time}. Submit your NID number, PIN, and 6-digit OTP at {link} immediately.",
                "[Call Transcript] Caller: Hello {name}, I am from {brand} Fraud Desk. A wrong transfer of Tk {amount} reached your wallet. Tell me the OTP on your phone right now to reverse it.",
            ],
        },
        {
            "scenario_id": "scen_dom_2",
            "label": 2,
            "techniques": "T1|T3|T4",
            "action": 2,
            "brands": MFS_BRANDS + TELECOM_BRANDS,
            "variants": [
                "Subject: Official Winner Notification - {brand} Annual Draw\nDear {name},\nYou have won Tk {amount} in our annual promotion. To release your prize within {time}, remit Tk 500 processing fee to {phone}.",
                "[Group Notice] @everyone {brand} just launched a giveaway! Every member gets Tk {amount} cashback—pay Tk 300 verification charge via {link} to unlock.",
            ],
        },
        {
            "scenario_id": "scen_dom_3",
            "label": 3,
            "techniques": "T3|T6",
            "action": 2,
            "brands": JOB_BRANDS,
            "variants": [
                "Subject: Remote Task Offer - Earn Tk {amount} Weekly\nHello {name},\nBased on your {brand} profile, you qualify for our online merchant task program. Deposit Tk 1,500 activation fee to {phone} to start earning.",
                "[Group Broadcast] Official VIP Investment Club: Turn Tk {amount} into 300% profit in {time}. Transfer your capital to {phone} before slots close.",
            ],
        },
        {
            "scenario_id": "scen_dom_4",
            "label": 4,
            "techniques": "T1|T3|T5",
            "action": 2,
            "brands": COURIER_BRANDS,
            "variants": [
                "Subject: Parcel #{order_id} Customs Clearance Required\nDear {name},\nYour international shipment via {brand} is on hold. Pay Tk {amount} customs duty at {link} within {time} to prevent return.",
                "[Automated Notice] {brand} Logistics: Delivery attempt failed for #{order_id}. Confirm your street address and pay Tk 45 redelivery fee at {link}.",
            ],
        },
        {
            "scenario_id": "scen_dom_5",
            "label": 5,
            "techniques": "NONE",
            "action": 0,
            "brands": ["Daraz", "GP", "Robi"],
            "variants": [
                "Subject: Weekend Flash Sale - Up to 40% Off!\nDear {name},\nExplore {brand} weekend deals on electronics, fashion, and groceries. Use code SAVE40 at checkout before Sunday midnight.",
                "[Broadcast] {brand} Super Pack: Enjoy 20GB data + 300 minutes for Tk {amount}, valid 30 days. Activate via official app.",
            ],
        },
    ]

    for spec in domain_specs:
        for i in range(n_per_class):
            brand = rng.choice(spec["brands"])
            text, group = _fill_slots(rng, spec["variants"][i % len(spec["variants"])], brand=brand)
            rows.append(
                {
                    "scenario_id": spec["scenario_id"],
                    "group": f"dom_{group}",
                    "text": text,
                    "label": spec["label"],
                    "techniques": spec["techniques"],
                    "action": spec["action"],
                }
            )
    return rows


def generate_dataset(seed: int = SEED, target_per_class: int = 260) -> pd.DataFrame:
    """Generate a balanced, deterministic synthetic dataset across all 6 classes."""
    rng = random.Random(seed)
    all_rows: list[dict] = []

    # 1. Core template library (~180 per class)
    templates = _template_bank()
    by_class: dict[int, list[dict]] = {c: [] for c in range(6)}
    for item in templates:
        by_class[item["label"]].append(item)

    for cls in range(6):
        cls_items = by_class[cls]
        for i in range(180):
            item = cls_items[i % len(cls_items)]
            brand = rng.choice(item["brands"])
            variant = rng.choice(item["variants"])
            text, group = _fill_slots(rng, variant, brand=brand)
            all_rows.append(
                {
                    "scenario_id": item["scenario_id"],
                    "group": group,
                    "text": text,
                    "label": item["label"],
                    "techniques": item["techniques"],
                    "action": item["action"],
                }
            )

    # 2. Hard negatives (class 0), conversations (all classes), domain shifts (all classes)
    all_rows.extend(generate_hard_negatives(rng, n_per_type=40))
    all_rows.extend(generate_conversations(rng, n_per_class=55))
    all_rows.extend(generate_domain_shifts(rng, n_per_class=30))

    df = pd.DataFrame(all_rows)

    # Balance each class to target_per_class (250-300 range) deterministically
    balanced_parts = []
    for cls in range(6):
        cls_df = df[df["label"] == cls]
        n = min(len(cls_df), target_per_class)
        balanced_parts.append(cls_df.sample(n=n, random_state=seed))

    out_df = pd.concat(balanced_parts, ignore_index=True)
    out_df = out_df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return out_df[["scenario_id", "group", "text", "label", "techniques", "action"]]


if __name__ == "__main__":
    df = generate_dataset(seed=SEED, target_per_class=260)
    out_path = _PROJECT_ROOT / "data" / "synthetic_train.csv"
    df.to_csv(out_path, index=False)

    assert not df.isna().any().any(), "Dataset contains NaN values!"
    assert (df["techniques"].astype(str).str.len() > 0).all(), "Empty techniques found!"
    benign = df["label"].isin([0, 5])
    assert (df.loc[benign, "techniques"] == "NONE").all(), "Class 0/5 must have NONE!"
    assert (df.loc[benign, "action"] == 0).all(), "Class 0/5 must have action 0!"
    scam = df["label"].isin([1, 2, 3, 4])
    assert (df.loc[scam, "techniques"] != "NONE").all(), "Class 1-4 cannot have NONE!"
    assert (df.loc[scam, "action"] != 0).all(), "Class 1-4 cannot have action 0!"

    print(f"Saved {len(df)} rows to {out_path}")
    print("Class distribution:")
    print(df["label"].value_counts().sort_index())

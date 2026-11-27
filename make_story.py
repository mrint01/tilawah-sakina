"""Stories of the Prophets: the story as Allah tells it in the Quran, one scene per ayah.

Every ayah is recited (with Arabic + English on screen) over a real nature clip that matches what it says
(Pixabay, film only). The prophets, angels and people are NEVER shown: scenes are places, sky, sea, light.

Usage (needs PIXABAY_API_KEY):
  python3 make_story.py adam
"""
import argparse
import random
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

import make_reel as mr
import nature

W, H = mr.W, mr.H
RECITER = "Mishary Alafasy"
# Extra tags never wanted in a prophet story (on top of nature.NO): no depictions, no myths that are not in the Quran.
STORY_NO = {"lantern", "lamp", "umbrella", "angel", "angels", "god", "jesus", "bible", "adam", "eve", "snake", "serpent", "apple", "devil", "demon",
            "religion", "christian", "cross", "heaven art", "painting", "illustration", "cartoon", "sculpture", "nude"}

# prophet -> (number in the series, Arabic name, English name, [(surah, ayah, scene search)])
STORIES = {
    "adam": (1, "آدم", "Adam", [
        (2, 30, "earth from space"),
        (2, 31, "galaxy stars"),
        (2, 32, "starry sky"),
        (2, 33, "nebula space"),
        (2, 34, "sun rays clouds"),
        (2, 35, "garden flowers"),
        (2, 36, "falling leaves"),
        (2, 37, "sunrise"),
    ]),
    "idris": (2, "إدريس", "Idris", [
        (19, 56, "mountain sunrise"),
        (19, 57, "starry sky"),
    ]),
}
TOTAL_PROPHETS = 25

# Narrated stories: an Arabic narrator tells the story (English subtitles) (from the Quran, authentic hadith and Ibn Kathir's
# Qasas al-Anbiya, without weak reports), and at the key moments Mishary Alafasy recites the ayah itself.
# Segments: ("n", narration, scene) or ("a", surah, ayah, scene).
VOICE = "ar-SA-HamedNeural"   # Arabic narrator (fusha); he tells the story, he never reads Quran words
# how many parts each narrated story has in total (the later parts are written after part 1 is approved)
PARTS = {"adam": 2, "idris": 1, "nuh": 3}
PART_TITLES = {"adam": ["The creation", "The garden"], "idris": ["Raised to a high place"],
               "nuh": ["The call", "The Ark", "The Flood"]}
# the series in order (Adam -> Muhammad ﷺ): key, English name
SERIES = [("adam", "Adam"), ("idris", "Idris"), ("nuh", "Nuh"), ("hud", "Hud"), ("salih", "Salih"), ("ibrahim", "Ibrahim"),
          ("lut", "Lut"), ("ismail", "Ismail"), ("ishaq", "Ishaq"), ("yaqub", "Ya'qub"), ("yusuf", "Yusuf"),
          ("ayyub", "Ayyub"), ("shuayb", "Shu'ayb"), ("musa", "Musa"), ("harun", "Harun"), ("dhulkifl", "Dhul-Kifl"),
          ("dawud", "Dawud"), ("sulayman", "Sulayman"), ("ilyas", "Ilyas"), ("alyasa", "Al-Yasa'"), ("yunus", "Yunus"),
          ("zakariya", "Zakariya"), ("yahya", "Yahya"), ("isa", "'Isa"), ("muhammad", "Muhammad ﷺ")]
SOURCES = "Quran · Sahih al-Bukhari · Ibn Kathir, Qasas al-Anbiya"
# Segments: ("n", Arabic narration, English subtitle, scene) or ("a", surah, ayah, scene).
# scene: a Pixabay video id picked by hand (looked at: no people, buildings, animals or symbols), or a search.
NARRATED = {
    "adam": (1, "آدم", "Adam", [
        [  # Part 1: the creation (Al-Baqarah 2:30-34, Al-A'raf 7:11-17, Sad 38:71-85, Al-Kahf 18:50)
            ("n", "قَبْلَ أَنْ يَكُونَ عَلَى الْأَرْضِ إِنْسَانٌ، أَخْبَرَ اللَّهُ الْمَلَائِكَةَ أَنَّهُ سَيَجْعَلُ فِي الْأَرْضِ خَلِيفَةً.",
             "Before there was any human on the earth, Allah told the angels that He would place a successor upon it.", 20763),
            ("a", 2, 30, 48899),
            ("n", "فَخَلَقَ اللَّهُ آدَمَ مِنْ طِينٍ، مِنْ تُرَابِ هَذِهِ الْأَرْضِ، ثُمَّ نَفَخَ فِيهِ مِنْ رُوحِهِ، فَصَارَ إِنْسَانًا حَيًّا.",
             "Allah created Adam from clay, from the dust of this earth. Then He breathed into him of His spirit, and he "
             "became a living man.", 248632),
            ("n", "وَعَلَّمَهُ اللَّهُ أَسْمَاءَ الْأَشْيَاءِ كُلِّهَا، ثُمَّ عَرَضَهَا عَلَى الْمَلَائِكَةِ، وَسَأَلَهُمْ عَنْهَا.",
             "And Allah taught him the names of all things. Then He showed them to the angels, and asked them about them.",
             1099),
            ("a", 2, 32, 6343),
            ("n", "ثُمَّ أَمَرَ اللَّهُ الْمَلَائِكَةَ أَنْ يَسْجُدُوا لِآدَمَ سُجُودَ تَحِيَّةٍ وَإِكْرَامٍ، فَسَجَدُوا جَمِيعًا، إِلَّا إِبْلِيسَ.",
             "Then Allah commanded the angels to bow down to Adam, a bow of greeting and honour. They all bowed, "
             "except Iblis.", 229685),
            ("a", 2, 34, 2147),
            ("n", "وَكَانَ إِبْلِيسُ مِنَ الْجِنِّ، فَتَكَبَّرَ، وَقَالَ: أَنَا خَيْرٌ مِنْهُ.",
             "Iblis was one of the jinn. He grew arrogant, and said: I am better than him.", 38998),
            ("a", 7, 12, 34532),
            ("n", "فَطَرَدَهُ اللَّهُ مِنْ رَحْمَتِهِ. فَطَلَبَ إِبْلِيسُ أَنْ يُمْهَلَ إِلَى يَوْمِ الْقِيَامَةِ، وَأَقْسَمَ أَنْ يُغْوِيَ بَنِي آدَمَ.",
             "So Allah cast him out of His mercy. Iblis asked to be given time until the Day of Resurrection, and swore "
             "to lead the children of Adam astray.", 2150),
            ("n", "فِي الْجُزْءِ الثَّانِي: آدَمُ وَزَوْجُهُ فِي الْجَنَّةِ.",
             "In part two: Adam and his wife in Paradise.", 7127),
        ],
        [  # Part 2: the garden (Al-Baqarah 2:35-38, Al-A'raf 7:19-25, Ta-Ha 20:115-123)
            ("n", "وَخَلَقَ اللَّهُ لِآدَمَ زَوْجَهُ حَوَّاءَ، لِيَسْكُنَ إِلَيْهَا، وَأَسْكَنَهُمَا الْجَنَّةَ.",
             "Allah created for Adam his wife, Hawwa, so he would find comfort with her, and He let them live in "
             "Paradise.", 246856),
            ("a", 2, 35, 238393),
            ("n", "لَكِنَّ إِبْلِيسَ لَمْ يَنْسَ عَدَاوَتَهُ، فَوَسْوَسَ لَهُمَا، وَحَلَفَ لَهُمَا إِنَّهُ لَهُمَا نَاصِحٌ.",
             "But Iblis had not forgotten his hatred. He whispered to them, and swore to them that he was a sincere "
             "adviser.", 110493),
            ("a", 20, 120, 217491),
            ("n", "فَأَكَلَا مِنَ الشَّجَرَةِ، فَعَرَفَا أَنَّهُمَا أَخْطَآ، وَعَصَيَا أَمْرَ رَبِّهِمَا.",
             "They ate from the tree, and they knew they had done wrong, and disobeyed their Lord.", 136193),
            ("n", "لَمْ يَتَكَبَّرَا كَمَا تَكَبَّرَ إِبْلِيسُ، بَلْ نَدِمَا، وَرَجَعَا إِلَى اللَّهِ بِقَلْبٍ صَادِقٍ.",
             "They did not grow arrogant as Iblis had. They regretted it, and turned back to Allah with sincere hearts.",
             2527),
            ("a", 7, 23, 120005),
            ("a", 2, 37, 237673),
            ("n", "وَأَنْزَلَهُمَا اللَّهُ إِلَى الْأَرْضِ، لِتَبْدَأَ عَلَيْهَا حَيَاةُ الْإِنْسَانِ، وَوَعَدَهُمْ بِالْهُدَى.",
             "Allah sent them down to the earth, where human life would begin, and He promised them guidance.", 46936),
            ("a", 2, 38, 179200),
            ("n", "عَصَى إِبْلِيسُ وَأَصَرَّ، وَأَخْطَأَ آدَمُ فَتَابَ. فَمَنْ أَخْطَأَ مِنَّا، فَلْيَرْجِعْ إِلَى رَبِّهِ.",
             "Iblis disobeyed and persisted. Adam made a mistake, and repented. So whoever of us does wrong, let him "
             "return to his Lord.", 192799),
            ("n", "انْتَهَتْ قِصَّةُ آدَمَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ إِدْرِيسُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Adam, peace be upon him. Next: the Prophet Idris, peace be upon him.", 168829),
        ],
    ]),
    "idris": (2, "إدريس", "Idris", [
        [  # One part: Maryam 19:56-57, Al-Anbiya 21:85-86, and the Mi'raj (Sahih al-Bukhari 3207)
            ("n", "بَعْدَ آدَمَ، وَقَبْلَ نُوحٍ، بَعَثَ اللَّهُ نَبِيًّا صَادِقًا، اسْمُهُ إِدْرِيسُ عَلَيْهِ السَّلَامُ.",
             "After Adam, and before Nuh, Allah sent a truthful prophet named Idris, peace be upon him.", 59291),
            ("n", "ذَكَرَهُ اللَّهُ فِي الْقُرْآنِ فِي مَوْضِعَيْنِ، وَأَثْنَى عَلَيْهِ.",
             "Allah mentions him in the Quran in two places, and praises him.", 204680),
            ("a", 19, 56, 7127),
            ("a", 19, 57, 2266),
            ("n", "وَذَكَرَهُ اللَّهُ مَعَ إِسْمَاعِيلَ وَذِي الْكِفْلِ، فِي الصَّابِرِينَ.",
             "And Allah names him with Ismail and Dhul-Kifl, among the patient.", 125695),
            ("a", 21, 85, 248452),
            ("n", "وَفِي لَيْلَةِ الْمِعْرَاجِ، رَآهُ نَبِيُّنَا مُحَمَّدٌ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ فِي السَّمَاءِ الرَّابِعَةِ.",
             "On the night of the Mi'raj, our Prophet Muhammad ﷺ saw him in the fourth heaven.", 1096),
            ("n", "فَرَحَّبَ بِهِ إِدْرِيسُ، وَقَالَ: مَرْحَبًا بِالْأَخِ الصَّالِحِ، وَالنَّبِيِّ الصَّالِحِ. رَوَاهُ الْبُخَارِيُّ.",
             "Idris welcomed him, and said: welcome to the righteous brother, and the righteous prophet. "
             "(Sahih al-Bukhari)", 55990),
            ("n", "كَانَ صِدِّيقًا فِي قَوْلِهِ وَعَمَلِهِ، فَرَفَعَ اللَّهُ قَدْرَهُ. وَمَنْ صَدَقَ مَعَ اللَّهِ، رَفَعَهُ اللَّهُ.",
             "He was truthful in word and deed, so Allah raised his rank. Whoever is true with Allah, Allah raises "
             "him.", 280486),
            ("n", "انْتَهَتْ قِصَّةُ إِدْرِيسَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ نُوحٌ عَلَيْهِ السَّلَامُ.",
             "This was the story of Idris, peace be upon him. Next: the Prophet Nuh, peace be upon him.", 203322),
        ],
    ]),
    "nuh": (3, "نوح", "Nuh", [
        [  # Part 1: the call. Narration is fully vowelled so the voice pronounces it right (the screen shows it plain).
            ("n", "بَعْدَ آدَمَ بِزَمَنٍ طَوِيلٍ، كَانَ فِي النَّاسِ رِجَالٌ صَالِحُونَ. فَلَمَّا مَاتُوا، وَسْوَسَ الشَّيْطَانُ "
                  "لِلنَّاسِ: اصْنَعُوا لَهُمْ تَمَاثِيلَ لِتَتَذَكَّرُوهُمْ.",
             "Long after Adam, there were righteous men among the people. When they died, Shaytan whispered to them: "
             "make statues of them, so you remember them.", 71344),
            ("n", "وَمَضَتِ الْأَجْيَالُ، وَنُسِيَ الْعِلْمُ، فَعَبَدَ النَّاسُ تِلْكَ التَّمَاثِيلَ مِنْ دُونِ اللَّهِ.",
             "Generations passed, the knowledge was forgotten, and the people worshipped those statues instead of Allah.",
             58475),
            ("n", "فَأَرْسَلَ اللَّهُ إِلَيْهِمْ رَسُولَهُ نُوحًا عَلَيْهِ السَّلَامُ.",
             "So Allah sent them His messenger: Nuh, peace be upon him.", 237672),
            ("a", 71, 1, 204006),
            ("n", "دَعَا نُوحٌ قَوْمَهُ لَيْلًا وَنَهَارًا، فِي الْعَلَنِ وَفِي السِّرِّ، وَبَقِيَ فِيهِمْ تِسْعَمِائَةٍ وَخَمْسِينَ سَنَةً.",
             "Nuh called his people night and day, in public and in secret. He stayed among them for nine hundred and "
             "fifty years.", 22555),
            ("a", 71, 7, 125192),
            ("n", "وَقَالَ لَهُمْ: اطْلُبُوا الْمَغْفِرَةَ مِنْ رَبِّكُمْ، فَيُنْزِلَ عَلَيْكُمُ الْمَطَرَ، وَيَرْزُقَكُمُ الْمَالَ وَالْأَوْلَادَ.",
             "He told them: ask your Lord for forgiveness, and He will send you rain, and give you wealth and children.",
             26369),
            ("a", 71, 10, 17013),
            ("n", "لَكِنَّ كُبَرَاءَ قَوْمِهِ سَخِرُوا مِنْهُ، وَقَالُوا: مَا أَنْتَ إِلَّا رَجُلٌ مِثْلُنَا، وَلَا يَتَّبِعُكَ إِلَّا الضُّعَفَاءُ مِنَّا.",
             "But the leaders mocked him. You are only a man like us, they said, and only the weakest among us follow you.",
             70899),
            ("n", "وَمَا آمَنَ مَعَهُ إِلَّا قَلِيلٌ، وَمَعَ ذَلِكَ لَمْ يَتَوَقَّفْ نُوحٌ عَنْ دَعْوَتِهِمْ إِلَى اللَّهِ.",
             "Only a few believed. And still, Nuh never stopped calling them to Allah.", 30222),
            ("n", "فِي الْجُزْءِ الثَّانِي: يَأْمُرُ اللَّهُ نُوحًا بِبِنَاءِ السَّفِينَةِ.",
             "In part two: Allah commands Nuh to build the Ark.", 341601),
        ],
        [  # Part 2: the Ark (Hud 11:36-40, Al-Qamar 54:10-13)
            ("n", "وَمَرَّتِ السِّنُونَ، وَنُوحٌ يَدْعُو قَوْمَهُ، فَلَا يَزْدَادُونَ إِلَّا عِنَادًا. فَأَخْبَرَهُ اللَّهُ أَنَّهُ لَنْ يُؤْمِنَ "
                  "مِنْ قَوْمِهِ أَحَدٌ غَيْرُ مَنْ آمَنَ.",
             "Years passed, and the more Nuh called them, the more stubborn they became. Then Allah told him that no one "
             "else of his people would believe, except those who already had.", 30218),
            ("n", "فَدَعَا نُوحٌ رَبَّهُ أَنْ يَنْصُرَهُ عَلَيْهِمْ.",
             "So Nuh called upon his Lord to help him against them.", 260397),
            ("a", 54, 10, 16160),
            ("n", "فَأَمَرَهُ اللَّهُ أَنْ يَصْنَعَ سَفِينَةً عَظِيمَةً، تَحْتَ رِعَايَتِهِ وَوَحْيِهِ.",
             "Allah commanded him to build a great ship, under His watch and His guidance.", 49981),
            ("a", 11, 37, 19400),
            ("n", "فَأَخَذَ نُوحٌ يَبْنِي السَّفِينَةَ مِنَ الْأَلْوَاحِ وَالْمَسَامِيرِ.",
             "So Nuh began building the ship, from planks of wood and nails.", 230495),
            ("n", "وَكَانَ كُلَّمَا مَرَّ بِهِ جَمَاعَةٌ مِنْ قَوْمِهِ سَخِرُوا مِنْهُ.",
             "And every time a group of his people passed by, they mocked him.", 70901),
            ("a", 11, 38, 220131),
            ("n", "حَتَّى جَاءَ أَمْرُ اللَّهِ، وَظَهَرَتِ الْعَلَامَةُ الَّتِي وَعَدَهُ بِهَا: الْمَاءُ يَفُورُ مِنَ الْأَرْضِ.",
             "Until Allah's command came, and the sign He had promised appeared: water gushing up from the ground.", 45707),
            ("a", 11, 40, 123312),
            ("n", "فِي الْجُزْءِ الثَّالِثِ: الطُّوفَانُ.", "In part three: the Flood.", 283533),
        ],
        [  # Part 3: the Flood (Hud 11:41-48, Al-Qamar 54:11-12)
            ("n", "فَرَكِبَ نُوحٌ وَالْمُؤْمِنُونَ السَّفِينَةَ، وَحَمَلَ فِيهَا مِنْ كُلِّ نَوْعٍ ذَكَرًا وَأُنْثَى، كَمَا أَمَرَهُ اللَّهُ.",
             "Nuh and the believers boarded the ship, and he took on board a male and a female of every kind, as Allah "
             "commanded.", 341601),
            ("a", 11, 41, 22713),
            ("n", "ثُمَّ نَزَلَ الْمَطَرُ مِنَ السَّمَاءِ بِغَزَارَةٍ لَمْ يَرَ النَّاسُ مِثْلَهَا، وَتَفَجَّرَتِ الْأَرْضُ بِالْمَاءِ.",
             "Then rain poured from the sky as never before, and water burst out of the earth.", 214985),
            ("a", 54, 11, 78),
            ("a", 54, 12, 215404),
            ("n", "وَكَانَ لِنُوحٍ ابْنٌ لَمْ يُؤْمِنْ، فَنَادَاهُ أَبُوهُ رَاجِيًا أَنْ يَنْجُوَ مَعَهُ.",
             "Nuh had a son who did not believe. His father called out to him, hoping he would be saved with him.", 2266),
            ("a", 11, 42, 205011),
            ("a", 11, 43, 174999),
            ("n", "وَهَلَكَ الظَّالِمُونَ جَمِيعًا، ثُمَّ هَدَأَ كُلُّ شَيْءٍ.",
             "All the wrongdoers perished, and then everything grew still.", 209489),
            ("a", 11, 44, 2950),
            ("n", "وَنَجَّى اللَّهُ نُوحًا وَمَنْ مَعَهُ.", "And Allah saved Nuh and those with him.", 148260),
            ("n", "انْتَهَتْ قِصَّةُ نُوحٍ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ هُودٌ عَلَيْهِ السَّلَامُ.",
             "This was the story of Nuh, peace be upon him. Next: the Prophet Hud, peace be upon him.", 21175),
        ],
    ]),
}


def scene_clip(query, seconds, rnd, out):
    """A clip (or a few joined) for one ayah, cropped to 9:16, darkened, exactly `seconds` long."""
    old = set(nature.NO)
    nature.NO |= STORY_NO
    try:
        hits = nature.search(query)
    finally:
        nature.NO = old
    rnd.shuffle(hits)
    clips, covered = [], 0.0
    for h in hits:
        try:
            path = nature.clip_file(h)
            real = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                  "-of", "csv=p=0", str(path)]).strip())
        except Exception:  # noqa: BLE001
            continue
        if real < 5:
            continue
        clips.append((path, real * nature.SLOW, h["id"]))
        covered += real * nature.SLOW - (nature.FADE if len(clips) > 1 else 0)
        if covered >= seconds + 0.5:
            break
    if not clips:
        raise RuntimeError(f"no clip for {query!r}")
    nature.render_background(clips, seconds, out)
    return out


def frame_png(no, ar, en, path, part=None, footer=None):
    """Header (series + prophet) and footer (reciter, handle) over the whole story."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gold = (232, 198, 128)
    d.text((W / 2, 190), f"STORIES OF THE PROPHETS · {no} / {TOTAL_PROPHETS}", font=mr.font("Lora-var.ttf", 28),
           fill=gold + (230,), anchor="mm")
    d.text((W / 2, 268), f"قصة {ar} عليه السلام", font=mr.font("Amiri-Bold.ttf", 66), fill=gold + (255,), anchor="mm",
           direction="rtl", language="ar")
    d.text((W / 2, 350), f"The story of {en} (peace be upon him)", font=mr.font("Lora-var.ttf", 34),
           fill=(240, 234, 220, 230), anchor="mm")
    if part:
        pill = f"PART {part[0]} OF {part[1]}"
        f = mr.font("Lora-var.ttf", 26)
        tw = d.textlength(pill, font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 22, 388, W / 2 + tw / 2 + 22, 432), 22, outline=gold + (220,), width=2)
        d.text((W / 2, 410), pill, font=f, fill=gold + (255,), anchor="mm")
    if footer:
        d.text((W / 2, 1668), footer, font=mr.font("Lora-var.ttf", 24), fill=(240, 234, 220, 170), anchor="mm")
    d.text((W / 2, 1720), RECITER if not footer else f"Recitation: {RECITER}", font=mr.font("Lora-var.ttf", 34),
           fill=gold + (240,), anchor="mm")
    d.text((W / 2, 1772), mr.HANDLE, font=mr.font("Lora-var.ttf", 28), fill=(240, 234, 220, 190), anchor="mm")
    mr.with_shadow(img, path)
    mr.dim_panel(path)


def narration(text, out):
    """Arabic narration with a neural voice (edge-tts), slightly slow and calm."""
    if not out.exists():
        subprocess.run(["edge-tts", "--voice", VOICE, "--rate=-12%", "--text", text, "--write-media", str(out)],
                       check=True, timeout=120)
    return out


HARAKAT = re.compile("[\u064B-\u0652\u0670]")


def narr_card(ar, en, path):
    """The narration in Arabic (large, shown without harakat: cleaner) with the English subtitle under it."""
    ar = HARAKAT.sub("", ar)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(74, 44, -2):
        fa = mr.font("Amiri-Regular.ttf", size)
        la = mr.wrap(d, ar, fa, W - 170, rtl=True)
        lha = int(size * 1.75)
        es = max(30, int(size * 0.5))
        fe = mr.font("Lora-var.ttf", es)
        le = mr.wrap(d, en, fe, W - 190)
        lhe = int(es * 1.45)
        block = len(la) * lha + 56 + len(le) * lhe
        if block <= 960:
            break
    y = 975 - block / 2
    for ln in la:
        d.text((W / 2, y + lha / 2), ln, font=fa, fill=(250, 244, 230, 255), anchor="mm", direction="rtl", language="ar")
        y += lha
    y += 56
    for ln in le:
        d.text((W / 2, y + lhe / 2), ln, font=fe, fill=(225, 218, 200, 230), anchor="mm")
        y += lhe
    mr.with_shadow(img, path)


def level_gain(path, target=-17.0):
    """dB to bring a clip's average loudness to `target` (same level for narrator and recitation, no pumping)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    mx = re.search(r"max_volume: (-?[\d.]+) dB", r.stderr)
    gain = target - float(m.group(1)) if m else 0.0
    return min(gain, -1.0 - float(mx.group(1))) if mx else gain   # never push the peaks over -1 dB


def compose(segs, cards, audio, frame, total, out):
    """Scene clips one after another (soft fades), the frame and cards over them, the audio under them."""
    work = Path(frame).parent
    ins, f = [], []
    for i, (p, d_) in enumerate(segs):
        ins += ["-i", str(p)]
        f.append(f"[{i}:v]trim=duration={d_:.3f},setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.35,"
                 f"fade=t=out:st={max(0, d_ - 0.35):.3f}:d=0.35[s{i}]")
    f.append("".join(f"[s{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=2[bg]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(f), "-map", "[bg]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(work / "bg.mp4")],
                   check=True, timeout=1800)
    a_ins, a_f = [], []
    for i, (p, d_, lead) in enumerate(audio):
        a_ins += ["-i", str(p)]
        a_f.append(f"[{i}:a]aresample=48000:resampler=soxr,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                   f"highpass=f=70,volume={level_gain(p):.1f}dB,"
                   f"adelay={int(lead * 1000)}:all=1,apad=whole_dur={d_:.3f},atrim=0:{d_:.3f}[a{i}]")
    a_f.append("".join(f"[a{i}]" for i in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1,"
                 f"alimiter=limit=0.95,apad=whole_dur={total:.2f},aresample=48000[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a_ins, "-filter_complex", ";".join(a_f), "-map", "[aout]",
                    "-t", f"{total:.2f}", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(work / "audio.m4a")],
                   check=True, timeout=600)
    with open(work / "cards.txt", "w") as fh:
        for p, d_ in cards:
            fh.write(f"file '{Path(p).resolve()}'\nduration {d_:.3f}\n")
        fh.write(f"file '{Path(cards[-1][0]).resolve()}'\n")
    fc = ("[0:v]format=yuv420p,fps=30[b0];[b0][1:v]overlay=0:0:shortest=1[b1];[2:v]format=rgba,fps=30[c];"
          f"[b1][c]overlay=0:0:eof_action=repeat,fade=t=out:st={total - 0.8:.2f}:d=0.8[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "bg.mp4"), "-loop", "1", "-i", str(frame),
                    "-f", "concat", "-safe", "0", "-i", str(work / "cards.txt"), "-i", str(work / "audio.m4a"),
                    "-filter_complex", fc, "-map", "[v]", "-map", "3:a", "-t", f"{total:.2f}", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "copy",
                    "-movflags", "+faststart", str(out)], check=True, timeout=1800)


def scene(query, seconds, rnd, out):
    """A hand-picked Pixabay clip (int id, checked by eye: no people, buildings or animals), repeated if it is
    shorter than the line; or a search (str), falling back to calm sky footage when it finds nothing usable."""
    if isinstance(query, int):
        hit = nature.by_id(query)
        path = nature.clip_file(hit)
        real = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                              "-of", "csv=p=0", str(path)]).strip()) * nature.SLOW
        if real < 3:
            raise RuntimeError(f"clip {query} is too short ({real:.1f}s)")
        n = 1
        while real * n - nature.FADE * (n - 1) < seconds + 0.5 and n < 8:
            n += 1
        v = max(hit["videos"].values(), key=lambda x: x.get("width") or 0)
        print(f"  scene {query}: {real:.1f}s clip x{n} for {seconds:.1f}s (source up to {v.get('width')}x{v.get('height')})",
              flush=True)
        nature.render_background([(path, real, hit["id"])] * n, seconds, out)
        return out
    for q in (query, "clouds sky", "sunset sky"):
        try:
            return scene_clip(q, seconds, rnd, out)
        except RuntimeError as e:
            print("scene:", e)
    raise RuntimeError(f"no scene for {query!r}")


def render_narrated(key, part=1, seed=None):
    rnd = random.Random(seed)
    no, ar_name, en_name, parts = NARRATED[key]
    segs_in = parts[part - 1]
    chs = mr.chapters()
    folder = mr.RECITERS[RECITER]
    theme = mr.THEMES[0]
    work = mr.CACHE / "work" / f"story_{key}_{part}"
    work.mkdir(parents=True, exist_ok=True)
    frame_png(no, ar_name, en_name, work / "frame.png", part=(part, PARTS.get(key, len(parts))) if PARTS.get(key, len(parts)) > 1 else None, footer=f"Sources: {SOURCES}")
    segs, cards, audio, t = [], [], [], 0.0
    import time
    t0 = time.time()
    for i, sg in enumerate(segs_in):
        print(f"[{time.time() - t0:5.0f}s] segment {i + 1}/{len(segs_in)}: {sg[0]} {sg[1:3] if sg[0] == 'a' else ''}", flush=True)
        lead = 0.6 if i == 0 else 0.25
        if sg[0] == "n":
            _, text, en, query = sg
            mp3 = narration(text, work / f"n{i}.mp3")
            narr_card(text, en, work / f"card{i}.png")
            cards.append((work / f"card{i}.png", 0))
        else:
            _, su, ay, query = sg
            mp3 = mr.audio(folder, su, ay)
            ar, en = mr.verse(su, ay)
            for n in range(1, 6):
                pieces, shares = mr.split_parts(ar, en, n) if n > 1 else ([(ar, en)], [1.0])
                paths = [work / f"card{i}_{k}.png" for k in range(n)]
                if all(mr.card(theme, chs[su], su, ay, pa, pe, RECITER, pp, ref=f"Surah {chs[su]['name_simple']} · {su}:{ay}") for (pa, pe), pp in zip(pieces, paths)):
                    break
        dur = mr.duration(mp3) + lead + 0.45
        if sg[0] == "n":
            cards[-1] = (cards[-1][0], dur)
        else:
            cards += [(pp, dur * sh) for pp, sh in zip(paths, shares)]
        segs.append((scene(query, dur, rnd, work / f"bg{i}.mp4"), dur))
        audio.append((mp3, dur, lead))
        t += dur
    total = t + 1.2
    mr.OUT.mkdir(exist_ok=True)
    mp4 = mr.OUT / f"story_{key}_{part}.mp4"
    print(f"[{time.time() - t0:5.0f}s] composing {total:.1f}s", flush=True)
    compose(segs, cards, audio, work / "frame.png", total, mp4)
    print(mp4, round(total, 1), "s")
    return {"kind": "story", "file": str(mp4), "duration": round(total, 1), "prophet": key, "part": part,
            "title": f"Stories of the Prophets {no}/{TOTAL_PROPHETS} · {en_name} · Part {part} of {PARTS.get(key, len(parts))}"}


def render(key, seed=None):
    rnd = random.Random(seed)
    no, ar_name, en_name, scenes = STORIES[key]
    chs = mr.chapters()
    folder = mr.RECITERS[RECITER]
    theme = mr.THEMES[0]
    work = mr.CACHE / "work" / f"story_{key}"
    work.mkdir(parents=True, exist_ok=True)
    frame_png(no, ar_name, en_name, work / "frame.png")

    # timeline: one segment per ayah; the ayah card can be split over a few screens if long
    segs, cards, audio, t = [], [], [], 0.0
    lead = 0.6
    for s, a, query in scenes:
        mp3 = mr.audio(folder, s, a)
        dur = mr.duration(mp3) + (lead if not segs else 0) + 0.35
        ar, en = mr.verse(s, a)
        for n in range(1, 6):
            parts, shares = mr.split_parts(ar, en, n) if n > 1 else ([(ar, en)], [1.0])
            paths = [work / f"card_{s}_{a}_{k}.png" for k in range(n)]
            if all(mr.card(theme, chs[s], s, a, pa, pe, RECITER, pp, ref=f"Surah {chs[s]['name_simple']} · {s}:{a}") for (pa, pe), pp in zip(parts, paths)):
                break
        for pp, sh in zip(paths, shares):
            cards.append((pp, dur * sh))
        bg = scene_clip(query, dur, rnd, work / f"bg_{s}_{a}.mp4")
        segs.append((bg, dur))
        audio.append((mp3, dur))
        t += dur
    total = t + 1.5

    # background: the scene clips one after another, each fading in/out softly
    ins, f = [], []
    for i, (p, d_) in enumerate(segs):
        ins += ["-i", str(p)]
        f.append(f"[{i}:v]trim=duration={d_:.3f},setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.35,"
                 f"fade=t=out:st={max(0, d_ - 0.35):.3f}:d=0.35[s{i}]")
    f.append("".join(f"[s{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=2[bg]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(f), "-map", "[bg]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(work / "bg.mp4")],
                   check=True, timeout=1800)
    # recitation: each ayah starts with its scene
    a_ins, a_f = [], []
    for i, (p, d_) in enumerate(audio):
        a_ins += ["-i", str(p)]
        pre = f"adelay={int(lead * 1000)}:all=1," if i == 0 else ""
        a_f.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,{pre}apad=whole_dur={d_:.3f},atrim=0:{d_:.3f}[a{i}]")
    a_f.append("".join(f"[a{i}]" for i in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1,apad=whole_dur={total:.2f}[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a_ins, "-filter_complex", ";".join(a_f), "-map", "[aout]",
                    "-t", f"{total:.2f}", "-c:a", "aac", "-b:a", "160k", str(work / "audio.m4a")], check=True, timeout=600)
    with open(work / "cards.txt", "w") as fh:
        for p, d_ in cards:
            fh.write(f"file '{p.resolve()}'\nduration {d_:.3f}\n")
        fh.write(f"file '{cards[-1][0].resolve()}'\n")
    fc = ("[0:v]format=yuv420p,fps=30[b0];[b0][1:v]overlay=0:0:shortest=1[b1];[2:v]format=rgba,fps=30[c];"
          f"[b1][c]overlay=0:0:eof_action=repeat,fade=t=out:st={total - 0.8:.2f}:d=0.8[v]")
    mr.OUT.mkdir(exist_ok=True)
    mp4 = mr.OUT / f"story_{key}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "bg.mp4"), "-loop", "1", "-i", str(work / "frame.png"),
                    "-f", "concat", "-safe", "0", "-i", str(work / "cards.txt"), "-i", str(work / "audio.m4a"),
                    "-filter_complex", fc, "-map", "[v]", "-map", "3:a", "-t", f"{total:.2f}", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "copy",
                    "-movflags", "+faststart", str(mp4)], check=True, timeout=1800)
    first, last = scenes[0][:2], scenes[-1][:2]
    caption = (f"The story of {en_name} (peace be upon him), as Allah tells it in the Quran 🤍\n\n"
               f"Surah {chs[first[0]]['name_simple']} {first[0]}:{first[1]}-{last[1]} · recited by {RECITER}\n\n"
               f"Stories of the Prophets · {no} of {TOTAL_PROPHETS}. Follow for the next prophet tomorrow.\n\n"
               f"#storiesoftheprophets #quran #prophet{en_name.lower()} #islam #qasasalanbiya")
    print(mp4, round(total, 1), "s")
    return {"kind": "story", "file": str(mp4), "caption": caption, "duration": round(total, 1), "prophet": key,
            "title": f"Stories of the Prophets {no}/{TOTAL_PROPHETS} · {en_name}"}


def story_meta(key, part):
    """Title, caption, cover text and series order of one part of a narrated story (for the queue)."""
    no, ar_name, en_name, parts = NARRATED[key]
    n = PARTS.get(key, len(parts))
    chs = mr.chapters()
    ptitle = (PART_TITLES.get(key) or [""] * n)[part - 1]
    refs = []
    for seg in parts[part - 1]:
        if seg[0] == "a":
            r = f"{chs[seg[1]]['name_simple']} {seg[1]}:{seg[2]}"
            if r not in refs:
                refs.append(r)
    pt = f"Part {part} of {n}" if n > 1 else ""
    if part < n:
        nxt = f"Part {part + 1} comes next on our page (Monday, Wednesday and Saturday at 15:00)."
    else:
        i = [k for k, _ in SERIES].index(key)
        nxt = f"Next: the story of the Prophet {SERIES[i + 1][1]}." if i + 1 < len(SERIES) else "This is the last story of the series."
    peace = "" if key == "muhammad" else " (peace be upon him)"
    caption = (f"The story of {en_name}{peace}{' · ' + pt if pt else ''}{': ' + ptitle if ptitle else ''} 🤍\n\n"
               f"Stories of the Prophets · {no} of {TOTAL_PROPHETS}\n"
               f"Told from the Quran, Sahih al-Bukhari and Ibn Kathir's Qasas al-Anbiya.\n"
               + (f"Ayat recited by {RECITER}: {', '.join(refs)}\n" if refs else "") +
               f"\n{nxt}\nFollow so you don't miss a part, and share it with someone who loves these stories.\n\n"
               f"#storiesoftheprophets #qasasalanbiya #prophet{en_name.lower().replace(' ', '')} #quran #islam")
    return {"kind": "story", "prophet": key, "part": part, "parts": n, "series_no": no, "order": no * 100 + part,
            "caption": caption, "keep_as": f"story-{key}-{part}",
            "title": " · ".join(x for x in (f"Stories of the Prophets {no}/{TOTAL_PROPHETS}", en_name, pt, ptitle) if x),
            "cover_label": f"Stories of the Prophets · {no} / {TOTAL_PROPHETS}", "cover_ar": f"قصة {ar_name}",
            "cover_en": f"The story of {en_name}", "cover_sub": " · ".join(x for x in (pt, ptitle) if x)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("prophet", choices=list(STORIES) + list(NARRATED))
    ap.add_argument("--part", type=int, default=1)
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    if a.prophet in NARRATED:
        render_narrated(a.prophet, a.part, a.seed)
    else:
        render(a.prophet, a.seed)

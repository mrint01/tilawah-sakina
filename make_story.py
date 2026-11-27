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
PARTS = {"adam": 2, "idris": 1, "nuh": 3, "hud": 2, "salih": 2, "ibrahim": 5, "lut": 2, "ismail": 1, "ishaq": 1, "yaqub": 1, "yusuf": 6, "ayyub": 1, "shuayb": 2, "musa": 8, "harun": 1, "dhulkifl": 1, "dawud": 2, "sulayman": 3}
PART_TITLES = {"adam": ["The creation", "The garden"], "idris": ["Raised to a high place"],
               "nuh": ["The call", "The Ark", "The Flood"], "hud": ["The people of 'Ad", "The wind"],
               "salih": ["The she-camel", "The blast"],
               "ibrahim": ["The search", "The idols", "The fire", "The valley", "The sacrifice"],
               "lut": ["The city", "The punishment"],
               "ismail": ["Son of the valley"],
               "ishaq": ["The good news"],
               "yaqub": ["Beautiful patience"],
               "yusuf": ["The dream", "To Egypt", "The test", "The prison", "The king's dream", "The reunion"],
               "ayyub": ["Patience"],
               "shuayb": ["The fair measure", "The day of the shadow"],
               "musa": ["The river", "Madyan", "The fire on the mountain", "Before Pharaoh", "The magicians", "The sea", "The calf", "Musa and al-Khidr"],
               "harun": ["The helper"], "dhulkifl": ["Among the patient"], "dawud": ["Dawud and Jalut", "The mountains glorified with him"],
               "sulayman": ["The kingdom", "The ant and the hoopoe", "The queen of Saba"]}
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
    "hud": (4, "هود", "Hud", [
        [  # Part 1: the people of 'Ad (Al-A'raf 7:65-72, Hud 11:50-57, Ash-Shu'ara 26:123-135, Fussilat 41:15, Al-Fajr 89:6-8)
            ("n", "بَعْدَ نُوحٍ، عَاشَتْ فِي جَنُوبِ جَزِيرَةِ الْعَرَبِ، بَيْنَ كُثْبَانِ الْأَحْقَافِ، قَبِيلَةٌ اسْمُهَا عَادٌ.",
             "After Nuh, in the south of Arabia, among the sand dunes of Al-Ahqaf, lived a tribe called 'Ad.", 16139),
            ("n", "أَعْطَاهُمُ اللَّهُ قُوَّةً عَظِيمَةً، وَأَجْسَامًا طَوِيلَةً، وَبَنَوْا مَدِينَةً لَمْ يُخْلَقْ مِثْلُهَا فِي الْبِلَادِ.",
             "Allah gave them great strength and tall bodies, and they built a city whose like had never been made in "
             "any land.", 258863),
            ("a", 89, 7, 222163),
            ("n", "لَكِنَّهُمْ نَسُوا اللَّهَ، وَعَبَدُوا الْأَصْنَامَ، وَظَلَمُوا النَّاسَ، وَاغْتَرُّوا بِقُوَّتِهِمْ.",
             "But they forgot Allah. They worshipped idols, oppressed people, and were deceived by their own strength.",
             304330),
            ("n", "فَأَرْسَلَ اللَّهُ إِلَيْهِمْ رَجُلًا مِنْهُمْ، يَعْرِفُونَ صِدْقَهُ وَنَسَبَهُ: هُودًا عَلَيْهِ السَّلَامُ.",
             "So Allah sent them a man from among themselves, whose honesty and family they knew: Hud, peace be upon "
             "him.", 26085),
            ("a", 7, 65, 284577),
            ("n", "قَالَ لَهُمْ: لَا أَسْأَلُكُمْ أَجْرًا، إِنَّمَا أَجْرِي عَلَى اللَّهِ. وَدَعَاهُمْ إِلَى التَّوْبَةِ.",
             "He told them: I ask you for no reward, my reward is only from Allah. And he called them to repent.", 42029),
            ("a", 11, 52, 152740),
            ("n", "فَقَالُوا: مَا جِئْتَنَا بِدَلِيلٍ، وَلَنْ نَتْرُكَ آلِهَتَنَا لِقَوْلِكَ، وَلَعَلَّ بَعْضَ آلِهَتِنَا أَصَابَكَ بِسُوءٍ.",
             "They said: you have brought us no proof, we will not leave our gods because you say so. Perhaps one of "
             "our gods has struck you with harm.", 147663),
            ("n", "فَأَجَابَهُمْ هُودٌ بِثِقَةِ الْمُؤْمِنِ بِرَبِّهِ:",
             "Hud answered them with the confidence of a believer in his Lord:", 1844),
            ("a", 11, 56, 175487),
            ("n", "لَكِنَّهُمُ ازْدَادُوا كِبْرًا، وَقَالُوا: لَا أَحَدَ أَقْوَى مِنَّا. وَنَسُوا أَنَّ اللَّهَ الَّذِي خَلَقَهُمْ هُوَ أَشَدُّ مِنْهُمْ قُوَّةً.",
             "But they only grew more arrogant. No one is stronger than us, they said. They forgot that Allah, who "
             "created them, is far greater in strength.", 225775),
            ("n", "فِي الْجُزْءِ الثَّانِي: الرِّيحُ.",
             "In part two: the wind.", 70898),
        ],
        [  # Part 2: the wind (Al-Ahqaf 46:24-25, Al-Haqqah 69:6-8, Hud 11:58-60; Sahih al-Bukhari 1035)
            ("n", "وَحُبِسَ الْمَطَرُ عَنْ عَادٍ، فَجَفَّتِ الْأَرْضُ، وَطَالَ انْتِظَارُهُمْ لِلْغَيْثِ.",
             "Then the rain was held back from 'Ad. The land dried up, and they waited a long time for rain.", 328726),
            ("n", "وَفِي يَوْمٍ، رَأَوْا سَحَابًا عَظِيمًا يَتَّجِهُ نَحْوَ أَوْدِيَتِهِمْ، فَفَرِحُوا بِهِ.",
             "One day, they saw a great cloud heading toward their valleys, and they rejoiced.", 9041),
            ("a", 46, 24, 230528),
            ("n", "كَانَتْ رِيحًا بَارِدَةً شَدِيدَةً، تُدَمِّرُ كُلَّ شَيْءٍ بِأَمْرِ رَبِّهَا.",
             "It was a fierce, bitterly cold wind, destroying everything by the command of its Lord.", 70899),
            ("a", 69, 6, 22070),
            ("a", 69, 7, 63281),
            ("n", "وَنَجَّى اللَّهُ هُودًا وَالَّذِينَ آمَنُوا مَعَهُ بِرَحْمَتِهِ.",
             "And Allah saved Hud and those who believed with him, by His mercy.", 145260),
            ("a", 11, 58, 1844),
            ("n", "وَقَالَ نَبِيُّنَا مُحَمَّدٌ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ: نُصِرْتُ بِالصَّبَا، وَأُهْلِكَتْ عَادٌ بِالدَّبُورِ. رَوَاهُ الْبُخَارِيُّ.",
             "Our Prophet Muhammad ﷺ said: I was helped by the east wind, and 'Ad were destroyed by the west wind. "
             "(Sahih al-Bukhari)", 212437),
            ("n", "لَمْ تَنْفَعْهُمْ قُوَّتُهُمْ وَلَا بُنْيَانُهُمْ. فَالْقُوَّةُ كُلُّهَا لِلَّهِ.",
             "Neither their strength nor their buildings could save them. All strength belongs to Allah.", 365737),
            ("n", "انْتَهَتْ قِصَّةُ هُودٍ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ صَالِحٌ عَلَيْهِ السَّلَامُ.",
             "This was the story of Hud, peace be upon him. Next: the Prophet Salih, peace be upon him.", 175495),
        ],
    ]),
    "salih": (5, "صالح", "Salih", [
        [  # Part 1: the she-camel (Hud 11:61-64, Ash-Shu'ara 26:141-156, Al-A'raf 7:73-74, Al-Fajr 89:9)
            ("n", "بَعْدَ عَادٍ، سَكَنَتْ قَبِيلَةُ ثَمُودَ فِي أَرْضِ الْحِجْرِ، فِي شَمَالِ جَزِيرَةِ الْعَرَبِ.",
             "After 'Ad, the tribe of Thamud lived in the land of Al-Hijr, in the north of Arabia.", 69321),
            ("n", "نَحَتُوا بُيُوتَهُمْ فِي الْجِبَالِ، وَعَاشُوا بَيْنَ الْبَسَاتِينِ وَالْعُيُونِ، فِي نِعْمَةٍ عَظِيمَةٍ.",
             "They carved their homes into the mountains, and lived among gardens and springs, in great blessing.",
             6538),
            ("a", 89, 9, 304330),
            ("n", "لَكِنَّهُمْ عَبَدُوا الْأَصْنَامَ، فَأَرْسَلَ اللَّهُ إِلَيْهِمْ أَخَاهُمْ صَالِحًا عَلَيْهِ السَّلَامُ.",
             "But they worshipped idols. So Allah sent them their brother, Salih, peace be upon him.", 212579),
            ("a", 11, 61, 71494),
            ("n", "فَقَالُوا: كُنَّا نَرْجُو أَنْ تَكُونَ سَيِّدًا فِينَا. ثُمَّ طَلَبُوا مِنْهُ آيَةً تَدُلُّ عَلَى صِدْقِهِ.",
             "They said: we had hoped you would be a leader among us. Then they asked him for a sign to prove he was "
             "telling the truth.", 14955),
            ("n", "فَأَخْرَجَ اللَّهُ لَهُمْ نَاقَةً، آيَةً وَاضِحَةً. لَهَا يَوْمٌ تَشْرَبُ فِيهِ مِنَ الْمَاءِ، وَلَهُمْ يَوْمٌ.",
             "So Allah brought forth a she-camel for them, a clear sign. She had one day to drink from the water, and "
             "they had another.", 7452),
            ("a", 26, 155, 220161),
            ("a", 26, 156, 190331),
            ("n", "فِي الْجُزْءِ الثَّانِي: الصَّيْحَةُ.",
             "In part two: the blast.", 7215),
        ],
        [  # Part 2: the blast (Ash-Shams 91:11-15, Al-A'raf 7:77-79, Hud 11:65-68, An-Naml 27:48-53; Sahih al-Bukhari 433)
            ("n", "عَاشَتِ النَّاقَةُ بَيْنَهُمْ، لَكِنَّ الْمُتَكَبِّرِينَ ضَاقُوا بِهَا، وَتَآمَرُوا عَلَى قَتْلِهَا.",
             "The she-camel lived among them. But the arrogant could not bear her, and they plotted to kill her.", 69320),
            ("a", 91, 12, 316435),
            ("n", "فَقَتَلَهَا أَشْقَاهُمْ، وَرَضِيَ قَوْمُهُ بِفِعْلِهِ، ثُمَّ تَحَدَّوْا صَالِحًا.",
             "The most wretched of them killed her, his people approved of what he did, and then they challenged "
             "Salih.", 284562),
            ("a", 7, 77, 43953),
            ("n", "فَأَخْبَرَهُمْ صَالِحٌ أَنَّ الْعَذَابَ سَيَأْتِيهِمْ بَعْدَ ثَلَاثَةِ أَيَّامٍ.",
             "Salih told them the punishment would come to them after three days.", 88562),
            ("a", 11, 65, 12759),
            ("n", "وَتَآمَرَ تِسْعَةُ رِجَالٍ عَلَى قَتْلِ صَالِحٍ وَأَهْلِهِ فِي اللَّيْلِ، فَمَكَرُوا، وَمَكَرَ اللَّهُ، وَهُمْ لَا يَشْعُرُونَ.",
             "Nine men plotted to kill Salih and his family at night. They planned, and Allah planned, while they did "
             "not know.", 205427),
            ("n", "وَفِي صَبَاحِ الْيَوْمِ الرَّابِعِ، جَاءَتْهُمْ صَيْحَةٌ عَظِيمَةٌ، وَرَجَفَتْ بِهِمُ الْأَرْضُ.",
             "On the morning of the fourth day, a mighty blast came upon them, and the earth shook beneath them.",
             283428),
            ("a", 11, 67, 125192),
            ("a", 11, 66, 328740),
            ("n", "وَلَمَّا مَرَّ نَبِيُّنَا مُحَمَّدٌ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ بِالْحِجْرِ، قَالَ: لَا تَدْخُلُوا مَسَاكِنَ الَّذِينَ ظَلَمُوا "
                  "أَنْفُسَهُمْ إِلَّا أَنْ تَكُونُوا بَاكِينَ. رَوَاهُ الْبُخَارِيُّ.",
             "When our Prophet Muhammad ﷺ passed by Al-Hijr, he said: do not enter the homes of those who wronged "
             "themselves unless you are weeping. (Sahih al-Bukhari)", 86847),
            ("n", "انْتَهَتْ قِصَّةُ صَالِحٍ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: خَلِيلُ اللَّهِ إِبْرَاهِيمُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Salih, peace be upon him. Next: Ibrahim, the friend of Allah, peace be upon him.",
             201308),
        ],
    ]),
    "ibrahim": (6, "إبراهيم", "Ibrahim", [
        [  # Part 1: the search (Al-An'am 6:74-79, Maryam 19:41-48)
            ("n", "فِي أَرْضِ الْعِرَاقِ، بَيْنَ قَوْمٍ يَعْبُدُونَ الْأَصْنَامَ وَالْكَوَاكِبَ، نَشَأَ إِبْرَاهِيمُ عَلَيْهِ السَّلَامُ. "
                  "وَكَانَ أَبُوهُ آزَرُ يَصْنَعُ الْأَصْنَامَ.",
             "In the land of Iraq, among a people who worshipped idols and stars, Ibrahim grew up, peace be upon him. "
             "His father Azar made idols.", 64745),
            ("a", 6, 74, 110685),
            ("n", "وَأَرَادَ إِبْرَاهِيمُ أَنْ يُبَيِّنَ لِقَوْمِهِ أَنَّ مَا يَغِيبُ وَيَزُولُ لَا يَكُونُ رَبًّا.",
             "Ibrahim wanted to show his people that what fades and disappears cannot be a lord.", 1099),
            ("a", 6, 76, 16802),
            ("a", 6, 77, 148100),
            ("a", 6, 78, 152483),
            ("a", 6, 79, 30850),
            ("n", "وَدَعَا أَبَاهُ بِرِفْقٍ وَأَدَبٍ:",
             "And he called his father, gently and with respect:", 236740),
            ("a", 19, 42, 50746),
            ("n", "فَغَضِبَ أَبُوهُ وَهَدَّدَهُ بِالرَّجْمِ. فَقَالَ إِبْرَاهِيمُ: سَلَامٌ عَلَيْكَ، سَأَسْتَغْفِرُ لَكَ رَبِّي.",
             "His father grew angry and threatened to stone him. Ibrahim said: peace be upon you, I will ask my Lord "
             "to forgive you.", 152699),
            ("n", "فِي الْجُزْءِ الثَّانِي: الْأَصْنَامُ.",
             "In part two: the idols.", 6367),
        ],
        [  # Part 2: the idols (Al-Anbiya 21:51-67, As-Saffat 37:88-96)
            ("n", "وَجَاءَ يَوْمُ عِيدٍ لِقَوْمِهِ، فَخَرَجُوا جَمِيعًا مِنَ الْمَدِينَةِ، وَبَقِيَ إِبْرَاهِيمُ.",
             "A feast day of his people came. They all went out of the city, and Ibrahim stayed behind.", 149180),
            ("a", 21, 57, 225775),
            ("n", "فَدَخَلَ بَيْتَ الْأَصْنَامِ، فَكَسَّرَهَا كُلَّهَا، إِلَّا كَبِيرَهَا.",
             "He went into the house of the idols, and broke them all, except the biggest one.", 128271),
            ("a", 21, 58, 134115),
            ("n", "فَلَمَّا رَجَعُوا وَرَأَوْا أَصْنَامَهُمْ مُحَطَّمَةً، قَالُوا: مَنْ فَعَلَ هَذَا؟ وَجَاؤُوا بِإِبْرَاهِيمَ أَمَامَ النَّاسِ.",
             "When they came back and saw their idols smashed, they said: who did this? And they brought Ibrahim "
             "before the people.", 2147),
            ("a", 21, 62, 9041),
            ("a", 21, 63, 319665),
            ("n", "فَنَظَرَ بَعْضُهُمْ إِلَى بَعْضٍ، وَعَرَفُوا أَنَّ الْأَصْنَامَ لَا تَنْطِقُ وَلَا تَنْفَعُ.",
             "They looked at one another. They knew the idols could not speak, nor do any good.", 93914),
            ("a", 21, 66, 253475),
            ("n", "فِي الْجُزْءِ الثَّالِثِ: النَّارُ.",
             "In part three: the fire.", 21531),
        ],
        [  # Part 3: the fire and the king (Al-Anbiya 21:68-71, Al-Baqarah 2:258, Al-'Ankabut 29:26; Sahih al-Bukhari 4563)
            ("n", "فَقَالُوا: أَحْرِقُوهُ. وَجَمَعُوا حَطَبًا كَثِيرًا، وَأَشْعَلُوا نَارًا عَظِيمَةً.",
             "They said: burn him. They gathered a great amount of wood, and lit a huge fire.", 192687),
            ("a", 21, 68, 2336),
            ("n", "وَأَلْقَوْهُ فِيهَا، فَقَالَ إِبْرَاهِيمُ: حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ. رَوَاهُ الْبُخَارِيُّ.",
             "They threw him into it, and Ibrahim said: Allah is enough for us, and He is the best to rely on. "
             "(Sahih al-Bukhari)", 51145),
            ("a", 21, 69, 66810),
            ("n", "فَلَمْ تَضُرَّهُ النَّارُ، وَخَرَجَ مِنْهَا سَالِمًا.",
             "The fire did not harm him, and he came out of it safe.", 189813),
            ("a", 21, 70, 50727),
            ("n", "ثُمَّ جَادَلَهُ مَلِكُ تِلْكَ الْبِلَادِ، الَّذِي ادَّعَى أَنَّهُ يُحْيِي وَيُمِيتُ.",
             "Then the king of that land argued with him, the one who claimed that he gives life and death.", 2150),
            ("a", 2, 258, 246214),
            ("n", "وَتَرَكَ إِبْرَاهِيمُ قَوْمَهُ، وَهَاجَرَ إِلَى رَبِّهِ، وَمَعَهُ زَوْجَتُهُ سَارَةُ، وَابْنُ أَخِيهِ لُوطٌ.",
             "Ibrahim left his people and emigrated for the sake of his Lord, with his wife Sarah and his nephew Lut.",
             236738),
            ("n", "فِي الْجُزْءِ الرَّابِعِ: هَاجَرُ وَإِسْمَاعِيلُ فِي الْوَادِي.",
             "In part four: Hajar and Ismail in the valley.", 87158),
        ],
        [  # Part 4: the valley of Makkah (Ibrahim 14:37, Al-Baqarah 2:125-127; Sahih al-Bukhari 3364)
            ("n", "وَرَزَقَ اللَّهُ إِبْرَاهِيمَ عَلَى كِبَرِهِ وَلَدًا مِنْ زَوْجَتِهِ هَاجَرَ، اسْمُهُ إِسْمَاعِيلُ.",
             "In his old age, Allah gave Ibrahim a son from his wife Hajar, named Ismail.", 57803),
            ("n", "وَأَمَرَهُ اللَّهُ أَنْ يَأْخُذَهُمَا إِلَى وَادٍ لَيْسَ فِيهِ مَاءٌ وَلَا زَرْعٌ: وَادِي مَكَّةَ.",
             "Allah commanded him to take them to a valley with no water and no plants: the valley of Makkah.", 71494),
            ("n", "فَلَمَّا هَمَّ بِالرُّجُوعِ، قَالَتْ هَاجَرُ: آللَّهُ أَمَرَكَ بِهَذَا؟ قَالَ: نَعَمْ. قَالَتْ: إِذَنْ لَا يُضَيِّعُنَا. "
                  "رَوَاهُ الْبُخَارِيُّ.",
             "As he turned to leave, Hajar asked: did Allah command you to do this? He said: yes. She said: then He will "
             "not abandon us. (Sahih al-Bukhari)", 212579),
            ("a", 14, 37, 26085),
            ("n", "وَنَفِدَ الْمَاءُ، فَسَعَتْ هَاجَرُ بَيْنَ الصَّفَا وَالْمَرْوَةِ سَبْعَ مَرَّاتٍ تَبْحَثُ عَنِ الْمَاءِ. وَمِنْ هُنَا كَانَ السَّعْيُ فِي الْحَجِّ.",
             "The water ran out, and Hajar ran between Safa and Marwa seven times, looking for water. This is where the "
             "sa'i of Hajj comes from.", 284562),
            ("n", "فَبَعَثَ اللَّهُ مَلَكًا، فَتَفَجَّرَ مَاءُ زَمْزَمَ.",
             "Then Allah sent an angel, and the water of Zamzam burst forth.", 14121),
            ("n", "وَسَكَنَ النَّاسُ حَوْلَ الْمَاءِ، وَكَبِرَ إِسْمَاعِيلُ. ثُمَّ رَفَعَ إِبْرَاهِيمُ وَإِسْمَاعِيلُ قَوَاعِدَ الْبَيْتِ الْحَرَامِ.",
             "People settled around the water, and Ismail grew up. Then Ibrahim and Ismail raised the foundations of "
             "the Sacred House.", 7127),
            ("a", 2, 127, 250742),
            ("n", "فِي الْجُزْءِ الْخَامِسِ: الذَّبْحُ الْعَظِيمُ.",
             "In part five: the great sacrifice.", 103542),
        ],
        [  # Part 5: the sacrifice (As-Saffat 37:99-111, An-Nisa 4:125)
            ("n", "وَلَمَّا كَبِرَ إِسْمَاعِيلُ وَصَارَ يَمْشِي مَعَ أَبِيهِ، رَأَى إِبْرَاهِيمُ فِي الْمَنَامِ أَنَّهُ يَذْبَحُهُ. وَرُؤْيَا الْأَنْبِيَاءِ وَحْيٌ.",
             "When Ismail was old enough to walk with his father, Ibrahim saw in a dream that he was sacrificing him. "
             "And the dreams of prophets are revelation.", 28931),
            ("a", 37, 102, 325636),
            ("n", "فَاسْتَسْلَمَ الْأَبُ وَالِابْنُ لِأَمْرِ اللَّهِ.",
             "The father and the son both submitted to the command of Allah.", 18390),
            ("a", 37, 103, 277097),
            ("a", 37, 104, 260397),
            ("a", 37, 105, 236740),
            ("a", 37, 107, 59291),
            ("n", "وَيَذْكُرُ الْمُسْلِمُونَ هَذَا الْيَوْمَ فِي كُلِّ عِيدِ أَضْحَى.",
             "Muslims remember this day at every Eid al-Adha.", 236738),
            ("n", "وَأَكْرَمَ اللَّهُ إِبْرَاهِيمَ، فَاتَّخَذَهُ خَلِيلًا.",
             "And Allah honoured Ibrahim: He took him as a close friend.", 30850),
            ("a", 4, 125, 7127),
            ("n", "انْتَهَتْ قِصَّةُ إِبْرَاهِيمَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ لُوطٌ عَلَيْهِ السَّلَامُ.",
             "This was the story of Ibrahim, peace be upon him. Next: the Prophet Lut, peace be upon him.", 238507),
        ],
    ]),
    "lut": (7, "لوط", "Lut", [
        [  # Part 1: the city (Al-A'raf 7:80-82, Ash-Shu'ara 26:160-169, Al-'Ankabut 29:28-30)
            ("n", "آمَنَ لُوطٌ بِعَمِّهِ إِبْرَاهِيمَ وَهَاجَرَ مَعَهُ، ثُمَّ أَرْسَلَهُ اللَّهُ إِلَى قَوْمِ سَدُومَ، قُرْبَ الْبَحْرِ الْمَيِّتِ.",
             "Lut believed in his uncle Ibrahim and emigrated with him. Then Allah sent him to the people of Sodom, "
             "near the Dead Sea.", 128114),
            ("n", "كَانُوا يَفْعَلُونَ فَاحِشَةً لَمْ يَفْعَلْهَا أَحَدٌ قَبْلَهُمْ، وَيَقْطَعُونَ الطَّرِيقَ، وَيَأْتُونَ الْمُنْكَرَ فِي مَجَالِسِهِمْ عَلَنًا.",
             "They committed an indecency no one before them had done. They robbed travellers, and did evil openly in "
             "their gatherings.", 59252),
            ("a", 7, 80, 234450),
            ("n", "دَعَاهُمْ لُوطٌ إِلَى تَقْوَى اللَّهِ وَالطَّهَارَةِ، وَلَمْ يَطْلُبْ مِنْهُمْ أَجْرًا.",
             "Lut called them to fear Allah and to be pure, and he asked them for no reward.", 352978),
            ("a", 26, 164, 206379),
            ("n", "فَرَدُّوا عَلَيْهِ بِالسُّخْرِيَةِ، وَعَدُّوا الطَّهَارَةَ عَيْبًا.",
             "They answered him with mockery, and treated purity as a fault.", 244539),
            ("a", 7, 82, 349452),
            ("n", "فَدَعَا لُوطٌ رَبَّهُ:",
             "So Lut called upon his Lord:", 2145),
            ("a", 29, 30, 212057),
            ("n", "فِي الْجُزْءِ الثَّانِي: الْعَذَابُ.",
             "In part two: the punishment.", 28916),
        ],
        [  # Part 2: the punishment (Hud 11:69-83, Al-Hijr 15:57-77, Al-'Ankabut 29:31-35, At-Tahrim 66:10)
            ("n", "مَرَّتِ الْمَلَائِكَةُ بِإِبْرَاهِيمَ أَوَّلًا، فَبَشَّرُوهُ بِإِسْحَاقَ، وَأَخْبَرُوهُ أَنَّهُمْ أُرْسِلُوا إِلَى قَوْمِ لُوطٍ.",
             "The angels passed by Ibrahim first. They gave him the good news of Ishaq, and told him they had been sent "
             "to the people of Lut.", 34623),
            ("a", 29, 31, 241748),
            ("n", "ثُمَّ جَاؤُوا لُوطًا فِي صُورَةِ شَبَابٍ حِسَانٍ، فَخَافَ عَلَيْهِمْ مِنْ قَوْمِهِ.",
             "Then they came to Lut in the form of handsome young men, and he feared for them because of his people.",
             32585),
            ("a", 11, 77, 174891),
            ("n", "وَأَسْرَعَ قَوْمُهُ إِلَى بَيْتِهِ، فَقَالَ لَهُمْ: اتَّقُوا اللَّهَ، وَلَا تُخْزُونِي فِي ضَيْفِي.",
             "His people rushed to his house. He told them: fear Allah, and do not disgrace me with my guests.", 205009),
            ("a", 11, 81, 315523),
            ("n", "فَخَرَجَ لُوطٌ لَيْلًا بِالْمُؤْمِنِينَ مِنْ أَهْلِهِ. وَبَقِيَتِ امْرَأَتُهُ مَعَ الْقَوْمِ، فَقَدْ كَانَتْ عَلَى كُفْرِهِمْ.",
             "Lut left at night with the believers of his family. His wife stayed behind with the people, for she shared "
             "their disbelief.", 219754),
            ("n", "وَعِنْدَ الشُّرُوقِ، جَاءَ أَمْرُ اللَّهِ.",
             "And at sunrise, the command of Allah came.", 92312),
            ("a", 11, 82, 260564),
            ("a", 29, 35, 65094),
            ("n", "انْتَهَتْ قِصَّةُ لُوطٍ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ إِسْمَاعِيلُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Lut, peace be upon him. Next: the Prophet Ismail, peace be upon him.", 22183),
        ],
    ]),
    "ismail": (8, "إسماعيل", "Ismail", [
        [  # One part: As-Saffat 37:101, Al-Baqarah 2:127-129, Maryam 19:54-55; Sahih al-Bukhari 3364, 2899
            ("n", "نَشَأَ إِسْمَاعِيلُ بْنُ إِبْرَاهِيمَ وَهَاجَرَ فِي وَادِي مَكَّةَ، عِنْدَ مَاءِ زَمْزَمَ.",
             "Ismail, the son of Ibrahim and Hajar, grew up in the valley of Makkah, by the water of Zamzam.", 7452),
            ("n", "وَوَصَفَهُ اللَّهُ بِالْحِلْمِ، فَقَدْ صَبَرَ حِينَ أَخْبَرَهُ أَبُوهُ بِالرُّؤْيَا.",
             "Allah described him as forbearing: he was patient when his father told him about the dream.", 59291),
            ("a", 37, 101, 280486),
            ("n", "وَنَزَلَتْ قَبِيلَةُ جُرْهُمَ عِنْدَ زَمْزَمَ، فَتَعَلَّمَ مِنْهُمُ الْعَرَبِيَّةَ، وَتَزَوَّجَ مِنْهُمْ. رَوَاهُ الْبُخَارِيُّ.",
             "The tribe of Jurhum settled by Zamzam. He learned Arabic from them, and married among them. "
             "(Sahih al-Bukhari)", 69320),
            ("n", "وَكَانَ رَامِيًا مَاهِرًا، قَالَ نَبِيُّنَا صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ: ارْمُوا بَنِي إِسْمَاعِيلَ، فَإِنَّ أَبَاكُمْ كَانَ رَامِيًا. "
                  "رَوَاهُ الْبُخَارِيُّ.",
             "He was a skilled archer. Our Prophet ﷺ said: shoot, children of Ismail, for your father was an archer. "
             "(Sahih al-Bukhari)", 284577),
            ("n", "وَبَنَى الْكَعْبَةَ مَعَ أَبِيهِ، وَدَعَوَا اللَّهَ:",
             "He built the Kaaba with his father, and together they prayed:", 7127),
            ("a", 2, 128, 260397),
            ("n", "وَأَثْنَى اللَّهُ عَلَيْهِ فِي الْقُرْآنِ:",
             "And Allah praised him in the Quran:", 175495),
            ("a", 19, 54, 328740),
            ("a", 19, 55, 46936),
            ("n", "وَمِنْ ذُرِّيَّتِهِ جَاءَ خَاتَمُ الْأَنْبِيَاءِ مُحَمَّدٌ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ، إِجَابَةً لِدُعَاءِ إِبْرَاهِيمَ وَإِسْمَاعِيلَ.",
             "From his descendants came the last of the prophets, Muhammad ﷺ, an answer to the prayer of Ibrahim and "
             "Ismail.", 48899),
            ("a", 2, 129, 237673),
            ("n", "انْتَهَتْ قِصَّةُ إِسْمَاعِيلَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ إِسْحَاقُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Ismail, peace be upon him. Next: the Prophet Ishaq, peace be upon him.", 365737),
        ],
    ]),
    "ishaq": (9, "إسحاق", "Ishaq", [
        [  # One part: Hud 11:69-73, Adh-Dhariyat 51:24-30, As-Saffat 37:112-113, Al-Anbiya 21:72
            ("n", "كَبِرَتْ سَارَةُ زَوْجَةُ إِبْرَاهِيمَ، وَلَمْ يُرْزَقَا وَلَدًا مِنْهَا.",
             "Sarah, the wife of Ibrahim, grew old, and they had no child together.", 2950),
            ("n", "فَجَاءَتْ إِبْرَاهِيمَ مَلَائِكَةٌ فِي صُورَةِ ضُيُوفٍ، فَقَدَّمَ لَهُمْ عِجْلًا مَشْوِيًّا، فَلَمْ يَأْكُلُوا، فَخَافَ مِنْهُمْ.",
             "Angels came to Ibrahim in the form of guests. He brought them a roasted calf, but they did not eat, and "
             "he felt afraid of them.", 38998),
            ("n", "فَقَالُوا: لَا تَخَفْ، إِنَّا أُرْسِلْنَا إِلَى قَوْمِ لُوطٍ.",
             "They said: do not be afraid, we have been sent to the people of Lut.", 2150),
            ("a", 11, 71, 237672),
            ("a", 11, 72, 22713),
            ("a", 11, 73, 2266),
            ("n", "وَوُلِدَ إِسْحَاقُ، فَكَانَ نَبِيًّا مِنَ الصَّالِحِينَ، وَبَارَكَ اللَّهُ عَلَيْهِ وَعَلَى أَبِيهِ.",
             "Ishaq was born. He was a prophet, one of the righteous, and Allah blessed him and his father.", 46936),
            ("a", 37, 112, 1844),
            ("a", 37, 113, 175487),
            ("n", "وَمِنْ إِسْحَاقَ جَاءَ يَعْقُوبُ، وَمِنْ ذُرِّيَّةِ يَعْقُوبَ جَاءَ أَنْبِيَاءُ بَنِي إِسْرَائِيلَ.",
             "From Ishaq came Ya'qub, and from the children of Ya'qub came the prophets of the Children of Israel.",
             179200),
            ("a", 21, 72, 246856),
            ("n", "انْتَهَتْ قِصَّةُ إِسْحَاقَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ يَعْقُوبُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Ishaq, peace be upon him. Next: the Prophet Ya'qub, peace be upon him.", 21175),
        ],
    ]),
    "yaqub": (10, "يعقوب", "Ya'qub", [
        [  # One part: Yusuf 12:18, 12:83-87, Al-Baqarah 2:132-133, Sad 38:45-47
            ("n", "يَعْقُوبُ بْنُ إِسْحَاقَ، وَيُسَمَّى إِسْرَائِيلَ. وَمِنْ أَبْنَائِهِ الِاثْنَيْ عَشَرَ جَاءَتْ أَسْبَاطُ بَنِي إِسْرَائِيلَ.",
             "Ya'qub, son of Ishaq, is also called Israel. From his twelve sons came the tribes of the Children of "
             "Israel.", 192799),
            ("n", "ابْتَلَاهُ اللَّهُ بِفَقْدِ ابْنِهِ يُوسُفَ سِنِينَ طَوِيلَةً، فَقَالَ:",
             "Allah tested him with the loss of his son Yusuf for many long years, and he said:", 30222),
            ("a", 12, 18, 30218),
            ("n", "وَبَكَى حَتَّى ابْيَضَّتْ عَيْنَاهُ مِنَ الْحُزْنِ، لَكِنَّهُ لَمْ يَشْكُ إِلَّا إِلَى اللَّهِ.",
             "He wept until his eyes turned white with grief, but he complained to no one but Allah.", 7215),
            ("a", 12, 86, 225775),
            ("n", "وَلَمْ يَفْقِدِ الْأَمَلَ أَبَدًا:",
             "And he never lost hope:", 280486),
            ("a", 12, 87, 260397),
            ("n", "وَأَوْصَى أَبْنَاءَهُ بِمَا أَوْصَى بِهِ إِبْرَاهِيمُ:",
             "He advised his sons as Ibrahim had advised his own:", 7127),
            ("a", 2, 132, 237673),
            ("a", 2, 133, 48899),
            ("a", 38, 45, 59291),
            ("n", "انْتَهَتْ قِصَّةُ يَعْقُوبَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ يُوسُفُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Ya'qub, peace be upon him. Next: the Prophet Yusuf, peace be upon him.", 365737),
        ],
    ]),
    "yusuf": (11, "يوسف", "Yusuf", [
        [  # Part 1: the dream (Yusuf 12:4-18)
            ("n", "كَانَ يُوسُفُ بْنُ يَعْقُوبَ أَحَبَّ أَبْنَائِهِ إِلَيْهِ. وَفِي لَيْلَةٍ، رَأَى رُؤْيَا عَجِيبَةً.",
             "Yusuf, son of Ya'qub, was the most beloved of his sons to him. One night, he saw an amazing dream.", 1099),
            ("a", 12, 4, 1096),
            ("n", "فَعَرَفَ يَعْقُوبُ أَنَّ لِابْنِهِ شَأْنًا عَظِيمًا، وَخَافَ عَلَيْهِ حَسَدَ إِخْوَتِهِ.",
             "Ya'qub knew that his son would have a great future, and he feared his brothers' envy.", 280486),
            ("a", 12, 5, 7215),
            ("n", "وَحَسَدَهُ إِخْوَتُهُ، وَقَالُوا: أَبُونَا يُحِبُّ يُوسُفَ وَأَخَاهُ أَكْثَرَ مِنَّا.",
             "His brothers envied him. They said: our father loves Yusuf and his brother more than us.", 147663),
            ("n", "فَأَخَذُوهُ مَعَهُمْ لِيَلْعَبَ، ثُمَّ أَلْقَوْهُ فِي قَعْرِ بِئْرٍ.",
             "They took him out with them to play, and then they threw him to the bottom of a well.", 284562),
            ("a", 12, 15, 244839),
            ("n", "وَعَادُوا لَيْلًا يَبْكُونَ، وَمَعَهُمْ قَمِيصُهُ بِدَمٍ كَذِبٍ. فَقَالَ يَعْقُوبُ:",
             "They came back at night weeping, with his shirt stained with false blood. Ya'qub said:", 205427),
            ("a", 12, 18, 14955),
            ("n", "فِي الْجُزْءِ الثَّانِي: مِنَ الْبِئْرِ إِلَى مِصْرَ.",
             "In part two: from the well to Egypt.", 26085),
        ],
        [  # Part 2: to Egypt (Yusuf 12:19-22)
            ("n", "وَمَرَّتْ قَافِلَةٌ بِالْبِئْرِ، فَأَرْسَلُوا مَنْ يَسْتَقِي لَهُمُ الْمَاءَ.",
             "A caravan passed by the well, and they sent someone to draw water for them.", 16139),
            ("a", 12, 19, 212579),
            ("n", "وَبَاعُوهُ بِثَمَنٍ قَلِيلٍ، كَأَنَّهُ لَا قِيمَةَ لَهُ.",
             "They sold him for a small price, as if he were worth nothing.", 284577),
            ("a", 12, 20, 71494),
            ("n", "وَفِي مِصْرَ، اشْتَرَاهُ الْعَزِيزُ، وَهُوَ مِنْ كِبَارِ رِجَالِ الْمَلِكِ، وَقَالَ لِامْرَأَتِهِ: أَكْرِمِيهِ.",
             "In Egypt, he was bought by the Aziz, one of the king's high officials, who told his wife: treat him "
             "well.", 216058),
            ("a", 12, 21, 201473),
            ("n", "وَكَبِرَ يُوسُفُ فِي ذَلِكَ الْبَيْتِ، وَآتَاهُ اللَّهُ الْحِكْمَةَ وَالْعِلْمَ.",
             "Yusuf grew up in that house, and Allah gave him wisdom and knowledge.", 46936),
            ("a", 12, 22, 59291),
            ("n", "فِي الْجُزْءِ الثَّالِثِ: الِابْتِلَاءُ.",
             "In part three: the test.", 7215),
        ],
        [  # Part 3: the test (Yusuf 12:23-34)
            ("n", "وَكَانَ يُوسُفُ جَمِيلًا، فَرَاوَدَتْهُ امْرَأَةُ الْعَزِيزِ عَنْ نَفْسِهِ، وَأَغْلَقَتِ الْأَبْوَابَ.",
             "Yusuf was handsome, and the wife of the Aziz tried to seduce him, and she locked the doors.", 230528),
            ("a", 12, 23, 9041),
            ("n", "فَهَرَبَ إِلَى الْبَابِ، فَشَقَّتْ قَمِيصَهُ مِنَ الْخَلْفِ، وَوَجَدَا زَوْجَهَا عِنْدَ الْبَابِ.",
             "He ran to the door. She tore his shirt from behind, and they found her husband at the door.", 2147),
            ("n", "فَشَهِدَ شَاهِدٌ مِنْ أَهْلِهَا:",
             "A witness from her own family testified:", 190331),
            ("a", 12, 27, 12759),
            ("a", 12, 28, 2150),
            ("n", "وَتَحَدَّثَتْ نِسَاءُ الْمَدِينَةِ عَنْهَا، فَلَمَّا رَأَيْنَهُ، دُهِشْنَ مِنْ جَمَالِهِ.",
             "The women of the city gossiped about her. When they saw him, they were stunned by his beauty.", 229685),
            ("n", "وَهَدَّدَتْهُ بِالسِّجْنِ إِنْ لَمْ يُطِعْهَا، فَدَعَا يُوسُفُ رَبَّهُ:",
             "She threatened him with prison if he did not obey her. And Yusuf called upon his Lord:", 225775),
            ("a", 12, 33, 6343),
            ("a", 12, 34, 48899),
            ("n", "فِي الْجُزْءِ الرَّابِعِ: السِّجْنُ.",
             "In part four: the prison.", 22555),
        ],
        [  # Part 4: the prison (Yusuf 12:35-42)
            ("n", "وَدَخَلَ يُوسُفُ السِّجْنَ وَهُوَ بَرِيءٌ، وَدَخَلَ مَعَهُ فَتَيَانِ.",
             "Yusuf went into prison though he was innocent, and two young men went in with him.", 205427),
            ("n", "رَأَى كُلٌّ مِنْهُمَا رُؤْيَا، فَطَلَبَا مِنْ يُوسُفَ أَنْ يُفَسِّرَهَا، لِمَا رَأَيَا مِنْ إِحْسَانِهِ.",
             "Each of them saw a dream, and they asked Yusuf to interpret it, because they saw how good he was.", 7215),
            ("n", "وَقَبْلَ أَنْ يُفَسِّرَ، دَعَاهُمَا إِلَى اللَّهِ:",
             "Before interpreting, he called them to Allah:", 14955),
            ("a", 12, 39, 225775),
            ("a", 12, 40, 1099),
            ("a", 12, 41, 283428),
            ("n", "وَطَلَبَ مِنَ الَّذِي سَيَنْجُو أَنْ يَذْكُرَهُ عِنْدَ الْمَلِكِ، لَكِنَّ الشَّيْطَانَ أَنْسَاهُ، فَبَقِيَ يُوسُفُ فِي السِّجْنِ سِنِينَ.",
             "He asked the one who would be freed to mention him to the king. But Shaytan made him forget, and Yusuf "
             "stayed in prison for years.", 30222),
            ("n", "فِي الْجُزْءِ الْخَامِسِ: رُؤْيَا الْمَلِكِ.",
             "In part five: the king's dream.", 7127),
        ],
        [  # Part 5: the king's dream (Yusuf 12:43-55)
            ("n", "وَرَأَى الْمَلِكُ رُؤْيَا، فَلَمْ يَعْرِفْ أَحَدٌ تَفْسِيرَهَا.",
             "The king saw a dream, and no one could interpret it.", 296971),
            ("a", 12, 43, 288592),
            ("n", "فَتَذَكَّرَ صَاحِبُ السِّجْنِ يُوسُفَ، فَفَسَّرَهَا: سَبْعُ سِنِينَ خِصْبٍ، ثُمَّ سَبْعٌ شِدَادٌ، ثُمَّ عَامٌ فِيهِ الْغَيْثُ.",
             "The man from the prison remembered Yusuf, who explained it: seven years of plenty, then seven hard "
             "years, then a year of rain.", 21444),
            ("a", 12, 47, 17285),
            ("a", 12, 48, 11053),
            ("a", 12, 49, 2527),
            ("n", "وَطَلَبَهُ الْمَلِكُ، فَرَفَضَ يُوسُفُ أَنْ يَخْرُجَ حَتَّى تَظْهَرَ بَرَاءَتُهُ. فَاعْتَرَفَتِ امْرَأَةُ الْعَزِيزِ:",
             "The king sent for him, but Yusuf refused to come out until his innocence was shown. And the wife of the "
             "Aziz confessed:", 237673),
            ("a", 12, 51, 260397),
            ("n", "فَجَعَلَهُ الْمَلِكُ أَمِينًا عَلَى خَزَائِنِ الْأَرْضِ.",
             "And the king put him in charge of the storehouses of the land.", 190131),
            ("a", 12, 55, 42379),
            ("n", "فِي الْجُزْءِ السَّادِسِ: اللِّقَاءُ.",
             "In part six: the reunion.", 365737),
        ],
        [  # Part 6: the reunion (Yusuf 12:58-101)
            ("n", "وَوَصَلَتِ الْمَجَاعَةُ إِلَى أَرْضِ يَعْقُوبَ، فَجَاءَ إِخْوَةُ يُوسُفَ إِلَى مِصْرَ يَطْلُبُونَ الطَّعَامَ. فَعَرَفَهُمْ، وَلَمْ يَعْرِفُوهُ.",
             "The famine reached the land of Ya'qub, and Yusuf's brothers came to Egypt asking for food. He knew them, "
             "but they did not know him.", 69321),
            ("n", "وَبَعْدَ سِنِينَ مِنَ الْفِرَاقِ، وَقَفُوا أَمَامَهُ مُنْكَسِرِينَ، فَقَالَ لَهُمْ:",
             "After years apart, they stood before him, humbled, and he said to them:", 70898),
            ("a", 12, 90, 280486),
            ("a", 12, 92, 48899),
            ("n", "وَأَرْسَلَ قَمِيصَهُ إِلَى أَبِيهِ، فَلَمَّا أُلْقِيَ عَلَى وَجْهِهِ، عَادَ إِلَيْهِ بَصَرُهُ.",
             "He sent his shirt to his father. When it was laid over his face, his sight came back.", 192799),
            ("a", 12, 96, 246856),
            ("n", "وَجَاءَتِ الْعَائِلَةُ كُلُّهَا إِلَى مِصْرَ، فَتَحَقَّقَتِ الرُّؤْيَا.",
             "The whole family came to Egypt, and the dream came true.", 7127),
            ("a", 12, 100, 175495),
            ("a", 12, 101, 237672),
            ("n", "انْتَهَتْ قِصَّةُ يُوسُفَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ أَيُّوبُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Yusuf, peace be upon him. Next: the Prophet Ayyub, peace be upon him.", 201308),
        ],
    ]),
    "ayyub": (12, "أيوب", "Ayyub", [
        [  # One part: Al-Anbiya 21:83-84, Sad 38:41-44
            ("n", "كَانَ أَيُّوبُ نَبِيًّا آتَاهُ اللَّهُ الْمَالَ وَالْأَوْلَادَ وَالصِّحَّةَ، فَكَانَ شَاكِرًا لِرَبِّهِ.",
             "Ayyub was a prophet to whom Allah gave wealth, children and health, and he was thankful to his Lord.",
             179200),
            ("n", "ثُمَّ ابْتَلَاهُ اللَّهُ، فَذَهَبَ مَالُهُ، وَمَاتَ أَوْلَادُهُ، ثُمَّ أَصَابَهُ الْمَرَضُ سِنِينَ طَوِيلَةً.",
             "Then Allah tested him. His wealth was lost, his children died, and then illness struck him for many "
             "long years.", 328726),
            ("n", "وَابْتَعَدَ عَنْهُ النَّاسُ، إِلَّا زَوْجَتَهُ، الَّتِي بَقِيَتْ تَخْدُمُهُ صَابِرَةً.",
             "People kept away from him, except his wife, who stayed and cared for him with patience.", 284562),
            ("n", "وَلَمْ يَشْكُ أَيُّوبُ إِلَّا إِلَى اللَّهِ، فَنَادَى رَبَّهُ:",
             "Ayyub complained to no one but Allah, and he called out to his Lord:", 7215),
            ("a", 21, 83, 205427),
            ("a", 38, 41, 225775),
            ("n", "فَأَمَرَهُ اللَّهُ أَنْ يَضْرِبَ الْأَرْضَ بِرِجْلِهِ، فَنَبَعَتْ عَيْنُ مَاءٍ، فَاغْتَسَلَ مِنْهَا وَشَرِبَ، فَشُفِيَ.",
             "Allah told him to strike the ground with his foot. A spring of water burst out. He washed in it and "
             "drank from it, and he was healed.", 220161),
            ("a", 38, 42, 7452),
            ("a", 21, 84, 246856),
            ("a", 38, 44, 237673),
            ("n", "فَمَنْ صَبَرَ عَلَى الْبَلَاءِ، وَلَمْ يَشْكُ إِلَّا إِلَى اللَّهِ، جَاءَهُ الْفَرَجُ.",
             "Whoever is patient through hardship, and complains only to Allah, relief will come to him.", 280486),
            ("n", "انْتَهَتْ قِصَّةُ أَيُّوبَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ شُعَيْبٌ عَلَيْهِ السَّلَامُ.",
             "This was the story of Ayyub, peace be upon him. Next: the Prophet Shu'ayb, peace be upon him.", 21175),
        ],
    ]),
    "shuayb": (13, "شعيب", "Shu'ayb", [
        [  # Part 1: the fair measure (Al-A'raf 7:85, Hud 11:84-88, Ash-Shu'ara 26:176-183)
            ("n", "بَعْدَ قَوْمِ لُوطٍ، عَاشَ أَهْلُ مَدْيَنَ فِي شَمَالِ جَزِيرَةِ الْعَرَبِ. كَانُوا تُجَّارًا، يَغُشُّونَ فِي الْمِكْيَالِ وَالْمِيزَانِ.",
             "After the people of Lut, the people of Madyan lived in the north of Arabia. They were traders who "
             "cheated in measures and scales.", 69321),
            ("n", "فَأَرْسَلَ اللَّهُ إِلَيْهِمْ أَخَاهُمْ شُعَيْبًا عَلَيْهِ السَّلَامُ.",
             "So Allah sent them their brother Shu'ayb, peace be upon him.", 26085),
            ("a", 7, 85, 304330),
            ("a", 11, 85, 21444),
            ("n", "فَسَخِرُوا مِنْهُ وَمِنْ صَلَاتِهِ:",
             "They mocked him and his prayer:", 147663),
            ("a", 11, 87, 70898),
            ("n", "فَأَجَابَهُمْ بِحِلْمٍ:",
             "He answered them gently:", 7127),
            ("a", 11, 88, 280486),
            ("n", "فِي الْجُزْءِ الثَّانِي: يَوْمُ الظُّلَّةِ.",
             "In part two: the day of the shadow.", 225775),
        ],
        [  # Part 2: the day of the shadow (Al-A'raf 7:88-93, Ash-Shu'ara 26:185-191, Hud 11:91-95)
            ("n", "وَهَدَّدَهُ كُبَرَاءُ قَوْمِهِ بِالطَّرْدِ هُوَ وَالْمُؤْمِنِينَ، إِنْ لَمْ يَعُودُوا إِلَى دِينِهِمْ.",
             "The leaders of his people threatened to drive him and the believers out, unless they returned to their "
             "religion.", 2147),
            ("a", 7, 88, 9041),
            ("n", "وَتَحَدَّوْهُ أَنْ يُسْقِطَ عَلَيْهِمْ قِطَعًا مِنَ السَّمَاءِ.",
             "They challenged him to make pieces of the sky fall upon them.", 190331),
            ("a", 26, 187, 12759),
            ("n", "فَأَصَابَهُمْ حَرٌّ شَدِيدٌ، ثُمَّ ظَهَرَتْ سَحَابَةٌ، فَاجْتَمَعُوا تَحْتَهَا يَطْلُبُونَ الظِّلَّ، فَجَاءَهُمُ الْعَذَابُ.",
             "A terrible heat came upon them. Then a cloud appeared, and they gathered under it seeking shade, and the "
             "punishment came.", 70899),
            ("a", 26, 189, 230528),
            ("a", 11, 94, 283428),
            ("n", "وَتَوَلَّى عَنْهُمْ شُعَيْبٌ، وَقَالَ:",
             "Shu'ayb turned away from them, and said:", 316435),
            ("a", 7, 93, 43953),
            ("n", "انْتَهَتْ قِصَّةُ شُعَيْبٍ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: كَلِيمُ اللَّهِ مُوسَى عَلَيْهِ السَّلَامُ.",
             "This was the story of Shu'ayb, peace be upon him. Next: Musa, who spoke with Allah, peace be upon him.",
             2950),
        ],
    ]),
    "musa": (14, "موسى", "Musa", [
        [  # Part 1: the river (Al-Qasas 28:3-13)
            ("n", "فِي مِصْرَ، حَكَمَ فِرْعَوْنُ طَاغِيَةً، فَاسْتَعْبَدَ بَنِي إِسْرَائِيلَ، وَكَانَ يَقْتُلُ أَبْنَاءَهُمْ.",
             "In Egypt, Pharaoh ruled as a tyrant. He enslaved the Children of Israel, and killed their sons.", 2147),
            ("a", 28, 4, 230528),
            ("n", "وَفِي ذَلِكَ الزَّمَنِ وُلِدَ مُوسَى، فَخَافَتْ عَلَيْهِ أُمُّهُ.",
             "In that time Musa was born, and his mother feared for him.", 7215),
            ("a", 28, 7, 364783),
            ("n", "فَوَضَعَتْهُ فِي صُنْدُوقٍ، وَأَلْقَتْهُ فِي النَّهْرِ، فَحَمَلَهُ الْمَاءُ إِلَى قَصْرِ فِرْعَوْنَ.",
             "She placed him in a box and put it in the river, and the water carried him to Pharaoh's palace.", 151940),
            ("n", "فَرَأَتْهُ امْرَأَةُ فِرْعَوْنَ، فَأَحَبَّتْهُ:",
             "Pharaoh's wife saw him, and loved him:", 107918),
            ("a", 28, 9, 69306),
            ("n", "وَرَفَضَ مُوسَى كُلَّ الْمَرَاضِعِ، فَقَالَتْ أُخْتُهُ: أَدُلُّكُمْ عَلَى أَهْلِ بَيْتٍ يَكْفُلُونَهُ؟ فَرَدَّهُ اللَّهُ إِلَى أُمِّهِ.",
             "Musa refused every nurse. His sister said: shall I show you a family who will care for him? And Allah "
             "returned him to his mother.", 134032),
            ("a", 28, 13, 63736),
            ("n", "فِي الْجُزْءِ الثَّانِي: مَدْيَنُ.",
             "In part two: Madyan.", 26085),
        ],
        [  # Part 2: Madyan (Al-Qasas 28:14-28)
            ("n", "وَكَبِرَ مُوسَى قَوِيًّا حَكِيمًا. وَذَاتَ يَوْمٍ، وَجَدَ رَجُلَيْنِ يَقْتَتِلَانِ، فَضَرَبَ أَحَدَهُمَا، فَمَاتَ، وَلَمْ يَكُنْ يُرِيدُ قَتْلَهُ.",
             "Musa grew up strong and wise. One day he found two men fighting. He struck one of them, and the man "
             "died, though Musa never meant to kill him.", 316435),
            ("a", 28, 16, 225775),
            ("n", "وَانْتَشَرَ الْخَبَرُ، فَخَرَجَ مُوسَى مِنْ مِصْرَ خَائِفًا، مُتَّجِهًا إِلَى مَدْيَنَ.",
             "The news spread, and Musa left Egypt in fear, heading for Madyan.", 16139),
            ("a", 28, 22, 70898),
            ("n", "وَعِنْدَ مَاءِ مَدْيَنَ، وَجَدَ امْرَأَتَيْنِ تَنْتَظِرَانِ، فَسَقَى لَهُمَا، ثُمَّ جَلَسَ فِي الظِّلِّ وَدَعَا:",
             "At the water of Madyan, he found two women waiting. He drew water for them, then sat in the shade and "
             "prayed:", 7452),
            ("a", 28, 24, 217491),
            ("n", "فَجَاءَتْهُ إِحْدَاهُمَا تَمْشِي عَلَى اسْتِحْيَاءٍ: إِنَّ أَبِي يَدْعُوكَ.",
             "One of them came to him, walking shyly: my father invites you.", 220161),
            ("a", 28, 26, 192799),
            ("n", "فَتَزَوَّجَ مُوسَى إِحْدَى الِابْنَتَيْنِ، وَعَمِلَ عِنْدَ أَبِيهَا سِنِينَ.",
             "Musa married one of the two daughters, and worked for her father for years.", 46936),
            ("n", "فِي الْجُزْءِ الثَّالِثِ: النَّارُ عَلَى الْجَبَلِ.",
             "In part three: the fire on the mountain.", 22555),
        ],
        [  # Part 3: the fire on the mountain (Ta-Ha 20:9-36)
            ("n", "وَبَعْدَ سِنِينَ، سَارَ مُوسَى بِأَهْلِهِ لَيْلًا، فِي بَرْدٍ شَدِيدٍ، فَرَأَى نَارًا عِنْدَ جَانِبِ الْجَبَلِ.",
             "Years later, Musa travelled with his family at night, in bitter cold, and he saw a fire by the side of "
             "the mountain.", 202877),
            ("a", 20, 10, 3742),
            ("a", 20, 11, 10018),
            ("a", 20, 12, 214938),
            ("a", 20, 14, 7127),
            ("n", "وَأَعْطَاهُ اللَّهُ آيَاتٍ: عَصَاهُ تَصِيرُ حَيَّةً تَسْعَى، وَيَدُهُ تَخْرُجُ بَيْضَاءَ مُضِيئَةً. وَأَمَرَهُ:",
             "Allah gave him signs: his staff became a moving snake, and his hand came out white and shining. And He "
             "commanded him:", 1099),
            ("a", 20, 24, 22512),
            ("n", "فَدَعَا مُوسَى رَبَّهُ:",
             "Musa called upon his Lord:", 280486),
            ("a", 20, 25, 30850),
            ("a", 20, 26, 237673),
            ("a", 20, 27, 59291),
            ("a", 20, 28, 48899),
            ("n", "وَسَأَلَ اللَّهَ أَنْ يَجْعَلَ أَخَاهُ هَارُونَ مَعَهُ، فَاسْتَجَابَ اللَّهُ لَهُ.",
             "He asked Allah to send his brother Harun with him, and Allah answered him.", 246856),
            ("n", "فِي الْجُزْءِ الرَّابِعِ: أَمَامَ فِرْعَوْنَ.",
             "In part four: before Pharaoh.", 2150),
        ],
        [  # Part 4: before Pharaoh (Ta-Ha 20:43-59, Ash-Shu'ara 26:16-34)
            ("n", "وَأَرْسَلَ اللَّهُ مُوسَى وَهَارُونَ إِلَى فِرْعَوْنَ:",
             "Allah sent Musa and Harun to Pharaoh:", 69320),
            ("a", 20, 43, 2266),
            ("a", 20, 44, 46936),
            ("n", "فَدَعَوَاهُ إِلَى اللَّهِ، وَطَلَبَا مِنْهُ أَنْ يُرْسِلَ مَعَهُمَا بَنِي إِسْرَائِيلَ. فَسَأَلَ فِرْعَوْنُ:",
             "They called him to Allah, and asked him to let the Children of Israel go with them. Pharaoh asked:",
             9041),
            ("a", 20, 49, 12759),
            ("a", 20, 50, 246856),
            ("n", "فَتَكَبَّرَ فِرْعَوْنُ، وَاتَّهَمَ مُوسَى بِالسِّحْرِ، وَطَلَبَ مَوْعِدًا لِلتَّحَدِّي.",
             "Pharaoh grew arrogant, accused Musa of magic, and demanded a day for a contest.", 190331),
            ("a", 20, 59, 6343),
            ("n", "فِي الْجُزْءِ الْخَامِسِ: السَّحَرَةُ.",
             "In part five: the magicians.", 225775),
        ],
        [  # Part 5: the magicians (Ta-Ha 20:60-73)
            ("n", "جَمَعَ فِرْعَوْنُ أَمْهَرَ سَحَرَةِ مِصْرَ، وَاجْتَمَعَ النَّاسُ يَوْمَ الزِّينَةِ.",
             "Pharaoh gathered the most skilled magicians of Egypt, and the people gathered on the day of the "
             "festival.", 70899),
            ("a", 20, 61, 316435),
            ("n", "فَأَلْقَوْا حِبَالَهُمْ وَعِصِيَّهُمْ، فَخُيِّلَ لِمُوسَى مِنْ سِحْرِهِمْ أَنَّهَا تَسْعَى، فَخَافَ.",
             "They threw down their ropes and staffs, and by their magic it seemed to Musa that they were moving, and "
             "he felt afraid.", 283428),
            ("a", 20, 68, 125192),
            ("a", 20, 69, 48899),
            ("n", "فَأَلْقَى مُوسَى عَصَاهُ، فَابْتَلَعَتْ مَا صَنَعُوا. فَعَرَفَ السَّحَرَةُ أَنَّ هَذَا لَيْسَ سِحْرًا:",
             "Musa threw down his staff, and it swallowed what they had made. The magicians knew this was not magic:",
             7127),
            ("a", 20, 70, 237673),
            ("n", "فَهَدَّدَهُمْ فِرْعَوْنُ بِالْقَتْلِ وَالصَّلْبِ، فَقَالُوا:",
             "Pharaoh threatened them with death and crucifixion, and they said:", 2147),
            ("a", 20, 72, 175495),
            ("a", 20, 73, 328740),
            ("n", "فِي الْجُزْءِ السَّادِسِ: الْبَحْرُ.",
             "In part six: the sea.", 283533),
        ],
        [  # Part 6: the sea (Ash-Shu'ara 26:52-67, Yunus 10:90-92; Sahih al-Bukhari 2004)
            ("n", "وَأَوْحَى اللَّهُ إِلَى مُوسَى أَنْ يَخْرُجَ لَيْلًا بِبَنِي إِسْرَائِيلَ.",
             "Allah revealed to Musa to leave at night with the Children of Israel.", 205427),
            ("a", 26, 52, 14955),
            ("n", "فَجَمَعَ فِرْعَوْنُ جُنُودَهُ، وَتَبِعَهُمْ، حَتَّى وَصَلُوا إِلَى الْبَحْرِ عِنْدَ الشُّرُوقِ.",
             "Pharaoh gathered his army and pursued them, until they reached the sea at sunrise.", 7487),
            ("a", 26, 61, 368),
            ("a", 26, 62, 280486),
            ("a", 26, 63, 184008),
            ("n", "فَعَبَرَ بَنُو إِسْرَائِيلَ عَلَى أَرْضٍ يَابِسَةٍ، وَتَبِعَهُمْ فِرْعَوْنُ، فَانْطَبَقَ عَلَيْهِمُ الْبَحْرُ.",
             "The Children of Israel crossed on dry land. Pharaoh followed them, and the sea closed over them.",
             374783),
            ("a", 26, 65, 50642),
            ("a", 26, 66, 243153),
            ("a", 10, 92, 2944),
            ("n", "وَكَانَ نَبِيُّنَا صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ يَصُومُ يَوْمَ عَاشُورَاءَ، شُكْرًا لِلَّهِ عَلَى نَجَاةِ مُوسَى. رَوَاهُ الْبُخَارِيُّ.",
             "Our Prophet ﷺ fasted the day of Ashura, in thanks to Allah for saving Musa. (Sahih al-Bukhari)", 201418),
            ("n", "فِي الْجُزْءِ السَّابِعِ: الْعِجْلُ.",
             "In part seven: the calf.", 1099),
        ],
        [  # Part 7: the calf (Al-A'raf 7:142-150, Ta-Ha 20:83-98)
            ("n", "وَدَعَا اللَّهُ مُوسَى إِلَى الْجَبَلِ أَرْبَعِينَ لَيْلَةً، وَتَرَكَ هَارُونَ فِي قَوْمِهِ.",
             "Allah called Musa to the mountain for forty nights, and he left Harun with his people.", 22512),
            ("a", 7, 143, 214938),
            ("n", "وَأَعْطَاهُ اللَّهُ الْأَلْوَاحَ، فِيهَا التَّوْرَاةُ، هُدًى وَرَحْمَةً.",
             "Allah gave him the tablets of the Torah, a guidance and a mercy.", 7127),
            ("n", "وَفِي غِيَابِهِ، صَنَعَ السَّامِرِيُّ عِجْلًا مِنْ ذَهَبِهِمْ، فَعَبَدَهُ كَثِيرٌ مِنْهُمْ. وَحَذَّرَهُمْ هَارُونُ:",
             "While he was away, As-Samiri made a calf out of their gold, and many of them worshipped it. Harun "
             "warned them:", 8625),
            ("a", 20, 90, 2150),
            ("n", "وَرَجَعَ مُوسَى غَاضِبًا حَزِينًا، فَأَحْرَقَ الْعِجْلَ، وَنَسَفَهُ فِي الْبَحْرِ، وَقَالَ:",
             "Musa came back angry and sad. He burned the calf, scattered it into the sea, and said:", 38998),
            ("a", 20, 98, 30850),
            ("n", "فِي الْجُزْءِ الثَّامِنِ: مُوسَى وَالْخَضِرُ.",
             "In part eight: Musa and al-Khidr.", 2950),
        ],
        [  # Part 8: Musa and al-Khidr (Al-Kahf 18:60-82; Sahih al-Bukhari 122)
            ("n", "قَالَ نَبِيُّنَا صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ: سُئِلَ مُوسَى مَنْ أَعْلَمُ النَّاسِ، فَقَالَ: أَنَا. فَأَخْبَرَهُ اللَّهُ أَنَّ لَهُ عَبْدًا "
                  "عِنْدَ مَجْمَعِ الْبَحْرَيْنِ هُوَ أَعْلَمُ مِنْهُ. رَوَاهُ الْبُخَارِيُّ.",
             "Our Prophet ﷺ said: Musa was asked who is the most knowledgeable, and he said: I am. Allah told him He "
             "had a servant where the two seas meet who knew more. (Sahih al-Bukhari)", 364783),
            ("a", 18, 60, 248158),
            ("n", "وَهُنَاكَ وَجَدَ الْخَضِرَ:",
             "And there, he found al-Khidr:", 2944),
            ("a", 18, 65, 7127),
            ("a", 18, 66, 280486),
            ("n", "فَخَرَقَ الْخَضِرُ سَفِينَةً، وَقَتَلَ غُلَامًا، وَأَقَامَ جِدَارًا بِلَا أَجْرٍ، وَمُوسَى لَا يَصْبِرُ عَلَى مَا لَا يَعْرِفُ حِكْمَتَهُ.",
             "Al-Khidr damaged a boat, killed a boy, and rebuilt a wall for no pay. And Musa could not stay patient "
             "with what he did not understand.", 368),
            ("n", "ثُمَّ بَيَّنَ لَهُ الْحِكْمَةَ: السَّفِينَةُ لِمَسَاكِينَ، وَالْغُلَامُ كَانَ سَيُرْهِقُ أَبَوَيْهِ، وَالْجِدَارُ تَحْتَهُ كَنْزٌ لِيَتِيمَيْنِ.",
             "Then he explained the wisdom: the boat belonged to poor people, the boy would have burdened his parents, "
             "and under the wall was a treasure for two orphans.", 59291),
            ("a", 18, 82, 46936),
            ("n", "فَعِلْمُ اللَّهِ وَحِكْمَتُهُ أَوْسَعُ مِمَّا نَرَى.",
             "The knowledge and wisdom of Allah are far greater than what we see.", 48899),
            ("n", "انْتَهَتْ قِصَّةُ مُوسَى عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ هَارُونُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Musa, peace be upon him. Next: the Prophet Harun, peace be upon him.", 21175),
        ],
    ]),
    "harun": (15, "هارون", "Harun", [
        [  # One part: Ta-Ha 20:29-36, 20:90-94, Al-Qasas 28:34, Maryam 19:53, Al-A'raf 7:150-151; Sahih al-Bukhari 3706
            ("n", "هَارُونُ هُوَ أَخُو مُوسَى الْأَكْبَرُ، كَانَ فَصِيحَ اللِّسَانِ، لَيِّنَ الْقَلْبِ، مَحْبُوبًا فِي قَوْمِهِ.",
             "Harun was Musa's older brother. He was eloquent, gentle, and loved by his people.", 46936),
            ("n", "وَطَلَبَ مُوسَى مِنْ رَبِّهِ أَنْ يَجْعَلَهُ مَعَهُ:",
             "Musa asked his Lord to send him along:", 280486),
            ("a", 28, 34, 7127),
            ("a", 19, 53, 237673),
            ("n", "فَوَقَفَ مَعَ أَخِيهِ أَمَامَ فِرْعَوْنَ، وَدَعَوَاهُ مَعًا إِلَى اللَّهِ.",
             "He stood with his brother before Pharaoh, and together they called him to Allah.", 69320),
            ("n", "وَلَمَّا عَبَدَ قَوْمُهُ الْعِجْلَ، نَصَحَهُمْ هَارُونُ، فَلَمْ يَسْمَعُوا لَهُ.",
             "When his people worshipped the calf, Harun warned them, but they would not listen to him.", 190331),
            ("n", "وَرَجَعَ مُوسَى غَاضِبًا، فَأَخَذَ بِرَأْسِ أَخِيهِ، فَقَالَ هَارُونُ:",
             "Musa came back angry and took hold of his brother's head. Harun said:", 225775),
            ("a", 20, 94, 205427),
            ("n", "فَدَعَا مُوسَى لِنَفْسِهِ وَلِأَخِيهِ:",
             "And Musa prayed for himself and for his brother:", 59291),
            ("a", 7, 151, 48899),
            ("n", "وَقَالَ نَبِيُّنَا صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ لِعَلِيٍّ: أَنْتَ مِنِّي بِمَنْزِلَةِ هَارُونَ مِنْ مُوسَى، إِلَّا أَنَّهُ لَا نَبِيَّ بَعْدِي. "
                  "رَوَاهُ الْبُخَارِيُّ.",
             "Our Prophet ﷺ said to Ali: you are to me as Harun was to Musa, except that there is no prophet after "
             "me. (Sahih al-Bukhari)", 260397),
            ("n", "انْتَهَتْ قِصَّةُ هَارُونَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ ذُو الْكِفْلِ عَلَيْهِ السَّلَامُ.",
             "This was the story of Harun, peace be upon him. Next: the Prophet Dhul-Kifl, peace be upon him.", 21175),
        ],
    ]),
    "dhulkifl": (16, "ذو الكفل", "Dhul-Kifl", [
        [  # One part: Al-Anbiya 21:85-86, Sad 38:48
            ("n", "ذَكَرَ اللَّهُ فِي الْقُرْآنِ نَبِيًّا اسْمُهُ ذُو الْكِفْلِ، فِي مَوْضِعَيْنِ، وَأَثْنَى عَلَيْهِ.",
             "Allah mentions in the Quran a prophet named Dhul-Kifl, in two places, and praises him.", 59291),
            ("a", 21, 85, 248452),
            ("a", 21, 86, 30850),
            ("a", 38, 48, 7127),
            ("n", "لَمْ يَذْكُرِ الْقُرْآنُ تَفَاصِيلَ حَيَاتِهِ، لَكِنَّهُ ذَكَرَ مَا يَكْفِي: كَانَ صَابِرًا، صَالِحًا، مِنَ الْأَخْيَارِ.",
             "The Quran does not tell the details of his life, but it tells us enough: he was patient, righteous, and "
             "among the best.", 280486),
            ("n", "فَالْعِبْرَةُ لَيْسَتْ بِكَثْرَةِ مَا يُقَالُ عَنِ الْمَرْءِ، بَلْ بِمَا يَشْهَدُ لَهُ بِهِ رَبُّهُ.",
             "What matters is not how much is said about a person, but what his Lord bears witness to.", 48899),
            ("n", "انْتَهَتْ قِصَّةُ ذِي الْكِفْلِ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ دَاوُدُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Dhul-Kifl, peace be upon him. Next: the Prophet Dawud, peace be upon him.", 21175),
        ],
    ]),
    "dawud": (17, "داود", "Dawud", [
        [  # Part 1: Dawud and Jalut (Al-Baqarah 2:246-251)
            ("n", "بَعْدَ مُوسَى بِزَمَنٍ، طَلَبَ بَنُو إِسْرَائِيلَ مَلِكًا يُقَاتِلُونَ مَعَهُ، فَاخْتَارَ اللَّهُ لَهُمْ طَالُوتَ.",
             "Long after Musa, the Children of Israel asked for a king to fight with, and Allah chose Talut for them.",
             69321),
            ("n", "وَفِي الطَّرِيقِ إِلَى الْمَعْرَكَةِ، ابْتَلَاهُمُ اللَّهُ بِنَهْرٍ:",
             "On the way to battle, Allah tested them with a river:", 364783),
            ("a", 2, 249, 201473),
            ("n", "وَوَقَفَ الْقَلِيلُ الصَّابِرُونَ أَمَامَ جَالُوتَ وَجُنُودِهِ، فَدَعَوْا:",
             "The few who were patient stood before Jalut and his army, and they prayed:", 70898),
            ("a", 2, 250, 280486),
            ("n", "وَكَانَ فِيهِمْ شَابٌّ اسْمُهُ دَاوُدُ، فَقَتَلَ جَالُوتَ، وَنَصَرَ اللَّهُ الْمُؤْمِنِينَ.",
             "Among them was a young man named Dawud. He killed Jalut, and Allah gave the believers victory.", 2150),
            ("a", 2, 251, 7127),
            ("n", "فِي الْجُزْءِ الثَّانِي: الْجِبَالُ تُسَبِّحُ مَعَهُ.",
             "In part two: the mountains glorified Allah with him.", 22512),
        ],
        [  # Part 2: the mountains glorified with him (Saba 34:10-11, Sad 38:17-26, Al-Isra 17:55; Sahih al-Bukhari 2072, 1131)
            ("n", "وَآتَى اللَّهُ دَاوُدَ الْمُلْكَ وَالنُّبُوَّةَ وَالزَّبُورَ، وَصَوْتًا جَمِيلًا يُسَبِّحُ بِهِ.",
             "Allah gave Dawud kingship, prophethood, the Zabur, and a beautiful voice with which he glorified Him.",
             22512),
            ("a", 34, 10, 214938),
            ("n", "وَعَلَّمَهُ صِنَاعَةَ الدُّرُوعِ، فَكَانَ يَأْكُلُ مِنْ عَمَلِ يَدِهِ. رَوَاهُ الْبُخَارِيُّ.",
             "And Allah taught him to make armour, and he ate from the work of his own hands. (Sahih al-Bukhari)",
             8625),
            ("a", 34, 11, 38998),
            ("n", "وَكَانَ يَصُومُ يَوْمًا، وَيُفْطِرُ يَوْمًا، وَيَقُومُ مِنَ اللَّيْلِ. قَالَ نَبِيُّنَا: ذَلِكَ أَحَبُّ الصِّيَامِ إِلَى اللَّهِ. رَوَاهُ الْبُخَارِيُّ.",
             "He fasted one day and ate the next, and stood in prayer at night. Our Prophet ﷺ said: that is the "
             "fasting most loved by Allah. (Sahih al-Bukhari)", 1099),
            ("n", "وَجَعَلَهُ اللَّهُ خَلِيفَةً يَحْكُمُ بَيْنَ النَّاسِ بِالْعَدْلِ:",
             "Allah made him a ruler to judge between people with justice:", 237673),
            ("a", 38, 26, 59291),
            ("n", "انْتَهَتْ قِصَّةُ دَاوُدَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: ابْنُهُ، نَبِيُّ اللَّهِ سُلَيْمَانُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Dawud, peace be upon him. Next: his son, the Prophet Sulayman, peace be upon him.",
             21175),
        ],
    ]),
    "sulayman": (18, "سليمان", "Sulayman", [
        [  # Part 1: the kingdom (An-Naml 27:16, Sad 38:30-40, Saba 34:12-13, Al-Anbiya 21:79-81)
            ("n", "وَرِثَ سُلَيْمَانُ أَبَاهُ دَاوُدَ فِي النُّبُوَّةِ وَالْمُلْكِ، وَعَلَّمَهُ اللَّهُ لُغَةَ الطَّيْرِ.",
             "Sulayman inherited prophethood and kingship from his father Dawud, and Allah taught him the language of "
             "the birds.", 7127),
            ("a", 27, 16, 46936),
            ("n", "وَدَعَا سُلَيْمَانُ رَبَّهُ:",
             "Sulayman called upon his Lord:", 280486),
            ("a", 38, 35, 237673),
            ("n", "فَاسْتَجَابَ اللَّهُ لَهُ، وَسَخَّرَ لَهُ الرِّيحَ تَجْرِي بِأَمْرِهِ، وَالْجِنَّ يَعْمَلُونَ لَهُ.",
             "Allah answered him. He made the wind blow at his command, and the jinn work for him.", 212437),
            ("a", 38, 36, 152740),
            ("a", 34, 13, 59291),
            ("n", "وَمَعَ هَذَا الْمُلْكِ الْعَظِيمِ، بَقِيَ عَبْدًا شَاكِرًا أَوَّابًا.",
             "And with all this great kingdom, he remained a grateful servant, always turning back to Allah.", 48899),
            ("n", "فِي الْجُزْءِ الثَّانِي: النَّمْلَةُ وَالْهُدْهُدُ.",
             "In part two: the ant and the hoopoe.", 179200),
        ],
        [  # Part 2: the ant and the hoopoe (An-Naml 27:17-28)
            ("n", "خَرَجَ سُلَيْمَانُ بِجُنُودِهِ، حَتَّى وَصَلُوا إِلَى وَادِي النَّمْلِ:",
             "Sulayman set out with his armies, until they reached the valley of the ants:", 69321),
            ("a", 27, 18, 134115),
            ("n", "فَتَبَسَّمَ سُلَيْمَانُ مِنْ قَوْلِهَا، وَشَكَرَ رَبَّهُ:",
             "Sulayman smiled at what she said, and thanked his Lord:", 192799),
            ("a", 27, 19, 246856),
            ("n", "وَتَفَقَّدَ الطَّيْرَ، فَلَمْ يَجِدِ الْهُدْهُدَ. ثُمَّ جَاءَ الْهُدْهُدُ بِخَبَرٍ عَجِيبٍ:",
             "He checked on the birds, and could not find the hoopoe. Then the hoopoe came with amazing news:", 16139),
            ("a", 27, 23, 26085),
            ("a", 27, 24, 152483),
            ("n", "فَأَرْسَلَ سُلَيْمَانُ مَعَهُ كِتَابًا إِلَى مَلِكَةِ سَبَأٍ.",
             "So Sulayman sent a letter with him to the queen of Saba.", 7127),
            ("n", "فِي الْجُزْءِ الثَّالِثِ: مَلِكَةُ سَبَأٍ.",
             "In part three: the queen of Saba.", 30850),
        ],
        [  # Part 3: the queen of Saba (An-Naml 27:29-44, Saba 34:14)
            ("n", "قَرَأَتِ الْمَلِكَةُ الْكِتَابَ عَلَى قَوْمِهَا:",
             "The queen read the letter to her people:", 152483),
            ("a", 27, 30, 237672),
            ("a", 27, 31, 280486),
            ("n", "وَأَرْسَلَتْ إِلَيْهِ هَدِيَّةً تَخْتَبِرُهُ، فَرَدَّهَا، فَعَرَفَتْ أَنَّهُ نَبِيٌّ، فَجَاءَتْ إِلَيْهِ.",
             "She sent him a gift to test him. He refused it, and she knew he was a prophet, so she came to him.",
             26085),
            ("n", "وَقَبْلَ وُصُولِهَا، أُحْضِرَ عَرْشُهَا فِي طَرْفَةِ عَيْنٍ، فَقَالَ سُلَيْمَانُ:",
             "Before she arrived, her throne was brought in the blink of an eye, and Sulayman said:", 1099),
            ("a", 27, 40, 7127),
            ("n", "فَأَسْلَمَتِ الْمَلِكَةُ مَعَ سُلَيْمَانَ لِلَّهِ رَبِّ الْعَالَمِينَ.",
             "And the queen submitted, with Sulayman, to Allah, Lord of the worlds.", 2950),
            ("a", 27, 44, 201308),
            ("n", "وَمَاتَ سُلَيْمَانُ وَهُوَ مُتَّكِئٌ عَلَى عَصَاهُ، وَلَمْ يَعْلَمِ الْجِنُّ بِمَوْتِهِ إِلَّا بَعْدَ زَمَنٍ.",
             "Sulayman died leaning on his staff, and the jinn did not know of his death until much later.", 205427),
            ("a", 34, 14, 225775),
            ("n", "انْتَهَتْ قِصَّةُ سُلَيْمَانَ عَلَيْهِ السَّلَامُ. وَفِي الْقِصَّةِ الْقَادِمَةِ: نَبِيُّ اللَّهِ إِلْيَاسُ عَلَيْهِ السَّلَامُ.",
             "This was the story of Sulayman, peace be upon him. Next: the Prophet Ilyas, peace be upon him.", 21175),
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
    en = en.replace("ﷺ", "(peace be upon him)")  # the English font has no ﷺ sign (it showed as an empty box)
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

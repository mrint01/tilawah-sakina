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
PARTS = {"adam": 2, "idris": 1, "nuh": 3, "hud": 2, "salih": 2, "ibrahim": 5}
PART_TITLES = {"adam": ["The creation", "The garden"], "idris": ["Raised to a high place"],
               "nuh": ["The call", "The Ark", "The Flood"], "hud": ["The people of 'Ad", "The wind"],
               "salih": ["The she-camel", "The blast"],
               "ibrahim": ["The search", "The idols", "The fire", "The valley", "The sacrifice"]}
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

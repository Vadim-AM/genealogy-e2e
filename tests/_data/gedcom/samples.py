"""GEDCOM sample strings for import tests."""

GEDCOM_THREE_GEN = """0 HEAD
1 SOUR DeepTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Иван /Сидоров/
1 SEX M
1 BIRT
2 DATE 1920
2 PLAC Краснодар
1 DEAT
2 DATE 1990
0 @I2@ INDI
1 NAME Мария /Сидорова/
1 SEX F
1 BIRT
2 DATE 1925
0 @I3@ INDI
1 NAME Сергей /Сидоров/
1 SEX M
1 BIRT
2 DATE 1950
1 FAMC @F1@
1 FAMS @F2@
0 @I4@ INDI
1 NAME Елена /Иванова/
1 SEX F
1 BIRT
2 DATE 1952
1 FAMS @F2@
0 @I5@ INDI
1 NAME Андрей /Сидоров/
1 SEX M
1 BIRT
2 DATE 1980
1 FAMC @F2@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
0 @F2@ FAM
1 HUSB @I3@
1 WIFE @I4@
1 CHIL @I5@
0 TRLR
"""


GEDCOM_CYRILLIC_EDGE = """0 HEAD
1 SOUR CyrillicTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Пётр /Аксёнов-Жёлтый/
1 SEX M
1 BIRT
2 DATE 1900
2 PLAC село Ёлкино, Костромская губерния
1 DEAT
2 DATE 1973
2 PLAC Москва
0 @I2@ INDI
1 NAME Евдокия /Аксёнова-Жёлтая/
1 SEX F
1 BIRT
2 DATE 1905
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
0 TRLR
"""


GEDCOM_MINIMAL_INDI = """0 HEAD
1 SOUR MinimalTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Минимальный /Тестов/
1 SEX M
0 TRLR
"""


_NOTE_BIO = (
    "Участник Первой мировой войны, награждён Георгиевским крестом 4 степени. "
    "С 1924 года работал учителем в селе Никольское. "
    "Эвакуировался в 1942 году вместе с семьёй."
)
GEDCOM_WITH_NOTE = f"""0 HEAD
1 SOUR NoteTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Захар /Семёнов/
1 SEX M
1 BIRT
2 DATE 1885
1 NOTE {_NOTE_BIO}
0 TRLR
"""


SAMPLE_GEDCOM_UTF8 = (
    "0 HEAD\n"
    "1 SOUR Genealogy-e2e\n"
    "1 GEDC\n"
    "2 VERS 5.5.1\n"
    "1 CHAR UTF-8\n"
    "0 @I1@ INDI\n"
    "1 NAME Тестовый /Импортов/\n"
    "1 SEX M\n"
    "1 BIRT\n"
    "2 DATE 1900\n"
    "0 @I2@ INDI\n"
    "1 NAME Импортова /Тестовая/\n"
    "1 SEX F\n"
    "1 BIRT\n"
    "2 DATE 1902\n"
    "0 TRLR\n"
)


SAMPLE_GEDCOM_CP1251 = (
    "0 HEAD\n"
    "1 SOUR Tree-1251\n"
    "1 CHAR ANSI\n"
    "0 @I1@ INDI\n"
    "1 NAME Иван /Кириллов/\n"
    "1 SEX M\n"
    "1 BIRT\n"
    "2 DATE 1890\n"
    "0 TRLR\n"
)


SAMPLE_GEDCOM_MALFORMED = b"this is not a gedcom file just random text\x00\x01\xff\xfe"

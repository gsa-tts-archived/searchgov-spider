from search_gov_crawler.elasticsearch.i14y_helper import null_date, detect_lang

def test_null_date_valid_date():
    assert null_date("2025-03-13") == "2025-03-13"

def test_null_date_empty_string():
    assert null_date("") is None

def test_null_date_none():
    assert null_date(None) is None

def test_null_date_zero():
    assert null_date(0) is None

def test_null_date_false():
    assert null_date(False) is None

def test_detect_lang_english():
    assert detect_lang("This is a test sentence in English. And, this is another test sentence in English.") == "en"

def test_detect_lang_spanish():
    assert detect_lang("Esta es una frase de prueba en español.") == "es"

def test_detect_lang_chinese():
    assert detect_lang("这是一个中文测试句子。") == "zh" or detect_lang("这是一个中文测试句子.") == "zh" or detect_lang("这是一个中文测试句子.") == "zh"

def test_detect_lang_short_text():
    assert detect_lang("How are you?") == "en"

def test_detect_lang_empty_text():
    assert detect_lang("") is None

def test_detect_lang_unrecognizable_text():
    assert detect_lang("1234567890!@#$%^&*()") is None

import re
import datetime


def extract_yr(txt):
    num_found = False
    year = 0
    for ind in range(len(txt)):
        ch = txt[ind]
        if ch.isalpha() and not num_found:
            continue
        elif num_found:
            break
        else:
            year = year * 10 + int(ch)
            if ind < len(txt) and txt[ind+1].isalpha():
                num_found = True
    return year


def validate_roll_no(inp):
    current_year = datetime.datetime.today().year
    current_year = current_year - 2000
    _inp_year = current_year
    try:
        _inp_year = int(inp[2:4])
    except ValueError:
        _inp_year = extract_yr(inp)
    if re.search(r'[A-Z]{2}\d{2}[A-Z]+\d{5}', inp) is not None:
        if _inp_year <= current_year:
            print("Valid Username")
            return True
        else:
            print("Invalid Username")
            return False
    else:
        print("Invalid Username")
        return False


def validate_email(mail_id):
    if re.search(r'\w+@iith.ac.in', mail_id) is not None:
        print("Valid Email")
        return True
    else:
        return False

validate_roll_no("EP23BTECH11015")

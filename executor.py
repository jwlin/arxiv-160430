#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Interact with the browser with identified input fields, types and values
"""

import os, json, random, time, string
from preprocess import extract_features
from bs4 import BeautifulSoup
from selenium import webdriver

current_dir = os.path.dirname(__file__)
exp_dir = os.path.join(current_dir, 'trial', 'experiment2')
input_types = ['text', 'email', 'password']

# load easy-forms
form = dict()
with open(os.path.join(current_dir, 'easy-forms.txt'), 'r') as f:
    f.readline()  # id name country short_url submit_actions
    while True:
        line = f.readline()
        if not line:
            break
        tokens = line.split('\t')
        d_id = tokens[0]
        url = tokens[3]
        # e.g. tag=button&&string=Create Account;<button class="btn btn-custom" type="submit">Create Account</button>
        action_list = tokens[-1].split(';')[0].split('&&')
        tag = action_list[0].split('==')[1]
        attr = action_list[1].split('==')[0]
        value = action_list[1].split('==')[1]
        form[d_id] = {
            'url': url,
            'action': (tag, attr, value)
        }
'''
for k, v in form.items():
    print k
    print v['url']
    for k2, v2 in v.items():
        print k2, v2[0], v2[1], v2[2]
raw_input()
'''


def run_oracle():
    answer = dict()
    with open(os.path.join(current_dir, 'corpus', 'label-all-corpus.json'), 'r') as f:
        data = json.load(f)
    for k, v in data.items():
        sorted_f = ' '.join(sorted(v['feature'].split()))
        if sorted_f in answer.keys():
            assert answer[sorted_f] == v['type']
        else:
            answer[sorted_f] = v['type']
    # add additional features not identified in off-line forms
    answer['birthdate birthdate id name text type'] = 'date-mm/dd/yyyy'  # 125
    answer[
        'email email email email id id0 id0 j j name osuthemegradapptemplate osuthemegradapptemplate theform theform type'] = 'email'  # 65
    answer['address email id name text type verify verifyemail verifyemail'] = 'email'  # 27

    oracle_dir = os.path.join(exp_dir, 'oracle')
    if not os.path.exists(oracle_dir):
        os.makedirs(oracle_dir)
    # load databank
    with open(os.path.join(oracle_dir, 'databank-oracle.json'), 'r') as f:
        db = json.load(f)
    for doc_id, v in form.items():
        #if doc_id in ['125','88','89','137','65','66','67','68','69','81','24','27','2','5','4','8','141',
        #              '98','75','74','72','103','94','104','39','38','59','14','17','18','57','51','123',
        #              '32','110']:
        #    continue
        print doc_id
        if not os.path.exists(os.path.join(oracle_dir, doc_id)):
            os.makedirs(os.path.join(oracle_dir, doc_id))
        driver = init_webdriver(v['url'])
        driver.get_screenshot_as_file(os.path.join(oracle_dir, doc_id, 'entry.png'))
        inputs = get_inputs(driver.page_source.encode('utf-8'))
        used_type = dict()  # use the same value for the same type
        for my_input in inputs:  # my_input = [(feature, xpath), ...]
            print 'feature:', my_input[0]
            key = answer[my_input[0]]
            if key in used_type.keys():
                value = used_type[key]
            else:
                value = random.choice(db[key]) if db[key] else ''
                value = special_value(doc_id, key, value, used_type, db)
                used_type[key] = value
            element = driver.find_element_by_xpath(my_input[1])
            if not element:
                raise ValueError('Can not locate input field: ' + my_input[1])
            try:
                element.send_keys(value)
            except Exception as e:  # just ignore uninteractable elements
                print 'Exception in send_keys()', str(e)
                pass
        # special process for doc_id: incorrectly classified real type and uncaught, changed input in online forms
        used_type = special_process(driver, doc_id, used_type, db)
        with open(os.path.join(oracle_dir, doc_id, 'input_value.json'), 'w') as f:
            json.dump(used_type, f, indent=2, sort_keys=True, ensure_ascii=False)
        print v['action']
        if v['action'][1] == 'id':
            element = driver.find_element_by_id(v['action'][2])
        elif v['action'][1] == 'name':
            element = driver.find_element_by_name(v['action'][2])
        elif v['action'][1] == 'xpath':
            element = driver.find_element_by_xpath(v['action'][2])
        else:
            raise ValueError('Error locator')
        if not element:
            raise ValueError('No clickable found')
        element.click()
        time.sleep(3)
        if doc_id == '17':
            time.sleep(6)
        driver.get_screenshot_as_file(os.path.join(oracle_dir, doc_id, 'submitted.png'))
        with open(os.path.join(oracle_dir, doc_id, 'submitted.html'), 'w') as f:
            f.write(driver.page_source.encode('utf-8'))
        raw_input()
        driver.close()


def run_random():
    random_dir = os.path.join(exp_dir, 'random')
    if not os.path.exists(random_dir):
        os.makedirs(random_dir)
    for doc_id, v in form.items():
        #if doc_id in ['125','88','89','137','65','66','67','68','69','81','24','27','2','5','4','8','141',
        #              '98','75','74','72','103','94','104','39','38','59','14','17','18','57','51','123',
        #              '32','110']:
        #    continue
        print doc_id
        if not os.path.exists(os.path.join(random_dir, doc_id)):
            os.makedirs(os.path.join(random_dir, doc_id))
        driver = init_webdriver(v['url'])
        driver.get_screenshot_as_file(os.path.join(random_dir, doc_id, 'entry.png'))
        inputs = get_inputs(driver.page_source.encode('utf-8'))
        used_type = dict()  # use the same value for the same type
        for my_input in inputs:  # my_input = [(feature, xpath), ...]
            print 'feature:', my_input[0]
            value = ''.join(random.choice(string.letters + string.digits) for i in xrange(8))
            used_type[my_input[0]] = value
            element = driver.find_element_by_xpath(my_input[1])
            if not element:
                raise ValueError('Can not locate input field: ' + my_input[1])
            try:
                element.send_keys(value)
            except Exception as e:  # just ignore uninteractable elements
                print 'Exception in send_keys()', str(e)
                pass
        # special process for doc_id: incorrectly classified real type and uncaught, changed input in online forms
        used_type = special_process(driver, doc_id, used_type)
        with open(os.path.join(random_dir, doc_id, 'input_value.json'), 'w') as f:
            json.dump(used_type, f, indent=2, sort_keys=True, ensure_ascii=False)
        print v['action']
        if v['action'][1] == 'id':
            element = driver.find_element_by_id(v['action'][2])
        elif v['action'][1] == 'name':
            element = driver.find_element_by_name(v['action'][2])
        elif v['action'][1] == 'xpath':
            element = driver.find_element_by_xpath(v['action'][2])
        else:
            raise ValueError('Error locator')
        if not element:
            raise ValueError('No clickable found')
        try:
            element.click()
        except:
            pass
        time.sleep(3)
        check_alert(driver)
        if doc_id == '17':
            time.sleep(6)
        try:
            driver.get_screenshot_as_file(os.path.join(random_dir, doc_id, 'submitted.png'))
        except:
            pass
        with open(os.path.join(random_dir, doc_id, 'submitted.html'), 'w') as f:
            f.write(driver.page_source.encode('utf-8'))
        raw_input()
        driver.close()


def run_exp2():
    for mode in ['nlp', 'rule', 'rule_mul_nlp', 'rule_nm_nlp']:
        print mode
        dnames = [name for name in os.listdir(os.path.join(exp_dir)) if os.path.isdir(os.path.join(exp_dir, name))]
        for dname in dnames:
            if not dname.startswith('trial'):
                continue
            print dname

            # load databank
            with open(os.path.join(current_dir, 'databank.json'), 'r') as f:
                db = json.load(f)
            # disturb the email to avoid duplicated data
            if len(mode) > 4:
                db['email'][0] = dname[-4] + mode[-5] + db['email'][0]
            else:
                db['email'][0] = dname[-4] + mode[0] + db['email'][0]

            mode_dir = os.path.join(exp_dir, dname, mode)
            if not os.path.exists(mode_dir):
                os.makedirs(mode_dir)

            #with open(os.path.join(exp_dir, dname, 'input_types_with_data_' + mode + '.json'), 'r') as f:
            with open(os.path.join(exp_dir, dname, 'input_types_with_data.json'), 'r') as f:
                data = json.load(f)
            for doc_id in data.keys():
                if data[doc_id][0]['is_training']:
                    continue
                executed_names = [name for name in os.listdir(mode_dir) if os.path.isdir(mode_dir)]
                if doc_id in executed_names:
                    continue
                print doc_id
                if not os.path.exists(os.path.join(mode_dir, doc_id)):
                    os.makedirs(os.path.join(mode_dir, doc_id))
                # add additional features not identified in off-line forms
                if doc_id == '125':
                    data[doc_id].append({
                        "feature": "birthdate birthdate id name text type",
                        "is_training": False,
                        "type": {
                            "nlp": "date-mm/dd/yyyy",
                            "real": "date-mm/dd/yyyy",
                            "rule": "date-mm/dd/yyyy",
                            "rule_mul_nlp": "",
                            "rule_nm_nlp": ""
                        },
                        "value": {
                            "nlp": "01/20/1984",
                            "rule": "01/20/1984",
                            "rule_mul_nlp": "01/20/1984",
                            "rule_nm_nlp": "01/20/1984"
                        }
                    })
                elif doc_id == '65':
                    data[doc_id].append({
                        "feature": "email email email email id id0 id0 j j name osuthemegradapptemplate osuthemegradapptemplate theform theform type",
                        "is_training": False,
                        "type": {
                            "nlp": "email",
                            "real": "email",
                            "rule": "email",
                            "rule_mul_nlp": "",
                            "rule_nm_nlp": ""
                        },
                        "value": {
                            "nlp": db['email'][0],
                            "rule": db['email'][0],
                            "rule_mul_nlp": db['email'][0],
                            "rule_nm_nlp": db['email'][0]
                        }
                    })
                elif doc_id == '27':
                    for ele in data[doc_id]:
                        if ele['feature'] == 'e mail is invalid required type text id email name email':
                            data[doc_id].append({
                                "feature": "address email id name text type verify verifyemail verifyemail",
                                "is_training": False,
                                "type": {
                                    "nlp": "email",
                                    "real": "email",
                                    "rule": "email",
                                    "rule_mul_nlp": "",
                                    "rule_nm_nlp": ""
                                },
                                "value": {
                                    "nlp": ele['value']['nlp'],
                                    "rule": ele['value']['rule'],
                                    "rule_mul_nlp": ele['value']['rule_mul_nlp'],
                                    "rule_nm_nlp": ele['value']['rule_nm_nlp']
                                }
                            })
                            break

                driver = init_webdriver(form[doc_id]['url'], doc_id)
                if doc_id in ['27']:  # wait page to be loaded
                    time.sleep(3)
                try:
                    driver.get_screenshot_as_file(os.path.join(mode_dir, doc_id, 'entry.png'))
                except:
                    pass
                inputs = get_inputs(driver.page_source.encode('utf-8'))
                for my_input in inputs:  # my_input = [(feature, xpath), ...]
                    print 'feature:', my_input[0]
                    for ele in data[doc_id]:
                        if my_input[0] == ' '.join(sorted(ele['feature'].split())):
                            value = ele['value'][mode]
                            the_type = ele['type'][mode]
                            if mode == 'rule_mul_nlp' or mode == 'rule_nm_nlp':
                                if ele['type'][mode] == '':
                                    the_type = ele['type']['rule']
                            value = special_value(doc_id, the_type, value, dict(), db)
                    element = driver.find_element_by_xpath(my_input[1])
                    if not element:
                        raise ValueError('Can not locate input field: ' + my_input[1])
                    try:
                        element.send_keys(value)
                    except Exception as e:  # just ignore uninteractable elements
                        print 'Exception in send_keys()', str(e)
                        pass
                # special process for doc_id: incorrectly classified real type and uncaught, changed input in online forms
                special_process(driver, doc_id, dict(), db)
                print form[doc_id]['action']
                if form[doc_id]['action'][1] == 'id':
                    element = driver.find_element_by_id(form[doc_id]['action'][2])
                elif form[doc_id]['action'][1] == 'name':
                    element = driver.find_element_by_name(form[doc_id]['action'][2])
                elif form[doc_id]['action'][1] == 'xpath':
                    element = driver.find_element_by_xpath(form[doc_id]['action'][2])
                else:
                    raise ValueError('Error locator')
                if not element:
                    raise ValueError('No clickable found')
                #raw_input('ready')
                element.click()
                time.sleep(3)
                check_alert(driver)
                if doc_id == '17':
                    time.sleep(8)
                try:
                    driver.get_screenshot_as_file(os.path.join(mode_dir, doc_id, 'submitted.png'))
                except:
                    pass
                try:
                    with open(os.path.join(mode_dir, doc_id, 'submitted.html'), 'w') as f:
                        f.write(driver.page_source.encode('utf-8'))
                except:
                    pass
                #raw_input('done')
                driver.close()


def init_webdriver(url, doc_id=None):
    try:
        if doc_id in ['141']:  # problematic page when using Chrome ..
            driver = webdriver.Firefox()
        else:
            # chrome_options = webdriver.ChromeOptions()
            # chrome_options.add_argument("--incognito")
            # driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=os.path.join(current_dir, 'chromedriver_win32', 'chromedriver.exe'))
            driver = webdriver.Chrome(executable_path=os.path.join(current_dir, 'chromedriver_win32', 'chromedriver.exe'))

        driver.set_window_size(1280, 960)
        #driver.implicitly_wait(30)
        driver.set_page_load_timeout(30)
        driver.get(url)
        return driver
    except Exception as e:
        print str(e)


def get_inputs(dom):
    soup = BeautifulSoup(dom, 'html5lib')
    # remove unrelated tags
    for invisible_tag in ['style', 'script', '[document]', 'head', 'title']:
        for tag in soup.find_all(invisible_tag):
            tag.decompose()
    # special process for nested span uncaught in off-line forms ...
    for element in soup.find_all():
        if element.attrs:
            if element.has_attr('unselectable') and 'on' in element['unselectable']:
                element.clear()
                continue
    input_list = []
    for input_type in input_types:
        inputs = soup.find_all('input', attrs={'type': input_type})
        for my_input in inputs:
            if is_invisible(my_input):
                continue
            xpath = get_xpath(my_input)
            feature = extract_features(my_input)
            feature = ' '.join(sorted(feature.split()))
            input_list.append((feature, xpath))
    return input_list


def get_node(node):
    # for XPATH we only count for nodes with the same type
    l = len(node.find_previous_siblings(node.name)) + 1
    return '%s[%s]' % (node.name, l)


def get_xpath(node):
    path = [get_node(node)]
    for parent in node.parents:
        if parent.name == 'body':
            break
        path.insert(0, get_node(parent))
    return '//html/body/' + '/'.join(path)


def is_invisible(node):
    if node.attrs:
        if node.has_attr('style') and 'display:' in node['style'] and 'none' in node['style']:
            return True
    return False


def special_value(doc_id, the_type, old_value, type_d, db):
    if doc_id == '125':
        if the_type == 'uname':
            if 'email' in type_d.keys():
                new_value = type_d['email']
            else:
                new_value = random.choice(db['email']) if db['email'] else ''
                type_d['uname'] = new_value
            return new_value
    elif doc_id == '141':
        if the_type == 'uname':
            if 'email' in type_d.keys():
                new_value = type_d['email']
            else:
                new_value = random.choice(db['email']) if db['email'] else ''
                type_d['uname'] = new_value
            return new_value
    elif doc_id == '137':
        if the_type == 'short_pwd':
            new_value = '987654'
            type_d['short_pwd'] = new_value
            return new_value
    elif doc_id == '39':
        if the_type == 'pwd':
            new_value = 'P@ssw0rd123456'
            type_d['pwd'] = new_value
            return new_value
    elif doc_id == '110':
        if the_type == 'pwd':
            new_value = 'Passw0rd'
            type_d['pwd'] = new_value
            return new_value
    return old_value


def special_process(driver, doc_id, type_d, db=None):
    # special process for doc_id: incorrectly classified real type and uncaught, changed input in online forms
    # or other actions needed to pass the form
    if not db:  # for run_random()
        db = dict()
        db['email'] = [''.join(random.choice(string.letters + string.digits) for i in xrange(8))]
        db['date-dd/mm/yyyy'] = [''.join(random.choice(string.letters + string.digits) for i in xrange(8))]
        db['uname'] = [''.join(random.choice(string.letters + string.digits) for i in xrange(8))]
    if doc_id == '141':
        element = driver.find_element_by_id('dtDateOfBirth')
        if 'date-dd/mm/yyyy' in type_d.keys():
            value = type_d['date-dd/mm/yyyy']
        else:
            value = random.choice(db['date-dd/mm/yyyy']) if db['date-dd/mm/yyyy'] else ''
            type_d['date-dd/mm/yyyy'] = value
        element.send_keys(value)
    elif doc_id == '32':
        element = driver.find_element_by_id('applicantId')
        if 'uname' in type_d.keys():
            value = type_d['uname']
        else:
            value = random.choice(db['uname']) if db['uname'] else ''
            type_d['uname'] = value
        element.send_keys(value)
    elif doc_id == '74':
        element = driver.find_element_by_id('EmailAddress')
        element.click()
        time.sleep(1)
    elif doc_id == '39':
        if 'special_id' in type_d.keys():
            del(type_d['special_id'])
        time.sleep(2)
    return type_d

def check_alert(driver):
    while True:
        try:
            alert = driver.switch_to.alert()
            alert.dismiss()
        except Exception:
            break


if __name__ == '__main__':
    run_exp2()

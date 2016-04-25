#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Infer testing data with rules from training datapre
"""

import os, json, random
import numpy
from bs4 import BeautifulSoup


if __name__ == '__main__':
    current_dir = os.path.dirname(__file__)
    trial_dir = os.path.join(current_dir, 'trial')
    input_dir = os.path.join(current_dir, 'corpus', 'all-input')

    # preload all .input files into memory
    inputs = dict()
    for fname in os.listdir(input_dir):
        key = fname.split('-')[0]
        with open(os.path.join(input_dir, fname), 'r') as f:
            data = json.load(f)
        inputs[key] = data


    dnames = [name for name in os.listdir(trial_dir) if os.path.isdir(os.path.join(trial_dir, name))]
    for dname in dnames:  # e.g. 10-training, 20-training, ...
        print dname
        '''
        # for experiment 2 (easy-forms)
        if dname != 'experiment2':
            continue
        '''
        correction_rates = []
        multiple_types = []
        no_matches = []
        program_rule_match_logs = list()  # cache for log file
        sub_dnames = [name for name in os.listdir(os.path.join(trial_dir, dname)) if os.path.isdir(os.path.join(trial_dir, dname, name))]
        for sub_dname in sub_dnames:  # e.g. trial-20160316-010033, trial-20160316-010035, ...
            rule_match_logs = list()  # cache for log file
            print sub_dname
            # load training and testing set
            with open(os.path.join(trial_dir, dname, sub_dname, 'config.json'), 'r') as f:
                config = json.load(f)
                training_ids = list(config['training_ids'])
                testing_ids = list(config['testing_ids'])
            #print dname, sub_dname, training_ids
            #raw_input()

            # add rules from training data into rules
            '''
            e.g. rules = {
                'fname': {
                    'name': ['first', 'fname'],
                    'id': ['first', 'fname'],
                },
                'email': {
                    'name': ['email'],
                    'id': ['email'],
                    'type': ['email']
                }
            }
            '''
            print 'Grab rules'
            rules = dict()
            for _id in training_ids:
                #print _id
                input_data = inputs[_id]
                for item in input_data:
                    _type = item['type']  # e.g. 'fname'
                    if _type not in rules.keys():
                        rules[_type] = dict(item['rule'])
                    else:
                        for k, v in item['rule'].items():
                            if k in rules[_type].keys():  # e.g. 'id'
                                rules[_type][k] += [l for l in item['rule'][k] if l not in rules[_type][k]]
                            else:
                                rules[_type][k] = item['rule'][k]
            '''
            for k, v in rules.items():
                print k
                print v
            #raw_input()
            '''
            rule_match_logs.append('Rules derived from training data:\n')
            for k, v in rules.items():
                rule_match_logs.append('Topic: %s, Rules: %s\n' % (k, v))

            # test rules with training data
            print 'Self-test rules'
            num_training = 0
            for _id in training_ids:
                #print _id
                input_data = inputs[_id]
                for item in input_data:
                    soup = BeautifulSoup(item['dom'], 'html5lib')
                    _input = soup.find('input')
                    _types = set()
                    for k, v_dict in rules.items():
                        for attr, value_list in v_dict.items():
                            if attr in _input.attrs:
                                for value in value_list:
                                    if value in _input[attr]:
                                        '''
                                        print _input
                                        print attr
                                        print _input[attr]
                                        '''
                                        _types.add(k)
                                        break
                    assert item['type'] in _types  # e.g. 'fname'
                    '''
                    if len(_types) > 1:
                        print _types
                        raw_input()
                    '''
                    num_training += 1

            # infer testing data with rules
            print 'Inferring'
            num_testing = 0
            num_incorrect = 0
            num_no_match = 0
            num_multiple_types = 0
            for _id in testing_ids:
                #print _id
                rule_match_logs.append('Doc id: %s\n' % _id)
                input_data = inputs[_id]
                for item in input_data:
                    soup = BeautifulSoup(item['dom'], 'html5lib')
                    _input = soup.find('input')
                    _types = set()
                    for k, v_dict in rules.items():
                        for attr, value_list in v_dict.items():
                            if attr in _input.attrs:
                                for value in value_list:
                                    if value in _input[attr]:
                                        _types.add(k)
                                        break
                    if not _types:
                        rule_match_logs.append('No Match. Type: %s\nDom: %s\nFeature: %s\n' %
                                               (item['type'], item['dom'], item['feature']))
                        num_incorrect += 1
                        num_no_match += 1
                    elif len(_types) > 1:
                        rule_match_logs.append('Multiple candidate types: %s\n' % _types)
                        rule_match_logs.append('Type: %s\nDom: %s\nFeature: %s\n' % (item['type'], item['dom'], item['feature']))
                        num_multiple_types += 1
                        inferred_type = random.choice(list(_types))
                        if inferred_type != item['type']:
                            rule_match_logs.append('Wrong from multiple candidates: %s. Ans: %s\n' % (inferred_type, item['type']))
                            num_incorrect += 1
                    else:  # len(_types) == 1
                        inferred_type = _types.pop()
                        if inferred_type != item['type']:
                            rule_match_logs.append('Wrong from single candidate: %s. Type: %s\nDom: %s\nFeature: %s\n' %
                                                   (inferred_type, item['type'], item['dom'], item['feature']))
                            num_incorrect += 1
                    num_testing += 1
            assert num_training + num_testing == 985

            # statistics
            with open(os.path.join(trial_dir, dname, sub_dname, 'rule_match.log'), 'w') as f:
                f.writelines(rule_match_logs)
                f.write('## %s Summary ##\n' % sub_dname)
                f.write('# of training data: %d\n' % num_training)
                f.write('total inferred: %d\n' % num_testing)
                f.write('# of multiple types: %d\n' % num_multiple_types)
                f.write('correction rate: %d/%d (%f)\n' %
                        (num_testing-num_incorrect, num_testing, ((num_testing-num_incorrect)/float(num_testing))))
                f.write('num_no_match: %d\n' % num_no_match)

            program_rule_match_logs.append('## %s Summary ##\n' % sub_dname)
            program_rule_match_logs.append('# of training data: %d\n' % num_training)
            program_rule_match_logs.append('total inferred: %d\n' % num_testing)
            program_rule_match_logs.append('# of multiple types: %d\n' % num_multiple_types)
            program_rule_match_logs.append('correction rate: %d/%d (%f)\n' %
                                           (num_testing-num_incorrect, num_testing, ((num_testing-num_incorrect)/float(num_testing))))
            program_rule_match_logs.append('num_no_match: %d\n' % num_no_match)

            correction_rates.append(((num_testing-num_incorrect)/float(num_testing)))
            multiple_types.append(num_multiple_types)
            no_matches.append(num_no_match)

        with open(os.path.join(trial_dir, dname, 'program_rule_match.log'), 'w') as f:
            f.writelines(program_rule_match_logs)
            arr = numpy.array(correction_rates)
            f.write('## %s Summary ##\n' % dname)
            f.write('avg correction rate: %f\t' % numpy.mean(arr))
            f.write('std: %f\t' % numpy.std(arr))
            f.write('min: %f\t' % numpy.min(arr))
            f.write('max: %f\n' % numpy.max(arr))

            arr = numpy.array(multiple_types)
            f.write('avg multiple_types: %f\t' % numpy.mean(arr))
            f.write('std: %f\t' % numpy.std(arr))
            f.write('min: %f\t' % numpy.min(arr))
            f.write('max: %f\n' % numpy.max(arr))

            arr = numpy.array(no_matches)
            f.write('avg no_matches: %f\t' % numpy.mean(arr))
            f.write('std: %f\t' % numpy.std(arr))
            f.write('min: %f\t' % numpy.min(arr))
            f.write('max: %f\n' % numpy.max(arr))
        #raw_input(dname)

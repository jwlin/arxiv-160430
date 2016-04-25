#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Combine nlp and rule-based approaches from logs and calculate the correction rates
(Generate no_match_with_nlp.log, multiple_with_nlp.log, program_combine.log)
"""

import os, random
import numpy


def load_rule_match_log(fpath):
    '''
    rule_match_data = {
        'id': {
            'no_match': list of (_type, feature)
            'single': list of (_type, feature, inferred_type)
            'multiple': list of {
                'data': list of (_type, feature, candidates_list)
                'ans': boolean
                'choice': the inferred type
            }
        'num_correct': int
        'num_total': int
        'num_no_match': int
        'num_multiple': int
        }
    }
    '''
    rm_data = dict()
    with open(fpath, 'r') as f:
        d_id = ''
        while True:
            line = f.readline()
            if line.startswith('Doc id'):
                d_id = line.split()[-1]
                rm_data[d_id] = dict()
            elif line.startswith('No Match'):
                _type = line.split()[-1]
                f.readline()  # skip 'Dom'
                line = f.readline()  # Feature
                assert line.startswith('Feature')
                feature = line.split(': ')[-1].replace('\n', '')
                if 'no_match' not in rm_data[d_id].keys():
                    rm_data[d_id]['no_match'] = [(_type, feature)]
                else:
                    rm_data[d_id]['no_match'].append((_type, feature))
            elif line.startswith('Multiple candidate'):  # e.g. Multiple candidate types: set([u'date', u'date-mm/dd/yyyy'])
                candidates = []
                for token in line.split(','):
                    candidates.append(token.split('\'')[1])
                line = f.readline()
                assert line.startswith('Type')
                _type = line.split(': ')[-1].replace('\n', '')
                f.readline()  # skip 'Dom'
                line = f.readline()
                assert line.startswith('Feature')
                feature = line.split(': ')[-1].replace('\n', '')
                if 'multiple' not in rm_data[d_id].keys():
                    rm_data[d_id]['multiple'] = [{
                        'data': (_type, feature, candidates),
                        'ans': True,
                        'choice': _type
                    }]
                else:
                    rm_data[d_id]['multiple'].append({
                        'data': (_type, feature, candidates),
                        'ans': True,
                        'choice': _type
                    })
            elif line.startswith('Wrong from multiple candidates'):  # e.g. Wrong from multiple candidates: date-dd/mm/yyyy. Ans: date-mm/dd/yyyy
                inferred = line.split('.')[0].split()[-1]
                rm_data[d_id]['multiple'][-1]['ans'] = False
                rm_data[d_id]['multiple'][-1]['choice'] = inferred
            elif line.startswith('Wrong from single candidate'):  # e.g. Wrong from single candidate: pwd. Type: complex_pwd
                inferred = line.split('.')[0].split()[-1]
                _type = line.split('.')[1].split()[-1]
                f.readline()  # skip 'Dom'
                line = f.readline()
                assert line.startswith('Feature')
                feature = line.split(': ')[-1].replace('\n', '')
                if 'single' not in rm_data[d_id].keys():
                    rm_data[d_id]['single'] = [(_type, feature, inferred)]
                else:
                    rm_data[d_id]['single'].append((_type, feature, inferred))
            elif line.startswith('##'):  # end of log
                f.readline()  # skip '# of training data'
                f.readline()  # skip 'total inferred'
                line = f.readline()
                assert line.startswith('# of multiple types')
                rm_data['num_multiple'] = int(line.split(': ')[-1])
                line = f.readline()
                assert line.startswith('correction rate')  # e.g. correction rate: 632/860 (0.734884)
                num = line.split(': ')[-1].split(' ')[0].split('/')
                rm_data['num_correct'] = int(num[0])
                rm_data['num_total'] = int(num[1])
                line = f.readline()
                assert line.startswith('num_no_match')  # e.g. num_no_match: 183
                rm_data['num_no_match'] = int(line.split(': ')[-1])
                break

    # check the numbers
    num_no_match = 0
    num_multiple = 0
    num_incorrect = 0
    for k, v in rm_data.items():
        if v and type(v) is dict:
            if 'no_match' in v.keys():
                num_no_match += len(v['no_match'])
                num_incorrect += len(v['no_match'])
            if 'multiple' in v.keys():
                num_multiple += len(v['multiple'])
                for ele in v['multiple']:
                    if not ele['ans']:
                        num_incorrect += 1
            if 'single' in v.keys():
                num_incorrect += len(v['single'])
    assert num_no_match == rm_data['num_no_match']
    assert num_multiple == rm_data['num_multiple']
    assert num_incorrect == rm_data['num_total'] - rm_data['num_correct']
    '''
    for k, v in rule_match_data.items():
        print k
        print v
    '''
    return rm_data


def load_log_data(fpath):
    '''
    log_data = {
        'id': {
            'single': list of (_type, feature, inferred_type)
        }
        'num_correct': int
        'num_total': int
    }
    '''
    l_data = dict()
    with open(fpath, 'r') as f:
        d_id = ''
        while True:
            line = f.readline()
            if line.startswith('corpus:'):  # e.g. corpus: 103
                d_id = line.split()[-1]
                l_data[d_id] = dict()
            # e.g. feature: email address password confirm password name searchtext id search type text maxlength 255. inferred: pwd. ans: search_term
            elif line.startswith('feature:'):
                tokens = line.split('.')
                feature = tokens[0].replace('feature: ', '')
                inferred = tokens[1].split()[-1]
                _type = tokens[2].split()[-1]
                if 'single' not in l_data[d_id].keys():
                    l_data[d_id]['single'] = [(_type, feature, inferred)]
                else:
                    l_data[d_id]['single'].append((_type, feature, inferred))
            elif line.startswith('##'):  # end of log
                f.readline()  # skip '# of training data'
                f.readline()  # skip 'total inferred'
                f.readline()  # skip '# of multiple types:'
                line = f.readline()
                assert line.startswith('correction rate')  # e.g. correction rate: 644/860 (0.748837)
                num = line.split(': ')[-1].split()[0].split('/')
                l_data['num_correct'] = int(num[0])
                l_data['num_total'] = int(num[1])
                break

    # check the numbers
    num_incorrect = 0
    for k, v in l_data.items():
        if v and type(v) is dict:
            if 'single' in v.keys():
                num_incorrect += len(v['single'])
    assert num_incorrect == l_data['num_total'] - l_data['num_correct']
    '''
    for k, v in l_data.items():
        print k
        print v
    '''
    return l_data


if __name__ == '__main__':
    current_dir = os.path.dirname(__file__)
    trial_dir = os.path.join(current_dir, 'trial')

    dnames = [name for name in os.listdir(trial_dir) if os.path.isdir(os.path.join(trial_dir, name))]
    for dname in dnames:  # e.g. 10-training, 20-training, ...
        print dname
        '''
        # for experiment 2 (easy-forms)
        if dname != 'experiment2':
            continue
        '''
        program_combine_logs = []
        no_match_correction_rates = []
        multiple_correction_rates = []
        combined_correction_rates = []
        sub_dnames = [name for name in os.listdir(os.path.join(trial_dir, dname)) if os.path.isdir(os.path.join(trial_dir, dname, name))]
        for sub_dname in sub_dnames:  # e.g. trial-20160316-010033, trial-20160316-010035, ...
            print sub_dname
            rule_match_data = load_rule_match_log(os.path.join(trial_dir, dname, sub_dname, 'rule_match.log'))
            log_data = load_log_data(os.path.join(trial_dir, dname, sub_dname, 'log.txt'))

            # try to infer the no_match feature with log_data (the nlp way)
            num_new_match = 0
            no_match_with_nlp_logs = []
            for k, v in rule_match_data.items():
                if v and type(v) is dict and 'no_match' in v.keys():  # also means k is doc_id
                    assert k in log_data.keys()
                    no_match_with_nlp_logs.append('doc id: %s\n' % k)
                    for _type, feature in rule_match_data[k]['no_match']:
                        if not log_data[k]:  # no error feature in log_data for the doc id, means correctly inferred
                            num_new_match += 1
                            no_match_with_nlp_logs.append('type: %s, feature: %s, type_from_nlp: %s\n' % (_type, feature, _type))
                        else:
                            assert 'single' in log_data[k].keys()
                            found = False
                            for t, f, i in log_data[k]['single']:
                                if f == feature:  # still incorrectly inferred
                                    found = True
                                    assert t == _type
                                    no_match_with_nlp_logs.append('type: %s, feature: %s, type_from_nlp: %s\n' % (_type, feature, i))
                                    break
                            if not found:
                                num_new_match += 1
                                no_match_with_nlp_logs.append('type: %s, feature: %s, type_from_nlp: %s\n' % (_type, feature, _type))
            with open(os.path.join(trial_dir, dname, sub_dname, 'no_match_with_nlp.log'), 'w') as f:
                f.writelines(no_match_with_nlp_logs)
                f.write('## %s Summary ##\n' % sub_dname)
                f.write('original correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'], rule_match_data['num_total'],
                        (rule_match_data['num_correct']/float(rule_match_data['num_total']))))
                f.write('new matches: %d\n' % num_new_match)
                f.write('new correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'] + num_new_match, rule_match_data['num_total'],
                        ((rule_match_data['num_correct'] + num_new_match)/float(rule_match_data['num_total']))))
            program_combine_logs.append('## %s Summary ##\n' % sub_dname)
            program_combine_logs.append('original correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'], rule_match_data['num_total'],
                        (rule_match_data['num_correct']/float(rule_match_data['num_total']))))
            program_combine_logs.append('new matches: %d\n' % num_new_match)
            program_combine_logs.append('new correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'] + num_new_match, rule_match_data['num_total'],
                        ((rule_match_data['num_correct'] + num_new_match)/float(rule_match_data['num_total']))))
            no_match_correction_rates.append((rule_match_data['num_correct'] + num_new_match)/float(rule_match_data['num_total']))

            # try to infer the multiple candidates feature with log_data (the nlp way)
            difference = 0
            multiple_with_nlp_logs = []
            for k, v in rule_match_data.items():
                if v and type(v) is dict and 'multiple' in v.keys():  # also means k is doc_id
                    assert k in log_data.keys()
                    multiple_with_nlp_logs.append('doc id: %s\n' % k)
                    for ele in rule_match_data[k]['multiple']:
                        _type, feature, candidate_list = ele['data']
                        ans = ele['ans']
                        if not log_data[k]:  # no error feature in log_data for the doc id, means correctly inferred
                            type_from_nlp = _type
                        else:
                            assert 'single' in log_data[k].keys()
                            found = False
                            for t, f, i in log_data[k]['single']:
                                if f == feature:  # still incorrectly inferred
                                    found = True
                                    type_from_nlp = i
                                    break
                            if not found:
                                type_from_nlp = _type
                        multiple_with_nlp_logs.append('type: %s, feature: %s, candidates: %s, type_from_nlp: %s\n' %
                                                      (_type, feature, candidate_list, type_from_nlp))
                        # consider type_from_nlp together with the original candidates
                        if type_from_nlp in candidate_list:
                            type_final = type_from_nlp
                        else:
                            candidate_list.append(type_from_nlp)
                            type_final = random.choice(candidate_list)
                        if type_final == _type:
                            ans_final = True
                        else:
                            ans_final = False
                        multiple_with_nlp_logs.append('choice: %s, ans: %s, ans_final: %s\n' % (type_final, ans, ans_final))
                        if ans and not ans_final:
                            difference -= 1
                        elif not ans and ans_final:
                            difference += 1
            with open(os.path.join(trial_dir, dname, sub_dname, 'multiple_with_nlp.log'), 'w') as f:
                f.writelines(multiple_with_nlp_logs)
                f.write('## %s Summary ##\n' % sub_dname)
                f.write('original correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'], rule_match_data['num_total'],
                        (rule_match_data['num_correct']/float(rule_match_data['num_total']))))
                f.write('difference: %d\n' % difference)
                f.write('new correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'] + difference, rule_match_data['num_total'],
                        ((rule_match_data['num_correct'] + difference)/float(rule_match_data['num_total']))))
            program_combine_logs.append('difference: %d\n' % difference)
            program_combine_logs.append('new correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'] + difference, rule_match_data['num_total'],
                        ((rule_match_data['num_correct'] + difference)/float(rule_match_data['num_total']))))
            program_combine_logs.append('combined correction rate: %d/%d (%f)\n' %
                        (rule_match_data['num_correct'] + difference + num_new_match, rule_match_data['num_total'],
                        ((rule_match_data['num_correct'] + difference + num_new_match)/float(rule_match_data['num_total']))))
            multiple_correction_rates.append((rule_match_data['num_correct'] + difference)/float(rule_match_data['num_total']))
            combined_correction_rates.append((rule_match_data['num_correct'] + difference + num_new_match)/float(rule_match_data['num_total']))

        with open(os.path.join(trial_dir, dname, 'program_combine.log'), 'w') as f:
            f.writelines(program_combine_logs)
            arr = numpy.array(no_match_correction_rates)
            f.write('## %s Summary ##\n' % dname)
            f.write('no_match-with-nlp correction rate: %f\t' % numpy.mean(arr))
            f.write('std: %f\t' % numpy.std(arr))
            f.write('min: %f\t' % numpy.min(arr))
            f.write('max: %f\n' % numpy.max(arr))

            arr = numpy.array(multiple_correction_rates)
            f.write('multiple-with-nlp correction rate: %f\t' % numpy.mean(arr))
            f.write('std: %f\t' % numpy.std(arr))
            f.write('min: %f\t' % numpy.min(arr))
            f.write('max: %f\n' % numpy.max(arr))

            arr = numpy.array(combined_correction_rates)
            f.write('combined correction rate: %f\t' % numpy.mean(arr))
            f.write('std: %f\t' % numpy.std(arr))
            f.write('min: %f\t' % numpy.min(arr))
            f.write('max: %f\n' % numpy.max(arr))

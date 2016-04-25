#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Train with training data and infer testing data, then calculate correction rate
(Generate log.txt, program.log)
"""

import os, random, datetime, json
import numpy
from gensim import corpora, models, similarities

current_dir = os.path.dirname(__file__)
corpus_dir = os.path.join(current_dir, 'corpus', 'all-corpus')
answer = dict()
with open(os.path.join(current_dir, 'corpus', 'label-all-corpus.json'), 'r') as f:
    data = json.load(f)
for k, v in data.items():
    if v['feature'] in answer.keys():
        assert answer[v['feature']] == v['type']
    else:
        answer[v['feature']] = v['type']

ids = list()
all_corpus = dict()  # load all corpus file at first
for fname in os.listdir(corpus_dir):
    key = fname.split('-')[0]
    ids.append(key)
    all_corpus[key] = [line.lower().split() for line in open(os.path.join(corpus_dir, fname), 'r')]

'''
# load easy-forms, replace ids with the ids in easy-forms
ids = list()
with open(os.path.join(current_dir, 'easy-forms.txt'), 'r') as f:
    f.readline()
    while True:
        line = f.readline()
        if not line:
            break
        ids.append(line.split('\t')[0])
'''

iteration = 1000
correction = []
program_log_data = []
for it in xrange(iteration):
    print 'iteration', it
    trial_dir = os.path.join(current_dir, 'trial', 'trial-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    os.makedirs(trial_dir)
    # Randomly pick 20 corpus as training data
    random.shuffle(ids)
    training_ids = ids[:7]
    testing_ids = ids[7:]
    with open(os.path.join(trial_dir, 'config.json'), 'w') as f:
        json.dump(
            {
                'training_ids': training_ids,
                'testing_ids': testing_ids
            },
            f, indent=2, sort_keys=True, ensure_ascii=False
        )

    # Train with training data, automatically label them with the answer
    corpus = []
    for t_id in training_ids:
        corpus += all_corpus[t_id]
    dictionary = corpora.Dictionary(corpus)
    # common words and tokenize to remove
    stoplist = set('your a the is and or in be to of for not on with as by'.split())
    # remove stop words and words that appear only once
    stop_ids = [dictionary.token2id[stopword] for stopword in stoplist if stopword in dictionary.token2id]
    #once_ids = [tokenid for tokenid, docfreq in dictionary.dfs.iteritems() if docfreq == 1]
    once_ids = []
    dictionary.filter_tokens(stop_ids + once_ids)  # remove stop words and words that appear only once
    dictionary.compactify()  # remove gaps in id sequence after words that were removed
    dictionary.save(os.path.join(trial_dir, 'trial.dict'))  # store the dictionary, for future reference

    corpus_bow = []
    for t_id in training_ids:
        corpus_bow += [dictionary.doc2bow(c) for c in all_corpus[t_id]]
    corpora.MmCorpus.serialize(os.path.join(trial_dir, 'trial.mm'), corpus_bow)  # store to disk, for later use

    tfidf = models.TfidfModel(corpus_bow)  # initialize (train) a model
    tfidf.save(os.path.join(trial_dir, 'trial.tfidf'))
    corpus_tfidf = tfidf[corpus_bow]
    lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=50)  # initialize an LSI transformation
    lsi.save(os.path.join(trial_dir, 'trial.lsi'))
    corpus_lsi = lsi[corpus_tfidf]
    index = similarities.MatrixSimilarity(corpus_lsi)  # transform corpus to LSI space and index it
    index.save(os.path.join(trial_dir, 'trial.index'))

    training_topic = {}
    for i in xrange(len(corpus)):
        feature = ' '.join(corpus[i])
        training_topic[str(i)] = {
            'type': answer[feature],
            'feature': feature
        }
    with open(os.path.join(trial_dir, 'training_topic.json'), 'w') as f:
        json.dump(training_topic, f, indent=2, sort_keys=True, ensure_ascii=False)

    # Infer testing data, calculate correction rate
    print 'Inference start'
    num_total = 0
    num_incorrect = 0
    num_multiple_types = 0

    log_data = []
    for t_id in testing_ids:
        log_data.append('corpus: %s\n' % t_id)
        '''
        with open(os.path.join(trial_dir, 'log.txt'), 'a') as f:
            f.write('corpus: %s\n' % t_id)
        '''
        for d in all_corpus[t_id]:
            num_total += 1
            vec_bow = dictionary.doc2bow(d)
            #print vec_bow
            vec_tfidf = tfidf[vec_bow]
            #print vec_tfidf
            vec_lsi = lsi[vec_tfidf]  # convert the query to LSI space
            sims = index[vec_lsi]  # perform a similarity query against the corpus
            sims = sorted(enumerate(sims), key=lambda item: -item[1])
            #print sims
            vec_type = training_topic[str(sims[0][0])]['type']
            feature = ' '.join(d)
            if (sims[0][1] - sims[4][1]) < 0.1:  # the similarity range of top 5 items is less than 0.1
                topic_count = {}
                for s in sims[:5]:
                    key = str(s[0])
                    if training_topic[key]['type'] in topic_count.keys():
                        topic_count[training_topic[key]['type']] += 1
                    else:
                        topic_count[training_topic[key]['type']] = 1
                max_times = topic_count[max(topic_count, key=topic_count.get)]
                max_types = { training_topic[str(v[0])]['type'] for v in sims[:5] if topic_count[training_topic[str(v[0])]['type']] == max_times }
                if len(max_types) > 1:
                    #print 'More than one candidate types: %s', max_types
                    log_data.append('More than one candidate types: %s. Ans: %s\n' % (max_types, answer[feature]))
                    '''
                    with open(os.path.join(trial_dir, 'log.txt'), 'a') as f:
                        f.write('More than one candidate types: %s. Ans: %s\n' % (max_types, answer[feature]))
                    '''
                    num_multiple_types += 1
                vec_type = random.choice(list(max_types))
            if vec_type != answer[feature]:
                #print 'feature:', feature
                #print 'Inferred type:', vec_type, 'Answer:', answer[feature], vec_type==answer[feature]
                log_data.append('feature: %s. inferred: %s. ans: %s\n' % (feature, vec_type, answer[feature]))
                log_data.append('sims[:5]:\n')
                for s in sims[:5]:
                    log_data.append('%s, %s, %s: %s\n' % (
                        s[0], s[1], training_topic[str(s[0])]['type'], training_topic[str(s[0])]['feature']))
                log_data.append('-----\n')
                '''
                with open(os.path.join(trial_dir, 'log.txt'), 'a') as f:
                    f.write('feature: %s. inferred: %s. ans: %s\n' % (feature, vec_type, answer[feature]))
                    f.write('sims[:5]:\n')
                    for s in sims[:5]:
                        f.write('%s, %s, %s: %s\n' % (
                            s[0], s[1], training_topic[str(s[0])]['type'], training_topic[str(s[0])]['feature']))
                    f.write('-----\n')
                '''
                num_incorrect += 1
                #raw_input()
    assert len(training_topic) + num_total == 985
    print '# of training data:', len(training_topic)
    print 'total inferred:', num_total
    print '# of multiple types:', num_multiple_types
    print 'correction rate: %d/%d (%f)' % (num_total-num_incorrect, num_total, ((num_total-num_incorrect)/float(num_total)))
    with open(os.path.join(trial_dir, 'log.txt'), 'w') as f:
        f.writelines(log_data)
        f.write('## Summary iteration %d ##\n' % it)
        f.write('# training data: %d\n' % len(training_topic))
        f.write('total inferred: %d\n' % num_total)
        f.write('# of multiple types: %d\n' % num_multiple_types)
        f.write('correction rate: %d/%d (%f)\n' % (num_total-num_incorrect, num_total, ((num_total-num_incorrect)/float(num_total))))

    program_log_data.append('## Summary iteration %d ##\n' % it)
    program_log_data.append('# training data: %d\n' % len(training_topic))
    program_log_data.append('total inferred: %d\n' % num_total)
    program_log_data.append('# of multiple types: %d\n' % num_multiple_types)
    program_log_data.append('correction rate: %d/%d (%f)\n' % (num_total-num_incorrect, num_total, ((num_total-num_incorrect)/float(num_total))))

    correction.append((num_total-num_incorrect)/float(num_total))

# statistics
with open(os.path.join(current_dir, 'trial', 'program.log'), 'w') as f:
    arr = numpy.array(correction)
    print '## Summary Total ##'
    print 'avg correction rate:', numpy.mean(arr)
    print 'std:', numpy.std(arr)
    print 'min:', numpy.min(arr)
    print 'max:', numpy.max(arr)
    f.writelines(program_log_data)
    f.write('## Summary Total ##\n')
    f.write('avg correction rate: %f\n' % numpy.mean(arr))
    f.write('std: %f\n' % numpy.std(arr))
    f.write('min: %f\n' % numpy.min(arr))
    f.write('max: %f\n' % numpy.max(arr))



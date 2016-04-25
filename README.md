## Using Semantic Similarity for Input Topic Identification in Crawling-based Web Application Testing

### Statistics

`results.ods`: The statistics

`forms.csv`: A list of the subject forms

`easy-forms.txt`: A list of the 35 simple forms used in the second experiment, with actions to submit the forms

### Programs

`train_and_test.py`: For running the proposed natural-language method

`rule_match.py`: For running the rule-based method

`combine.py`: For getting results for the RB+NL-n, RB+NL-m, and RB+NL-b methods

`executor.py`: A web driver for running the second expeirment

`preprocess.py`: A library for feature extraction

### Corpus and the labeled topics

`forms`: Offline cache of the subject forms

`corpus`: Preprocessed corpus from `forms`

`label-all-corpus.json`: Labeled topics of all 985 input fields from the 100 subject forms used in the experiments

### Experimental results

`trial/NUM-training.zip`: The first experiment, using NUM% as training data

`trial/experiment2.zip`: The second experiment, using 7 (20%) of the 35 forms as training data



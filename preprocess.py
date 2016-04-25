#!/usr/bin/python
# -*- coding: utf-8 -*-

import re


# extract feature vector of each input field of html files
def extract_features(soup_element):
    descriptive_attrs = ['id', 'name', 'value', 'type', 'placeholder']
    constraint_attrs = ['maxlength']
    feature_d = []  # descriptive features of the input element
    feature_c = []  # constraint features of the input element
    label_features = find_closest_labels(soup_element, iteration=5)
    if label_features:
        feature_d += label_features
    for key, value in soup_element.attrs.items():
        if value and key in descriptive_attrs:
            value = re.sub('[^a-zA-Z0-9]', ' ', value.lower())
            feature_d += [key, value]
        if value and key in constraint_attrs:
            value = re.sub('[^a-zA-Z0-9]', ' ', value.lower())
            feature_c += [key, value]
    return re.sub(' +', ' ', ' '.join(feature_d + feature_c))


def find_closest_labels(soup_element, iteration):
    if iteration == 0:  # No label found after multiple iterations
        return None
    siblings = []
    siblings += soup_element.find_previous_siblings()
    siblings += soup_element.find_next_siblings()
    labels = []
    candidate_tags = ['span', 'label']
    for tag in candidate_tags:
        labels += soup_element.find_previous_siblings(tag)
        labels += soup_element.find_next_siblings(tag)
        for sib in siblings:
            labels += sib.find_all(tag)
    if not labels:
        return find_closest_labels(soup_element.parent, iteration-1)
    else:
        content = []
        for l in labels:
            for s in l.stripped_strings:
                content.append(re.sub('[^a-zA-Z0-9]', ' ', s.lower()))
        if content:
            return content
        else:
            return find_closest_labels(soup_element.parent, iteration-1)
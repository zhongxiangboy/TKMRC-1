#! /user/bin/evn python
# -*- coding:utf8 -*-

"""

@Author   : Lau James
@Contact  : LauJames2017@whu.edu.cn
@Project  : TKMRC 
@File     : preprocess4tk.py
@Time     : 18-10-12 下午2:41
@Software : PyCharm
@Copyright: "Copyright (c) 2018 Lau James. All Rights Reserved"
"""

import json
import importlib
import sys
from collections import Counter
if sys.version[0] == '2':
    importlib.reload(sys)
    sys.setdefaultencoding("utf-8")


def precision_recall_f1(prediction, ground_truth):
    """
    This function calculates and returns the precision, recall and f1-score
    Args:
        prediction: prediction string or list to be matched
        ground_truth: golden string or list reference
    Returns:
        floats of (p, r, f1)
    Raises:
        None
    """

    # 基于Bool检索的方法
    # Prediction -- paragraph
    # ground_truth -- question
    if not isinstance(prediction, list):  # 不属于list类（isinstance考虑继承属性，认为子类和父类不同; type不考虑继承 ）
        prediction_tokens = prediction.split()
    else:
        prediction_tokens = prediction
    if not isinstance(ground_truth, list):
        ground_truth_tokens = ground_truth.split()
    else:
        ground_truth_tokens = ground_truth
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)  # Counter实现了运算符重载，这里求交集
    num_same = sum(common.values())
    if num_same == 0:
        return 0, 0, 0
    p = 1.0 * num_same / len(prediction_tokens)
    r = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * p * r) / (p + r)
    return p, r, f1


def recall(prediction, ground_truth):
    """
    This function calculates and returns the recall
    Args:
        prediction: prediction string or list to be matched
        ground_truth: golden string or list reference
    Returns:
        floats of recall
    Raises:
        None
    """
    return precision_recall_f1(prediction, ground_truth)[1]


def f1_score(prediction, ground_truth):
    """
    This function calculates and returns the f1-score
    Args:
        prediction: prediction string or list to be matched
        ground_truth: golden string or list reference
    Returns:
        floats of f1
    Raises:
        None
    """
    return precision_recall_f1(prediction, ground_truth)[2]


def metric_max_over_ground_truths(metric_fn, prediction, ground_truths):
    """
    This function calculates and returns the precision, recall and f1-score
    Args:
        metric_fn: metric function pointer which calculates scores according to corresponding logic.
        prediction: prediction string or list to be matched
        ground_truth: golden string or list reference
    Returns:
        floats of (p, r, f1)
    Raises:
        None
    """
    scores_for_ground_truths = []
    for ground_truth in ground_truths:
        score = metric_fn(prediction, ground_truth)
        scores_for_ground_truths.append(score)
    return max(scores_for_ground_truths)


def find_best_question_match(doc, question, with_score=False):
    """
    For each docment, find the paragraph that matches best to the question.
    Args:
        doc: The document object.
        question: The question tokens.
        with_score: If True then the match score will be returned,
            otherwise False.
    Returns:
        The index of the best match paragraph, if with_score=False,
        otherwise returns a tuple of the index of the best match paragraph
        and the match score of that paragraph.
    """
    most_related_para = -1
    max_related_score = 0
    most_related_para_len = 0
    for p_idx, para_tokens in enumerate(doc['segmented_paragraphs']):
        if len(question) > 0:
            related_score = metric_max_over_ground_truths(recall, para_tokens, question)
            # 以recall为标准，找出和问题最佳匹配的段落
        else:
            related_score = 0

        if related_score > max_related_score \
                or (related_score == max_related_score \
                and len(para_tokens) < most_related_para_len):
            most_related_para = p_idx
            max_related_score = related_score
            most_related_para_len = len(para_tokens)
    if most_related_para == -1:
        most_related_para = 0
    if with_score:
        return most_related_para, max_related_score
    return most_related_para


def find_fake_answer(sample):
    """
    For each document, finds the most related paragraph based on recall,
    then finds a span that maximize the f1_score compared with the gold answers
    and uses this span as a fake answer span
    Args:
        sample: a sample in the dataset
    Returns:
        None
    Raises:
        None
    """
    for doc in sample['documents']:
        most_related_para = -1
        most_related_para_len = 999999
        max_related_score = 0
        for p_idx, para_tokens in enumerate(doc['segmented_paragraphs']):
            if len(sample['segmented_answers']) > 0:
                related_score = metric_max_over_ground_truths(recall,
                                                              para_tokens,
                                                              sample['segmented_answers'])
                # 以recall为标准，根据答案寻找最佳匹配段落
            else:
                continue
            if related_score > max_related_score \
                    or (related_score == max_related_score
                        and len(para_tokens) < most_related_para_len):
                most_related_para = p_idx
                most_related_para_len = len(para_tokens)
                max_related_score = related_score
        doc['most_related_para'] = most_related_para

    sample['answer_docs'] = []
    sample['answer_spans'] = []
    sample['fake_answers'] = []
    sample['match_scores'] = []

    best_match_score = 0
    best_match_d_idx, best_match_span = -1, [-1, -1]
    best_fake_answer = None
    answer_tokens = set()
    for segmented_answer in sample['segmented_answers']:
        answer_tokens = answer_tokens | set([token for token in segmented_answer])
    for d_idx, doc in enumerate(sample['documents']):
        if not doc['is_selected']:
            continue
        if doc['most_related_para'] == -1:
            doc['most_related_para'] = 0
        most_related_para_tokens = doc['segmented_paragraphs'][doc['most_related_para']][:1000]
        for start_tidx in range(len(most_related_para_tokens)):
            if most_related_para_tokens[start_tidx] not in answer_tokens:
                continue
            for end_tidx in range(len(most_related_para_tokens) - 1, start_tidx - 1, -1):
                span_tokens = most_related_para_tokens[start_tidx: end_tidx + 1]
                if len(sample['segmented_answers']) > 0:
                    match_score = metric_max_over_ground_truths(f1_score, span_tokens,
                                                                sample['segmented_answers'])
                    # 在找出的段落tokens list，以最大化f1为标准，找出和答案最相关的span定位
                else:
                    match_score = 0
                if match_score == 0:
                    break
                if match_score > best_match_score:
                    best_match_d_idx = d_idx
                    best_match_span = [start_tidx, end_tidx]
                    best_match_score = match_score
                    best_fake_answer = ''.join(span_tokens)
    if best_match_score > 0:
        sample['answer_docs'].append(best_match_d_idx)
        sample['answer_spans'].append(best_match_span)
        sample['fake_answers'].append(best_fake_answer)
        sample['match_scores'].append(best_match_score)


if __name__ == '__main__':
    # for line in sys.stdin:
    #     sample = json.loads(line)
    #     find_fake_answer(sample)
    #     print(json.dumps(sample, encoding='utf8', ensure_ascii=False))
    try:
        # fo = open('../data/TKData/tk_processed.json', 'w', encoding='utf8')
        # with open('../data/TKData/tk_json_cut.json', 'r') as fin:
        fo = open('../data/TKData/tk_processed.json', 'w', encoding='utf8')
        with open('../data/TKData/tk_json_cut.json', 'r') as fin:
            samples = fin.readlines()
            for line in samples:
                sample = json.loads(line)
                find_fake_answer(sample)
                # print(sample['answer_spans'])
                if sample['answer_spans']:  # 注意None 和 [] 的区别
                    json_sample = json.dumps(sample, ensure_ascii=False)
                    # print(str(json_sample))
                    fo.write(str(json_sample))
                    fo.write('\n')
                else:
                    continue
    finally:
        fo.close()